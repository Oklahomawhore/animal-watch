#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本
创建初始客户和管理员账号
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from werkzeug.security import generate_password_hash
from app import create_app, db
from models_v2 import Client, User, UserRole, UserStatus, VisibilityLevel

def init_database():
    """初始化数据库"""
    app = create_app()
    
    with app.app_context():
        # 创建所有表
        db.create_all()
        print("✅ 数据库表创建完成")
        
        # 检查是否已有客户
        if Client.query.first():
            print("⚠️  数据库已有数据，跳过初始化")
            return
        
        # 创建默认客户
        client = Client(
            name="默认养殖场",
            code="default",
            contact_name="管理员",
            contact_phone="13800138000",
            config={
                "wechat": {},
                "notification": {
                    "enabled_types": ["motion", "grass_low", "offline"]
                }
            }
        )
        db.session.add(client)
        db.session.flush()  # 获取client.id
        
        print(f"✅ 客户创建完成: {client.name} (ID: {client.id})")
        
        # 创建管理员账号
        admin = User(
            client_id=client.id,
            username="admin",
            password_hash=generate_password_hash("admin123"),  # 首次登录后修改
            nickname="系统管理员",
            phone="13800138000",
            role=UserRole.ADMIN,
            visibility_level=VisibilityLevel.FACTORY,
            visibility_scope_ids=[],
            permissions={
                "can_manage_users": True,
                "can_manage_platforms": True,
                "can_view_analytics": True,
                "can_receive_alerts": True
            },
            status=UserStatus.ACTIVE
        )
        db.session.add(admin)
        db.session.commit()
        
        print(f"✅ 管理员账号创建完成: {admin.username}")
        print("⚠️  请登录后立即修改默认密码！")
        print("\n初始账号信息:")
        print(f"  客户编码: {client.code}")
        print(f"  用户名: admin")
        print(f"  密码: admin123")

if __name__ == '__main__':
    init_database()
