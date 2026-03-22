#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
算法 Pipeline 数据库模型 - 事件流、小时统计、日报、诊疗记录、饲养记录

表结构:
1. events - 原子事件表（秒级事件入库）
2. event_hourly_stats - 小时统计表
3. daily_reports - 日报表
4. medical_records_v2 - 诊疗记录表（新版）
5. care_records - 饲养记录表
"""

from datetime import datetime
from enum import Enum as PyEnum
from models_v2 import db


# ==================== 枚举定义 ====================

class EventType(PyEnum):
    """事件类型"""
    MOVEMENT = 'movement'       # 移动
    EATING = 'eating'           # 进食
    DRINKING = 'drinking'       # 饮水
    RESTING = 'resting'         # 休息
    ALERT = 'alert'             # 告警

class HealthStatus(PyEnum):
    """健康状态"""
    GREEN = 0   # 正常（绿）
    YELLOW = 1  # 关注（黄）
    RED = 2     # 告警（红）

class ActivityLevel(PyEnum):
    """活动水平"""
    LOW = '偏低'
    NORMAL = '正常'
    HIGH = '偏高'

class EatingStatus(PyEnum):
    """进食状态"""
    SLOW = '慢食'
    NORMAL = '正常'
    FAST = '快食'
    NOT_EATING = '未进食'

class DrinkingStatus(PyEnum):
    """饮水状态"""
    LOW = '偏少'
    NORMAL = '正常'
    HIGH = '偏多'

class MedicalStatus(PyEnum):
    """诊疗状态"""
    ONGOING = 'ongoing'         # 治疗中
    RESOLVED = 'resolved'       # 已康复
    CHRONIC = 'chronic'         # 慢性病管理

class CareRecordType(PyEnum):
    """饲养记录类型"""
    OBSERVATION = 'observation'     # 观察记录
    TASK = 'task'                   # 任务
    MEASUREMENT = 'measurement'     # 测量
    PHOTO = 'photo'                 # 拍照记录

class CareRecordCategory(PyEnum):
    """饲养记录分类"""
    FECES = '粪便'
    TEMPERATURE = '体温'
    HOOF = '蹄部'
    MEDICATION = '用药'
    FEEDING = '喂食'
    OTHER = '其他'

class CareRecordStatus(PyEnum):
    """饲养记录状态"""
    PENDING = 'pending'         # 待办
    COMPLETED = 'completed'     # 已完成
    CANCELLED = 'cancelled'     # 已取消

class Priority(PyEnum):
    """优先级"""
    NORMAL = 0      # 普通
    HIGH = 1        # 优先
    URGENT = 2      # 紧急


# ==================== 1. 原子事件表 ====================

class Event(db.Model):
    """原子事件表 - 算法秒级输出"""
    __tablename__ = 'events'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    enclosure_id = db.Column(db.Integer, db.ForeignKey('enclosures.id'), nullable=False, index=True)
    animal_id = db.Column(db.String(32), index=True, comment='动物耳标号（个体识别后）')
    camera_id = db.Column(db.String(64), comment='摄像头ID')
    channel_no = db.Column(db.Integer, comment='通道号')
    
    # 事件类型和置信度
    event_type = db.Column(db.Enum(EventType), nullable=False, comment='事件类型')
    confidence = db.Column(db.Float, comment='置信度 0-1')
    
    # 位置信息（边界框）
    bbox_x1 = db.Column(db.Float)
    bbox_y1 = db.Column(db.Float)
    bbox_x2 = db.Column(db.Float)
    bbox_y2 = db.Column(db.Float)
    
    # 元数据 (使用 event_metadata 避免与 SQLAlchemy 保留字冲突)
    event_metadata = db.Column('metadata', db.JSON, default=dict, comment='事件元数据: overlap_ratio, movement_score等')
    
    # 时间
    event_time = db.Column(db.DateTime(3), nullable=False, index=True, comment='事件发生时间（毫秒精度）')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 索引
    __table_args__ = (
        db.Index('idx_client_time', 'client_id', 'event_time'),
        db.Index('idx_enclosure_time', 'enclosure_id', 'event_time'),
        db.Index('idx_event_type_time', 'event_type', 'event_time'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'clientId': self.client_id,
            'enclosureId': self.enclosure_id,
            'animalId': self.animal_id,
            'cameraId': self.camera_id,
            'channelNo': self.channel_no,
            'eventType': self.event_type.value if self.event_type else None,
            'confidence': self.confidence,
            'bbox': [self.bbox_x1, self.bbox_y1, self.bbox_x2, self.bbox_y2] if self.bbox_x1 else None,
            'metadata': self.event_metadata,
            'eventTime': self.event_time.isoformat() if self.event_time else None,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }


# ==================== 2. 小时统计表 ====================

class EventHourlyStats(db.Model):
    """小时级事件统计"""
    __tablename__ = 'event_hourly_stats'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    enclosure_id = db.Column(db.Integer, db.ForeignKey('enclosures.id'), nullable=False)
    animal_id = db.Column(db.String(32), index=True, comment='耳标号，为空表示群体统计')
    
    # 统计时间
    stat_date = db.Column(db.Date, nullable=False, comment='统计日期')
    hour = db.Column(db.SmallInteger, nullable=False, comment='小时 0-23')
    
    # 活动统计
    movement_count = db.Column(db.Integer, default=0, comment='移动次数')
    movement_duration = db.Column(db.Integer, default=0, comment='移动总时长(秒)')
    avg_movement_score = db.Column(db.Float, comment='平均运动强度')
    
    # 进食统计
    eating_count = db.Column(db.Integer, default=0, comment='进食次数')
    eating_duration = db.Column(db.Integer, default=0, comment='进食时长(秒)')
    feed_consumption_percent = db.Column(db.Float, comment='饲料消耗百分比估算')
    
    # 饮水统计
    drinking_count = db.Column(db.Integer, default=0, comment='饮水次数')
    drinking_duration = db.Column(db.Integer, default=0, comment='饮水时长(秒)')
    water_consumption_liters = db.Column(db.Float, comment='饮水量估算')
    
    # 休息统计
    resting_duration = db.Column(db.Integer, default=0, comment='休息时长(秒)')
    
    # 异常统计
    alert_count = db.Column(db.Integer, default=0, comment='告警次数')
    alert_types = db.Column(db.JSON, default=list, comment='告警类型列表')
    
    # 综合评分
    activity_score = db.Column(db.Integer, comment='活动评分 0-100')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 唯一索引和查询索引
    __table_args__ = (
        db.UniqueConstraint('enclosure_id', 'animal_id', 'stat_date', 'hour', name='uk_enclosure_animal_hour'),
        db.Index('idx_stat_date_hour', 'stat_date', 'hour'),
        db.Index('idx_animal_date', 'animal_id', 'stat_date'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'clientId': self.client_id,
            'enclosureId': self.enclosure_id,
            'animalId': self.animal_id,
            'statDate': self.stat_date.isoformat() if self.stat_date else None,
            'hour': self.hour,
            'movement': {
                'count': self.movement_count,
                'duration': self.movement_duration,
                'avgScore': self.avg_movement_score
            },
            'eating': {
                'count': self.eating_count,
                'duration': self.eating_duration,
                'feedConsumption': self.feed_consumption_percent
            },
            'drinking': {
                'count': self.drinking_count,
                'duration': self.drinking_duration,
                'waterConsumption': self.water_consumption_liters
            },
            'resting': {
                'duration': self.resting_duration
            },
            'alerts': {
                'count': self.alert_count,
                'types': self.alert_types
            },
            'activityScore': self.activity_score,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }


# ==================== 3. 日报表 ====================

class DailyReport(db.Model):
    """动物健康日报"""
    __tablename__ = 'daily_reports'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    enclosure_id = db.Column(db.Integer, db.ForeignKey('enclosures.id'), nullable=False)
    animal_id = db.Column(db.String(32), nullable=False, index=True, comment='耳标号如 LS-B2-025')
    report_date = db.Column(db.Date, nullable=False, comment='报告日期')
    
    # 基础信息（快照）
    ear_tag = db.Column(db.String(32), comment='耳标号')
    gender = db.Column(db.String(8), comment='雌/雄')
    age = db.Column(db.String(16), comment='年龄如 1岁')
    health_status = db.Column(db.SmallInteger, default=0, comment='0:绿 1:黄 2:红')
    
    # 活动数据
    activity_score = db.Column(db.Integer, comment='活动评分如 82分')
    activity_level = db.Column(db.String(16), comment='正常/偏低/偏高')
    activity_trend = db.Column(db.JSON, default=list, comment='7天趋势 [78,82,75,80,82,79,82]')
    
    # 进食数据
    feed_main_remain_percent = db.Column(db.Float, comment='主槽剩余%如 35')
    feed_aux_remain_percent = db.Column(db.Float, comment='辅槽剩余%如 72')
    eating_status = db.Column(db.String(32), comment='慢食/正常/快食/未进食')
    
    # 饮水数据
    water_consumption_liters = db.Column(db.Float, comment='饮水量如 6.8L')
    drinking_status = db.Column(db.String(32), comment='偏多/正常/偏少')
    
    # 告警摘要
    alerts_summary = db.Column(db.JSON, default=list, comment='[{type,message,level,time}]')
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 唯一索引和查询索引
    __table_args__ = (
        db.UniqueConstraint('animal_id', 'report_date', name='uk_animal_date'),
        db.Index('idx_enclosure_date', 'enclosure_id', 'report_date'),
        db.Index('idx_report_date', 'report_date'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'clientId': self.client_id,
            'enclosureId': self.enclosure_id,
            'animalId': self.animal_id,
            'reportDate': self.report_date.isoformat() if self.report_date else None,
            'basic': {
                'earTag': self.ear_tag,
                'gender': self.gender,
                'age': self.age,
                'healthStatus': self.health_status
            },
            'activity': {
                'score': self.activity_score,
                'level': self.activity_level,
                'trend': self.activity_trend
            },
            'eating': {
                'feedMainRemain': self.feed_main_remain_percent,
                'feedAuxRemain': self.feed_aux_remain_percent,
                'status': self.eating_status
            },
            'drinking': {
                'consumptionLiters': self.water_consumption_liters,
                'status': self.drinking_status
            },
            'alerts': self.alerts_summary,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }


# ==================== 4. 诊疗记录表 (V2) ====================

class MedicalRecordV2(db.Model):
    """诊疗记录 - 新版（基于算法开发计划V2）"""
    __tablename__ = 'medical_records_v2'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    animal_id = db.Column(db.String(32), nullable=False, index=True, comment='耳标号')
    
    # 诊断信息
    diagnosis = db.Column(db.String(128), comment='诊断如 肠炎')
    diagnosis_date = db.Column(db.Date, comment='诊断日期')
    status = db.Column(db.Enum(MedicalStatus), default=MedicalStatus.ONGOING, comment='ongoing/resolved/chronic')
    
    # 用药方案
    medications = db.Column(db.JSON, default=list, comment='用药方案: [{name,dosage,route,remain_days}]')
    treatment_day = db.Column(db.Integer, default=1, comment='治疗第几天')
    
    # 兽医和备注
    veterinarian = db.Column(db.String(64), comment='兽医')
    notes = db.Column(db.Text)
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 索引
    __table_args__ = (
        db.Index('idx_status_date', 'status', 'diagnosis_date'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'clientId': self.client_id,
            'animalId': self.animal_id,
            'diagnosis': self.diagnosis,
            'diagnosisDate': self.diagnosis_date.isoformat() if self.diagnosis_date else None,
            'status': self.status.value if self.status else None,
            'medications': self.medications,
            'treatmentDay': self.treatment_day,
            'veterinarian': self.veterinarian,
            'notes': self.notes,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }


# ==================== 5. 饲养记录表 ====================

class CareRecord(db.Model):
    """饲养记录"""
    __tablename__ = 'care_records'
    
    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    enclosure_id = db.Column(db.Integer, db.ForeignKey('enclosures.id'), nullable=True)
    animal_id = db.Column(db.String(32), index=True)
    
    # 记录类型和分类
    record_type = db.Column(db.Enum(CareRecordType), nullable=False, comment='observation/task/measurement/photo')
    category = db.Column(db.Enum(CareRecordCategory), comment='粪便/体温/蹄部/用药/喂食')
    
    # 记录内容
    content = db.Column(db.Text, comment='记录内容')
    status = db.Column(db.Enum(CareRecordStatus), default=CareRecordStatus.COMPLETED, comment='pending/completed/cancelled')
    priority = db.Column(db.SmallInteger, default=0, comment='0:普通 1:优先 2:紧急')
    
    # 多媒体
    voice_url = db.Column(db.String(512), comment='语音URL')
    images = db.Column(db.JSON, default=list, comment='图片URL列表')
    
    # 执行人
    operator_id = db.Column(db.BigInteger, comment='执行人ID')
    operator_name = db.Column(db.String(64), comment='执行人姓名')
    
    # 时间
    scheduled_date = db.Column(db.Date, comment='计划日期（待办用）')
    completed_at = db.Column(db.DateTime, comment='完成时间')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 索引
    __table_args__ = (
        db.Index('idx_animal_created', 'animal_id', 'created_at'),
        db.Index('idx_scheduled_status', 'scheduled_date', 'status'),
        db.Index('idx_record_type', 'record_type', 'created_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'clientId': self.client_id,
            'enclosureId': self.enclosure_id,
            'animalId': self.animal_id,
            'recordType': self.record_type.value if self.record_type else None,
            'category': self.category.value if self.category else None,
            'content': self.content,
            'status': self.status.value if self.status else None,
            'priority': self.priority,
            'voiceUrl': self.voice_url,
            'images': self.images,
            'operator': {
                'id': self.operator_id,
                'name': self.operator_name
            },
            'scheduledDate': self.scheduled_date.isoformat() if self.scheduled_date else None,
            'completedAt': self.completed_at.isoformat() if self.completed_at else None,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }


# ==================== 辅助函数 ====================

def init_algorithm_models(app):
    """初始化算法模型表"""
    with app.app_context():
        db.create_all()
        print("✅ 算法 Pipeline 数据库表已创建")


def get_hourly_stats_summary(enclosure_id: int, stat_date, hour: int = None):
    """获取小时统计摘要"""
    query = EventHourlyStats.query.filter_by(
        enclosure_id=enclosure_id,
        stat_date=stat_date
    )
    if hour is not None:
        query = query.filter_by(hour=hour)
    
    stats = query.all()
    if not stats:
        return None
    
    # 聚合所有动物的数据
    total_movement = sum(s.movement_duration for s in stats)
    total_eating = sum(s.eating_duration for s in stats)
    total_drinking = sum(s.drinking_duration for s in stats)
    avg_activity = sum(s.activity_score or 0 for s in stats) / len(stats) if stats else 0
    
    return {
        'enclosureId': enclosure_id,
        'statDate': stat_date.isoformat() if stat_date else None,
        'hour': hour,
        'animalCount': len(stats),
        'totalMovementDuration': total_movement,
        'totalEatingDuration': total_eating,
        'totalDrinkingDuration': total_drinking,
        'avgActivityScore': round(avg_activity, 1)
    }
