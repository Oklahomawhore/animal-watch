#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康互联开放平台 API 完整客户端
基于已测试确认的端点和认证流程

已知信息:
- Base URL: https://open-api.hikiot.com
- Token URL: /auth/exchangeAppToken (POST, JSON)
- 设备列表: 需要 User-Access-Token (待确认路径)
- 设备抓拍: 待确认路径
"""

import hashlib
import json
import time
import logging
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import requests
from pathlib import Path

# 禁用 SSL 警告
requests.packages.urllib3.disable_warnings()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)


class HikvisionCloudAPI:
    """
    海康互联开放平台 API 客户端
    
    使用方法:
        api = HikvisionCloudAPI(app_key, app_secret)
        
        # 获取设备列表 (需要正确的API路径和权限)
        devices = api.get_device_list()
        
        # 设备抓拍 (需要正确的API路径和权限)
        image_url = api.capture_device("GF5155888")
    """
    
    BASE_URL = "https://open-api.hikiot.com"
    
    def __init__(self, app_key: str, app_secret: str):
        self.app_key = app_key
        self.app_secret = app_secret
        self.app_token: Optional[str] = None
        self.user_token: Optional[str] = None
        self.token_expire_time: float = 0
        
        self.session = requests.Session()
        
        # 自动获取 token
        self._refresh_app_token()
    
    def _generate_sign(self, timestamp: str) -> str:
        """
        生成 API 签名
        算法: MD5(appKey + appSecret + timestamp)
        """
        sign_str = f"{self.app_key}{self.app_secret}{timestamp}"
        return hashlib.md5(sign_str.encode('utf-8')).hexdigest()
    
    def _refresh_app_token(self):
        """获取 App Access Token"""
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
        
        logger.info(f"获取 App Token...")
        
        resp = self.session.post(url, headers=headers, json=payload, timeout=30, verify=False)
        result = resp.json()
        
        if result.get("code") == 0:
            self.app_token = result["data"]["appAccessToken"]
            expire_in = result["data"].get("expiresIn", 7200)
            self.token_expire_time = time.time() + expire_in - 300  # 提前5分钟过期
            logger.info(f"✅ App Token 获取成功，有效期 {expire_in} 秒")
        else:
            raise Exception(f"Token 获取失败: {result.get('msg')}")
    
    def _ensure_token(self):
        """确保 token 有效"""
        if time.time() >= self.token_expire_time:
            logger.info("Token 即将过期，刷新中...")
            self._refresh_app_token()
    
    def _request(self, method: str, path: str, **kwargs) -> Dict:
        """发送 API 请求"""
        self._ensure_token()
        
        url = f"{self.BASE_URL}{path}"
        
        headers = kwargs.pop('headers', {})
        headers['Content-Type'] = 'application/json'
        headers['App-Access-Token'] = self.app_token
        
        # 如果有 user token，也加上
        if self.user_token:
            headers['User-Access-Token'] = self.user_token
        
        try:
            resp = self.session.request(method, url, headers=headers, **kwargs, timeout=30, verify=False)
            return resp.json()
        except Exception as e:
            logger.error(f"请求失败: {e}")
            raise
    
    # ==================== 设备管理 API ====================
    
    def get_device_list(self, page: int = 1, page_size: int = 20) -> List[Dict]:
        """
        获取设备列表
        
        ⚠️ 注意: 这个 API 需要开通设备管理权限，并且需要 User-Access-Token
        
        待确认的正确路径:
        - GET /device/camera/v1/page
        - GET /api/device/list
        - GET /v1/device/list
        """
        # 可能的 API 路径
        possible_paths = [
            "/device/camera/v1/page",
            "/api/device/list",
            "/v1/device/list",
            "/device/list",
        ]
        
        params = {"page": page, "pageSize": page_size}
        
        for path in possible_paths:
            logger.info(f"尝试设备列表 API: {path}")
            
            try:
                result = self._request("GET", path, params=params)
                
                if result.get("code") == 0:
                    logger.info(f"✅ 成功! API路径: {path}")
                    return result.get("data", {}).get("list", [])
                    
                elif result.get("code") == 400018:
                    logger.warning(f"需要 User-Access-Token")
                    # 尝试使用 app token 作为 user token
                    self.user_token = self.app_token
                    result = self._request("GET", path, params=params)
                    
                    if result.get("code") == 0:
                        return result.get("data", {}).get("list", [])
                        
            except Exception as e:
                logger.debug(f"{path} 失败: {e}")
        
        logger.error("所有设备列表 API 路径都失败了")
        return []
    
    def capture_device(self, device_serial: str, channel_no: int = 1) -> Optional[str]:
        """
        设备抓拍
        
        ⚠️ 注意: 这个 API 需要开通设备控制权限
        
        待确认的正确路径:
        - POST /device/camera/v1/capture
        - POST /api/device/capture
        - POST /v1/device/capture
        
        Returns:
            图片 URL 或 None
        """
        # 可能的 API 路径
        possible_paths = [
            "/device/camera/v1/capture",
            "/device/camera/v1/snapshot",
            "/api/device/capture",
            "/v1/device/capture",
            "/device/capture",
            "/device/snapshot",
        ]
        
        payload = {
            "deviceSerial": device_serial,
            "channelNo": channel_no,
        }
        
        for path in possible_paths:
            logger.info(f"尝试抓拍 API: {path}")
            
            try:
                result = self._request("POST", path, json=payload)
                
                if result.get("code") == 0:
                    logger.info(f"✅ 抓拍成功! API路径: {path}")
                    return result.get("data", {}).get("picUrl")
                    
            except Exception as e:
                logger.debug(f"{path} 失败: {e}")
        
        logger.error("所有抓拍 API 路径都失败了")
        return None
    
    def get_preview_url(self, device_serial: str, channel_no: int = 1, protocol: str = "hls") -> Optional[str]:
        """
        获取实时预览地址
        
        待确认的正确路径:
        - POST /device/camera/v1/preview
        - POST /api/device/preview
        """
        possible_paths = [
            "/device/camera/v1/preview",
            "/api/device/preview",
            "/v1/device/preview",
        ]
        
        payload = {
            "deviceSerial": device_serial,
            "channelNo": channel_no,
            "protocol": protocol,  # hls, webrtc, flv
        }
        
        for path in possible_paths:
            try:
                result = self._request("POST", path, json=payload)
                
                if result.get("code") == 0:
                    logger.info(f"✅ 预览地址获取成功! API路径: {path}")
                    return result.get("data", {}).get("url")
                    
            except Exception as e:
                logger.debug(f"{path} 失败: {e}")
        
        return None
    
    def download_image(self, image_url: str, save_path: str) -> bool:
        """下载图片"""
        try:
            resp = self.session.get(image_url, timeout=30, verify=False)
            resp.raise_for_status()
            
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                f.write(resp.content)
            
            logger.info(f"✅ 图片已保存: {save_path} ({len(resp.content)} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"下载失败: {e}")
            return False


# ==================== 使用示例 ====================

def main():
    """使用示例"""
    print("="*60)
    print("海康互联开放平台 API 使用示例")
    print("="*60)
    
    # 配置
    AK = "2023987187632369716"
    SK = "MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBAJLMIOuommDeg+8yY0sNzL8VeOBfLdZkiHjIUZK64Om+S1pVo6SLFT5hNLsip+5nSuvlXo+tgfyzaqbidsCZZQaCM48RViKfFZr7vhTmVDBBO1exrWpacu/wCmwstu9cf//UTM0KO3M/IhJ0qZ713vyMuc7EXUX0yqj/IpDI5S6nAgMBAAECgYB8gOTq+nT088Syeun8HhgpeOysYA1gaKPWzQ9ig11+4gbG9xtz0wKRhaBTl3EWokTJDiDFe0NkMEekgy5066TiNl483a4sU+t/4A1evajpTHsGN9aLDE7xT7rmCwNGCtZrUjlZAWzAIHzA1P7g/4V8DyfThDCVFlMxeKyzxJtmAQJBANJP8n7wGawsXyYOzh7dJxaouDRTHvyhfSbXJlqRcLqF4+msXdeyj1qSWCwYTI92EiT6yuNknSg2o/7SBoWoJGkCQQCyr/CY+tfci/+Au4O+cITeD/Uton9g8Nn1W7O9Uql0mZ7AKNtmF2ZpN+H+lX6fHxktXZWVMufYoBGfDUb6NxiPAkEAqM5oysB3Kr4WxRpfEWDbLhHQgJczKP2J0bIhY9KXU++B5x5l2GrHK6CJSyNZ2FCh8bKnROuORSfObAsyFvfF+QJAeiquHXmK8h/JXTNW/HIjdUuFvmCWJConaof62FrWvoB1OD322tLu0stBOPTusE3rwcd1CJ/YQZQW2B6Uw2e94wJAZtbsaaCeiCmfVPNFwBiTQKYemg/s8xL3Rqhbx4ofoWLnyj+sY+Dtw5sn6XV2eY4d2+jVufz8eoiJszISw8dH5w=="
    
    DEVICE_SERIAL = "GF5155888"
    
    try:
        # 初始化 API 客户端
        api = HikvisionCloudAPI(AK, SK)
        print(f"\n✅ API 客户端初始化成功")
        print(f"App Token: {api.app_token[:40]}...")
        
        # 尝试获取设备列表
        print("\n" + "="*60)
        print("获取设备列表...")
        print("="*60)
        
        devices = api.get_device_list()
        
        if devices:
            print(f"\n✅ 找到 {len(devices)} 个设备")
            for i, dev in enumerate(devices[:5], 1):
                print(f"  [{i}] {dev}")
        else:
            print("\n⚠️ 未找到设备或 API 路径不正确")
        
        # 尝试设备抓拍
        print("\n" + "="*60)
        print(f"设备抓拍: {DEVICE_SERIAL}")
        print("="*60)
        
        pic_url = api.capture_device(DEVICE_SERIAL)
        
        if pic_url:
            print(f"\n✅ 抓拍成功!")
            print(f"图片 URL: {pic_url}")
            
            # 下载图片
            api.download_image(pic_url, "capture.jpg")
        else:
            print("\n⚠️ 抓拍失败，API 路径可能不正确")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
