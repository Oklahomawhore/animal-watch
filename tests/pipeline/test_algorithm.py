#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
算法 Pipeline 测试

测试模块:
1. capture_service - 帧抓取服务
2. hourly_aggregator - 小时聚合器
3. daily_reporter - 日报生成器
4. 事件流端到端流程
"""

import pytest
import asyncio
import sys
import os
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
import json

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../hikvision-backend'))

from flask import Flask
from models_algorithm import (
    Event, EventHourlyStats, DailyReport, EventType, 
    ActivityLevel, EatingStatus, DrinkingStatus
)
from models_v2 import db, Client, Factory, Area, Enclosure, Camera, CameraStatus


# ==================== Fixtures ====================

@pytest.fixture
def app():
    """创建测试应用"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def sample_data(app):
    """创建测试数据"""
    with app.app_context():
        # 创建客户
        client_obj = Client(
            name='测试客户',
            code='TEST001'
        )
        db.session.add(client_obj)
        db.session.commit()
        
        # 创建厂区
        factory = Factory(
            client_id=client_obj.id,
            name='测试厂区',
            code='F001'
        )
        db.session.add(factory)
        db.session.commit()
        
        # 创建区域
        area = Area(
            client_id=client_obj.id,
            factory_id=factory.id,
            name='测试区域',
            code='A001'
        )
        db.session.add(area)
        db.session.commit()
        
        # 创建圈舍
        enclosure = Enclosure(
            client_id=client_obj.id,
            factory_id=factory.id,
            area_id=area.id,
            name='测试圈舍',
            code='E001',
            animal_count=2,
            animal_tags=[
                {'tag': 'LS-001', 'name': '小白', 'gender': 'female', 'birth_date': '2023-01-15'},
                {'tag': 'LS-002', 'name': '小黑', 'gender': 'male', 'birth_date': '2022-06-20'}
            ]
        )
        db.session.add(enclosure)
        db.session.commit()
        
        yield {
            'client': client_obj,
            'enclosure': enclosure
        }


# ==================== 测试1: Capture Service 帧抓取 ====================

class TestCaptureService:
    """测试帧抓取服务"""
    
    @pytest.mark.asyncio
    async def test_capture_service_initialization(self, app):
        """测试抓取服务初始化"""
        from algorithm_pipeline.capture_service import CaptureService
        
        service = CaptureService(app, interval=1.0)
        
        assert service.app == app
        assert service.interval == 1.0
        assert service.running == False
        assert service.stats['total_frames'] == 0
    
    @pytest.mark.asyncio
    async def test_capture_service_start_stop(self, app):
        """测试启动和停止服务"""
        from algorithm_pipeline.capture_service import CaptureService
        
        service = CaptureService(app, interval=0.1)
        
        # 启动服务（短暂运行后停止）
        async def run_and_stop():
            asyncio.create_task(service.start())
            await asyncio.sleep(0.2)
            await service.stop()
        
        await run_and_stop()
        
        assert service.running == False
        assert service.session is None
    
    @pytest.mark.asyncio
    async def test_capture_service_stats(self, app):
        """测试统计信息"""
        from algorithm_pipeline.capture_service import CaptureService
        
        service = CaptureService(app)
        
        stats = service.get_stats()
        
        assert 'running' in stats
        assert 'camera_count' in stats
        assert 'total_frames' in stats
        assert 'total_events' in stats
        assert 'total_alerts' in stats
        assert 'errors' in stats
    
    @pytest.mark.asyncio
    async def test_fetch_frame_with_mock(self, app):
        """测试帧抓取（模拟）"""
        from algorithm_pipeline.capture_service import CaptureService
        
        service = CaptureService(app)
        service.session = MagicMock()
        
        # 模拟HTTP响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.read = AsyncMock(return_value=b'fake_image_data')
        
        service.session.get = AsyncMock(return_value=mock_response)
        
        camera = {
            'camera_id': 'CAM001',
            'snapshot_url': 'http://example.com/snapshot.jpg'
        }
        
        frame = await service.fetch_frame(camera)
        
        assert frame == b'fake_image_data'
    
    @pytest.mark.asyncio
    async def test_run_inference_mock(self, app):
        """测试算法推理（模拟）"""
        from algorithm_pipeline.capture_service import CaptureService
        
        service = CaptureService(app)
        
        camera = {'camera_id': 'CAM001'}
        frame = b'fake_image_data'
        
        result = await service.run_inference(camera, frame)
        
        assert 'events' in result
        assert 'animal_count' in result
        assert 'activity_score' in result
        assert isinstance(result['events'], list)
    
    @pytest.mark.asyncio
    async def test_check_alerts(self, app):
        """测试告警检测"""
        from algorithm_pipeline.capture_service import CaptureService
        
        service = CaptureService(app)
        
        # 测试低活动告警
        detection_result = {'activity_score': 5, 'animal_count': 1}
        events = []
        
        alerts = service.check_alerts(detection_result, events)
        
        assert len(alerts) > 0
        assert any(a['type'] == 'low_activity' for a in alerts)
    
    @pytest.mark.asyncio
    async def test_check_alerts_no_animal(self, app):
        """测试无动物告警"""
        from algorithm_pipeline.capture_service import CaptureService
        
        service = CaptureService(app)
        
        detection_result = {'activity_score': 0, 'animal_count': 0}
        events = []
        
        alerts = service.check_alerts(detection_result, events)
        
        assert any(a['type'] == 'no_animal' for a in alerts)


