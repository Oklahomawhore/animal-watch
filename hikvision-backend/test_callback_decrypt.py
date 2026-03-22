#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试海康回调解密
支持 AES 和 RSA 两种加密方式
"""

import os
import sys
import json
import base64
import urllib.parse

# 添加项目路径
sys.path.insert(0, '/Users/wangshuzhu/.openclaw/workspace/lin-she-health-monitor/hikvision-backend')

from services.decryptor import decryptor
from services.rsa_encryptor import encryptor

# 测试数据（请替换为实际的回调数据）
test_encrypt_data = ""  # 填入海康发送的 encrypt 字段值

def test_aes_decrypt(encrypt_data):
    """测试 AES 解密"""
    print("=" * 50)
    print("测试 AES 解密...")
    print(f"Encrypt Key: {decryptor.encrypt_key}")
    print(f"密文长度: {len(encrypt_data)}")
    
    try:
        result = decryptor.decrypt_event(encrypt_data)
        if result:
            print(f"✅ AES 解密成功!")
            print(f"解密结果: {result[:200]}...")
            return json.loads(result)
        else:
            print("❌ AES 解密失败")
            return None
    except Exception as e:
        print(f"❌ AES 解密异常: {e}")
        return None

def test_rsa_decrypt(encrypt_data):
    """测试 RSA 解密"""
    print("=" * 50)
    print("测试 RSA 解密...")
    print(f"私钥已配置: {encryptor.private_key_pem is not None}")
    print(f"密文长度: {len(encrypt_data)}")
    
    try:
        result = encryptor.decrypt_response(encrypt_data)
        if result:
            print(f"✅ RSA 解密成功!")
            print(f"解密结果: {result[:200]}...")
            return json.loads(result)
        else:
            print("❌ RSA 解密失败")
            return None
    except Exception as e:
        print(f"❌ RSA 解密异常: {e}")
        return None

if __name__ == "__main__":
    # 从环境变量读取测试数据
    test_data = os.getenv('TEST_ENCRYPT_DATA', test_encrypt_data)
    
    if not test_data:
        print("请设置 TEST_ENCRYPT_DATA 环境变量，或修改脚本中的 test_encrypt_data")
        print("\n使用方法:")
        print("export TEST_ENCRYPT_DATA='海康发送的encrypt字段值'")
        print("python test_callback_decrypt.py")
        sys.exit(1)
    
    print("海康回调解密测试")
    print(f"测试密文: {test_data[:50]}...")
    
    # 尝试 AES 解密
    aes_result = test_aes_decrypt(test_data)
    
    # 尝试 RSA 解密
    rsa_result = test_rsa_decrypt(test_data)
    
    print("\n" + "=" * 50)
    print("测试结果汇总:")
    if aes_result:
        print("✅ 使用 AES 解密成功")
        print(f"结果: {json.dumps(aes_result, ensure_ascii=False, indent=2)}")
    elif rsa_result:
        print("✅ 使用 RSA 解密成功")
        print(f"结果: {json.dumps(rsa_result, ensure_ascii=False, indent=2)}")
    else:
        print("❌ AES 和 RSA 解密都失败")
        print("\n可能原因:")
        print("1. Encrypt Key / App Secret 配置错误")
        print("2. 密文格式不正确")
        print("3. 海康使用了其他加密方式")
