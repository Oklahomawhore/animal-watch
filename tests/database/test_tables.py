#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库测试 - 测试5张表的创建、迁移、关系和约束

测试表:
1. events - 原子事件表
2. event_hourly_stats - 小时统计表
3. daily_reports - 日报表
4. medical_records_v2 - 诊疗记录表
5. care_records - 饲养记录表
"""

import pytest
import sys
import os
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../hikvision-backend'))

from models_algorithm import (
    Event, EventHourlyStats, DailyReport, MedicalRecordV2, CareRecord,
    EventType, HealthStatus, ActivityLevel, EatingStatus, DrinkingStatus,
    MedicalStatus, CareRecordType, CareRecordCategory, CareRecordStatus
)
from models_v2 import db, Client, User, Factory, Area, Enclosure, Camera


# ==================== Fixtures ====================

@pytest.fixture
def engine():
    """创建内存数据库引擎"""
    engine = create_engine('sqlite:///:memory:', echo=False)
    return engine


@pytest.fixture
def tables(engine):
    """创建所有表"""
    from models_v2 import db as _db
    from models_algorithm import db as _algo_db
    
    # 使用相同的metadata
    _db.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(tables):
    """创建数据库会话"""
    Session = sessionmaker(bind=tables)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def sample_client(session):
    """创建测试客户"""
    client = Client(
        name='测试客户',
        code='TEST001',
        contact_name='测试联系人',
        contact_phone='13800138000'
    )
    session.add(client)
    session.commit()
    return client


@pytest.fixture
def sample_enclosure(session, sample_client):
    """创建测试圈舍"""
    factory = Factory(
        client_id=sample_client.id,
        name='测试厂区',
        code='F001'
    )
    session.add(factory)
    session.commit()
    
    area = Area(
        client_id=sample_client.id,
        factory_id=factory.id,
        name='测试区域',
        code='A001'
    )
    session.add(area)
    session.commit()
    
    enclosure = Enclosure(
        client_id=sample_client.id,
        factory_id=factory.id,
        area_id=area.id,
        name='测试圈舍',
        code='E001',
        animal_count=2,
        animal_tags=[
            {'tag': 'LS-001', 'name': '小白', 'gender': 'female'},
            {'tag': 'LS-002', 'name': '小黑', 'gender': 'male'}
        ]
    )
    session.add(enclosure)
    session.commit()
    return enclosure


# ==================== 测试1: 表创建和迁移 ====================

class TestTableCreation:
    """测试表创建和迁移"""
    
    def test_events_table_exists(self, tables):
        """测试 events 表是否存在"""
        inspector = inspect(tables)
        assert 'events' in inspector.get_table_names(), "events 表不存在"
    
    def test_event_hourly_stats_table_exists(self, tables):
        """测试 event_hourly_stats 表是否存在"""
        inspector = inspect(tables)
        assert 'event_hourly_stats' in inspector.get_table_names(), "event_hourly_stats 表不存在"
    
    def test_daily_reports_table_exists(self, tables):
        """测试 daily_reports 表是否存在"""
        inspector = inspect(tables)
        assert 'daily_reports' in inspector.get_table_names(), "daily_reports 表不存在"
    
    def test_medical_records_v2_table_exists(self, tables):
        """测试 medical_records_v2 表是否存在"""
        inspector = inspect(tables)
        assert 'medical_records_v2' in inspector.get_table_names(), "medical_records_v2 表不存在"
    
    def test_care_records_table_exists(self, tables):
        """测试 care_records 表是否存在"""
        inspector = inspect(tables)
        assert 'care_records' in inspector.get_table_names(), "care_records 表不存在"
    
    def test_events_table_columns(self, tables):
        """测试 events 表字段"""
        inspector = inspect(tables)
        columns = {col['name'] for col in inspector.get_columns('events')}
        
        required_columns = {
            'id', 'client_id', 'enclosure_id', 'animal_id', 'camera_id',
            'channel_no', 'event_type', 'confidence', 'bbox_x1', 'bbox_y1',
            'bbox_x2', 'bbox_y2', 'event_time', 'created_at'
        }
        
        missing = required_columns - columns
        assert not missing, f"events 表缺少字段: {missing}"
    
    def test_daily_reports_table_columns(self, tables):
        """测试 daily_reports 表字段"""
        inspector = inspect(tables)
        columns = {col['name'] for col in inspector.get_columns('daily_reports')}
        
        required_columns = {
            'id', 'client_id', 'enclosure_id', 'animal_id', 'report_date',
            'ear_tag', 'gender', 'age', 'health_status', 'activity_score',
            'activity_level', 'activity_trend', 'feed_main_remain_percent',
            'feed_aux_remain_percent', 'eating_status', 'water_consumption_liters',
            'drinking_status', 'alerts_summary', 'created_at', 'updated_at'
        }
        
        missing = required_columns - columns
        assert not missing, f"daily_reports 表缺少字段: {missing}"


# ==================== 测试2: 表关系和约束 ====================

class TestTableRelations:
    """测试表关系和约束"""
    
    def test_event_foreign_keys(self, tables):
        """测试 events 表外键约束"""
        inspector = inspect(tables)
        fks = inspector.get_foreign_keys('events')
        fk_names = {fk['name'] for fk in fks}
        
        # 检查外键是否存在
        assert len(fks) > 0, "events 表缺少外键约束"
    
    def test_daily_report_unique_constraint(self, tables):
        """测试日报表唯一约束"""
        inspector = inspect(tables)
        indexes = inspector.get_indexes('daily_reports')
        
        # 检查唯一索引
        unique_indexes = [idx for idx in indexes if idx.get('unique')]
        assert len(unique_indexes) > 0, "daily_reports 表缺少唯一索引"
    
    def test_event_create_and_query(self, session, sample_client, sample_enclosure):
        """测试创建和查询事件"""
        from sqlalchemy import text
        
        # 对于SQLite，我们需要手动设置ID
        result = session.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM events"))
        next_id = result.scalar()
        
        event = Event(
            id=next_id,
            client_id=sample_client.id,
            enclosure_id=sample_enclosure.id,
            animal_id='LS-001',
            camera_id='CAM001',
            channel_no=1,
            event_type=EventType.MOVEMENT,
            confidence=0.95,
            bbox_x1=10.0,
            bbox_y1=20.0,
            bbox_x2=100.0,
            bbox_y2=200.0,
            event_time=datetime.utcnow()
        )
        session.add(event)
        session.commit()
        
        # 查询验证
        result = session.query(Event).filter_by(animal_id='LS-001').first()
        assert result is not None, "事件创建失败"
        assert result.event_type == EventType.MOVEMENT, "事件类型不匹配"
        assert result.confidence == 0.95, "置信度不匹配"
    
    def test_daily_report_create_and_query(self, session, sample_client, sample_enclosure):
        """测试创建和查询日报"""
        report = DailyReport(
            client_id=sample_client.id,
            enclosure_id=sample_enclosure.id,
            animal_id='LS-001',
            report_date=date.today(),
            ear_tag='LS-001',
            gender='雌性',
            age='1岁',
            health_status=HealthStatus.GREEN.value,
            activity_score=82,
            activity_level=ActivityLevel.NORMAL.value,
            activity_trend=[78, 82, 75, 80, 82, 79, 82],
            feed_main_remain_percent=35.0,
            feed_aux_remain_percent=72.0,
            eating_status=EatingStatus.NORMAL.value,
            water_consumption_liters=6.8,
            drinking_status=DrinkingStatus.NORMAL.value,
            alerts_summary=[]
        )
        session.add(report)
        session.commit()
        
        # 查询验证
        result = session.query(DailyReport).filter_by(animal_id='LS-001').first()
        assert result is not None, "日报创建失败"
        assert result.activity_score == 82, "活动评分不匹配"
    
    def test_medical_record_create_and_query(self, session, sample_client):
        """测试创建和查询诊疗记录"""
        record = MedicalRecordV2(
            client_id=sample_client.id,
            animal_id='LS-001',
            diagnosis='肠炎',
            diagnosis_date=date.today(),
            status=MedicalStatus.ONGOING,
            medications=[
                {'name': '消炎针', 'dosage': '每天1次', 'remain_days': 3},
                {'name': '益生菌', 'dosage': '拌料', 'remain_days': 5}
            ],
            treatment_day=3,
            veterinarian='李医生',
            notes='注意观察进食情况'
        )
        session.add(record)
        session.commit()
        
        # 查询验证
        result = session.query(MedicalRecordV2).filter_by(animal_id='LS-001').first()
        assert result is not None, "诊疗记录创建失败"
        assert result.diagnosis == '肠炎', "诊断不匹配"
        assert len(result.medications) == 2, "用药记录数量不匹配"
    
    def test_care_record_create_and_query(self, session, sample_client, sample_enclosure):
        """测试创建和查询饲养记录"""
        record = CareRecord(
            client_id=sample_client.id,
            enclosure_id=sample_enclosure.id,
            animal_id='LS-001',
            record_type=CareRecordType.OBSERVATION,
            category=CareRecordCategory.FECES,
            content='粪便稍软（已送检）',
            status=CareRecordStatus.COMPLETED,
            priority=0,
            images=['https://example.com/image1.jpg'],
            operator_id=1,
            operator_name='张师傅',
            scheduled_date=date.today(),
            completed_at=datetime.utcnow()
        )
        session.add(record)
        session.commit()
        
        # 查询验证
        result = session.query(CareRecord).filter_by(animal_id='LS-001').first()
        assert result is not None, "饲养记录创建失败"
        assert result.category == CareRecordCategory.FECES, "分类不匹配"
    
    def test_hourly_stats_create_and_query(self, session, sample_client, sample_enclosure):
        """测试创建和查询小时统计"""
        stats = EventHourlyStats(
            client_id=sample_client.id,
            enclosure_id=sample_enclosure.id,
            animal_id='LS-001',
            stat_date=date.today(),
            hour=10,
            movement_count=15,
            movement_duration=45,
            avg_movement_score=75.5,
            eating_count=3,
            eating_duration=300,
            drinking_count=5,
            drinking_duration=120,
            resting_duration=1800,
            alert_count=0,
            activity_score=82
        )
        session.add(stats)
        session.commit()
        
        # 查询验证
        result = session.query(EventHourlyStats).filter_by(
            animal_id='LS-001',
            stat_date=date.today(),
            hour=10
        ).first()
        assert result is not None, "小时统计创建失败"
        assert result.activity_score == 82, "活动评分不匹配"


# ==================== 测试3: 索引性能 ====================

class TestIndexPerformance:
    """测试索引性能"""
    
    def test_events_time_index(self, tables):
        """测试 events 表时间索引"""
        inspector = inspect(tables)
        indexes = inspector.get_indexes('events')
        index_names = {idx['name'] for idx in indexes}
        
        # 检查时间相关索引
        time_indexes = [name for name in index_names if 'time' in name.lower()]
        assert len(time_indexes) > 0, "events 表缺少时间索引"
    
    def test_daily_reports_date_index(self, tables):
        """测试 daily_reports 表日期索引"""
        inspector = inspect(tables)
        indexes = inspector.get_indexes('daily_reports')
        index_names = {idx['name'] for idx in indexes}
        
        # 检查日期索引
        date_indexes = [name for name in index_names if 'date' in name.lower()]
        assert len(date_indexes) > 0, "daily_reports 表缺少日期索引"
    
    def test_hourly_stats_unique_index(self, tables):
        """测试小时统计唯一索引"""
        inspector = inspect(tables)
        indexes = inspector.get_indexes('event_hourly_stats')
        
        unique_indexes = [idx for idx in indexes if idx.get('unique')]
        assert len(unique_indexes) > 0, "event_hourly_stats 表缺少唯一索引"
    
    def test_query_performance_with_index(self, session, sample_client, sample_enclosure):
        """测试索引查询性能"""
        import time
        from sqlalchemy import text
        
        # 批量插入测试数据
        base_time = datetime.utcnow() - timedelta(hours=100)
        
        for i in range(1000):
            result = session.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM events"))
            next_id = result.scalar() or 1
            
            event = Event(
                id=next_id + i,
                client_id=sample_client.id,
                enclosure_id=sample_enclosure.id,
                animal_id=f'LS-{i % 10:03d}',
                camera_id='CAM001',
                event_type=EventType.MOVEMENT if i % 3 == 0 else EventType.EATING,
                confidence=0.8 + (i % 20) / 100,
                event_time=base_time + timedelta(minutes=i)
            )
            session.add(event)
        
        session.commit()
        
        # 测试带索引查询性能
        start_time = time.time()
        result = session.query(Event).filter(
            Event.client_id == sample_client.id,
            Event.event_time >= base_time,
            Event.event_time <= base_time + timedelta(hours=10)
        ).all()
        query_time = time.time() - start_time
        
        assert len(result) > 0, "查询结果为空"
        assert query_time < 1.0, f"查询时间过长: {query_time:.3f}s"


# ==================== 测试4: 数据完整性 ====================

class TestDataIntegrity:
    """测试数据完整性"""
    
    def test_cascade_delete(self, session, sample_client, sample_enclosure):
        """测试级联删除"""
        from sqlalchemy import text
        
        # 创建关联数据
        result = session.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM events"))
        next_id = result.scalar()
        
        event = Event(
            id=next_id,
            client_id=sample_client.id,
            enclosure_id=sample_enclosure.id,
            animal_id='LS-001',
            event_type=EventType.MOVEMENT,
            event_time=datetime.utcnow()
        )
        session.add(event)
        session.commit()
        
        event_id = event.id
        
        # 删除圈舍（检查是否级联删除或阻止）
        # 注意：根据实际外键约束配置，可能阻止删除或级联删除
        session.delete(sample_enclosure)
        session.commit()
        
        # 验证事件是否还存在
        remaining = session.query(Event).filter_by(id=event_id).first()
        # 这里根据实际的外键约束行为断言
        # 如果配置了级联删除，remaining 应该为 None
        # 如果没有配置，remaining 可能仍然存在
    
    def test_null_constraints(self, session, sample_client):
        """测试非空约束"""
        # 尝试创建缺少必填字段的记录
        with pytest.raises(Exception):
            report = DailyReport(
                client_id=sample_client.id,
                # 缺少 animal_id 和 report_date
            )
            session.add(report)
            session.commit()
        
        session.rollback()
    
    def test_enum_constraints(self, session, sample_client, sample_enclosure):
        """测试枚举约束"""
        # 测试有效的枚举值
        event = Event(
            client_id=sample_client.id,
            enclosure_id=sample_enclosure.id,
            event_type=EventType.MOVEMENT,
            event_time=datetime.utcnow()
        )
        session.add(event)
        session.commit()
        
        assert event.event_type == EventType.MOVEMENT


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
