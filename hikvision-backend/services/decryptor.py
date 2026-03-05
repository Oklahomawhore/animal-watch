#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康互联消息解密工具
支持 AES 解密和签名验证
"""

import os
import json
import base64
import hashlib
import hmac
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
import logging

logger = logging.getLogger(__name__)


class HikvisionMessageDecryptor:
    """海康互联消息解密器"""
    
    def __init__(self, encrypt_key=None, verification_token=None):
        """
        初始化解密器
        
        Args:
            encrypt_key: 加密密钥（从海康平台获取）
            verification_token: 验证令牌（从海康平台获取）
        """
        self.encrypt_key = encrypt_key or os.getenv('HIK_ENCRYPT_KEY')
        self.verification_token = verification_token or os.getenv('HIK_VERIFICATION_TOKEN')
    
    def decrypt_message(self, encrypted_data):
        """
        解密海康推送的消息
        
        Args:
            encrypted_data: 加密的消息数据（包含 encryptData、encryptKey 等字段）
            
        Returns:
            dict: 解密后的消息内容
        """
        try:
            # 获取加密数据
            encrypt_data = encrypted_data.get('encryptData') or encrypted_data.get('encrypt_data')
            encrypt_key = encrypted_data.get('encryptKey') or encrypted_data.get('encrypt_key')
            
            if not encrypt_data:
                logger.warning("没有加密数据，返回原始数据")
                return encrypted_data
            
            # 如果提供了 encryptKey，需要先用 EncryptKey 解密
            if encrypt_key and self.encrypt_key:
                # 解密 encryptKey（使用 HIK_ENCRYPT_KEY）
                decrypted_key = self._decrypt_aes(encrypt_key, self.encrypt_key)
            else:
                decrypted_key = self.encrypt_key
            
            # 使用解密后的密钥解密消息内容
            if decrypted_key:
                decrypted_message = self._decrypt_aes(encrypt_data, decrypted_key)
                return json.loads(decrypted_message)
            else:
                logger.warning("没有解密密钥，返回原始数据")
                return encrypted_data
                
        except Exception as e:
            logger.error(f"解密消息失败: {e}")
            return encrypted_data
    
    def _decrypt_aes(self, encrypted_data, key):
        """
        AES 解密
        
        Args:
            encrypted_data: Base64 编码的加密数据
            key: 解密密钥
            
        Returns:
            str: 解密后的字符串
        """
        try:
            # Base64 解码
            encrypted_bytes = base64.b64decode(encrypted_data)
            
            # 准备密钥（确保 16/24/32 字节）
            key_bytes = key.encode('utf-8')
            if len(key_bytes) < 16:
                key_bytes = key_bytes.ljust(16, b'\0')
            elif len(key_bytes) > 32:
                key_bytes = key_bytes[:32]
            elif len(key_bytes) not in [16, 24, 32]:
                # 补齐到最近的合法长度
                if len(key_bytes) < 24:
                    key_bytes = key_bytes.ljust(16, b'\0')
                elif len(key_bytes) < 32:
                    key_bytes = key_bytes.ljust(24, b'\0')
                else:
                    key_bytes = key_bytes.ljust(32, b'\0')
            
            # 提取 IV（前 16 字节）和密文
            iv = encrypted_bytes[:16]
            ciphertext = encrypted_bytes[16:]
            
            # 创建 AES 解密器
            cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
            
            # 解密并去除填充
            decrypted_bytes = unpad(cipher.decrypt(ciphertext), AES.block_size)
            
            return decrypted_bytes.decode('utf-8')
            
        except Exception as e:
            logger.error(f"AES 解密失败: {e}")
            raise
    
    def verify_signature(self, data, signature):
        """
        验证消息签名
        
        Args:
            data: 消息数据
            signature: 签名
            
        Returns:
            bool: 签名是否有效
        """
        if not self.verification_token:
            logger.warning("没有配置 VerificationToken，跳过签名验证")
            return True
        
        try:
            # 计算签名
            message = json.dumps(data, sort_keys=True, ensure_ascii=False)
            expected_signature = hmac.new(
                self.verification_token.encode('utf-8'),
                message.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"签名验证失败: {e}")
            return False
    
    def verify_url(self, msg_signature, timestamp, nonce, echo_str):
        """
        验证回调 URL（海康配置回调时调用）
        
        Args:
            msg_signature: 消息签名
            timestamp: 时间戳
            nonce: 随机数
            echo_str: 回显字符串
            
        Returns:
            str: 解密后的 echo_str（用于响应海康的验证请求）
        """
        try:
            if not self.verification_token:
                logger.warning("没有配置 VerificationToken，直接返回 echo_str")
                return echo_str
            
            # 计算签名
            message = f"{self.verification_token}{timestamp}{nonce}{echo_str}"
            expected_signature = hashlib.sha1(message.encode('utf-8')).hexdigest()
            
            if msg_signature != expected_signature:
                logger.error("URL 验证签名不匹配")
                return None
            
            # 解密 echo_str
            if self.encrypt_key:
                return self._decrypt_aes(echo_str, self.encrypt_key)
            else:
                return echo_str
                
        except Exception as e:
            logger.error(f"URL 验证失败: {e}")
            return None


# 创建全局解密器实例
decryptor = HikvisionMessageDecryptor()
