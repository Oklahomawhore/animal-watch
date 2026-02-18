#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
海康互联云 API 客户端 + 食量监控集成
==================================

功能:
1. 海康云 API 认证与调用
2. 自动获取设备截图
3. 集成食量分析

依赖:
  pip install requests opencv-python numpy

使用方法:
  python hikcloud_grass_monitor.py --demo
  python hikcloud_grass_monitor.py --device-id XXX --ak XXX --sk XXX
"""

import os
import sys
import json
import time
import hmac
import hashlib
import base64
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlencode

import requests
import cv2
import numpy as np

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HikvisionCloudClient:
    """海康互联云 API 客户端"""
    
    BASE_URL = "https://openapi.hikiot.com"
    
    def __init__(self, ak: str, sk: str):
        """
        初始化客户端
        
        Args:
            ak: Access Key
            sk: Secret Key (Base64 编码的 RSA 私钥)
        """
        self.ak = ak
        self.sk = sk
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
    
    def _sign(self, method: str, uri: str, params: dict = None, body: str = None) -> dict:
        """
        生成 API 签名
        
        签名算法:
        1. 构建签名字符串: METHOD + "\n" + URI + "\n" + TIMESTAMP + ["\n" + BODY]
        2. 使用 SK 进行 HMAC-SHA256 签名
        3. Base64 编码签名结果
        """
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # 构建签名字符串
        parts = [method.upper(), uri, timestamp]
        if params:
            query = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
            parts.append(query)
        if body:
            parts.append(body)
        
        string_to_sign = "\n".join(parts)
        
        try:
            # HMAC-SHA256 签名
            # SK 是 Base64 编码的，需要先解码
            sk_bytes = base64.b64decode(self.sk)
            signature = hmac.new(
                sk_bytes,
                string_to_sign.encode('utf-8'),
                hashlib.sha256
            ).digest()
            signature_b64 = base64.b64encode(signature).decode('utf-8')
        except Exception as e:
            logger.error(f"签名生成失败: {e}")
            raise
        
        return {
            'Content-Type': 'application/json',
            'X-Ca-Key': self.ak,
            'X-Ca-Signature': signature_b64,
            'X-Ca-Timestamp': timestamp,
        }
    
    def _request(self, method: str, path: str, **kwargs) -> dict:
        """发送 HTTP 请求"""
        url = f"{self.BASE_URL}{path}"
        
        # 准备参数
        params = kwargs.get('params')
        data = kwargs.get('json')
        body = json.dumps(data) if data else None
        
        # 生成签名
        headers = self._sign(method, path, params, body)
        
        # 发送请求
        try:
            resp = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=data,
                timeout=30
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"请求失败: {e}")
            raise
    
    # ============ 设备管理 API ============
    
    def get_device_list(self, page: int = 1, page_size: int = 20) -> dict:
        """获取设备列表"""
        return self._request('GET', '/v1/devices', params={
            'page': page,
            'pageSize': page_size
        })
    
    def get_device_info(self, device_id: str) -> dict:
        """获取设备详情"""
        return self._request('GET', f'/v1/devices/{device_id}')
    
    def get_device_status(self, device_id: str) -> dict:
        """获取设备状态"""
        return self._request('GET', f'/v1/devices/{device_id}/status')
    
    # ============ 视频相关 API ============
    
    def get_snapshot(self, device_id: str, channel_no: int = 1) -> bytes:
        """
        获取设备实时截图
        
        Returns:
            JPEG 图像字节
        """
        path = f'/v1/devices/{device_id}/snapshot'
        params = {'channelNo': channel_no}
        
        headers = self._sign('GET', path, params)
        url = f"{self.BASE_URL}{path}?{urlencode(params)}"
        
        resp = self.session.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        return resp.content
    
    def get_preview_url(self, device_id: str, channel_no: int = 1,
                       protocol: str = 'hls', stream_type: int = 0) -> dict:
        """
        获取实时预览地址
        
        Args:
            protocol: hls, webrtc, flv
            stream_type: 0=主码流, 1=子码流
        """
        return self._request('POST', f'/v1/devices/{device_id}/preview', json={
            'channelNo': channel_no,
            'protocol': protocol,
            'streamType': stream_type
        })
    
    def capture(self, device_id: str, channel_no: int = 1, 
                save_path: Optional[str] = None) -> np.ndarray:
        """
        截图并转换为 OpenCV 图像
        
        Args:
            save_path: 可选，保存路径
        
        Returns:
            OpenCV 图像 (BGR格式)
        """
        image_bytes = self.get_snapshot(device_id, channel_no)
        
        # 转换为 numpy 数组
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise ValueError("截图解码失败")
        
        if save_path:
            cv2.imwrite(save_path, image)
            logger.info(f"截图已保存: {save_path}")
        
        return image
    
    # ============ PTZ 控制 API ============
    
    def ptz_control(self, device_id: str, command: str, channel_no: int = 1,
                   speed: int = 50, duration: int = 500) -> dict:
        """
        云台控制
        
        Args:
            command: UP, DOWN, LEFT, RIGHT, ZOOM_IN, ZOOM_OUT
            speed: 1-100
            duration: 持续时间(毫秒)
        """
        return self._request('POST', f'/v1/devices/{device_id}/ptz', json={
            'channelNo': channel_no,
            'command': command,
            'speed': speed,
            'duration': duration
        })


class CloudGrassMonitor:
    """云端食量监控系统"""
    
    def __init__(self, ak: str, sk: str, config_file: str = "cloud_troughs.json"):
        self.client = HikvisionCloudClient(ak, sk)
        self.config_file = config_file
        self.configs = self._load_configs()
    
    def _load_configs(self) -> dict:
        """加载食槽配置"""
        if not Path(self.config_file).exists():
            logger.warning(f"配置文件不存在: {self.config_file}")
            return {}
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def analyze_trough(self, trough_id: str) -> dict:
        """分析指定食槽"""
        if trough_id not in self.configs:
            raise ValueError(f"未知食槽: {trough_id}")
        
        cfg = self.configs[trough_id]
        device_id = cfg['device_id']
        channel_no = cfg.get('channel_no', 1)
        roi = cfg.get('roi', [0, 0, 640, 480])
        
        # 获取实时截图
        logger.info(f"[{trough_id}] 正在获取截图...")
        image = self.client.capture(device_id, channel_no)
        
        # 分析草量
        result = self._analyze_image(image, roi, cfg)
        result['trough_id'] = trough_id
        result['device_id'] = device_id
        result['timestamp'] = datetime.now().isoformat()
        
        return result
    
    def _analyze_image(self, image: np.ndarray, roi: list, cfg: dict) -> dict:
        """分析图像草量"""
        x, y, w, h = roi
        roi_img = image[y:y+h, x:x+w]
        
        # 转换到 HSV
        hsv = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
        
        # 绿色掩码
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 255])
        mask = cv2.inRange(hsv, lower_green, upper_green)
        
        # 计算绿色占比
        green_ratio = np.sum(mask > 0) / mask.size
        
        # 计算覆盖率 (基于基准图)
        empty_ratio = cfg.get('empty_green_ratio', 0.05)
        full_ratio = cfg.get('full_green_ratio', 0.60)
        
        if full_ratio > empty_ratio:
            coverage = (green_ratio - empty_ratio) / (full_ratio - empty_ratio) * 100
        else:
            coverage = 50.0
        
        coverage = max(0, min(100, coverage))
        
        # 状态判断
        if coverage < 10:
            status = "empty"
        elif coverage < 30:
            status = "low"
        elif coverage < 60:
            status = "medium"
        elif coverage < 90:
            status = "high"
        else:
            status = "full"
        
        return {
            'coverage_ratio': round(coverage, 2),
            'green_ratio': round(green_ratio * 100, 2),
            'status': status,
            'roi': roi
        }
    
    def calibrate(self, trough_id: str, state: str):
        """
        校准基准图
        
        Args:
            state: 'empty' 或 'full'
        """
        if trough_id not in self.configs:
            raise ValueError(f"未知食槽: {trough_id}")
        
        cfg = self.configs[trough_id]
        device_id = cfg['device_id']
        channel_no = cfg.get('channel_no', 1)
        roi = cfg.get('roi', [0, 0, 640, 480])
        
        # 获取截图
        image = self.client.capture(device_id, channel_no)
        
        # 计算绿色占比
        x, y, w, h = roi
        roi_img = image[y:y+h, x:x+w]
        hsv = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([35, 40, 40]), np.array([85, 255, 255]))
        green_ratio = np.sum(mask > 0) / mask.size
        
        # 更新配置
        key = f"{state}_green_ratio"
        self.configs[trough_id][key] = green_ratio
        
        # 保存截图
        save_dir = Path("calibration")
        save_dir.mkdir(exist_ok=True)
        save_path = save_dir / f"{trough_id}_{state}_{datetime.now():%Y%m%d_%H%M%S}.jpg"
        cv2.imwrite(str(save_path), image)
        
        # 保存配置
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.configs, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[{trough_id}] {state} 校准完成: 绿色占比={green_ratio:.2%}, 图片保存: {save_path}")
        return green_ratio


def create_sample_config():
    """创建示例配置文件"""
    config = {
        "trough_A01": {
            "device_id": "D123456789",
            "channel_no": 1,
            "name": "A01号食槽",
            "roi": [200, 150, 400, 300],
            "empty_green_ratio": 0.05,
            "full_green_ratio": 0.60
        }
    }
    
    with open("cloud_troughs.json", 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print("示例配置已创建: cloud_troughs.json")
    print(json.dumps(config, indent=2, ensure_ascii=False))


def demo_mode():
    """演示模式 - 使用模拟数据"""
    print("="*60)
    print("海康云食量监控系统 - 演示模式")
    print("="*60)
    print("\n注意: 演示模式使用本地模拟数据，不涉及真实 API 调用")
    print("      如需测试真实设备，请提供 AK/SK 和设备ID\n")
    
    # 创建演示目录
    Path("demo_cloud").mkdir(exist_ok=True)
    
    # 模拟截图和分析流程
    from grass_monitor import generate_mock_trough_image, GrassCoverageAnalyzer, TroughConfig
    
    # 生成基准图
    empty_img = generate_mock_trough_image("empty", (640, 480))
    full_img = generate_mock_trough_image("full", (640, 480))
    
    cv2.imwrite("demo_cloud/empty.jpg", empty_img)
    cv2.imwrite("demo_cloud/full.jpg", full_img)
    
    # 创建配置
    config = TroughConfig(
        trough_id="demo_trough",
        name="演示食槽",
        roi=(100, 100, 400, 300),
        empty_baseline="demo_cloud/empty.jpg",
        full_baseline="demo_cloud/full.jpg"
    )
    
    analyzer = GrassCoverageAnalyzer(config)
    
    # 模拟多次检测
    print("\n模拟进食过程:")
    for coverage in [100, 80, 60, 40, 20, 5]:
        img = generate_mock_trough_image("eating", (640, 480), coverage)
        img_path = f"demo_cloud/current_{coverage}.jpg"
        cv2.imwrite(img_path, img)
        
        result = analyzer.analyze(img_path)
        print(f"  真实覆盖率: {coverage:3d}% | 检测结果: {result.coverage_ratio:5.1f}% | 状态: {result.status}")
    
    print("\n演示完成! 查看 demo_cloud/ 目录")


def main():
    parser = argparse.ArgumentParser(description='海康云食量监控系统')
    parser.add_argument('--ak', help='Access Key')
    parser.add_argument('--sk', help='Secret Key')
    parser.add_argument('--device-id', help='设备ID')
    parser.add_argument('--demo', action='store_true', help='运行演示模式')
    parser.add_argument('--list-devices', action='store_true', help='列出设备')
    parser.add_argument('--capture', action='store_true', help='截图并分析')
    parser.add_argument('--calibrate', choices=['empty', 'full'], help='校准基准图')
    parser.add_argument('--trough-id', default='trough_A01', help='食槽ID')
    
    args = parser.parse_args()
    
    if args.demo:
        demo_mode()
        return
    
    if not args.ak or not args.sk:
        print("错误: 请提供 AK 和 SK")
        print("示例: python hikcloud_grass_monitor.py --ak XXX --sk XXX --list-devices")
        return
    
    client = HikvisionCloudClient(args.ak, args.sk)
    
    if args.list_devices:
        print("获取设备列表...")
        devices = client.get_device_list()
        print(json.dumps(devices, indent=2, ensure_ascii=False))
    
    elif args.capture and args.device_id:
        print(f"获取设备 {args.device_id} 截图...")
        image = client.capture(args.device_id, save_path="capture.jpg")
        print(f"截图成功: {image.shape}")
    
    elif args.calibrate and args.device_id:
        # 校准模式
        create_sample_config()
        monitor = CloudGrassMonitor(args.ak, args.sk)
        ratio = monitor.calibrate(args.trough_id, args.calibrate)
        print(f"校准完成: {args.calibrate} = {ratio:.2%}")


if __name__ == "__main__":
    main()
