#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康互联开放平台 API 请求加密工具
使用 RSA 私钥加密请求参数

加密规则（根据官方文档）:
1. GET 请求: 将参数拼接成 "key1=value1&key2=value2" 格式，RSA 加密后作为 querySecret 参数
2. POST 请求: 将 body 内容 RSA 加密后作为 bodySecret 字段
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
    """海康互联 RSA 加密器"""
    
    # RSA 加密块大小（PKCS1_v1_5 填充）
    MAX_ENCRYPT_BLOCK = 117  # 1024位密钥时
    MAX_DECRYPT_BLOCK = 128
    
    def __init__(self, private_key_pem: Optional[str] = None):
        """
        初始化 RSA 加密器
        
        Args:
            private_key_pem: RSA 私钥（PEM 格式，包含 BEGIN/END 标记）
                              如果不提供，从环境变量 HIK_PRIVATE_KEY 或 HIK_APP_SECRET 读取
        """
        # 优先使用传入的参数，其次 HIK_PRIVATE_KEY，最后 HIK_APP_SECRET
        self.private_key_pem = private_key_pem or os.getenv('HIK_PRIVATE_KEY') or os.getenv('HIK_APP_SECRET')
        self._private_key = None
        
        if self.private_key_pem:
            key_preview = self.private_key_pem[:50] if len(self.private_key_pem) > 50 else self.private_key_pem
            logger.info(f"[RSA初始化] 私钥来源: {'传入参数' if private_key_pem else '环境变量'}")
            logger.info(f"[RSA初始化] 私钥前50字符: {key_preview}...")
            logger.info(f"[RSA初始化] 私钥总长度: {len(self.private_key_pem)} 字符")
            self._load_key()
        else:
            logger.warning("[RSA初始化] 未配置 RSA 私钥（HIK_PRIVATE_KEY 或 HIK_APP_SECRET），无法进行请求加密")
    
    def _load_key(self):
        """加载 RSA 私钥"""
        try:
            key_content = self.private_key_pem.strip()
            
            if '-----BEGIN' not in key_content:
                # 纯 base64 字符串，需要包装成 PEM 格式
                # 每 64 字符换行（PEM 标准格式）
                key_lines = []
                for i in range(0, len(key_content), 64):
                    key_lines.append(key_content[i:i+64])
                key_with_newlines = '\n'.join(key_lines)
                
                key_content = f"-----BEGIN RSA PRIVATE KEY-----\n{key_with_newlines}\n-----END RSA PRIVATE KEY-----"
                logger.info("[RSA初始化] 纯 key 字符串，已包装为 PEM 格式")
                logger.info(f"[RSA初始化] 包装后前100字符:\n{key_content[:100]}...")
            
            if CRYPTO_LIB == 'pycryptodome':
                self._private_key = RSA.import_key(key_content)
                logger.info(f"[RSA初始化] 私钥加载成功 (pycryptodome)")
                logger.info(f"[RSA初始化] 密钥大小: {self._private_key.size_in_bits()} bits")
                
            elif CRYPTO_LIB == 'cryptography':
                self._private_key = serialization.load_pem_private_key(
                    key_content.encode('utf-8'),
                    password=None
                )
                logger.info("[RSA初始化] 私钥加载成功 (cryptography)")
            else:
                raise ImportError("未安装加密库，请安装 pycryptodome 或 cryptography")
                
        except Exception as e:
            logger.error(f"[RSA初始化] RSA 私钥加载失败: {e}")
            logger.error(f"[RSA初始化] 私钥内容前50字符: {self.private_key_pem[:50]}...")
            raise
    
    def _encrypt_block_pycryptodome(self, data: bytes) -> bytes:
        """使用 pycryptodome 加密单个块"""
        cipher = PKCS1_v1_5.new(self._private_key)
        return cipher.encrypt(data)
    
    def _encrypt_block_cryptography(self, data: bytes) -> bytes:
        """使用 cryptography 加密单个块"""
        return self._private_key.sign(
            data,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
    
    def encrypt(self, plaintext: str, url_encode_input: bool = True) -> str:
        """
        RSA 加密字符串
        
        按照海康文档要求:
        1. 先对明文进行 URL encode（可选，GET参数加密时不需要）
        2. 分段 RSA 加密（每段不超过 117 字节）
        3. Base64 编码结果
        
        Args:
            plaintext: 待加密的明文字符串
            url_encode_input: 是否对输入做URL encode（GET参数加密时应为False）
            
        Returns:
            Base64 编码的加密结果
        """
        if not self._private_key:
            raise ValueError("RSA 私钥未配置，无法加密")
        
        try:
            # 1. 可选：URL encode
            if url_encode_input:
                url_encoded = urllib.parse.quote(plaintext, safe='')
                data_bytes = url_encoded.encode('utf-8')
                logger.info(f"[RSA加密] URL编码后: {url_encoded}")
            else:
                data_bytes = plaintext.encode('utf-8')
                logger.info(f"[RSA加密] 不做URL编码，直接加密")
            
            logger.info(f"[RSA加密] 原始明文: {plaintext}")
            logger.info(f"[RSA加密] 数据长度: {len(data_bytes)} 字节")
            
            # 2. 分段加密
            encrypted_blocks = []
            
            if CRYPTO_LIB == 'pycryptodome':
                cipher = PKCS1_v1_5.new(self._private_key)
                
                for i in range(0, len(data_bytes), self.MAX_ENCRYPT_BLOCK):
                    block = data_bytes[i:i + self.MAX_ENCRYPT_BLOCK]
                    logger.info(f"[RSA加密] 加密块 {i//self.MAX_ENCRYPT_BLOCK + 1}: {len(block)} 字节")
                    encrypted_block = cipher.encrypt(block)
                    encrypted_blocks.append(encrypted_block)
                    logger.info(f"[RSA加密] 块加密结果长度: {len(encrypted_block)} 字节")
            
            elif CRYPTO_LIB == 'cryptography':
                from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
                
                for i in range(0, len(data_bytes), self.MAX_ENCRYPT_BLOCK):
                    block = data_bytes[i:i + self.MAX_ENCRYPT_BLOCK]
                    # 使用私钥加密（海康要求用私钥加密）
                    # 注意：标准 RSA 是用公钥加密、私钥解密
                    # 海康这里用的是私钥加密（相当于签名）
                    encrypted_block = self._private_key.sign(
                        block,
                        asym_padding.PKCS1v15(),
                        hashes.SHA256()
                    )
                    encrypted_blocks.append(encrypted_block)
            
            # 3. 拼接所有加密块并 Base64 编码
            encrypted_data = b''.join(encrypted_blocks)
            encrypted_base64 = base64.b64encode(encrypted_data).decode('utf-8')
            
            logger.info(f"[RSA加密] 最终密文长度: {len(encrypted_base64)} 字符")
            logger.info(f"[RSA加密] 密文前100字符: {encrypted_base64[:100]}...")
            
            return encrypted_base64
            
        except Exception as e:
            logger.error(f"[RSA加密] 加密失败: {e}")
            raise
    
    def encrypt_get_params(self, params: Dict[str, Union[str, int, bool]]) -> str:
        """
        加密 GET 请求参数
        
        按照海康官方文档:
        1. 获取所有GET请求参数（?后面的字符串，不包含?）
        2. 将请求参数组合成 参数=参数值 的格式，并且把这些参数用&字符连接起来
           ⚠️ 注意：这里不需要对参数值做URL encode！
        3. 用RSA加密
        4. 将加密后的字符串做url encode操作
        5. 拼接成querySecret=url encode后字符串
        
        Args:
            params: 参数字典，如 {"departNos": "BM0001", "beginDate": "2024-08-01"}
            
        Returns:
            加密后的 querySecret 值（已 URL encode）
        """
        # 1. 构建参数字符串 "key1=value1&key2=value2"
        # ⚠️ 关键：海康官方示例中，参数值是明文，不做URL encode！
        param_pairs = []
        for key, value in sorted(params.items()):  # 按 key 排序确保一致性
            if value is not None:
                # 不做 URL encode，直接使用原始值
                param_pairs.append(f"{key}={value}")
        
        param_string = "&".join(param_pairs)
        logger.info(f"[RSA加密GET] 原始参数字符串: {param_string}")
        
        # 2. RSA 加密（GET参数不需要内部URL encode）
        encrypted = self.encrypt(param_string, url_encode_input=False)
        
        # 3. URL encode 加密结果
        query_secret = urllib.parse.quote(encrypted, safe='')
        
        logger.info(f"[RSA加密GET] 最终 querySecret 长度: {len(query_secret)} 字符")
        
        return query_secret
    
    def encrypt_post_body(self, body: Union[Dict, str]) -> Dict:
        """
        加密 POST 请求体
        
        按照海康官方文档:
        1. 获取 POST 请求参数（request body 中的内容）
        2. 直接用 RSA 加密（不做 URL encode）
        3. 拼接成 {"bodySecret": "加密后字符串"}
        
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
        
        # 2. RSA 加密（POST body 也不需要内部 URL encode）
        encrypted = self.encrypt(body_str, url_encode_input=False)
        
        # 3. 返回 bodySecret 格式
        logger.info(f"[RSA加密POST] 最终 bodySecret 长度: {len(encrypted)} 字符")
        
        return {"bodySecret": encrypted}
    
    def decrypt_response(self, encrypted_data: str) -> str:
        """
        解密响应数据（海康返回的加密 data 字段）
        
        按照海康官方文档的解密流程:
        1. Base64 解码
        2. 分段 RSA 解密（每段 128 字节）
        3. URL decode
        
        Args:
            encrypted_data: Base64 编码的加密数据
            
        Returns:
            解密后的明文字符串
        """
        if not self._private_key:
            raise ValueError("RSA 私钥未配置，无法解密")
        
        try:
            logger.info(f"[RSA解密] 密文长度: {len(encrypted_data)} 字符")
            logger.info(f"[RSA解密] 密文前100字符: {encrypted_data[:100]}...")
            
            # Base64 解码
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            logger.info(f"[RSA解密] Base64解码后长度: {len(encrypted_bytes)} 字节")
            
            # 分段解密
            decrypted_data = b""
            input_len = len(encrypted_bytes)
            offset = 0
            block_count = 0
            
            if CRYPTO_LIB == 'pycryptodome':
                cipher = PKCS1_v1_5.new(self._private_key)
                
                while input_len - offset > 0:
                    block_count += 1
                    if input_len - offset > self.MAX_DECRYPT_BLOCK:
                        block = encrypted_bytes[offset:offset + self.MAX_DECRYPT_BLOCK]
                    else:
                        block = encrypted_bytes[offset:input_len]
                    
                    logger.info(f"[RSA解密] 解密块 {block_count}: {len(block)} 字节")
                    
                    # 使用 None 作为 sentinel（与官方代码一致）
                    cache = cipher.decrypt(block, None)
                    if cache:
                        decrypted_data += cache
                        logger.info(f"[RSA解密] 块 {block_count} 解密成功: {len(cache)} 字节")
                    else:
                        logger.warning(f"[RSA解密] 块 {block_count} 解密返回 None")
                    offset += self.MAX_DECRYPT_BLOCK
            
            elif CRYPTO_LIB == 'cryptography':
                from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
                
                while input_len - offset > 0:
                    block_count += 1
                    if input_len - offset > self.MAX_DECRYPT_BLOCK:
                        block = encrypted_bytes[offset:offset + self.MAX_DECRYPT_BLOCK]
                    else:
                        block = encrypted_bytes[offset:input_len]
                    
                    logger.info(f"[RSA解密] 解密块 {block_count}: {len(block)} 字节")
                    
                    decrypted_block = self._private_key.decrypt(
                        block,
                        asym_padding.PKCS1v15()
                    )
                    decrypted_data += decrypted_block
                    logger.info(f"[RSA解密] 块 {block_count} 解密成功: {len(decrypted_block)} 字节")
                    offset += self.MAX_DECRYPT_BLOCK
            
            # URL decode
            decoded_data = decrypted_data.decode('utf-8')
            logger.info(f"[RSA解密] URL解码前: {decoded_data[:200]}...")
            
            plaintext = urllib.parse.unquote(decoded_data)
            logger.info(f"[RSA解密] 最终明文: {plaintext[:200]}...")
            
            return plaintext
            
        except Exception as e:
            logger.error(f"[RSA解密] 解密失败: {e}")
            import traceback
            logger.error(f"[RSA解密] 异常堆栈: {traceback.format_exc()}")
            raise


# 创建全局加密器实例
encryptor = HikvisionRSAEncryptor()


def get_encryptor() -> HikvisionRSAEncryptor:
    """获取全局加密器实例"""
    return encryptor


def reload_encryptor(private_key_pem: Optional[str] = None):
    """重新加载加密器（用于动态更新私钥）"""
    global encryptor
    encryptor = HikvisionRSAEncryptor(private_key_pem)
    return encryptor


# 便捷函数
def encrypt_get_params(params: Dict) -> str:
    """加密 GET 参数"""
    return encryptor.encrypt_get_params(params)


def encrypt_post_body(body: Union[Dict, str]) -> Dict:
    """加密 POST 请求体"""
    return encryptor.encrypt_post_body(body)


def decrypt_response(encrypted_data: str) -> str:
    """解密响应数据"""
    return encryptor.decrypt_response(encrypted_data)


if __name__ == "__main__":
    # 测试代码
    import sys
    
    # 示例私钥（测试用，请替换为真实私钥）
    test_key = """-----BEGIN RSA PRIVATE KEY-----
MIICXAIBAAKBgQC0PxeU4v6YKn8S2VtknGzZU5Lh7jHXgHkZ3JQ8d8w4y5Yl7z9c
q3X8y5Yl7z9cq3X8y5Yl7z9cq3X8y5Yl7z9cq3X8y5Yl7z9cq3X8y5Yl7z9cq3X8
y5Yl7z9cq3X8y5Yl7z9cq3X8y5Yl7z9cq3X8y5Yl7z9cq3X8yQIDAQABAoGAN6rK
-----END RSA PRIVATE KEY-----"""
    
    # 从环境变量读取
    private_key = os.getenv('HIK_PRIVATE_KEY', test_key)
    
    if not private_key or private_key == test_key:
        print("请设置 HIK_PRIVATE_KEY 环境变量")
        sys.exit(1)
    
    # 创建加密器
    enc = HikvisionRSAEncryptor(private_key)
    
    # 测试 GET 参数加密
    test_params = {
        "departNos": "BM0001",
        "containsDeletedPerson": True,
        "beginDate": "2024-08-01",
        "endDate": "2024-08-15"
    }
    
    encrypted = enc.encrypt_get_params(test_params)
    print(f"加密后的 querySecret: {encrypted[:100]}...")
    
    # 测试 POST 请求体加密
    test_body = {
        "holidayType": "测试请假类型",
        "holidayUnit": 1,
        "hourForDay": 8
    }
    
    encrypted_body = enc.encrypt_post_body(test_body)
    print(f"加密后的 bodySecret: {encrypted_body['bodySecret'][:100]}...")
