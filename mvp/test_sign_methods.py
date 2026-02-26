#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康云 API 测试 - 尝试不同签名方式
"""

import hashlib
import json
import time
import requests

requests.packages.urllib3.disable_warnings()

AK = "2023987187632369716"
SK = "MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBAJLMIOuommDeg+8yY0sNzL8VeOBfLdZkiHjIUZK64Om+S1pVo6SLFT5hNLsip+5nSuvlXo+tgfyzaqbidsCZZQaCM48RViKfFZr7vhTmVDBBO1exrWpacu/wCmwstu9cf//UTM0KO3M/IhJ0qZ713vyMuc7EXUX0yqj/IpDI5S6nAgMBAAECgYB8gOTq+nT088Syeun8HhgpeOysYA1gaKPWzQ9ig11+4gbG9xtz0wKRhaBTl3EWokTJDiDFe0NkMEekgy5066TiNl483a4sU+t/4A1evajpTHsGN9aLDE7xT7rmCwNGCtZrUjlZAWzAIHzA1P7g/4V8DyfThDCVFlMxeKyzxJtmAQJBANJP8n7wGawsXyYOzh7dJxaouDRTHvyhfSbXJlqRcLqF4+msXdeyj1qSWCwYTI92EiT6yuNknSg2o/7SBoWoJGkCQQCyr/CY+tfci/+Au4O+cITeD/Uton9g8Nn1W7O9Uql0mZ7AKNtmF2ZpN+H+lX6fHxktXZWVMufYoBGfDUb6NxiPAkEAqM5oysB3Kr4WxRpfEWDbLhHQgJczKP2J0bIhY9KXU++B5x5l2GrHK6CJSyNZ2FCh8bKnROuORSfObAsyFvfF+QJAeiquHXmK8h/JXTNW/HIjdUuFvmCWJConaof62FrWvoB1OD322tLu0stBOPTusE3rwcd1CJ/YQZQW2B6Uw2e94wJAZtbsaaCeiCmfVPNFwBiTQKYemg/s8xL3Rqhbx4ofoWLnyj+sY+Dtw5sn6XV2eY4d2+jVufz8eoiJszISw8dH5w=="

BASE_URL = "https://open-api.hikiot.com"

def test_token_methods():
    """测试不同的 Token 获取方式"""
    
    url = f"{BASE_URL}/auth/exchangeAppToken"
    timestamp = str(int(time.time() * 1000))
    
    # 方式1: MD5(appKey + appSecret + timestamp) - 小写
    sign1 = hashlib.md5(f"{AK}{SK}{timestamp}".encode()).hexdigest()
    
    # 方式2: MD5(appKey + appSecret + timestamp) - 大写
    sign2 = sign1.upper()
    
    # 方式3: 带等号的参数
    sign3 = hashlib.md5(f"appKey={AK}&appSecret={SK}&timestamp={timestamp}".encode()).hexdigest()
    
    # 方式4: 只有 appKey + appSecret
    sign4 = hashlib.md5(f"{AK}{SK}".encode()).hexdigest()
    
    methods = [
        ("MD5小写", sign1),
        ("MD5大写", sign2),
        ("参数形式", sign3),
        ("无时间戳", sign4),
    ]
    
    print("="*60)
    print("测试不同的签名方式")
    print("="*60)
    print(f"\nURL: {url}")
    print(f"Timestamp: {timestamp}")
    
    for name, sign in methods:
        print(f"\n[{name}]")
        print(f"  Sign: {sign}")
        
        # 尝试 form-data
        data = {
            "appKey": AK,
            "appSecret": SK,
            "timestamp": timestamp,
            "signature": sign,
        }
        
        try:
            resp = requests.post(url, data=data, timeout=15, verify=False)
            result = resp.json()
            print(f"  Status: {resp.status_code}")
            print(f"  Code: {result.get('code')}")
            print(f"  Msg: {result.get('msg', 'N/A')[:100]}")
            
            if result.get("code") in [200, "200"]:
                print(f"  ✅ 成功!")
                return result.get("data", {}).get("accessToken")
        except Exception as e:
            print(f"  Error: {e}")
    
    return None

def test_other_endpoints():
    """测试其他可能的端点"""
    
    print("\n" + "="*60)
    print("测试其他端点")
    print("="*60)
    
    endpoints = [
        "/auth/token",
        "/v1/auth/token", 
        "/api/auth/token",
        "/oauth/token",
        "/token",
    ]
    
    timestamp = str(int(time.time() * 1000))
    sign = hashlib.md5(f"{AK}{SK}{timestamp}".encode()).hexdigest()
    
    for endpoint in endpoints:
        url = f"{BASE_URL}{endpoint}"
        print(f"\n尝试: {endpoint}")
        
        data = {
            "appKey": AK,
            "appSecret": SK,
            "timestamp": timestamp,
            "signature": sign,
        }
        
        try:
            resp = requests.post(url, data=data, timeout=10, verify=False)
            print(f"  Status: {resp.status_code}")
            print(f"  Response: {resp.text[:200]}")
        except Exception as e:
            print(f"  Error: {str(e)[:50]}")

def main():
    print("="*60)
    print("海康云 API - 签名方式测试")
    print("="*60)
    print(f"\nAK: {AK[:25]}...")
    print(f"SK: {SK[:40]}...")
    
    token = test_token_methods()
    
    if token:
        print(f"\n\n✅ 获取到 Token: {token[:30]}...")
    else:
        print("\n\n❌ 所有签名方式都失败了")
        test_other_endpoints()
        
        print("\n" + "="*60)
        print("问题分析:")
        print("="*60)
        print("错误码 400004: 无权限")
        print("这意味着:")
        print("1. 你的 AK/SK 没有在开放平台开通 API 权限")
        print("2. 需要在海康互联 APP 中申请开放 API 权限")
        print("3. 或者 AK/SK 类型不支持这个 API")
        print("\n解决方案:")
        print("1. 在海康互联 APP 中检查 API 权限设置")
        print("2. 联系海康客服开通 [身份及授权] 权限")
        print("3. 使用本地 ISAPI 接口替代")

if __name__ == "__main__":
    main()
