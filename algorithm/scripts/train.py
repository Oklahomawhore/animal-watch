#!/usr/bin/env python3
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
