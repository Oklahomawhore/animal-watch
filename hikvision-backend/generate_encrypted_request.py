#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成加密 GET 请求示例

使用方法:
1. 修改下面的 PRIVATE_KEY 变量，填入你的实际私钥
2. 运行: python3 generate_encrypted_request.py
"""

import base64
import urllib.parse
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

# ==========================================
# 请在这里填入你的实际私钥
# 格式1: 纯 base64 字符串（不含 BEGIN/END 标记）
# 格式2: 完整的 PEM 格式（包含 BEGIN/END 标记）
# ==========================================
PRIVATE_KEY = """
-----BEGIN RSA PRIVATE KEY-----
MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBAJ0lKj8R5bA5lhjF
8yqXxQ8qLnrhRG8UQ0QjB5K6m1jE8vI0X0oWjY4Z3dX2sV5kL7mN9pQ8rT3uJ6w
Y1bK4nH0eF5iC2dA9fG7hE3bB6jC0gD8kH4mA1nF5jB2hE7cA4iD9fB5kH2mE8n
B4jC1hF6dA3gE9iB5mC2jF7dA4hE0kB6nC3iF8dB5jE1mC4hF9dA2iE6nB7jC3h
FAdB4kE2mC5hF8iA3jE7nB9cD1hF4jB6mE0kC2hF5iA7jE3nB8cD4hF1jB9mE2k
C5hF8iA0jE4nB7cD3hF6jB0mE8kC1hF3iA5jE9nB2cD6hF4jB7mE0kC9hF2iA4jE6
nB8cD1hF5jB3mE7kC0hF9iA2jE5nB1cD8hF3jB6mE9kC4hF0iA7jE2nB5cD
-----END RSA PRIVATE KEY-----
"""

def encrypt_get_params(params, private_key_pem):
    """加密 GET 参数"""
    # 加载私钥
    private_key = RSA.import_key(private_key_pem)
    cipher = PKCS1_v1_5.new(private_key)
    
    # 构建参数字符串（按 key 排序，不 URL encode 参数值）
    param_pairs = []
    for key, value in sorted(params.items()):
        param_pairs.append(f"{key}={value}")
    param_string = "&".join(param_pairs)
    
    print(f"原始参数字符串: {param_string}")
    
    # 加密（内部做 URL encode）
    url_encoded = urllib.parse.quote(param_string, safe='')
    print(f"URL encode 后: {url_encoded}")
    
    data_bytes = url_encoded.encode('utf-8')
    print(f"数据长度: {len(data_bytes)} 字节")
    
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
    
    print(f"\nBase64 加密结果 ({len(encrypted_b64)} 字符):")
    print(encrypted_b64)
    
    # URL encode 用于 GET 请求
    query_secret = urllib.parse.quote(encrypted_b64, safe='')
    print(f"\nURL encode 后 ({len(query_secret)} 字符):")
    print(query_secret)
    
    return query_secret

if __name__ == "__main__":
    # 示例 1: 海康官方示例参数
    print("=" * 70)
    print("示例 1: 海康官方示例参数")
    print("=" * 70)
    params1 = {
        "departNos": "BM0001",
        "containsDeletedPerson": "true",
        "beginDate": "2024-08-01",
        "endDate": "2024-08-15"
    }
    query_secret1 = encrypt_get_params(params1, PRIVATE_KEY)
    full_url1 = f"https://open-api.hikiot.com/attendance/export/v1/card/report?querySecret={query_secret1}"
    print(f"\n完整 URL:\n{full_url1}")
    
    # 示例 2: authCode 参数
    print("\n" + "=" * 70)
    print("示例 2: authCode 参数")
    print("=" * 70)
    params2 = {
        "authCode": "2dd3270c36029a3a1e46e7f68130196b"
    }
    query_secret2 = encrypt_get_params(params2, PRIVATE_KEY)
    full_url2 = f"https://open-api.hikiot.com/auth/third/code2Token?querySecret={query_secret2}"
    print(f"\n完整 URL:\n{full_url2}")
    
    # 示例 3: 不加密的明文请求（用于对比）
    print("\n" + "=" * 70)
    print("示例 3: 不加密的明文请求")
    print("=" * 70)
    plain_url = f"https://open-api.hikiot.com/auth/third/code2Token?authCode=2dd3270c36029a3a1e46e7f68130196b"
    print(f"完整 URL:\n{plain_url}")
