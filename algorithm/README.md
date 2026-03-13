# 林麝检测算法 - 冷启动方案

**目标**: 无人工标注，复用已有模型，快速完成冷启动  
**策略**: 迁移学习 + 无监督检测 + 规则引擎

---

## 核心策略

使用**无监督方法** + **迁移学习**，无需7天标注期即可启动检测。

| 模块 | 方法 | 预期准确率 | 数据需求 |
|------|------|-----------|---------|
| 林麝检测 | YOLOv8 COCO迁移 | mAP@0.5: 0.65 | 0张标注 |
| 食槽检测 | CV矩形+颜色分割 | 准确率: 75% | 0张标注 |
| 饮水检测 | CV颜色+规则 | 准确率: 70% | 0张标注 |
| 运动量计算 | IOU追踪+位移 | 相对误差<15% | 0张标注 |
| 异常检测 | 统计学习+动态基线 | 召回率>80% | 0张标注 |

---

## 快速开始

### 1. 环境安装

```bash
cd lin-she-health-monitor/algorithm

# 使用 uv 安装依赖
uv pip install -r requirements.txt

# 或使用 pip
pip install -r requirements.txt
```

### 2. 运行检测

```bash
# 林麝检测（使用YOLOv8 COCO预训练权重）
python scripts/detect_animal.py --image data/images/test.jpg --output output/

# 食槽检测
python scripts/detect_trough.py --image data/images/test.jpg --output output/

# 运动量计算
python scripts/calculate_activity.py --video data/videos/test.mp4 --output output/

# 完整流程
python scripts/pipeline.py --config config/cold_start.yaml
```

---

## 算法模块说明

### 1. 林麝检测 (detect_animal.py)

**原理**: 使用YOLOv8 COCO预训练权重，检测动物类别后通过规则过滤

```python
from scripts.detect_animal import AnimalDetector

detector = AnimalDetector(model_path='yolov8n.pt')
results = detector.detect('image.jpg')

# 返回格式
[
  {
    'bbox': [x1, y1, x2, y2],
    'confidence': 0.85,
    'class': 'animal',
    'estimated_size': 'medium'  # 基于bbox估算体型
  }
]
```

### 2. 食槽检测 (detect_trough.py)

**原理**: 霍夫变换检测矩形 + HSV颜色空间绿色像素分析

```python
from scripts.detect_trough import TroughDetector

detector = TroughDetector()
troughs = detector.detect('image.jpg')

# 返回格式
[
  {
    'bbox': [x, y, w, h],
    'green_ratio': 0.45,  # 绿色像素占比
    'status': 'has_food'  # has_food / empty / unknown
  }
]
```

### 3. 运动量计算 (calculate_activity.py)

**原理**: IOU匹配追踪 + 中心点位移计算

```python
from scripts.calculate_activity import ActivityCalculator

calculator = ActivityCalculator()
activity_score = calculator.calculate(video_path='video.mp4')

# 返回格式
{
  'total_movement': 1250.5,  # 总位移像素
  'avg_movement': 15.2,      # 平均每帧位移
  'activity_level': 'high',  # high / medium / low
  'score': 78                # 0-100活动评分
}
```

### 4. 异常检测 (detect_anomaly.py)

**原理**: 动态基线 + 统计学习（Z-Score + IQR）

```python
from scripts.detect_anomaly import AnomalyDetector

detector = AnomalyDetector(window_size=60)  # 60分钟窗口
is_anomaly, info = detector.detect(current_activity=25.0)

# 返回格式
{
  'is_anomaly': True,
  'type': 'activity_low',
  'z_score': -2.8,
  'baseline': 45.0,
  'threshold': 30.0
}
```

---

## 目录结构

```
algorithm/
├── scripts/              # 算法脚本
│   ├── detect_animal.py      # 林麝检测
│   ├── detect_trough.py      # 食槽检测
│   ├── detect_water.py       # 饮水检测
│   ├── calculate_activity.py # 运动量计算
│   ├── detect_anomaly.py     # 异常检测
│   └── pipeline.py           # 完整流程
├── models/               # 模型文件
│   └── yolov8n.pt       # YOLOv8预训练权重
├── data/                 # 数据目录
│   ├── images/          # 测试图片
│   └── videos/          # 测试视频
├── output/               # 输出目录
├── config/               # 配置文件
│   └── cold_start.yaml
├── requirements.txt      # Python依赖
└── README.md            # 本文档
```

---

## 性能指标

| 指标 | 目标值 | 实际值 |
|------|--------|--------|
| 林麝检测 mAP@0.5 | > 0.60 | 待测试 |
| 食槽检测准确率 | > 70% | 待测试 |
| 运动量计算误差 | < 20% | 待测试 |
| 异常检测召回率 | > 80% | 待测试 |
| 单帧处理时间 | < 100ms | 待测试 |

---

## 下一步优化

1. **收集真实数据**: 抓拍100-500张现场图片验证算法效果
2. **微调模型**: 如有条件，用50-100张标注数据微调YOLOv8
3. **参数调优**: 根据实际场景调整颜色阈值、检测区域等参数
4. **集成部署**: 将算法集成到后端服务，提供API接口

---

## 参考

- [YOLOv8 Documentation](https://docs.ultralytics.com/)
- [OpenCV Documentation](https://docs.opencv.org/)
- [冷启动方案详细设计](../docs/COLD_START_PLAN.md)
