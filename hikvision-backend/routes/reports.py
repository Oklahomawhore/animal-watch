#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小程序 API - 日报相关接口

接口列表：
1. GET /api/v2/mp/daily-reports - 获取日报列表
2. GET /api/v2/mp/animals/:id/daily - 获取动物详情（含诊疗、饲养记录）
3. POST /api/v2/mp/care-records - 添加饲养记录
"""

from datetime import datetime, date
from flask import Blueprint, request, jsonify, g

from models_algorithm import DailyReport, MedicalRecordV2, CareRecord, CareRecordStatus
from models_v2 import Enclosure
from utils.auth import login_required

# 创建蓝图
mp_reports_bp = Blueprint('mp_reports', __name__, url_prefix='/api/v2/mp')


# ==================== 1. 获取日报列表 ====================

@mp_reports_bp.route('/daily-reports', methods=['GET'])
@login_required
def get_daily_reports():
    """
    获取日报列表
    
    Query参数:
        - enclosure_id: 圈舍ID（可选）
        - date: 日期，格式 YYYY-MM-DD（可选，默认今天）
        - page: 页码（可选，默认1）
        - page_size: 每页数量（可选，默认20）
    
    Response:
        {
            "code": 0,
            "data": {
                "date": "2026-03-22",
                "enclosure_id": 123,
                "animals": [
                    {
                        "ear_tag": "LS-B2-025",
                        "gender": "雌性",
                        "age": "1岁",
                        "health_status": 0,
                        "activity_score": 82,
                        "activity_level": "正常",
                        "activity_trend": [78, 82, 75, 80, 82, 79, 82],
                        "feed_main_remain": 35,
                        "feed_aux_remain": 72,
                        "eating_status": "慢食",
                        "water_consumption": 6.8,
                        "drinking_status": "偏多"
                    }
                ]
            }
        }
    """
    try:
        # 获取参数
        enclosure_id = request.args.get('enclosure_id', type=int)
        report_date_str = request.args.get('date')
        page = request.args.get('page', 1, type=int)
        page_size = min(request.args.get('page_size', 20, type=int), 100)
        
        # 解析日期
        if report_date_str:
            report_date = datetime.strptime(report_date_str, '%Y-%m-%d').date()
        else:
            report_date = date.today()
        
        # 获取当前用户
        current_user = g.current_user
        client_id = current_user.client_id
        
        # 构建查询
        query = DailyReport.query.filter_by(
            client_id=client_id,
            report_date=report_date
        )
        
        if enclosure_id:
            query = query.filter_by(enclosure_id=enclosure_id)
        
        # 分页
        pagination = query.paginate(page=page, per_page=page_size, error_out=False)
        reports = pagination.items
        
        # 构建响应
        animals = []
        for report in reports:
            animals.append({
                'ear_tag': report.ear_tag,
                'gender': report.gender,
                'age': report.age,
                'health_status': report.health_status,
                'activity_score': report.activity_score,
                'activity_level': report.activity_level,
                'activity_trend': report.activity_trend,
                'feed_main_remain': report.feed_main_remain_percent,
                'feed_aux_remain': report.feed_aux_remain_percent,
                'eating_status': report.eating_status,
                'water_consumption': report.water_consumption_liters,
                'drinking_status': report.drinking_status
            })
        
        return jsonify({
            'code': 0,
            'data': {
                'date': report_date.isoformat(),
                'enclosure_id': enclosure_id,
                'animals': animals,
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total': pagination.total,
                    'pages': pagination.pages
                }
            }
        })
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取日报列表失败: {str(e)}'
        }), 500


# ==================== 2. 获取动物详情 ====================

@mp_reports_bp.route('/animals/<animal_id>/daily', methods=['GET'])
@login_required
def get_animal_daily(animal_id):
    """
    获取动物详情（含诊疗、饲养记录）
    
    Path参数:
        - animal_id: 动物耳标号
    
    Query参数:
        - date: 日期，格式 YYYY-MM-DD（可选，默认今天）
    
    Response:
        {
            "code": 0,
            "data": {
                "basic": {
                    "ear_tag": "LS-B2-025",
                    "gender": "雌性",
                    "age": "1岁",
                    "health_status": 0,
                    "enclosure": "B区2排3号"
                },
                "daily_data": {
                    "activity_score": 82,
                    "activity_level": "正常",
                    "activity_trend": [78, 82, 75, 80, 82, 79, 82],
                    "feed_main_remain": 35,
                    "feed_aux_remain": 72,
                    "eating_status": "慢食",
                    "water_consumption": 6.8,
                    "drinking_status": "偏多",
                    "alerts": []
                },
                "medical": {
                    "diagnosis": "肠炎",
                    "treatment_day": 3,
                    "medications": [
                        {"name": "消炎针", "dosage": "每天1次", "remain_days": 2},
                        {"name": "益生菌", "dosage": "拌料", "remain_days": 5}
                    ]
                },
                "care_records": {
                    "today": [...],
                    "tomorrow": [...]
                }
            }
        }
    """
    try:
        # 获取参数
        report_date_str = request.args.get('date')
        if report_date_str:
            report_date = datetime.strptime(report_date_str, '%Y-%m-%d').date()
        else:
            report_date = date.today()
        
        # 获取当前用户
        current_user = g.current_user
        client_id = current_user.client_id
        
        # 查询日报
        report = DailyReport.query.filter_by(
            client_id=client_id,
            animal_id=animal_id,
            report_date=report_date
        ).first()
        
        # 查询圈舍信息
        enclosure = None
        if report:
            enclosure = Enclosure.query.get(report.enclosure_id)
        
        # 查询诊疗记录
        medical = MedicalRecordV2.query.filter_by(
            client_id=client_id,
            animal_id=animal_id
        ).order_by(MedicalRecordV2.created_at.desc()).first()
        
        # 查询饲养记录
        today_records = CareRecord.query.filter(
            CareRecord.client_id == client_id,
            CareRecord.animal_id == animal_id,
            CareRecord.scheduled_date == report_date
        ).order_by(CareRecord.created_at.desc()).all()
        
        tomorrow = report_date + __import__('datetime').timedelta(days=1)
        tomorrow_records = CareRecord.query.filter(
            CareRecord.client_id == client_id,
            CareRecord.animal_id == animal_id,
            CareRecord.scheduled_date == tomorrow,
            CareRecord.status == CareRecordStatus.PENDING
        ).order_by(CareRecord.priority.desc(), CareRecord.created_at.desc()).all()
        
        # 构建响应
        response = {
            'basic': {
                'ear_tag': animal_id,
                'gender': report.gender if report else None,
                'age': report.age if report else None,
                'health_status': report.health_status if report else 0,
                'enclosure': enclosure.name if enclosure else None
            },
            'daily_data': {
                'activity_score': report.activity_score if report else None,
                'activity_level': report.activity_level if report else None,
                'activity_trend': report.activity_trend if report else [],
                'feed_main_remain': report.feed_main_remain_percent if report else None,
                'feed_aux_remain': report.feed_aux_remain_percent if report else None,
                'eating_status': report.eating_status if report else None,
                'water_consumption': report.water_consumption_liters if report else None,
                'drinking_status': report.drinking_status if report else None,
                'alerts': report.alerts_summary if report else []
            } if report else None,
            'medical': {
                'diagnosis': medical.diagnosis,
                'status': medical.status.value if medical else None,
                'treatment_day': medical.treatment_day,
                'medications': medical.medications if medical else []
            } if medical else None,
            'care_records': {
                'today': [r.to_dict() for r in today_records],
                'tomorrow': [r.to_dict() for r in tomorrow_records]
            }
        }
        
        return jsonify({
            'code': 0,
            'data': response
        })
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取动物详情失败: {str(e)}'
        }), 500


# ==================== 3. 添加饲养记录 ====================

@mp_reports_bp.route('/care-records', methods=['POST'])
@login_required
def create_care_record():
    """
    添加饲养记录
    
    Request Body:
        {
            "animal_id": "LS-B2-025",
            "record_type": "observation",
            "category": "粪便",
            "content": "粪便稍软（已送检）",
            "priority": 0,
            "voice_url": "",
            "images": [],
            "scheduled_date": "2026-03-23"  // 可选，待办任务用
        }
    
    Response:
        {
            "code": 0,
            "data": {
                "id": 123,
                "animal_id": "LS-B2-025",
                "record_type": "observation",
                "category": "粪便",
                "content": "粪便稍软（已送检）",
                "status": "completed",
                "created_at": "2026-03-22T10:30:00"
            }
        }
    """
    try:
        data = request.get_json()
        
        # 验证必填字段
        required_fields = ['animal_id', 'record_type', 'content']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'code': 400,
                    'message': f'缺少必填字段: {field}'
                }), 400
        
        # 获取当前用户
        current_user = g.current_user
        client_id = current_user.client_id
        
        # 解析scheduled_date
        scheduled_date = None
        if data.get('scheduled_date'):
            scheduled_date = datetime.strptime(data['scheduled_date'], '%Y-%m-%d').date()
        
        # 确定状态
        from models_algorithm import CareRecordType, CareRecordCategory, CareRecordStatus
        
        status = CareRecordStatus.COMPLETED
        if scheduled_date and scheduled_date > date.today():
            status = CareRecordStatus.PENDING
        
        # 创建记录
        record = CareRecord(
            client_id=client_id,
            animal_id=data['animal_id'],
            record_type=CareRecordType(data['record_type']),
            category=CareRecordCategory(data['category']) if data.get('category') else None,
            content=data['content'],
            status=status,
            priority=data.get('priority', 0),
            voice_url=data.get('voice_url', ''),
            images=data.get('images', []),
            operator_id=current_user.id,
            operator_name=current_user.nickname or current_user.username,
            scheduled_date=scheduled_date,
            completed_at=datetime.utcnow() if status == CareRecordStatus.COMPLETED else None
        )
        
        from models_v2 import db
        db.session.add(record)
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'data': record.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'添加饲养记录失败: {str(e)}'
        }), 500


# ==================== 辅助接口 ====================

@mp_reports_bp.route('/daily-reports/dates', methods=['GET'])
@login_required
def get_available_dates():
    """
    获取有日报数据的日期列表
    
    Query参数:
        - enclosure_id: 圈舍ID（可选）
        - days: 最近多少天（可选，默认30）
    
    Response:
        {
            "code": 0,
            "data": {
                "dates": ["2026-03-22", "2026-03-21", ...]
            }
        }
    """
    try:
        enclosure_id = request.args.get('enclosure_id', type=int)
        days = request.args.get('days', 30, type=int)
        
        current_user = g.current_user
        client_id = current_user.client_id
        
        # 查询有数据的日期
        from sqlalchemy import func
        
        query = DailyReport.query.filter(
            DailyReport.client_id == client_id,
            DailyReport.report_date >= date.today() - __import__('datetime').timedelta(days=days)
        )
        
        if enclosure_id:
            query = query.filter_by(enclosure_id=enclosure_id)
        
        dates = query.with_entities(DailyReport.report_date).distinct().order_by(DailyReport.report_date.desc()).all()
        
        return jsonify({
            'code': 0,
            'data': {
                'dates': [d[0].isoformat() for d in dates]
            }
        })
        
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'获取日期列表失败: {str(e)}'
        }), 500
