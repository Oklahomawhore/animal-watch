#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试不同的 RSA 填充模式
"""

import sys
import base64
import urllib.parse
sys.path.insert(0, '/Users/wangshuzhu/.openclaw/workspace/lin-she-health-monitor/hikvision-backend')

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5, PKCS1_OAEP
from Crypto.Hash import SHA1

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

PARAM_STRING = 'departNos=BM0001&containsDeletedPerson=true&beginDate=2024-08-01&endDate=2024-08-15'
EXPECTED = 'pmttDL8cTHDp8SRRFnBL69EdlyDVkASZ1MheaGGv38jduOw7ye5MdT1Vtd+fThQkrSHUuihMphZXbiGGHGov2N0YWmcmi9QX+kFUlNmzafU7MTaUijaPEgku8xHTWXAcP02arqs3RYNNJpfaI86Ruaq/bNwT8j/nb1CTuiYbzvw='

def test_pkcs1_v1_5():
    """测试 PKCS1_v1_5 填充"""
    print("=" * 60)
    print("测试 PKCS1_v1_5 填充")
    print("=" * 60)
    
    private_key = RSA.import_key(TEST_PRIVATE_KEY)
    cipher = PKCS1_v1_5.new(private_key)
    
    # 方式1: 直接加密原始字符串
    data = PARAM_STRING.encode('utf-8')
    encrypted = cipher.encrypt(data)
    result = base64.b64encode(encrypted).decode('utf-8')
    print(f"直接加密: {result}")
    print(f"匹配: {result == EXPECTED}")
    
    # 方式2: 先URL encode
    url_encoded = urllib.parse.quote(PARAM_STRING, safe='')
    data = url_encoded.encode('utf-8')
    encrypted = cipher.encrypt(data)
    result = base64.b64encode(encrypted).decode('utf-8')
    print(f"URL编码后加密: {result}")
    print(f"匹配: {result == EXPECTED}")

def test_pkcs1_oaep():
    """测试 PKCS1_OAEP 填充"""
    print("\n" + "=" * 60)
    print("测试 PKCS1_OAEP 填充 (SHA1)")
    print("=" * 60)
    
    private_key = RSA.import_key(TEST_PRIVATE_KEY)
    cipher = PKCS1_OAEP.new(private_key, hashAlgo=SHA1)
    
    # 方式1: 直接加密原始字符串
    try:
        data = PARAM_STRING.encode('utf-8')
        encrypted = cipher.encrypt(data)
        result = base64.b64encode(encrypted).decode('utf-8')
        print(f"直接加密: {result}")
        print(f"匹配: {result == EXPECTED}")
    except Exception as e:
        print(f"直接加密失败: {e}")
    
    # 方式2: 先URL encode
    try:
        url_encoded = urllib.parse.quote(PARAM_STRING, safe='')
        data = url_encoded.encode('utf-8')
        encrypted = cipher.encrypt(data)
        result = base64.b64encode(encrypted).decode('utf-8')
        print(f"URL编码后加密: {result}")
        print(f"匹配: {result == EXPECTED}")
    except Exception as e:
        print(f"URL编码后加密失败: {e}")

def test_java_style():
    """测试 Java 风格 - 可能需要特定的编码"""
    print("\n" + "=" * 60)
    print("测试 Java 风格 (UTF-16BE)")
    print("=" * 60)
    
    private_key = RSA.import_key(TEST_PRIVATE_KEY)
    cipher = PKCS1_v1_5.new(private_key)
    
    # Java 默认可能是 UTF-16BE
    data = PARAM_STRING.encode('utf-16be')
    encrypted = cipher.encrypt(data)
    result = base64.b64encode(encrypted).decode('utf-8')
    print(f"UTF-16BE 编码后加密: {result}")
    print(f"匹配: {result == EXPECTED}")

if __name__ == "__main__":
    test_pkcs1_v1_5()
    test_pkcs1_oaep()
    test_java_style()
