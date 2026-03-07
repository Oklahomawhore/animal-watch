#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康云 API 服务
"""

import hashlib
import json
import time
import logging
from typing import Optional, Dict, List
import requests

requests.packages.urllib3.disable_warnings()

logger = logging.getLogger(__name__)


class HikvisionCloudAPI:
    """海康互联开放平台 API 客户端"""
    
    BASE_URL = "https://open-api.hikiot.com"
    
    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.app_token: Optional[str] = None
        self.user_token: Optional[str] = None
        
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
        """发送 API 请求"""
        url = f"{self.BASE_URL}{path}"
        
        headers = kwargs.pop('headers', {})
        headers['Content-Type'] = 'application/json'
        headers['App-Access-Token'] = self.app_token
        
        if self.user_token:
            headers['User-Access-Token'] = self.user_token
        
        resp = requests.request(method, url, headers=headers, **kwargs, timeout=30, verify=False)
        return resp.json()
    
    def get_device_list(self) -> List[Dict]:
        """获取设备列表"""
        # 待确认正确的 API 路径
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
        """设备抓拍"""
        # 待确认正确的 API 路径
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
    
    # ========== 用户认证相关 API ==========
    
    def apply_auth_code(self, user_name: str, password: str, redirect_url: str, state: str = '') -> Dict:
        """
        申请授权码
        https://open-api.hikiot.com/auth/third/applyAuthCode
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
        https://open-api.hikiot.com/auth/third/code2Token
        """
        url = f"{self.BASE_URL}/auth/third/code2Token"
        
        params = {
            "authCode": auth_code
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "App-Access-Token": self.app_token
        }
        
        resp = requests.get(url, headers=headers, params=params, timeout=30, verify=False)
        result = resp.json()
        
        if result.get("code") == 0:
            logger.info("User Access Token 获取成功")
            # 存储 user_token 供后续 API 调用使用
            self.user_token = result["data"]["userAccessToken"]
        else:
            logger.warning(f"User Access Token 获取失败: {result.get('msg')}")
        
        return result
    
    def refresh_user_token(self, user_access_token: str, refresh_user_token: str) -> Dict:
        """
        刷新 User Access Token
        https://open-api.hikiot.com/auth/third/refreshUserAccessToken
        """
        url = f"{self.BASE_URL}/auth/third/refreshUserAccessToken"
        
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
            # 更新 user_token
            self.user_token = result["data"]["userAccessToken"]
        else:
            logger.warning(f"User Access Token 刷新失败: {result.get('msg')}")
        
        return result
    
    def set_user_token(self, user_token: str):
        """设置 User Access Token"""
        self.user_token = user_token
