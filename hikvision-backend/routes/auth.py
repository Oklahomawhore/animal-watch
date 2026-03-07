#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户认证路由
海康互联 User Access Token 获取与刷新

授权流程（内部自建应用）:
1. 前端/用户访问 /api/auth/login-url 获取 OAuth 登录链接
2. 用户在海康页面输入账号密码完成授权
3. 海康回调 /api/auth/oauth-callback?authCode=xxx
4. 后端用 authCode 换取 UserAccessToken（有效期30天）
5. 后续通过 /api/auth/refresh-token 刷新 Token
"""

import logging
import uuid
from datetime import datetime, timedelta
from urllib.parse import quote
from flask import Blueprint, request, jsonify, current_app, redirect
from models import db, UserAuth
from services.hikcloud import HikvisionCloudAPI

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

# UserAccessToken 有效期为30天（海康文档规定）
USER_TOKEN_EXPIRES_DAYS = 30


def get_hik_api():
    """获取海康 API 实例"""
    app_key = current_app.config.get('HIK_APP_KEY')
    app_secret = current_app.config.get('HIK_APP_SECRET')
    return HikvisionCloudAPI(app_key, app_secret)


@auth_bp.route('/login-url', methods=['GET'])
def get_login_url():
    """
    获取 OAuth 授权登录链接
    
    用户在浏览器中打开此链接，完成海康账号登录后，
    海康会回调 redirectUrl 并带上 authCode 参数。
    
    请求参数:
        userId: 小程序用户ID (可选，用于state传递)
    
    返回:
        loginUrl: 海康 OAuth 授权页面链接
    """
    try:
        app_key = current_app.config.get('HIK_APP_KEY')
        redirect_url = current_app.config.get('HIK_REDIRECT_URL', '')
        
        if not app_key:
            return jsonify({'code': 500, 'msg': 'HIK_APP_KEY not configured'}), 500
        if not redirect_url:
            return jsonify({'code': 500, 'msg': 'HIK_REDIRECT_URL not configured'}), 500
        
        # state参数用于传递用户ID和防CSRF
        user_id = request.args.get('userId', '')
        state_token = str(uuid.uuid4())[:8]
        state = f"{user_id}|{state_token}" if user_id else state_token
        
        # 拼接 OAuth 授权URL（内部自建应用使用 thirdpart）
        encoded_redirect = quote(redirect_url, safe='')
        login_url = (
            f"https://open.hikiot.com/oauth/thirdpart"
            f"?appKey={app_key}"
            f"&redirectUrl={encoded_redirect}"
            f"&state={quote(state, safe='')}"
        )
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'loginUrl': login_url,
                'state': state
            }
        })
        
    except Exception as e:
        logger.error(f"生成登录链接失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@auth_bp.route('/oauth-callback', methods=['GET'])
def oauth_callback():
    """
    OAuth 授权回调接口
    
    海康授权成功后会重定向到此接口:
    {redirectUrl}?authCode=xxx&state=xxx
    
    此接口会自动用 authCode 换取 UserAccessToken 并存储。
    """
    try:
        auth_code = request.args.get('authCode')
        state = request.args.get('state', '')
        
        if not auth_code:
            return jsonify({'code': 400, 'msg': 'Missing authCode parameter'}), 400
        
        logger.info(f"收到 OAuth 回调: authCode={auth_code[:8]}..., state={state}")
        
        # 从state中解析userId
        user_id = ''
        if '|' in state:
            user_id = state.split('|')[0]
        
        # 如果没有userId，生成一个默认的
        if not user_id:
            user_id = f"hik_user_{str(uuid.uuid4())[:8]}"
        
        # 用 authCode 换取 UserAccessToken
        hik_api = get_hik_api()
        result = hik_api.code2token(auth_code)
        
        if result.get('code') == 0:
            token_data = result['data']
            
            # 有效期30天
            expires_at = datetime.utcnow() + timedelta(days=USER_TOKEN_EXPIRES_DAYS)
            
            # 存储Token
            user_auth = UserAuth.query.filter_by(user_id=user_id).first()
            if user_auth:
                user_auth.user_access_token = token_data['userAccessToken']
                user_auth.refresh_user_token = token_data.get('refreshUserToken')
                user_auth.token_expires_at = expires_at
                user_auth.hik_account = token_data.get('accountNo')
                user_auth.team_no = token_data.get('teamNo')
                user_auth.person_no = token_data.get('personNo')
                user_auth.status = 'active'
            else:
                user_auth = UserAuth(
                    user_id=user_id,
                    user_access_token=token_data['userAccessToken'],
                    refresh_user_token=token_data.get('refreshUserToken'),
                    token_expires_at=expires_at,
                    hik_account=token_data.get('accountNo'),
                    team_no=token_data.get('teamNo'),
                    person_no=token_data.get('personNo'),
                    status='active'
                )
                db.session.add(user_auth)
            db.session.commit()
            
            logger.info(f"用户 {user_id} 授权成功，Token有效期至 {expires_at}")
            
            # 返回授权成功页面
            return f"""
            <!DOCTYPE html>
            <html>
            <head><meta charset="utf-8"><title>授权成功</title></head>
            <body style="display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;">
                <div style="text-align:center;">
                    <h1 style="color:#4CAF50;">✅ 授权成功</h1>
                    <p>用户ID: {user_id}</p>
                    <p>海康账号: {token_data.get('accountNo', 'N/A')}</p>
                    <p>Token有效期至: {expires_at.strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
                    <p style="color:#888;">此页面可以关闭</p>
                </div>
            </body>
            </html>
            """, 200
        else:
            error_msg = result.get('msg', 'Unknown error')
            logger.error(f"OAuth 回调换取Token失败: {error_msg}")
            return f"""
            <!DOCTYPE html>
            <html>
            <head><meta charset="utf-8"><title>授权失败</title></head>
            <body style="display:flex;justify-content:center;align-items:center;height:100vh;font-family:sans-serif;">
                <div style="text-align:center;">
                    <h1 style="color:#f44336;">❌ 授权失败</h1>
                    <p>{error_msg}</p>
                    <p style="color:#888;">请重试或联系管理员</p>
                </div>
            </body>
            </html>
            """, 400
            
    except Exception as e:
        logger.error(f"OAuth 回调处理失败: {e}", exc_info=True)
        return jsonify({'code': 500, 'msg': str(e)}), 500


@auth_bp.route('/apply-auth-code', methods=['POST'])
def apply_auth_code():
    """
    申请授权码
    用户登录获取授权码，以便换取用户访问凭证
    
    请求参数:
        userName: 登录账号手机号
        password: 密码
        userId: 小程序用户ID (可选，用于关联Token)
    """
    try:
        data = request.get_json() or {}
        
        user_name = data.get('userName')
        password = data.get('password')
        user_id = data.get('userId')  # 小程序用户ID
        
        if not user_name:
            return jsonify({'code': 400, 'msg': 'Missing parameter: userName'}), 400
        if not password:
            return jsonify({'code': 400, 'msg': 'Missing parameter: password'}), 400
        
        # 获取 redirectUrl
        redirect_url = current_app.config.get('HIK_REDIRECT_URL', 'http://localhost:8080/callback')
        
        # 调用海康 API 申请授权码
        hik_api = get_hik_api()
        result = hik_api.apply_auth_code(
            user_name=user_name,
            password=password,
            redirect_url=redirect_url
        )
        
        if result.get('code') == 0:
            auth_code = result['data']['authCode']
            
            # 如果提供了 userId，先临时存储授权码
            if user_id:
                # 检查是否已存在用户记录
                user_auth = UserAuth.query.filter_by(user_id=user_id).first()
                if user_auth:
                    # 更新临时授权码
                    user_auth.temp_auth_code = auth_code
                    user_auth.temp_auth_expires = datetime.utcnow() + timedelta(minutes=5)
                else:
                    # 创建新记录
                    user_auth = UserAuth(
                        user_id=user_id,
                        user_access_token='',  # 临时为空
                        temp_auth_code=auth_code,
                        temp_auth_expires=datetime.utcnow() + timedelta(minutes=5)
                    )
                    db.session.add(user_auth)
                db.session.commit()
            
            return jsonify({
                'code': 0,
                'msg': 'success',
                'data': {
                    'authCode': auth_code,
                    'expiresIn': 300  # 5分钟
                }
            })
        else:
            return jsonify({
                'code': result.get('code', 500),
                'msg': result.get('msg', 'Failed to apply auth code')
            }), 400
            
    except Exception as e:
        logger.error(f"申请授权码失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@auth_bp.route('/code2token', methods=['POST'])
def code2token():
    """
    授权码换取 User Access Token
    
    请求参数:
        authCode: 授权码
        userId: 小程序用户ID
    """
    try:
        data = request.get_json() or {}
        
        auth_code = data.get('authCode')
        user_id = data.get('userId')
        
        if not auth_code:
            return jsonify({'code': 400, 'msg': 'Missing parameter: authCode'}), 400
        
        # 调用海康 API 换取 Token
        hik_api = get_hik_api()
        result = hik_api.code2token(auth_code)
        
        if result.get('code') == 0:
            token_data = result['data']
            
            # UserAccessToken 有效期30天
            expires_at = datetime.utcnow() + timedelta(days=USER_TOKEN_EXPIRES_DAYS)
            
            # 存储或更新用户 Token
            if user_id:
                user_auth = UserAuth.query.filter_by(user_id=user_id).first()
                if user_auth:
                    user_auth.user_access_token = token_data['userAccessToken']
                    user_auth.refresh_user_token = token_data.get('refreshUserToken')
                    user_auth.token_expires_at = expires_at
                    user_auth.hik_account = token_data.get('accountNo')
                    user_auth.team_no = token_data.get('teamNo')
                    user_auth.person_no = token_data.get('personNo')
                    user_auth.status = 'active'
                else:
                    user_auth = UserAuth(
                        user_id=user_id,
                        user_access_token=token_data['userAccessToken'],
                        refresh_user_token=token_data.get('refreshUserToken'),
                        token_expires_at=expires_at,
                        hik_account=token_data.get('accountNo'),
                        team_no=token_data.get('teamNo'),
                        person_no=token_data.get('personNo'),
                        status='active'
                    )
                    db.session.add(user_auth)
                db.session.commit()
            
            return jsonify({
                'code': 0,
                'msg': 'success',
                'data': {
                    'userAccessToken': token_data['userAccessToken'],
                    'expiresIn': token_data.get('expiresIn', '7'),
                    'expiresAt': expires_at.isoformat()
                }
            })
        else:
            return jsonify({
                'code': result.get('code', 500),
                'msg': result.get('msg', 'Failed to exchange token')
            }), 400
            
    except Exception as e:
        logger.error(f"换取Token失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@auth_bp.route('/refresh-token', methods=['POST'])
def refresh_token():
    """
    刷新 User Access Token
    
    请求参数:
        userId: 小程序用户ID
    """
    try:
        data = request.get_json() or {}
        
        user_id = data.get('userId')
        
        if not user_id:
            return jsonify({'code': 400, 'msg': 'Missing parameter: userId'}), 400
        
        # 获取用户当前的 Token
        user_auth = UserAuth.query.filter_by(user_id=user_id).first()
        if not user_auth:
            return jsonify({'code': 404, 'msg': 'User not found'}), 404
        
        if not user_auth.refresh_user_token:
            return jsonify({'code': 400, 'msg': 'No refresh token available'}), 400
        
        # 调用海康 API 刷新 Token
        hik_api = get_hik_api()
        result = hik_api.refresh_user_token(
            user_auth.user_access_token,
            user_auth.refresh_user_token
        )
        
        if result.get('code') == 0:
            token_data = result['data']
            
            # UserAccessToken 有效期30天
            expires_at = datetime.utcnow() + timedelta(days=USER_TOKEN_EXPIRES_DAYS)
            
            # 更新数据库
            user_auth.user_access_token = token_data['userAccessToken']
            user_auth.refresh_user_token = token_data.get('refreshUserToken')
            user_auth.token_expires_at = expires_at
            user_auth.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'code': 0,
                'msg': 'success',
                'data': {
                    'userAccessToken': token_data['userAccessToken'],
                    'expiresIn': token_data.get('expiresIn', '7'),
                    'expiresAt': expires_at.isoformat()
                }
            })
        else:
            # 如果刷新失败，检查是否是 Token 已过期
            if result.get('code') in [400026, 100903]:
                user_auth.status = 'expired'
                db.session.commit()
                return jsonify({
                    'code': result.get('code', 500),
                    'msg': 'Token expired, please re-authenticate'
                }), 401
            
            return jsonify({
                'code': result.get('code', 500),
                'msg': result.get('msg', 'Failed to refresh token')
            }), 400
            
    except Exception as e:
        logger.error(f"刷新Token失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@auth_bp.route('/status', methods=['GET'])
def get_token_status():
    """
    获取用户 Token 状态
    
    请求参数:
        userId: 小程序用户ID
    """
    try:
        user_id = request.args.get('userId')
        
        if not user_id:
            return jsonify({'code': 400, 'msg': 'Missing parameter: userId'}), 400
        
        user_auth = UserAuth.query.filter_by(user_id=user_id).first()
        if not user_auth:
            return jsonify({
                'code': 0,
                'msg': 'success',
                'data': {
                    'isBound': False,
                    'status': None
                }
            })
        
        # 检查是否即将过期 (1天内)
        is_expiring_soon = False
        if user_auth.token_expires_at:
            time_left = user_auth.token_expires_at - datetime.utcnow()
            is_expiring_soon = time_left.total_seconds() < 24 * 3600  # 24小时
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'isBound': True,
                'status': user_auth.status,
                'hikAccount': user_auth.hik_account,
                'expiresAt': user_auth.token_expires_at.isoformat() if user_auth.token_expires_at else None,
                'isExpiringSoon': is_expiring_soon,
                'updatedAt': user_auth.updated_at.isoformat() if user_auth.updated_at else None
            }
        })
        
    except Exception as e:
        logger.error(f"获取Token状态失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@auth_bp.route('/unbind', methods=['POST'])
def unbind_user():
    """
    解除用户绑定
    
    请求参数:
        userId: 小程序用户ID
    """
    try:
        data = request.get_json() or {}
        user_id = data.get('userId')
        
        if not user_id:
            return jsonify({'code': 400, 'msg': 'Missing parameter: userId'}), 400
        
        user_auth = UserAuth.query.filter_by(user_id=user_id).first()
        if not user_auth:
            return jsonify({'code': 404, 'msg': 'User not found'}), 404
        
        # 删除用户 Token
        db.session.delete(user_auth)
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'msg': 'success'
        })
        
    except Exception as e:
        logger.error(f"解除绑定失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500
