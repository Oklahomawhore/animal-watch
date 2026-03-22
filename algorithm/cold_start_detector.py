"""
林麝行为检测系统 - 冷启动方案（优化版）
无需标注数据，使用预训练模型 + 传统CV方法

优化点：
1. 支持真实视频帧处理
2. 自适应参数调整
3. 更好的噪声过滤
4. 性能优化（满足1秒/帧要求）
"""

import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    
    @property
    def width(self) -> float:
        return self.x2 - self.x1
    
    @property
    def height(self) -> float:
        return self.y2 - self.y1
    
    @property
    def area(self) -> float:
        return self.width * self.height
    
    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)


@dataclass
class AtomicEvent:
    """原子事件"""
    event_type: EventType
    timestamp: float
    confidence: float
    bbox: Optional[DetectionBox] = None
    metadata: Dict = field(default_factory=dict)
    
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
            "metadata": self.metadata
        }


class ColdStartDetector:
    """
    冷启动检测器（优化版）
    使用无监督方法检测林麝及行为
    
    优化：
    - 自适应背景建模
    - 多尺度检测
    - 时序平滑
    """
    
    def __init__(self, 
                 min_animal_area: int = 800,
                 max_animal_area_ratio: float = 0.3,
                 movement_threshold: float = 10.0,
                 enable_temporal_smooth: bool = True):
        """
        初始化检测器
        
        Args:
            min_animal_area: 最小动物区域面积（像素）
            max_animal_area_ratio: 最大动物区域占画面比例
            movement_threshold: 运动量阈值
            enable_temporal_smooth: 启用时序平滑
        """
        self.min_animal_area = min_animal_area
        self.max_animal_area_ratio = max_animal_area_ratio
        self.movement_threshold = movement_threshold
        self.enable_temporal_smooth = enable_temporal_smooth
        
        # 帧缓存
        self.prev_frame = None
        self.prev_gray = None
        self.prev_boxes: List[DetectionBox] = []
        
        # 背景建模（用于检测移动）
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, 
            varThreshold=25,  # 提高阈值减少噪声
            detectShadows=False
        )
        
        # 时序平滑
        self.detection_history = deque(maxlen=5)
        self.movement_history = deque(maxlen=10)
        
        # 食槽/水盆区域（初始化后设置）
        self.feeding_roi: Optional[Tuple[int, int, int, int]] = None
        self.water_roi: Optional[Tuple[int, int, int, int]] = None
        
        # 性能统计
        self.frame_count = 0
        self.skip_frames = 0  # 跳过的帧数（用于降速）
        
    def set_regions(self, feeding_roi: Optional[Tuple[int, int, int, int]] = None, 
                    water_roi: Optional[Tuple[int, int, int, int]] = None):
        """
        设置食槽和水盆区域 (x, y, w, h)
        
        Args:
            feeding_roi: 食槽区域
            water_roi: 水盆区域
        """
        self.feeding_roi = feeding_roi
        self.water_roi = water_roi
        logger.info(f"✅ ROI区域已设置: 食槽={feeding_roi}, 水盆={water_roi}")
    
    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        预处理帧
        
        Args:
            frame: 原始帧
            
        Returns:
            预处理后的帧
        """
        # 确保是BGR格式
        if len(frame.shape) == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        elif frame.shape[2] == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
        
        # 降噪
        frame = cv2.GaussianBlur(frame, (5, 5), 0)
        
        return frame
    
    def detect_animals(self, frame: np.ndarray) -> List[DetectionBox]:
        """
        检测动物（优化版）
        使用背景减除 + 轮廓检测 + 多尺度分析
        
        Args:
            frame: 输入帧
            
        Returns:
            检测框列表
        """
        h, w = frame.shape[:2]
        max_area = w * h * self.max_animal_area_ratio
        
        # 背景减除
        fg_mask = self.bg_subtractor.apply(frame)
        
        # 形态学操作去噪（更强的滤波）
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel_open)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel_close)
        
        # 查找轮廓
        contours, _ = cv2.findContours(
            fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        boxes = []
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            
            # 面积过滤
            if area < self.min_animal_area or area > max_area:
                continue
            
            # 获取边界框
            x, y, bw, bh = cv2.boundingRect(cnt)
            
            # 长宽比过滤（林麝体型特征）
            aspect_ratio = bh / bw if bw > 0 else 0
            if aspect_ratio < 0.4 or aspect_ratio > 3.5:
                continue
            
            # 轮廓规整度（圆形度）
            perimeter = cv2.arcLength(cnt, True)
            circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
            
            # 凸包分析（排除不规则形状）
            hull = cv2.convexHull(cnt)
            hull_area = cv2.contourArea(hull)
            solidity = area / hull_area if hull_area > 0 else 0
            
            # 综合置信度
            confidence = min(0.95, 0.3 + circularity * 0.3 + solidity * 0.4)
            
            # 只保留高置信度检测
            if confidence > 0.4:
                boxes.append(DetectionBox(
                    x1=float(x),
                    y1=float(y),
                    x2=float(x + bw),
                    y2=float(y + bh),
                    confidence=confidence,
                    class_id=0,
                    class_name="animal"
                ))
        
        # 非极大值抑制（NMS）
        boxes = self._nms(boxes, threshold=0.3)
        
        # 时序平滑
        if self.enable_temporal_smooth:
            boxes = self._temporal_smooth(boxes)
        
        return boxes
    
    def _nms(self, boxes: List[DetectionBox], threshold: float = 0.3) -> List[DetectionBox]:
        """
        非极大值抑制
        
        Args:
            boxes: 检测框列表
            threshold: IOU阈值
            
        Returns:
            过滤后的框列表
        """
        if not boxes:
            return []
        
        # 按置信度排序
        boxes = sorted(boxes, key=lambda x: x.confidence, reverse=True)
        
        keep = []
        while boxes:
            current = boxes.pop(0)
            keep.append(current)
            
            # 移除重叠框
            boxes = [
                b for b in boxes 
                if self._calculate_iou(current, b) < threshold
            ]
        
        return keep
    
    def _temporal_smooth(self, boxes: List[DetectionBox]) -> List[DetectionBox]:
        """
        时序平滑（减少抖动）
        
        Args:
            boxes: 当前帧检测框
            
        Returns:
            平滑后的框
        """
        self.detection_history.append(boxes)
        
        if len(self.detection_history) < 3:
            return boxes
        
        # 如果连续多帧检测到相似位置，增加置信度
        smoothed = []
        for box in boxes:
            consistent_detections = 1
            for prev_boxes in list(self.detection_history)[:-1]:
                for prev_box in prev_boxes:
                    if self._calculate_iou(box, prev_box) > 0.5:
                        consistent_detections += 1
                        break
            
            # 根据一致性调整置信度
            if consistent_detections >= 2:
                box.confidence = min(0.99, box.confidence * 1.1)
            
            smoothed.append(box)
        
        return smoothed
    
    def detect_feeding_trough(self, frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        检测食槽区域（基于颜色和形状）
        
        Args:
            frame: 输入帧
            
        Returns:
            区域坐标 (x, y, w, h) 或 None
        """
        if self.feeding_roi:
            return self.feeding_roi
        
        # 自动检测（基于绿色区域）
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 检测绿色区域（草料）
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 255])
        mask = cv2.inRange(hsv, lower_green, upper_green)
        
        # 形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 10))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # 查找最大绿色区域
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)
            if area > 2000:  # 最小面积阈值
                x, y, w, h = cv2.boundingRect(largest)
                return (x, y, w, h)
        
        return None
    
    def detect_water_basin(self, frame: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        """
        检测水盆区域（基于颜色）
        
        Args:
            frame: 输入帧
            
        Returns:
            区域坐标 (x, y, w, h) 或 None
        """
        if self.water_roi:
            return self.water_roi
        
        # 自动检测（基于蓝色/反光区域）
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 检测蓝色区域
        lower_blue = np.array([90, 50, 50])
        upper_blue = np.array([130, 255, 255])
        mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)
        
        # 检测高亮区域（反光）
        lower_white = np.array([0, 0, 200])
        upper_white = np.array([180, 30, 255])
        mask_white = cv2.inRange(hsv, lower_white, upper_white)
        
        # 合并掩码
        mask = cv2.bitwise_or(mask_blue, mask_white)
        
        # 形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)
            if area > 1000:
                x, y, w, h = cv2.boundingRect(largest)
                return (x, y, w, h)
        
        return None
    
    def calculate_movement(self, current_boxes: List[DetectionBox]) -> float:
        """
        计算整体运动量（优化版）
        
        Args:
            current_boxes: 当前帧检测框
            
        Returns:
            运动量评分 (0-100)
        """
        if not self.prev_boxes or not current_boxes:
            self.prev_boxes = current_boxes
            return 0.0
        
        total_movement = 0.0
        matched_count = 0
        
        # IOU匹配
        for curr in current_boxes:
            best_iou = 0.3
            best_prev = None
            
            for prev in self.prev_boxes:
                iou = self._calculate_iou(curr, prev)
                if iou > best_iou:
                    best_iou = iou
                    best_prev = prev
            
            if best_prev:
                # 计算位移
                curr_cx, curr_cy = curr.center
                prev_cx, prev_cy = best_prev.center
                displacement = np.sqrt((curr_cx - prev_cx)**2 + (curr_cy - prev_cy)**2)
                total_movement += displacement
                matched_count += 1
        
        # 考虑未匹配的新检测（进入画面的动物）
        new_detections = len(current_boxes) - matched_count
        total_movement += new_detections * 20  # 新检测贡献固定运动量
        
        self.prev_boxes = current_boxes
        
        # 归一化
        movement_score = min(100, total_movement / max(len(current_boxes), 1) * 2)
        
        # 时序平滑
        self.movement_history.append(movement_score)
        if len(self.movement_history) >= 3:
            # 使用中位数平滑
            movement_score = np.median(list(self.movement_history)[-3:])
        
        return movement_score
    
    def detect_eating(self, frame: np.ndarray, animal_boxes: List[DetectionBox]) -> List[AtomicEvent]:
        """
        检测进食行为（动物在食槽区域停留）
        
        Args:
            frame: 输入帧
            animal_boxes: 动物检测框
            
        Returns:
            进食事件列表
        """
        events = []
        feeding_roi = self.detect_feeding_trough(frame)
        
        if not feeding_roi:
            return events
        
        fx, fy, fw, fh = feeding_roi
        
        for box in animal_boxes:
            # 计算重叠
            overlap_x = max(0, min(box.x2, fx + fw) - max(box.x1, fx))
            overlap_y = max(0, min(box.y2, fy + fh) - max(box.y1, fy))
            overlap_area = overlap_x * overlap_y
            
            overlap_ratio = overlap_area / box.area if box.area > 0 else 0
            
            # 重叠超过30%认为是进食
            if overlap_ratio > 0.3:
                events.append(AtomicEvent(
                    event_type=EventType.EATING,
                    timestamp=time.time(),
                    confidence=min(0.95, overlap_ratio),
                    bbox=box,
                    metadata={
                        "feeding_roi": feeding_roi,
                        "overlap_ratio": round(overlap_ratio, 3),
                        "feeding_area": fw * fh
                    }
                ))
        
        return events
    
    def detect_drinking(self, frame: np.ndarray, animal_boxes: List[DetectionBox]) -> List[AtomicEvent]:
        """
        检测饮水行为（动物在水盆区域停留）
        
        Args:
            frame: 输入帧
            animal_boxes: 动物检测框
            
        Returns:
            饮水事件列表
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
            
            overlap_ratio = overlap_area / box.area if box.area > 0 else 0
            
            if overlap_ratio > 0.3:
                events.append(AtomicEvent(
                    event_type=EventType.DRINKING,
                    timestamp=time.time(),
                    confidence=min(0.95, overlap_ratio),
                    bbox=box,
                    metadata={
                        "water_roi": water_roi,
                        "overlap_ratio": round(overlap_ratio, 3),
                        "water_area": ww * wh
                    }
                ))
        
        return events
    
    def detect_interactions(self, animal_boxes: List[DetectionBox]) -> List[AtomicEvent]:
        """
        检测社交互动（动物之间距离较近）
        
        Args:
            animal_boxes: 动物检测框
            
        Returns:
            互动事件列表
        """
        events = []
        
        if len(animal_boxes) < 2:
            return events
        
        # 检查每对动物的距离
        for i in range(len(animal_boxes)):
            for j in range(i + 1, len(animal_boxes)):
                box1, box2 = animal_boxes[i], animal_boxes[j]
                
                # 计算中心点距离
                c1 = box1.center
                c2 = box2.center
                distance = np.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2)
                
                # 距离小于阈值认为是互动
                avg_size = (box1.width + box1.height + box2.width + box2.height) / 4
                if distance < avg_size * 2:
                    events.append(AtomicEvent(
                        event_type=EventType.INTERACTION,
                        timestamp=time.time(),
                        confidence=min(0.9, 1.0 - distance / (avg_size * 3)),
                        metadata={
                            "distance": round(distance, 2),
                            "animal_pair": (i, j)
                        }
                    ))
        
        return events
    
    def process_frame(self, frame: np.ndarray) -> Dict:
        """
        处理单帧图像（优化版）
        
        Args:
            frame: 输入帧 (BGR格式)
            
        Returns:
            处理结果字典
        """
        start_time = time.time()
        timestamp = time.time()
        
        # 预处理
        frame = self.preprocess_frame(frame)
        
        # 1. 检测动物
        animal_boxes = self.detect_animals(frame)
        
        # 2. 计算运动量
        movement_score = self.calculate_movement(animal_boxes)
        
        # 3. 检测各种行为
        events = []
        
        # 移动事件
        if movement_score > self.movement_threshold:
            events.append(AtomicEvent(
                event_type=EventType.MOVEMENT,
                timestamp=timestamp,
                confidence=min(1.0, movement_score / 100),
                metadata={
                    "movement_score": round(movement_score, 2),
                    "threshold": self.movement_threshold
                }
            ))
        
        # 进食事件
        eating_events = self.detect_eating(frame, animal_boxes)
        events.extend(eating_events)
        
        # 饮水事件
        drinking_events = self.detect_drinking(frame, animal_boxes)
        events.extend(drinking_events)
        
        # 互动事件
        interaction_events = self.detect_interactions(animal_boxes)
        events.extend(interaction_events)
        
        # 休息事件（低运动量 + 存在动物）
        if movement_score < 5 and len(animal_boxes) > 0 and not eating_events and not drinking_events:
            events.append(AtomicEvent(
                event_type=EventType.RESTING,
                timestamp=timestamp,
                confidence=0.8,
                metadata={
                    "animal_count": len(animal_boxes),
                    "movement_score": round(movement_score, 2)
                }
            ))
        
        # 异常检测（高运动量但无明确行为）
        if movement_score > 50 and not eating_events and not drinking_events:
            events.append(AtomicEvent(
                event_type=EventType.ALERT,
                timestamp=timestamp,
                confidence=min(0.8, movement_score / 100),
                metadata={
                    "alert_type": "abnormal_activity",
                    "movement_score": round(movement_score, 2),
                    "description": "检测到异常活动"
                }
            ))
        
        # 计算处理时间
        process_time = time.time() - start_time
        self.frame_count += 1
        
        return {
            "timestamp": timestamp,
            "frame_count": self.frame_count,
            "process_time_ms": round(process_time * 1000, 2),
            "animal_count": len(animal_boxes),
            "movement_score": round(movement_score, 2),
            "events": [e.to_dict() for e in events],
            "detections": [
                {
                    "x1": round(b.x1, 2),
                    "y1": round(b.y1, 2),
                    "x2": round(b.x2, 2),
                    "y2": round(b.y2, 2),
                    "confidence": round(b.confidence, 3),
                    "center": (round(b.center[0], 2), round(b.center[1], 2))
                } for b in animal_boxes
            ],
            "roi": {
                "feeding": self.feeding_roi,
                "water": self.water_roi
            }
        }
    
    def _calculate_iou(self, box1: DetectionBox, box2: DetectionBox) -> float:
        """
        计算两个框的IOU
        
        Args:
            box1: 框1
            box2: 框2
            
        Returns:
            IOU值
        """
        x1 = max(box1.x1, box2.x1)
        y1 = max(box1.y1, box2.y1)
        x2 = min(box1.x2, box2.x2)
        y2 = min(box1.y2, box2.y2)
        
        intersection = max(0, x2 - x1) * max(0, y2 - y1)
        union = box1.area + box2.area - intersection
        
        return intersection / union if union > 0 else 0
    
    def reset(self):
        """重置检测器状态"""
        self.prev_frame = None
        self.prev_gray = None
        self.prev_boxes = []
        self.detection_history.clear()
        self.movement_history.clear()
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=25, detectShadows=False
        )
        self.frame_count = 0
        logger.info("✅ 检测器状态已重置")


class EventStreamGenerator:
    """
    事件流生成器
    将连续帧处理为结构化事件流
    """
    
    def __init__(self, detector: ColdStartDetector, cooldowns: Optional[Dict] = None):
        """
        初始化
        
        Args:
            detector: 检测器实例
            cooldowns: 事件冷却时间配置
        """
        self.detector = detector
        self.event_history: List[AtomicEvent] = []
        self.last_event_time: Dict[EventType, float] = {}
        
        # 事件冷却时间（秒）
        self.event_cooldown = cooldowns or {
            EventType.EATING: 30,
            EventType.DRINKING: 30,
            EventType.MOVEMENT: 5,
            EventType.RESTING: 60,
            EventType.INTERACTION: 10,
            EventType.ALERT: 5
        }
    
    def process_frame(self, frame: np.ndarray) -> List[AtomicEvent]:
        """
        处理单帧并返回新事件（去重后）
        
        Args:
            frame: 输入帧
            
        Returns:
            新事件列表
        """
        result = self.detector.process_frame(frame)
        current_time = time.time()
        
        new_events = []
        
        for event_dict in result["events"]:
            try:
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
            except Exception as e:
                logger.error(f"处理事件失败: {e}")
        
        return new_events
    
    def get_event_stream(self, max_events: int = 100) -> List[Dict]:
        """
        获取最近的事件流
        
        Args:
            max_events: 最大返回数量
            
        Returns:
            事件字典列表
        """
        recent = self.event_history[-max_events:]
        return [e.to_dict() for e in recent]
    
    def get_statistics(self, time_window: int = 3600) -> Dict:
        """
        获取事件统计
        
        Args:
            time_window: 时间窗口（秒）
            
        Returns:
            统计信息字典
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
    
    def reset(self):
        """重置生成器状态"""
        self.event_history.clear()
        self.last_event_time.clear()
        logger.info("✅ 事件流生成器已重置")
