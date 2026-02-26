#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 open.hikiot.com 端点测试海康云 API
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
    import subprocess
    subprocess.check_call(['pip3', 'install', '-q', 'requests'])
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(message)s')

AK = "2023987187632369716"
SK = "MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBAJLMIOuommDeg+8yY0sNzL8VeOBfLdZkiHjIUZK64Om+S1pVo6SLFT5hNLsip+5nSuvlXo+tgfyzaqbidsCZZQaCM48RViKfFZr7vhTmVDBBO1exrWpacu/wCmwstu9cf//UTM0KO3M/IhJ0qZ713vyMuc7EXUX0yqj/IpDI5S6nAgMBAAECgYB8gOTq+nT088Syeun8HhgpeOysYA1gaKPWzQ9ig11+4gbG9xtz0wKRhaBTl3EWokTJDiDFe0NkMEekgy5066TiNl483a4sU+t/4A1evajpTHsGN9aLDE7xT7rmCwNGCtZrUjlZAWzAIHzA1P7g/4V8DyfThDCVFlMxeKyzxJtmAQJBANJP8n7wGawsXyYOzh7dJxaouDRTHvyhfSbXJlqRcLqF4+msXdeyj1qSWCwYTI92EiT6yuNknSg2o/7SBoWoJGkCQQCyr/CY+tfci/+Au4O+cITeD/Uton9g8Nn1W7O9Uql0mZ7AKNtmF2ZpN+H+lX6fHxktXZWVMufYoBGfDUb6NxiPAkEAqM5oysB3Kr4WxRpfEWDbLhHQgJczKP2J0bIhY9KXU++B5x5l2GrHK6CJSyNZ2FCh8bKnROuORSfObAsyFvfF+QJAeiquHXmK8h/JXTNW/HIjdUuFvmCWJConaof62FrWvoB1OD322tLu0stBOPTusE3rwcd1CJ/YQZQW2B6Uw2e94wJAZtbsaaCeiCmfVPNFwBiTQKYemg/s8xL3Rqhbx4ofoWLnyj+sY+Dtw5sn6XV2eY4d2+jVufz8eoiJszISw8dH5w=="

# 使用可以 TLS 握手的端点
BASE_URL = "https://open.hikiot.com"

def sign_request(ak, sk, method, uri, params=None, body=None):
    """生成 API 签名"""
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    parts = [method.upper(), uri, timestamp]
    if params:
        query = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        parts.append(query)
    if body:
        parts.append(body)
    
    string_to_sign = "\n".join(parts)
    
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
print("海康互联云 API 连接测试")
print(f"端点: {BASE_URL}")
print("="*60)

# 测试 API
uri = "/v1/devices"
params = {"page": 1, "pageSize": 10}
headers = sign_request(AK, SK, "GET", uri, params)
url = f"{BASE_URL}{uri}"

print(f"\n请求: GET {url}")
print(f"Headers:")
for k, v in headers.items():
    print(f"  {k}: {v[:50]}...")

try:
    resp = requests.get(url, headers=headers, params=params, 
                       timeout=30, verify=False)
    
    print(f"\n✓ 收到响应 (状态码: {resp.status_code})")
    
    if resp.status_code == 200:
        try:
            result = resp.json()
            print(f"\n响应内容:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except:
            print(f"\n响应内容 (非 JSON):")
            print(resp.text[:1000])
    else:
        print(f"\n错误响应:")
        print(resp.text[:1000])
        
except Exception as e:
    print(f"\n✗ 请求失败: {e}")

print("\n" + "="*60)
