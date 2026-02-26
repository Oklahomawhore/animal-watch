#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康互联开放平台 - 运动量检测系统
=================================

功能：
1. 使用 AK/SK 换取 AccessToken
2. 调用抓拍 API 获取设备图片
3. YOLO 检测动物矩形框
4. 记录运动轨迹并计算活动量

使用方法：
  python activity_monitor.py --ak YOUR_AK --sk YOUR_SK --device-id YOUR_DEVICE_ID
"""

import os
import sys
import json
import time
import base64
import hashlib
import hmac
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import deque
import threading
import queue

try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
except ImportError:
    print("Installing requests...")
    os.system("pip3 install -q requests")
    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry

try:
    import cv2
    import numpy as np
except ImportError:
    print("Installing opencv-python...")
    os.system("pip3 install -q opencv-python numpy")
    import cv2
    import numpy as np

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class AnimalDetection:
    """动物检测结果"""
    timestamp: str
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    confidence: float
    center_x: float
    center_y: float
    area: float


@dataclass
class ActivityMetrics:
    """活动量指标"""
    timestamp: str
    animal_count: int
    total_movement: float  # 总移动距离(像素)
    avg_speed: float       # 平均速度(像素/秒)
    activity_level: str    # idle/low/medium/high
    bounding_boxes: List[Dict]


class HikvisionCloudClient:
    """海康互联云 API 客户端"""
    
    # API 端点配置
    BASE_URL = "https://api.hikiot.com"  # 正式环境
    # BASE_URL = "https://test-api.hikiot.com"  # 测试环境
    
    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.access_token = None
        self.token_expire_time = 0
        
        # 创建会话
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 先获取 token
        self._refresh_token()
    
    def _sign(self, params: Dict[str, str]) -> str:
        """
        生成签名
        海康互联签名算法: MD5(appKey + appSecret + timestamp)
        """
        # 按参数名排序
        sorted_params = sorted(params.items())
        param_str = "".join([f"{k}{v}" for k, v in sorted_params])
        
        # 拼接签名字符串
        sign_str = f"{self.app_key}{self.app_secret}{param_str}"
        
        # MD5 签名
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()
    
    def _refresh_token(self):
        """获取/刷新 AccessToken"""
        url = f"{self.BASE_URL}/v1/token/get"
        
        timestamp = str(int(time.time() * 1000))
        params = {
            "appKey": self.app_key,
            "timestamp": timestamp,
        }
        
        sign = self._sign(params)
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        data = {
            "appKey": self.app_key,
            "timestamp": timestamp,
            "sign": sign,
        }
        
        try:
            resp = self.session.post(url, data=data, headers=headers, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            
            if result.get("code") == "200" or result.get("code") == 200:
                self.access_token = result["data"]["accessToken"]
                expire_in = result["data"].get("expireIn", 7200)  # 默认2小时
                self.token_expire_time = time.time() + expire_in - 300  # 提前5分钟过期
                logger.info(f"Token 获取成功，有效期 {expire_in} 秒")
            else:
                raise Exception(f"Token 获取失败: {result.get('msg', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"获取 Token 失败: {e}")
            raise
    
    def _ensure_token(self):
        """确保 token 有效"""
        if time.time() >= self.token_expire_time:
            logger.info("Token 即将过期，刷新中...")
            self._refresh_token()
    
    def _api_request(self, method: str, path: str, **kwargs) -> Dict:
        """发送 API 请求"""
        self._ensure_token()
        
        url = f"{self.BASE_URL}{path}"
        headers = kwargs.pop('headers', {})
        headers['accessToken'] = self.access_token
        
        try:
            resp = self.session.request(method, url, headers=headers, **kwargs, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"API 请求失败: {e}")
            raise
    
    def get_device_list(self) -> List[Dict]:
        """获取设备列表"""
        result = self._api_request('GET', '/v1/device/list')
        if result.get("code") in [200, "200"]:
            return result.get("data", {}).get("list", [])
        return []
    
    def capture_device(self, device_id: str, channel_no: int = 1) -> Optional[np.ndarray]:
        """
        设备抓拍
        
        Args:
            device_id: 设备序列号
            channel_no: 通道号，默认1
        
        Returns:
            OpenCV 图像 (BGR格式) 或 None
        """
        url = f"{self.BASE_URL}/v1/device/capture"
        
        params = {
            "deviceSerial": device_id,
            "channelNo": channel_no,
        }
        
        headers = {
            'accessToken': self.access_token,
        }
        
        try:
            resp = self.session.post(url, data=params, headers=headers, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            
            if result.get("code") in [200, "200"]:
                # 获取图片 URL
                pic_url = result.get("data", {}).get("picUrl")
                if pic_url:
                    # 下载图片
                    img_resp = self.session.get(pic_url, timeout=30)
                    img_resp.raise_for_status()
                    
                    # 转换为 OpenCV 格式
                    img_array = np.frombuffer(img_resp.content, np.uint8)
                    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                    return img
            else:
                logger.warning(f"抓拍失败: {result.get('msg')}")
                
        except Exception as e:
            logger.error(f"抓拍异常: {e}")
        
        return None


class SimpleYOLODetector:
    """
    简化版 YOLO 检测器
    
    使用 OpenCV DNN 模块加载 YOLO 模型
    或使用背景差分作为 fallback
    """
    
    def __init__(self, use_background_subtraction: bool = True):
        self.use_bg_subtraction = use_background_subtraction
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=50, varThreshold=25, detectShadows=False
        )
        self.prev_frame = None
        self.prev_detections = []
        
        # YOLO 模型路径（可选）
        self.yolo_net = None
        self.yolo_classes = []
        self._load_yolo_model()
    
    def _load_yolo_model(self):
        """加载 YOLO 模型（如果有）"""
        model_path = Path("models/yolov5s.onnx")
        config_path = Path("models/yolov5s.yaml")
        
        if model_path.exists():
            try:
                self.yolo_net = cv2.dnn.readNetFromONNX(str(model_path))
                logger.info(f"YOLO 模型加载成功: {model_path}")
            except Exception as e:
                logger.warning(f"YOLO 模型加载失败: {e}，使用背景差分")
                self.yolo_net = None
    
    def detect(self, frame: np.ndarray) -> List[AnimalDetection]:
        """
        检测动物
        
        Returns:
            检测结果列表
        """
        detections = []
        
        if self.yolo_net is not None:
            # 使用 YOLO 检测
            detections = self._detect_yolo(frame)
        else:
            # 使用背景差分检测移动物体
            detections = self._detect_background_subtraction(frame)
        
        return detections
    
    def _detect_yolo(self, frame: np.ndarray) -> List[AnimalDetection]:
        """YOLO 检测"""
        detections = []
        
        # 预处理
        blob = cv2.dnn.blobFromImage(frame, 1/255.0, (640, 640), swapRB=True, crop=False)
        self.yolo_net.setInput(blob)
        
        # 推理
        outputs = self.yolo_net.forward()
        
        # 解析结果
        h, w = frame.shape[:2]
        for detection in outputs[0]:
            confidence = detection[4]
            if confidence > 0.5:  # 置信度阈值
                # 提取边界框
                cx, cy, bw, bh = detection[0:4]
                x1 = int((cx - bw/2) * w)
                y1 = int((cy - bh/2) * h)
                x2 = int((cx + bw/2) * w)
                y2 = int((cy + bh/2) * h)
                
                bbox = (max(0, x1), max(0, y1), x2-x1, y2-y1)
                
                det = AnimalDetection(
                    timestamp=datetime.now().isoformat(),
                    bbox=bbox,
                    confidence=float(confidence),
                    center_x=(x1 + x2) / 2,
                    center_y=(y1 + y2) / 2,
                    area=(x2-x1) * (y2-y1)
                )
                detections.append(det)
        
        return detections
    
    def _detect_background_subtraction(self, frame: np.ndarray) -> List[AnimalDetection]:
        """背景差分检测移动物体"""
        detections = []
        
        # 应用背景减除
        fg_mask = self.bg_subtractor.apply(frame)
        
        # 形态学操作
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_CLOSE, kernel)
        
        # 查找轮廓
        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > 500:  # 过滤小噪声
                x, y, w, h = cv2.boundingRect(cnt)
                
                det = AnimalDetection(
                    timestamp=datetime.now().isoformat(),
                    bbox=(x, y, w, h),
                    confidence=min(0.95, area / 10000),  # 根据面积估算置信度
                    center_x=x + w/2,
                    center_y=y + h/2,
                    area=area
                )
                detections.append(det)
        
        return detections


class ActivityMonitor:
    """运动量监控器"""
    
    def __init__(self, cloud_client: HikvisionCloudClient, detector: SimpleYOLODetector):
        self.cloud = cloud_client
        self.detector = detector
        
        # 历史记录
        self.detection_history: deque = deque(maxlen=1000)
        self.metrics_history: deque = deque(maxlen=100)
        
        # 运行状态
        self.running = False
        self.monitor_thread = None
        self.result_queue = queue.Queue()
    
    def calculate_activity(self, detections: List[AnimalDetection], 
                          prev_detections: List[AnimalDetection],
                          time_delta: float) -> ActivityMetrics:
        """计算活动量"""
        timestamp = datetime.now().isoformat()
        
        if not detections:
            return ActivityMetrics(
                timestamp=timestamp,
                animal_count=0,
                total_movement=0,
                avg_speed=0,
                activity_level="idle",
                bounding_boxes=[]
            )
        
        # 计算移动距离
        total_movement = 0
        matched_pairs = []
        
        # 简单的最近邻匹配
        for det in detections:
            min_dist = float('inf')
            nearest_prev = None
            
            for prev_det in prev_detections:
                dist = ((det.center_x - prev_det.center_x)**2 + 
                       (det.center_y - prev_det.center_y)**2)**0.5
                if dist < min_dist:
                    min_dist = dist
                    nearest_prev = prev_det
            
            if nearest_prev and min_dist < 200:  # 最大匹配距离
                total_movement += min_dist
                matched_pairs.append((det, nearest_prev, min_dist))
        
        # 计算平均速度
        avg_speed = total_movement / time_delta if time_delta > 0 else 0
        
        # 判定活动等级
        if avg_speed < 5:
            level = "idle"
        elif avg_speed < 20:
            level = "low"
        elif avg_speed < 50:
            level = "medium"
        else:
            level = "high"
        
        return ActivityMetrics(
            timestamp=timestamp,
            animal_count=len(detections),
            total_movement=total_movement,
            avg_speed=avg_speed,
            activity_level=level,
            bounding_boxes=[{
                "x": d.bbox[0],
                "y": d.bbox[1],
                "width": d.bbox[2],
                "height": d.bbox[3],
                "confidence": d.confidence
            } for d in detections]
        )
    
    def start_monitoring(self, device_id: str, channel_no: int = 1, 
                        interval: float = 1.0, callback=None):
        """
        开始监控
        
        Args:
            device_id: 设备序列号
            channel_no: 通道号
            interval: 抓拍间隔(秒)
            callback: 结果回调函数
        """
        self.running = True
        prev_detections = []
        prev_time = time.time()
        
        logger.info(f"开始监控设备 {device_id}, 间隔 {interval} 秒")
        
        while self.running:
            try:
                # 抓拍
                frame = self.cloud.capture_device(device_id, channel_no)
                
                if frame is None:
                    logger.warning("抓拍失败，等待下次")
                    time.sleep(interval)
                    continue
                
                current_time = time.time()
                time_delta = current_time - prev_time
                
                # 检测动物
                detections = self.detector.detect(frame)
                
                # 记录历史
                self.detection_history.extend(detections)
                
                # 计算活动量
                metrics = self.calculate_activity(detections, prev_detections, time_delta)
                self.metrics_history.append(metrics)
                
                # 回调
                if callback:
                    callback(frame, detections, metrics)
                
                # 更新状态
                prev_detections = detections
                prev_time = current_time
                
                # 打印状态
                logger.info(f"[{device_id}] 检测到 {metrics.animal_count} 只动物, "
                          f"活动等级: {metrics.activity_level}, "
                          f"速度: {metrics.avg_speed:.1f} px/s")
                
                # 等待下次
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"监控异常: {e}")
                time.sleep(interval)
    
    def stop(self):
        """停止监控"""
        self.running = False
        logger.info("监控已停止")
    
    def get_report(self, hours: int = 1) -> Dict:
        """生成活动报告"""
        recent_metrics = list(self.metrics_history)[-3600:]  # 最近1小时
        
        if not recent_metrics:
            return {"error": "无数据"}
        
        speeds = [m.avg_speed for m in recent_metrics]
        counts = [m.animal_count for m in recent_metrics]
        
        # 统计活动等级
        level_counts = {}
        for m in recent_metrics:
            level_counts[m.activity_level] = level_counts.get(m.activity_level, 0) + 1
        
        return {
            "period_hours": hours,
            "total_samples": len(recent_metrics),
            "avg_speed": sum(speeds) / len(speeds),
            "max_speed": max(speeds),
            "avg_animal_count": sum(counts) / len(counts),
            "activity_distribution": level_counts,
            "current_level": recent_metrics[-1].activity_level if recent_metrics else "unknown"
        }


def visualize_detection(frame: np.ndarray, detections: List[AnimalDetection], 
                       metrics: ActivityMetrics, save_path: Optional[str] = None) -> np.ndarray:
    """可视化检测结果"""
    img = frame.copy()
    
    # 绘制边界框
    for det in detections:
        x, y, w, h = det.bbox
        color = (0, 255, 0) if det.confidence > 0.7 else (0, 165, 255)
        cv2.rectangle(img, (x, y), (x+w, y+h), color, 2)
        
        # 标签
        label = f"{det.confidence:.2f}"
        cv2.putText(img, label, (x, y-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    # 绘制状态信息
    info_lines = [
        f"Animals: {metrics.animal_count}",
        f"Level: {metrics.activity_level}",
        f"Speed: {metrics.avg_speed:.1f} px/s",
        f"Time: {datetime.now().strftime('%H:%M:%S')}"
    ]
    
    y_offset = 30
    for line in info_lines:
        cv2.putText(img, line, (10, y_offset),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        y_offset += 30
    
    if save_path:
        cv2.imwrite(save_path, img)
    
    return img


def main():
    parser = argparse.ArgumentParser(description='海康云运动量检测')
    parser.add_argument('--ak', required=True, help='App Key')
    parser.add_argument('--sk', required=True, help='App Secret')
    parser.add_argument('--device-id', required=True, help='设备序列号')
    parser.add_argument('--channel', type=int, default=1, help='通道号')
    parser.add_argument('--interval', type=float, default=1.0, help='抓拍间隔(秒)')
    parser.add_argument('--output', default='output', help='输出目录')
    
    args = parser.parse_args()
    
    # 创建输出目录
    output_dir = Path(args.output)
    output_dir.mkdir(exist_ok=True)
    
    try:
        # 初始化
        logger.info("初始化海康云客户端...")
        cloud = HikvisionCloudClient(args.ak, args.sk)
        
        logger.info("初始化检测器...")
        detector = SimpleYOLODetector()
        
        monitor = ActivityMonitor(cloud, detector)
        
        # 可视化回调
        frame_count = 0
        def on_frame(frame, detections, metrics):
            nonlocal frame_count
            frame_count += 1
            
            vis_img = visualize_detection(frame, detections, metrics)
            
            # 每10帧保存一次
            if frame_count % 10 == 0:
                save_path = output_dir / f"frame_{frame_count:04d}.jpg"
                cv2.imwrite(str(save_path), vis_img)
                logger.info(f"保存图片: {save_path}")
            
            # 显示 (如果有图形界面)
            try:
                cv2.imshow('Activity Monitor', vis_img)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    monitor.stop()
            except:
                pass
        
        # 开始监控
        logger.info(f"开始监控设备 {args.device_id}...")
        monitor.start_monitoring(
            device_id=args.device_id,
            channel_no=args.channel,
            interval=args.interval,
            callback=on_frame
        )
        
    except KeyboardInterrupt:
        logger.info("用户中断")
    except Exception as e:
        logger.error(f"错误: {e}")
        raise


if __name__ == "__main__":
    main()
