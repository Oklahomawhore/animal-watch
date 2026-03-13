"""
林麝行为检测系统 - 冷启动方案
无需标注数据，使用预训练模型 + 传统CV方法
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import time

class EventType(Enum):
    """原子事件类型"""
    MOVEMENT = "movement"           # 移动
    EATING = "eating"               # 进食
    DRINKING = "drinking"           # 饮水
    RESTING = "resting"             # 休息
    INTERACTION = "interaction"     # 社交互动
    ALERT = "alert"                 # 警觉/异常

@dataclass
class DetectionBox:
    """检测框"""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int
    class_name: str

@dataclass
class AtomicEvent:
    """原子事件"""
    event_type: EventType
    timestamp: float
    confidence: float
    bbox: Optional[DetectionBox] = None
    metadata: Dict = None
    
    def to_dict(self) -> Dict:
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "bbox": {
                "x1": self.bbox.x1,
                "y1": self.bbox.y1,
                "x2": self.bbox.x2,
                "y2": self.bbox.y2,
                "confidence": self.bbox.confidence
            } if self.bbox else None,
            "metadata": self.metadata or {}
        }

class ColdStartDetector:
    """
    冷启动检测器
    使用无监督方法检测林麝及行为
    """
    
    def __init__(self):
        self.prev_frame = None
        self.prev_boxes = []
        self.movement_history = []
        self.event_buffer = []
        
        # 背景建模（用于检测移动）
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=16, detectShadows=False
        )
        
        # 食槽/水盆区域（初始化后设置）
        self.feeding_roi = None
        self.water_roi = None
        
    def set_regions(self, feeding_roi: Tuple[int, int, int, int], 
                    water_roi: Tuple[int, int, int, int]):
        """设置食槽和水盆区域 (x, y, w, h)"""
        self.feeding_roi = feeding_roi
        self.water_roi = water_roi
    
    def detect_animals(self, frame: np.ndarray) -> List[DetectionBox]:
        """
        检测动物（冷启动：使用背景减除 + 轮廓检测）
        无需预训练模型，纯CV方法
        """
        # 背景减除
        fg_mask = self.bg_subtractor.apply(frame)
        
        # 形态学操作去噪
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        
        # 查找轮廓
        contours, _ = cv2.findContours(
            fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        boxes = []
        h, w = frame.shape[:2]
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            # 过滤太小的轮廓（噪声）和太大的轮廓（背景）
            if area < 500 or area > w * h * 0.5:
                continue
                
            x, y, bw, bh = cv2.boundingRect(cnt)
            
            # 长宽比过滤（林麝体型特征：长>宽）
            aspect_ratio = bh / bw if bw > 0 else 0
            if aspect_ratio < 0.5 or aspect_ratio > 3.0:
                continue
            
            # 计算置信度（基于轮廓规整度）
            perimeter = cv2.arcLength(cnt, True)
            circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
            confidence = min(0.95, 0.5 + circularity * 0.5)
            
            boxes.append(DetectionBox(
                x1=x, y1=y, x2=x+bw, y2=y+bh,
                confidence=confidence,
                class_id=0,
                class_name="animal"
            ))
        
        return boxes
    
    def detect_feeding_trough(self, frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        检测食槽区域（基于颜色和形状）
        """
        if self.feeding_roi:
            return self.feeding_roi
            
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 检测绿色区域（草料）
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 255])
        mask = cv2.inRange(hsv, lower_green, upper_green)
        
        # 查找最大绿色区域
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            largest = max(contours, key=cv2.contourArea)
            if cv2.contourArea(largest) > 1000:
                x, y, w, h = cv2.boundingRect(largest)
                return (x, y, w, h)
        
        return None
    
    def detect_water_basin(self, frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        检测水盆区域（基于颜色）
        """
        if self.water_roi:
            return self.water_roi
            
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 检测蓝色/反光区域
        lower_blue = np.array([90, 50, 50])
        upper_blue = np.array([130, 255, 255])
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            largest = max(contours, key=cv2.contourArea)
            if cv2.contourArea(largest) > 500:
                x, y, w, h = cv2.boundingRect(largest)
                return (x, y, w, h)
        
        return None
    
    def calculate_movement(self, current_boxes: List[DetectionBox]) -> float:
        """
        计算整体运动量（基于框的位移和数量变化）
        """
        if not self.prev_boxes or not current_boxes:
            self.prev_boxes = current_boxes
            return 0.0
        
        total_movement = 0.0
        matched_pairs = []
        
        # 简单的IOU匹配
        for curr in current_boxes:
            best_iou = 0.3  # IOU阈值
            best_prev = None
            
            for prev in self.prev_boxes:
                iou = self._calculate_iou(curr, prev)
                if iou > best_iou:
                    best_iou = iou
                    best_prev = prev
            
            if best_prev:
                # 计算中心点位移
                curr_cx = (curr.x1 + curr.x2) / 2
                curr_cy = (curr.y1 + curr.y2) / 2
                prev_cx = (best_prev.x1 + best_prev.x2) / 2
                prev_cy = (best_prev.y1 + best_prev.y2) / 2
                
                displacement = np.sqrt((curr_cx - prev_cx)**2 + (curr_cy - prev_cy)**2)
                total_movement += displacement
                matched_pairs.append((curr, best_prev))
        
        self.prev_boxes = current_boxes
        
        # 归一化运动量 (0-100)
        movement_score = min(100, total_movement / max(len(current_boxes), 1) * 2)
        return movement_score
    
    def detect_eating(self, frame: np.ndarray, animal_boxes: List[DetectionBox]) -> List[AtomicEvent]:
        """
        检测进食行为（动物在食槽区域停留）
        """
        events = []
        feeding_roi = self.detect_feeding_trough(frame)
        
        if not feeding_roi:
            return events
        
        fx, fy, fw, fh = feeding_roi
        
        for box in animal_boxes:
            # 计算动物框与食槽区域的重叠
            overlap_x = max(0, min(box.x2, fx + fw) - max(box.x1, fx))
            overlap_y = max(0, min(box.y2, fy + fh) - max(box.y1, fy))
            overlap_area = overlap_x * overlap_y
            
            box_area = (box.x2 - box.x1) * (box.y2 - box.y1)
            overlap_ratio = overlap_area / box_area if box_area > 0 else 0
            
            # 如果重叠超过30%，认为是进食
            if overlap_ratio > 0.3:
                events.append(AtomicEvent(
                    event_type=EventType.EATING,
                    timestamp=time.time(),
                    confidence=overlap_ratio,
                    bbox=box,
                    metadata={
                        "feeding_roi": feeding_roi,
                        "overlap_ratio": overlap_ratio
                    }
                ))
        
        return events
    
    def detect_drinking(self, frame: np.ndarray, animal_boxes: List[DetectionBox]) -> List[AtomicEvent]:
        """
        检测饮水行为（动物在水盆区域停留）
        """
        events = []
        water_roi = self.detect_water_basin(frame)
        
        if not water_roi:
            return events
        
        wx, wy, ww, wh = water_roi
        
        for box in animal_boxes:
            overlap_x = max(0, min(box.x2, wx + ww) - max(box.x1, wx))
            overlap_y = max(0, min(box.y2, wy + wh) - max(box.y1, wy))
            overlap_area = overlap_x * overlap_y
            
            box_area = (box.x2 - box.x1) * (box.y2 - box.y1)
            overlap_ratio = overlap_area / box_area if box_area > 0 else 0
            
            if overlap_ratio > 0.3:
                events.append(AtomicEvent(
                    event_type=EventType.DRINKING,
                    timestamp=time.time(),
                    confidence=overlap_ratio,
                    bbox=box,
                    metadata={
                        "water_roi": water_roi,
                        "overlap_ratio": overlap_ratio
                    }
                ))
        
        return events
    
    def process_frame(self, frame: np.ndarray) -> Dict:
        """
        处理单帧图像，返回所有检测到的事件
        """
        timestamp = time.time()
        
        # 1. 检测动物
        animal_boxes = self.detect_animals(frame)
        
        # 2. 计算运动量
        movement_score = self.calculate_movement(animal_boxes)
        
        # 3. 检测各种行为
        events = []
        
        # 移动事件
        if movement_score > 10:
            events.append(AtomicEvent(
                event_type=EventType.MOVEMENT,
                timestamp=timestamp,
                confidence=min(1.0, movement_score / 100),
                metadata={"movement_score": movement_score}
            ))
        
        # 进食事件
        eating_events = self.detect_eating(frame, animal_boxes)
        events.extend(eating_events)
        
        # 饮水事件
        drinking_events = self.detect_drinking(frame, animal_boxes)
        events.extend(drinking_events)
        
        # 休息事件（低运动量 + 存在动物）
        if movement_score < 5 and len(animal_boxes) > 0:
            events.append(AtomicEvent(
                event_type=EventType.RESTING,
                timestamp=timestamp,
                confidence=0.8,
                metadata={"animal_count": len(animal_boxes)}
            ))
        
        return {
            "timestamp": timestamp,
            "animal_count": len(animal_boxes),
            "movement_score": movement_score,
            "events": [e.to_dict() for e in events],
            "detections": [
                {
                    "x1": b.x1, "y1": b.y1, "x2": b.x2, "y2": b.y2,
                    "confidence": b.confidence
                } for b in animal_boxes
            ]
        }
    
    def _calculate_iou(self, box1: DetectionBox, box2: DetectionBox) -> float:
        """计算两个框的IOU"""
        x1 = max(box1.x1, box2.x1)
        y1 = max(box1.y1, box2.y1)
        x2 = min(box1.x2, box2.x2)
        y2 = min(box1.y2, box2.y2)
        
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1.x2 - box1.x1) * (box1.y2 - box1.y1)
        area2 = (box2.x2 - box2.x1) * (box2.y2 - box2.y1)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0


class EventStreamGenerator:
    """
    事件流生成器
    将连续帧处理为结构化事件流
    """
    
    def __init__(self, detector: ColdStartDetector):
        self.detector = detector
        self.event_history = []
        self.last_event_time = {}
        
        # 事件去重间隔（秒）
        self.event_cooldown = {
            EventType.EATING: 30,      # 进食事件30秒内不重复
            EventType.DRINKING: 30,    # 饮水事件30秒内不重复
            EventType.MOVEMENT: 5,     # 移动事件5秒内不重复
            EventType.RESTING: 60      # 休息事件60秒内不重复
        }
    
    def process_frame(self, frame: np.ndarray) -> List[AtomicEvent]:
        """
        处理单帧并返回新事件（去重后）
        """
        result = self.detector.process_frame(frame)
        current_time = time.time()
        
        new_events = []
        
        for event_dict in result["events"]:
            event_type = EventType(event_dict["event_type"])
            
            # 检查冷却时间
            last_time = self.last_event_time.get(event_type, 0)
            cooldown = self.event_cooldown.get(event_type, 10)
            
            if current_time - last_time > cooldown:
                event = AtomicEvent(
                    event_type=event_type,
                    timestamp=current_time,
                    confidence=event_dict["confidence"],
                    metadata=event_dict.get("metadata", {})
                )
                new_events.append(event)
                self.last_event_time[event_type] = current_time
                self.event_history.append(event)
        
        return new_events
    
    def get_event_stream(self, max_events: int = 100) -> List[Dict]:
        """获取最近的事件流"""
        recent = self.event_history[-max_events:]
        return [e.to_dict() for e in recent]
    
    def get_statistics(self, time_window: int = 3600) -> Dict:
        """
        获取事件统计（默认最近1小时）
        """
        current_time = time.time()
        recent_events = [
            e for e in self.event_history 
            if current_time - e.timestamp < time_window
        ]
        
        stats = {
            "total_events": len(recent_events),
            "event_counts": {},
            "time_window_seconds": time_window
        }
        
        for event_type in EventType:
            count = sum(1 for e in recent_events if e.event_type == event_type)
            stats["event_counts"][event_type.value] = count
        
        return stats