# ==================== 测试2: Hourly Aggregator 聚合逻辑 ====================

class TestHourlyAggregator:
    """测试小时聚合器"""
    
    @pytest.mark.asyncio
    async def test_aggregator_initialization(self, app):
        """测试聚合器初始化"""
        from algorithm_pipeline.hourly_aggregator import HourlyAggregator
        
        aggregator = HourlyAggregator(app)
        
        assert aggregator.app == app
        assert aggregator.running == False
    
    @pytest.mark.asyncio
    async def test_calculate_metrics_movement(self, app, sample_data):
        """测试移动指标计算"""
        from algorithm_pipeline.hourly_aggregator import HourlyAggregator
        
        aggregator = HourlyAggregator(app)
        
        # 创建测试事件
        events = []
        for i in range(10):
            event = Event(
                client_id=sample_data['client'].id,
                enclosure_id=sample_data['enclosure'].id,
                animal_id='LS-001',
                event_type=EventType.MOVEMENT,
                event_time=datetime.utcnow()
            )
            events.append(event)
        
        stats = aggregator._calculate_metrics(events)
        
        assert stats['movement_count'] == 10
        assert stats['movement_duration'] == 30  # 10 * 3秒
        assert stats['avg_movement_score'] is not None
    
    @pytest.mark.asyncio
    async def test_calculate_metrics_eating(self, app, sample_data):
        """测试进食指标计算"""
        from algorithm_pipeline.hourly_aggregator import HourlyAggregator
        
        aggregator = HourlyAggregator(app)
        
        events = []
        for i in range(5):
            event = Event(
                client_id=sample_data['client'].id,
                enclosure_id=sample_data['enclosure'].id,
                animal_id='LS-001',
                event_type=EventType.EATING,
                event_time=datetime.utcnow()
            )
            events.append(event)
        
        stats = aggregator._calculate_metrics(events)
        
        assert stats['eating_count'] == 5
        assert stats['eating_duration'] == 25  # 5 * 5秒
    
    @pytest.mark.asyncio
    async def test_calculate_activity_score(self, app):
        """测试活动评分计算"""
        from algorithm_pipeline.hourly_aggregator import HourlyAggregator
        
        aggregator = HourlyAggregator(app)
        
        # 测试正常活动
        stats = {
            'movement_duration': 120,
            'eating_count': 3,
            'drinking_count': 5,
            'alert_count': 0
        }
        
        score = aggregator._calculate_activity_score(stats)
        
        assert 0 <= score <= 100
        assert score > 50  # 正常活动应该得分较高
    
    @pytest.mark.asyncio
    async def test_calculate_activity_score_low(self, app):
        """测试低活动评分"""
        from algorithm_pipeline.hourly_aggregator import HourlyAggregator
        
        aggregator = HourlyAggregator(app)
        
        # 测试低活动
        stats = {
            'movement_duration': 0,
            'eating_count': 0,
            'drinking_count': 0,
            'alert_count': 2
        }
        
        score = aggregator._calculate_activity_score(stats)
        
        assert score < 50  # 低活动应该得分较低
    
    @pytest.mark.asyncio
    async def test_aggregate_hour(self, app, sample_data):
        """测试小时聚合"""
        from algorithm_pipeline.hourly_aggregator import HourlyAggregator
        
        aggregator = HourlyAggregator(app)
        
        # 先创建一些事件
        with app.app_context():
            for i in range(5):
                event = Event(
                    client_id=sample_data['client'].id,
                    enclosure_id=sample_data['enclosure'].id,
                    animal_id='LS-001',
                    event_type=EventType.MOVEMENT,
                    event_time=datetime.utcnow() - timedelta(minutes=i*10)
                )
                db.session.add(event)
            db.session.commit()
        
        # 聚合当前小时
        today = date.today()
        current_hour = datetime.utcnow().hour
        
        await aggregator.aggregate_hour(today, current_hour)
        
        # 验证统计记录是否创建
        with app.app_context():
            stats = EventHourlyStats.query.filter_by(
                enclosure_id=sample_data['enclosure'].id,
                stat_date=today,
                hour=current_hour
            ).first()
            
            assert stats is not None
            assert stats.movement_count >= 0


# ==================== 测试3: Daily Reporter 日报生成 ====================

class TestDailyReporter:
    """测试日报生成器"""
    
    @pytest.mark.asyncio
    async def test_reporter_initialization(self, app):
        """测试生成器初始化"""
        from algorithm_pipeline.daily_reporter import DailyReporter
        
        reporter = DailyReporter(app)
        
        assert reporter.app == app
        assert reporter.running == False
    
    def test_calculate_age(self, app):
        """测试年龄计算"""
        from algorithm_pipeline.daily_reporter import DailyReporter
        
        reporter = DailyReporter(app)
        
        # 测试1岁
        age = reporter._calculate_age('2023-01-15')
        assert '岁' in age or '个月' in age
        
        # 测试无效日期
        age = reporter._calculate_age(None)
        assert age == '未知'
    
    def test_determine_activity_level(self, app):
        """测试活动水平判断"""
        from algorithm_pipeline.daily_reporter import DailyReporter, ActivityLevel
        
        reporter = DailyReporter(app)
        
        assert reporter._determine_activity_level(20) == ActivityLevel.LOW
        assert reporter._determine_activity_level(50) == ActivityLevel.NORMAL
        assert reporter._determine_activity_level(90) == ActivityLevel.HIGH
    
    def test_determine_eating_status(self, app):
        """测试进食状态判断"""
        from algorithm_pipeline.daily_reporter import DailyReporter, EatingStatus
        
        reporter = DailyReporter(app)
        
        # 未进食（<10分钟）
        assert reporter._determine_eating_status(0) == EatingStatus.NOT_EATING
        # 慢食（10-20分钟）
        assert reporter._determine_eating_status(900) == EatingStatus.SLOW  # 15分钟
        # 正常（20-120分钟）
        assert reporter._determine_eating_status(3600) == EatingStatus.NORMAL  # 60分钟
        # 快食（>120分钟）
        assert reporter._determine_eating_status(9000) == EatingStatus.FAST  # 150分钟
    
    def test_determine_drinking_status(self, app):
        """测试饮水状态判断"""
        from algorithm_pipeline.daily_reporter import DailyReporter, DrinkingStatus
        
        reporter = DailyReporter(app)
        
        assert reporter._determine_drinking_status(1.0) == DrinkingStatus.LOW
        assert reporter._determine_drinking_status(3.0) == DrinkingStatus.NORMAL
        assert reporter._determine_drinking_status(7.0) == DrinkingStatus.HIGH
    
    def test_aggregate_daily(self, app, sample_data):
        """测试日数据聚合"""
        from algorithm_pipeline.daily_reporter import DailyReporter
        
        reporter = DailyReporter(app)
        
        # 创建小时统计
        hourly_stats = []
        for hour in range(24):
            stats = EventHourlyStats(
                client_id=sample_data['client'].id,
                enclosure_id=sample_data['enclosure'].id,
                animal_id='LS-001',
                stat_date=date.today(),
                hour=hour,
                movement_duration=100,
                eating_duration=50,
                drinking_duration=30,
                activity_score=75
            )
            hourly_stats.append(stats)
        
        daily = reporter._aggregate_daily(hourly_stats)
        
        assert 'activity_score' in daily
        assert 'activity_level' in daily
        assert 'eating_status' in daily
        assert 'drinking_status' in daily
    
    @pytest.mark.asyncio
    async def test_generate_animal_report(self, app, sample_data):
        """测试生成单只动物日报"""
        from algorithm_pipeline.daily_reporter import DailyReporter
        
        reporter = DailyReporter(app)
        
        animal = {
            'client_id': sample_data['client'].id,
            'enclosure_id': sample_data['enclosure'].id,
            'animal_id': 'LS-001',
            'ear_tag': 'LS-001',
            'gender': 'female',
            'age': '1岁'
        }
        
        await reporter._generate_animal_report(animal, date.today())
        
        # 验证日报是否创建
        with app.app_context():
            report = DailyReport.query.filter_by(
                animal_id='LS-001',
                report_date=date.today()
            ).first()
            
            assert report is not None
            assert report.animal_id == 'LS-001'


# ==================== 测试4: 事件流端到端流程 ====================

