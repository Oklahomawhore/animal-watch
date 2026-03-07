#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
定时任务服务 - 自动刷新 User Token
"""

import os
import sys
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def refresh_expired_tokens():
    """刷新即将过期的 User Token"""
    try:
        from app import create_app, db
        from models import UserAuth
        from services.hikcloud import HikvisionCloudAPI
        
        app = create_app()
        
        with app.app_context():
            # 查找即将过期的 Token (1天内过期)
            threshold = datetime.utcnow() + timedelta(days=1)
            expired_tokens = UserAuth.query.filter(
                UserAuth.token_expires_at <= threshold,
                UserAuth.status == 'active'
            ).all()
            
            if not expired_tokens:
                logger.info("没有需要刷新的 Token")
                return
            
            logger.info(f"发现 {len(expired_tokens)} 个需要刷新的 Token")
            
            # 获取海康 API 实例
            app_key = app.config.get('HIK_APP_KEY')
            app_secret = app.config.get('HIK_APP_SECRET')
            hik_api = HikvisionCloudAPI(app_key, app_secret)
            
            for user_auth in expired_tokens:
                try:
                    logger.info(f"正在刷新用户 {user_auth.user_id} 的 Token")
                    
                    result = hik_api.refresh_user_token(
                        user_auth.user_access_token,
                        user_auth.refresh_user_token
                    )
                    
                    if result.get('code') == 0:
                        token_data = result['data']
                        
                        # 更新数据库
                        user_auth.user_access_token = token_data['userAccessToken']
                        user_auth.refresh_user_token = token_data.get('refreshUserToken')
                        user_auth.token_expires_at = datetime.utcnow() + timedelta(
                            days=30  # UserAccessToken 有效期30天
                        )
                        user_auth.updated_at = datetime.utcnow()
                        db.session.commit()
                        
                        logger.info(f"用户 {user_auth.user_id} 的 Token 刷新成功")
                    else:
                        logger.warning(
                            f"用户 {user_auth.user_id} 的 Token 刷新失败: {result.get('msg')}"
                        )
                        
                        # 如果是 Token 已过期，标记为 expired
                        if result.get('code') in [400026, 100903]:
                            user_auth.status = 'expired'
                            db.session.commit()
                            logger.warning(f"用户 {user_auth.user_id} 的 Token 已过期，需要重新认证")
                
                except Exception as e:
                    logger.error(f"刷新用户 {user_auth.user_id} 的 Token 时出错: {e}")
                    db.session.rollback()
            
            logger.info("Token 刷新任务完成")
    
    except Exception as e:
        logger.error(f"Token 刷新任务执行失败: {e}")


if __name__ == '__main__':
    logger.info("开始执行 Token 刷新任务...")
    refresh_expired_tokens()
