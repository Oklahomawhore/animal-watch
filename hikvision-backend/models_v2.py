#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库模型 V2 - 多租户RBAC + 多厂商 + 层级权限

架构:
  Client(客户) → Factory(厂) → Area(区域) → Enclosure(圈/个体)
  
权限:
  Admin: 全部权限(账号管理、授权、查看)
  FactoryManager: 除账号管理外的全部权限
  Breeder: 基础通知 + 被授权后可查看
  
可视范围:
  FactoryLevel → AreaLevel → EnclosureLevel
"""

from datetime import datetime
from enum import Enum as PyEnum
from flask_sqlalchemy import SQLAlchemy

# 创建 SQLAlchemy 实例 (延迟初始化)
db = SQLAlchemy()


# ==================== 枚举定义 ====================

class UserRole(PyEnum):
    """用户角色"""
    ADMIN = 'admin'           # 管理员：全部权限
    FACTORY_MANAGER = 'factory_manager'  # 厂长：除账号管理外的全部
    BREEDER = 'breeder'       # 饲养员：基础权限，需被授权

class UserStatus(PyEnum):
    """用户状态"""
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    SUSPENDED = 'suspended'

class VisibilityLevel(PyEnum):
    """可视范围级别"""
    FACTORY = 'factory'       # 厂级别
    AREA = 'area'             # 区域级别
    ENCLOSURE = 'enclosure'   # 圈级别

class CameraProvider(PyEnum):
    """摄像头厂商"""
    HIKVISION = 'hikvision'   # 海康威视
    DAHUA = 'dahua'           # 大华（预留）
    UNIVIEW = 'uniview'       # 宇视（预留）
    OTHER = 'other'           # 其他

class PlatformAuthStatus(PyEnum):
    """平台授权状态"""
    ACTIVE = 'active'
    EXPIRED = 'expired'
    REVOKED = 'revoked'

class CameraType(PyEnum):
    """摄像头类型"""
    ENCLOSURE = 'enclosure'   # 圈摄像头（监控林麝）
    FEEDING = 'feeding'       # 食槽摄像头（监控草量）
    ENVIRONMENT = 'environment'  # 环境摄像头

class CameraStatus(PyEnum):
    """摄像头状态"""
    ONLINE = 'online'
    OFFLINE = 'offline'
    ERROR = 'error'
    UNBOUND = 'unbound'       # 未绑定到圈


# ==================== 客户/租户 ====================

class Client(db.Model):
    """客户（租户）- 每个客户独立的数据空间"""
    __tablename__ = 'clients'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)           # 客户名称
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)  # 客户编码
    contact_name = db.Column(db.String(50))                     # 联系人
    contact_phone = db.Column(db.String(20))                    # 联系电话
    
    # 配置
    config = db.Column(db.JSON, default=dict)                   # 客户级配置（JSON）
    
    status = db.Column(db.Enum(UserStatus), default=UserStatus.ACTIVE)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    factories = db.relationship('Factory', backref='client', lazy=True)
    users = db.relationship('User', backref='client', lazy=True)
    platforms = db.relationship('CameraPlatform', backref='client', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'contactName': self.contact_name,
            'contactPhone': self.contact_phone,
            'status': self.status.value,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }


# ==================== 用户与权限 ====================

class User(db.Model):
    """系统用户 - 属于某个客户"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    
    # 基本信息
    username = db.Column(db.String(50), nullable=False, index=True)  # 登录名
    password_hash = db.Column(db.String(255), nullable=False)        # 密码
    nickname = db.Column(db.String(50))                              # 显示名
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    
    # 角色
    role = db.Column(db.Enum(UserRole), nullable=False)
    
    # 可视范围（用于厂长、饲养员）
    visibility_level = db.Column(db.Enum(VisibilityLevel), default=VisibilityLevel.FACTORY)
    visibility_scope_ids = db.Column(db.JSON, default=list)  # 可看的具体IDs [factory_id] 或 [area_id] 或 [enclosure_id]
    
    # 权限（额外细粒度权限，JSON格式）
    permissions = db.Column(db.JSON, default=dict)  # { 'can_view_analytics': True, 'can_receive_alerts': ['motion', 'grass'] }
    
    # 上次登录
    last_login_at = db.Column(db.DateTime)
    last_login_ip = db.Column(db.String(50))
    
    status = db.Column(db.Enum(UserStatus), default=UserStatus.ACTIVE)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # 谁创建的
    
    # 关联
    created_users = db.relationship('User', backref=db.backref('creator', remote_side=[id]))
    
    def to_dict(self):
        return {
            'id': self.id,
            'clientId': self.client_id,
            'username': self.username,
            'nickname': self.nickname,
            'phone': self.phone,
            'email': self.email,
            'role': self.role.value,
            'visibilityLevel': self.visibility_level.value if self.visibility_level else None,
            'visibilityScopeIds': self.visibility_scope_ids,
            'status': self.status.value,
            'lastLoginAt': self.last_login_at.isoformat() if self.last_login_at else None,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }
    
    def has_permission(self, permission_name):
        """检查是否有某权限"""
        if self.role == UserRole.ADMIN:
            return True
        return self.permissions.get(permission_name, False)


