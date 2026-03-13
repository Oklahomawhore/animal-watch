#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
详细调试 RSA 加密过程
"""

import sys
import base64
import urllib.parse
sys.path.insert(0, '/Users/wangshuzhu/.openclaw/workspace/lin-she-health-monitor/hikvision-backend')

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

# 海康官方示例私钥
TEST_PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBAK2sNFBlj1H9aDvl
Sz24TlN80qpVYSrO1PXt66hlNMRt/+sRAslj4Y69CjIlsePmByrCGdN4g6AipT/W
yUydqpZWDcWbjyK4SEyU+dII9MXuP1cpCjCKAOsk6VdCeEVntByqQRKjqGNIq1s5
XU3tZAOXNUL21Dy6MIaGesE69NNpAgMBAAECgYBkoi8iEudMNBEs+71wgxZnzCFp
79VA7954rqdpyVMdKzwqoo3B0m2Fv0ZkLnF4w/aNMTGz1tY2eTzV1AiKq6WHRmfa
tWM0Azo7hCg3QB827ffH4a88XJyI3S9mhxpwyCErvldzIXAYjLDwCj/dhBVaFWUa
fB3BNqwvr7VCF5143QJBAPOPZorxikQiqRnTYTLZvmVw7J29/62rfM0gxnnvZQlr
5r+AQk9FJRzMG0+6RfCqKIkd3s5qyYsSyhA5dlltudsCQQC2iwKuSbYLhVACCAxg
JMG6LLUbM+94qGtwdiRThstOAJCvUh5r3bK/7W2qGB2DMDs8C58tH1j8DFyKf93L
YrULAkEA5sxRuIKQqmZJ5d4nsj8iLBBpOEVufo0Nk3hme++9x8LHA1sv+twkAfjs
PI3gbuFfzidPFj2dRLuGXP+GxdGzlwJAUswOtTsd5W/ccG9yHZHOhUGOC/6smg/a
W7Jam8BCKuk6tysKPWbbkw6AdWxmxoBz/bJPysmzNO/ucau50Gy/LQJBAL5a8dnF
POminqd4cTHLgrZ14sdurtqL7gONnBdvSe02US775Vuf06WvSZPH+jPy9wOPcl9R
B3HPV4pCcnrX/es=
-----END RSA PRIVATE KEY-----"""

# 海康官方示例参数
PARAM_STRING = "beginDate=2024-08-01&containsDeletedPerson=true&departNos=BM0001&endDate=2024-08-15"

# 海康官方示例期望结果
EXPECTED_ENCRYPTED = "pmttDL8cTHDp8SRRFnBL69EdlyDVkASZ1MheaGGv38jduOw7ye5MdT1Vtd+fThQkrSHUuihMphZXbiGGHGov2N0YWmcmi9QX+kFUlNmzafU7MTaUijaPEgku8xHTWXAcP02arqs3RYNNJpfaI86Ruaq/bNwT8j/nb1CTuiYbzvw="

def test_step_by_step():
    print("=" * 60)
    print("RSA 加密详细调试")
    print("=" * 60)
    
    # 1. 加载私钥
    private_key = RSA.import_key(TEST_PRIVATE_KEY)
    print(f"\n1. 私钥信息:")
    print(f"   密钥大小: {private_key.size_in_bits()} bits")
    print(f"   n (模数): {hex(private_key.n)[:50]}...")
    print(f"   e (公钥指数): {private_key.e}")
    print(f"   d (私钥指数): {hex(private_key.d)[:50]}...")
    
    # 2. 准备数据
    print(f"\n2. 待加密数据:")
    print(f"   原始字符串: {PARAM_STRING}")
    print(f"   字符串长度: {len(PARAM_STRING)} 字符")
    
    # 3. 检查是否需要 URL encode
    # 海康官方代码: data_bytes = urllib.parse.quote(data).encode("UTF-8")
    url_encoded = urllib.parse.quote(PARAM_STRING, safe='')
    print(f"\n3. URL encode 后:")
    print(f"   结果: {url_encoded}")
    print(f"   长度: {len(url_encoded)} 字符")
    
    # 4. 加密 - 方式1: 直接加密原始字符串
    print(f"\n4. 加密方式1 - 直接加密原始字符串:")
    data_bytes = PARAM_STRING.encode('utf-8')
    print(f"   数据长度: {len(data_bytes)} 字节")
    
    cipher = PKCS1_v1_5.new(private_key)
    encrypted = cipher.encrypt(data_bytes)
    encrypted_b64 = base64.b64encode(encrypted).decode('utf-8')
    print(f"   加密结果: {encrypted_b64}")
    print(f"   期望结果: {EXPECTED_ENCRYPTED}")
    print(f"   匹配: {'✅' if encrypted_b64 == EXPECTED_ENCRYPTED else '❌'}")
    
    # 5. 加密 - 方式2: 先URL encode再加密
    print(f"\n5. 加密方式2 - 先URL encode再加密:")
    data_bytes = url_encoded.encode('utf-8')
    print(f"   数据长度: {len(data_bytes)} 字节")
    
    cipher = PKCS1_v1_5.new(private_key)
    encrypted = cipher.encrypt(data_bytes)
    encrypted_b64 = base64.b64encode(encrypted).decode('utf-8')
    print(f"   加密结果: {encrypted_b64}")
    print(f"   期望结果: {EXPECTED_ENCRYPTED}")
    print(f"   匹配: {'✅' if encrypted_b64 == EXPECTED_ENCRYPTED else '❌'}")
    
    # 6. 检查分段加密
    print(f"\n6. 分段加密测试:")
    MAX_BLOCK = 117
    data_bytes = PARAM_STRING.encode('utf-8')
    blocks = []
    for i in range(0, len(data_bytes), MAX_BLOCK):
        block = data_bytes[i:i+MAX_BLOCK]
        print(f"   块 {len(blocks)+1}: {len(block)} 字节 - {block}")
        encrypted_block = cipher.encrypt(block)
        blocks.append(encrypted_block)
    full_encrypted = b''.join(blocks)
    full_b64 = base64.b64encode(full_encrypted).decode('utf-8')
    print(f"   完整加密结果: {full_b64}")
    print(f"   期望结果:     {EXPECTED_ENCRYPTED}")
    print(f"   匹配: {'✅' if full_b64 == EXPECTED_ENCRYPTED else '❌'}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_step_by_step()
