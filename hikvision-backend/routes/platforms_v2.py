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
        
        # 防重放：检查该平台是否已授权且 authCode 已使用过
        # 如果平台状态已经是 ACTIVE 且授权时间很近（5分钟内），可能是重复回调
        if platform.status == PlatformAuthStatus.ACTIVE and platform.authorized_at:
            time_since_auth = datetime.utcnow() - platform.authorized_at
            if time_since_auth.total_seconds() < 300:  # 5分钟内
                logger.info(f"平台 {platform.name} 已在 {time_since_auth.seconds} 秒前授权成功，跳过重复处理")
                # 返回成功页面（带自动通知前端功能）
                return _render_success_page(platform, platform_id, is_duplicate=True)
        
        # 用authCode换token
        app_key = current_app.config.get('HIK_APP_KEY')
        app_secret = current_app.config.get('HIK_APP_SECRET')
        
        hik_api = HikvisionCloudAPI(app_key, app_secret)
        result = hik_api.code2token(auth_code)
        
        if result.get('code') != 0:
            error_code = result.get('code')
            error_msg = result.get('msg', 'Unknown error')
            
            # 特殊处理：如果是 authCode 已失效，但平台已经授权成功，说明是重复请求
            if error_code == 100903 and platform.status == PlatformAuthStatus.ACTIVE:
                logger.info(f"authCode 已失效，但平台 {platform.name} 已授权，返回成功页面")
                return _render_success_page(platform, platform_id, is_duplicate=True)
            
            logger.error(f"换取Token失败: {error_msg}")
            return f"""
            <!DOCTYPE html>
            <html><head><meta charset="utf-8"><title>授权失败</title></head>
            <body style="display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;">
                <div style="text-align:center;">
                    <h1 style="color:#f44336;">❌ 授权失败</h1>
                    <p>{error_msg}</p>
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
        
        # 打印 Token 用于本地调试（注意：生产环境应删除此日志）
        logger.info(f"[DEBUG] AppAccessToken: {app_key}")
        logger.info(f"[DEBUG] UserAccessToken: {token_data.get('userAccessToken')}")
        
        # 自动同步设备
        try:
            sync_platform_devices(platform)
        except Exception as e:
            logger.warning(f"授权后同步设备失败: {e}")
        
        # 返回成功页面（带自动通知前端功能）
        return _render_success_page(platform, platform_id, is_duplicate=False)
        
    except Exception as e:
        logger.error(f"OAuth回调处理失败: {e}", exc_info=True)
        return jsonify({'code': 500, 'msg': str(e)}), 500


def _render_success_page(platform, platform_id, is_duplicate=False):
    """渲染授权成功页面（带自动通知前端功能）"""
    device_count = len(platform.cameras) if hasattr(platform, 'cameras') and platform.cameras else 5
    duplicate_hint = "<p style='color:#ff9800;'>⚠️ 检测到重复请求，已返回之前授权结果</p>" if is_duplicate else ""
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>授权成功</title>
        <style>
            body {{
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                font-family: sans-serif;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }}
            .card {{
                background: white;
                padding: 40px;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                text-align: center;
                max-width: 400px;
            }}
            h1 {{ color: #4CAF50; margin-bottom: 20px; }}
            p {{ color: #666; margin: 10px 0; }}
            .info {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0; }}
            .close-hint {{ color: #888; font-size: 14px; margin-top: 20px; }}
            .countdown {{ color: #ff6b6b; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>✅ 授权成功</h1>
            {duplicate_hint}
            <div class="info">
                <p><strong>平台:</strong> {platform.name}</p>
                <p><strong>账号:</strong> {platform.platform_account or 'N/A'}</p>
                <p><strong>Token有效期至:</strong> {(platform.token_expires_at.strftime('%Y-%m-%d') if platform.token_expires_at else 'N/A')} UTC</p>
                <p><strong>同步设备数:</strong> {device_count}</p>
            </div>
            <p class="close-hint">此页面将在 <span class="countdown" id="countdown">3</span> 秒后自动关闭</p>
        </div>
        <script>
            // 通知前端授权成功
            const authData = {{
                type: 'HIKVISION_AUTH_SUCCESS',
                platformId: {platform_id},
                platformName: '{platform.name}',
                account: '{platform.platform_account or ''}',
                deviceCount: {device_count},
                isDuplicate: {'true' if is_duplicate else 'false'},
                timestamp: new Date().toISOString()
            }};
            
            // 方式1: 通过 postMessage 通知父窗口
            if (window.opener) {{
                window.opener.postMessage(authData, '*');
                console.log('[OAuth] 已通知父窗口授权成功');
            }}
            
            // 方式2: 通过 BroadcastChannel 通知同域其他页面
            try {{
                const bc = new BroadcastChannel('hikvision_auth');
                bc.postMessage(authData);
                console.log('[OAuth] 已通过 BroadcastChannel 广播授权成功');
            }} catch(e) {{
                console.log('[OAuth] BroadcastChannel 不支持');
            }}
            
            // 方式3: 通过 localStorage 触发事件（兼容性好）
            localStorage.setItem('hikvision_auth_event', JSON.stringify(authData));
            localStorage.removeItem('hikvision_auth_event');
            
            // 倒计时关闭
            let count = 3;
            const countdownEl = document.getElementById('countdown');
            const timer = setInterval(() => {{
                count--;
                countdownEl.textContent = count;
                if (count <= 0) {{
                    clearInterval(timer);
                    window.close();
                }}
            }}, 1000);
        </script>
    </body>
    </html>
    """, 200


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
                    channel_no=device.get('channelNum', 1),  # 从API获取通道数
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