# ==================== 摄像头平台（多厂商支持）====================

class CameraPlatform(db.Model):
    """摄像头平台授权 - 支持多个平台、多个账号"""
    __tablename__ = 'camera_platforms'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    
    # 平台信息
    provider = db.Column(db.Enum(CameraProvider), nullable=False)
    name = db.Column(db.String(100))                    # 自定义名称（如"总部海康账号"）
    
    # 平台账号信息
    platform_account = db.Column(db.String(100))        # 平台登录账号
    platform_user_id = db.Column(db.String(100))        # 平台用户ID
    
    # 授权Token（加密存储）
    access_token = db.Column(db.Text)                   # 访问凭证
    refresh_token = db.Column(db.Text)                  # 刷新凭证
    token_expires_at = db.Column(db.DateTime)           # Token过期时间
    
    # OAuth相关
    auth_code = db.Column(db.String(255))               # 临时授权码
    auth_callback_url = db.Column(db.String(500))       # 回调URL
    
    # API配置（不同厂商配置不同）
    api_config = db.Column(db.JSON, default=dict)       # { 'appKey': 'xxx', 'appSecret': 'xxx', 'baseUrl': 'xxx' }
    
    # 授权人（哪个管理员授权的）
    authorized_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    authorized_at = db.Column(db.DateTime)
    
    status = db.Column(db.Enum(PlatformAuthStatus), default=PlatformAuthStatus.ACTIVE)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    cameras = db.relationship('Camera', backref='platform', lazy=True)
    authorizer = db.relationship('User', foreign_keys=[authorized_by])
    
    def to_dict(self):
        return {
            'id': self.id,
            'clientId': self.client_id,
            'provider': self.provider.value,
            'name': self.name,
            'platformAccount': self.platform_account,
            'status': self.status.value,
            'authorizedAt': self.authorized_at.isoformat() if self.authorized_at else None,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }


# ==================== 厂区-区域-圈 层级结构 ====================

