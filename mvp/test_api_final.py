#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康云 API - 获取设备列表和抓拍
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
    print("="*60)
    print("获取 AccessToken")
    print("="*60)
    
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
    
    print(f"\nURL: {url}")
    
    resp = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
    result = resp.json()
    
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    if result.get("code") == 0:
        token = result.get("data", {}).get("appAccessToken")
        print(f"\n✅ Token 获取成功!")
        print(f"Token: {token}")
        return token
    else:
        print(f"\n❌ 失败: {result.get('msg')}")
        return None

def get_devices(token):
    """获取设备列表"""
    print("\n" + "="*60)
    print("获取设备列表")
    print("="*60)
    
    url = f"{BASE_URL}/device/list"
    
    headers = {
        "Content-Type": "application/json",
        "App-Access-Token": token,  # 注意: 请求头名称是 App-Access-Token
    }
    
    params = {"page": 1, "pageSize": 20}
    
    print(f"\nURL: {url}")
    print(f"Headers: {headers}")
    
    resp = requests.get(url, headers=headers, params=params, timeout=30, verify=False)
    result = resp.json()
    
    print(f"\nStatus: {resp.status_code}")
    print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)[:2000]}")
    
    if result.get("code") == 0:
        devices = result.get("data", {}).get("list", [])
        print(f"\n✅ 找到 {len(devices)} 个设备")
        return devices
    else:
        print(f"\n⚠️ 失败: {result.get('msg')}")
        return []

def capture_device(token, device_serial):
    """设备抓拍"""
    print("\n" + "="*60)
    print(f"设备抓拍: {device_serial}")
    print("="*60)
    
    url = f"{BASE_URL}/device/capture"
    
    headers = {
        "Content-Type": "application/json",
        "App-Access-Token": token,
    }
    
    payload = {
        "deviceSerial": device_serial,
        "channelNo": 1,
    }
    
    print(f"\nURL: {url}")
    print(f"Payload: {payload}")
    
    resp = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
    result = resp.json()
    
    print(f"\nStatus: {resp.status_code}")
    print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    if result.get("code") == 0:
        pic_url = result.get("data", {}).get("picUrl")
        print(f"\n✅ 抓拍成功!")
        print(f"图片URL: {pic_url}")
        return pic_url
    else:
        print(f"\n⚠️ 失败: {result.get('msg')}")
        return None

def download_image(url, save_path="capture.jpg"):
    """下载图片"""
    print(f"\n下载图片: {url[:80]}...")
    
    try:
        resp = requests.get(url, timeout=30, verify=False)
        resp.raise_for_status()
        
        with open(save_path, "wb") as f:
            f.write(resp.content)
        
        print(f"✅ 图片已保存: {save_path} ({len(resp.content)} bytes)")
        return True
    except Exception as e:
        print(f"❌ 下载失败: {e}")
        return False

def main():
    print("="*60)
    print("海康云 API - 完整测试")
    print("="*60)
    
    # 获取 Token
    token = get_token()
    
    if not token:
        return
    
    # 获取设备列表
    devices = get_devices(token)
    
    if devices:
        print("\n\n📋 设备列表:")
        for i, dev in enumerate(devices[:10], 1):
            name = dev.get('deviceName', 'Unknown')
            serial = dev.get('deviceSerial', dev.get('deviceId', 'N/A'))
            status = dev.get('status', 'unknown')
            print(f"  [{i}] {name}")
            print(f"      Serial: {serial}")
            print(f"      状态: {status}")
        
        # 测试抓拍第一个设备
        first = devices[0]
        device_serial = first.get('deviceSerial')
        
        if device_serial:
            pic_url = capture_device(token, device_serial)
            
            if pic_url:
                download_image(pic_url)
    else:
        print("\n⚠️ 暂无设备")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)

if __name__ == "__main__":
    main()
