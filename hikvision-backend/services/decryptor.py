#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康互联消息解密工具
支持 AES-256-CBC 解密和 Verification Token 校验

加密原理（来自海康官方文档）：
1. 使用 SHA256 对 Encrypt Key 进行哈希得到密钥 key
2. 使用 PKCS7Padding 方式将事件内容进行填充
3. 生成 16 字节的随机数作为初始向量 iv
4. 使用 iv 和 key 对事件内容加密得到 encrypted_event
5. 应用收到的密文为 base64(iv+encrypted_event)
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
        
        # 预计算 SHA256 密钥
        if self.encrypt_key:
            self._key_hash = hashlib.sha256(self.encrypt_key.encode('utf-8')).digest()
        else:
            self._key_hash = None
    
    def decrypt_event(self, encrypted_base64):
        """
        解密海康事件内容
        
        按照海康官方文档的 AES-256-CBC 解密流程：
        1. Base64 解码得到 iv + encrypted_data
        2. 使用 SHA256(EncryptKey) 作为密钥
        3. AES-CBC 解密
        4. PKCS7Padding 去填充
        
        Args:
            encrypted_base64: Base64 编码的加密事件内容
            
        Returns:
            str: 解密后的事件内容（JSON 字符串）
        """
        if not self._key_hash:
            logger.warning("没有配置 EncryptKey，无法解密")
            return None
        
        try:
            # Base64 解码
            encrypted_bytes = base64.b64decode(encrypted_base64)
            
            # 提取 IV（前 16 字节）和密文
            iv = encrypted_bytes[:16]
            ciphertext = encrypted_bytes[16:]
            
            # AES-256-CBC 解密（使用 SHA256(EncryptKey) 作为密钥）
            cipher = AES.new(self._key_hash, AES.MODE_CBC, iv)
            decrypted_bytes = cipher.decrypt(ciphertext)
            
            # PKCS7Padding 去填充
            decrypted_bytes = unpad(decrypted_bytes, AES.block_size)
            
            return decrypted_bytes.decode('utf-8')
            
        except Exception as e:
            logger.error(f"事件解密失败: {e}")
            return None
    
    def decrypt_message(self, encrypted_data):
        """
        解密海康推送的消息（完整消息格式）
        
        Args:
            encrypted_data: 加密的消息数据（包含 encryptData、encryptKey 等字段）
            
        Returns:
            dict: 解密后的消息内容
        """
        try:
            # 获取加密数据
            encrypt_data = encrypted_data.get('encryptData') or encrypted_data.get('encrypt_data')
            
            if not encrypt_data:
                logger.warning("没有加密数据，返回原始数据")
                return encrypted_data
            
            # 解密事件内容
            decrypted_message = self.decrypt_event(encrypt_data)
            if decrypted_message:
                return json.loads(decrypted_message)
            else:
                return encrypted_data
                
        except Exception as e:
            logger.error(f"解密消息失败: {e}")
            return encrypted_data
    
    def verify_token(self, request_headers, decrypted_body=None):
        """
        验证 Verification Token
        
        海康会在请求头中传递 Verification-Token：
        - 如果是加密事件，需要从解密后的内容中获取 VerificationToken 进行校验
        - 如果是未加密事件，直接从请求头中获取 VerificationToken 进行校验
        
        Args:
            request_headers: 请求头字典
            decrypted_body: 解密后的消息体（如果是加密事件）
            
        Returns:
            bool: 验证是否通过
        """
        if not self.verification_token:
            logger.warning("没有配置 VerificationToken，跳过验证")
            return True
        
        try:
            # 从请求头获取 Verification-Token
            header_token = request_headers.get('Verification-Token') or request_headers.get('verification-token')
            
            # 如果是加密事件，从解密后的内容中获取 VerificationToken
            if decrypted_body and isinstance(decrypted_body, dict):
                body_token = decrypted_body.get('VerificationToken') or decrypted_body.get('verification_token')
                if body_token:
                    return hmac.compare_digest(body_token, self.verification_token)
            
            # 如果是未加密事件，直接比较请求头中的 Token
            if header_token:
                return hmac.compare_digest(header_token, self.verification_token)
            
            logger.warning("请求中没有找到 VerificationToken")
            return False
            
        except Exception as e:
            logger.error(f"Token 验证失败: {e}")
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
            
            # 计算签名（与海康保持一致）
            message = f"{self.verification_token}{timestamp}{nonce}{echo_str}"
            expected_signature = hashlib.sha1(message.encode('utf-8')).hexdigest()
            
            if msg_signature != expected_signature:
                logger.error(f"URL 验证签名不匹配: expected={expected_signature}, got={msg_signature}")
                return None
            
            # 解密 echo_str
            if self.encrypt_key:
                decrypted = self.decrypt_event(echo_str)
                return decrypted if decrypted else echo_str
            else:
                return echo_str
                
        except Exception as e:
            logger.error(f"URL 验证失败: {e}")
            return None
    
    def encrypt_response(self, plaintext):
        """
        加密响应内容（用于海康 URL 验证回调）
        
        海康要求返回加密的 JSON 格式：{"encryptData": "xxx"}
        
        Args:
            plaintext: 明文内容（如 "success"）
            
        Returns:
            dict: 包含 encryptData 的字典
        """
        if not self._key_hash:
            logger.warning("没有配置 EncryptKey，返回明文")
            return {"data": plaintext}
        
        try:
            from Crypto.Cipher import AES
            from Crypto.Util.Padding import pad
            import os
            
            # 生成随机 IV
            iv = os.urandom(16)
            
            # PKCS7 填充
            data_bytes = plaintext.encode('utf-8')
            padded_data = pad(data_bytes, AES.block_size)
            
            # AES-256-CBC 加密
            cipher = AES.new(self._key_hash, AES.MODE_CBC, iv)
            encrypted = cipher.encrypt(padded_data)
            
            # iv + ciphertext，然后 Base64 编码
            encrypted_bytes = iv + encrypted
            encrypted_base64 = base64.b64encode(encrypted_bytes).decode('utf-8')
            
            return {"encryptData": encrypted_base64}
            
        except Exception as e:
            logger.error(f"加密响应失败: {e}")
            return {"data": plaintext}


# 创建全局解密器实例
decryptor = HikvisionMessageDecryptor()
