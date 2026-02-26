#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 requests 测试海康云 API
"""

import hashlib
import hmac
import base64
import json
import logging
from datetime import datetime, timezone

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
except ImportError:
    print("正在安装 requests...")
    import subprocess
    subprocess.check_call(['pip3', 'install', '-q', 'requests'])
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(message)s')

# 用户提供的 AK/SK
AK = "2023987187632369716"
SK = "MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBAJLMIOuommDeg+8yY0sNzL8VeOBfLdZkiHjIUZK64Om+S1pVo6SLFT5hNLsip+5nSuvlXo+tgfyzaqbidsCZZQaCM48RViKfFZr7vhTmVDBBO1exrWpacu/wCmwstu9cf//UTM0KO3M/IhJ0qZ713vyMuc7EXUX0yqj/IpDI5S6nAgMBAAECgYB8gOTq+nT088Syeun8HhgpeOysYA1gaKPWzQ9ig11+4gbG9xtz0wKRhaBTl3EWokTJDiDFe0NkMEekgy5066TiNl483a4sU+t/4A1evajpTHsGN9aLDE7xT7rmCwNGCtZrUjlZAWzAIHzA1P7g/4V8DyfThDCVFlMxeKyzxJtmAQJBANJP8n7wGawsXyYOzh7dJxaouDRTHvyhfSbXJlqRcLqF4+msXdeyj1qSWCwYTI92EiT6yuNknSg2o/7SBoWoJGkCQQCyr/CY+tfci/+Au4O+cITeD/Uton9g8Nn1W7O9Uql0mZ7AKNtmF2ZpN+H+lX6fHxktXZWVMufYoBGfDUb6NxiPAkEAqM5oysB3Kr4WxRpfEWDbLhHQgJczKP2J0bIhY9KXU++B5x5l2GrHK6CJSyNZ2FCh8bKnROuORSfObAsyFvfF+QJAeiquHXmK8h/JXTNW/HIjdUuFvmCWJConaof62FrWvoB1OD322tLu0stBOPTusE3rwcd1CJ/YQZQW2B6Uw2e94wJAZtbsaaCeiCmfVPNFwBiTQKYemg/s8xL3Rqhbx4ofoWLnyj+sY+Dtw5sn6XV2eY4d2+jVufz8eoiJszISw8dH5w=="

BASE_URL = "https://openapi.hikiot.com"

def sign_request(ak, sk, method, uri, params=None, body=None):
    """生成 API 签名"""
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # 构建签名字符串 - 按照海康规范
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

print("="*60)
print("海康互联云 API 连接测试 (Requests 版)")
print("="*60)
print(f"\nAK: {AK[:20]}...")
print(f"SK 长度: {len(SK)} 字符\n")

# 测试1: 签名生成
print("[1/4] 测试签名生成...")
try:
    test_headers = sign_request(AK, SK, "GET", "/v1/devices")
    print(f"   ✓ 签名生成成功")
    print(f"     Timestamp: {test_headers['X-Ca-Timestamp']}")
except Exception as e:
    print(f"   ✗ 签名失败: {e}")
    exit(1)

# 测试2: API 连接
print("\n[2/4] 测试 API 连接...")
uri = "/v1/devices"
params = {"page": 1, "pageSize": 10}
headers = sign_request(AK, SK, "GET", uri, params)
url = f"{BASE_URL}{uri}"

try:
    resp = requests.get(url, headers=headers, params=params, 
                       timeout=30, verify=False)
    
    print(f"   ✓ 收到响应")
    print(f"     状态码: {resp.status_code}")
    print(f"     内容长度: {len(resp.text)} 字节")
    
    try:
        result = resp.json()
        code = result.get('code', 'N/A')
        message = result.get('message', 'N/A')
        
        print(f"\n   API 响应:")
        print(f"     Code: {code}")
        print(f"     Message: {message}")
        
        if code == 200:
            data = result.get('data', {})
            total = data.get('total', 0)
            devices = data.get('list', [])
            
            print(f"\n   ✅ 连接成功!")
            print(f"   ✅ 共有 {total} 个设备")
            
            if devices:
                print("\n   设备列表:")
                for i, dev in enumerate(devices[:5], 1):
                    dev_id = dev.get('deviceId', 'N/A')
                    dev_name = dev.get('deviceName', 'Unknown')
                    status = dev.get('status', 'unknown')
                    print(f"      [{i}] {dev_name}")
                    print(f"          ID: {dev_id[:20]}...")
                    print(f"          状态: {status}")
        else:
            print(f"\n   ⚠️ API 返回错误码: {code}")
            print(f"   完整响应:")
            print(json.dumps(result, indent=2, ensure_ascii=False)[:1000])
            
    except json.JSONDecodeError:
        print(f"\n   ⚠️ 响应不是 JSON 格式")
        print(f"   原始响应: {resp.text[:500]}")
        
except requests.exceptions.Timeout:
    print(f"   ✗ 请求超时")
except requests.exceptions.ConnectionError as e:
    print(f"   ✗ 连接错误: {e}")
except Exception as e:
    print(f"   ✗ 请求失败: {e}")

# 测试3: 检查可能的错误
print("\n[3/4] 诊断信息...")
print(f"   请求 URL: {url}")
print(f"   请求头:")
for k, v in headers.items():
    print(f"      {k}: {v[:50]}...")

# 测试4: 总结
print("\n[4/4] 总结...")
print("   如果连接失败，可能原因:")
print("   1. AK/SK 不正确或不匹配")
print("   2. 签名算法与预期不符")
print("   3. 账号未激活或权限不足")
print("   4. 网络连接问题")
print("   5. API 端点地址已变更")

print("\n" + "="*60)
print("测试完成")
print("="*60)
