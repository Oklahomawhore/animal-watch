#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康云 API 完整测试 - 设备列表获取
"""

import hashlib
import hmac
import base64
import json
import time
import requests
from datetime import datetime, timezone
from urllib.parse import urlencode, quote

requests.packages.urllib3.disable_warnings()

# 用户提供的 AK/SK
AK = "2023987187632369716"
SK = "MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBAJLMIOuommDeg+8yY0sNzL8VeOBfLdZkiHjIUZK64Om+S1pVo6SLFT5hNLsip+5nSuvlXo+tgfyzaqbidsCZZQaCM48RViKfFZr7vhTmVDBBO1exrWpacu/wCmwstu9cf//UTM0KO3M/IhJ0qZ713vyMuc7EXUX0yqj/IpDI5S6nAgMBAAECgYB8gOTq+nT088Syeun8HhgpeOysYA1gaKPWzQ9ig11+4gbG9xtz0wKRhaBTl3EWokTJDiDFe0NkMEekgy5066TiNl483a4sU+t/4A1evajpTHsGN9aLDE7xT7rmCwNGCtZrUjlZAWzAIHzA1P7g/4V8DyfThDCVFlMxeKyzxJtmAQJBANJP8n7wGawsXyYOzh7dJxaouDRTHvyhfSbXJlqRcLqF4+msXdeyj1qSWCwYTI92EiT6yuNknSg2o/7SBoWoJGkCQQCyr/CY+tfci/+Au4O+cITeD/Uton9g8Nn1W7O9Uql0mZ7AKNtmF2ZpN+H+lX6fHxktXZWVMufYoBGfDUb6NxiPAkEAqM5oysB3Kr4WxRpfEWDbLhHQgJczKP2J0bIhY9KXU++B5x5l2GrHK6CJSyNZ2FCh8bKnROuORSfObAsyFvfF+QJAeiquHXmK8h/JXTNW/HIjdUuFvmCWJConaof62FrWvoB1OD322tLu0stBOPTusE3rwcd1CJ/YQZQW2B6Uw2e94wJAZtbsaaCeiCmfVPNFwBiTQKYemg/s8xL3Rqhbx4ofoWLnyj+sY+Dtw5sn6XV2eY4d2+jVufz8eoiJszISw8dH5w=="

# 可能的 API 端点
ENDPOINTS = [
    "https://api.hikiot.com",
    "https://open.hikiot.com",
    "https://openapi.hikiot.com",
    "https://api.hikvision.com",
    "https://open.hikvision.com",
]

def test_endpoint(base_url):
    """测试单个端点"""
    print(f"\n{'='*60}")
    print(f"测试端点: {base_url}")
    print('='*60)
    
    session = requests.Session()
    
    # 测试1: Token 接口 (方式1 - 海康标准签名)
    print("\n[1] 测试 Token 接口 (MD5签名)...")
    
    timestamp = str(int(time.time() * 1000))
    
    # 海康签名算法: MD5(appKey + appSecret + timestamp)
    sign_str = f"{AK}{SK}{timestamp}"
    sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()
    
    url = f"{base_url}/v1/token/get"
    data = {
        "appKey": AK,
        "timestamp": timestamp,
        "sign": sign,
    }
    
    print(f"  URL: {url}")
    print(f"  Timestamp: {timestamp}")
    print(f"  Sign: {sign[:30]}...")
    
    try:
        resp = session.post(url, data=data, timeout=15, verify=False)
        print(f"  Status: {resp.status_code}")
        print(f"  Response: {resp.text[:500]}")
        
        if resp.status_code == 200:
            try:
                result = resp.json()
                if result.get("code") in [200, "200"]:
                    token = result.get("data", {}).get("accessToken")
                    print(f"\n  ✅ Token 获取成功!")
                    print(f"  Token: {token[:30]}...")
                    return token
            except:
                pass
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # 测试2: Token 接口 (方式2 - 大写签名)
    print("\n[2] 测试 Token 接口 (MD5大写)...")
    sign_upper = sign.upper()
    data["sign"] = sign_upper
    
    try:
        resp = session.post(url, data=data, timeout=15, verify=False)
        print(f"  Status: {resp.status_code}")
        print(f"  Response: {resp.text[:500]}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # 测试3: GET 方式
    print("\n[3] 测试 Token 接口 (GET)...")
    try:
        resp = session.get(url, params=data, timeout=15, verify=False)
        print(f"  Status: {resp.status_code}")
        print(f"  Response: {resp.text[:500]}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    # 测试4: JSON body
    print("\n[4] 测试 Token 接口 (JSON)...")
    try:
        headers = {"Content-Type": "application/json"}
        resp = session.post(url, json=data, headers=headers, timeout=15, verify=False)
        print(f"  Status: {resp.status_code}")
        print(f"  Response: {resp.text[:500]}")
    except Exception as e:
        print(f"  ❌ Error: {e}")
    
    return None

def test_with_token(base_url, token):
    """使用 Token 测试设备列表"""
    print(f"\n{'='*60}")
    print(f"使用 Token 测试设备列表")
    print('='*60)
    
    session = requests.Session()
    
    # 测试1: 设备列表
    print("\n[1] 获取设备列表...")
    
    endpoints = [
        "/v1/device/list",
        "/v1/devices",
        "/v1/device/query",
    ]
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        headers = {"accessToken": token}
        
        print(f"\n  尝试: {endpoint}")
        print(f"  URL: {url}")
        
        try:
            resp = session.get(url, headers=headers, timeout=15, verify=False)
            print(f"  Status: {resp.status_code}")
            print(f"  Response: {resp.text[:800]}")
            
            if resp.status_code == 200:
                try:
                    result = resp.json()
                    if result.get("code") in [200, "200"]:
                        print(f"\n  ✅ 成功!")
                        return result
                except:
                    pass
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    return None

def test_snapshot(base_url, token, device_id):
    """测试设备抓拍"""
    print(f"\n{'='*60}")
    print(f"测试设备抓拍")
    print('='*60)
    
    session = requests.Session()
    
    endpoints = [
        "/v1/device/capture",
        "/v1/capture",
        "/v1/snapshot",
    ]
    
    for endpoint in endpoints:
        url = f"{base_url}{endpoint}"
        headers = {"accessToken": token}
        data = {
            "deviceSerial": device_id,
            "channelNo": 1,
        }
        
        print(f"\n  尝试: {endpoint}")
        print(f"  Device: {device_id}")
        
        try:
            resp = session.post(url, data=data, headers=headers, timeout=15, verify=False)
            print(f"  Status: {resp.status_code}")
            print(f"  Response: {resp.text[:800]}")
            
            if resp.status_code == 200:
                try:
                    result = resp.json()
                    if result.get("code") in [200, "200"]:
                        print(f"\n  ✅ 抓拍成功!")
                        return result
                except:
                    pass
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    return None

def main():
    print("="*60)
    print("海康云 API 完整测试")
    print("="*60)
    print(f"\nAK: {AK[:25]}...")
    print(f"SK: {SK[:40]}... (长度: {len(SK)})")
    
    # 测试所有端点
    working_token = None
    working_endpoint = None
    
    for endpoint in ENDPOINTS:
        token = test_endpoint(endpoint)
        if token:
            working_token = token
            working_endpoint = endpoint
            break
    
    if working_token:
        print(f"\n\n{'='*60}")
        print(f"✅ 找到可用端点: {working_endpoint}")
        print(f"✅ Token: {working_token[:30]}...")
        print('='*60)
        
        # 获取设备列表
        devices_result = test_with_token(working_endpoint, working_token)
        
        if devices_result:
            print("\n\n📋 设备列表:")
            print(json.dumps(devices_result, indent=2, ensure_ascii=False))
            
            # 如果有设备，测试抓拍
            devices = devices_result.get("data", {}).get("list", [])
            if devices:
                first_device = devices[0]
                device_id = first_device.get("deviceSerial") or first_device.get("deviceId")
                if device_id:
                    print(f"\n\n测试设备 {device_id} 抓拍...")
                    snapshot_result = test_snapshot(working_endpoint, working_token, device_id)
                    if snapshot_result:
                        print("\n✅ 抓拍成功!")
                        print(json.dumps(snapshot_result, indent=2, ensure_ascii=False))
    else:
        print("\n\n❌ 所有端点都无法获取 Token")
        print("\n可能原因:")
        print("1. AK/SK 不正确")
        print("2. 签名算法不正确")
        print("3. 网络问题")
        print("4. API 端点已变更")

if __name__ == "__main__":
    main()
