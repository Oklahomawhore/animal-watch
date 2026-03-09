#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试海康 RSA 加密功能
"""

import os
import sys
import json

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.rsa_encryptor import HikvisionRSAEncryptor


def test_encryption():
    """测试 RSA 加密功能"""
    
    # 从环境变量读取私钥（优先 HIK_PRIVATE_KEY，其次 HIK_APP_SECRET）
    private_key = os.getenv('HIK_PRIVATE_KEY') or os.getenv('HIK_APP_SECRET')
    
    if not private_key:
        print("❌ 错误: 未设置 HIK_APP_SECRET 或 HIK_PRIVATE_KEY 环境变量")
        print("请确保 .env 文件中包含:")
        print("  HIK_APP_KEY=your_app_key")
        print("  HIK_APP_SECRET=your_app_secret  (这就是 RSA 私钥)")
        return False
    
    print("=" * 60)
    print("海康互联 RSA 加密测试")
    print("=" * 60)
    
    try:
        # 创建加密器
        print("\n1. 初始化 RSA 加密器...")
        encryptor = HikvisionRSAEncryptor(private_key)
        print("✅ RSA 私钥加载成功")
        
        # 测试 GET 参数加密
        print("\n2. 测试 GET 参数加密...")
        test_params = {
            "departNos": "BM0001",
            "containsDeletedPerson": True,
            "beginDate": "2024-08-01",
            "endDate": "2024-08-15"
        }
        
        encrypted_query = encryptor.encrypt_get_params(test_params)
        print(f"原始参数: {json.dumps(test_params, ensure_ascii=False)}")
        print(f"加密后 querySecret: {encrypted_query[:80]}...")
        print("✅ GET 参数加密成功")
        
        # 测试 POST 请求体加密
        print("\n3. 测试 POST 请求体加密...")
        test_body = {
            "holidayType": "测试请假类型",
            "holidayUnit": 1,
            "hourForDay": 8,
            "holidayRule": 1,
            "durationCalculateType": 0
        }
        
        encrypted_body = encryptor.encrypt_post_body(test_body)
        print(f"原始请求体: {json.dumps(test_body, ensure_ascii=False)}")
        print(f"加密后 bodySecret: {encrypted_body['bodySecret'][:80]}...")
        print("✅ POST 请求体加密成功")
        
        # 测试空参数
        print("\n4. 测试空参数处理...")
        empty_params = {}
        encrypted_empty = encryptor.encrypt_get_params(empty_params)
        print(f"空参数加密结果: {encrypted_empty}")
        print("✅ 空参数处理成功")
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过！RSA 加密功能正常")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_call():
    """测试实际 API 调用（需要有效的 app_key 和 app_secret）"""
    
    from services.hikcloud import HikvisionCloudAPI
    
    app_key = os.getenv('HIK_APP_KEY')
    app_secret = os.getenv('HIK_APP_SECRET')
    private_key = os.getenv('HIK_PRIVATE_KEY')
    
    if not all([app_key, app_secret, private_key]):
        print("\n⚠️  跳过 API 调用测试（缺少必要的环境变量）")
        print("需要设置: HIK_APP_KEY, HIK_APP_SECRET")
        return
    
    print("\n" + "=" * 60)
    print("测试实际 API 调用")
    print("=" * 60)
    
    try:
        # 创建 API 客户端
        print("\n1. 创建 API 客户端...")
        api = HikvisionCloudAPI(app_key, app_secret, private_key)
        print("✅ API 客户端创建成功")
        
        # 获取设备列表
        print("\n2. 获取设备列表...")
        devices = api.get_device_list(page=1, page_size=10)
        print(f"获取到 {len(devices)} 个设备")
        if devices:
            print(f"第一个设备: {devices[0].get('deviceSerial', 'N/A')}")
        print("✅ 设备列表获取成功")
        
        print("\n" + "=" * 60)
        print("✅ API 调用测试通过！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ API 调用失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 加载 .env 文件
    try:
        from dotenv import load_dotenv
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        if os.path.exists(env_path):
            load_dotenv(env_path)
            print(f"✅ 已加载环境变量: {env_path}")
    except ImportError:
        print("⚠️  未安装 python-dotenv，跳过 .env 文件加载")
    
    # 运行测试
    success = test_encryption()
    
    if success:
        test_api_call()
    
    sys.exit(0 if success else 1)
