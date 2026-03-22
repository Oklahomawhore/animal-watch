"""
林麝算法 Pipeline - 捕获服务
整合摄像头捕获和算法推理
"""
import cv2
import numpy as np
import time
import uuid
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Callable
from pathlib import Path
import threading
import queue

from cold_start_detector import ColdStartDetector, EventStreamGenerator, EventType, DetectionBox
from config_manager import get_config, CameraConfig, ROIConfig
from event_database import AlgorithmEvent, EventDatabaseWriter, EventLevel

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CaptureService:
    """
    捕获服务
    整合摄像头捕获和算法推理，实现从视频帧到事件流的完整 pipeline
    """
    
    def __init__(self, 
                 camera_id: str,
                 device_serial: str,
                 channel_no: int = 1,
                 capture_source: Optional[str] = None,
                 db_writer: Optional[EventDatabaseWriter] = None):
        """
        初始化捕获服务
        
        Args:
            camera_id: 摄像头唯一ID
            device_serial: 设备序列号
            channel_no: 通道号
            capture_source: 视频源（文件路径、URL或None使用API捕获）
            db_writer: 数据库写入器
        """
        self.camera_id = camera_id
        self.device_serial = device_serial
        self.channel_no = channel_no
        self.capture_source = capture_source
        
        # 加载配置
        self.config = get_config().get_camera_config(camera_id)
        if self.config is None:
            logger.warning(f"⚠️ 未找到摄像头配置: {camera_id}，使用默认配置")
            self.config = CameraConfig(
                camera_id=camera_id,
                device_serial=device_serial,
                channel_no=channel_no
            )
        
        # 初始化检测器
        self.detector = ColdStartDetector()
        self.stream_generator = EventStreamGenerator(self.detector)
        
        # 设置ROI区域
        self._setup_roi_regions()
        
        # 数据库写入器
        self.db_writer = db_writer or EventDatabaseWriter()
        
        # 运行状态
        self.is_running = False
        self.capture_thread = None
        self.frame_queue = queue.Queue(maxsize=10)
        self.last_frame = None
        self.last_process_time = 0
        
        # 性能统计
        self.stats = {
            'frames_processed': 0,
            'events_generated': 0,
            'avg_process_time': 0.0,
            'start_time': None
        }
        
        # 回调函数
        self.on_event: Optional[Callable[[AlgorithmEvent], None]] = None
        self.on_frame: Optional[Callable[[np.ndarray, Dict], None]] = None
        
        logger.info(f"✅ 捕获服务初始化完成: {camera_id}")
    
    def _setup_roi_regions(self):
        """设置ROI区域"""
        for roi in self.config.roi_regions:
            if roi.roi_type == 'feeding':
                self.detector.feeding_roi = (roi.x, roi.y, roi.width, roi.height)
                logger.info(f"   食槽ROI: {roi.x}, {roi.y}, {roi.width}, {roi.height}")
            elif roi.roi_type == 'water':
                self.detector.water_roi = (roi.x, roi.y, roi.width, roi.height)
                logger.info(f"   水盆ROI: {roi.x}, {roi.y}, {roi.width}, {roi.height}")
    
    def start(self):
        """启动捕获服务"""
        if self.is_running:
            logger.warning("⚠️ 服务已在运行中")
            return
        
        self.is_running = True
        self.stats['start_time'] = datetime.now()
        
        # 启动捕获线程
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        
        logger.info(f"✅ 捕获服务已启动: {self.camera_id}")
    
    def stop(self):
        """停止捕获服务"""
        self.is_running = False
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=5.0)
        
        logger.info(f"⏹️ 捕获服务已停止: {self.camera_id}")
        self._print_stats()
    
    def _capture_loop(self):
        """捕获循环（在独立线程中运行）"""
        frame_interval = get_config().global_settings.get('frame_interval', 1.0)
        
        if self.capture_source:
            # 从视频文件或流捕获
            cap = cv2.VideoCapture(self.capture_source)
            if not cap.isOpened():
                logger.error(f"❌ 无法打开视频源: {self.capture_source}")
                self.is_running = False
                return
            
            logger.info(f"📹 从视频源捕获: {self.capture_source}")
            
            while self.is_running:
                ret, frame = cap.read()
                if not ret:
                    logger.warning("⚠️ 视频读取结束或失败")
                    break
                
                self._process_frame(frame)
                time.sleep(frame_interval)
            
            cap.release()
        else:
            # 从API捕获（模拟模式）
            logger.info("📷 使用API捕获模式（模拟）")
            while self.is_running:
                frame = self._capture_from_api()
                if frame is not None:
                    self._process_frame(frame)
                time.sleep(frame_interval)
    
    def _capture_from_api(self) -> Optional[np.ndarray]:
        """从海康API捕获图像"""
        # TODO: 实现实际的API调用
        # 目前返回模拟帧用于测试
        return self._create_test_frame()
    
    def _create_test_frame(self) -> np.ndarray:
        """创建测试帧（用于开发和测试）"""
        # 创建空白帧
        frame = np.ones((720, 1280, 3), dtype=np.uint8) * 100
        
        # 添加一些随机"动物"
        import random
        for i in range(random.randint(1, 3)):
            x = random.randint(200, 1000)
            y = random.randint(100, 500)
            cv2.ellipse(frame, (x, y), (40, 60), 0, 0, 360, (80, 100, 120), -1)
        
        # 绘制ROI区域
        if self.config.roi_regions:
            for roi in self.config.roi_regions:
                color = (0, 255, 0) if roi.roi_type == 'feeding' else (255, 0, 0)
                cv2.rectangle(frame, (roi.x, roi.y), 
                            (roi.x + roi.width, roi.y + roi.height), color, 2)
        
        return frame
    
    def _process_frame(self, frame: np.ndarray):
        """处理单帧"""
        start_time = time.time()
        
        try:
            # 使用冷启动检测器处理
            result = self.detector.process_frame(frame)
            
            # 转换事件并写入数据库
            events = self._convert_events(result.get('events', []))
            
            for event in events:
                # 写入数据库
                success = self.db_writer.write_event(event)
                if success:
                    self.stats['events_generated'] += 1
                
                # 触发回调
                if self.on_event:
                    self.on_event(event)
            
            # 写入检测记录
            self._write_detection_record(result)
            
            # 更新统计
            self.stats['frames_processed'] += 1
            process_time = time.time() - start_time
            self._update_avg_process_time(process_time)
            
            # 触发帧回调
            if self.on_frame:
                self.on_frame(frame, result)
            
            self.last_frame = frame
            self.last_process_time = process_time
            
        except Exception as e:
            logger.error(f"❌ 处理帧失败: {e}")
    
    def _convert_events(self, raw_events: List[Dict]) -> List[AlgorithmEvent]:
        """将原始事件转换为AlgorithmEvent"""
        events = []
        
        for raw_event in raw_events:
            try:
                event = AlgorithmEvent(
                    event_id=str(uuid.uuid4()),
                    event_type=raw_event.get('event_type', 'unknown'),
                    camera_id=self.camera_id,
                    device_serial=self.device_serial,
                    channel_no=self.channel_no,
                    timestamp=datetime.now(),
                    confidence=raw_event.get('confidence', 0.0),
                    level=self._get_event_level(raw_event.get('event_type')),
                    bbox_x1=raw_event.get('bbox', {}).get('x1'),
                    bbox_y1=raw_event.get('bbox', {}).get('y1'),
                    bbox_x2=raw_event.get('bbox', {}).get('x2'),
                    bbox_y2=raw_event.get('bbox', {}).get('y2'),
                    metadata=raw_event.get('metadata'),
                    image_url=None  # TODO: 保存图片后更新
                )
                events.append(event)
            except Exception as e:
                logger.error(f"❌ 转换事件失败: {e}")
        
        return events
    
    def _get_event_level(self, event_type: str) -> str:
        """获取事件级别"""
        level_map = {
            'movement': 'info',
            'eating': 'info',
            'drinking': 'info',
            'resting': 'info',
            'interaction': 'info',
            'alert': 'warning'
        }
        return level_map.get(event_type, 'info')
    
    def _write_detection_record(self, result: Dict):
        """写入检测记录"""
        try:
            # 确定活动级别
            movement_score = result.get('movement_score', 0)
            if movement_score < 5:
                activity_level = 'idle'
            elif movement_score < 20:
                activity_level = 'low'
            elif movement_score < 50:
                activity_level = 'medium'
            else:
                activity_level = 'high'
            
            self.db_writer.write_detection_record(
                camera_id=self.camera_id,
                device_serial=self.device_serial,
                channel_no=self.channel_no,
                timestamp=datetime.now(),
                animal_count=result.get('animal_count', 0),
                activity_score=movement_score,
                activity_level=activity_level,
                bounding_boxes=result.get('detections', []),
                metadata={
                    'events_count': len(result.get('events', [])),
                    'process_time_ms': self.last_process_time * 1000
                }
            )
        except Exception as e:
            logger.error(f"❌ 写入检测记录失败: {e}")
    
    def _update_avg_process_time(self, process_time: float):
        """更新平均处理时间"""
        n = self.stats['frames_processed']
        if n == 1:
            self.stats['avg_process_time'] = process_time
        else:
            self.stats['avg_process_time'] = (
                self.stats['avg_process_time'] * (n - 1) + process_time
            ) / n
    
    def _print_stats(self):
        """打印统计信息"""
        if self.stats['start_time']:
            duration = (datetime.now() - self.stats['start_time']).total_seconds()
            fps = self.stats['frames_processed'] / duration if duration > 0 else 0
            
            logger.info("=" * 50)
            logger.info(f"📊 捕获服务统计: {self.camera_id}")
            logger.info(f"   运行时间: {duration:.1f} 秒")
            logger.info(f"   处理帧数: {self.stats['frames_processed']}")
            logger.info(f"   生成事件: {self.stats['events_generated']}")
            logger.info(f"   平均FPS: {fps:.2f}")
            logger.info(f"   平均处理时间: {self.stats['avg_process_time'] * 1000:.1f} ms")
            logger.info("=" * 50)
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'camera_id': self.camera_id,
            'is_running': self.is_running,
            **self.stats
        }
    
    def process_single_frame(self, frame: np.ndarray) -> Dict:
        """
        处理单帧（用于测试和调试）
        
        Args:
            frame: 输入帧
            
        Returns:
            Dict: 处理结果
        """
        return self.detector.process_frame(frame)


