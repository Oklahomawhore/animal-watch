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
