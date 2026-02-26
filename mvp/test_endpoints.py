#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试海康云 API 端点连通性
"""

import socket
import ssl
import sys

# 可能的 API 端点
ENDPOINTS = [
    "openapi.hikiot.com",
    "open.hikiot.com", 
    "api.hikvision.com",
    "openapi.hikvision.com",
    "hik-open.hikvision.com",
]

def test_tcp_connect(host, port=443, timeout=10):
    """测试 TCP 连接"""
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return True, "TCP 连接成功"
    except socket.timeout:
        return False, "连接超时"
    except socket.gaierror:
        return False, "DNS 解析失败"
    except ConnectionRefused:
        return False, "连接被拒绝"
    except Exception as e:
        return False, str(e)

def test_tls_handshake(host, port=443, timeout=10):
    """测试 TLS 握手"""
    try:
        context = ssl.create_default_context()
        sock = socket.create_connection((host, port), timeout=timeout)
        with context.wrap_socket(sock, server_hostname=host) as ssock:
            cipher = ssock.cipher()
            version = ssock.version()
            return True, f"TLS {version}, Cipher: {cipher[0]}"
    except ssl.SSLError as e:
        return False, f"TLS 错误: {e}"
    except Exception as e:
        return False, str(e)

print("="*60)
print("海康云 API 端点连通性测试")
print("="*60)
print()

for endpoint in ENDPOINTS:
    print(f"测试: {endpoint}")
    
    # TCP 测试
    tcp_ok, tcp_msg = test_tcp_connect(endpoint)
    print(f"  TCP 443: {'✓' if tcp_ok else '✗'} {tcp_msg}")
    
    if tcp_ok:
        # TLS 测试
        tls_ok, tls_msg = test_tls_handshake(endpoint)
        print(f"  TLS: {'✓' if tls_ok else '✗'} {tls_msg}")
    
    print()

print("="*60)
print("说明:")
print("  - 如果 TCP 失败: 可能是网络不通或端口未开放")
print("  - 如果 TLS 失败: 可能是证书问题或协议不匹配")
print("  - 如果都成功: API 签名算法可能有问题")
print("="*60)
