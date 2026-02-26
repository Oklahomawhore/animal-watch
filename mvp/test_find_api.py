#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康云 API - 查找正确的设备列表接口
"""

import hashlib
import json
import time
import requests

requests.packages.urllib3.disable_warnings()

AK = "2023987187632369716"
SK = "MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBAJLMIOuommDeg+8yY0sNzL8VeOBfLdZkiHjIUZK64Om+S1pVo6SLFT5hNLsip+5nSuvlXo+tgfyzaqbidsCZZQaCM48RViKfFZr7vhTmVDBBO1exrWpacu/wCmwstu9cf//UTM0KO3M/IhJ0qZ713vyMuc7EXUX0yqj/IpDI5S6nAgMBAAECgYB8gOTq+nT088Syeun8HhgpeOysYA1gaKPWzQ9ig11+4gbG9xtz0wKRhaBTl3EWokTJDiDFe0NkMEekgy5066TiNl483a4sU+t/4A1evajpTHsGN9aLDE7xT7rmCwNGCtZrUjlZAWzAIHzA1P7g/4V8DyfThDCVFlMxeKyzxJtmAQJBANJP8n7wGawsXyYOzh7dJxaouDRTHvyhfSbXJlqRcLqF4+msXdeyj1qSWCwYTI92EiT6yuNknSg2o/7SBoWoJGkCQQCyr/CY+tfci/+Au4O+cITeD/Uton9g8Nn1W7O9Uql0mZ7AKNtmF2ZpN+H+lX6fHxktXZWVMufYoBGfDUb6NxiPAkEAqM5oysB3Kr4WxRpfEWDbLhHQgJczKP2J0bIhY9KXU++B5x5l2GrHK6CJSyNZ2FCh8bKnROuORSfObAsyFvfF+QJAeiquHXmK8h/JXTNW/HIjdUuFvmCWJConaof62FrWvoB1OD322tLu0stBOPTusE3rwcd1CJ/YQZQW2B6Uw2e94wJAZtbsaaCeiCmfVPNFwBiTQKYemg/s8xL3Rqhbx4ofoWLnyj+sY+Dtw5sn6XV2eY4d2+jVufz8eoiJszISw8dH5w=="

BASE_URL = "https://open-api.hikiot.com"
TOKEN = "at-GmJzaRSFX8tOWRZzaRHBVTraecreS7IlLlJ6vEfE"

def test_endpoint(method, path, params=None, data=None):
    """测试单个端点"""
    url = f"{BASE_URL}{path}"
    headers = {
        "Content-Type": "application/json",
        "App-Access-Token": TOKEN,
    }
    
    print(f"\n[{method}] {path}")
    
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, params=params, timeout=15, verify=False)
        else:
            resp = requests.post(url, headers=headers, json=data, timeout=15, verify=False)
        
        result = resp.json()
        print(f"  Status: {resp.status_code}")
        print(f"  Code: {result.get('code')}")
        print(f"  Msg: {result.get('msg', 'N/A')[:100]}")
        
        if result.get("code") == 0:
            print(f"  ✅ 成功!")
            return result.get("data")
    except Exception as e:
        print(f"  Error: {e}")
    
    return None

def main():
    print("="*60)
    print("海康云 API - 查找设备接口")
    print("="*60)
    
    # 尝试不同的设备列表接口
    paths = [
        ("GET", "/v1/device/list"),
        ("GET", "/v1/devices"),
        ("GET", "/device/list"),
        ("GET", "/devices"),
        ("POST", "/device/query"),
        ("POST", "/v1/device/query"),
    ]
    
    for method, path in paths:
        data = test_endpoint(method, path, params={"page": 1, "pageSize": 20})
        if data:
            print(f"\n🎉 找到正确接口: {method} {path}")
            print(f"数据: {json.dumps(data, indent=2, ensure_ascii=False)[:1000]}")
            break
    
    # 尝试抓拍接口
    print("\n" + "="*60)
    print("查找抓拍接口")
    print("="*60)
    
    capture_paths = [
        ("POST", "/device/capture"),
        ("POST", "/v1/device/capture"),
        ("POST", "/capture"),
    ]
    
    for method, path in capture_paths:
        data = test_endpoint(method, path, data={
            "deviceSerial": "TEST123",
            "channelNo": 1
        })
        if data:
            print(f"\n🎉 找到正确接口: {method} {path}")
            break

if __name__ == "__main__":
    main()
