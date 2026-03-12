# 动物检测算法开发方案

## 目标
开发林麝检测算法，能够：
1. 检测视频/图片中的林麝
2. 统计数量
3. 输出检测框和置信度

---

## 方案对比

### 方案A: YOLOv8 (推荐)

**优点:**
- 速度快 (实时检测)
- 准确率高
- 部署简单
- 社区活跃

**缺点:**
- 需要标注数据
- 对遮挡和小目标有一定挑战

**适用场景:** 固定摄像头，光线变化不大的圈舍环境

### 方案B: 传统CV + 深度学习

**优点:**
- 不需要大量标注
- 对固定场景优化效果好

**缺点:**
- 开发复杂
- 调参困难

**适用场景:** 背景相对固定的室内环境

---

## 推荐方案: YOLOv8

### 开发步骤

#### Step 1: 环境准备
```bash
# 创建算法开发环境
conda create -n animal-detection python=3.10
conda activate animal-detection

# 安装依赖
pip install ultralytics opencv-python numpy pillow requests
```

#### Step 2: 数据收集
```python
# 使用已获取的 Token 下载测试图片
import requests

APP_TOKEN = "at-wna4ifY5raIKfMjOgybhp4cJik_63ZMJ09MoSY0T"
USER_TOKEN = "ut-39605109-9f5f-4766-aeb7-ee7be1a92cc8"

def capture_image(device_serial, channel_no=1):
    """抓拍设备图片"""
    url = "https://open-api.hikiot.com/device/camera/v1/capture"
    headers = {
        "App-Access-Token": APP_TOKEN,
        "User-Access-Token": USER_TOKEN,
    }
    data = {
        "deviceSerial": device_serial,
        "channelNo": channel_no
    }
    resp = requests.post(url, headers=headers, json=data)
    result = resp.json()
    if result.get("code") == 0:
        return result["data"]["picUrl"]
    return None

# 测试抓拍
pic_url = capture_image("GF6830765")
print(f"抓拍图片URL: {pic_url}")
```

#### Step 3: 数据标注
- 工具: LabelImg / CVAT / Makesense.ai
- 格式: YOLO format (class x_center y_center width height)
- 目标: 100-500张标注图片

#### Step 4: 模型训练
```python
from ultralytics import YOLO

# 加载预训练模型
model = YOLO('yolov8n.pt')  # nano版本，速度快

# 训练
model.train(
    data='lin-she.yaml',  # 数据集配置文件
    epochs=100,
    imgsz=640,
    batch=16,
    device=0  # GPU
)
```

#### Step 5: 模型部署
```python
# 加载训练好的模型
model = YOLO('runs/detect/train/weights/best.pt')

# 推理
def detect_animals(image_path):
    results = model(image_path)
    detections = []
    for r in results:
        boxes = r.boxes
        for box in boxes:
            detections.append({
                'class': 'lin-she',
                'confidence': float(box.conf),
                'bbox': box.xyxy.tolist()[0]
            })
    return detections
```

---

## 草量分析算法

### 方案: 颜色分割 + 像素统计

```python
import cv2
import numpy as np

def analyze_grass(image_path):
    """分析草量"""
    img = cv2.imread(image_path)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # 绿色范围
    lower_green = np.array([35, 40, 40])
    upper_green = np.array([85, 255, 255])
    
    # 创建掩码
    mask = cv2.inRange(hsv, lower_green, upper_green)
    
    # 计算绿色像素比例
    green_ratio = np.sum(mask > 0) / mask.size
    
    # 判断草量
    if green_ratio > 0.3:
        return '充足', green_ratio
    elif green_ratio > 0.15:
        return '中等', green_ratio
    else:
        return '不足', green_ratio
```

---

## 测试步骤

### 1. 环境测试
```bash
python -c "import torch; print(torch.cuda.is_available())"
python -c "import cv2; print(cv2.__version__)"
```

### 2. API 测试
```bash
# 测试设备列表
curl -H "App-Access-Token: at-wna4ifY5raIKfMjOgybhp4cJik_63ZMJ09MoSY0T" \
     -H "User-Access-Token: ut-39605109-9f5f-4766-aeb7-ee7be1a92cc8" \
     "https://open-api.hikiot.com/device/v1/page?page=1&size=10"

# 测试抓拍
curl -X POST \
     -H "App-Access-Token: at-wna4ifY5raIKfMjOgybhp4cJik_63ZMJ09MoSY0T" \
     -H "User-Access-Token: ut-39605109-9f5f-4766-aeb7-ee7be1a92cc8" \
     -H "Content-Type: application/json" \
     -d '{"deviceSerial": "GF6830765", "channelNo": 1}' \
     "https://open-api.hikiot.com/device/camera/v1/capture"
```

### 3. 算法测试
```python
# 下载测试图片并运行检测
python test_detection.py --device GF6830765 --output result.jpg
```

---

## 下一步

1. 等待 PR 合并
2. 搭建算法开发环境
3. 批量下载测试图片
4. 开始数据标注
