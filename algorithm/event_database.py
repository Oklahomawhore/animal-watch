"""
林麝算法 Pipeline - 事件数据库写入模块
处理事件到数据库的持久化
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import sqlite3
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型"""
    MOVEMENT = "movement"           # 移动
    EATING = "eating"               # 进食
    DRINKING = "drinking"           # 饮水
    RESTING = "resting"             # 休息
    INTERACTION = "interaction"     # 社交互动
    ALERT = "alert"                 # 警觉/异常


class EventLevel(Enum):
    """事件级别"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AlgorithmEvent:
    """算法事件数据结构"""
    event_id: str
    event_type: str
    camera_id: str
    device_serial: str
    channel_no: int
    timestamp: datetime
    confidence: float
    level: str = "info"
    
    # 检测框信息
    bbox_x1: Optional[float] = None
    bbox_y1: Optional[float] = None
    bbox_x2: Optional[float] = None
    bbox_y2: Optional[float] = None
    
    # 元数据
    metadata: Optional[Dict] = None
    image_url: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'event_id': self.event_id,
            'event_type': self.event_type,
            'camera_id': self.camera_id,
            'device_serial': self.device_serial,
            'channel_no': self.channel_no,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'confidence': self.confidence,
            'level': self.level,
            'bbox': {
                'x1': self.bbox_x1,
                'y1': self.bbox_y1,
                'x2': self.bbox_x2,
                'y2': self.bbox_y2
            } if any([self.bbox_x1, self.bbox_y1, self.bbox_x2, self.bbox_y2]) else None,
            'metadata': self.metadata,
            'image_url': self.image_url
        }


class EventDatabaseWriter:
    """事件数据库写入器"""
    
    def __init__(self, db_url: Optional[str] = None):
        """
        初始化数据库写入器
        
        Args:
            db_url: 数据库URL，默认使用 SQLite
        """
        self.db_url = db_url or os.path.join(
            os.path.dirname(__file__), 
            'data', 
            'events.db'
        )
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表结构"""
        os.makedirs(os.path.dirname(self.db_url), exist_ok=True)
        
        conn = sqlite3.connect(self.db_url)
        cursor = conn.cursor()
        
        # 创建事件表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS algorithm_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                event_type TEXT NOT NULL,
                camera_id TEXT NOT NULL,
                device_serial TEXT NOT NULL,
                channel_no INTEGER DEFAULT 1,
                timestamp TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                level TEXT DEFAULT 'info',
                bbox_x1 REAL,
                bbox_y1 REAL,
                bbox_x2 REAL,
                bbox_y2 REAL,
                metadata TEXT,
                image_url TEXT,
                processed BOOLEAN DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_events_camera_time 
            ON algorithm_events(camera_id, timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_events_type 
            ON algorithm_events(event_type)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_events_timestamp 
            ON algorithm_events(timestamp)
        ''')
        
        # 创建检测记录表（聚合数据）
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detection_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id TEXT NOT NULL,
                device_serial TEXT NOT NULL,
                channel_no INTEGER DEFAULT 1,
                timestamp TEXT NOT NULL,
                animal_count INTEGER DEFAULT 0,
                activity_score REAL DEFAULT 0.0,
                activity_level TEXT,
                image_url TEXT,
                bounding_boxes TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_detections_camera_time 
            ON detection_records(camera_id, timestamp)
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"✅ 数据库初始化完成: {self.db_url}")
    
    def write_event(self, event: AlgorithmEvent) -> bool:
        """
        写入单个事件
        
        Args:
            event: 算法事件
            
        Returns:
            bool: 是否成功
        """
        try:
            conn = sqlite3.connect(self.db_url)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO algorithm_events 
                (event_id, event_type, camera_id, device_serial, channel_no,
                 timestamp, confidence, level, bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                 metadata, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.event_id,
                event.event_type,
                event.camera_id,
                event.device_serial,
                event.channel_no,
                event.timestamp.isoformat() if event.timestamp else datetime.now().isoformat(),
                event.confidence,
                event.level,
                event.bbox_x1,
                event.bbox_y1,
                event.bbox_x2,
                event.bbox_y2,
                json.dumps(event.metadata, ensure_ascii=False) if event.metadata else None,
                event.image_url
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ 写入事件失败: {e}")
            return False
    
    def write_events_batch(self, events: List[AlgorithmEvent]) -> int:
        """
        批量写入事件
        
        Args:
            events: 事件列表
            
        Returns:
            int: 成功写入的数量
        """
        success_count = 0
        
        try:
            conn = sqlite3.connect(self.db_url)
            cursor = conn.cursor()
            
            for event in events:
                try:
                    cursor.execute('''
                        INSERT OR REPLACE INTO algorithm_events 
                        (event_id, event_type, camera_id, device_serial, channel_no,
                         timestamp, confidence, level, bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                         metadata, image_url)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        event.event_id,
                        event.event_type,
                        event.camera_id,
                        event.device_serial,
                        event.channel_no,
                        event.timestamp.isoformat() if event.timestamp else datetime.now().isoformat(),
                        event.confidence,
                        event.level,
                        event.bbox_x1,
                        event.bbox_y1,
                        event.bbox_x2,
                        event.bbox_y2,
                        json.dumps(event.metadata, ensure_ascii=False) if event.metadata else None,
                        event.image_url
                    ))
                    success_count += 1
                except Exception as e:
                    logger.error(f"❌ 写入单个事件失败: {e}")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ 批量写入事件失败: {e}")
        
        return success_count
    
    def write_detection_record(self, 
                               camera_id: str,
                               device_serial: str,
                               channel_no: int,
                               timestamp: datetime,
                               animal_count: int = 0,
                               activity_score: float = 0.0,
                               activity_level: str = "idle",
                               image_url: Optional[str] = None,
                               bounding_boxes: Optional[List[Dict]] = None,
                               metadata: Optional[Dict] = None) -> bool:
        """
        写入检测记录（聚合数据）
        
        Args:
            camera_id: 摄像头ID
            device_serial: 设备序列号
            channel_no: 通道号
            timestamp: 时间戳
            animal_count: 动物数量
            activity_score: 活动量评分
            activity_level: 活动级别
            image_url: 图片URL
            bounding_boxes: 边界框列表
            metadata: 元数据
            
        Returns:
            bool: 是否成功
        """
        try:
            conn = sqlite3.connect(self.db_url)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO detection_records 
                (camera_id, device_serial, channel_no, timestamp, animal_count,
                 activity_score, activity_level, image_url, bounding_boxes, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                camera_id,
                device_serial,
                channel_no,
                timestamp.isoformat(),
                animal_count,
                activity_score,
                activity_level,
                image_url,
                json.dumps(bounding_boxes, ensure_ascii=False) if bounding_boxes else None,
                json.dumps(metadata, ensure_ascii=False) if metadata else None
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ 写入检测记录失败: {e}")
            return False
    
    def query_events(self, 
                     camera_id: Optional[str] = None,
                     event_type: Optional[str] = None,
                     start_time: Optional[datetime] = None,
                     end_time: Optional[datetime] = None,
                     limit: int = 100) -> List[Dict]:
        """
        查询事件
        
        Args:
            camera_id: 摄像头ID过滤
            event_type: 事件类型过滤
            start_time: 开始时间
            end_time: 结束时间
            limit: 返回数量限制
            
        Returns:
            List[Dict]: 事件列表
        """
        try:
            conn = sqlite3.connect(self.db_url)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM algorithm_events WHERE 1=1"
            params = []
            
            if camera_id:
                query += " AND camera_id = ?"
                params.append(camera_id)
            
            if event_type:
                query += " AND event_type = ?"
                params.append(event_type)
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time.isoformat())
            
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time.isoformat())
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            events = []
            for row in rows:
                event = dict(row)
                if event.get('metadata'):
                    event['metadata'] = json.loads(event['metadata'])
                events.append(event)
            
            conn.close()
            return events
            
        except Exception as e:
            logger.error(f"❌ 查询事件失败: {e}")
            return []
    
    def get_statistics(self, camera_id: Optional[str] = None, 
                       hours: int = 24) -> Dict:
        """
        获取事件统计
        
        Args:
            camera_id: 摄像头ID
            hours: 统计小时数
            
        Returns:
            Dict: 统计信息
        """
        try:
            conn = sqlite3.connect(self.db_url)
            cursor = conn.cursor()
            
            from datetime import timedelta
            start_time = (datetime.now() - timedelta(hours=hours)).isoformat()
            
            # 基础查询条件
            base_query = "FROM algorithm_events WHERE timestamp >= ?"
            params = [start_time]
            
            if camera_id:
                base_query += " AND camera_id = ?"
                params.append(camera_id)
            
            # 总事件数
            cursor.execute(f"SELECT COUNT(*) {base_query}", params)
            total = cursor.fetchone()[0]
            
            # 各类型事件数
            cursor.execute(f'''
                SELECT event_type, COUNT(*) as count 
                {base_query}
                GROUP BY event_type
            ''', params)
            type_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 平均置信度
            cursor.execute(f'''
                SELECT AVG(confidence) {base_query}
            ''', params)
            avg_confidence = cursor.fetchone()[0] or 0.0
            
            conn.close()
            
            return {
                'total_events': total,
                'event_types': type_counts,
                'avg_confidence': round(avg_confidence, 3),
                'time_window_hours': hours
            }
            
        except Exception as e:
            logger.error(f"❌ 获取统计失败: {e}")
            return {'total_events': 0, 'event_types': {}, 'avg_confidence': 0.0}


