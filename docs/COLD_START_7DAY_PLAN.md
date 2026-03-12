# 林麝检测算法 - 冷启动开发计划（7天）

**策略**: 复用已有模型 + 无监督方法 + 规则引擎  
**目标**: 零人工标注，7天内完成可运行demo  
**当前时间**: 2026-03-12 22:50  
**汇报时间**: 2026-03-19 明早

---

## 📋 方案概览

| 模块 | 方法 | 复用模型/技术 | 标注需求 |
|------|------|--------------|---------|
| **林麝检测** | YOLOv8 COCO迁移 | COCO预训练权重 | 0张 |
| **食槽检测** | CV矩形+颜色分割 | OpenCV传统CV | 0张 |
| **饮水检测** | CV颜色+位置规则 | OpenCV传统CV | 0张 |
| **运动量** | IOU追踪+位移计算 | 自定义算法 | 0张 |

---

## 🗓️ 7天开发计划

### Day 1 (3/12) - 林麝检测基础
**目标**: 实现基于YOLOv8 COCO的林麝检测

**方案**:
- 使用YOLOv8n COCO预训练模型
- 检测动物类别: cat(15), dog(16), horse(17), bear(21), zebra(22), giraffe(23)
- 规则过滤: 面积比3-35%，宽高比0.8-2.5

**代码**: `algorithm/scripts/detect_linshe_coldstart.py`

**预期mAP**: 0.60-0.70（冷启动）

---

### Day 2 (3/13) - 检测优化
**目标**: 优化检测阈值，提高召回率

**方案**:
- 在100张测试图片上验证
- 调整置信度阈值（0.2-0.4）
- 调整面积过滤范围
- 计算初步mAP

---

### Day 3 (3/14) - 食槽检测
**目标**: 实现无监督食槽检测

**方案**:
```python
# 1. 边缘检测 -> 矩形检测
edges = cv2.Canny(gray, 50, 150)
contours = cv2.findContours(edges, ...)

# 2. 四边形筛选
approx = cv2.approxPolyDP(cnt, ...)
if len(approx) == 4:  # 矩形

# 3. 绿色像素检测
hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
mask = cv2.inRange(hsv, lower_green, upper_green)
green_ratio = np.sum(mask > 0) / area

# 4. 食槽判断
if 0.1 < green_ratio < 0.6:  # 有草料
```

**预期准确率**: 70-80%

---

### Day 4 (3/15) - 饮水检测
**目标**: 实现无监督饮水检测

**方案**:
- 水盆检测: 蓝色/反光区域检测
- 饮水判断: 林麝位置与水盆距离 < 阈值

```python
# 蓝色区域检测
lower_blue = np.array([90, 50, 50])
upper_blue = np.array([130, 255, 255])
mask = cv2.inRange(hsv, lower_blue, upper_blue)

# 距离判断
def is_drinking(animal_bbox, basin_bbox):
    distance = compute_center_distance(animal_bbox, basin_bbox)
    return distance < 50  # 像素
```

**预期准确率**: 65-75%

---

### Day 5 (3/16) - 运动量计算
**目标**: 实现运动量检测算法

**方案**:
```python
def calculate_movement(boxes_curr, boxes_prev):
    total_movement = 0
    for curr in boxes_curr:
        # IOU匹配
        best_prev = find_best_match_by_iou(curr, boxes_prev)
        if best_prev:
            # 计算位移
            displacement = distance(curr.center, best_prev.center)
            total_movement += displacement
    return total_movement
```

---

### Day 6 (3/17) - 算法集成
**目标**: 整合所有模块，构建pipeline

**Pipeline**:
```
视频帧 -> 林麝检测 -> 食槽/水盆检测 -> 行为判断 -> 运动量计算
                ↓
         进食判断: 林麝与食槽重叠 + 停留时间
         饮水判断: 林麝与水盆距离 < 阈值
```

---

### Day 7 (3/18) - 测试优化
**目标**: 端到端测试，计算最终mAP

**测试内容**:
1. 100张图片检测测试
2. 视频流实时检测测试
3. 计算各项mAP和准确率
4. 性能优化（FPS > 15）

---

## 📊 预期性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| **林麝检测mAP@0.5** | ≥ 0.60 | COCO迁移冷启动 |
| **林麝检测召回率** | ≥ 0.75 | 减少漏检 |
| **食槽检测准确率** | ≥ 0.70 | CV方法 |
| **饮水检测准确率** | ≥ 0.65 | CV+规则 |
| **运动量误差** | < 20% | 相对误差 |
| **处理速度** | ≥ 15 FPS | 实时性 |

---

## 🛠️ 技术栈

```python
# 核心依赖
ultralytics>=8.0.0      # YOLOv8
opencv-python>=4.8.0    # CV处理
numpy>=1.24.0           # 数值计算

# 运行环境
Python 3.10+
PyTorch 2.0+ (YOLOv8依赖)
CUDA (可选，GPU加速)
```

---

## 📁 代码结构

```
algorithm/
├── scripts/
│   ├── detect_linshe_coldstart.py    # 林麝检测
│   ├── detect_trough_cv.py           # 食槽检测
│   ├── detect_water_cv.py            # 饮水检测
│   ├── calculate_movement.py         # 运动量计算
│   └── run_pipeline.py               # 完整pipeline
├── output/
│   ├── detection/                    # 检测结果
│   └── metrics/                      # 性能指标
└── requirements.txt
```

---

## ✅ 当前进展 (Day 1)

**已完成**:
1. ✅ 冷启动方案设计
2. ✅ YOLOv8 COCO检测代码
3. ✅ 规则过滤逻辑（面积、宽高比）
4. ✅ 批量检测脚本

**待完成**:
- 🟡 环境部署（依赖安装中）
- 🟡 在100张图片上测试
- 🟡 计算初步mAP

---

## 🚀 下一步行动

**今晚**:
1. 完成环境部署
2. 在服务器上运行检测
3. 获取初步检测结果

**明早汇报内容**:
1. 检测代码实现
2. 100张图片检测结果
3. 初步mAP估算
4. Day 2-7详细计划

---

**GitHub分支**: `feature/algorithm-development`  
**代码提交**: `abbad05` - Day 1 cold start implementation
