#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回调处理路由
接收海康云的事件推送
"""

import json
import logging
from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from models import db, AlarmRecord, Detection, Device
from services.decryptor import decryptor

logger = logging.getLogger(__name__)

callback_bp = Blueprint('callback', __name__)


@callback_bp.route('', methods=['POST'])
def handle_callback():
    """
    接收海康云回调
    
    海康云推送的事件类型:
    - motion_detection: 移动检测告警
    - capture_result: 抓拍结果
    - device_status: 设备状态变化
    - url_verify: URL 验证（海康配置回调时发送）
    
    支持加密消息解密（需要配置 HIK_ENCRYPT_KEY 和 HIK_VERIFICATION_TOKEN）
    """
    try:
        data = request.get_json() or {}
        
        # 记录请求头和完整请求内容用于调试
        logger.info(f"收到海康 POST 回调")
        logger.info(f"请求头: {dict(request.headers)}")
        logger.info(f"请求体: {json.dumps(data, ensure_ascii=False)}")
        
        # 检查是否需要解密（海康使用 'encrypt' 字段）
        is_encrypted = 'encrypt' in data or 'encryptData' in data or 'encrypt_data' in data
        if is_encrypted:
            logger.info("检测到加密消息，开始解密...")
            decrypted_data = decryptor.decrypt_message(data)
            logger.info(f"解密后数据: {json.dumps(decrypted_data, ensure_ascii=False)}")
        else:
            decrypted_data = data
        
        # 验证 Verification Token
        if not decryptor.verify_token(request.headers, decrypted_data if is_encrypted else None):
            logger.error("Verification Token 验证失败")
            # 即使验证失败，对于 URL 验证请求也要返回成功，让海康知道地址有效
            # 返回 200 表示地址可达
        
        # 检查是否是 URL 验证请求（海康配置回调时的验证）
        # 海康 URL 验证可能通过不同的字段标识
        # 解密后的事件结构: {"eventBase": {...}, "eventInfo": {...}}
        event_base = decrypted_data.get('eventBase') or {}
        event_info = decrypted_data.get('eventInfo') or {}
        
        event_type = (event_base.get('eventType') or 
                     event_base.get('event_type') or
                     decrypted_data.get('eventType') or 
                     decrypted_data.get('event_type'))
        msg_type = decrypted_data.get('msgType') or decrypted_data.get('msg_type')
        
        # 处理 URL 验证请求 - 返回加密的 "success"
        if (event_type == 'url_verify' or 
            decrypted_data.get('type') == 'url_verify' or
            msg_type == 'url_verify'):
            
            logger.info("收到海康 URL 验证请求，返回加密响应...")
            
            # 如果请求是加密的，响应也需要加密
            if is_encrypted:
                response_data = decryptor.encrypt_response("success")
                logger.info(f"URL 验证响应(加密): {json.dumps(response_data)}")
                return jsonify(response_data)
            else:
                # 明文响应
                logger.info("URL 验证响应(明文): success")
                return jsonify({"data": "success"})
        
        if not event_type:
            logger.warning(f"无法识别事件类型，数据: {json.dumps(decrypted_data, ensure_ascii=False)}")
            # 对于无法识别的事件，也返回成功，避免海康重试
            return jsonify({'code': 0, 'msg': 'success'})
        
        # 处理不同类型的事件
        # 从 eventInfo 中获取业务数据
        event_data = event_info if event_info else decrypted_data
        
        if event_type == 'motion_detection':
            handle_motion_detection(event_data)
        elif event_type == 'capture_result':
            handle_capture_result(event_data)
        elif event_type == 'device_status':
            handle_device_status(event_data)
        elif event_type == 'grass_alarm':
            handle_grass_alarm(event_data)
        else:
            logger.warning(f"未知事件类型: {event_type}")
        
        # 返回成功响应
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {'timestamp': datetime.now().isoformat()}
        })
        
    except Exception as e:
        logger.error(f"处理回调异常: {e}", exc_info=True)
        db.session.rollback()
        # 即使处理异常，也返回 200，避免海康无限重试
        return jsonify({'code': 0, 'msg': 'received'}), 200


@callback_bp.route('', methods=['GET'])
def verify_callback():
    """
    验证回调地址
    海康互联配置回调URL时会先发送GET请求验证
    支持海康的 URL 验证协议（msg_signature, timestamp, nonce, echo_str）
    """
    try:
        # 获取海康验证参数
        msg_signature = request.args.get('msg_signature')
        timestamp = request.args.get('timestamp')
        nonce = request.args.get('nonce')
        echo_str = request.args.get('echo_str')
        
        # 如果有海康验证参数，进行验证
        if msg_signature and timestamp and nonce and echo_str:
            logger.info(f"收到海康 URL 验证请求: timestamp={timestamp}")
            decrypted_echo = decryptor.verify_url(msg_signature, timestamp, nonce, echo_str)
            if decrypted_echo:
                return decrypted_echo, 200
            else:
                return jsonify({'code': 400, 'msg': 'Verification failed'}), 400
        
        # 普通验证请求
        return jsonify({
            'code': 0,
            'msg': 'Callback URL is valid',
            'data': {
                'service': 'Hikvision Cloud Backend',
                'status': 'running',
                'timestamp': datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"验证回调地址异常: {e}")
        return jsonify({'code': 500, 'msg': str(e)}), 500


def handle_motion_detection(data):
    """处理移动检测告警"""
    # 从 eventInfo 中获取数据，字段名可能是驼峰或下划线格式
    device_serial = data.get('deviceSerial') or data.get('device_serial')
    alarm_time = data.get('alarmTime') or data.get('alarm_time')
    pic_url = data.get('alarmPicUrl') or data.get('alarm_pic_url') or data.get('picUrl')
    
    logger.info(f"移动检测告警: 设备={device_serial}")
    
    # 保存告警记录
    alarm = AlarmRecord(
        device_serial=device_serial,
        alarm_type='motion_detection',
        alarm_time=alarm_time,
        alarm_pic_url=pic_url,
        status='unhandled'
    )
    db.session.add(alarm)
    db.session.commit()
    
    # TODO: 
    # 1. 下载图片
    # 2. AI检测动物
    # 3. 如果检测到动物，保存检测记录
    # 4. 发送通知（微信/短信）


def handle_capture_result(data):
    """处理抓拍结果"""
    device_serial = data.get('deviceSerial') or data.get('device_serial')
    pic_url = data.get('picUrl') or data.get('pic_url')
    capture_time = data.get('captureTime') or data.get('capture_time')
    
    logger.info(f"抓拍结果: 设备={device_serial}, URL={pic_url}")
    
    # 查找设备
    device = Device.query.filter_by(device_serial=device_serial).first()
    if not device:
        logger.warning(f"设备不存在: {device_serial}")
        return
    
    # TODO:
    # 1. 下载图片
    # 2. 动物检测
    # 3. 草量分析
    # 4. 保存检测记录


def handle_device_status(data):
    """处理设备状态变化"""
    device_serial = data.get('deviceSerial') or data.get('device_serial')
    status = data.get('status')  # online/offline
    
    logger.info(f"设备状态变化: {device_serial} -> {status}")
    
    # 更新设备状态
    device = Device.query.filter_by(device_serial=device_serial).first()
    if device:
        device.status = status
        db.session.commit()


def handle_grass_alarm(data):
    """处理草量告警"""
    device_serial = data.get('deviceSerial') or data.get('device_serial')
    coverage = data.get('coverage')  # 草量覆盖率
    
    logger.info(f"草量告警: 设备={device_serial}, 覆盖率={coverage}")
    
    # 保存告警记录
    alarm = AlarmRecord(
        device_serial=device_serial,
        alarm_type='grass_low' if coverage < 20 else 'grass_high',
        alarm_pic_url=data.get('picUrl'),
        status='unhandled'
    )
    db.session.add(alarm)
    db.session.commit()