class Factory(db.Model):
    """厂区/养殖场"""
    __tablename__ = 'factories'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    
    name = db.Column(db.String(100), nullable=False)    # 厂名
    code = db.Column(db.String(50), nullable=False)     # 厂编码
    address = db.Column(db.String(255))                 # 地址
    description = db.Column(db.Text)
    
    # 地理信息
    location_lat = db.Column(db.Float)                  # 纬度
    location_lng = db.Column(db.Float)                  # 经度
    
    status = db.Column(db.Enum(UserStatus), default=UserStatus.ACTIVE)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    areas = db.relationship('Area', backref='factory', lazy=True)
    
    __table_args__ = (
        db.UniqueConstraint('client_id', 'code', name='uix_factory_client_code'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'clientId': self.client_id,
            'name': self.name,
            'code': self.code,
            'address': self.address,
            'status': self.status.value,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }


class Area(db.Model):
    """区域（厂下面的分区）"""
    __tablename__ = 'areas'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    factory_id = db.Column(db.Integer, db.ForeignKey('factories.id'), nullable=False, index=True)
    
    name = db.Column(db.String(100), nullable=False)    # 区域名
    code = db.Column(db.String(50), nullable=False)     # 区域编码
    description = db.Column(db.Text)
    
    status = db.Column(db.Enum(UserStatus), default=UserStatus.ACTIVE)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联
    enclosures = db.relationship('Enclosure', backref='area', lazy=True)
    
    __table_args__ = (
        db.UniqueConstraint('factory_id', 'code', name='uix_area_factory_code'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'clientId': self.client_id,
            'factoryId': self.factory_id,
            'name': self.name,
            'code': self.code,
            'status': self.status.value,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }


class Enclosure(db.Model):
    """圈/个体 - 林麝的实际居住单元"""
    __tablename__ = 'enclosures'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    factory_id = db.Column(db.Integer, db.ForeignKey('factories.id'), nullable=False, index=True)
    area_id = db.Column(db.Integer, db.ForeignKey('areas.id'), nullable=False, index=True)
    
    name = db.Column(db.String(100), nullable=False)    # 圈名/个体名
    code = db.Column(db.String(50), nullable=False)     # 圈编码
    description = db.Column(db.Text)
    
    # 林麝信息
    animal_count = db.Column(db.Integer, default=0)     # 当前存栏数
    # animal_tags JSON格式示例:
    # [
    #   {
    #     "tag": "001",           # 耳标号
    #     "name": "小白",          # 昵称
    #     "gender": "female",      # 性别
    #     "birth_date": "2023-01-15",
    #     "status": "healthy",     # healthy/sick/quarantine/dead
    #     "status_note": "",
    #     "entry_date": "2023-03-01"  # 入圈日期
    #   }
    # ]
    animal_tags = db.Column(db.JSON, default=list)      # 个体标签列表
    
    # 位置信息
    location_x = db.Column(db.Float)                    # 平面图X坐标
    location_y = db.Column(db.Float)                    # 平面图Y坐标
    
    status = db.Column(db.Enum(UserStatus), default=UserStatus.ACTIVE)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    cameras = db.relationship('Camera', backref='enclosure', lazy=True)
    
    __table_args__ = (
        db.UniqueConstraint('area_id', 'code', name='uix_enclosure_area_code'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'clientId': self.client_id,
            'factoryId': self.factory_id,
            'areaId': self.area_id,
            'name': self.name,
            'code': self.code,
            'animalCount': self.animal_count,
            'animalTags': self.animal_tags,
            'status': self.status.value,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }


# ==================== 摄像头 ====================

class Camera(db.Model):
    """摄像头 - 属于平台，可绑定到圈
    
    命名冲突解决: 渠道名_账号名_摄像头名
    示例: hik_总部账号_圈A-01
    """
    __tablename__ = 'cameras'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    platform_id = db.Column(db.Integer, db.ForeignKey('camera_platforms.id'), nullable=False, index=True)
    enclosure_id = db.Column(db.Integer, db.ForeignKey('enclosures.id'), nullable=True, index=True)  # 可为空（未绑定）
    
    # 平台侧信息
    platform_device_id = db.Column(db.String(100), nullable=False)  # 平台设备ID
    device_serial = db.Column(db.String(50), nullable=False, index=True)  # 设备序列号
    channel_no = db.Column(db.Integer, default=1)
    
    # 唯一标识（解决多账号命名冲突）
    # 格式: {provider}_{platform_account}_{device_name}
    # 示例: hik_总部_圈A-01, hik_分部_圈A-01
    unique_name = db.Column(db.String(200), nullable=False, index=True)
    
    # 本地信息
    name = db.Column(db.String(100))                    # 摄像头名称（原始名称）
    camera_type = db.Column(db.Enum(CameraType), default=CameraType.ENCLOSURE)
    
    # 状态
    status = db.Column(db.Enum(CameraStatus), default=CameraStatus.UNBOUND)
    last_online_at = db.Column(db.DateTime)             # 最后在线时间
    
    # 图像信息（授权时抓取一帧）
    snapshot_url = db.Column(db.String(500))            # 快照URL
    snapshot_at = db.Column(db.DateTime)                # 快照时间
    
    # 位置（如果在圈上，相对于圈的位置；否则绝对位置）
    position_in_enclosure = db.Column(db.String(20))    # 圈内位置: 'front', 'back', 'left', 'right', 'top'
    
    # 导入标记
    is_auto_imported = db.Column(db.Boolean, default=False)  # 是否一键导入（名字匹配圈名）
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    detections = db.relationship('Detection', backref='camera', lazy=True)
    alarms = db.relationship('AlarmRecord', backref='camera', lazy=True)
    
    def generate_unique_name(self):
        """生成唯一名称"""
        platform = CameraPlatform.query.get(self.platform_id)
        provider = platform.provider.value if platform else 'unknown'
        account = platform.platform_account if platform else 'unknown'
        return f"{provider}_{account}_{self.name or self.device_serial}"
    
    def to_dict(self):
        return {
            'id': self.id,
            'clientId': self.client_id,
            'platformId': self.platform_id,
            'enclosureId': self.enclosure_id,
            'deviceSerial': self.device_serial,
            'uniqueName': self.unique_name,
            'name': self.name,
            'cameraType': self.camera_type.value if self.camera_type else None,
            'status': self.status.value if self.status else None,
            'snapshotUrl': self.snapshot_url,
            'isAutoImported': self.is_auto_imported,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }


# ==================== 检测与告警 ====================

class Detection(db.Model):
    """检测结果记录"""
    __tablename__ = 'detections'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    camera_id = db.Column(db.Integer, db.ForeignKey('cameras.id'), nullable=False, index=True)
    enclosure_id = db.Column(db.Integer, db.ForeignKey('enclosures.id'), nullable=False, index=True)
    
    # 检测时间
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    # 动物信息
    animal_count = db.Column(db.Integer, default=0)
    
    # 活动量指标
    activity_score = db.Column(db.Float)                # 0-100
    activity_level = db.Column(db.String(20))           # idle/low/medium/high
    
    # 图片URL
    image_url = db.Column(db.String(500))
    
    # 边界框坐标 (JSON格式)
    bounding_boxes = db.Column(db.Text)
    
    # 草量覆盖率 (食槽摄像头)
    grass_coverage = db.Column(db.Float)
    
    # AI分析结果
    ai_result = db.Column(db.JSON, default=dict)        # { 'model': 'yolo-v8', 'confidence': 0.95, ... }
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        import json
        return {
            'id': self.id,
            'clientId': self.client_id,
            'cameraId': self.camera_id,
            'enclosureId': self.enclosure_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'animalCount': self.animal_count,
            'activityScore': self.activity_score,
            'activityLevel': self.activity_level,
            'imageUrl': self.image_url,
            'boundingBoxes': json.loads(self.bounding_boxes) if self.bounding_boxes else [],
            'grassCoverage': self.grass_coverage,
            'aiResult': self.ai_result
        }


class AlarmRecord(db.Model):
    """告警记录"""
    __tablename__ = 'alarm_records'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    camera_id = db.Column(db.Integer, db.ForeignKey('cameras.id'), nullable=False, index=True)
    enclosure_id = db.Column(db.Integer, db.ForeignKey('enclosures.id'), nullable=False, index=True)
    
    # 告警类型
    alarm_type = db.Column(db.String(50))               # motion_detection, grass_low, offline, etc.
    alarm_level = db.Column(db.String(20), default='normal')  # normal/warning/critical
    
    # 告警时间
    alarm_time = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 告警图片
    alarm_pic_url = db.Column(db.String(500))
    
    # 处理状态
    status = db.Column(db.String(20), default='unhandled')  # unhandled/handled/ignored
    handled_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    handled_at = db.Column(db.DateTime)
    handle_remark = db.Column(db.Text)
    
    # 通知状态
    notification_sent = db.Column(db.Boolean, default=False)
    notification_time = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联
    handler = db.relationship('User', foreign_keys=[handled_by])
    
    def to_dict(self):
        return {
            'id': self.id,
            'clientId': self.client_id,
            'cameraId': self.camera_id,
            'enclosureId': self.enclosure_id,
            'alarmType': self.alarm_type,
            'alarmLevel': self.alarm_level,
            'alarmTime': self.alarm_time.isoformat() if self.alarm_time else None,
            'alarmPicUrl': self.alarm_pic_url,
            'status': self.status,
            'handledAt': self.handled_at.isoformat() if self.handled_at else None,
            'notificationSent': self.notification_sent
        }


# ==================== 诊疗随访记录 ====================

class MedicalRecordStatus(PyEnum):
    """诊疗记录状态"""
    ONGOING = 'ongoing'       # 治疗中
    RECOVERED = 'recovered'   # 已康复
    CHRONIC = 'chronic'       # 转为慢性病管理
    DECEASED = 'deceased'     # 死亡

class MedicalRecord(db.Model):
    """诊疗记录 - 个体林麝的诊疗随访"""
    __tablename__ = 'medical_records'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    enclosure_id = db.Column(db.Integer, db.ForeignKey('enclosures.id'), nullable=False, index=True)
    
    # 患病个体信息
    animal_tag = db.Column(db.String(50), nullable=False, index=True)  # 耳标号
    animal_name = db.Column(db.String(50))              # 昵称
    
    # 病情信息
    symptom = db.Column(db.Text, nullable=False)        # 症状描述
    diagnosis = db.Column(db.Text)                      # 诊断结果
    
    # 治疗信息
    treatment = db.Column(db.Text)                      # 治疗方案
    medications = db.Column(db.JSON, default=list)      # 用药记录 [{"name": "", "dose": "", "frequency": ""}]
    
    # 状态
    status = db.Column(db.Enum(MedicalRecordStatus), default=MedicalRecordStatus.ONGOING)
    
    # 时间
    onset_date = db.Column(db.DateTime)                 # 发病日期
    diagnosis_date = db.Column(db.DateTime)             # 确诊日期
    recovery_date = db.Column(db.DateTime)              # 康复日期
    
    # 记录人
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    enclosure = db.relationship('Enclosure', backref='medical_records')
    recorder = db.relationship('User', foreign_keys=[recorded_by])
    
    def to_dict(self):
        return {
            'id': self.id,
            'clientId': self.client_id,
            'enclosureId': self.enclosure_id,
            'animalTag': self.animal_tag,
            'animalName': self.animal_name,
            'symptom': self.symptom,
            'diagnosis': self.diagnosis,
            'treatment': self.treatment,
            'medications': self.medications,
            'status': self.status.value if self.status else None,
            'onsetDate': self.onset_date.isoformat() if self.onset_date else None,
            'diagnosisDate': self.diagnosis_date.isoformat() if self.diagnosis_date else None,
            'recoveryDate': self.recovery_date.isoformat() if self.recovery_date else None,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }


class FollowUpRecord(db.Model):
    """随访记录 - 诊疗的后续跟踪"""
    __tablename__ = 'follow_up_records'
    
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False, index=True)
    medical_record_id = db.Column(db.Integer, db.ForeignKey('medical_records.id'), nullable=False, index=True)
    
    # 随访内容
    follow_up_date = db.Column(db.DateTime, default=datetime.utcnow)  # 随访日期
    condition = db.Column(db.Text)                      # 病情变化
    notes = db.Column(db.Text)                          # 备注
    
    # 体征数据
    vital_signs = db.Column(db.JSON, default=dict)      # { "temperature": 38.5, "weight": 12.5, ... }
    
    # 随访人
    followed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # 下次随访
    next_follow_up_date = db.Column(db.DateTime)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联
    medical_record = db.relationship('MedicalRecord', backref='follow_ups')
    follower = db.relationship('User', foreign_keys=[followed_by])
    
    def to_dict(self):
        return {
            'id': self.id,
            'clientId': self.client_id,
            'medicalRecordId': self.medical_record_id,
            'followUpDate': self.follow_up_date.isoformat() if self.follow_up_date else None,
            'condition': self.condition,
            'notes': self.notes,
            'vitalSigns': self.vital_signs,
            'nextFollowUpDate': self.next_follow_up_date.isoformat() if self.next_follow_up_date else None,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }


# ==================== 旧模型兼容（保留用于迁移）====================

class UserAuth(db.Model):
    """
    用户认证信息 - 存储海康互联用户Token
    【保留用于向后兼容，新系统使用 CameraPlatform 表】
    """
    __tablename__ = 'user_auths'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 用户标识 (小程序用户ID或账号)
    user_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    
    # 海康互联账号信息
    hik_account = db.Column(db.String(50))              # 海康通行证账号
    team_no = db.Column(db.String(50))                  # 团队编号
    person_no = db.Column(db.String(50))                # 成员编号
    
    # Token 信息
    user_access_token = db.Column(db.String(500), nullable=False)
    refresh_user_token = db.Column(db.String(500))
    token_expires_at = db.Column(db.DateTime)           # Token 过期时间
    
    # 临时授权码 (用于授权过程中)
    temp_auth_code = db.Column(db.String(128))
    temp_auth_expires = db.Column(db.DateTime)
    
    # 状态
    status = db.Column(db.String(20), default='active')  # active/expired
    
    # 时间戳
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'userId': self.user_id,
            'hikAccount': self.hik_account,
            'teamNo': self.team_no,
            'personNo': self.person_no,
            'tokenExpiresAt': self.token_expires_at.isoformat() if self.token_expires_at else None,
            'status': self.status,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }
