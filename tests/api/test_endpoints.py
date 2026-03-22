#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 接口测试

测试接口:
1. GET /api/v2/mp/daily-reports - 获取日报列表
2. GET /api/v2/mp/animals/:id/daily - 获取动物详情
3. POST /api/v2/mp/care-records - 添加饲养记录
4. 边界条件和错误处理
"""

import pytest
import json
import sys
import os
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../hikvision-backend'))

from flask import Flask
from models_algorithm import (
    DailyReport, MedicalRecordV2, CareRecord, EventHourlyStats,
    HealthStatus, ActivityLevel, MedicalStatus, CareRecordType, 
    CareRecordCategory, CareRecordStatus
)
from models_v2 import db, Client, User, UserRole, Factory, Area, Enclosure


# ==================== Fixtures ====================

@pytest.fixture
def app():
    """创建测试应用"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture
def auth_headers(app):
    """创建认证头"""
    # 模拟JWT token
    return {'Authorization': 'Bearer test-token'}


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
        
        # 创建用户
        user = User(
            client_id=client_obj.id,
            username='testuser',
            password_hash='hashed_password',
            nickname='测试用户',
            role=UserRole.ADMIN
        )
        db.session.add(user)
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
                {'tag': 'LS-001', 'name': '小白', 'gender': 'female'},
                {'tag': 'LS-002', 'name': '小黑', 'gender': 'male'}
            ]
        )
        db.session.add(enclosure)
        db.session.commit()
        
        # 创建日报
        report = DailyReport(
            client_id=client_obj.id,
            enclosure_id=enclosure.id,
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
            eating_status='正常',
            water_consumption_liters=6.8,
            drinking_status='正常',
            alerts_summary=[]
        )
        db.session.add(report)
        
        # 创建诊疗记录
        medical = MedicalRecordV2(
            client_id=client_obj.id,
            animal_id='LS-001',
            diagnosis='肠炎',
            diagnosis_date=date.today(),
            status=MedicalStatus.ONGOING,
            medications=[
                {'name': '消炎针', 'dosage': '每天1次', 'remain_days': 3}
            ],
            treatment_day=3,
            veterinarian='李医生'
        )
        db.session.add(medical)
        
        # 创建饲养记录
        care = CareRecord(
            client_id=client_obj.id,
            enclosure_id=enclosure.id,
            animal_id='LS-001',
            record_type=CareRecordType.OBSERVATION,
            category=CareRecordCategory.FECES,
            content='粪便正常',
            status=CareRecordStatus.COMPLETED,
            operator_id=user.id,
            operator_name='张师傅',
            scheduled_date=date.today(),
            completed_at=datetime.utcnow()
        )
        db.session.add(care)
        
        db.session.commit()
        
        yield {
            'client': client_obj,
            'user': user,
            'enclosure': enclosure,
            'report': report,
            'medical': medical,
            'care': care
        }


# ==================== Mock 认证装饰器 ====================

def mock_login_required(f):
    """模拟登录装饰器"""
    def decorated(*args, **kwargs):
        from flask import g
        # 从 sample_data 获取用户
        g.current_user = MagicMock()
        g.current_user.id = 1
        g.current_user.client_id = 1
        g.current_user.username = 'testuser'
        g.current_user.nickname = '测试用户'
        return f(*args, **kwargs)
    return decorated


# ==================== 测试1: GET /api/v2/mp/daily-reports ====================

class TestDailyReportsAPI:
    """测试日报列表接口"""
    
    @patch('routes.reports.login_required', mock_login_required)
    def test_get_daily_reports_success(self, app, client, sample_data):
        """测试成功获取日报列表"""
        with app.app_context():
            from routes.reports import mp_reports_bp
            app.register_blueprint(mp_reports_bp)
            
            response = client.get('/api/v2/mp/daily-reports')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['code'] == 0
            assert 'data' in data
            assert 'animals' in data['data']
    
    @patch('routes.reports.login_required', mock_login_required)
    def test_get_daily_reports_with_date(self, app, client, sample_data):
        """测试带日期参数获取日报"""
        with app.app_context():
            from routes.reports import mp_reports_bp
            app.register_blueprint(mp_reports_bp)
            
            today = date.today().isoformat()
            response = client.get(f'/api/v2/mp/daily-reports?date={today}')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['code'] == 0
    
    @patch('routes.reports.login_required', mock_login_required)
    def test_get_daily_reports_with_enclosure(self, app, client, sample_data):
        """测试带圈舍ID获取日报"""
        with app.app_context():
            from routes.reports import mp_reports_bp
            app.register_blueprint(mp_reports_bp)
            
            enclosure_id = sample_data['enclosure'].id
            response = client.get(f'/api/v2/mp/daily-reports?enclosure_id={enclosure_id}')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['code'] == 0
    
    @patch('routes.reports.login_required', mock_login_required)
    def test_get_daily_reports_pagination(self, app, client, sample_data):
        """测试分页功能"""
        with app.app_context():
            from routes.reports import mp_reports_bp
            app.register_blueprint(mp_reports_bp)
            
            response = client.get('/api/v2/mp/daily-reports?page=1&page_size=10')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['code'] == 0
            assert 'pagination' in data['data']


# ==================== 测试2: GET /api/v2/mp/animals/:id/daily ====================

class TestAnimalDailyAPI:
    """测试动物详情接口"""
    
    @patch('routes.reports.login_required', mock_login_required)
    def test_get_animal_daily_success(self, app, client, sample_data):
        """测试成功获取动物详情"""
        with app.app_context():
            from routes.reports import mp_reports_bp
            app.register_blueprint(mp_reports_bp)
            
            response = client.get('/api/v2/mp/animals/LS-001/daily')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['code'] == 0
            assert 'data' in data
            assert 'basic' in data['data']
            assert 'daily_data' in data['data']
    
    @patch('routes.reports.login_required', mock_login_required)
    def test_get_animal_daily_with_date(self, app, client, sample_data):
        """测试带日期参数获取动物详情"""
        with app.app_context():
            from routes.reports import mp_reports_bp
            app.register_blueprint(mp_reports_bp)
            
            today = date.today().isoformat()
            response = client.get(f'/api/v2/mp/animals/LS-001/daily?date={today}')
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['code'] == 0
    
    @patch('routes.reports.login_required', mock_login_required)
    def test_get_animal_daily_not_found(self, app, client, sample_data):
        """测试获取不存在的动物详情"""
        with app.app_context():
            from routes.reports import mp_reports_bp
            app.register_blueprint(mp_reports_bp)
            
            response = client.get('/api/v2/mp/animals/NONEXISTENT/daily')
            
            # 应该返回空数据而不是404
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['code'] == 0


# ==================== 测试3: POST /api/v2/mp/care-records ====================

