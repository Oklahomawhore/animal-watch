#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量抓拍所有摄像头通道
- 遍历所有设备的通道
- 抓拍图片保存
- 生成摄像头清单
"""

import os
import requests
import json
import time
from datetime import datetime

# Token 配置
APP_TOKEN = "at-wna4ifY5raIKfMjOgybhp4cJik_63ZMJ09MoSY0T"
USER_TOKEN = "ut-39605109-9f5f-4766-aeb7-ee7be1a92cc8"
BASE_URL = "https://open-api.hikiot.com"

# 模拟浏览器的请求头
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Origin": "https://open.hikiot.com",
    "Referer": "https://open.hikiot.com/",
    "Connection": "keep-alive",
}


def get_all_devices():
    """
    分页获取所有设备列表
    API: GET /device/v1/page
    """
    url = f"{BASE_URL}/device/v1/page"
    headers = {
        **BROWSER_HEADERS,
        "App-Access-Token": APP_TOKEN,
        "User-Access-Token": USER_TOKEN,
    }
    
    all_devices = []
    page = 1
    page_size = 50
    
    while True:
        params = {"page": page, "size": page_size}
        
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            result = resp.json()
            
            if result.get("code") == 0:
                data = result.get("data", [])
                count = result.get("count", 0)
                
                if not data:
                    break
                
                all_devices.extend(data)
                print(f"  第 {page} 页: 获取 {len(data)} 个设备 (总计: {len(all_devices)}/{count})")
                
                # 如果已经获取全部设备，退出循环
                if len(all_devices) >= count or len(data) < page_size:
                    break
                
                page += 1
            else:
                print(f"获取设备列表失败: {result.get('msg')}")
                break
        except Exception as e:
            print(f"请求失败: {e}")
            break
    
    return all_devices


# 保持向后兼容
def get_device_list():
    """获取设备列表（旧接口，使用分页获取）"""
    return get_all_devices()


def capture_image(device_serial, channel_no=1):
    """
    抓拍设备图片
    API: POST /device/direct/v1/captureImage/captureImage
    """
    url = f"{BASE_URL}/device/direct/v1/captureImage/captureImage"
    headers = {
        **BROWSER_HEADERS,
        "App-Access-Token": APP_TOKEN,
        "User-Access-Token": USER_TOKEN,
        "Content-Type": "application/json"
    }
    data = {
        "deviceSerial": device_serial,
        "payload": {
            "channelNo": channel_no
        }
    }
    
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        result = resp.json()
        if result.get("code") == 0:
            capture_url = result["data"].get("captureUrl")
            return capture_url
        else:
            return None
    except Exception as e:
        return None


def download_image(url, save_path):
    """下载图片"""
    try:
        headers = {
            **BROWSER_HEADERS,
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
        }
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(resp.content)
            return True
        return False
    except Exception as e:
        return False


def get_all_cameras_list():
    """
    获取所有摄像头列表（设备和通道展开）
    返回平铺的摄像头列表
    """
    devices = get_all_devices()
    all_cameras = []
    
    for device in devices:
        device_serial = device.get("deviceSerial")
        device_name = device.get("name", "未知")
        channel_num = device.get("channelNum", 64)
        
        # 为每个通道创建一个摄像头记录
        for channel_no in range(1, channel_num + 1):
            all_cameras.append({
                "deviceSerial": device_serial,
                "deviceName": device_name,
                "channelNo": channel_no,
                "cameraId": f"{device_serial}_{channel_no}",
                "cameraName": f"{device_name}_通道{channel_no}"
            })
    
    return all_cameras


def batch_capture_all_channels(max_channels_per_device=20):
    """
    批量抓拍所有通道
    Args:
        max_channels_per_device: 每个设备最多抓拍的通道数（默认20）
    """
    print("=" * 70)
    print("批量抓拍所有摄像头通道")
    print("=" * 70)
    
    # 获取设备列表
    devices = get_all_devices()
    if not devices:
        print("获取设备列表失败")
        return
    
    print(f"\n共有 {len(devices)} 个设备")
    
    # 计算总摄像头数
    total_cameras = sum(min(d.get("channelNum", 64), max_channels_per_device) for d in devices)
    print(f"预计抓拍: {total_cameras} 个摄像头（每个设备最多{max_channels_per_device}个通道）")
    
    # 创建输出目录
    output_dir = "algorithm/data/images/all_channels"
    os.makedirs(output_dir, exist_ok=True)
    
    # 摄像头清单
    camera_list = []
    captured_count = 0
    failed_count = 0
    
    # 遍历每个设备的通道
    for device in devices:
        device_serial = device.get("deviceSerial")
        device_name = device.get("name", "未知")
        channel_num = device.get("channelNum", 64)
        
        print(f"\n设备: {device_name} ({device_serial})")
        print(f"通道数: {channel_num}")
        print("-" * 70)
        
        # 遍历通道
        for channel_no in range(1, min(channel_num + 1, max_channels_per_device + 1)):
            print(f"  抓拍通道 {channel_no}...", end=" ")
            
            capture_url = capture_image(device_serial, channel_no)
            
            if capture_url:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{device_serial}_ch{channel_no}_{timestamp}.jpg"
                save_path = f"{output_dir}/{filename}"
                
                if download_image(capture_url, save_path):
                    print(f"✓ 成功")
                    camera_list.append({
                        "deviceSerial": device_serial,
                        "deviceName": device_name,
                        "channelNo": channel_no,
                        "captureUrl": capture_url,
                        "localPath": save_path,
                        "timestamp": timestamp,
                        "status": "success"
                    })
                    captured_count += 1
                else:
                    print(f"✗ 下载失败")
                    camera_list.append({
                        "deviceSerial": device_serial,
                        "deviceName": device_name,
                        "channelNo": channel_no,
                        "status": "download_failed"
                    })
                    failed_count += 1
            else:
                print(f"✗ 抓拍失败")
                camera_list.append({
                    "deviceSerial": device_serial,
                    "deviceName": device_name,
                    "channelNo": channel_no,
                    "status": "capture_failed"
                })
                failed_count += 1
            
            # 避免请求过快
            time.sleep(0.5)
    
    # 保存摄像头清单
    summary = {
        "timestamp": datetime.now().isoformat(),
        "totalDevices": len(devices),
        "totalCameras": len(camera_list),
        "captured": captured_count,
        "failed": failed_count,
        "cameras": camera_list
    }
    
    with open(f"{output_dir}/camera_list.json", "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 70)
    print(f"总计: {len(camera_list)} 个摄像头")
    print(f"成功: {captured_count}")
    print(f"失败: {failed_count}")
    print(f"清单保存至: {output_dir}/camera_list.json")
    print("=" * 70)
    
    return camera_list


def export_camera_list():
    """
    导出所有摄像头清单（仅列表，不抓拍）
    用于确认有林麝的摄像头ID
    """
    print("=" * 70)
    print("导出所有摄像头清单")
    print("=" * 70)
    
    cameras = get_all_cameras_list()
    
    print(f"\n总计: {len(cameras)} 个摄像头\n")
    print("-" * 70)
    
    # 按设备分组显示
    current_device = None
    for cam in cameras:
        if cam["deviceSerial"] != current_device:
            current_device = cam["deviceSerial"]
            print(f"\n设备: {cam['deviceName']} ({cam['deviceSerial']})")
            print("-" * 70)
        print(f"  通道 {cam['channelNo']:2d}: {cam['cameraId']}")
    
    # 保存清单
    output_dir = "algorithm/data"
    os.makedirs(output_dir, exist_ok=True)
    
    with open(f"{output_dir}/all_cameras_list.json", "w") as f:
        json.dump({
            "total": len(cameras),
            "cameras": cameras
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'=' * 70}")
    print(f"清单已保存: {output_dir}/all_cameras_list.json")
    print(f"{'=' * 70}")
    
    return cameras


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        # 仅导出清单模式
        export_camera_list()
    else:
        # 批量抓拍模式
        batch_capture_all_channels()
