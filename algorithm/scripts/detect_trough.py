#!/usr/bin/env python3
"""
食槽检测 - 冷启动方案
使用OpenCV传统CV方法：矩形检测 + 绿色像素分析
无需训练数据
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TroughDetector:
    """
    食槽检测器
    
    检测逻辑：
    1. 边缘检测（Canny）
    2. 轮廓检测
    3. 矩形筛选（4边形，面积适中）
    4. 绿色像素分析（HSV颜色空间）
    5. 判断是否有草
    """
    
    def __init__(self, 
                 min_area: int = 1000,
                 max_area: int = 100000,
                 green_ratio_threshold: Tuple[float, float] = (0.05, 0.8)):
        """
        初始化检测器
        
        Args:
            min_area: 最小轮廓面积
            max_area: 最大轮廓面积
            green_ratio_threshold: 绿色像素占比阈值 (min, max)
        """
        self.min_area = min_area
        self.max_area = max_area
        self.green_ratio_min, self.green_ratio_max = green_ratio_threshold
        
        # HSV绿色范围（草的颜色）
        self.lower_green = np.array([35, 40, 40])
        self.upper_green = np.array([85, 255, 255])
    
    def detect(self, image_path: str) -> List[Dict]:
        """
        检测图片中的食槽
        
        Args:
            image_path: 图片路径
            
        Returns:
            食槽列表，每个包含位置、绿色占比、状态等
        """
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法读取图片: {image_path}")
        
        # 1. 预处理
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 2. 边缘检测
        edges = cv2.Canny(blurred, 50, 150)
        
        # 3. 膨胀连接边缘
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        edges = cv2.dilate(edges, kernel, iterations=1)
        
        # 4. 轮廓检测
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        troughs = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            
            # 面积筛选
            if not (self.min_area <= area <= self.max_area):
                continue
            
            # 近似多边形
            epsilon = 0.02 * cv2.arcLength(cnt, True)
            approx = cv2.approxPolyDP(cnt, epsilon, True)
            
            # 获取外接矩形
            x, y, w, h = cv2.boundingRect(approx)
            aspect_ratio = float(w) / h if h > 0 else 0
            
            # 食槽通常是扁平矩形（长宽比 > 1.5）
            if aspect_ratio < 1.2:
                continue
            
            # 提取ROI
            roi = image[y:y+h, x:x+w]
            if roi.size == 0:
                continue
            
            # 5. 绿色像素分析
            green_ratio = self._calculate_green_ratio(roi)
            
            # 判断状态
            status = self._judge_status(green_ratio)
            
            trough = {
                'bbox': [int(x), int(y), int(w), int(h)],
                'area': int(area),
                'aspect_ratio': round(aspect_ratio, 2),
                'green_ratio': round(green_ratio, 3),
                'status': status,
                'confidence': self._calculate_confidence(green_ratio, aspect_ratio)
            }
            troughs.append(trough)
        
        # 按置信度排序
        troughs.sort(key=lambda x: x['confidence'], reverse=True)
        
        logger.info(f"检测到 {len(troughs)} 个食槽")
        return troughs
    
    def _calculate_green_ratio(self, roi: np.ndarray) -> float:
        """计算ROI中绿色像素占比"""
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower_green, self.upper_green)
        
        # 形态学操作去噪
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        green_pixels = np.sum(mask > 0)
        total_pixels = roi.shape[0] * roi.shape[1]
        
        return green_pixels / total_pixels if total_pixels > 0 else 0
    
    def _judge_status(self, green_ratio: float) -> str:
        """根据绿色占比判断食槽状态"""
        if green_ratio < 0.05:
            return 'empty'  # 空槽
        elif green_ratio < 0.3:
            return 'low'    # 少量
        elif green_ratio < 0.6:
            return 'medium' # 中等
        else:
            return 'full'   # 满槽
    
    def _calculate_confidence(self, green_ratio: float, aspect_ratio: float) -> float:
        """计算检测置信度"""
        # 绿色占比在合理范围内
        green_score = 1.0 - abs(green_ratio - 0.3) * 2
        green_score = max(0, min(1, green_score))
        
        # 长宽比合适（食槽通常是扁平的）
        ratio_score = 1.0 - abs(aspect_ratio - 3.0) / 3.0
        ratio_score = max(0, min(1, ratio_score))
        
        return round((green_score + ratio_score) / 2, 2)
    
    def visualize(self, image_path: str, troughs: List[Dict],
                  output_path: Optional[str] = None) -> np.ndarray:
        """可视化检测结果"""
        image = cv2.imread(image_path)
        
        # 状态颜色映射
        status_colors = {
            'empty': (128, 128, 128),   # 灰色
            'low': (0, 165, 255),       # 橙色
            'medium': (0, 255, 255),    # 黄色
            'full': (0, 255, 0)         # 绿色
        }
        
        status_text = {
            'empty': '空槽',
            'low': '少量',
            'medium': '中等',
            'full': '满槽'
        }
        
        for trough in troughs:
            x, y, w, h = trough['bbox']
            status = trough['status']
            color = status_colors.get(status, (128, 128, 128))
            
            # 画框
            cv2.rectangle(image, (x, y), (x+w, y+h), color, 2)
            
            # 标签
            label = f"{status_text.get(status, status)} {trough['green_ratio']:.1%}"
            
            # 标签背景
            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(image, (x, y - text_h - 10), (x + text_w, y), color, -1)
            cv2.putText(image, label, (x, y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        if output_path:
            cv2.imwrite(output_path, image)
            logger.info(f"可视化结果保存至: {output_path}")
        
        return image


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='食槽检测 - 冷启动方案')
    parser.add_argument('--image', '-i', required=True, help='输入图片路径')
    parser.add_argument('--output', '-o', default='output', help='输出目录')
    parser.add_argument('--min-area', type=int, default=1000, help='最小面积')
    parser.add_argument('--max-area', type=int, default=100000, help='最大面积')
    parser.add_argument('--visualize', '-v', action='store_true', help='可视化结果')
    
    args = parser.parse_args()
    
    # 创建输出目录
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 初始化检测器
    detector = TroughDetector(min_area=args.min_area, max_area=args.max_area)
    
    # 检测
    troughs = detector.detect(args.image)
    
    # 打印结果
    print(f"\n检测到 {len(troughs)} 个食槽:")
    for i, trough in enumerate(troughs, 1):
        status_text = {'empty': '空槽', 'low': '少量', 'medium': '中等', 'full': '满槽'}
        print(f"  {i}. 位置: {trough['bbox']}, "
              f"状态: {status_text.get(trough['status'], trough['status'])}, "
              f"绿色占比: {trough['green_ratio']:.1%}, "
              f"置信度: {trough['confidence']}")
    
    # 可视化
    if args.visualize:
        output_path = output_dir / f"{Path(args.image).stem}_troughs.jpg"
        detector.visualize(args.image, troughs, str(output_path))
    
    # 保存结果
    import json
    result_path = output_dir / f"{Path(args.image).stem}_troughs.json"
    with open(result_path, 'w') as f:
        json.dump(troughs, f, indent=2, ensure_ascii=False)
    print(f"\n结果已保存至: {result_path}")


if __name__ == '__main__':
    main()
