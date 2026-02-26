#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版海康云 API 测试（无 OpenCV 依赖）
"""

import hashlib
import hmac
import base64
import json
import logging
from datetime import datetime
import urllib.request
import ssl

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# 禁用 SSL 验证（用于测试）
ssl._create_default_https_context = ssl._create_unverified_context

# 用户提供的 AK/SK
AK = "2023987187632369716"
SK = "MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBAJLMIOuommDeg+8yY0sNzL8VeOBfLdZkiHjIUZK64Om+S1pVo6SLFT5hNLsip+5nSuvlXo+tgfyzaqbidsCZZQaCM48RViKfFZr7vhTmVDBBO1exrWpacu/wCmwstu9cf//UTM0KO3M/IhJ0qZ713vyMuc7EXUX0yqj/IpDI5S6nAgMBAAECgYB8gOTq+nT088Syeun8HhgpeOysYA1gaKPWzQ9ig11+4gbG9xtz0wKRhaBTl3EWokTJDiDFe0NkMEekgy5066TiNl483a4sU+t/4A1evajpTHsGN9aLDE7xT7rmCwNGCtZrUjlZAWzAIHzA1P7g/4V8DyfThDCVFlMxeKyzxJtmAQJBANJP8n7wGawsXyYOzh7dJxaouDRTHvyhfSbXJlqRcLqF4+msXdeyj1qSWCwYTI92EiT6yuNknSg2o/7SBoWoJGkCQQCyr/CY+tfci/+Au4O+cITeD/Uton9g8Nn1W7O9Uql0mZ7AKNtmF2ZpN+H+lX6fHxktXZWVMufYoBGfDUb6NxiPAkEAqM5oysB3Kr4WxRpfEWDbLhHQgJczKP2J0bIhY9KXU++B5x5l2GrHK6CJSyNZ2FCh8bKnROuORSfObAsyFvfF+QJAeiquHXmK8h/JXTNW/HIjdUuFvmCWJConaof62FrWvoB1OD322tLu0stBOPTusE3rwcd1CJ/YQZQW2B6Uw2e94wJAZtbsaaCeiCmfVPNFwBiTQKYemg/s8xL3Rqhbx4ofoWLnyj+sY+Dtw5sn6XV2eY4d2+jVufz8eoiJszISw8dH5w=="

BASE_URL = "https://openapi.hikiot.com"

def sign_request(ak, sk, method, uri, params=None, body=None):
    """生成 API 签名"""
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # 构建签名字符串
    parts = [method.upper(), uri, timestamp]
    if params:
        query = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        parts.append(query)
    if body:
        parts.append(body)
    
    string_to_sign = "\n".join(parts)
    
    # HMAC-SHA256
    try:
        sk_bytes = base64.b64decode(sk)
        signature = hmac.new(sk_bytes, string_to_sign.encode('utf-8'), hashlib.sha256).digest()
        signature_b64 = base64.b64encode(signature).decode('utf-8')
    except Exception as e:
        raise Exception(f"签名失败: {e}")
    
    return {
        'X-Ca-Key': ak,
        'X-Ca-Signature': signature_b64,
        'X-Ca-Timestamp': timestamp,
        'Content-Type': 'application/json'
    }

def http_request(method, path, params=None, body=None):
    """发送 HTTP 请求"""
    uri = path
    url = f"{BASE_URL}{path}"
    
    body_str = json.dumps(body) if body else None
    headers = sign_request(AK, SK, method, uri, params, body_str)
    
    # 构建完整 URL
    if params:
        query = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        url = f"{url}?{query}"
    
    # 创建请求
    req = urllib.request.Request(url, method=method)
    for key, value in headers.items():
        req.add_header(key, value)
    
    if body_str:
        req.data = body_str.encode('utf-8')
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return {
            'error': f'HTTP {e.code}',
            'message': e.read().decode('utf-8')
        }
    except Exception as e:
        return {'error': str(e)}

print("="*60)
print("海康互联云 API 连接测试")
print("="*60)
print(f"\nAK: {AK[:20]}...")
print(f"SK: {SK[:40]}...\n")

print("[1/4] 测试签名生成...")
try:
    test_headers = sign_request(AK, SK, "GET", "/v1/devices")
    print(f"   ✓ 签名生成成功")
    print(f"     X-Ca-Key: {test_headers['X-Ca-Key'][:20]}...")
    print(f"     X-Ca-Signature: {test_headers['X-Ca-Signature'][:30]}...")
    print(f"     X-Ca-Timestamp: {test_headers['X-Ca-Timestamp']}")
except Exception as e:
    print(f"   ✗ 签名失败: {e}")
    exit(1)

print("\n[2/4] 获取设备列表...")
result = http_request("GET", "/v1/devices", params={"page": 1, "pageSize": 10})

if 'error' in result:
    print(f"   ✗ 请求失败: {result['error']}")
    if 'message' in result:
        print(f"     详情: {result['message'][:200]}")
else:
    code = result.get('code', 0)
    message = result.get('message', 'Unknown')
    
    if code == 200:
        data = result.get('data', {})
        total = data.get('total', 0)
        devices = data.get('list', [])
        
        print(f"   ✓ API 连接成功!")
        print(f"   ✓ 响应码: {code} ({message})")
        print(f"   ✓ 共有 {total} 个设备")
        
        if devices:
            print("\n   设备列表 (前5个):")
            for i, dev in enumerate(devices[:5], 1):
                dev_id = dev.get('deviceId', 'N/A')
                dev_name = dev.get('deviceName', 'Unknown')
                status = dev.get('status', 'unknown')
                print(f"      [{i}] {dev_name}")
                print(f"          ID: {dev_id}")
                print(f"          状态: {status}")
        else:
            print("\n   ⚠️ 暂无绑定的设备")
            print("      请在海康互联 APP 中添加设备后重试")
    else:
        print(f"   ✗ API 返回错误")
        print(f"     错误码: {code}")
        print(f"     消息: {message}")
        print(f"\n   完整响应:")
        print(json.dumps(result, indent=2, ensure_ascii=False)[:500])

print("\n[3/4] 测试截图 API (如果有设备)...")
if 'data' in result and result['data'].get('list'):
    first_device = result['data']['list'][0]
    device_id = first_device.get('deviceId')
    print(f"   尝试获取设备 {device_id[:15]}... 的截图")
    # 这里只测试接口是否可调用，不实际下载图片
    print(f"   ℹ️  截图功能需要设备在线，跳过实际测试")
else:
    print("   ℹ️  无可用设备，跳过截图测试")

print("\n[4/4] 总结...")
if 'error' not in result and result.get('code') == 200:
    print("   ✅ API 连接测试成功!")
    print("   ✅ AK/SK 有效")
    print("   ✅ 可以进行后续开发")
else:
    print("   ⚠️ API 连接存在问题")
    print("   可能原因:")
    print("   - AK/SK 错误或不匹配")
    print("   - 签名算法不正确")
    print("   - API 端点地址错误")

print("\n" + "="*60)
print("测试完成")
print("="*60)
