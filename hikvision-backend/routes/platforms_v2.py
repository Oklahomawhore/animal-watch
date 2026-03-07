#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2 摄像头平台管理 - 海康互联授权与设备同步
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, g, current_app

from models_v2 import db, CameraPlatform, Camera, PlatformAuthStatus, CameraProvider, CameraStatus
from utils.auth import login_required, admin_required
from services.hikcloud import HikvisionCloudAPI

logger = logging.getLogger(__name__)

platforms_bp = Blueprint('platforms_v2', __name__)


@platforms_bp.route('', methods=['GET'])
@login_required
def list_platforms():
    """获取平台授权列表"""
    try:
        platforms = CameraPlatform.query.filter_by(
            client_id=g.client_id
        ).order_by(CameraPlatform.created_at.desc()).all()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': [p.to_dict() for p in platforms]
        })
        
    except Exception as e:
        logger.error(f"获取平台列表失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@platforms_bp.route('', methods=['POST'])
@admin_required
def create_platform():
    """
    添加摄像头平台（仅管理员）
    
    请求参数:
        name: 平台名称（如"总部海康账号"）
        provider: 厂商 (hikvision/dahua/uniview)
    """
    try:
        data = request.get_json() or {}
        name = data.get('name')
        provider = data.get('provider', 'hikvision')
        
        if not name:
            return jsonify({'code': 400, 'msg': 'Missing platform name'}), 400
        
        platform = CameraPlatform(
            client_id=g.client_id,
            name=name,
            provider=CameraProvider(provider),
            status=PlatformAuthStatus.REVOKED  # 初始未授权
        )
        
        db.session.add(platform)
        db.session.commit()
        
        logger.info(f"平台 {name} 创建成功")
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': platform.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"创建平台失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500


@platforms_bp.route('/<int:platform_id>/oauth-callback', methods=['GET'])
def oauth_callback(platform_id):
    """
    海康OAuth回调处理
    
    海康授权成功后重定向到: {redirectUrl}?authCode=xxx&state=xxx
    state格式: {client_id}|{user_id}
    """
    try:
        auth_code = request.args.get('authCode')
        state = request.args.get('state', '')
        
        if not auth_code:
            return jsonify({'code': 400, 'msg': 'Missing authCode'}), 400
        
        # 解析state
        parts = state.split('|')
        if len(parts) != 2:
            return jsonify({'code': 400, 'msg': 'Invalid state format'}), 400
        
        client_id, user_id = parts[0], parts[1]
        
        # 获取平台
        platform = CameraPlatform.query.filter_by(
            id=platform_id,
            client_id=client_id
        ).first()
        
        if not platform:
            return jsonify({'code': 404, 'msg': 'Platform not found'}), 404
        
        # 用authCode换token
        app_key = current_app.config.get('HIK_APP_KEY')
        app_secret = current_app.config.get('HIK_APP_SECRET')
        
        hik_api = HikvisionCloudAPI(app_key, app_secret)
        result = hik_api.code2token(auth_code)
        
        if result.get('code') != 0:
            logger.error(f"换取Token失败: {result.get('msg')}")
            return f"""
            <!DOCTYPE html>
            <html><head><meta charset="utf-8"><title>授权失败</title></head>
            <body style="display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;">
                <div style="text-align:center;">
                    <h1 style="color:#f44336;">❌ 授权失败</h1>
                    <p>{result.get('msg', 'Unknown error')}</p>
                </div>
            </body></html>
            """, 400
        
        token_data = result['data']
        
        # 保存授权信息
        platform.access_token = token_data['userAccessToken']
        platform.refresh_token = token_data.get('refreshUserToken')
        platform.token_expires_at = datetime.utcnow() + timedelta(days=30)
        platform.platform_account = token_data.get('accountNo')
        platform.platform_user_id = token_data.get('personNo')
        platform.authorized_by = user_id
        platform.authorized_at = datetime.utcnow()
        platform.status = PlatformAuthStatus.ACTIVE
        
        db.session.commit()
        
        logger.info(f"平台 {platform.name} 授权成功")
        
        # 自动同步设备
        try:
            sync_platform_devices(platform)
        except Exception as e:
            logger.warning(f"授权后同步设备失败: {e}")
        
        # 返回成功页面
        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"><title>授权成功</title></head>
        <body style="display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;">
            <div style="text-align:center;">
                <h1 style="color:#4CAF50;">✅ 授权成功</h1>
                <p>平台: {platform.name}</p>
                <p>账号: {platform.platform_account or 'N/A'}</p>
                <p>Token有效期至: {platform.token_expires_at.strftime('%Y-%m-%d')} UTC</p>
                <p style="color:#888;">此页面可以关闭</p>
            </div>
        </body>
        </html>
        """, 200
        
    except Exception as e:
        logger.error(f"OAuth回调处理失败: {e}", exc_info=True)
        return jsonify({'code': 500, 'msg': str(e)}), 500


def sync_platform_devices(platform):
    """同步平台设备列表"""
    from models_v2 import Enclosure
    
    app_key = current_app.config.get('HIK_APP_KEY')
    app_secret = current_app.config.get('HIK_APP_SECRET')
    
    hik_api = HikvisionCloudAPI(app_key, app_secret)
    hik_api.set_user_token(platform.access_token)
    
    # 获取设备列表
    page = 1
    total_synced = 0
    
    while True:
        result = hik_api._request('GET', '/device/v1/page', params={'page': page, 'size': 50})
        
        if result.get('code') != 0:
            logger.error(f"获取设备列表失败: {result.get('msg')}")
            break
        
        devices = result.get('data', [])
        if not devices:
            break
        
        for device in devices:
            device_serial = device.get('deviceSerial')
            device_name = device.get('name')
            
            # 检查是否已存在
            existing = Camera.query.filter_by(
                client_id=platform.client_id,
                device_serial=device_serial
            ).first()
            
            if existing:
                # 更新状态
                existing.status = CameraStatus.ONLINE if device.get('status') == 1 else CameraStatus.OFFLINE
                existing.name = device_name
            else:
                # 创建新摄像头
                # 尝试自动匹配圈
                enclosure = Enclosure.query.filter_by(
                    client_id=platform.client_id,
                    name=device_name
                ).first()
                
                unique_name = f"{platform.provider.value}_{platform.platform_account or 'default'}_{device_name or device_serial}"
                
                camera = Camera(
                    client_id=platform.client_id,
                    platform_id=platform.id,
                    enclosure_id=enclosure.id if enclosure else None,
                    platform_device_id=device.get('deviceSerial'),
                    device_serial=device_serial,
                    unique_name=unique_name,
                    name=device_name,
                    status=CameraStatus.ONLINE if device.get('status') == 1 else CameraStatus.OFFLINE,
                    is_auto_imported=bool(enclosure)
                )
                db.session.add(camera)
            
            total_synced += 1
        
        # 检查是否还有下一页
        if len(devices) < 50:
            break
        page += 1
    
    db.session.commit()
    logger.info(f"平台 {platform.name} 同步了 {total_synced} 个设备")


@platforms_bp.route('/<int:platform_id>/sync', methods=['POST'])
@admin_required
def sync_devices(platform_id):
    """手动同步设备列表"""
    try:
        platform = CameraPlatform.query.filter_by(
            id=platform_id,
            client_id=g.client_id
        ).first()
        
        if not platform:
            return jsonify({'code': 404, 'msg': 'Platform not found'}), 404
        
        if platform.status != PlatformAuthStatus.ACTIVE:
            return jsonify({'code': 400, 'msg': 'Platform not authorized'}), 400
        
        sync_platform_devices(platform)
        
        # 统计
        camera_count = Camera.query.filter_by(platform_id=platform_id).count()
        bound_count = Camera.query.filter_by(platform_id=platform_id).filter(Camera.enclosure_id.isnot(None)).count()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'totalCameras': camera_count,
                'boundCameras': bound_count,
                'unboundCameras': camera_count - bound_count
            }
        })
        
    except Exception as e:
        logger.error(f"同步设备失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@platforms_bp.route('/<int:platform_id>', methods=['DELETE'])
@admin_required
def delete_platform(platform_id):
    """删除平台授权（同时删除关联摄像头）"""
    try:
        platform = CameraPlatform.query.filter_by(
            id=platform_id,
            client_id=g.client_id
        ).first()
        
        if not platform:
            return jsonify({'code': 404, 'msg': 'Platform not found'}), 404
        
        # 删除关联摄像头
        Camera.query.filter_by(platform_id=platform_id).delete()
        
        db.session.delete(platform)
        db.session.commit()
        
        logger.info(f"平台 {platform.name} 被删除")
        
        return jsonify({
            'code': 0,
            'msg': 'Platform deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"删除平台失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500
