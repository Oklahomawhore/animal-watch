#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试海康云 API 连接
"""

import sys
sys.path.insert(0, '/Users/wangshuzhu/.openclaw/workspace/lin-she-health-monitor/mvp')

from hikcloud_grass_monitor import HikvisionCloudClient
import json

# 用户提供的 AK/SK
AK = "2023987187632369716"
SK = "MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBAJLMIOuommDeg+8yY0sNzL8VeOBfLdZkiHjIUZK64Om+S1pVo6SLFT5hNLsip+5nSuvlXo+tgfyzaqbidsCZZQaCM48RViKfFZr7vhTmVDBBO1exrWpacu/wCmwstu9cf//UTM0KO3M/IhJ0qZ713vyMuc7EXUX0yqj/IpDI5S6nAgMBAAECgYB8gOTq+nT088Syeun8HhgpeOysYA1gaKPWzQ9ig11+4gbG9xtz0wKRhaBTl3EWokTJDiDFe0NkMEekgy5066TiNl483a4sU+t/4A1evajpTHsGN9aLDE7xT7rmCwNGCtZrUjlZAWzAIHzA1P7g/4V8DyfThDCVFlMxeKyzxJtmAQJBANJP8n7wGawsXyYOzh7dJxaouDRTHvyhfSbXJlqRcLqF4+msXdeyj1qSWCwYTI92EiT6yuNknSg2o/7SBoWoJGkCQQCyr/CY+tfci/+Au4O+cITeD/Uton9g8Nn1W7O9Uql0mZ7AKNtmF2ZpN+H+lX6fHxktXZWVMufYoBGfDUb6NxiPAkEAqM5oysB3Kr4WxRpfEWDbLhHQgJczKP2J0bIhY9KXU++B5x5l2GrHK6CJSyNZ2FCh8bKnROuORSfObAsyFvfF+QJAeiquHXmK8h/JXTNW/HIjdUuFvmCWJConaof62FrWvoB1OD322tLu0stBOPTusE3rwcd1CJ/YQZQW2B6Uw2e94wJAZtbsaaCeiCmfVPNFwBiTQKYemg/s8xL3Rqhbx4ofoWLnyj+sY+Dtw5sn6XV2eY4d2+jVufz8eoiJszISw8dH5w=="

print("="*60)
print("海康互联云 API 连接测试")
print("="*60)
print(f"\nAK: {AK[:10]}...")
print(f"SK: {SK[:30]}...")
print()

try:
    # 创建客户端
    print("[1/3] 初始化客户端...")
    client = HikvisionCloudClient(AK, SK)
    print("   ✓ 客户端初始化成功")
    
    # 获取设备列表
    print("\n[2/3] 获取设备列表...")
    devices = client.get_device_list(page=1, page_size=20)
    
    if devices.get('code') == 200:
        total = devices.get('data', {}).get('total', 0)
        device_list = devices.get('data', {}).get('list', [])
        
        print(f"   ✓ API 连接成功!")
        print(f"   ✓ 共有 {total} 个设备")
        
        if device_list:
            print("\n   设备列表:")
            for i, dev in enumerate(device_list[:5], 1):
                print(f"      [{i}] {dev.get('deviceName', 'Unknown')} "
                      f"(ID: {dev.get('deviceId', 'N/A')[:15]}..., "
                      f"状态: {dev.get('status', 'unknown')})")
        else:
            print("\n   ⚠️  暂无绑定的设备")
            print("      请在海康互联 APP 中添加设备")
    else:
        print(f"   ✗ API 错误: {devices.get('message', 'Unknown error')}")
        print(f"   错误码: {devices.get('code')}")

except Exception as e:
    print(f"\n   ✗ 连接失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("测试完成")
print("="*60)
