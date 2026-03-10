#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康云 API 服务 (v2 - 支持 RSA 加密)
"""

import hashlib
import json
import time
import logging
from typing import Optional, Dict, List
import requests

from services.rsa_encryptor import encryptor

requests.packages.urllib3.disable_warnings()

logger = logging.getLogger(__name__)


class HikvisionCloudAPI:
    """海康互联开放平台 API 客户端 (支持 RSA 加密)"""
    
    BASE_URL = "https://open-api.hikiot.com"
    
    def __init__(self, app_key: str, app_secret: str, public_key: Optional[str] = None):
        """
        初始化 API 客户端
        
        Args:
            app_key: 应用 Key
            app_secret: 应用 Secret
            public_key: RSA 公钥（用于加密请求，从环境变量 HIK_PUBLIC_KEY 读取或传入）
        """
        self.app_key = app_key
        self.app_secret = app_secret
        self.app_token: Optional[str] = None
        self.user_token: Optional[str] = None
        
        # 初始化 RSA 加密器（使用公钥！）
        # 从环境变量 HIK_PUBLIC_KEY 或传入参数获取
        from services.rsa_encryptor import HikvisionRSAEncryptor
        self._encryptor = HikvisionRSAEncryptor(public_key)
        
        self._refresh_app_token()
    
    def _generate_sign(self, timestamp: str) -> str:
        """生成签名: MD5(appKey + appSecret + timestamp)"""
        sign_str = f"{self.app_key}{self.app_secret}{timestamp}"
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest()
    
    def _refresh_app_token(self):
        """获取 App Token"""
        url = f"{self.BASE_URL}/auth/exchangeAppToken"
        timestamp = str(int(time.time() * 1000))
        
        payload = {
            "appKey": self.app_key,
            "appSecret": self.app_secret,
            "timestamp": timestamp,
            "signature": self._generate_sign(timestamp),
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
        result = resp.json()
        
        if result.get("code") == 0:
            self.app_token = result["data"]["appAccessToken"]
            logger.info("App Token 获取成功")
        else:
            raise Exception(f"Token 获取失败: {result.get('msg')}")
    
    def _request(self, method: str, path: str, **kwargs) -> Dict:
        """
        发送 API 请求（支持 RSA 加密）
        
        根据海康文档，除以下接口外，所有请求都需要 RSA 加密：
        - /auth/exchangeAppToken (获取应用访问凭证)
        - /auth/refreshAppToken (刷新应用访问凭证)
        - /auth/third/applyAuthCode (申请授权码)
        """
        url = f"{self.BASE_URL}{path}"
        
        # 判断是否需要加密（这些接口不需要）
        # 根据海康文档，以下接口不需要 RSA 加密
        no_encrypt_paths = [
            '/auth/exchangeAppToken',
            '/auth/refreshAppToken',
            '/auth/third/applyAuthCode'
            # 注意：/auth/third/code2Token 需要加密
        ]
        need_encrypt = path not in no_encrypt_paths and self._encryptor._public_key is not None
        
        headers = kwargs.pop('headers', {})
        headers['Accept'] = 'application/json'
        
        # 设置认证 Token
        if self.app_token:
            headers['App-Access-Token'] = self.app_token
        if self.user_token:
            headers['User-Access-Token'] = self.user_token
        
        # 处理请求参数加密
        if method.upper() == 'GET' and need_encrypt:
            params = kwargs.get('params', {})
            if params:
                # 加密参数
                encrypted_params = self._encryptor.encrypt_get_params(params)
                # 替换为 querySecret
                kwargs['params'] = {'querySecret': encrypted_params}
                logger.debug(f"GET 参数已加密: {path}")
        
        elif method.upper() in ['POST', 'PUT', 'PATCH'] and need_encrypt:
            json_data = kwargs.get('json')
            if json_data:
                # 加密请求体
                encrypted_body = self._encryptor.encrypt_post_body(json_data)
                kwargs['json'] = encrypted_body
                logger.debug(f"POST 请求体已加密: {path}")
        
        # 发送请求
        logger.info(f"[API请求] {method} {url}")
        logger.info(f"[API请求] Headers: {headers}")
        logger.info(f"[API请求] 需要加密: {need_encrypt}")
        if 'params' in kwargs:
            logger.info(f"[API请求] Params: {kwargs['params']}")
        if 'json' in kwargs:
            logger.info(f"[API请求] Body: {kwargs['json']}")
        
        resp = requests.request(method, url, headers=headers, **kwargs, timeout=30, verify=False)
        result = resp.json()
        
        logger.info(f"[API响应] Status: {resp.status_code}")
        logger.info(f"[API响应] Result: {json.dumps(result, ensure_ascii=False)[:500]}...")
        
        # 处理响应解密
        if result.get("code") == 0 and 'data' in result and need_encrypt:
            encrypted_data = result['data']
            logger.info(f"[API响应] 需要解密的数据: {str(encrypted_data)[:200]}...")
            if encrypted_data and isinstance(encrypted_data, str):
                try:
                    # 解密响应数据
                    decrypted = self._encryptor.decrypt_response(encrypted_data)
                    result['data'] = json.loads(decrypted)
                    logger.info(f"[API响应] 解密成功: {path}")
                except Exception as e:
                    logger.error(f"[API响应] 解密失败: {e}，返回原始数据")
        
        return result
    
    def get_device_list(self, page: int = 1, page_size: int = 20) -> List[Dict]:
        """
        获取设备列表
        https://open.hikiot.com/documents/detail/11?docId=1823648500886351894
        """
        params = {
            "page": page,
            "pageSize": page_size
        }
        
        result = self._request("GET", "/device/camera/v1/page", params=params)
        
        if result.get("code") == 0:
            return result.get("data", {}).get("list", [])
        else:
            logger.error(f"获取设备列表失败: {result.get('msg')}")
            return []
    
    def capture_device(self, device_serial: str, channel_no: int = 1) -> Optional[str]:
        """
        设备抓拍
        https://open.hikiot.com/documents/detail/11?docId=1823648500886351894
        """
        payload = {
            "deviceSerial": device_serial,
            "channelNo": channel_no,
        }
        
        result = self._request("POST", "/device/camera/v1/capture", json=payload)
        
        if result.get("code") == 0:
            return result.get("data", {}).get("picUrl")
        else:
            logger.error(f"设备抓拍失败: {result.get('msg')}")
            return None
    
    def get_device_info(self, device_serial: str) -> Optional[Dict]:
        """
        获取设备信息
        """
        params = {
            "deviceSerial": device_serial
        }
        
        result = self._request("GET", "/device/camera/v1/info", params=params)
        
        if result.get("code") == 0:
            return result.get("data")
        else:
            logger.error(f"获取设备信息失败: {result.get('msg')}")
            return None
    
    def get_device_status(self, device_serial: str) -> Optional[str]:
        """
        获取设备在线状态
        """
        params = {
            "deviceSerial": device_serial
        }
        
        result = self._request("GET", "/device/camera/v1/status", params=params)
        
        if result.get("code") == 0:
            return result.get("data", {}).get("status")
        else:
            logger.error(f"获取设备状态失败: {result.get('msg')}")
            return None
    
    # ========== 用户认证相关 API ==========
    
    def apply_auth_code(self, user_name: str, password: str, redirect_url: str, state: str = '') -> Dict:
        """
        申请授权码
        https://open.hikiot.com/documents/detail/11?docId=1825505782565777436
        
        注意：此接口不需要 RSA 加密
        """
        url = f"{self.BASE_URL}/auth/third/applyAuthCode"
        
        payload = {
            "appKey": self.app_key,
            "userName": user_name,
            "password": password,
            "redirectUrl": redirect_url
        }
        
        if state:
            payload["state"] = state
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
        result = resp.json()
        
        if result.get("code") == 0:
            logger.info(f"授权码申请成功: {result['data'].get('authCode')}")
        else:
            logger.warning(f"授权码申请失败: {result.get('msg')}")
        
        return result
    
    def code2token(self, auth_code: str) -> Dict:
        """
        授权码换取 User Access Token
        https://open.hikiot.com/documents/detail/11?docId=1825505782565777436
        """
        logger.info(f"[code2token] 开始换取 Token, authCode: {auth_code[:20]}...")
        
        params = {
            "authCode": auth_code
        }
        
        result = self._request("GET", "/auth/third/code2Token", params=params)
        
        if result.get("code") == 0:
            logger.info("[code2token] User Access Token 获取成功")
            self.user_token = result["data"]["userAccessToken"]
        else:
            logger.error(f"[code2token] User Access Token 获取失败: {result.get('msg')}")
            logger.error(f"[code2token] 完整响应: {json.dumps(result, ensure_ascii=False)}")
        
        return result
    
    def refresh_user_token(self, user_access_token: str, refresh_user_token: str) -> Dict:
        """
        刷新 User Access Token
        https://open.hikiot.com/documents/detail/11?docId=1825505782565777436
        """
        payload = {
            "userAccessToken": user_access_token,
            "refreshUserToken": refresh_user_token
        }
        
        result = self._request("POST", "/auth/third/refreshUserAccessToken", json=payload)
        
        if result.get("code") == 0:
            logger.info("User Access Token 刷新成功")
            self.user_token = result["data"]["userAccessToken"]
        else:
            logger.warning(f"User Access Token 刷新失败: {result.get('msg')}")
        
        return result
    
    def set_user_token(self, user_token: str):
        """设置 User Access Token"""
        self.user_token = user_token


# 兼容旧版本 API 类
class HikvisionCloudAPIV1:
    """兼容旧版本的 API 客户端（不加密）"""
    
    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.app_token: Optional[str] = None
        self.user_token: Optional[str] = None
        
        self._refresh_app_token()
    
    def _generate_sign(self, timestamp: str) -> str:
        sign_str = f"{self.app_key}{self.app_secret}{timestamp}"
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest()
    
    def _refresh_app_token(self):
        url = f"https://open-api.hikiot.com/auth/exchangeAppToken"
        timestamp = str(int(time.time() * 1000))
        
        payload = {
            "appKey": self.app_key,
            "appSecret": self.app_secret,
            "timestamp": timestamp,
            "signature": self._generate_sign(timestamp),
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
        result = resp.json()
        
        if result.get("code") == 0:
            self.app_token = result["data"]["appAccessToken"]
            logger.info("App Token 获取成功")
        else:
            raise Exception(f"Token 获取失败: {result.get('msg')}")
    
    def _request(self, method: str, path: str, **kwargs) -> Dict:
        url = f"https://open-api.hikiot.com{path}"
        
        headers = kwargs.pop('headers', {})
        headers['Content-Type'] = 'application/json'
        headers['App-Access-Token'] = self.app_token
        
        if self.user_token:
            headers['User-Access-Token'] = self.user_token
        
        resp = requests.request(method, url, headers=headers, **kwargs, timeout=30, verify=False)
        return resp.json()
    
    def get_device_list(self) -> List[Dict]:
        possible_paths = [
            "/device/camera/v1/page",
            "/api/v1/device/camera/page",
            "/v1/devices",
        ]
        
        for path in possible_paths:
            try:
                result = self._request("GET", path, params={"page": 1, "pageSize": 20})
                if result.get("code") == 0:
                    logger.info(f"设备列表 API 路径: {path}")
                    return result.get("data", {}).get("list", [])
            except Exception as e:
                logger.debug(f"{path} 失败: {e}")
        
        return []
    
    def capture_device(self, device_serial: str, channel_no: int = 1) -> Optional[str]:
        possible_paths = [
            "/device/camera/v1/capture",
            "/api/v1/device/camera/capture",
            "/v1/device/capture",
        ]
        
        payload = {
            "deviceSerial": device_serial,
            "channelNo": channel_no,
        }
        
        for path in possible_paths:
            try:
                result = self._request("POST", path, json=payload)
                if result.get("code") == 0:
                    logger.info(f"抓拍 API 路径: {path}")
                    return result.get("data", {}).get("picUrl")
            except Exception as e:
                logger.debug(f"{path} 失败: {e}")
        
        return None
    
    def apply_auth_code(self, user_name: str, password: str, redirect_url: str, state: str = '') -> Dict:
        url = f"https://open-api.hikiot.com/auth/third/applyAuthCode"
        
        payload = {
            "appKey": self.app_key,
            "userName": user_name,
            "password": password,
            "redirectUrl": redirect_url
        }
        
        if state:
            payload["state"] = state
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
        result = resp.json()
        
        if result.get("code") == 0:
            logger.info(f"授权码申请成功: {result['data'].get('authCode')}")
        else:
            logger.warning(f"授权码申请失败: {result.get('msg')}")
        
        return result
    
    def code2token(self, auth_code: str) -> Dict:
        url = f"https://open-api.hikiot.com/auth/third/code2Token"
        
        params = {"authCode": auth_code}
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "App-Access-Token": self.app_token
        }
        
        resp = requests.get(url, headers=headers, params=params, timeout=30, verify=False)
        result = resp.json()
        
        if result.get("code") == 0:
            logger.info("User Access Token 获取成功")
            self.user_token = result["data"]["userAccessToken"]
        else:
            logger.warning(f"User Access Token 获取失败: {result.get('msg')}")
        
        return result
    
    def refresh_user_token(self, user_access_token: str, refresh_user_token: str) -> Dict:
        url = f"https://open-api.hikiot.com/auth/third/refreshUserAccessToken"
        
        payload = {
            "userAccessToken": user_access_token,
            "refreshUserToken": refresh_user_token
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "App-Access-Token": self.app_token
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
        result = resp.json()
        
        if result.get("code") == 0:
            logger.info("User Access Token 刷新成功")
            self.user_token = result["data"]["userAccessToken"]
        else:
            logger.warning(f"User Access Token 刷新失败: {result.get('msg')}")
        
        return result
    
    def set_user_token(self, user_token: str):
        self.user_token = user_token