class TestCareRecordsAPI:
    """测试添加饲养记录接口"""
    
    @patch('routes.reports.login_required', mock_login_required)
    def test_create_care_record_success(self, app, client, sample_data):
        """测试成功添加饲养记录"""
        with app.app_context():
            from routes.reports import mp_reports_bp
            app.register_blueprint(mp_reports_bp)
            
            payload = {
                'animal_id': 'LS-001',
                'record_type': 'observation',
                'category': '粪便',
                'content': '粪便稍软（已送检）',
                'priority': 0
            }
            
            response = client.post(
                '/api/v2/mp/care-records',
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['code'] == 0
            assert 'data' in data
            assert data['data']['animal_id'] == 'LS-001'
    
    @patch('routes.reports.login_required', mock_login_required)
    def test_create_care_record_missing_fields(self, app, client, sample_data):
        """测试缺少必填字段"""
        with app.app_context():
            from routes.reports import mp_reports_bp
            app.register_blueprint(mp_reports_bp)
            
            # 缺少 content
            payload = {
                'animal_id': 'LS-001',
                'record_type': 'observation'
            }
            
            response = client.post(
                '/api/v2/mp/care-records',
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['code'] == 400
    
    @patch('routes.reports.login_required', mock_login_required)
    def test_create_care_record_with_scheduled_date(self, app, client, sample_data):
        """测试创建待办任务"""
        with app.app_context():
            from routes.reports import mp_reports_bp
            app.register_blueprint(mp_reports_bp)
            
            tomorrow = (date.today() + timedelta(days=1)).isoformat()
            
            payload = {
                'animal_id': 'LS-001',
                'record_type': 'observation',
                'category': '体温',
                'content': '测量体温',
                'scheduled_date': tomorrow
            }
            
            response = client.post(
                '/api/v2/mp/care-records',
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['code'] == 0
    
    @patch('routes.reports.login_required', mock_login_required)
    def test_create_care_record_with_images(self, app, client, sample_data):
        """测试添加带图片的记录"""
        with app.app_context():
            from routes.reports import mp_reports_bp
            app.register_blueprint(mp_reports_bp)
            
            payload = {
                'animal_id': 'LS-001',
                'record_type': 'observation',
                'category': '粪便',
                'content': '粪便异常',
                'images': ['https://example.com/image1.jpg', 'https://example.com/image2.jpg']
            }
            
            response = client.post(
                '/api/v2/mp/care-records',
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['code'] == 0


# ==================== 测试4: 边界条件和错误处理 ====================

class TestEdgeCasesAndErrors:
    """测试边界条件和错误处理"""
    
    @patch('routes.reports.login_required', mock_login_required)
    def test_invalid_date_format(self, app, client, sample_data):
        """测试无效日期格式"""
        with app.app_context():
            from routes.reports import mp_reports_bp
            app.register_blueprint(mp_reports_bp)
            
            response = client.get('/api/v2/mp/daily-reports?date=invalid-date')
            
            # 应该返回错误
            assert response.status_code in [400, 500]
    
    @patch('routes.reports.login_required', mock_login_required)
    def test_invalid_json_payload(self, app, client, sample_data):
        """测试无效JSON数据"""
        with app.app_context():
            from routes.reports import mp_reports_bp
            app.register_blueprint(mp_reports_bp)
            
            response = client.post(
                '/api/v2/mp/care-records',
                data='invalid json',
                content_type='application/json'
            )
            
            assert response.status_code == 400
    
    @patch('routes.reports.login_required', mock_login_required)
    def test_empty_animal_id(self, app, client, sample_data):
        """测试空动物ID"""
        with app.app_context():
            from routes.reports import mp_reports_bp
            app.register_blueprint(mp_reports_bp)
            
            payload = {
                'animal_id': '',
                'record_type': 'observation',
                'content': '测试内容'
            }
            
            response = client.post(
                '/api/v2/mp/care-records',
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            assert response.status_code == 400
    
    @patch('routes.reports.login_required', mock_login_required)
    def test_large_page_size(self, app, client, sample_data):
        """测试超大分页大小"""
        with app.app_context():
            from routes.reports import mp_reports_bp
            app.register_blueprint(mp_reports_bp)
            
            response = client.get('/api/v2/mp/daily-reports?page_size=1000')
            
            # 应该限制最大分页大小
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['code'] == 0
    
    @patch('routes.reports.login_required', mock_login_required)
    def test_special_characters_in_content(self, app, client, sample_data):
        """测试特殊字符内容"""
        with app.app_context():
            from routes.reports import mp_reports_bp
            app.register_blueprint(mp_reports_bp)
            
            payload = {
                'animal_id': 'LS-001',
                'record_type': 'observation',
                'content': '特殊字符测试: <script>alert("xss")</script> 中文测试 🐾'
            }
            
            response = client.post(
                '/api/v2/mp/care-records',
                data=json.dumps(payload),
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['code'] == 0
    
    @patch('routes.reports.login_required', mock_login_required)
    def test_concurrent_requests(self, app, client, sample_data):
        """测试并发请求处理"""
        import threading
        import time
        
        with app.app_context():
            from routes.reports import mp_reports_bp
            app.register_blueprint(mp_reports_bp)
            
            results = []
            
            def make_request():
                try:
                    response = client.get('/api/v2/mp/daily-reports')
                    results.append(response.status_code)
                except Exception as e:
                    results.append(str(e))
            
            # 创建多个线程同时请求
            threads = []
            for i in range(5):
                t = threading.Thread(target=make_request)
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join()
            
            # 所有请求都应该成功
            assert all(code == 200 for code in results), f"并发请求失败: {results}"


# ==================== 测试5: 响应格式验证 ====================

class TestResponseFormat:
    """测试响应格式"""
    
    @patch('routes.reports.login_required', mock_login_required)
    def test_daily_report_response_structure(self, app, client, sample_data):
        """测试日报响应结构"""
        with app.app_context():
            from routes.reports import mp_reports_bp
            app.register_blueprint(mp_reports_bp)
            
            response = client.get('/api/v2/mp/daily-reports')
            data = json.loads(response.data)
            
            # 验证标准响应格式
            assert 'code' in data
            assert 'data' in data
            assert isinstance(data['data'], dict)
    
    @patch('routes.reports.login_required', mock_login_required)
    def test_animal_daily_response_structure(self, app, client, sample_data):
        """测试动物详情响应结构"""
        with app.app_context():
            from routes.reports import mp_reports_bp
            app.register_blueprint(mp_reports_bp)
            
            response = client.get('/api/v2/mp/animals/LS-001/daily')
            data = json.loads(response.data)
            
            # 验证数据结构
            assert 'code' in data
            if data['code'] == 0:
                assert 'data' in data
                if data['data']:
                    assert 'basic' in data['data']
                    assert 'daily_data' in data['data']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
