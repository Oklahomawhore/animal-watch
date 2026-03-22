#!/usr/bin/env python3
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