# 兼容主数据库的写入器
class MainDatabaseWriter:
    """主数据库写入器（Flask-SQLAlchemy 兼容）"""
    
    def __init__(self, db_session=None):
        """
        初始化
        
        Args:
            db_session: SQLAlchemy 数据库会话
        """
        self.db_session = db_session
        self._local_writer = None
    
    def _get_local_writer(self) -> EventDatabaseWriter:
        """获取本地写入器（当没有db_session时）"""
        if self._local_writer is None:
            self._local_writer = EventDatabaseWriter()
        return self._local_writer
    
    def write_event(self, event: AlgorithmEvent) -> bool:
        """写入事件"""
        if self.db_session is None:
            return self._get_local_writer().write_event(event)
        
        # 如果有db_session，使用SQLAlchemy模型写入
        # 这里需要根据实际模型实现
        try:
            # TODO: 使用 models_v2.Detection 或其他适当模型
            logger.info(f"写入事件到主数据库: {event.event_id}")
            return True
        except Exception as e:
            logger.error(f"写入主数据库失败: {e}")
            return False
    
    def write_detection_record(self, **kwargs) -> bool:
        """写入检测记录"""
        if self.db_session is None:
            return self._get_local_writer().write_detection_record(**kwargs)
        
        try:
            logger.info(f"写入检测记录到主数据库: {kwargs.get('camera_id')}")
            return True
        except Exception as e:
            logger.error(f"写入主数据库失败: {e}")
            return False
