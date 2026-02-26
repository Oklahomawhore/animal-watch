#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康云 API 测试 - 尝试更多端点和签名方式
"""

import hashlib
import hmac
import base64
import json
import time
import requests

requests.packages.urllib3.disable_warnings()

AK = "2023987187632369716"
SK = "MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBAJLMIOuommDeg+8yY0sNzL8VeOBfLdZkiHjIUZK64Om+S1pVo6SLFT5hNLsip+5nSuvlXo+tgfyzaqbidsCZZQaCM48RViKfFZr7vhTmVDBBO1exrWpacu/wCmwstu9cf//UTM0KO3M/IhJ0qZ713vyMuc7EXUX0yqj/IpDI5S6nAgMBAAECgYB8gOTq+nT088Syeun8HhgpeOysYA1gaKPWzQ9ig11+4gbG9xtz0wKRhaBTl3EWokTJDiDFe0NkMEekgy5066TiNl483a4sU+t/4A1evajpTHsGN9aLDE7xT7rmCwNGCtZrUjlZAWzAIHzA1P7g/4V8DyfThDCVFlMxeKyzxJtmAQJBANJP8n7wGawsXyYOzh7dJxaouDRTHvyhfSbXJlqRcLqF4+msXdeyj1qSWCwYTI92EiT6yuNknSg2o/7SBoWoJGkCQQCyr/CY+tfci/+Au4O+cITeD/Uton9g8Nn1W7O9Uql0mZ7AKNtmF2ZpN+H+lX6fHxktXZWVMufYoBGfDUb6NxiPAkEAqM5oysB3Kr4WxRpfEWDbLhHQgJczKP2J0bIhY9KXU++B5x5l2GrHK6CJSyNZ2FCh8bKnROuORSfObAsyFvfF+QJAeiquHXmK8h/JXTNW/HIjdUuFvmCWJConaof62FrWvoB1OD322tLu0stBOPTusE3rwcd1CJ/YQZQW2B6Uw2e94wJAZtbsaaCeiCmfVPNFwBiTQKYemg/s8xL3Rqhbx4ofoWLnyj+sY+Dtw5sn6XV2eY4d2+jVufz8eoiJszISw8dH5w=="

# 更多可能的端点
ENDPOINTS = [
    "https://api.hikiot.com",
    "https://api.hikvision.com",
    "https://api.hikvision.com.cn",
    "https://iot.hikvision.com",
    "https://iot.hikvision.com.cn",
    "https://hik-open.hikvision.com",
    "https://open.ys7.com",  # 萤石云
    "https://open.ys7.com.cn",
    "https://api.ys7.com",
    "https://www.hik-online.com",
    "https://www.hik-online.com.cn",
]

def try_endpoint(base_url):
    """尝试单个端点"""
    print(f"\n{'='*60}")
    print(f"测试: {base_url}")
    print('='*60)
    
    # 签名方式1: MD5(appKey + appSecret + timestamp)
    timestamp = str(int(time.time() * 1000))
    sign1 = hashlib.md5(f"{AK}{SK}{timestamp}".encode()).hexdigest()
    
    # 签名方式2: MD5大写
    sign2 = sign1.upper()
    
    # 签名方式3: 带时间戳参数的MD5
    sign3 = hashlib.md5(f"appKey={AK}&appSecret={SK}&timestamp={timestamp}".encode()).hexdigest()
    
    paths = [
        "/v1/token/get",
        "/api/v1/token/get", 
        "/openapi/v1/token/get",
        "/token/get",
    ]
    
    for path in paths:
        url = f"{base_url}{path}"
        print(f"\n  尝试: {path}")
        
        for i, sign in enumerate([sign1, sign2, sign3], 1):
            data = {
                "appKey": AK,
                "timestamp": timestamp,
                "sign": sign,
            }
            
            try:
                resp = requests.post(url, data=data, timeout=10, verify=False)
                print(f"    签名{i}: {resp.status_code}")
                
                if resp.status_code == 200:
                    print(f"    ✅ 成功! Response: {resp.text[:500]}")
                    return True, resp.text
                elif resp.status_code not in [404, 405, 502, 503]:
                    print(f"    Response: {resp.text[:200]}")
                    
            except Exception as e:
                print(f"    签名{i}: Error - {str(e)[:50]}")
    
    return False, None

def main():
    print("="*60)
    print("海康云 API 端点扫描")
    print("="*60)
    print(f"AK: {AK[:20]}...")
    
    found = False
    for endpoint in ENDPOINTS:
        success, response = try_endpoint(endpoint)
        if success:
            found = True
            print(f"\n\n🎉 找到可用端点: {endpoint}")
            print(f"Response: {response[:1000]}")
            break
    
    if not found:
        print("\n\n❌ 所有端点都失败了")
        print("\n建议:")
        print("1. 检查海康互联 APP 中的 API 文档")
        print("2. 确认账号是否已激活开放 API 权限")
        print("3. 联系海康客服获取正确的 API 端点")
        print("4. 使用本地 ISAPI 接口替代")

if __name__ == "__main__":
    main()