class TestEventStreamEndToEnd:
    """测试事件流端到端流程"""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_flow(self, app, sample_data):
        """测试完整流程：事件生成 -> 小时聚合 -> 日报生成"""
        from algorithm_pipeline.capture_service import CaptureService
        from algorithm_pipeline.hourly_aggregator import HourlyAggregator
        from algorithm_pipeline.daily_reporter import DailyReporter
        
        # 1. 模拟生成事件
        with app.app_context():
            for i in range(20):
                event = Event(
                    client_id=sample_data['client'].id,
                    enclosure_id=sample_data['enclosure'].id,
                    animal_id='LS-001',
                    event_type=EventType.MOVEMENT if i % 2 == 0 else EventType.EATING,
                    confidence=0.8 + (i % 10) / 100,
                    event_time=datetime.utcnow() - timedelta(minutes=i*3)
                )
                db.session.add(event)
            db.session.commit()
        
        # 2. 运行小时聚合
        aggregator = HourlyAggregator(app)
        today = date.today()
        current_hour = datetime.utcnow().hour
        
        await aggregator.aggregate_hour(today, current_hour)
        
        # 3. 生成日报
        reporter = DailyReporter(app)
        
        animal = {
            'client_id': sample_data['client'].id,
            'enclosure_id': sample_data['enclosure'].id,
            'animal_id': 'LS-001',
            'ear_tag': 'LS-001',
            'gender': '雌性',
            'age': '1岁'
        }
        
        await reporter._generate_animal_report(animal, today)
        
        # 4. 验证结果
        with app.app_context():
            # 检查小时统计
            hourly_stats = EventHourlyStats.query.filter_by(
                animal_id='LS-001',
                stat_date=today
            ).all()
            assert len(hourly_stats) > 0
            
            # 检查日报
            daily_report = DailyReport.query.filter_by(
                animal_id='LS-001',
                report_date=today
            ).first()
            assert daily_report is not None
            assert daily_report.activity_score is not None
    
    @pytest.mark.asyncio
    async def test_event_to_hourly_stats_consistency(self, app, sample_data):
        """测试事件到小时统计的一致性"""
        from algorithm_pipeline.hourly_aggregator import HourlyAggregator
        
        # 创建已知数量的事件
        with app.app_context():
            for i in range(10):
                event = Event(
                    client_id=sample_data['client'].id,
                    enclosure_id=sample_data['enclosure'].id,
                    animal_id='LS-001',
                    event_type=EventType.MOVEMENT,
                    metadata={'movement_score': 80},
                    event_time=datetime.utcnow()
                )
                db.session.add(event)
            db.session.commit()
        
        # 聚合
        aggregator = HourlyAggregator(app)
        today = date.today()
        current_hour = datetime.utcnow().hour
        
        await aggregator.aggregate_hour(today, current_hour)
        
        # 验证统计准确性
        with app.app_context():
            stats = EventHourlyStats.query.filter_by(
                animal_id='LS-001',
                stat_date=today,
                hour=current_hour
            ).first()
            
            assert stats is not None
            assert stats.movement_count == 10
    
    @pytest.mark.asyncio
    async def test_hourly_to_daily_consistency(self, app, sample_data):
        """测试小时统计到日报的一致性"""
        from algorithm_pipeline.daily_reporter import DailyReporter
        
        # 创建24小时统计
        with app.app_context():
            for hour in range(24):
                stats = EventHourlyStats(
                    client_id=sample_data['client'].id,
                    enclosure_id=sample_data['enclosure'].id,
                    animal_id='LS-001',
                    stat_date=date.today(),
                    hour=hour,
                    movement_count=10,
                    movement_duration=30,
                    eating_count=2,
                    eating_duration=60,
                    drinking_count=3,
                    drinking_duration=30,
                    activity_score=80
                )
                db.session.add(stats)
            db.session.commit()
        
        # 生成日报
        reporter = DailyReporter(app)
        
        animal = {
            'client_id': sample_data['client'].id,
            'enclosure_id': sample_data['enclosure'].id,
            'animal_id': 'LS-001',
            'ear_tag': 'LS-001',
            'gender': '雌性',
            'age': '1岁'
        }
        
        await reporter._generate_animal_report(animal, date.today())
        
        # 验证日报数据
        with app.app_context():
            report = DailyReport.query.filter_by(
                animal_id='LS-001',
                report_date=date.today()
            ).first()
            
            assert report is not None
            # 活动评分应该基于24小时的平均值
            assert report.activity_score == 80
    
    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self, app, sample_data):
        """测试流水线错误处理"""
        from algorithm_pipeline.hourly_aggregator import HourlyAggregator
        
        aggregator = HourlyAggregator(app)
        
        # 测试无效日期
        with pytest.raises(Exception):
            await aggregator.aggregate_hour(None, 12)
        
        # 验证错误统计
        assert aggregator.stats['errors'] > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
