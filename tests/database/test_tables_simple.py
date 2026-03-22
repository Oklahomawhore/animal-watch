#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版数据库测试 - 验证表结构和基本功能

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

from models_v2 import db, Client, User, UserRole, Factory, Area, Enclosure
from models_algorithm import (
    Event, EventHourlyStats, DailyReport, MedicalRecordV2, CareRecord,
    EventType, HealthStatus, ActivityLevel, EatingStatus, DrinkingStatus,
    MedicalStatus, CareRecordType, CareRecordCategory, CareRecordStatus
)


# ==================== Fixtures ====================

@pytest.fixture
def engine():
    """创建内存数据库引擎"""
    engine = create_engine('sqlite:///:memory:', echo=False)
    return engine


@pytest.fixture
def tables(engine):
    """创建所有表"""
    db.metadata.create_all(engine)
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
        
        # 检查外键是否存在
        assert len(fks) > 0, "events 表缺少外键约束"
    
    def test_enclosure_client_relation(self, session, sample_client):
        """测试圈舍-客户关系"""
        factory = Factory(
            client_id=sample_client.id,
            name='测试厂区2',
            code='F002'
        )
        session.add(factory)
        session.commit()
        
        # 验证关系
        assert factory.client_id == sample_client.id
        assert factory.client.name == '测试客户'
    
    def test_client_create_and_query(self, session):
        """测试客户创建和查询"""
        client = Client(
            name='新客户',
            code='NEW001'
        )
        session.add(client)
        session.commit()
        
        result = session.query(Client).filter_by(code='NEW001').first()
        assert result is not None
        assert result.name == '新客户'
    
    def test_enclosure_create_and_query(self, session, sample_client):
        """测试圈舍创建和查询"""
        factory = Factory(
            client_id=sample_client.id,
            name='厂区',
            code='F003'
        )
        session.add(factory)
        session.commit()
        
        area = Area(
            client_id=sample_client.id,
            factory_id=factory.id,
            name='区域',
            code='A003'
        )
        session.add(area)
        session.commit()
        
        enclosure = Enclosure(
            client_id=sample_client.id,
            factory_id=factory.id,
            area_id=area.id,
            name='圈舍',
            code='E003',
            animal_count=1,
            animal_tags=[{'tag': 'LS-003', 'name': '小黄'}]
        )
        session.add(enclosure)
        session.commit()
        
        result = session.query(Enclosure).filter_by(code='E003').first()
        assert result is not None
        assert result.animal_count == 1


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
    
    def test_client_query_performance(self, session):
        """测试客户查询性能"""
        import time
        
        # 批量创建客户
        for i in range(100):
            client = Client(
                name=f'客户{i}',
                code=f'CODE{i:04d}'
            )
            session.add(client)
        session.commit()
        
        # 测试查询性能
        start_time = time.time()
        result = session.query(Client).filter(
            Client.code.like('CODE%')
        ).limit(10).all()
        query_time = time.time() - start_time
        
        assert len(result) > 0
        assert query_time < 1.0, f"查询时间过长: {query_time:.3f}s"


# ==================== 测试4: 数据完整性 ====================

class TestDataIntegrity:
    """测试数据完整性"""
    
    def test_unique_constraint_client_code(self, session):
        """测试客户编码唯一约束"""
        client1 = Client(name='客户1', code='UNIQUE001')
        session.add(client1)
        session.commit()
        
        # 尝试创建重复编码的客户
        client2 = Client(name='客户2', code='UNIQUE001')
        session.add(client2)
        
        with pytest.raises(Exception):
            session.commit()
        
        session.rollback()
    
    def test_factory_area_relation(self, session, sample_client):
        """测试厂区-区域关系"""
        factory = Factory(
            client_id=sample_client.id,
            name='测试厂区',
            code='FTEST'
        )
        session.add(factory)
        session.commit()
        
        area = Area(
            client_id=sample_client.id,
            factory_id=factory.id,
            name='测试区域',
            code='ATEST'
        )
        session.add(area)
        session.commit()
        
        # 验证关系
        assert area.factory.id == factory.id
        assert area in factory.areas


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
