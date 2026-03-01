#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模型
"""

from datetime import datetime
from app import db


class Device(db.Model):
    """设备信息"""
    __tablename__ = 'devices'
    
    id = db.Column(db.Integer, primary_key=True)
    device_serial = db.Column(db.String(50), unique=True, nullable=False, index=True)
    device_name = db.Column(db.String(100))
    channel_no = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='offline')  # online/offline
    
    # 摄像头位置信息
    location_x = db.Column(db.Float)
    location_y = db.Column(db.Float)
    
    # 关联的食槽
    trough_id = db.Column(db.String(50))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    detections = db.relationship('Detection', backref='device', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'deviceSerial': self.device_serial,
            'deviceName': self.device_name,
            'channelNo': self.channel_no,
            'status': self.status,
            'location': {'x': self.location_x, 'y': self.location_y},
            'troughId': self.trough_id,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }


class Detection(db.Model):
    """检测结果记录"""
    __tablename__ = 'detections'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    
    # 检测时间
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # 动物信息
    animal_count = db.Column(db.Integer, default=0)
    
    # 活动量指标
    activity_score = db.Column(db.Float)  # 0-100
    activity_level = db.Column(db.String(20))  # idle/low/medium/high
    
    # 图片URL
    image_url = db.Column(db.String(500))
    
    # 边界框坐标 (JSON格式)
    bounding_boxes = db.Column(db.Text)
    
    # 草量覆盖率 (如果是食槽摄像头)
    grass_coverage = db.Column(db.Float)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        import json
        return {
            'id': self.id,
            'deviceId': self.device_id,
            'deviceSerial': self.device.device_serial if self.device else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'animalCount': self.animal_count,
            'activityScore': self.activity_score,
            'activityLevel': self.activity_level,
            'imageUrl': self.image_url,
            'boundingBoxes': json.loads(self.bounding_boxes) if self.bounding_boxes else [],
            'grassCoverage': self.grass_coverage
        }


class AlarmRecord(db.Model):
    """告警记录"""
    __tablename__ = 'alarm_records'
    
    id = db.Column(db.Integer, primary_key=True)
    device_serial = db.Column(db.String(50), nullable=False, index=True)
    
    # 告警类型
    alarm_type = db.Column(db.String(50))  # motion_detection, grass_low, etc.
    
    # 告警时间
    alarm_time = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 告警图片
    alarm_pic_url = db.Column(db.String(500))
    
    # 处理状态
    status = db.Column(db.String(20), default='unhandled')  # unhandled/handled/ignored
    
    # 备注
    remark = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'deviceSerial': self.device_serial,
            'alarmType': self.alarm_type,
            'alarmTime': self.alarm_time.isoformat() if self.alarm_time else None,
            'alarmPicUrl': self.alarm_pic_url,
            'status': self.status,
            'remark': self.remark
        }
