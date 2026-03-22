#!/usr/bin/env python3
"""
林麝检测 - 冷启动方案
使用YOLOv8 COCO预训练权重 + 规则过滤
无需人工标注数据
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AnimalDetector:
    """
    动物检测器 - 基于YOLOv8 COCO预训练模型
    
    使用COCO数据集中的动物类别进行迁移检测：
    - 15: cat (猫)
    - 16: dog (狗)
    - 17: horse (马)
    - 21: bear (熊)
    - 22: zebra (斑马)
    - 23: giraffe (长颈鹿)
    
    林麝体型类似小型鹿/山羊，可通过规则过滤筛选
    """
    
    # COCO动物类别ID
    ANIMAL_CLASSES = [15, 16, 17, 21, 22, 23]
    
    # 林麝体型参数（占画面比例）
    MIN_SIZE_RATIO = 0.02  # 最小占比 2%
    MAX_SIZE_RATIO = 0.5   # 最大占比 50%
    
    def __init__(self, model_path: str = 'yolov8n.pt', conf_threshold: float = 0.3):
        """
        初始化检测器
        
        Args:
            model_path: YOLOv8模型路径，默认自动下载
            conf_threshold: 置信度阈值
        """
        self.conf_threshold = conf_threshold
        
        try:
            from ultralytics import YOLO
            self.model = YOLO(model_path)
            logger.info(f"模型加载成功: {model_path}")
        except ImportError:
            raise ImportError("请先安装ultralytics: pip install ultralytics")
    
    def detect(self, image_path: str) -> List[Dict]:
        """
        检测图片中的动物
        
        Args:
            image_path: 图片路径
            
        Returns:
            检测结果列表，每个结果包含bbox、confidence等
        """
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法读取图片: {image_path}")
        
        height, width = image.shape[:2]
        image_area = height * width
        
        # 运行检测
        results = self.model(image, classes=self.ANIMAL_CLASSES, conf=self.conf_threshold)
        
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0].cpu().numpy())
                cls = int(box.cls[0].cpu().numpy())
                
                # 计算bbox面积占比
                bbox_area = (x2 - x1) * (y2 - y1)
                size_ratio = bbox_area / image_area
                
                # 规则过滤：根据体型筛选
                if self.MIN_SIZE_RATIO <= size_ratio <= self.MAX_SIZE_RATIO:
                    detection = {
                        'bbox': [float(x1), float(y1), float(x2), float(y2)],
                        'confidence': conf,
                        'class': self.model.names[cls],
                        'class_id': cls,
                        'size_ratio': size_ratio,
                        'estimated_size': self._estimate_size(size_ratio),
                        'is_likely_linshe': self._is_likely_linshe(size_ratio, cls)
                    }
                    detections.append(detection)
        
        logger.info(f"检测到 {len(detections)} 个目标")
        return detections
    
    def _estimate_size(self, size_ratio: float) -> str:
        """根据占比估算体型"""
        if size_ratio < 0.05:
            return 'small'  # 小型
        elif size_ratio < 0.2:
            return 'medium'  # 中型（林麝属于此类）
        else:
            return 'large'  # 大型
    
    def _is_likely_linshe(self, size_ratio: float, class_id: int) -> bool:
        """
        判断是否可能是林麝
        
        林麝特征：
        - 体型：中型（占画面5%-20%）
        - 类别：优先匹配 deer-like 动物（horse, bear）
        """
        is_medium = 0.05 <= size_ratio <= 0.2
        is_deer_like = class_id in [17, 21]  # horse, bear
        
        return is_medium and is_deer_like
    
    def visualize(self, image_path: str, detections: List[Dict], 
                  output_path: Optional[str] = None) -> np.ndarray:
        """
        可视化检测结果
        
        Args:
            image_path: 原图路径
            detections: 检测结果
            output_path: 输出路径（可选）
            
        Returns:
            可视化后的图片
        """
        image = cv2.imread(image_path)
        
        for det in detections:
            x1, y1, x2, y2 = map(int, det['bbox'])
            conf = det['confidence']
            is_linshe = det['is_likely_linshe']
            
            # 根据是否可能是林麝选择颜色
            color = (0, 255, 0) if is_linshe else (0, 165, 255)
            
            # 画框
            cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
            
            # 标签
            label = f"{det['class']} {conf:.2f}"
            if is_linshe:
                label += " [林麝?]"
            
            # 画标签背景
            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(image, (x1, y1 - text_h - 10), (x1 + text_w, y1), color, -1)
            cv2.putText(image, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        if output_path:
            cv2.imwrite(output_path, image)
            logger.info(f"可视化结果保存至: {output_path}")
        
        return image


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='林麝检测 - 冷启动方案')
    parser.add_argument('--image', '-i', required=True, help='输入图片路径')
    parser.add_argument('--output', '-o', default='output', help='输出目录')
    parser.add_argument('--model', '-m', default='yolov8n.pt', help='模型路径')
    parser.add_argument('--conf', '-c', type=float, default=0.3, help='置信度阈值')
    parser.add_argument('--visualize', '-v', action='store_true', help='可视化结果')
    
    args = parser.parse_args()
    
    # 创建输出目录
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 初始化检测器
    detector = AnimalDetector(model_path=args.model, conf_threshold=args.conf)
    
    # 检测
    detections = detector.detect(args.image)
    
    # 打印结果
    print(f"\n检测到 {len(detections)} 个目标:")
    for i, det in enumerate(detections, 1):
        print(f"  {i}. {det['class']} (置信度: {det['confidence']:.2f}, "
              f"体型: {det['estimated_size']}, 可能是林麝: {det['is_likely_linshe']})")
    
    # 可视化
    if args.visualize:
        output_path = output_dir / f"{Path(args.image).stem}_detected.jpg"
        detector.visualize(args.image, detections, str(output_path))
    
    # 保存检测结果
    import json
    result_path = output_dir / f"{Path(args.image).stem}_result.json"
    with open(result_path, 'w') as f:
        json.dump(detections, f, indent=2, ensure_ascii=False)
    print(f"\n结果已保存至: {result_path}")


if __name__ == '__main__':
    main()
