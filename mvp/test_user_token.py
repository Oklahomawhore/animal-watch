#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康云 API - 获取 User-Access-Token
"""

import hashlib
import json
import time
import requests

requests.packages.urllib3.disable_warnings()

AK = "2023987187632369716"
SK = "MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBAJLMIOuommDeg+8yY0sNzL8VeOBfLdZkiHjIUZK64Om+S1pVo6SLFT5hNLsip+5nSuvlXo+tgfyzaqbidsCZZQaCM48RViKfFZr7vhTmVDBBO1exrWpacu/wCmwstu9cf//UTM0KO3M/IhJ0qZ713vyMuc7EXUX0yqj/IpDI5S6nAgMBAAECgYB8gOTq+nT088Syeun8HhgpeOysYA1gaKPWzQ9ig11+4gbG9xtz0wKRhaBTl3EWokTJDiDFe0NkMEekgy5066TiNl483a4sU+t/4A1evajpTHsGN9aLDE7xT7rmCwNGCtZrUjlZAWzAIHzA1P7g/4V8DyfThDCVFlMxeKyzxJtmAQJBANJP8n7wGawsXyYOzh7dJxaouDRTHvyhfSbXJlqRcLqF4+msXdeyj1qSWCwYTI92EiT6yuNknSg2o/7SBoWoJGkCQQCyr/CY+tfci/+Au4O+cITeD/Uton9g8Nn1W7O9Uql0mZ7AKNtmF2ZpN+H+lX6fHxktXZWVMufYoBGfDUb6NxiPAkEAqM5oysB3Kr4WxRpfEWDbLhHQgJczKP2J0bIhY9KXU++B5x5l2GrHK6CJSyNZ2FCh8bKnROuORSfObAsyFvfF+QJAeiquHXmK8h/JXTNW/HIjdUuFvmCWJConaof62FrWvoB1OD322tLu0stBOPTusE3rwcd1CJ/YQZQW2B6Uw2e94wJAZtbsaaCeiCmfVPNFwBiTQKYemg/s8xL3Rqhbx4ofoWLnyj+sY+Dtw5sn6XV2eY4d2+jVufz8eoiJszISw8dH5w=="

BASE_URL = "https://open-api.hikiot.com"
APP_TOKEN = "at-GmJzaRSFX8tOWRZzaRHBVTraecreS7IlLlJ6vEfE"

def get_user_token():
    """获取 User-Access-Token"""
    print("="*60)
    print("获取 User-Access-Token")
    print("="*60)
    
    # 可能的接口
    endpoints = [
        "/auth/exchangeUserToken",
        "/auth/userToken",
        "/user/token",
        "/v1/auth/userToken",
        "/auth/getUserToken",
    ]
    
    timestamp = str(int(time.time() * 1000))
    sign = hashlib.md5(f"{AK}{SK}{timestamp}".encode()).hexdigest()
    
    for endpoint in endpoints:
        url = f"{BASE_URL}{endpoint}"
        print(f"\n尝试: {endpoint}")
        
        payload = {
            "appKey": AK,
            "appSecret": SK,
            "timestamp": timestamp,
            "signature": sign,
        }
        
        headers = {
            "Content-Type": "application/json",
            "App-Access-Token": APP_TOKEN,
        }
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15, verify=False)
            result = resp.json()
            
            print(f"  Status: {resp.status_code}")
            print(f"  Code: {result.get('code')}")
            print(f"  Msg: {result.get('msg', 'N/A')[:100]}")
            
            if result.get("code") == 0:
                user_token = result.get("data", {}).get("userAccessToken") or result.get("data", {}).get("accessToken")
                if user_token:
                    print(f"\n  ✅ User Token 获取成功!")
                    print(f"  Token: {user_token}")
                    return user_token
                    
        except Exception as e:
            print(f"  Error: {str(e)[:50]}")
    
    return None

def test_device_list_with_user_token(user_token):
    """使用 User Token 获取设备列表"""
    print("\n" + "="*60)
    print("使用 User Token 获取设备列表")
    print("="*60)
    
    url = f"{BASE_URL}/device/camera/v1/page"
    
    headers = {
        "Content-Type": "application/json",
        "App-Access-Token": APP_TOKEN,
        "User-Access-Token": user_token,
    }
    
    params = {"page": 1, "pageSize": 20}
    
    print(f"\nURL: {url}")
    print(f"Headers: {headers}")
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15, verify=False)
        result = resp.json()
        
        print(f"\nStatus: {resp.status_code}")
        print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)[:2000]}")
        
        if result.get("code") == 0:
            print(f"\n✅ 成功!")
            return result.get("data")
            
    except Exception as e:
        print(f"\nError: {e}")
    
    return None

def main():
    print("="*60)
    print("海康云 API - User Token 测试")
    print("="*60)
    
    # 获取 User Token
    user_token = get_user_token()
    
    if user_token:
        # 使用 User Token 获取设备列表
        devices = test_device_list_with_user_token(user_token)
        
        if devices:
            print("\n\n📋 设备列表:")
            print(json.dumps(devices, indent=2, ensure_ascii=False))
    else:
        print("\n❌ 无法获取 User Token")
        print("\n可能原因:")
        print("1. 不需要单独获取 User Token，账号就是用户")
        print("2. 需要其他认证方式（如手机号+验证码）")
        print("3. 使用 App Token 的某个字段作为 User Token")

if __name__ == "__main__":
    main()
