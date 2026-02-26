#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康云 API 测试 - 正确的端点
地址: open-api.hikiot.com/auth/exchangeAppToken
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

BASE_URL = "https://open-api.hikiot.com"

def get_token():
    """获取 AccessToken"""
    print("="*60)
    print("获取 AccessToken")
    print("="*60)
    
    url = f"{BASE_URL}/auth/exchangeAppToken"
    
    # 海康签名算法
    timestamp = str(int(time.time() * 1000))
    sign_str = f"{AK}{SK}{timestamp}"
    sign = hashlib.md5(sign_str.encode()).hexdigest()
    
    data = {
        "appKey": AK,
        "appSecret": SK,
        "timestamp": timestamp,
        "signature": sign,
    }
    
    print(f"\nURL: {url}")
    print(f"Timestamp: {timestamp}")
    print(f"Sign: {sign}")
    print(f"\nRequest Data: {json.dumps(data, indent=2)}")
    
    try:
        resp = requests.post(url, json=data, timeout=30, verify=False)
        print(f"\nStatus: {resp.status_code}")
        print(f"Response: {resp.text}")
        
        result = resp.json()
        if result.get("code") in [200, "200"]:
            token = result.get("data", {}).get("accessToken")
            print(f"\n✅ Token 获取成功!")
            print(f"Token: {token}")
            return token
        else:
            print(f"\n⚠️ 失败: {result.get('msg')}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    return None

def get_devices(token):
    """获取设备列表"""
    print("\n" + "="*60)
    print("获取设备列表")
    print("="*60)
    
    url = f"{BASE_URL}/device/list"
    headers = {"accessToken": token}
    params = {"page": 1, "pageSize": 20}
    
    print(f"\nURL: {url}")
    print(f"Headers: {headers}")
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30, verify=False)
        print(f"\nStatus: {resp.status_code}")
        print(f"Response: {resp.text[:2000]}")
        
        result = resp.json()
        if result.get("code") in [200, "200"]:
            devices = result.get("data", {}).get("list", [])
            print(f"\n✅ 找到 {len(devices)} 个设备")
            return devices
        else:
            print(f"\n⚠️ 失败: {result.get('msg')}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    return []

def capture_device(token, device_id):
    """设备抓拍"""
    print("\n" + "="*60)
    print(f"设备抓拍: {device_id}")
    print("="*60)
    
    url = f"{BASE_URL}/device/capture"
    headers = {"accessToken": token}
    data = {
        "deviceSerial": device_id,
        "channelNo": 1,
    }
    
    print(f"\nURL: {url}")
    print(f"Data: {data}")
    
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=30, verify=False)
        print(f"\nStatus: {resp.status_code}")
        print(f"Response: {resp.text}")
        
        result = resp.json()
        if result.get("code") in [200, "200"]:
            pic_url = result.get("data", {}).get("picUrl")
            print(f"\n✅ 抓拍成功!")
            print(f"图片URL: {pic_url}")
            return pic_url
        else:
            print(f"\n⚠️ 失败: {result.get('msg')}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    return None

def main():
    print("="*60)
    print("海康云 API 测试 (正确端点)")
    print("="*60)
    print(f"\nAK: {AK[:20]}...")
    print(f"Endpoint: {BASE_URL}")
    
    # 获取 Token
    token = get_token()
    
    if token:
        # 获取设备列表
        devices = get_devices(token)
        
        if devices:
            print("\n\n设备列表:")
            for i, dev in enumerate(devices[:10], 1):
                print(f"  [{i}] {dev.get('deviceName', 'Unknown')}")
                print(f"      ID: {dev.get('deviceSerial', dev.get('deviceId', 'N/A'))}")
                print(f"      状态: {dev.get('status', 'unknown')}")
            
            # 测试抓拍
            if devices:
                first = devices[0]
                device_id = first.get('deviceSerial') or first.get('deviceId')
                capture_device(token, device_id)
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)

if __name__ == "__main__":
    main()
