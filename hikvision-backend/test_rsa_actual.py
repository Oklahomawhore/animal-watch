#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试海康 RSA 加密 - 使用实际私钥
"""

import sys
import os
import base64
import urllib.parse
sys.path.insert(0, '/Users/wangshuzhu/.openclaw/workspace/lin-she-health-monitor/hikvision-backend')

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

# 从环境变量读取实际私钥
APP_SECRET = os.getenv('HIK_APP_SECRET', '')

if not APP_SECRET:
    print("请设置 HIK_APP_SECRET 环境变量")
    print("export HIK_APP_SECRET='你的应用密钥'")
    sys.exit(1)

# 包装成 PEM 格式
if '-----BEGIN' not in APP_SECRET:
    PRIVATE_KEY_PEM = f"-----BEGIN RSA PRIVATE KEY-----\n{APP_SECRET}\n-----END RSA PRIVATE KEY-----"
else:
    PRIVATE_KEY_PEM = APP_SECRET

def test_encrypt_authcode(auth_code):
    """测试加密 authCode"""
    print("=" * 60)
    print(f"测试加密 authCode: {auth_code[:20]}...")
    print("=" * 60)
    
    # 加载私钥
    private_key = RSA.import_key(PRIVATE_KEY_PEM)
    print(f"\n私钥信息:")
    print(f"  密钥大小: {private_key.size_in_bits()} bits")
    print(f"  n: {hex(private_key.n)[:30]}...")
    
    # 构建参数字符串
    param_string = f"authCode={auth_code}"
    print(f"\n原始字符串: {param_string}")
    print(f"  长度: {len(param_string)} 字符")
    
    # 海康官方代码: 先 URL encode
    url_encoded = urllib.parse.quote(param_string, safe='')
    print(f"\nURL编码后: {url_encoded}")
    print(f"  长度: {len(url_encoded)} 字符")
    
    # 加密
    data_bytes = url_encoded.encode('utf-8')
    cipher = PKCS1_v1_5.new(private_key)
    
    # 分段加密
    MAX_BLOCK = 117
    encrypted_blocks = []
    for i in range(0, len(data_bytes), MAX_BLOCK):
        block = data_bytes[i:i+MAX_BLOCK]
        encrypted_block = cipher.encrypt(block)
        encrypted_blocks.append(encrypted_block)
        print(f"  块 {len(encrypted_blocks)}: {len(block)} 字节 -> {len(encrypted_block)} 字节")
    
    full_encrypted = b''.join(encrypted_blocks)
    encrypted_b64 = base64.b64encode(full_encrypted).decode('utf-8')
    
    print(f"\nBase64 加密结果:")
    print(f"  长度: {len(encrypted_b64)} 字符")
    print(f"  内容: {encrypted_b64}")
    
    # URL encode 用于 GET 请求
    url_encoded_result = urllib.parse.quote(encrypted_b64, safe='')
    print(f"\nURL encode 后 (用于 querySecret):")
    print(f"  长度: {len(url_encoded_result)} 字符")
    print(f"  内容: {url_encoded_result[:100]}...")
    
    # 完整 URL
    full_url = f"https://open-api.hikiot.com/auth/third/code2Token?querySecret={url_encoded_result}"
    print(f"\n完整请求 URL:")
    print(f"  {full_url[:120]}...")
    
    return encrypted_b64, url_encoded_result

if __name__ == "__main__":
    # 使用示例 authCode 测试
    test_authcode = "2dd3270c36029a3a1e46e7f68130196b"
    test_encrypt_authcode(test_authcode)
