#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2 摄像头管理路由 - 绑定、解绑、一键导入
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, g

from models_v2 import (
    db, Camera, Enclosure, UserStatus, CameraStatus, CameraType, CameraProvider
)
from utils.auth import login_required, manager_required

logger = logging.getLogger(__name__)

cameras_bp = Blueprint('cameras_v2', __name__)


@cameras_bp.route('', methods=['GET'])
@login_required
def list_cameras():
    """
    获取摄像头列表（带权限过滤）
    
    查询参数:
        enclosureId: 按圈筛选
        platformId: 按平台筛选
        status: 按状态筛选
        bound: true/false 是否已绑定
    """
    try:
        enclosure_id = request.args.get('enclosureId', type=int)
        platform_id = request.args.get('platformId', type=int)
        status = request.args.get('status')
        bound = request.args.get('bound')
        
        # 基础查询（带client_id过滤）
        query = Camera.query.filter_by(client_id=g.client_id)
        
        # 应用筛选
        if enclosure_id:
            query = query.filter_by(enclosure_id=enclosure_id)
        if platform_id:
            query = query.filter_by(platform_id=platform_id)
        if status:
            query = query.filter_by(status=CameraStatus(status))
        if bound is not None:
            if bound.lower() == 'true':
                query = query.filter(Camera.enclosure_id.isnot(None))
            else:
                query = query.filter(Camera.enclosure_id.is_(None))
        
        # 权限过滤（饲养员只能看自己有权限的圈）
        if g.user.role.value == 'breeder':
            from models_v2 import VisibilityLevel
            
            if g.user.visibility_level == VisibilityLevel.ENCLOSURE:
                query = query.filter(Camera.enclosure_id.in_(g.user.visibility_scope_ids or []))
            elif g.user.visibility_level == VisibilityLevel.AREA:
                from models_v2 import Enclosure
                enclosures = Enclosure.query.filter(
                    Enclosure.area_id.in_(g.user.visibility_scope_ids or [])
                ).all()
                enclosure_ids = [e.id for e in enclosures]
                query = query.filter(Camera.enclosure_id.in_(enclosure_ids))
            elif g.user.visibility_level == VisibilityLevel.FACTORY:
                from models_v2 import Enclosure, Area
                areas = Area.query.filter(
                    Area.factory_id.in_(g.user.visibility_scope_ids or [])
                ).all()
                area_ids = [a.id for a in areas]
                enclosures = Enclosure.query.filter(Enclosure.area_id.in_(area_ids)).all()
                enclosure_ids = [e.id for e in enclosures]
                query = query.filter(Camera.enclosure_id.in_(enclosure_ids))
        
        # 分页
        page = request.args.get('page', 1, type=int)
        size = request.args.get('size', 20, type=int)
        
        pagination = query.order_by(Camera.created_at.desc()).paginate(
            page=page, per_page=size, error_out=False
        )
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'items': [c.to_dict() for c in pagination.items],
                'total': pagination.total,
                'page': page,
                'size': size
            }
        })
        
    except Exception as e:
        logger.error(f"获取摄像头列表失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@cameras_bp.route('/<int:camera_id>', methods=['GET'])
@login_required
def get_camera(camera_id):
    """获取摄像头详情"""
    try:
        camera = Camera.query.filter_by(
            id=camera_id,
            client_id=g.client_id
        ).first()
        
        if not camera:
            return jsonify({'code': 404, 'msg': 'Camera not found'}), 404
        
        # 权限检查
        if g.user.role.value == 'breeder' and camera.enclosure_id:
            # 检查是否有权限看这个圈
            from models_v2 import VisibilityLevel
            if g.user.visibility_level == VisibilityLevel.ENCLOSURE:
                if camera.enclosure_id not in (g.user.visibility_scope_ids or []):
                    return jsonify({'code': 403, 'msg': 'Permission denied'}), 403
        
        result = camera.to_dict()
        if camera.enclosure:
            result['enclosure'] = camera.enclosure.to_dict()
            if camera.enclosure.area:
                result['area'] = camera.enclosure.area.to_dict()
                if camera.enclosure.area.factory:
                    result['factory'] = camera.enclosure.area.factory.to_dict()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': result
        })
        
    except Exception as e:
        logger.error(f"获取摄像头详情失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@cameras_bp.route('/<int:camera_id>/bind', methods=['POST'])
@manager_required
def bind_camera(camera_id):
    """
    绑定摄像头到圈
    
    请求参数:
        enclosureId: 圈ID
        cameraType: 摄像头类型 (enclosure/feeding/environment)
        positionInEnclosure: 圈内位置 (front/back/left/right/top)
    """
    try:
        camera = Camera.query.filter_by(
            id=camera_id,
            client_id=g.client_id
        ).first()
        
        if not camera:
            return jsonify({'code': 404, 'msg': 'Camera not found'}), 404
        
        data = request.get_json() or {}
        enclosure_id = data.get('enclosureId')
        
        if not enclosure_id:
            return jsonify({'code': 400, 'msg': 'Missing enclosureId'}), 400
        
        # 验证圈存在
        enclosure = Enclosure.query.filter_by(
            id=enclosure_id,
            client_id=g.client_id
        ).first()
        
        if not enclosure:
            return jsonify({'code': 404, 'msg': 'Enclosure not found'}), 404
        
        # 更新绑定
        camera.enclosure_id = enclosure_id
        camera.camera_type = CameraType(data.get('cameraType', 'enclosure'))
        camera.position_in_enclosure = data.get('positionInEnclosure')
        camera.status = CameraStatus.ONLINE
        
        db.session.commit()
        
        logger.info(f"摄像头 {camera.unique_name} 绑定到圈 {enclosure.name}")
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': camera.to_dict()
        })
        
    except Exception as e:
        logger.error(f"绑定摄像头失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500


@cameras_bp.route('/<int:camera_id>/unbind', methods=['POST'])
@manager_required
def unbind_camera(camera_id):
    """解绑摄像头"""
    try:
        camera = Camera.query.filter_by(
            id=camera_id,
            client_id=g.client_id
        ).first()
        
        if not camera:
            return jsonify({'code': 404, 'msg': 'Camera not found'}), 404
        
        camera.enclosure_id = None
        camera.camera_type = CameraType.ENCLOSURE
        camera.position_in_enclosure = None
        camera.status = CameraStatus.UNBOUND
        
        db.session.commit()
        
        logger.info(f"摄像头 {camera.unique_name} 已解绑")
        
        return jsonify({
            'code': 0,
            'msg': 'Camera unbound successfully',
            'data': camera.to_dict()
        })
        
    except Exception as e:
        logger.error(f"解绑摄像头失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500


@cameras_bp.route('/auto-import', methods=['POST'])
@manager_required
def auto_import_cameras():
    """
    一键导入摄像头（根据名字自动匹配圈）
    
    请求参数:
        platformId: 平台ID（可选，默认全部平台）
        dryRun: true/false（默认false，true时只返回预览不执行）
    
    匹配规则: 摄像头名 == 圈名
    """
    try:
        data = request.get_json() or {}
        platform_id = data.get('platformId')
        dry_run = data.get('dryRun', False)
        
        # 获取未绑定的摄像头
        query = Camera.query.filter_by(
            client_id=g.client_id,
            enclosure_id=None
        )
        if platform_id:
            query = query.filter_by(platform_id=platform_id)
        
        unbound_cameras = query.all()
        
        # 获取所有圈
        enclosures = Enclosure.query.filter_by(
            client_id=g.client_id,
            status=UserStatus.ACTIVE
        ).all()
        
        enclosure_map = {e.name: e for e in enclosures}
        
        matched = []
        unmatched = []
        
        for camera in unbound_cameras:
            if camera.name in enclosure_map:
                enclosure = enclosure_map[camera.name]
                matched.append({
                    'camera': camera.to_dict(),
                    'enclosure': enclosure.to_dict()
                })
                
                if not dry_run:
                    camera.enclosure_id = enclosure.id
                    camera.status = CameraStatus.ONLINE
                    camera.is_auto_imported = True
            else:
                unmatched.append(camera.to_dict())
        
        if not dry_run:
            db.session.commit()
            logger.info(f"一键导入了 {len(matched)} 个摄像头")
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'dryRun': dry_run,
                'matchedCount': len(matched),
                'unmatchedCount': len(unmatched),
                'matched': matched,
                'unmatched': unmatched
            }
        })
        
    except Exception as e:
        logger.error(f"一键导入失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500


@cameras_bp.route('/<int:camera_id>/snapshot', methods=['POST'])
@manager_required
def capture_snapshot(camera_id):
    """
    手动抓取摄像头快照
    
    返回:
        snapshotUrl: 快照URL
    """
    try:
        from flask import current_app
        from services.hikcloud import HikvisionCloudAPI
        
        camera = Camera.query.filter_by(
            id=camera_id,
            client_id=g.client_id
        ).first()
        
        if not camera:
            return jsonify({'code': 404, 'msg': 'Camera not found'}), 404
        
        # 获取平台授权
        from models_v2 import CameraPlatform, PlatformAuthStatus
        platform = CameraPlatform.query.get(camera.platform_id)
        
        if not platform or platform.status != PlatformAuthStatus.ACTIVE:
            return jsonify({'code': 400, 'msg': 'Platform not authorized'}), 400
        
        # 调用海康API抓拍
        app_key = current_app.config.get('HIK_APP_KEY')
        app_secret = current_app.config.get('HIK_APP_SECRET')
        
        hik_api = HikvisionCloudAPI(app_key, app_secret)
        hik_api.set_user_token(platform.access_token)
        
        pic_url = hik_api.capture_device(camera.device_serial, camera.channel_no)
        
        if pic_url:
            camera.snapshot_url = pic_url
            camera.snapshot_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'code': 0,
                'msg': 'success',
                'data': {
                    'snapshotUrl': pic_url,
                    'snapshotAt': camera.snapshot_at.isoformat()
                }
            })
        else:
            return jsonify({'code': 500, 'msg': 'Failed to capture snapshot'}), 500
        
    except Exception as e:
        logger.error(f"抓取快照失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500
