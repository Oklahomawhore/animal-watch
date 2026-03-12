#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
林麝检测算法开发环境搭建脚本
- 创建 conda 环境
- 安装依赖
- 测试摄像头 API 连接
- 批量下载测试图片
"""

import os
import sys
import requests
import json
from datetime import datetime

# Token 配置
APP_TOKEN = "at-wna4ifY5raIKfMjOgybhp4cJik_63ZMJ09MoSY0T"
USER_TOKEN = "ut-39605109-9f5f-4766-aeb7-ee7be1a92cc8"
BASE_URL = "https://open-api.hikiot.com"

# 已知的设备列表
DEVICES = [
    {"deviceSerial": "GF6830765", "name": "2区母麝圈", "model": "DS-8864N-R8(C)", "channelNum": 64},
    {"deviceSerial": "GG3425740", "name": "2区公麝圈", "model": "DS-8864N-R8(C)", "channelNum": 64},
    {"deviceSerial": "FU7533003", "name": "1区A1侧✕共同区域", "model": "DS-8864N-R8(D)", "channelNum": 64},
    # 添加更多设备...
]


# 模拟浏览器的请求头（避免被 WAF 拦截）
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Origin": "https://open.hikiot.com",
    "Referer": "https://open.hikiot.com/",
    "Connection": "keep-alive",
}


def get_device_list():
    """获取设备列表"""
    url = f"{BASE_URL}/device/v1/page"
    headers = {
        **BROWSER_HEADERS,
        "App-Access-Token": APP_TOKEN,
        "User-Access-Token": USER_TOKEN,
    }
    params = {"page": 1, "size": 50}
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        result = resp.json()
        if result.get("code") == 0:
            return result.get("data", [])
        else:
            print(f"获取设备列表失败: {result.get('msg')}")
            return []
    except Exception as e:
        print(f"请求失败: {e}")
        return []


def capture_image(device_serial, channel_no=1):
    """抓拍设备图片"""
    # 海康 API: POST /device/camera/v1/capture
    url = f"{BASE_URL}/device/camera/v1/capture"
    headers = {
        **BROWSER_HEADERS,
        "App-Access-Token": APP_TOKEN,
        "User-Access-Token": USER_TOKEN,
        "Content-Type": "application/json"
    }
    data = {
        "deviceSerial": device_serial,
        "channelNo": channel_no
    }
    
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=30)
        result = resp.json()
        if result.get("code") == 0:
            return result["data"].get("picUrl")
        else:
            print(f"  抓拍失败 [{device_serial}]: {result.get('msg')} (code: {result.get('code')})")
            return None
    except Exception as e:
        print(f"  请求失败 [{device_serial}]: {e}")
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
        print(f"下载失败: {e}")
        return False


def setup_environment():
    """搭建算法开发环境"""
    print("=" * 60)
    print("林麝检测算法开发环境搭建")
    print("=" * 60)
    
    # 创建目录
    dirs = [
        "algorithm/data/images",
        "algorithm/data/annotations",
        "algorithm/models",
        "algorithm/scripts",
        "algorithm/output"
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        print(f"✓ 创建目录: {d}")
    
    print("\n" + "=" * 60)
    print("测试 API 连接")
    print("=" * 60)
    
    # 测试获取设备列表
    devices = get_device_list()
    if devices:
        print(f"✓ 成功获取 {len(devices)} 个设备")
        for d in devices[:5]:
            print(f"  - {d.get('deviceSerial')}: {d.get('name')}")
    else:
        print("✗ 获取设备列表失败，使用预定义列表")
        devices = DEVICES
    
    print("\n" + "=" * 60)
    print("批量抓拍测试图片")
    print("=" * 60)
    
    captured = []
    for device in devices[:5]:  # 前5个设备
        device_serial = device.get("deviceSerial")
        device_name = device.get("name", "unknown")
        
        print(f"\n抓拍: {device_name} ({device_serial})")
        
        # 抓拍第1通道
        pic_url = capture_image(device_serial, channel_no=1)
        if pic_url:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{device_serial}_ch1_{timestamp}.jpg"
            save_path = f"algorithm/data/images/{filename}"
            
            if download_image(pic_url, save_path):
                print(f"  ✓ 保存: {save_path}")
                captured.append({
                    "device": device,
                    "channel": 1,
                    "path": save_path,
                    "url": pic_url
                })
            else:
                print(f"  ✗ 下载失败")
        else:
            print(f"  ✗ 抓拍失败")
    
    # 保存元数据
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "total_devices": len(devices),
        "captured_images": len(captured),
        "images": captured
    }
    
    with open("algorithm/data/captured_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    print("\n" + "=" * 60)
    print(f"完成！共抓拍 {len(captured)} 张图片")
    print("元数据保存至: algorithm/data/captured_metadata.json")
    print("=" * 60)
    
    return captured


def create_requirements():
    """创建 requirements.txt"""
    requirements = """# 算法开发依赖
