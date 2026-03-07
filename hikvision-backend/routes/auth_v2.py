#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2 认证路由 - SaaS多租户登录
"""

import logging
import uuid
from datetime import datetime, timedelta
from urllib.parse import quote
from flask import Blueprint, request, jsonify, current_app, g
from werkzeug.security import generate_password_hash, check_password_hash

from models_v2 import db, User, UserRole, UserStatus, Client, VisibilityLevel
from services.hikcloud import HikvisionCloudAPI
from utils.auth import generate_token, login_required, admin_required

logger = logging.getLogger(__name__)

auth_v2_bp = Blueprint('auth_v2', __name__)


@auth_v2_bp.route('/login', methods=['POST'])
def login():
    """
    用户登录
    
    请求参数:
        username: 用户名
        password: 密码
        clientCode: 客户编码 (可选，用于多租户区分)
    
    返回:
        token: JWT Token
        user: 用户信息
    """
    try:
        data = request.get_json() or {}
        username = data.get('username')
        password = data.get('password')
        client_code = data.get('clientCode', 'default')
        
        if not username or not password:
            return jsonify({'code': 400, 'msg': 'Missing username or password'}), 400
        
        # 查找用户
        user = User.query.filter_by(username=username).first()
        
        # 如果指定了client_code，验证是否匹配
        if client_code and client_code != 'default':
            client = Client.query.filter_by(code=client_code).first()
            if not client:
                return jsonify({'code': 404, 'msg': 'Client not found'}), 404
            if user and user.client_id != client.id:
                return jsonify({'code': 401, 'msg': 'Invalid credentials'}), 401
        
        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({'code': 401, 'msg': 'Invalid credentials'}), 401
        
        if user.status != UserStatus.ACTIVE:
            return jsonify({'code': 403, 'msg': 'Account is inactive or suspended'}), 403
        
        # 更新最后登录时间
        user.last_login_at = datetime.utcnow()
        user.last_login_ip = request.remote_addr
        db.session.commit()
        
        # 生成Token
        token = generate_token(user)
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'token': token,
                'user': user.to_dict()
            }
        })
        
    except Exception as e:
        logger.error(f"登录失败: {e}", exc_info=True)
        return jsonify({'code': 500, 'msg': str(e)}), 500


@auth_v2_bp.route('/me', methods=['GET'])
@login_required
def get_current_user():
    """获取当前登录用户信息"""
    return jsonify({
        'code': 0,
        'msg': 'success',
        'data': g.user.to_dict()
    })


@auth_v2_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """修改密码"""
    try:
        data = request.get_json() or {}
        old_password = data.get('oldPassword')
        new_password = data.get('newPassword')
        
        if not old_password or not new_password:
            return jsonify({'code': 400, 'msg': 'Missing password'}), 400
        
        if not check_password_hash(g.user.password_hash, old_password):
            return jsonify({'code': 400, 'msg': 'Old password is incorrect'}), 400
        
        g.user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        return jsonify({'code': 0, 'msg': 'Password changed successfully'})
        
    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


# ========== 海康互联OAuth (用于平台授权) ==========

@auth_v2_bp.route('/hikvision/login-url', methods=['GET'])
@admin_required
def get_hikvision_login_url():
    """
    获取海康互联OAuth授权登录链接
    
    请求参数:
        platformId: 平台ID (可选，用于重新授权)
    
    返回:
        loginUrl: 海康OAuth授权页面链接
    """
    try:
        from models_v2 import CameraPlatform
        
        app_key = current_app.config.get('HIK_APP_KEY')
        redirect_url = current_app.config.get('HIK_REDIRECT_URL', '')
        
        if not app_key:
            return jsonify({'code': 500, 'msg': 'HIK_APP_KEY not configured'}), 500
        if not redirect_url:
            return jsonify({'code': 500, 'msg': 'HIK_REDIRECT_URL not configured'}), 500
        
        # state参数用于传递client_id和user_id
        state_data = f"{g.client_id}|{g.user.id}"
        
        # 拼接 OAuth 授权URL
        encoded_redirect = quote(redirect_url, safe='')
        login_url = (
            f"https://open.hikiot.com/oauth/thirdpart"
            f"?appKey={app_key}"
            f"&redirectUrl={encoded_redirect}"
            f"&state={quote(state_data, safe='')}"
        )
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'loginUrl': login_url,
                'state': state_data
            }
        })
        
    except Exception as e:
        logger.error(f"生成登录链接失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500
