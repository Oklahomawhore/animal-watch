#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小程序登录API
支持微信code登录，自动绑定openid
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash

from models_v2 import db, User, UserRole, UserStatus, Client, VisibilityLevel
from services.wechat_mp import wechat_service
from utils.auth import generate_token

logger = logging.getLogger(__name__)

miniprogram_bp = Blueprint('miniprogram', __name__)


@miniprogram_bp.route('/login', methods=['POST'])
def mp_login():
    """
    小程序登录
    
    请求参数:
        code: 微信登录凭证（wx.login获取）
        clientCode: 客户编码（租户标识）
        phoneCode: 获取手机号的code（可选，wx.getPhoneNumber获取）
    
    流程:
        1. code换openid
        2. 根据openid查找用户
        3. 如果用户不存在，且提供了phoneCode，自动创建账号
        4. 返回JWT token
    """
    try:
        data = request.get_json() or {}
        code = data.get('code')
        client_code = data.get('clientCode')
        phone_code = data.get('phoneCode')
        
        if not code:
            return jsonify({'code': 400, 'msg': 'Missing code'}), 400
        if not client_code:
            return jsonify({'code': 400, 'msg': 'Missing clientCode'}), 400
        
        # 查找客户
        client = Client.query.filter_by(code=client_code).first()
        if not client:
            return jsonify({'code': 404, 'msg': 'Client not found'}), 404
        
        # code换openid
        session_info = wechat_service.code_to_session(code)
        if not session_info:
            return jsonify({'code': 401, 'msg': 'Invalid wechat code'}), 401
        
        openid = session_info.get('openid')
        session_key = session_info.get('session_key')
        unionid = session_info.get('unionid')
        
        # 查找用户
        user = User.query.filter_by(
            client_id=client.id,
            wechat_openid=openid
        ).first()
        
        # 如果用户不存在，尝试用手机号创建
        if not user and phone_code:
            phone = wechat_service.get_phone_number(phone_code)
            if phone:
                # 检查手机号是否已存在
                user = User.query.filter_by(
                    client_id=client.id,
                    phone=phone
                ).first()
                
                if user:
                    # 绑定微信
                    user.wechat_openid = openid
                    user.wechat_unionid = unionid
                    user.wechat_session_key = session_key
                else:
                    # 创建新用户（默认饲养员角色）
                    user = User(
                        client_id=client.id,
                        username=f"mp_{openid[-8:]}",  # 自动生成用户名
                        password_hash=generate_password_hash(openid),  # 随机密码
                        nickname=f"用户{phone[-4:]}",
                        phone=phone,
                        wechat_openid=openid,
                        wechat_unionid=unionid,
                        wechat_session_key=session_key,
                        role=UserRole.BREEDER,  # 默认饲养员
                        visibility_level=VisibilityLevel.FACTORY,
                        notification_settings={
                            "alarm": True,
                            "offline": True,
                            "medical": True
                        },
                        status=UserStatus.ACTIVE
                    )
                    db.session.add(user)
        
        if not user:
            return jsonify({
                'code': 404,
                'msg': 'User not found, please bind phone',
                'data': {
                    'needPhone': True,
                    'openid': openid  # 返回openid用于后续绑定
                }
            }), 404
        
        # 更新session_key
        user.wechat_session_key = session_key
        user.last_login_at = datetime.utcnow()
        db.session.commit()
        
        # 生成token
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
        logger.error(f"小程序登录失败: {e}", exc_info=True)
        return jsonify({'code': 500, 'msg': str(e)}), 500


@miniprogram_bp.route('/bind-phone', methods=['POST'])
def bind_phone():
    """
    绑定手机号（首次登录时）
    
    请求参数:
        openid: 之前返回的openid
        clientCode: 客户编码
        phoneCode: 获取手机号的code
        nickname: 用户昵称（可选）
    """
    try:
        data = request.get_json() or {}
        openid = data.get('openid')
        client_code = data.get('clientCode')
        phone_code = data.get('phoneCode')
        nickname = data.get('nickname', '')
        
        if not openid or not client_code or not phone_code:
            return jsonify({'code': 400, 'msg': 'Missing required fields'}), 400
        
        # 查找客户
        client = Client.query.filter_by(code=client_code).first()
        if not client:
            return jsonify({'code': 404, 'msg': 'Client not found'}), 404
        
        # 获取手机号
        phone = wechat_service.get_phone_number(phone_code)
        if not phone:
            return jsonify({'code': 400, 'msg': 'Failed to get phone number'}), 400
        
        # 检查是否已存在
        user = User.query.filter_by(
            client_id=client.id,
            wechat_openid=openid
        ).first()
        
        if user:
            # 更新手机号
            user.phone = phone
            if nickname:
                user.nickname = nickname
        else:
            # 检查手机号是否已绑定其他账号
            existing = User.query.filter_by(
                client_id=client.id,
                phone=phone
            ).first()
            
            if existing:
                # 绑定微信到这个账号
                existing.wechat_openid = openid
                if nickname:
                    existing.nickname = nickname
                user = existing
            else:
                # 创建新用户
                user = User(
                    client_id=client.id,
                    username=f"mp_{openid[-8:]}",
                    password_hash=generate_password_hash(openid),
                    nickname=nickname or f"用户{phone[-4:]}",
                    phone=phone,
                    wechat_openid=openid,
                    role=UserRole.BREEDER,
                    visibility_level=VisibilityLevel.FACTORY,
                    notification_settings={
                        "alarm": True,
                        "offline": True,
                        "medical": True
                    },
                    status=UserStatus.ACTIVE
                )
                db.session.add(user)
        
        db.session.commit()
        
        # 生成token
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
        logger.error(f"绑定手机号失败: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500


@miniprogram_bp.route('/clients', methods=['GET'])
def list_clients():
    """
    获取客户列表（小程序登录前选择）
    
    返回:
        [{ id, name, code, logo }]
    """
    try:
        clients = Client.query.filter_by(status=UserStatus.ACTIVE).all()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': [
                {
                    'id': c.id,
                    'name': c.name,
                    'code': c.code,
                    'logo': c.config.get('logo', '')
                } for c in clients
            ]
        })
        
    except Exception as e:
        logger.error(f"获取客户列表失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500
