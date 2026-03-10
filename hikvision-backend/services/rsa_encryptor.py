#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康互联开放平台 API 请求加密工具
使用 RSA 私钥加密（OpenSSL 兼容实现）

根据海康官方 C++ 代码复现：
1. 先对数据进行 URL encode
2. 使用 RSA_PKCS1_PADDING 填充
3. 分段加密（每段 keySize - 11 字节）
4. Base64 编码（无换行）
"""

import os
import json
import base64
import urllib.parse
import logging
from typing import Dict, Optional, Union

# 尝试导入 pycryptodome
try:
    from Crypto.PublicKey import RSA
    from Crypto.Cipher import PKCS1_v1_5
    CRYPTO_LIB = 'pycryptodome'
except ImportError:
    CRYPTO_LIB = None

logger = logging.getLogger(__name__)


class HikvisionRSAEncryptor:
    """海康互联 RSA 加密器 - OpenSSL 兼容实现"""
    
    def __init__(self, private_key_pem: Optional[str] = None):
        """
        初始化 RSA 加密器
        
        Args:
            private_key_pem: RSA 私钥（PEM 格式或纯 base64 字符串）
                              如果不提供，从环境变量 HIK_APP_SECRET 读取
        """
        self.private_key_pem = private_key_pem or os.getenv('HIK_APP_SECRET')
        self._private_key = None
        self._key_size = 0
        self._max_encrypt_block = 0
        
        if self.private_key_pem:
            self._load_key()
        else:
            logger.warning("[RSA] 未配置私钥（HIK_APP_SECRET）")
    
    def _load_key(self):
        """加载 RSA 私钥"""
        try:
            key_content = self.private_key_pem.strip()
            
            # 处理纯 base64 私钥（海康 HIK_APP_SECRET 格式）
            if '-----BEGIN' not in key_content:
                key_content = f"-----BEGIN RSA PRIVATE KEY-----\n{key_content}\n-----END RSA PRIVATE KEY-----"
                logger.info("[RSA] 已包装为 PEM 格式")
            
            if CRYPTO_LIB == 'pycryptodome':
                self._private_key = RSA.import_key(key_content)
                self._key_size = self._private_key.size_in_bits() // 8  # 转换为字节
                # RSA_PKCS1_PADDING: max_input = key_size - 11
                self._max_encrypt_block = self._key_size - 11
                logger.info(f"[RSA] 私钥加载成功: {self._key_size * 8} bits, 最大块: {self._max_encrypt_block} 字节")
            else:
                raise ImportError("需要安装 pycryptodome: pip install pycryptodome")
                
        except Exception as e:
            logger.error(f"[RSA] 私钥加载失败: {e}")
            raise
    
    def _url_encode(self, data: str) -> str:
        """
        URL encode（兼容海康 C++ 实现）
        保留字符: A-Z a-z 0-9 - _ . ~
        其他字符: %XX
        """
        return urllib.parse.quote(data, safe='-_.~')
    
    def _url_decode(self, data: str) -> str:
        """URL decode"""
        return urllib.parse.unquote(data)
    
    def encrypt(self, plain_text: str) -> str:
        """
        RSA 加密（OpenSSL 兼容）
        
        流程:
        1. URL encode 明文
        2. RSA_PKCS1_PADDING 加密（分段）
        3. Base64 编码（无换行）
        
        Args:
            plain_text: 待加密的明文字符串
            
        Returns:
            Base64 编码的加密结果
        """
        if not self._private_key:
            raise ValueError("RSA 私钥未配置")
        
        try:
            logger.info(f"[RSA加密] 原始明文: {plain_text}")
            
            # 1. URL encode（海康 C++ 代码在加密前做 URL encode）
            url_encoded = self._url_encode(plain_text)
            logger.info(f"[RSA加密] URL encode 后: {url_encoded}")
            
            # 2. 转字节
            plain_bytes = url_encoded.encode('utf-8')
            logger.info(f"[RSA加密] 数据长度: {len(plain_bytes)} 字节, 块大小: {self._max_encrypt_block}")
            
            # 3. RSA 加密（PKCS1_v1_5 对应 OpenSSL 的 RSA_PKCS1_PADDING）
            cipher = PKCS1_v1_5.new(self._private_key)
            
            encrypted_blocks = []
            for i in range(0, len(plain_bytes), self._max_encrypt_block):
                block = plain_bytes[i:i + self._max_encrypt_block]
                encrypted_block = cipher.encrypt(block)
                encrypted_blocks.append(encrypted_block)
                logger.info(f"[RSA加密] 块 {len(encrypted_blocks)}: {len(block)} -> {len(encrypted_block)} 字节")
            
            encrypted_bytes = b''.join(encrypted_blocks)
            
            # 4. Base64 编码（无换行，BIO_FLAGS_BASE64_NO_NL）
            encrypted_b64 = base64.b64encode(encrypted_bytes).decode('utf-8')
            logger.info(f"[RSA加密] Base64 结果: {len(encrypted_b64)} 字符")
            
            return encrypted_b64
            
        except Exception as e:
            logger.error(f"[RSA加密] 失败: {e}")
            raise
    
    def decrypt(self, encrypted_b64: str) -> str:
        """
        RSA 解密（OpenSSL 兼容）
        
        流程:
        1. Base64 解码
        2. RSA_PKCS1_PADDING 解密（分段）
        3. URL decode
        
        Args:
            encrypted_b64: Base64 编码的加密数据
            
        Returns:
            解密后的明文字符串
        """
        if not self._private_key:
            raise ValueError("RSA 私钥未配置")
        
        try:
            logger.info(f"[RSA解密] Base64 输入: {encrypted_b64[:50]}...")
            
            # 1. Base64 解码
            encrypted_bytes = base64.b64decode(encrypted_b64)
            logger.info(f"[RSA解密] 解码后: {len(encrypted_bytes)} 字节")
            
            # 2. RSA 解密（分段）
            cipher = PKCS1_v1_5.new(self._private_key)
            
            decrypted_blocks = []
            for i in range(0, len(encrypted_bytes), self._key_size):
                block = encrypted_bytes[i:i + self._key_size]
                decrypted_block = cipher.decrypt(block, sentinel=None)
                if decrypted_block:
                    decrypted_blocks.append(decrypted_block)
                logger.info(f"[RSA解密] 块 {len(decrypted_blocks)}: {len(block)} -> {len(decrypted_block) if decrypted_block else 0} 字节")
            
            decrypted_bytes = b''.join(decrypted_blocks)
            
            # 3. URL decode
            decrypted_str = decrypted_bytes.decode('utf-8')
            plain_text = self._url_decode(decrypted_str)
            logger.info(f"[RSA解密] 结果: {plain_text}")
            
            return plain_text
            
        except Exception as e:
            logger.error(f"[RSA解密] 失败: {e}")
            raise
    
    def encrypt_get_params(self, params: Dict[str, Union[str, int, bool]]) -> str:
        """
        加密 GET 请求参数
        
        Args:
            params: 参数字典
            
        Returns:
            URL encode 后的加密结果（用于 querySecret）
        """
        # 构建参数字符串（不预先 URL encode 参数值）
        param_pairs = []
        for key, value in sorted(params.items()):
            if value is not None:
                param_pairs.append(f"{key}={value}")
        
        param_string = "&".join(param_pairs)
        logger.info(f"[RSA加密GET] 参数字符串: {param_string}")
        
        # 加密（内部会做 URL encode）
        encrypted_b64 = self.encrypt(param_string)
        
        # URL encode 用于 GET 请求
        url_encoded = urllib.parse.quote(encrypted_b64, safe='')
        logger.info(f"[RSA加密GET] querySecret: {url_encoded[:80]}...")
        
        return url_encoded
    
    def encrypt_post_body(self, body: Union[Dict, str]) -> Dict:
        """
        加密 POST 请求体
        
        Args:
            body: 请求体（字典或 JSON 字符串）
            
        Returns:
            包含 bodySecret 的字典
        """
        if isinstance(body, dict):
            body_str = json.dumps(body, ensure_ascii=False, separators=(',', ':'))
        else:
            body_str = body
        
        logger.info(f"[RSA加密POST] JSON: {body_str}")
        
        encrypted_b64 = self.encrypt(body_str)
        
        return {"bodySecret": encrypted_b64}


# 全局实例
encryptor = HikvisionRSAEncryptor()


def get_encryptor() -> HikvisionRSAEncryptor:
    """获取全局加密器"""
    return encryptor


def reload_encryptor(private_key_pem: Optional[str] = None):
    """重新加载加密器"""
    global encryptor
    encryptor = HikvisionRSAEncryptor(private_key_pem)
    return encryptor


# 便捷函数
def encrypt_get_params(params: Dict) -> str:
    return encryptor.encrypt_get_params(params)


def encrypt_post_body(body: Union[Dict, str]) -> Dict:
    return encryptor.encrypt_post_body(body)


def decrypt_response(encrypted_b64: str) -> str:
    return encryptor.decrypt(encrypted_b64)


if __name__ == "__main__":
    import sys
    
    private_key = os.getenv('HIK_APP_SECRET')
    if not private_key:
        print("请设置 HIK_APP_SECRET 环境变量")
        sys.exit(1)
    
    enc = HikvisionRSAEncryptor(private_key)
    
    # 测试
    test_params = {"authCode": "863bd1f4aa218e9b5ddeaa6e26561799"}
    result = enc.encrypt_get_params(test_params)
    print(f"\n加密结果: {result}")
