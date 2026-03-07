#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康互联开放平台后端服务
Flask + SQLAlchemy + Redis

环境变量:
    HIK_APP_KEY - 海康应用Key
    HIK_APP_SECRET - 海康应用Secret
    DATABASE_URL - 数据库连接
    REDIS_URL - Redis连接
"""

import os
import logging
from datetime import datetime
from flask import Flask, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化扩展 (使用 models 中的 db)
from models import db
migrate = Migrate()

def create_app():
    """创建 Flask 应用"""
    app = Flask(__name__)
    
    # 配置
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    # 使用绝对路径避免工作目录问题
    db_url = os.getenv('DATABASE_URL', 'sqlite:///app/data/hikvision.db')
    if db_url.startswith('sqlite:///') and not db_url.startswith('sqlite:////'):
        # 转换为绝对路径格式
        db_path = db_url.replace('sqlite:///', '')
        if not db_path.startswith('/'):
            db_path = '/app/data/' + db_path
        db_url = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # 海康配置
    app.config['HIK_APP_KEY'] = os.getenv('HIK_APP_KEY', '')
    app.config['HIK_APP_SECRET'] = os.getenv('HIK_APP_SECRET', '')
    app.config['HIK_BASE_URL'] = os.getenv('HIK_BASE_URL', 'https://open-api.hikiot.com')
    app.config['HIK_REDIRECT_URL'] = os.getenv('HIK_REDIRECT_URL', 'http://localhost:8080/callback')
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    
    # 注册V1蓝图（兼容保留）
    from routes.callback import callback_bp
    from routes.device import device_bp
    from routes.detection import detection_bp
    from routes.auth import auth_bp
    
    app.register_blueprint(callback_bp, url_prefix='/api/callback')
    app.register_blueprint(device_bp, url_prefix='/api/devices')
    app.register_blueprint(detection_bp, url_prefix='/api/detection')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    
    # 注册V2蓝图（SaaS多租户）
    from routes.auth_v2 import auth_v2_bp
    from routes.users_v2 import users_bp
    from routes.platforms_v2 import platforms_bp
    from routes.hierarchy_v2 import factories_bp, areas_bp, enclosures_bp
    from routes.cameras_v2 import cameras_bp
    from routes.alarms_v2 import alarms_bp
    from routes.detections_v2 import detections_bp
    
    app.register_blueprint(auth_v2_bp, url_prefix='/api/v2/auth')
    app.register_blueprint(users_bp, url_prefix='/api/v2/users')
    app.register_blueprint(platforms_bp, url_prefix='/api/v2/platforms')
    app.register_blueprint(factories_bp, url_prefix='/api/v2/factories')
    app.register_blueprint(areas_bp, url_prefix='/api/v2/areas')
    app.register_blueprint(enclosures_bp, url_prefix='/api/v2/enclosures')
    app.register_blueprint(cameras_bp, url_prefix='/api/v2/cameras')
    app.register_blueprint(alarms_bp, url_prefix='/api/v2/alarms')
    app.register_blueprint(detections_bp, url_prefix='/api/v2/detections')
    
    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'code': 404, 'msg': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({'code': 500, 'msg': 'Internal server error'}), 500
    
    # 健康检查
    @app.route('/health')
    def health_check():
        return jsonify({
            'code': 0,
            'msg': 'Service is running',
            'data': {
                'timestamp': datetime.now().isoformat(),
                'version': '1.0.0'
            }
        })
    
    # 根路由
    @app.route('/')
    def index():
        return jsonify({
            'code': 0,
            'msg': 'Hikvision Cloud Backend Service',
            'data': {
                'version': '2.0.0',
                'endpoints': {
                    'v1_legacy': [
                        '/api/callback - 海康互联回调',
                        '/api/devices - 设备管理',
                        '/api/detection - 检测服务',
                        '/api/auth - 用户认证 (Token获取/刷新)',
                    ],
                    'v2_saas': [
                        '/api/v2/auth/login - 登录',
                        '/api/v2/auth/me - 当前用户',
                        '/api/v2/users - 用户管理 (Admin)',
                        '/api/v2/platforms - 平台授权管理',
                        '/api/v2/factories - 厂区管理',
                        '/api/v2/areas - 区域管理',
                        '/api/v2/enclosures - 圈/个体管理',
                        '/api/v2/cameras - 摄像头管理',
                        '/api/v2/alarms - 告警管理',
                        '/api/v2/detections - 检测记录',
                    ],
                    'system': [
                        '/health - 健康检查'
                    ]
                }
            }
        })
    
    return app

# 创建应用实例
app = create_app()

# 延迟初始化数据库表，添加错误处理
def init_database():
    """初始化数据库表"""
    max_retries = 5
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            with app.app_context():
                # 确保数据目录存在
                db_uri = app.config['SQLALCHEMY_DATABASE_URI']
                if db_uri.startswith('sqlite:///'):
                    db_path = db_uri.replace('sqlite:///', '')
                    db_dir = os.path.dirname(db_path)
                    if db_dir and not os.path.exists(db_dir):
                        os.makedirs(db_dir, exist_ok=True)
                        logger.info(f"创建数据目录: {db_dir}")
                
                db.create_all()
                logger.info("数据库表已创建")
                return True
        except Exception as e:
            logger.warning(f"数据库初始化失败 (尝试 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(retry_delay)
            else:
                logger.error("数据库初始化最终失败，但应用仍将继续启动")
                return False

# 在应用启动时初始化数据库
init_database()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"启动服务: port={port}, debug={debug}")
    app.run(host='0.0.0.0', port=port, debug=debug)
