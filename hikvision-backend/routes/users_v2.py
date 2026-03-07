#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2 用户管理路由 - 仅管理员可操作
"""

import logging
from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash

from models_v2 import db, User, UserRole, UserStatus, VisibilityLevel
from utils.auth import login_required, admin_required, client_isolation

logger = logging.getLogger(__name__)

users_bp = Blueprint('users_v2', __name__)


@users_bp.route('', methods=['GET'])
@login_required
def list_users():
    """获取用户列表（管理员看全部，厂长看饲养员）"""
    try:
        query = User.query.filter_by(client_id=g.client_id)
        
        # 厂长只能看饲养员
        if g.user.role == UserRole.FACTORY_MANAGER:
            query = query.filter_by(role=UserRole.BREEDER)
        
        # 分页
        page = request.args.get('page', 1, type=int)
        size = request.args.get('size', 20, type=int)
        
        pagination = query.paginate(page=page, per_page=size, error_out=False)
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'items': [u.to_dict() for u in pagination.items],
                'total': pagination.total,
                'page': page,
                'size': size
            }
        })
        
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@users_bp.route('', methods=['POST'])
@admin_required
def create_user():
    """
    创建用户（仅管理员）
    
    请求参数:
        username: 用户名（唯一）
        password: 密码
        nickname: 昵称
        phone: 手机号
        email: 邮箱
        role: 角色 (factory_manager/breeder)
        visibilityLevel: 可视级别 (factory/area/enclosure)
        visibilityScopeIds: 可视范围ID列表
        permissions: 额外权限配置
    """
    try:
        data = request.get_json() or {}
        
        # 必填字段
        username = data.get('username')
        password = data.get('password')
        role = data.get('role')
        
        if not username or not password or not role:
            return jsonify({'code': 400, 'msg': 'Missing required fields: username, password, role'}), 400
        
        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            return jsonify({'code': 400, 'msg': 'Username already exists'}), 400
        
        # 验证角色
        try:
            user_role = UserRole(role)
        except ValueError:
            return jsonify({'code': 400, 'msg': f'Invalid role: {role}'}), 400
        
        # 不能创建管理员（只能有一个初始管理员）
        if user_role == UserRole.ADMIN:
            return jsonify({'code': 403, 'msg': 'Cannot create admin user via API'}), 403
        
        # 解析可视范围
        visibility_level = data.get('visibilityLevel', 'factory')
        try:
            vis_level = VisibilityLevel(visibility_level)
        except ValueError:
            return jsonify({'code': 400, 'msg': f'Invalid visibility level: {visibility_level}'}), 400
        
        # 创建用户
        user = User(
            client_id=g.client_id,
            username=username,
            password_hash=generate_password_hash(password),
            nickname=data.get('nickname'),
            phone=data.get('phone'),
            email=data.get('email'),
            role=user_role,
            visibility_level=vis_level,
            visibility_scope_ids=data.get('visibilityScopeIds', []),
            permissions=data.get('permissions', {}),
            created_by=g.user.id
        )
        
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"用户 {username} 创建成功，由 {g.user.username} 创建")
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': user.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"创建用户失败: {e}", exc_info=True)
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500


@users_bp.route('/<int:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    """获取用户详情"""
    try:
        user = User.query.filter_by(id=user_id, client_id=g.client_id).first()
        if not user:
            return jsonify({'code': 404, 'msg': 'User not found'}), 404
        
        # 权限检查：管理员和厂长可以查看，用户只能查看自己
        if g.user.role == UserRole.BREEDER and g.user.id != user_id:
            return jsonify({'code': 403, 'msg': 'Permission denied'}), 403
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': user.to_dict()
        })
        
    except Exception as e:
        logger.error(f"获取用户详情失败: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


@users_bp.route('/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    """
    更新用户信息（仅管理员）
    """
    try:
        user = User.query.filter_by(id=user_id, client_id=g.client_id).first()
        if not user:
            return jsonify({'code': 404, 'msg': 'User not found'}), 404
        
        data = request.get_json() or {}
        
        # 更新字段
        if 'nickname' in data:
            user.nickname = data['nickname']
        if 'phone' in data:
            user.phone = data['phone']
        if 'email' in data:
            user.email = data['email']
        if 'visibilityLevel' in data:
            user.visibility_level = VisibilityLevel(data['visibilityLevel'])
        if 'visibilityScopeIds' in data:
            user.visibility_scope_ids = data['visibilityScopeIds']
        if 'permissions' in data:
            user.permissions = data['permissions']
        if 'status' in data:
            user.status = UserStatus(data['status'])
        
        db.session.commit()
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': user.to_dict()
        })
        
    except Exception as e:
        logger.error(f"更新用户失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500


@users_bp.route('/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_user_password(user_id):
    """
    重置用户密码（仅管理员）
    
    请求参数:
        newPassword: 新密码
    """
    try:
        user = User.query.filter_by(id=user_id, client_id=g.client_id).first()
        if not user:
            return jsonify({'code': 404, 'msg': 'User not found'}), 404
        
        data = request.get_json() or {}
        new_password = data.get('newPassword')
        
        if not new_password:
            return jsonify({'code': 400, 'msg': 'Missing newPassword'}), 400
        
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        logger.info(f"用户 {user.username} 密码被 {g.user.username} 重置")
        
        return jsonify({
            'code': 0,
            'msg': 'Password reset successfully'
        })
        
    except Exception as e:
        logger.error(f"重置密码失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500


@users_bp.route('/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    """删除用户（仅管理员）"""
    try:
        user = User.query.filter_by(id=user_id, client_id=g.client_id).first()
        if not user:
            return jsonify({'code': 404, 'msg': 'User not found'}), 404
        
        # 不能删除自己
        if user.id == g.user.id:
            return jsonify({'code': 400, 'msg': 'Cannot delete yourself'}), 400
        
        db.session.delete(user)
        db.session.commit()
        
        logger.info(f"用户 {user.username} 被 {g.user.username} 删除")
        
        return jsonify({
            'code': 0,
            'msg': 'User deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"删除用户失败: {e}")
        db.session.rollback()
        return jsonify({'code': 500, 'msg': str(e)}), 500
