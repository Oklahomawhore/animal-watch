# 林麝检测算法 - 冷启动方案（7天）

**目标**: 无人工标注，复用已有模型，7天内完成冷启动  
**策略**: 迁移学习 + 无监督检测 + 规则引擎

---

## Day 1-2: 林麝检测（动物活体检测复用）

### 方案
**使用预训练模型**: YOLOv8 COCO 预训练权重
- COCO 数据集包含 "bear", "cat", "dog" 等动物类别
- 林麝属于鹿科，外形类似小型鹿/山羊
- 利用相似动物特征进行迁移检测

### 实现步骤
1. 加载 YOLOv8 COCO 预训练模型
2. 检测所有动物类别（过滤出类似林麝的目标）
3. 基于大小/形状规则过滤（林麝体型：体长60-80cm）
4. 保存检测结果作为伪标签

### 代码
```python
from ultralytics import YOLO

# 加载COCO预训练模型
model = YOLO('yolov8n.pt')  # 自动下载COCO权重

# 检测
results = model('image.jpg', classes=[15, 16, 17, 21, 22])  # 动物类别
# 15: cat, 16: dog, 17: horse, 21: bear, 22: zebra

# 过滤规则：根据bbox大小估算体型
for r in results:
    for box in r.boxes:
        w, h = box.xywh[0][2:4]  # 宽高
        area = w * h
        if 0.05 < area < 0.3:  # 林麝占画面5-30%
            # 保存为林麝候选
```

### 预期效果
- mAP@0.5: 0.6-0.7（冷启动）
- 召回率: > 80%
- 误检率: 20-30%（可接受）

---

## Day 3-4: 食槽检测（矩形框 + 绿色像素）

### 方案
**无需训练，纯CV方法**

### 检测逻辑
1. **矩形检测**: 使用霍夫变换检测画面中的矩形/四边形
2. **颜色过滤**: 检测区域内绿色像素比例
3. **位置规则**: 食槽通常在地面/固定位置

### 实现步骤
```python
import cv2
import numpy as np

def detect_feeding_trough(image):
    # 1. 边缘检测
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    
    # 2. 轮廓检测
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    troughs = []
    for cnt in contours:
        # 3. 近似多边形
        approx = cv2.approxPolyDP(cnt, 0.02 * cv2.arcLength(cnt, True), True)
        
        # 4. 矩形筛选（4边形，面积适中）
        if len(approx) == 4:
            area = cv2.contourArea(cnt)
            if area > 1000:  # 最小面积阈值
                # 5. 提取区域
                x, y, w, h = cv2.boundingRect(approx)
                roi = image[y:y+h, x:x+w]
                
                # 6. 绿色像素检测
                hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
                lower_green = np.array([35, 40, 40])
                upper_green = np.array([85, 255, 255])
                mask = cv2.inRange(hsv, lower_green, upper_green)
                green_ratio = np.sum(mask > 0) / (w * h)
                
                # 7. 食槽判断：绿色比例10-60%
                if 0.1 < green_ratio < 0.6:
                    troughs.append({
                        'bbox': [x, y, w, h],
                        'green_ratio': green_ratio
                    })
    
    return troughs
```

### 预期效果
- 食槽检测准确率: 70-80%
- 无需标注数据

---

## Day 5-6: 饮水检测（水盆检测 + 姿态规则）

### 方案
**水盆检测**: 类似食槽，检测蓝色/反光区域  
**饮水姿态**: 基于林麝位置 + 水盆位置规则判断

### 检测逻辑
```python
def detect_water_basin(image):
    # 1. 检测蓝色区域（水盆常见颜色）
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # 蓝色范围
    lower_blue = np.array([90, 50, 50])
    upper_blue = np.array([130, 255, 255])
    mask = cv2.inRange(hsv, lower_blue, upper_blue)
    
    # 2. 轮廓检测
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    basins = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 500:
            x, y, w, h = cv2.boundingRect(cnt)
            basins.append({'bbox': [x, y, w, h]})
    
    return basins


def is_drinking(animal_bbox, basin_bbox, distance_threshold=50):
    """判断是否在饮水：动物与水盆距离"""
    # 计算中心点距离
    ax = animal_bbox[0] + animal_bbox[2] / 2
    ay = animal_bbox[1] + animal_bbox[3] / 2
    bx = basin_bbox[0] + basin_bbox[2] / 2
    by = basin_bbox[1] + basin_bbox[3] / 2
    
    distance = np.sqrt((ax - bx)**2 + (ay - by)**2)
    return distance < distance_threshold
```

---

## Day 7: 运动量计算 + 集成测试

### 运动量计算
```python
def calculate_movement(boxes_current, boxes_previous, iou_threshold=0.5):
    """
    计算运动量：基于检测框位移
    """
    total_movement = 0
    
    for curr in boxes_current:
        # 找到匹配的上一帧框（IOU匹配）
        best_iou = 0
        best_prev = None
        
        for prev in boxes_previous:
            iou = compute_iou(curr, prev)
            if iou > best_iou:
                best_iou = iou
                best_prev = prev
        
        if best_iou > iou_threshold:
            # 计算位移
            cx1, cy1 = get_center(curr)
            cx2, cy2 = get_center(best_prev)
            displacement = np.sqrt((cx1 - cx2)**2 + (cy1 - cy2)**2)
            total_movement += displacement
    
    return total_movement
```

---

## 技术栈

```python
# requirements.txt
ultralytics>=8.0.0      # YOLOv8
opencv-python>=4.8.0    # CV处理
numpy>=1.24.0           # 数值计算
scikit-image>=0.21.0    # 图像处理
```

---

## 预期成果

| 模块 | 方法 | 预期mAP/准确率 | 数据需求 |
|------|------|---------------|---------|
| 林麝检测 | YOLOv8 COCO迁移 | mAP@0.5: 0.65 | 0张标注 |
| 食槽检测 | CV矩形+颜色 | 准确率: 75% | 0张标注 |
| 饮水检测 | CV颜色+规则 | 准确率: 70% | 0张标注 |
| 运动量 | IOU追踪+位移 | 相对误差<15% | 0张标注 |

---

## 下一步

1. **Day 1**: 实现林麝检测（YOLOv8 COCO）
2. **Day 2**: 测试并优化检测阈值
3. **Day 3**: 实现食槽检测（CV方法）
4. **Day 4**: 测试食槽检测准确率
5. **Day 5**: 实现饮水检测
6. **Day 6**: 实现运动量计算
7. **Day 7**: 集成测试 + 汇报

---

**开始时间**: 2026-03-12  
**汇报时间**: 2026-03-19（明早）