class MultiCameraCaptureService:
    """多摄像头捕获服务管理器"""
    
    def __init__(self):
        self.services: Dict[str, CaptureService] = {}
        self.db_writer = EventDatabaseWriter()
    
    def add_camera(self, 
                   camera_id: str,
                   device_serial: str,
                   channel_no: int = 1,
                   capture_source: Optional[str] = None) -> CaptureService:
        """添加摄像头"""
        service = CaptureService(
            camera_id=camera_id,
            device_serial=device_serial,
            channel_no=channel_no,
            capture_source=capture_source,
            db_writer=self.db_writer
        )
        self.services[camera_id] = service
        return service
    
    def remove_camera(self, camera_id: str):
        """移除摄像头"""
        if camera_id in self.services:
            self.services[camera_id].stop()
            del self.services[camera_id]
    
    def start_all(self):
        """启动所有摄像头"""
        for service in self.services.values():
            service.start()
    
    def stop_all(self):
        """停止所有摄像头"""
        for service in self.services.values():
            service.stop()
    
    def get_service(self, camera_id: str) -> Optional[CaptureService]:
        """获取指定摄像头的服务"""
        return self.services.get(camera_id)
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """获取所有摄像头的统计信息"""
        return {cid: svc.get_stats() for cid, svc in self.services.items()}
