#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
帧抓取服务 (Capture Service)

功能：
1. 每1秒抓取所有摄像头帧
2. 调用算法引擎进行推理
3. 将原子事件入库
4. 实时告警检测

技术栈：
- asyncio: 异步并发处理
- aiohttp: 异步HTTP请求
- SQLAlchemy: 数据库操作
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import aiohttp

# 导入模型
from models_algorithm import Event, EventType
from models_v2 import db, Camera, CameraStatus

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CaptureService:
    """1秒间隔帧抓取服务"""
    
    def __init__(self, app=None, interval: float = 1.0):
        """
        初始化抓取服务
        
        Args:
            app: Flask应用实例
            interval: 抓取间隔（秒），默认1秒
        """
        self.app = app
        self.interval = interval
        self.running = False
        self.cameras: List[Dict] = []
        self.session: Optional[aiohttp.ClientSession] = None
        
        # 统计信息
        self.stats = {
            'total_frames': 0,
            'total_events': 0,
            'total_alerts': 0,
            'errors': 0,
            'start_time': None
        }
    
    async def start(self):
        """启动抓取服务"""
        if self.running:
            logger.warning("⚠️ 抓取服务已在运行")
            return
        
        self.running = True
        self.stats['start_time'] = datetime.utcnow()
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5))
        
        logger.info("🚀 帧抓取服务已启动")
        
        try:
            await self.capture_loop()
        except asyncio.CancelledError:
            logger.info("🛑 抓取服务已取消")
        except Exception as e:
            logger.error(f"❌ 抓取服务异常: {e}")
            self.stats['errors'] += 1
        finally:
            await self.stop()
    
    async def stop(self):
        """停止抓取服务"""
        self.running = False
        if self.session:
            await self.session.close()
            self.session = None
        logger.info("🛑 帧抓取服务已停止")
    
    async def capture_loop(self):
        """主抓取循环 - 精确1秒间隔"""
        while self.running:
            start_time = datetime.utcnow()
            
            try:
                # 刷新摄像头列表
                await self.refresh_cameras()
                
                if not self.cameras:
                    logger.debug("⚠️ 没有可用的摄像头")
                    await asyncio.sleep(self.interval)
                    continue
                
                # 并行处理所有摄像头
                tasks = [self.process_camera(cam) for cam in self.cameras]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 处理结果
                for cam, result in zip(self.cameras, results):
                    if isinstance(result, Exception):
                        logger.error(f"❌ 摄像头 {cam.get('camera_id')} 处理失败: {result}")
                        self.stats['errors'] += 1
                    else:
                        self.stats['total_frames'] += 1
                        if result.get('events'):
                            self.stats['total_events'] += len(result['events'])
                        if result.get('alerts'):
                            self.stats['total_alerts'] += len(result['alerts'])
                
            except Exception as e:
                logger.error(f"❌ 抓取循环异常: {e}")
                self.stats['errors'] += 1
            
            # 精确1秒间隔
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            sleep_time = max(0, self.interval - elapsed)
            
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
    
    async def refresh_cameras(self):
        """刷新摄像头列表"""
        if not self.app:
            return
        
        with self.app.app_context():
            # 查询在线且已绑定的摄像头
            cameras = Camera.query.filter_by(
                status=CameraStatus.ONLINE
            ).filter(
                Camera.enclosure_id.isnot(None)
            ).all()
            
            self.cameras = [
                {
                    'id': cam.id,
                    'camera_id': cam.camera_id if hasattr(cam, 'camera_id') else cam.device_serial,
                    'device_serial': cam.device_serial,
                    'client_id': cam.client_id,
                    'enclosure_id': cam.enclosure_id,
                    'platform_id': cam.platform_id,
                    'channel_no': cam.channel_no if hasattr(cam, 'channel_no') else 1,
                    'snapshot_url': cam.snapshot_url
                }
                for cam in cameras
            ]
    
    async def process_camera(self, camera: Dict) -> Dict:
        """
        处理单个摄像头帧
        
        Args:
            camera: 摄像头信息字典
            
        Returns:
            处理结果字典
        """
        result = {
            'camera_id': camera.get('camera_id'),
            'events': [],
            'alerts': [],
            'timestamp': datetime.utcnow().isoformat()
        }
        
        try:
            # 1. 抓取帧
            frame = await self.fetch_frame(camera)
            
            if frame is None:
                logger.warning(f"⚠️ 摄像头 {camera.get('camera_id')} 抓取帧失败")
                return result
            
            # 2. 算法推理（模拟，实际接入算法引擎）
            detection_result = await self.run_inference(camera, frame)
            
            # 3. 秒级事件入库
            events = detection_result.get('events', [])
            if events:
                await self.save_events(camera, events)
                result['events'] = events
            
            # 4. 实时告警检测
            alerts = self.check_alerts(detection_result, events)
            if alerts:
                await self.send_alerts(camera, alerts)
                result['alerts'] = alerts
            
        except Exception as e:
            logger.error(f"❌ 处理摄像头 {camera.get('camera_id')} 异常: {e}")
            raise
        
        return result
    
    async def fetch_frame(self, camera: Dict) -> Optional[bytes]:
        """
        抓取摄像头帧
        
        Args:
            camera: 摄像头信息
            
        Returns:
            帧数据（bytes）或 None
        """
        # 使用快照URL抓取帧
        snapshot_url = camera.get('snapshot_url')
        
        if not snapshot_url:
            # 如果没有快照URL，使用海康API获取
            snapshot_url = await self.get_hikvision_snapshot(camera)
        
        if not snapshot_url:
            return None
        
        try:
            async with self.session.get(snapshot_url) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logger.warning(f"⚠️ 获取快照失败: HTTP {response.status}")
                    return None
        except Exception as e:
            logger.error(f"❌ 抓取帧失败: {e}")
            return None
    
    async def get_hikvision_snapshot(self, camera: Dict) -> Optional[str]:
        """获取海康摄像头快照URL"""
        # TODO: 实现海康API获取快照URL
        # 这里需要调用海康API获取实时快照
        return None
    
    async def run_inference(self, camera: Dict, frame: bytes) -> Dict:
        """
        运行算法推理
        
        Args:
            camera: 摄像头信息
            frame: 帧数据
            
        Returns:
            推理结果
        """
        # TODO: 接入实际算法引擎
        # 这里模拟算法推理结果
        
        import random
        
        # 模拟检测结果
        events = []
        event_types = [EventType.MOVEMENT, EventType.EATING, EventType.DRINKING, EventType.RESTING]
        
        # 随机生成事件（实际应从算法引擎获取）
        if random.random() > 0.7:  # 30%概率产生事件
            event_type = random.choice(event_types)
            events.append({
                'event_type': event_type.value,
                'confidence': random.uniform(0.7, 0.99),
                'bbox': [random.uniform(0, 100), random.uniform(0, 100), 
                        random.uniform(100, 200), random.uniform(100, 200)],
                'metadata': {
                    'movement_score': random.uniform(0, 100) if event_type == EventType.MOVEMENT else None,
                    'overlap_ratio': random.uniform(0, 1)
                }
            })
        
        return {
            'events': events,
            'animal_count': random.randint(1, 3),
            'activity_score': random.uniform(0, 100)
        }
    
    async def save_events(self, camera: Dict, events: List[Dict]):
        """
        保存原子事件到数据库
        
        Args:
            camera: 摄像头信息
            events: 事件列表
        """
        if not self.app:
            return
        
        with self.app.app_context():
            for event_data in events:
                event = Event(
                    client_id=camera['client_id'],
                    enclosure_id=camera['enclosure_id'],
                    camera_id=camera.get('camera_id'),
                    channel_no=camera.get('channel_no'),
                    event_type=EventType(event_data['event_type']),
                    confidence=event_data.get('confidence'),
                    bbox_x1=event_data.get('bbox', [None, None, None, None])[0],
                    bbox_y1=event_data.get('bbox', [None, None, None, None])[1],
                    bbox_x2=event_data.get('bbox', [None, None, None, None])[2],
                    bbox_y2=event_data.get('bbox', [None, None, None, None])[3],
                    metadata=event_data.get('metadata', {}),
                    event_time=datetime.utcnow()
                )
                db.session.add(event)
            
            try:
                db.session.commit()
                logger.debug(f"✅ 保存 {len(events)} 个事件")
            except Exception as e:
                db.session.rollback()
                logger.error(f"❌ 保存事件失败: {e}")
                raise
    
    def check_alerts(self, detection_result: Dict, events: List[Dict]) -> List[Dict]:
        """
        检查告警条件
        
        Args:
            detection_result: 检测结果
            events: 事件列表
            
        Returns:
            告警列表
        """
        alerts = []
        
        # 检查活动异常（示例规则）
        activity_score = detection_result.get('activity_score', 0)
        if activity_score < 10:
            alerts.append({
                'type': 'low_activity',
                'level': 'warning',
                'message': '动物活动量异常偏低',
                'score': activity_score
            })
        
        # 检查动物数量异常
        animal_count = detection_result.get('animal_count', 0)
        if animal_count == 0:
            alerts.append({
                'type': 'no_animal',
                'level': 'critical',
                'message': '未检测到动物'
            })
        
        return alerts
    
    async def send_alerts(self, camera: Dict, alerts: List[Dict]):
        """
        发送告警通知
        
        Args:
            camera: 摄像头信息
            alerts: 告警列表
        """
        for alert in alerts:
            logger.warning(f"🚨 告警 [{alert['level'].upper()}] {camera.get('camera_id')}: {alert['message']}")
            # TODO: 实现实际告警通知（WebSocket、推送等）
    
    def get_stats(self) -> Dict:
        """获取服务统计信息"""
        uptime = None
        if self.stats['start_time']:
            uptime = (datetime.utcnow() - self.stats['start_time']).total_seconds()
        
        return {
            'running': self.running,
            'camera_count': len(self.cameras),
            'uptime_seconds': uptime,
            'total_frames': self.stats['total_frames'],
            'total_events': self.stats['total_events'],
            'total_alerts': self.stats['total_alerts'],
            'errors': self.stats['errors']
        }


# ==================== 服务管理 ====================

_capture_service: Optional[CaptureService] = None


def get_capture_service(app=None) -> CaptureService:
    """获取抓取服务实例（单例）"""
    global _capture_service
    if _capture_service is None:
        _capture_service = CaptureService(app)
    return _capture_service


async def start_capture_service(app):
    """启动抓取服务"""
    service = get_capture_service(app)
    await service.start()


async def stop_capture_service():
    """停止抓取服务"""
    global _capture_service
    if _capture_service:
        await _capture_service.stop()
        _capture_service = None


# ==================== 测试入口 ====================

if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    service = CaptureService()
    
    try:
        asyncio.run(service.start())
    except KeyboardInterrupt:
        print("\n收到中断信号，正在停止...")
        asyncio.run(service.stop())
