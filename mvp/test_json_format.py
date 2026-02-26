#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康云 API - JSON 格式请求
"""

import hashlib
import json
import time
import requests

requests.packages.urllib3.disable_warnings()

AK = "2023987187632369716"
SK = "MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBAJLMIOuommDeg+8yY0sNzL8VeOBfLdZkiHjIUZK64Om+S1pVo6SLFT5hNLsip+5nSuvlXo+tgfyzaqbidsCZZQaCM48RViKfFZr7vhTmVDBBO1exrWpacu/wCmwstu9cf//UTM0KO3M/IhJ0qZ713vyMuc7EXUX0yqj/IpDI5S6nAgMBAAECgYB8gOTq+nT088Syeun8HhgpeOysYA1gaKPWzQ9ig11+4gbG9xtz0wKRhaBTl3EWokTJDiDFe0NkMEekgy5066TiNl483a4sU+t/4A1evajpTHsGN9aLDE7xT7rmCwNGCtZrUjlZAWzAIHzA1P7g/4V8DyfThDCVFlMxeKyzxJtmAQJBANJP8n7wGawsXyYOzh7dJxaouDRTHvyhfSbXJlqRcLqF4+msXdeyj1qSWCwYTI92EiT6yuNknSg2o/7SBoWoJGkCQQCyr/CY+tfci/+Au4O+cITeD/Uton9g8Nn1W7O9Uql0mZ7AKNtmF2ZpN+H+lX6fHxktXZWVMufYoBGfDUb6NxiPAkEAqM5oysB3Kr4WxRpfEWDbLhHQgJczKP2J0bIhY9KXU++B5x5l2GrHK6CJSyNZ2FCh8bKnROuORSfObAsyFvfF+QJAeiquHXmK8h/JXTNW/HIjdUuFvmCWJConaof62FrWvoB1OD322tLu0stBOPTusE3rwcd1CJ/YQZQW2B6Uw2e94wJAZtbsaaCeiCmfVPNFwBiTQKYemg/s8xL3Rqhbx4ofoWLnyj+sY+Dtw5sn6XV2eY4d2+jVufz8eoiJszISw8dH5w=="

BASE_URL = "https://open-api.hikiot.com"

def get_token_json():
    """使用 JSON 格式获取 Token"""
    print("="*60)
    print("获取 AccessToken (JSON格式)")
    print("="*60)
    
    url = f"{BASE_URL}/auth/exchangeAppToken"
    timestamp = str(int(time.time() * 1000))
    
    # MD5 签名
    sign_str = f"{AK}{SK}{timestamp}"
    sign = hashlib.md5(sign_str.encode()).hexdigest()
    
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
    
    print(f"\nURL: {url}")
    print(f"Headers: {headers}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
        print(f"\nStatus: {resp.status_code}")
        print(f"Response: {resp.text}")
        
        result = resp.json()
        if result.get("code") in [200, "200"]:
            token = result.get("data", {}).get("accessToken")
            print(f"\n✅ Token 获取成功!")
            return token
        else:
            print(f"\n⚠️ 失败: {result.get('msg')}")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
    
    return None

def get_devices_json(token):
    """获取设备列表"""
    print("\n" + "="*60)
    print("获取设备列表 (JSON格式)")
    print("="*60)
    
    url = f"{BASE_URL}/device/list"
    
    headers = {
        "Content-Type": "application/json",
        "accessToken": token,
    }
    
    # 有些 API 参数放在 URL，有些放在 body
    # 先尝试 URL 参数
    params = {"page": 1, "pageSize": 20}
    
    print(f"\nURL: {url}")
    print(f"Headers: {headers}")
    print(f"Params: {params}")
    
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

def capture_json(token, device_id):
    """设备抓拍"""
    print("\n" + "="*60)
    print(f"设备抓拍 (JSON格式): {device_id}")
    print("="*60)
    
    url = f"{BASE_URL}/device/capture"
    
    headers = {
        "Content-Type": "application/json",
        "accessToken": token,
    }
    
    payload = {
        "deviceSerial": device_id,
        "channelNo": 1,
    }
    
    print(f"\nURL: {url}")
    print(f"Headers: {headers}")
    print(f"Payload: {json.dumps(payload)}")
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
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
    print("海康云 API - JSON 格式测试")
    print("="*60)
    print(f"\nAK: {AK[:25]}...")
    print(f"Endpoint: {BASE_URL}")
    
    # 获取 Token
    token = get_token_json()
    
    if token:
        print(f"\n\n✅ Token: {token[:40]}...")
        
        # 获取设备
        devices = get_devices_json(token)
        
        if devices:
            print("\n\n📋 设备列表:")
            for i, dev in enumerate(devices[:10], 1):
                print(f"  [{i}] {dev.get('deviceName', 'Unknown')}")
                print(f"      ID: {dev.get('deviceSerial', dev.get('deviceId', 'N/A'))}")
                print(f"      状态: {dev.get('status', 'unknown')}")
            
            # 测试抓拍
            if devices:
                first = devices[0]
                device_id = first.get('deviceSerial') or first.get('deviceId')
                capture_json(token, device_id)
    else:
        print("\n\n❌ 无法获取 Token")
        print("\n错误分析:")
        print("- 你的 AK/SK 需要在海康互联 APP 中开通开放 API 权限")
        print("- 权限: [身份及授权] (identity.auth)")
        print("- 请联系海康客服开通权限，或使用本地 ISAPI 方案")

if __name__ == "__main__":
    main()
