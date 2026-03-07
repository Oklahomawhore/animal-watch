#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2 层级管理路由 - Factory / Area / Enclosure
"""

import logging
from flask import Blueprint, request, jsonify, g

from models_v2 import db, Factory, Area, Enclosure, UserRole, UserStatus
from utils.auth import login_required, admin_required, manager_required

logger = logging.getLogger(__name__)

# 创建蓝图
factories_bp = Blueprint('factories_v2', __name__)
areas_bp = Blueprint('areas_v2', __name__)
enclosures_bp = Blueprint('enclosures_v2', __name__)


# ========== Factory 厂区管理 ==========

@factories_bp.route('', methods=['GET'])
@login_required
def list_factories():
    """获取厂区列表"""
    try:
        factories = Factory.query.filter_by(
            client_id=g.client_id,
            status=UserStatus.ACTIVE
        ).order_by(Factory.created_at.desc()).all()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': [f.to_dict() for f in factories]
        })
        
    except Exception as e:
        logger.error(f"获取厂区列表失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@factories_bp.route('', methods=['POST'])
@manager_required
def create_factory():
    """创建厂区（管理员/厂长）"""
    try:
        data = request.get_json() or {}
        name = data.get('name')
        code = data.get('code')
        
        if not name or not code:
            return jsonify({'code': 400, 'msg': 'Missing name or code'}), 400
        
        # 检查code是否重复
        if Factory.query.filter_by(client_id=g.client_id, code=code).first():
            return jsonify({'code': 400, 'msg': 'Factory code already exists'}), 400
        
        factory = Factory(
            client_id=g.client_id,
            name=name,
            code=code,
            address=data.get('address'),
            description=data.get('description'),
            location_lat=data.get('locationLat'),
            location_lng=data.get('locationLng')
        )
        
        db.session.add(factory)
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': factory.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"创建厂区失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500


@factories_bp.route('/<int:factory_id>', methods=['GET'])
@login_required
def get_factory(factory_id):
    """获取厂区详情（含区域列表）"""
    try:
        factory = Factory.query.filter_by(
            id=factory_id,
            client_id=g.client_id
        ).first()
        
        if not factory:
            return jsonify({'code': 404, 'msg': 'Factory not found'}), 404
        
        result = factory.to_dict()
        result['areas'] = [a.to_dict() for a in factory.areas if a.status == UserStatus.ACTIVE]
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"获取厂区详情失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@factories_bp.route('/<int:factory_id>', methods=['PUT'])
@manager_required
def update_factory(factory_id):
    """更新厂区信息"""
    try:
        factory = Factory.query.filter_by(
            id=factory_id,
            client_id=g.client_id
        ).first()
        
        if not factory:
            return jsonify({'code': 404, 'msg': 'Factory not found'}), 404
        
        data = request.get_json() or {}
        
        if 'name' in data:
            factory.name = data['name']
        if 'address' in data:
            factory.address = data['address']
        if 'description' in data:
            factory.description = data['description']
        if 'locationLat' in data:
            factory.location_lat = data['locationLat']
        if 'locationLng' in data:
            factory.location_lng = data['locationLng']
        
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': factory.to_dict()
        })
        
    except Exception as e:
        logger.error(f"更新厂区失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500


@factories_bp.route('/<int:factory_id>', methods=['DELETE'])
@admin_required
def delete_factory(factory_id):
    """删除厂区（仅管理员）"""
    try:
        factory = Factory.query.filter_by(
            id=factory_id,
            client_id=g.client_id
        ).first()
        
        if not factory:
            return jsonify({'code': 404, 'msg': 'Factory not found'}), 404
        
        # 软删除
        factory.status = UserStatus.INACTIVE
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'msg': 'Factory deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"删除厂区失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500


# ========== Area 区域管理 ==========

@areas_bp.route('', methods=['GET'])
@login_required
def list_areas():
    """获取区域列表"""
    try:
        factory_id = request.args.get('factoryId', type=int)
        
        query = Area.query.filter_by(
            client_id=g.client_id,
            status=UserStatus.ACTIVE
        )
        
        if factory_id:
            query = query.filter_by(factory_id=factory_id)
        
        areas = query.order_by(Area.created_at.desc()).all()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': [a.to_dict() for a in areas]
        })
        
    except Exception as e:
        logger.error(f"获取区域列表失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@areas_bp.route('', methods=['POST'])
@manager_required
def create_area():
    """创建区域"""
    try:
        data = request.get_json() or {}
        factory_id = data.get('factoryId')
        name = data.get('name')
        code = data.get('code')
        
        if not factory_id or not name or not code:
            return jsonify({'code': 400, 'msg': 'Missing factoryId, name or code'}), 400
        
        # 验证厂区存在
        factory = Factory.query.filter_by(id=factory_id, client_id=g.client_id).first()
        if not factory:
            return jsonify({'code': 404, 'msg': 'Factory not found'}), 404
        
        # 检查code是否重复
        if Area.query.filter_by(factory_id=factory_id, code=code).first():
            return jsonify({'code': 400, 'msg': 'Area code already exists in this factory'}), 400
        
        area = Area(
            client_id=g.client_id,
            factory_id=factory_id,
            name=name,
            code=code,
            description=data.get('description')
        )
        
        db.session.add(area)
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': area.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"创建区域失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500


@areas_bp.route('/<int:area_id>', methods=['GET'])
@login_required
def get_area(area_id):
    """获取区域详情（含圈列表）"""
    try:
        area = Area.query.filter_by(
            id=area_id,
            client_id=g.client_id
        ).first()
        
        if not area:
            return jsonify({'code': 404, 'msg': 'Area not found'}), 404
        
        result = area.to_dict()
        result['enclosures'] = [e.to_dict() for e in area.enclosures if e.status == UserStatus.ACTIVE]
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"获取区域详情失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@areas_bp.route('/<int:area_id>', methods=['PUT'])
@manager_required
def update_area(area_id):
    """更新区域信息"""
    try:
        area = Area.query.filter_by(
            id=area_id,
            client_id=g.client_id
        ).first()
        
        if not area:
            return jsonify({'code': 404, 'msg': 'Area not found'}), 404
        
        data = request.get_json() or {}
        
        if 'name' in data:
            area.name = data['name']
        if 'description' in data:
            area.description = data['description']
        
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': area.to_dict()
        })
        
    except Exception as e:
        logger.error(f"更新区域失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500


@areas_bp.route('/<int:area_id>', methods=['DELETE'])
@admin_required
def delete_area(area_id):
    """删除区域（仅管理员）"""
    try:
        area = Area.query.filter_by(
            id=area_id,
            client_id=g.client_id
        ).first()
        
        if not area:
            return jsonify({'code': 404, 'msg': 'Area not found'}), 404
        
        area.status = UserStatus.INACTIVE
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'msg': 'Area deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"删除区域失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500


# ========== Enclosure 圈管理 ==========

@enclosures_bp.route('', methods=['GET'])
@login_required
def list_enclosures():
    """获取圈列表"""
    try:
        factory_id = request.args.get('factoryId', type=int)
        area_id = request.args.get('areaId', type=int)
        
        query = Enclosure.query.filter_by(
            client_id=g.client_id,
            status=UserStatus.ACTIVE
        )
        
        if factory_id:
            query = query.filter_by(factory_id=factory_id)
        if area_id:
            query = query.filter_by(area_id=area_id)
        
        enclosures = query.order_by(Enclosure.created_at.desc()).all()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': [e.to_dict() for e in enclosures]
        })
        
    except Exception as e:
        logger.error(f"获取圈列表失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@enclosures_bp.route('', methods=['POST'])
@manager_required
def create_enclosure():
    """创建圈"""
    try:
        data = request.get_json() or {}
        factory_id = data.get('factoryId')
        area_id = data.get('areaId')
        name = data.get('name')
        code = data.get('code')
        
        if not factory_id or not area_id or not name or not code:
            return jsonify({'code': 400, 'msg': 'Missing required fields'}), 400
        
        # 验证区域存在
        area = Area.query.filter_by(id=area_id, factory_id=factory_id, client_id=g.client_id).first()
        if not area:
            return jsonify({'code': 404, 'msg': 'Area not found'}), 404
        
        # 检查code是否重复
        if Enclosure.query.filter_by(area_id=area_id, code=code).first():
            return jsonify({'code': 400, 'msg': 'Enclosure code already exists in this area'}), 400
        
        enclosure = Enclosure(
            client_id=g.client_id,
            factory_id=factory_id,
            area_id=area_id,
            name=name,
            code=code,
            description=data.get('description'),
            animal_count=data.get('animalCount', 0),
            animal_tags=data.get('animalTags', []),
            location_x=data.get('locationX'),
            location_y=data.get('locationY')
        )
        
        db.session.add(enclosure)
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': enclosure.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"创建圈失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500


@enclosures_bp.route('/<int:enclosure_id>', methods=['GET'])
@login_required
def get_enclosure(enclosure_id):
    """获取圈详情（含摄像头、个体信息）"""
    try:
        enclosure = Enclosure.query.filter_by(
            id=enclosure_id,
            client_id=g.client_id
        ).first()
        
        if not enclosure:
            return jsonify({'code': 404, 'msg': 'Enclosure not found'}), 404
        
        result = enclosure.to_dict()
        result['cameras'] = [c.to_dict() for c in enclosure.cameras]
        result['area'] = enclosure.area.to_dict() if enclosure.area else None
        result['factory'] = enclosure.area.factory.to_dict() if enclosure.area and enclosure.area.factory else None
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"获取圈详情失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@enclosures_bp.route('/<int:enclosure_id>', methods=['PUT'])
@manager_required
def update_enclosure(enclosure_id):
    """更新圈信息"""
    try:
        enclosure = Enclosure.query.filter_by(
            id=enclosure_id,
            client_id=g.client_id
        ).first()
        
        if not enclosure:
            return jsonify({'code': 404, 'msg': 'Enclosure not found'}), 404
        
        data = request.get_json() or {}
        
        if 'name' in data:
            enclosure.name = data['name']
        if 'description' in data:
            enclosure.description = data['description']
        if 'animalCount' in data:
            enclosure.animal_count = data['animalCount']
        if 'animalTags' in data:
            enclosure.animal_tags = data['animalTags']
        if 'locationX' in data:
            enclosure.location_x = data['locationX']
        if 'locationY' in data:
            enclosure.location_y = data['locationY']
        
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': enclosure.to_dict()
        })
        
    except Exception as e:
        logger.error(f"更新圈失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500


@enclosures_bp.route('/<int:enclosure_id>', methods=['DELETE'])
@admin_required
def delete_enclosure(enclosure_id):
    """删除圈（仅管理员）"""
    try:
        enclosure = Enclosure.query.filter_by(
            id=enclosure_id,
            client_id=g.client_id
        ).first()
        
        if not enclosure:
            return jsonify({'code': 404, 'msg': 'Enclosure not found'}), 404
        
        enclosure.status = UserStatus.INACTIVE
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'msg': 'Enclosure deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"删除圈失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500
