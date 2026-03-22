#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用海康官方示例验证 RSA 加密算法
"""

import sys
sys.path.insert(0, '/Users/wangshuzhu/.openclaw/workspace/lin-she-health-monitor/hikvision-backend')

from services.rsa_encryptor import HikvisionRSAEncryptor

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
TEST_PARAMS = {
    "departNos": "BM0001",
    "containsDeletedPerson": "true",
    "beginDate": "2024-08-01",
    "endDate": "2024-08-15"
}

# 海康官方示例期望结果
EXPECTED_ENCRYPTED = "pmttDL8cTHDp8SRRFnBL69EdlyDVkASZ1MheaGGv38jduOw7ye5MdT1Vtd+fThQkrSHUuihMphZXbiGGHGov2N0YWmcmi9QX+kFUlNmzafU7MTaUijaPEgku8xHTWXAcP02arqs3RYNNJpfaI86Ruaq/bNwT8j/nb1CTuiYbzvw="
EXPECTED_URL_ENCODED = "pmttDL8cTHDp8SRRFnBL69EdlyDVkASZ1MheaGGv38jduOw7ye5MdT1Vtd%2BfThQkrSHUuihMphZXbiGGHGov2N0YWmcmi9QX%2BkFUlNmzafU7MTaUijaPEgku8xHTWXAcP02arqs3RYNNJpfaI86Ruaq%2FbNwT8j%2Fnb1CTuiYbzvw%3D"

def test_encrypt():
    """测试加密算法"""
    print("=" * 60)
    print("海康 RSA 加密算法验证")
    print("=" * 60)
    
    # 创建加密器
    encryptor = HikvisionRSAEncryptor(TEST_PRIVATE_KEY)
    
    # 1. 构建参数字符串
    param_pairs = []
    for key, value in sorted(TEST_PARAMS.items()):
        param_pairs.append(f"{key}={value}")
    param_string = "&".join(param_pairs)
    
    print(f"\n1. 原始参数字符串:")
    print(f"   {param_string}")
    
    # 2. RSA 加密（不做 URL encode）
    encrypted = encryptor.encrypt(param_string, url_encode_input=False)
    
    print(f"\n2. RSA 加密结果:")
    print(f"   我的:  {encrypted}")
    print(f"   期望:  {EXPECTED_ENCRYPTED}")
    print(f"   匹配:  {'✅ 正确!' if encrypted == EXPECTED_ENCRYPTED else '❌ 不匹配!'}")
    
    # 3. URL encode
    import urllib.parse
    url_encoded = urllib.parse.quote(encrypted, safe='')
    
    print(f"\n3. URL encode 结果:")
    print(f"   我的:  {url_encoded}")
    print(f"   期望:  {EXPECTED_URL_ENCODED}")
    print(f"   匹配:  {'✅ 正确!' if url_encoded == EXPECTED_URL_ENCODED else '❌ 不匹配!'}")
    
    # 4. 完整 URL
    full_url = f"https://open-api.hikiot.com/attendance/export/v1/card/report?querySecret={url_encoded}"
    expected_url = "https://open-api.hikiot.com/attendance/export/v1/card/report?querySecret=pmttDL8cTHDp8SRRFnBL69EdlyDVkASZ1MheaGGv38jduOw7ye5MdT1Vtd%2BfThQkrSHUuihMphZXbiGGHGov2N0YWmcmi9QX%2BkFUlNmzafU7MTaUijaPEgku8xHTWXAcP02arqs3RYNNJpfaI86Ruaq%2FbNwT8j%2Fnb1CTuiYbzvw%3D"
    
    print(f"\n4. 完整 URL:")
    print(f"   我的:  {full_url}")
    print(f"   期望:  {expected_url}")
    print(f"   匹配:  {'✅ 正确!' if full_url == expected_url else '❌ 不匹配!'}")
    
    print("\n" + "=" * 60)
    
    return encrypted == EXPECTED_ENCRYPTED

if __name__ == "__main__":
    success = test_encrypt()
    sys.exit(0 if success else 1)
