#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康互联 API RSA 加密使用示例
"""

import os
from services.hikcloud import HikvisionCloudAPI

# ============ 配置 ============
# 请替换为你的实际配置
APP_KEY = os.getenv('HIK_APP_KEY', 'your_app_key')
APP_SECRET = os.getenv('HIK_APP_SECRET', 'your_app_secret')
# RSA 私钥就是 APP_SECRET，无需额外配置
PRIVATE_KEY = os.getenv('HIK_PRIVATE_KEY') or APP_SECRET


def example_get_request():
    """GET 请求示例 - 获取设备列表"""
    print("=" * 60)
    print("示例1: GET 请求（获取设备列表）")
    print("=" * 60)
    
    # 创建 API 客户端
    api = HikvisionCloudAPI(APP_KEY, APP_SECRET, PRIVATE_KEY)
    
    # 调用 API - 参数会自动加密
    # 实际发送的请求:
    # GET /device/camera/v1/page?querySecret=加密后的参数
    devices = api.get_device_list(page=1, page_size=10)
    
    print(f"获取到 {len(devices)} 个设备")
    for device in devices[:3]:  # 只显示前3个
        print(f"  - {device.get('deviceSerial')}: {device.get('deviceName')}")
    
    return devices


def example_post_request():
    """POST 请求示例 - 设备抓拍"""
    print("\n" + "=" * 60)
    print("示例2: POST 请求（设备抓拍）")
    print("=" * 60)
    
    api = HikvisionCloudAPI(APP_KEY, APP_SECRET, PRIVATE_KEY)
    
    # 调用 API - body 会自动加密
    # 实际发送的请求体:
    # {"bodySecret": "加密后的JSON"}
    device_serial = "D12345678"  # 替换为实际设备序列号
    pic_url = api.capture_device(device_serial, channel_no=1)
    
    if pic_url:
        print(f"抓拍成功，图片URL: {pic_url}")
    else:
        print("抓拍失败或设备不存在")
    
    return pic_url


def example_manual_encryption():
    """手动加密示例"""
    print("\n" + "=" * 60)
    print("示例3: 手动加密参数")
    print("=" * 60)
    
    from services.rsa_encryptor import HikvisionRSAEncryptor
    
    # 创建加密器
    encryptor = HikvisionRSAEncryptor(PRIVATE_KEY)
    
    # 手动加密 GET 参数
    params = {
        "departNos": "BM0001",
        "beginDate": "2024-08-01",
        "endDate": "2024-08-15"
    }
    
    encrypted = encryptor.encrypt_get_params(params)
    print(f"原始参数: {params}")
    print(f"加密后的 querySecret:\n{encrypted}")
    
    # 构建完整 URL
    base_url = "https://open-api.hikiot.com/attendance/export/v1/card/report"
    full_url = f"{base_url}?querySecret={encrypted}"
    print(f"\n完整请求 URL:\n{full_url[:120]}...")


def example_manual_post_encryption():
    """手动加密 POST 请求体示例"""
    print("\n" + "=" * 60)
    print("示例4: 手动加密 POST 请求体")
    print("=" * 60)
    
    from services.rsa_encryptor import HikvisionRSAEncryptor
    
    encryptor = HikvisionRSAEncryptor(PRIVATE_KEY)
    
    # 原始请求体
    body = {
        "holidayType": "年假",
        "holidayUnit": 1,
        "hourForDay": 8
    }
    
    # 加密
    encrypted_body = encryptor.encrypt_post_body(body)
    
    print(f"原始请求体: {body}")
    print(f"加密后的请求体:\n{encrypted_body}")


if __name__ == "__main__":
    # 加载 .env 文件
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    # 检查配置
    if APP_KEY == 'your_app_key' or not os.getenv('HIK_APP_KEY'):
        print("⚠️  请先设置环境变量 HIK_APP_KEY, HIK_APP_SECRET, HIK_PRIVATE_KEY")
        print("或者修改本文件中的配置")
        exit(1)
    
    # 运行示例
    try:
        example_manual_encryption()
        example_manual_post_encryption()
        # example_get_request()  # 需要有效的 app_key/secret
        # example_post_request()  # 需要有效的 app_key/secret
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
