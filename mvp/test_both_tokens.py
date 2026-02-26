#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康云 API - 使用 App Token 作为 User Token 测试
"""

import json
import requests

requests.packages.urllib3.disable_warnings()

BASE_URL = "https://open-api.hikiot.com"
APP_TOKEN = "at-GmJzaRSFX8tOWRZzaRHBVTraecreS7IlLlJ6vEfE"

def test_with_both_tokens():
    """同时使用 App-Access-Token 和 User-Access-Token"""
    print("="*60)
    print("使用 App Token 同时作为 User Token")
    print("="*60)
    
    url = f"{BASE_URL}/device/camera/v1/page"
    
    # 尝试使用 App Token 作为 User Token
    headers = {
        "Content-Type": "application/json",
        "App-Access-Token": APP_TOKEN,
        "User-Access-Token": APP_TOKEN,  # 使用同一个 token
    }
    
    params = {"page": 1, "pageSize": 20}
    
    print(f"\nURL: {url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    
    resp = requests.get(url, headers=headers, params=params, timeout=15, verify=False)
    result = resp.json()
    
    print(f"\nStatus: {resp.status_code}")
    print(f"Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    if result.get("code") == 0:
        print("\n✅ 成功!")
        return result.get("data")
    
    return None

def test_capture_with_tokens(device_id):
    """测试抓拍接口"""
    print("\n" + "="*60)
    print(f"设备抓拍: {device_id}")
    print("="*60)
    
    # 可能的抓拍接口
    capture_apis = [
        "/device/camera/v1/capture",
        "/device/camera/v1/snapshot",
        "/camera/v1/capture",
        "/device/capture",
    ]
    
    headers = {
        "Content-Type": "application/json",
        "App-Access-Token": APP_TOKEN,
        "User-Access-Token": APP_TOKEN,
    }
    
    payload = {
        "deviceSerial": device_id,
        "channelNo": 1,
    }
    
    for api_path in capture_apis:
        url = f"{BASE_URL}{api_path}"
        print(f"\n尝试: {api_path}")
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15, verify=False)
            result = resp.json()
            
            print(f"  Status: {resp.status_code}")
            print(f"  Code: {result.get('code')}")
            print(f"  Msg: {result.get('msg', 'N/A')[:80]}")
            
            if result.get("code") == 0:
                print(f"\n  ✅ 抓拍成功!")
                print(f"  Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
                return result.get("data")
                
        except Exception as e:
            print(f"  Error: {str(e)[:50]}")

def main():
    print("="*60)
    print("海康云 API - 双 Token 测试")
    print("="*60)
    
    # 获取设备列表
    devices = test_with_both_tokens()
    
    if devices:
        print("\n\n📋 设备列表:")
        records = devices.get("records", []) if isinstance(devices, dict) else devices
        print(json.dumps(records, indent=2, ensure_ascii=False)[:2000])
        
        # 测试抓拍
        if records and len(records) > 0:
            first = records[0]
            device_id = first.get("deviceSerial") or first.get("deviceId") or first.get("cameraId")
            if device_id:
                test_capture_with_tokens(device_id)
    else:
        print("\n❌ 仍无法获取设备列表")
        print("\n可能原因:")
        print("1. 需要绑定手机号获取 User Token")
        print("2. 账号下没有设备")
        print("3. API 路径不正确")

if __name__ == "__main__":
    main()