# 安装: pip install -r requirements.txt

# 深度学习
torch>=2.0.0
torchvision>=0.15.0
ultralytics>=8.0.0  # YOLOv8

# 图像处理
opencv-python>=4.8.0
Pillow>=10.0.0
numpy>=1.24.0
scikit-image>=0.21.0

# 数据标注
labelImg>=1.8.0

# 工具
requests>=2.31.0
tqdm>=4.65.0
matplotlib>=3.7.0
"""
    
    with open("algorithm/requirements.txt", "w") as f:
        f.write(requirements)
    print("✓ 创建 algorithm/requirements.txt")


def create_train_script():
    """创建训练脚本"""
    script = '''#!/usr/bin/env python3
"""
YOLOv8 训练脚本
"""
from ultralytics import YOLO

def train():
    # 加载预训练模型
    model = YOLO('yolov8n.pt')  # nano版本，速度快
    
    # 训练配置
    model.train(
        data='lin-she.yaml',      # 数据集配置文件
        epochs=100,                # 训练轮数
        imgsz=640,                 # 输入尺寸
        batch=16,                  # 批次大小
        device=0,                  # GPU设备
        workers=8,                 # 数据加载线程
        patience=20,               # 早停耐心值
        save=True,                 # 保存模型
        project='runs/detect',     # 项目目录
        name='lin-she-detection',  # 实验名称
    )
    
    # 验证
    metrics = model.val()
    print(f"mAP50-95: {metrics.box.map}")
    print(f"mAP50: {metrics.box.map50}")

if __name__ == "__main__":
    train()
'''
    
    with open("algorithm/scripts/train.py", "w") as f:
        f.write(script)
    print("✓ 创建 algorithm/scripts/train.py")


def create_detect_script():
    """创建检测脚本"""
    script = '''#!/usr/bin/env python3
"""
动物检测推理脚本
"""
import cv2
from ultralytics import YOLO
import argparse

def detect(image_path, model_path='runs/detect/lin-she-detection/weights/best.pt'):
    """检测图片中的动物"""
    # 加载模型
    model = YOLO(model_path)
    
    # 推理
    results = model(image_path)
    
    # 解析结果
    detections = []
    for r in results:
        boxes = r.boxes
        for box in boxes:
            detection = {
                'class': model.names[int(box.cls)],
                'confidence': float(box.conf),
                'bbox': box.xyxy.tolist()[0]  # [x1, y1, x2, y2]
            }
            detections.append(detection)
    
    # 保存标注图片
    annotated = results[0].plot()
    output_path = image_path.replace('.jpg', '_detected.jpg')
    cv2.imwrite(output_path, annotated)
    
    return detections, output_path

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', required=True, help='输入图片路径')
    parser.add_argument('--model', default='runs/detect/lin-she-detection/weights/best.pt')
    args = parser.parse_args()
    
    detections, output = detect(args.image, args.model)
    print(f"检测到 {len(detections)} 个目标")
    for d in detections:
        print(f"  - {d['class']}: {d['confidence']:.2f}")
    print(f"结果保存至: {output}")
'''
    
    with open("algorithm/scripts/detect.py", "w") as f:
        f.write(script)
    print("✓ 创建 algorithm/scripts/detect.py")


if __name__ == "__main__":
    # 创建环境
    setup_environment()
    
    # 创建依赖文件
    create_requirements()
    
    # 创建训练脚本
    create_train_script()
    
    # 创建检测脚本
    create_detect_script()
    
    print("\n" + "=" * 60)
    print("下一步:")
    print("1. 安装依赖: pip install -r algorithm/requirements.txt")
    print("2. 标注数据: labelImg algorithm/data/images")
    print("3. 训练模型: python algorithm/scripts/train.py")
    print("4. 测试检测: python algorithm/scripts/detect.py --image xxx.jpg")
    print("=" * 60)
