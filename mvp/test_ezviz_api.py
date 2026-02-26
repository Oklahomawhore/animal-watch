#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
萤石云 API 测试 - 找到了可用端点
"""

import hashlib
import json
import time
import requests

requests.packages.urllib3.disable_warnings()

AK = "2023987187632369716"
SK = "MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBAJLMIOuommDeg+8yY0sNzL8VeOBfLdZkiHjIUZK64Om+S1pVo6SLFT5hNLsip+5nSuvlXo+tgfyzaqbidsCZZQaCM48RViKfFZr7vhTmVDBBO1exrWpacu/wCmwstu9cf//UTM0KO3M/IhJ0qZ713vyMuc7EXUX0yqj/IpDI5S6nAgMBAAECgYB8gOTq+nT088Syeun8HhgpeOysYA1gaKPWzQ9ig11+4gbG9xtz0wKRhaBTl3EWokTJDiDFe0NkMEekgy5066TiNl483a4sU+t/4A1evajpTHsGN9aLDE7xT7rmCwNGCtZrUjlZAWzAIHzA1P7g/4V8DyfThDCVFlMxeKyzxJtmAQJBANJP8n7wGawsXyYOzh7dJxaouDRTHvyhfSbXJlqRcLqF4+msXdeyj1qSWCwYTI92EiT6yuNknSg2o/7SBoWoJGkCQQCyr/CY+tfci/+Au4O+cITeD/Uton9g8Nn1W7O9Uql0mZ7AKNtmF2ZpN+H+lX6fHxktXZWVMufYoBGfDUb6NxiPAkEAqM5oysB3Kr4WxRpfEWDbLhHQgJczKP2J0bIhY9KXU++B5x5l2GrHK6CJSyNZ2FCh8bKnROuORSfObAsyFvfF+QJAeiquHXmK8h/JXTNW/HIjdUuFvmCWJConaof62FrWvoB1OD322tLu0stBOPTusE3rwcd1CJ/YQZQW2B6Uw2e94wJAZtbsaaCeiCmfVPNFwBiTQKYemg/s8xL3Rqhbx4ofoWLnyj+sY+Dtw5sn6XV2eY4d2+jVufz8eoiJszISw8dH5w=="

BASE_URL = "https://open.ys7.com"

def test_ezviz_api():
    """测试萤石云 API"""
    print("="*60)
    print("萤石云 API 测试")
    print("="*60)
    
    # 萤石云签名算法
    # sign = MD5(appKey + appSecret + timestamp)
    timestamp = str(int(time.time() * 1000))
    sign_str = f"{AK}{SK}{timestamp}"
    sign = hashlib.md5(sign_str.encode()).hexdigest()
    
    print(f"\nAK: {AK[:20]}...")
    print(f"Timestamp: {timestamp}")
    print(f"Sign: {sign}")
    print(f"Sign Upper: {sign.upper()}")
    
    # 测试 Token 获取
    print("\n" + "="*60)
    print("[1] 获取 AccessToken")
    print("="*60)
    
    url = f"{BASE_URL}/api/lapp/token/get"
    data = {
        "appKey": AK,
        "appSecret": SK,
    }
    
    print(f"\nURL: {url}")
    print(f"Data: {data}")
    
    try:
        resp = requests.post(url, data=data, timeout=30, verify=False)
        print(f"\nStatus: {resp.status_code}")
        print(f"Response: {resp.text}")
        
        result = resp.json()
        if result.get("code") == "200" or result.get("code") == 200:
            access_token = result.get("data", {}).get("accessToken")
            print(f"\n✅ Token 获取成功!")
            print(f"Token: {access_token}")
            return access_token
        else:
            print(f"\n⚠️ Token 获取失败: {result.get('msg')}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    # 尝试其他路径
    paths = [
        "/api/v1/token/get",
        "/v1/token/get",
        "/api/token/get",
        "/lapp/token/get",
    ]
    
    print("\n尝试其他路径...")
    for path in paths:
        url = f"{BASE_URL}{path}"
        print(f"\n  {path}: ", end="")
        try:
            resp = requests.post(url, data=data, timeout=10, verify=False)
            print(f"{resp.status_code} - {resp.text[:100]}")
        except Exception as e:
            print(f"Error - {str(e)[:50]}")
    
    return None

def test_device_list(access_token):
    """测试设备列表"""
    print("\n" + "="*60)
    print("[2] 获取设备列表")
    print("="*60)
    
    url = f"{BASE_URL}/api/lapp/device/list"
    data = {
        "accessToken": access_token,
        "pageStart": 0,
        "pageSize": 20,
    }
    
    try:
        resp = requests.post(url, data=data, timeout=30, verify=False)
        print(f"\nStatus: {resp.status_code}")
        print(f"Response: {resp.text[:1000]}")
        
        result = resp.json()
        if result.get("code") == "200" or result.get("code") == 200:
            devices = result.get("data", [])
            print(f"\n✅ 找到 {len(devices)} 个设备")
            return devices
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    return []

def test_capture(access_token, device_serial):
    """测试设备抓拍"""
    print("\n" + "="*60)
    print("[3] 设备抓拍")
    print("="*60)
    
    url = f"{BASE_URL}/api/lapp/device/capture"
    data = {
        "accessToken": access_token,
        "deviceSerial": device_serial,
        "channelNo": 1,
    }
    
    try:
        resp = requests.post(url, data=data, timeout=30, verify=False)
        print(f"\nStatus: {resp.status_code}")
        print(f"Response: {resp.text}")
        
        result = resp.json()
        if result.get("code") == "200" or result.get("code") == 200:
            pic_url = result.get("data", {}).get("picUrl")
            print(f"\n✅ 抓拍成功!")
            print(f"图片URL: {pic_url}")
            return pic_url
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    return None

def main():
    # 获取 Token
    token = test_ezviz_api()
    
    if token:
        # 获取设备列表
        devices = test_device_list(token)
        
        if devices:
            print("\n\n设备列表:")
            for i, dev in enumerate(devices[:5], 1):
                print(f"  [{i}] {dev.get('deviceName')} ({dev.get('deviceSerial')})")
            
            # 测试抓拍
            if devices:
                first_device = devices[0]
                device_serial = first_device.get('deviceSerial')
                test_capture(token, device_serial)
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)

if __name__ == "__main__":
    main()
