#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康互联开放平台 API 请求加密工具
使用 RSA 公钥加密请求参数（符合海康规范）

加密规则（根据官方文档）:
1. GET 请求: 将参数拼接成 "key1=value1&key2=value2" 格式，RSA 公钥加密后作为 querySecret 参数
2. POST 请求: 将 body 内容 RSA 公钥加密后作为 bodySecret 字段

关键修正：海康要求使用公钥加密，不是私钥！
"""

import os
import json
import base64
import urllib.parse
import logging
from typing import Dict, Optional, Union

# 尝试导入 pycryptodome，如果失败则使用 cryptography
try:
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_v1_5
    CRYPTO_LIB = 'pycryptodome'
except ImportError:
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives import hashes
        CRYPTO_LIB = 'cryptography'
    except ImportError:
        CRYPTO_LIB = None

logger = logging.getLogger(__name__)


class HikvisionRSAEncryptor:
    """海康互联 RSA 加密器 - 使用公钥加密"""
    
    # RSA 加密块大小（PKCS1_v1_5 填充，1024位密钥）
    MAX_ENCRYPT_BLOCK = 117
    MAX_DECRYPT_BLOCK = 128
    
    def __init__(self, public_key_pem: Optional[str] = None):
        """
        初始化 RSA 加密器（使用公钥！）
        
        Args:
            public_key_pem: RSA 公钥（PEM 格式）
                            如果不提供，从环境变量 HIK_PUBLIC_KEY 读取
        """
        # 优先使用传入的参数，其次 HIK_PUBLIC_KEY
        self.public_key_pem = public_key_pem or os.getenv('HIK_PUBLIC_KEY')
        self._public_key = None
        
        if self.public_key_pem:
            key_preview = self.public_key_pem[:50] if len(self.public_key_pem) > 50 else self.public_key_pem
            logger.info(f"[RSA初始化] 公钥来源: {'传入参数' if public_key_pem else '环境变量'}")
            logger.info(f"[RSA初始化] 公钥前50字符: {key_preview}...")
            logger.info(f"[RSA初始化] 公钥总长度: {len(self.public_key_pem)} 字符")
            self._load_key()
        else:
            logger.warning("[RSA初始化] 未配置 RSA 公钥（HIK_PUBLIC_KEY），无法进行请求加密")
    
    def _load_key(self):
        """加载 RSA 公钥"""
        try:
            key_content = self.public_key_pem.strip()
            
            # 处理纯 base64 公钥字符串
            if '-----BEGIN' not in key_content:
                # 每 64 字符换行（PEM 标准格式）
                key_lines = []
                for i in range(0, len(key_content), 64):
                    key_lines.append(key_content[i:i+64])
                key_with_newlines = '\n'.join(key_lines)
                
                key_content = f"-----BEGIN PUBLIC KEY-----\n{key_with_newlines}\n-----END PUBLIC KEY-----"
                logger.info("[RSA初始化] 纯 key 字符串，已包装为 PEM 格式")
                logger.info(f"[RSA初始化] 包装后前100字符:\n{key_content[:100]}...")
            
            if CRYPTO_LIB == 'pycryptodome':
                self._public_key = RSA.import_key(key_content)
                logger.info(f"[RSA初始化] 公钥加载成功 (pycryptodome)")
                logger.info(f"[RSA初始化] 密钥大小: {self._public_key.size_in_bits()} bits")
                
            elif CRYPTO_LIB == 'cryptography':
                self._public_key = serialization.load_pem_public_key(
                    key_content.encode('utf-8')
                )
                logger.info("[RSA初始化] 公钥加载成功 (cryptography)")
            else:
                raise ImportError("未安装加密库，请安装 pycryptodome 或 cryptography")
                
        except Exception as e:
            logger.error(f"[RSA初始化] RSA 公钥加载失败: {e}")
            logger.error(f"[RSA初始化] 公钥内容前50字符: {self.public_key_pem[:50]}...")
            raise
    
    def encrypt(self, plain_text: str) -> str:
        """
        RSA 加密字符串（使用公钥）
        
        海康标准加密流程：
        1. 明文转 UTF-8 字节流
        2. RSA PKCS1_v1_5 加密（使用公钥）
        3. Base64 编码
        
        Args:
            plain_text: 待加密的明文字符串
            
        Returns:
            Base64 编码的加密结果
        """
        if not self._public_key:
            raise ValueError("RSA 公钥未配置，无法加密")
        
        try:
            logger.info(f"[RSA加密] 原始明文: {plain_text}")
            
            # 1. 转 UTF-8 字节
            plain_bytes = plain_text.encode('utf-8')
            logger.info(f"[RSA加密] 数据长度: {len(plain_bytes)} 字节")
            
            # 2. RSA 加密（PKCS1_v1_5 填充，使用公钥）
            if CRYPTO_LIB == 'pycryptodome':
                cipher = PKCS1_v1_5.new(self._public_key)
                
                # 分段加密
                encrypted_blocks = []
                for i in range(0, len(plain_bytes), self.MAX_ENCRYPT_BLOCK):
                    block = plain_bytes[i:i + self.MAX_ENCRYPT_BLOCK]
                    encrypted_block = cipher.encrypt(block)
                    encrypted_blocks.append(encrypted_block)
                    logger.info(f"[RSA加密] 块 {len(encrypted_blocks)}: {len(block)} 字节 -> {len(encrypted_block)} 字节")
                
                encrypted_bytes = b''.join(encrypted_blocks)
            
            elif CRYPTO_LIB == 'cryptography':
                from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
                
                encrypted_blocks = []
                for i in range(0, len(plain_bytes), self.MAX_ENCRYPT_BLOCK):
                    block = plain_bytes[i:i + self.MAX_ENCRYPT_BLOCK]
                    encrypted_block = self._public_key.encrypt(
                        block,
                        asym_padding.PKCS1v15()
                    )
                    encrypted_blocks.append(encrypted_block)
                    logger.info(f"[RSA加密] 块 {len(encrypted_blocks)}: {len(block)} 字节 -> {len(encrypted_block)} 字节")
                
                encrypted_bytes = b''.join(encrypted_blocks)
            
            # 3. Base64 编码
            encrypted_b64 = base64.b64encode(encrypted_bytes).decode('utf-8')
            logger.info(f"[RSA加密] Base64 结果长度: {len(encrypted_b64)} 字符")
            logger.info(f"[RSA加密] Base64 前100字符: {encrypted_b64[:100]}...")
            
            return encrypted_b64
            
        except Exception as e:
            logger.error(f"[RSA加密] 加密失败: {e}")
            raise
    
    def encrypt_get_params(self, params: Dict[str, Union[str, int, bool]]) -> str:
        """
        加密 GET 请求参数
        
        海康标准流程：
        1. 参数组合成 key=value&key2=value2（参数值不做 URL encode）
        2. RSA 公钥加密
        3. Base64 编码
        4. URL encode（用于 querySecret）
        
        Args:
            params: 参数字典
            
        Returns:
            URL encode 后的加密结果（用于 querySecret）
        """
        # 1. 构建参数字符串
        param_pairs = []
        for key, value in sorted(params.items()):
            if value is not None:
                param_pairs.append(f"{key}={value}")
        
        param_string = "&".join(param_pairs)
        logger.info(f"[RSA加密GET] 原始参数字符串: {param_string}")
        
        # 2. RSA 加密
        encrypted_b64 = self.encrypt(param_string)
        
        # 3. URL encode（用于 GET 请求参数）
        url_encoded = urllib.parse.quote(encrypted_b64, safe='')
        logger.info(f"[RSA加密GET] URL encode 后长度: {len(url_encoded)} 字符")
        
        return url_encoded
    
    def encrypt_post_body(self, body: Union[Dict, str]) -> Dict:
        """
        加密 POST 请求体
        
        Args:
            body: 请求体（字典或 JSON 字符串）
            
        Returns:
            包含 bodySecret 的字典
        """
        # 1. 转换为 JSON 字符串
        if isinstance(body, dict):
            body_str = json.dumps(body, ensure_ascii=False, separators=(',', ':'))
        else:
            body_str = body
        
        logger.info(f"[RSA加密POST] JSON字符串: {body_str}")
        
        # 2. RSA 加密
        encrypted_b64 = self.encrypt(body_str)
        
        # 3. 返回 bodySecret 格式
        logger.info(f"[RSA加密POST] 最终 bodySecret 长度: {len(encrypted_b64)} 字符")
        
        return {"bodySecret": encrypted_b64}


# 创建全局加密器实例（使用公钥）
encryptor = HikvisionRSAEncryptor()


def get_encryptor() -> HikvisionRSAEncryptor:
    """获取全局加密器实例"""
    return encryptor


def reload_encryptor(public_key_pem: Optional[str] = None):
    """重新加载加密器（用于动态更新公钥）"""
    global encryptor
    encryptor = HikvisionRSAEncryptor(public_key_pem)
    return encryptor


# 便捷函数
def encrypt_get_params(params: Dict) -> str:
    """加密 GET 参数"""
    return encryptor.encrypt_get_params(params)


def encrypt_post_body(body: Union[Dict, str]) -> Dict:
    """加密 POST 请求体"""
    return encryptor.encrypt_post_body(body)


if __name__ == "__main__":
    # 测试代码
    import sys
    
    # 示例公钥（测试用）
    test_key = """-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDQENQu1UqP9wR4bb6h
-----END PUBLIC KEY-----"""
    
    # 从环境变量读取
    public_key = os.getenv('HIK_PUBLIC_KEY', test_key)
    
    if not public_key or public_key == test_key:
        print("请设置 HIK_PUBLIC_KEY 环境变量")
        sys.exit(1)
    
    # 创建加密器
    enc = HikvisionRSAEncryptor(public_key)
    
    # 测试 GET 参数加密
    test_params = {
        "authCode": "863bd1f4aa218e9b5ddeaa6e26561799"
    }
    
    encrypted = enc.encrypt_get_params(test_params)
    print(f"\n加密后的 querySecret: {encrypted}")
