#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
林麝检测 - 冷启动方案 Day 1
使用YOLOv8 COCO预训练模型 + 规则过滤
无需人工标注
"""

import cv2
import numpy as np
from ultralytics import YOLO
from pathlib import Path
import json
from datetime import datetime

# COCO数据集中与林麝相似的动物类别
# 15: cat, 16: dog, 17: horse, 21: bear, 22: zebra, 23: giraffe
ANIMAL_CLASSES = [15, 16, 17, 21, 22, 23]

# 林麝体型参数（基于画面比例）
MIN_AREA_RATIO = 0.03   # 最小占画面3%
MAX_AREA_RATIO = 0.35   # 最大占画面35%
MIN_ASPECT_RATIO = 0.8  # 最小宽高比
MAX_ASPECT_RATIO = 2.5  # 最大宽高比


class LinSheDetector:
    """林麝检测器 - 冷启动版本"""
    
    def __init__(self, model_path='yolov8n.pt', conf_threshold=0.3):
        """
        初始化检测器
        Args:
            model_path: YOLOv8模型路径，默认下载COCO预训练权重
            conf_threshold: 置信度阈值
        """
        print("[初始化] 加载YOLOv8 COCO预训练模型...")
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        print(f"[初始化] 模型加载完成，置信度阈值: {conf_threshold}")
        
    def detect(self, image_path, save_result=True):
        """
        检测林麝
        Args:
            image_path: 图片路径
            save_result: 是否保存结果
        Returns:
            detections: 检测框列表
        """
        # 读取图片
        image = cv2.imread(str(image_path))
        if image is None:
            print(f"[错误] 无法读取图片: {image_path}")
            return []
        
        h, w = image.shape[:2]
        
        # YOLOv8检测（只检测动物类别）
        results = self.model(image, classes=ANIMAL_CLASSES, conf=self.conf_threshold, verbose=False)
        
        detections = []
        for r in results:
            boxes = r.boxes
            for box in boxes:
                # 获取框坐标
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                
                # 计算面积比例
                box_w = x2 - x1
                box_h = y2 - y1
                area_ratio = (box_w * box_h) / (w * h)
                aspect_ratio = box_w / box_h if box_h > 0 else 0
                
                # 规则过滤：大小和形状
                if MIN_AREA_RATIO < area_ratio < MAX_AREA_RATIO and \
                   MIN_ASPECT_RATIO < aspect_ratio < MAX_ASPECT_RATIO:
                    
                    detection = {
                        'bbox': [int(x1), int(y1), int(x2), int(y2)],
                        'confidence': round(conf, 3),
                        'coco_class': cls,
                        'area_ratio': round(area_ratio, 4),
                        'aspect_ratio': round(aspect_ratio, 2)
                    }
                    detections.append(detection)
        
        # 保存结果
        if save_result and detections:
            self._save_result(image, detections, image_path)
        
        return detections
    
    def _save_result(self, image, detections, image_path):
        """保存检测结果"""
        # 绘制检测框
        result_img = image.copy()
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            conf = det['confidence']
            
            # 绘制框
            cv2.rectangle(result_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # 绘制标签
            label = f"LinShe {conf:.2f}"
            cv2.putText(result_img, label, (x1, y1-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # 保存路径
        output_dir = Path('algorithm/output/detection')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / f"{Path(image_path).stem}_detected.jpg"
        cv2.imwrite(str(output_path), result_img)
        
        # 保存JSON
        json_path = output_dir / f"{Path(image_path).stem}_detected.json"
        with open(json_path, 'w') as f:
            json.dump({
                'image': str(image_path),
                'timestamp': datetime.now().isoformat(),
                'model': 'yolov8n-coco',
                'detections': detections
            }, f, indent=2)
        
        print(f"[保存] 结果已保存: {output_path}")


def batch_detect(image_dir, output_summary=True):
    """
    批量检测
    Args:
        image_dir: 图片目录
        output_summary: 是否输出汇总
    """
    detector = LinSheDetector()
    
    image_paths = list(Path(image_dir).glob('*.jpg'))
    print(f"[批量检测] 共 {len(image_paths)} 张图片")
    
    all_results = []
    for i, img_path in enumerate(image_paths, 1):
        print(f"\n[{i}/{len(image_paths)}] 检测: {img_path.name}")
        detections = detector.detect(img_path)
        
        result = {
            'image': str(img_path),
            'detection_count': len(detections),
            'detections': detections
        }
        all_results.append(result)
        
        if detections:
            print(f"  ✓ 检测到 {len(detections)} 个目标")
            for j, det in enumerate(detections):
                print(f"    - 目标{j+1}: 置信度={det['confidence']}, 面积比={det['area_ratio']}")
        else:
            print(f"  ✗ 未检测到目标")
    
    # 保存汇总
    if output_summary:
        summary_path = Path('algorithm/output/detection/summary.json')
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(summary_path, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_images': len(image_paths),
                'images_with_detection': sum(1 for r in all_results if r['detection_count'] > 0),
                'total_detections': sum(r['detection_count'] for r in all_results),
                'results': all_results
            }, f, indent=2)
        
        print(f"\n[汇总] 结果已保存: {summary_path}")
        print(f"  - 总图片数: {len(image_paths)}")
        print(f"  - 检测到目标的图片: {sum(1 for r in all_results if r['detection_count'] > 0)}")
        print(f"  - 总检测数: {sum(r['detection_count'] for r in all_results)}")


if __name__ == "__main__":
    import sys
    
    # 测试单张图片
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        detector = LinSheDetector()
        detections = detector.detect(image_path)
        print(f"\n检测结果: {len(detections)} 个目标")
    else:
        # 批量检测
        image_dir = "algorithm/data/images/all_channels"
        batch_detect(image_dir)
