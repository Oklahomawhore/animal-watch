#!/bin/bash
# 在服务器上运行林麝检测冷启动

SERVER="root@47.111.141.55"
WORK_DIR="/opt/animalwatch"

echo "=== 林麝检测冷启动 - 服务器部署 ==="

# 1. 进入Docker容器运行检测
ssh $SERVER << 'EOF'
cd /opt/animalwatch

# 进入animalwatch容器
docker exec -i animalwatch bash << 'CONTAINER'

# 安装依赖
pip install ultralytics opencv-python numpy matplotlib -q

# 创建检测脚本
cat > /tmp/detect_linshe.py << 'PYTHON'
#!/usr/bin/env python3
import cv2
import numpy as np
from ultralytics import YOLO
from pathlib import Path
import json
from datetime import datetime

# COCO动物类别
ANIMAL_CLASSES = [15, 16, 17, 21, 22, 23]  # cat, dog, horse, bear, zebra, giraffe

class LinSheDetector:
    def __init__(self, model_path='yolov8n.pt', conf_threshold=0.3):
        print("[初始化] 加载YOLOv8 COCO预训练模型...")
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        print(f"[初始化] 模型加载完成")
        
    def detect(self, image_path):
        image = cv2.imread(str(image_path))
        if image is None:
            return []
        
        h, w = image.shape[:2]
        results = self.model(image, classes=ANIMAL_CLASSES, conf=self.conf_threshold, verbose=False)
        
        detections = []
        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                
                box_w, box_h = x2 - x1, y2 - y1
                area_ratio = (box_w * box_h) / (w * h)
                aspect_ratio = box_w / box_h if box_h > 0 else 0
                
                # 林麝体型过滤
                if 0.03 < area_ratio < 0.35 and 0.8 < aspect_ratio < 2.5:
                    detections.append({
                        'bbox': [int(x1), int(y1), int(x2), int(y2)],
                        'confidence': round(conf, 3),
                        'area_ratio': round(area_ratio, 4)
                    })
        
        return detections

def batch_detect(image_dir):
    detector = LinSheDetector()
    image_paths = list(Path(image_dir).glob('*.jpg'))
    
    print(f"[批量检测] 共 {len(image_paths)} 张图片")
    
    results = []
    for i, img_path in enumerate(image_paths, 1):
        detections = detector.detect(img_path)
        results.append({
            'image': str(img_path),
            'count': len(detections),
            'detections': detections
        })
        if i % 10 == 0:
            print(f"  进度: {i}/{len(image_paths)}")
    
    # 保存结果
    output = {
        'timestamp': datetime.now().isoformat(),
        'total_images': len(image_paths),
        'images_with_detection': sum(1 for r in results if r['count'] > 0),
        'total_detections': sum(r['count'] for r in results),
        'results': results
    }
    
    with open('/tmp/detection_results.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\n[汇总]")
    print(f"  - 总图片数: {len(image_paths)}")
    print(f"  - 检测到目标的图片: {output['images_with_detection']}")
    print(f"  - 总检测数: {output['total_detections']}")
    print(f"  - 检测率: {output['images_with_detection']/len(image_paths)*100:.1f}%")

if __name__ == "__main__":
    batch_detect("/app/algorithm/data/images/all_channels")
PYTHON

# 运行检测
python3 /tmp/detect_linshe.py

# 复制结果出来
cp /tmp/detection_results.json /app/algorithm/output/

CONTAINER

EOF

echo "=== 检测完成 ==="
