#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
林麝运动量检测系统 - 海康云 API 版本
基于海康互联开放平台 API

需要确认:
1. 设备列表 API 路径
2. 设备抓拍 API 路径
3. User-Access-Token 获取方式
"""

import hashlib
import json
import time
import logging
from datetime import datetime
from typing import Optional, Dict, List
from dataclasses import dataclass
from collections import deque
import requests

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ActivityMetrics:
    """运动量指标"""
    timestamp: str
    device_serial: str
    animal_count: int
    total_movement: float
    avg_speed: float
    activity_level: str
    bboxes: List[Dict]


class HikvisionCloudAPI:
    """海康互联云 API 客户端"""
    
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
            logger.info(f"✅ App Token 获取成功")
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
        """
        获取设备列表
        
        ⚠️ 需要确认正确的 API 路径
        候选路径:
        - GET /api/v1/device/camera/page
        - GET /device/camera/list
        - GET /v1/devices
        """
        # TODO: 确认正确的 API 路径
        possible_paths = [
            "/api/v1/device/camera/page",
            "/device/camera/list",
            "/v1/devices",
        ]
        
        for path in possible_paths:
            try:
                result = self._request("GET", path, params={"page": 1, "pageSize": 20})
                if result.get("code") == 0:
                    logger.info(f"✅ 设备列表 API 路径: {path}")
                    return result.get("data", {}).get("list", [])
            except Exception as e:
                logger.debug(f"{path} 失败: {e}")
        
        logger.error("无法获取设备列表，请确认 API 路径")
        return []
    
    def capture_device(self, device_serial: str, channel_no: int = 1) -> Optional[str]:
        """
        设备抓拍
        
        ⚠️ 需要确认正确的 API 路径
        候选路径:
        - POST /api/v1/device/camera/capture
        - POST /device/camera/snapshot
        - POST /v1/device/capture
        """
        # TODO: 确认正确的 API 路径
        possible_paths = [
            "/api/v1/device/camera/capture",
            "/device/camera/snapshot",
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
                    logger.info(f"✅ 抓拍 API 路径: {path}")
                    return result.get("data", {}).get("picUrl")
            except Exception as e:
                logger.debug(f"{path} 失败: {e}")
        
        logger.error("无法抓拍，请确认 API 路径")
        return None


class AnimalDetector:
    """动物检测器 (简化版)"""
    
    def __init__(self):
        self.prev_frame = None
        self.prev_bboxes = []
    
    def detect(self, image_url: str) -> List[Dict]:
        """
        检测动物
        
        简化实现: 返回模拟数据
        实际应该:
        1. 下载图片
        2. 使用 YOLO/OpenCV 检测
        3. 返回边界框坐标
        """
        # TODO: 实现 YOLO 检测
        logger.info(f"检测图片: {image_url[:50]}...")
        
        # 模拟返回
        return [
            {"x": 100, "y": 200, "width": 150, "height": 100, "confidence": 0.85}
        ]


class ActivityMonitor:
    """运动量监控器"""
    
    def __init__(self, api: HikvisionCloudAPI, detector: AnimalDetector):
        self.api = api
        self.detector = detector
        self.history: deque = deque(maxlen=1000)
        self.running = False
    
    def calculate_activity(self, current_bboxes: List[Dict], 
                          prev_bboxes: List[Dict],
                          time_delta: float) -> ActivityMetrics:
        """计算运动量"""
        timestamp = datetime.now().isoformat()
        
        if not current_bboxes:
            return ActivityMetrics(
                timestamp=timestamp,
                device_serial="",
                animal_count=0,
                total_movement=0,
                avg_speed=0,
                activity_level="idle",
                bboxes=[]
            )
        
        # 简单的移动距离计算
        total_movement = 0
        for curr, prev in zip(current_bboxes, prev_bboxes):
            cx1, cy1 = curr["x"] + curr["width"]/2, curr["y"] + curr["height"]/2
            cx2, cy2 = prev["x"] + prev["width"]/2, prev["y"] + prev["height"]/2
            distance = ((cx1-cx2)**2 + (cy1-cy2)**2)**0.5
            total_movement += distance
        
        avg_speed = total_movement / time_delta if time_delta > 0 else 0
        
        # 活动等级
        if avg_speed < 5:
            level = "idle"
        elif avg_speed < 20:
            level = "low"
        elif avg_speed < 50:
            level = "medium"
        else:
            level = "high"
        
        return ActivityMetrics(
            timestamp=timestamp,
            device_serial="",
            animal_count=len(current_bboxes),
            total_movement=total_movement,
            avg_speed=avg_speed,
            activity_level=level,
            bboxes=current_bboxes
        )
    
    def monitor_device(self, device_serial: str, interval: float = 1.0):
        """监控单个设备"""
        logger.info(f"开始监控设备: {device_serial}")
        
        self.running = True
        prev_bboxes = []
        prev_time = time.time()
        
        while self.running:
            try:
                # 1. 抓拍
                pic_url = self.api.capture_device(device_serial)
                
                if not pic_url:
                    logger.warning("抓拍失败，等待重试")
                    time.sleep(interval)
                    continue
                
                # 2. 检测动物
                current_bboxes = self.detector.detect(pic_url)
                
                # 3. 计算活动量
                current_time = time.time()
                time_delta = current_time - prev_time
                
                metrics = self.calculate_activity(current_bboxes, prev_bboxes, time_delta)
                metrics.device_serial = device_serial
                
                self.history.append(metrics)
                
                # 4. 输出结果
                logger.info(
                    f"[{device_serial}] 动物: {metrics.animal_count}, "
                    f"活动: {metrics.activity_level}, 速度: {metrics.avg_speed:.1f}px/s"
                )
                
                # 更新状态
                prev_bboxes = current_bboxes
                prev_time = current_time
                
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"监控异常: {e}")
                time.sleep(interval)
    
    def stop(self):
        """停止监控"""
        self.running = False


def main():
    """主程序"""
    print("="*60)
    print("林麝运动量检测系统")
    print("="*60)
    
    # 配置
    AK = "2023987187632369716"
    SK = "MIICdgIBADANBgkqhkiG9w0BAQEFAASCAmAwggJcAgEAAoGBAJLMIOuommDeg+8yY0sNzL8VeOBfLdZkiHjIUZK64Om+S1pVo6SLFT5hNLsip+5nSuvlXo+tgfyzaqbidsCZZQaCM48RViKfFZr7vhTmVDBBO1exrWpacu/wCmwstu9cf//UTM0KO3M/IhJ0qZ713vyMuc7EXUX0yqj/IpDI5S6nAgMBAAECgYB8gOTq+nT088Syeun8HhgpeOysYA1gaKPWzQ9ig11+4gbG9xtz0wKRhaBTl3EWokTJDiDFe0NkMEekgy5066TiNl483a4sU+t/4A1evajpTHsGN9aLDE7xT7rmCwNGCtZrUjlZAWzAIHzA1P7g/4V8DyfThDCVFlMxeKyzxJtmAQJBANJP8n7wGawsXyYOzh7dJxaouDRTHvyhfSbXJlqRcLqF4+msXdeyj1qSWCwYTI92EiT6yuNknSg2o/7SBoWoJGkCQQCyr/CY+tfci/+Au4O+cITeD/Uton9g8Nn1W7O9Uql0mZ7AKNtmF2ZpN+H+lX6fHxktXZWVMufYoBGfDUb6NxiPAkEAqM5oysB3Kr4WxRpfEWDbLhHQgJczKP2J0bIhY9KXU++B5x5l2GrHK6CJSyNZ2FCh8bKnROuORSfObAsyFvfF+QJAeiquHXmK8h/JXTNW/HIjdUuFvmCWJConaof62FrWvoB1OD322tLu0stBOPTusE3rwcd1CJ/YQZQW2B6Uw2e94wJAZtbsaaCeiCmfVPNFwBiTQKYemg/s8xL3Rqhbx4ofoWLnyj+sY+Dtw5sn6XV2eY4d2+jVufz8eoiJszISw8dH5w=="
    DEVICE_SERIAL = "GF5155888"
    
    try:
        # 初始化
        api = HikvisionCloudAPI(AK, SK)
        detector = AnimalDetector()
        monitor = ActivityMonitor(api, detector)
        
        # 获取设备列表
        devices = api.get_device_list()
        logger.info(f"找到 {len(devices)} 个设备")
        
        # 开始监控
        monitor.monitor_device(DEVICE_SERIAL, interval=1.0)
        
    except KeyboardInterrupt:
        logger.info("用户中断")
    except Exception as e:
        logger.error(f"错误: {e}")


if __name__ == "__main__":
    main()
