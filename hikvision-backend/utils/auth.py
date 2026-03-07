#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证装饰器 - JWT + 多租户隔离
"""

import jwt
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app, g
from models_v2 import User, UserRole, UserStatus

logger = logging.getLogger(__name__)


def generate_token(user):
    """生成JWT Token"""
    payload = {
        'user_id': user.id,
        'client_id': user.client_id,
        'role': user.role.value,
        'exp': datetime.utcnow() + timedelta(days=7)  # 7天有效期
    }
    return jwt.encode(
        payload,
        current_app.config['SECRET_KEY'],
        algorithm='HS256'
    )


def decode_token(token):
    """解码JWT Token"""
    try:
        payload = jwt.decode(
            token,
            current_app.config['SECRET_KEY'],
            algorithms=['HS256']
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_auth_token():
    """从请求头获取Token"""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    return None


def login_required(f):
    """登录 required 装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = get_auth_token()
        if not token:
            return jsonify({'code': 401, 'msg': 'Missing authorization token'}), 401
        
        payload = decode_token(token)
        if not payload:
            return jsonify({'code': 401, 'msg': 'Invalid or expired token'}), 401
        
        # 加载用户信息
        user = User.query.get(payload['user_id'])
        if not user or user.status != UserStatus.ACTIVE:
            return jsonify({'code': 401, 'msg': 'User not found or inactive'}), 401
        
        # 设置全局用户
        g.user = user
        g.client_id = user.client_id
        
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """管理员权限 required 装饰器"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if g.user.role != UserRole.ADMIN:
            return jsonify({'code': 403, 'msg': 'Admin permission required'}), 403
        return f(*args, **kwargs)
    return decorated_function


def manager_required(f):
    """管理员或厂长权限 required 装饰器"""
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if g.user.role not in [UserRole.ADMIN, UserRole.FACTORY_MANAGER]:
            return jsonify({'code': 403, 'msg': 'Manager permission required'}), 403
        return f(*args, **kwargs)
    return decorated_function


def client_isolation(query):
    """添加客户隔离过滤"""
    if hasattr(g, 'client_id'):
        return query.filter_by(client_id=g.client_id)
    return query
