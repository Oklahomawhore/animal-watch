#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康云 API - 使用设备序列号 GF5155888 测试
"""

import json
import requests

requests.packages.urllib3.disable_warnings()

BASE_URL = "https://open-api.hikiot.com"
APP_TOKEN = "at-GmJzaRSFX8tOWRZzaRHBVTraecreS7IlLlJ6vEfE"
DEVICE_SERIAL = "GF5155888"

def test_capture_apis():
    """测试所有可能的抓拍接口"""
    print("="*60)
    print(f"设备抓拍测试: {DEVICE_SERIAL}")
    print("="*60)
    
    # 可能的抓拍接口
    capture_apis = [
        "/device/camera/v1/capture",
        "/device/camera/v1/snapshot", 
        "/camera/v1/capture",
        "/camera/v1/snapshot",
        "/device/capture",
        "/device/snapshot",
        "/v1/device/capture",
        "/v1/camera/capture",
        "/capture",
        "/snapshot",
    ]
    
    # 可能的参数格式
    payload_options = [
        {"deviceSerial": DEVICE_SERIAL, "channelNo": 1},
        {"deviceId": DEVICE_SERIAL, "channelNo": 1},
        {"cameraId": DEVICE_SERIAL, "channelNo": 1},
        {"deviceSerial": DEVICE_SERIAL},
        {"deviceId": DEVICE_SERIAL},
        {"serial": DEVICE_SERIAL},
    ]
    
    headers_options = [
        {"Content-Type": "application/json", "App-Access-Token": APP_TOKEN},
        {"Content-Type": "application/json", "App-Access-Token": APP_TOKEN, "User-Access-Token": APP_TOKEN},
    ]
    
    for api_path in capture_apis:
        url = f"{BASE_URL}{api_path}"
        print(f"\n{'='*60}")
        print(f"API: {api_path}")
        print('='*60)
        
        for i, payload in enumerate(payload_options[:3], 1):
            for j, headers in enumerate(headers_options, 1):
                print(f"\n  参数{i}-头{j}: {payload} | UserToken={j==2}")
                
                try:
                    resp = requests.post(url, headers=headers, json=payload, timeout=15, verify=False)
                    result = resp.json()
                    
                    print(f"    Status: {resp.status_code}")
                    print(f"    Code: {result.get('code')}")
                    print(f"    Msg: {result.get('msg', 'N/A')[:100]}")
                    
                    if result.get("code") == 0:
                        print(f"\n    ✅ 抓拍成功!")
                        print(f"    Response: {json.dumps(result, indent=2, ensure_ascii=False)}")
                        return result.get("data")
                        
                except Exception as e:
                    print(f"    Error: {str(e)[:50]}")

def test_device_info():
    """获取设备信息"""
    print("\n" + "="*60)
    print(f"设备信息查询: {DEVICE_SERIAL}")
    print("="*60)
    
    # 可能的设备信息接口
    info_apis = [
        ("GET", f"/device/camera/v1/info/{DEVICE_SERIAL}"),
        ("GET", f"/device/camera/v1/detail/{DEVICE_SERIAL}"),
        ("GET", f"/camera/v1/info/{DEVICE_SERIAL}"),
        ("POST", "/device/camera/v1/info"),
        ("POST", "/camera/v1/detail"),
    ]
    
    headers = {
        "Content-Type": "application/json",
        "App-Access-Token": APP_TOKEN,
        "User-Access-Token": APP_TOKEN,
    }
    
    for method, api_path in info_apis:
        url = f"{BASE_URL}{api_path}"
        print(f"\n[{method}] {api_path}")
        
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=15, verify=False)
            else:
                payload = {"deviceSerial": DEVICE_SERIAL}
                resp = requests.post(url, headers=headers, json=payload, timeout=15, verify=False)
            
            result = resp.json()
            
            print(f"  Status: {resp.status_code}")
            print(f"  Code: {result.get('code')}")
            print(f"  Msg: {result.get('msg', 'N/A')[:100]}")
            
            if result.get("code") == 0:
                print(f"\n  ✅ 成功!")
                print(f"  Data: {json.dumps(result.get('data'), indent=2, ensure_ascii=False)[:500]}")
                
        except Exception as e:
            print(f"  Error: {str(e)[:50]}")

def test_preview_url():
    """获取预览地址"""
    print("\n" + "="*60)
    print(f"获取预览地址: {DEVICE_SERIAL}")
    print("="*60)
    
    preview_apis = [
        "/device/camera/v1/preview",
        "/camera/v1/preview",
        "/device/preview",
    ]
    
    headers = {
        "Content-Type": "application/json",
        "App-Access-Token": APP_TOKEN,
        "User-Access-Token": APP_TOKEN,
    }
    
    payload = {
        "deviceSerial": DEVICE_SERIAL,
        "channelNo": 1,
        "protocol": "hls",  # hls, webrtc, flv
    }
    
    for api_path in preview_apis:
        url = f"{BASE_URL}{api_path}"
        print(f"\n尝试: {api_path}")
        
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=15, verify=False)
            result = resp.json()
            
            print(f"  Status: {resp.status_code}")
            print(f"  Code: {result.get('code')}")
            print(f"  Msg: {result.get('msg', 'N/A')[:100]}")
            
            if result.get("code") == 0:
                print(f"\n  ✅ 成功!")
                print(f"  URL: {result.get('data', {}).get('url', 'N/A')}")
                return result.get("data")
                
        except Exception as e:
            print(f"  Error: {str(e)[:50]}")

def main():
    print("="*60)
    print("海康云 API - 设备 GF5155888 测试")
    print("="*60)
    print(f"\n设备序列号: {DEVICE_SERIAL}")
    print(f"App Token: {APP_TOKEN[:40]}...")
    
    # 1. 获取设备信息
    test_device_info()
    
    # 2. 获取预览地址
    test_preview_url()
    
    # 3. 测试抓拍
    capture_data = test_capture_apis()
    
    if capture_data:
        print("\n\n" + "="*60)
        print("✅ 抓拍成功!")
        print("="*60)
        print(f"图片 URL: {capture_data.get('picUrl', 'N/A')}")
        
        # 下载图片
        pic_url = capture_data.get('picUrl')
        if pic_url:
            print(f"\n下载图片...")
            try:
                resp = requests.get(pic_url, timeout=30, verify=False)
                with open("capture.jpg", "wb") as f:
                    f.write(resp.content)
                print(f"✅ 图片已保存: capture.jpg ({len(resp.content)} bytes)")
            except Exception as e:
                print(f"❌ 下载失败: {e}")
    else:
        print("\n\n" + "="*60)
        print("⚠️ 未能成功抓拍")
        print("="*60)
        print("\n可能原因:")
        print("1. 设备不在线")
        print("2. 需要 User-Access-Token")
        print("3. API 路径不正确")
        print("4. 设备序列号错误")

if __name__ == "__main__":
    main()
