#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康云 API - 测试 device/camera/v1/page 接口
"""

import hashlib
import json
import time
import requests

requests.packages.urllib3.disable_warnings()

AK = "2023987187632369716"
SK = "MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBAJLMIOuommDeg+8yY0sNzL8VeOBfLdZkiHjIUZK64Om+S1pVo6SLFT5hNLsip+5nSuvlXo+tgfyzaqbidsCZZQaCM48RViKfFZr7vhTmVDBBO1exrWpacu/wCmwstu9cf//UTM0KO3M/IhJ0qZ713vyMuc7EXUX0yqj/IpDI5S6nAgMBAAECgYB8gOTq+nT088Syeun8HhgpeOysYA1gaKPWzQ9ig11+4gbG9xtz0wKRhaBTl3EWokTJDiDFe0NkMEekgy5066TiNl483a4sU+t/4A1evajpTHsGN9aLDE7xT7rmCwNGCtZrUjlZAWzAIHzA1P7g/4V8DyfThDCVFlMxeKyzxJtmAQJBANJP8n7wGawsXyYOzh7dJxaouDRTHvyhfSbXJlqRcLqF4+msXdeyj1qSWCwYTI92EiT6yuNknSg2o/7SBoWoJGkCQQCyr/CY+tfci/+Au4O+cITeD/Uton9g8Nn1W7O9Uql0mZ7AKNtmF2ZpN+H+lX6fHxktXZWVMufYoBGfDUb6NxiPAkEAqM5oysB3Kr4WxRpfEWDbLhHQgJczKP2J0bIhY9KXU++B5x5l2GrHK6CJSyNZ2FCh8bKnROuORSfObAsyFvfF+QJAeiquHXmK8h/JXTNW/HIjdUuFvmCWJConaof62FrWvoB1OD322tLu0stBOPTusE3rwcd1CJ/YQZQW2B6Uw2e94wJAZtbsaaCeiCmfVPNFwBiTQKYemg/s8xL3Rqhbx4ofoWLnyj+sY+Dtw5sn6XV2eY4d2+jVufz8eoiJszISw8dH5w=="

BASE_URL = "https://open-api.hikiot.com"

def get_token():
    """获取 AccessToken"""
    url = f"{BASE_URL}/auth/exchangeAppToken"
    timestamp = str(int(time.time() * 1000))
    sign = hashlib.md5(f"{AK}{SK}{timestamp}".encode()).hexdigest()
    
    payload = {
        "appKey": AK,
        "appSecret": SK,
        "timestamp": timestamp,
        "signature": sign,
    }
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    
    resp = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
    result = resp.json()
    
    if result.get("code") == 0:
        return result.get("data", {}).get("appAccessToken")
    return None

def test_device_list(token):
    """测试设备列表接口"""
    print("="*60)
    print("获取设备列表")
    print("="*60)
    
    url = f"{BASE_URL}/device/camera/v1/page"
    
    headers = {
        "Content-Type": "application/json",
        "App-Access-Token": token,
    }
    
    # 可能的参数格式
    params_list = [
        {"page": 1, "pageSize": 20},
        {"current": 1, "size": 20},
        {"pageNo": 1, "pageSize": 20},
    ]
    
    for i, params in enumerate(params_list, 1):
        print(f"\n尝试参数格式 {i}: {params}")
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15, verify=False)
            result = resp.json()
            
            print(f"  Status: {resp.status_code}")
            print(f"  Code: {result.get('code')}")
            print(f"  Msg: {result.get('msg', 'N/A')[:100]}")
            
            if result.get("code") == 0:
                print(f"\n  ✅ 成功!")
                print(f"  Response: {json.dumps(result, indent=2, ensure_ascii=False)[:2000]}")
                return result.get("data")
                
        except Exception as e:
            print(f"  Error: {e}")
    
    return None

def test_capture_api(token, device_id):
    """测试抓拍接口"""
    print("\n" + "="*60)
    print(f"设备抓拍: {device_id}")
    print("="*60)
    
    # 可能的抓拍接口
    capture_apis = [
        "/device/camera/v1/capture",
        "/device/capture",
        "/camera/v1/capture",
        "/v1/device/capture",
        "/device/snapshot",
        "/camera/v1/snapshot",
    ]
    
    payload_options = [
        {"deviceSerial": device_id, "channelNo": 1},
        {"deviceId": device_id, "channelNo": 1},
        {"cameraId": device_id, "channelNo": 1},
        {"deviceSerial": device_id},
        {"deviceId": device_id},
    ]
    
    for api_path in capture_apis:
        url = f"{BASE_URL}{api_path}"
        print(f"\n尝试: {api_path}")
        
        headers = {
            "Content-Type": "application/json",
            "App-Access-Token": token,
        }
        
        for j, payload in enumerate(payload_options[:2], 1):
            print(f"  参数 {j}: {payload}")
            
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=15, verify=False)
                result = resp.json()
                
                print(f"    Status: {resp.status_code}")
                print(f"    Code: {result.get('code')}")
                print(f"    Msg: {result.get('msg', 'N/A')[:80]}")
                
                if result.get("code") == 0:
                    print(f"\n    ✅ 抓拍成功!")
                    print(f"    Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
                    return result.get("data")
                    
            except Exception as e:
                print(f"    Error: {str(e)[:50]}")

def main():
    print("="*60)
    print("海康云 API - 设备列表和抓拍测试")
    print("="*60)
    
    # 获取 Token
    print("\n获取 Token...")
    token = get_token()
    
    if not token:
        print("❌ Token 获取失败")
        return
    
    print(f"✅ Token: {token[:40]}...")
    
    # 获取设备列表
    devices = test_device_list(token)
    
    if devices:
        print("\n\n📋 设备列表:")
        records = devices.get("records", []) if isinstance(devices, dict) else devices
        for i, dev in enumerate(records[:10], 1):
            print(f"  [{i}] {dev}")
        
        # 测试抓拍
        if records:
            first = records[0]
            device_id = first.get("deviceSerial") or first.get("deviceId") or first.get("cameraId")
            if device_id:
                test_capture_api(token, device_id)
    else:
        print("\n⚠️ 无法获取设备列表")

if __name__ == "__main__":
    main()
