# 林麝行为检测 - 冷启动方案

## 🎯 核心目标

将视频截图转化为结构化 events 流：
- **movement** - 移动
- **eating** - 进食  
- **drinking** - 饮水
- **resting** - 休息
- **interaction** - 社交互动
- **alert** - 警觉/异常

## 🚀 快速开始

```bash
# 进入算法目录
cd algorithm/

# 运行快速验证
python quick_test.py

# 运行完整演示
python demo_cold_start.py
```

## 📦 依赖安装

```bash
# 使用 uv（推荐）
uv pip install opencv-python numpy scikit-learn ultralytics

# 或使用 pip
pip install opencv-python numpy scikit-learn ultralytics
```

## 🔧 核心组件

### 1. ColdStartDetector - 冷启动检测器

无需预训练模型，使用纯CV方法：

- **背景减除** - 检测移动目标
- **轮廓分析** - 识别动物形状
- **颜色分割** - 检测食槽（绿色）、水盆（蓝色）
- **区域重叠** - 判断进食/饮水行为

```python
from cold_start_detector import ColdStartDetector

detector = ColdStartDetector()
result = detector.process_frame(frame)

print(f"动物数量: {result['animal_count']}")
print(f"运动量: {result['movement_score']}")
print(f"事件: {result['events']}")
```

### 2. EventStreamGenerator - 事件流生成器

将连续帧转换为去重的事件流：

```python
from cold_start_detector import EventStreamGenerator

stream_gen = EventStreamGenerator(detector)
new_events = stream_gen.process_frame(frame)

# 获取统计
stats = stream_gen.get_statistics(time_window=3600)
```

## 📊 事件格式

```json
{
  "event_type": "eating",
  "timestamp": 1710312345.123,
  "confidence": 0.85,
  "bbox": {
    "x1": 100, "y1": 200,
    "x2": 200, "y2": 350,
    "confidence": 0.92
  },
  "metadata": {
    "feeding_roi": [100, 300, 150, 100],
    "overlap_ratio": 0.65
  }
}
```

## 🎨 工作原理

```
视频截图/帧
    ↓
背景减除 → 检测移动目标
    ↓
轮廓分析 → 识别动物（长宽比、面积过滤）
    ↓
颜色分割 → 检测食槽（HSV绿色）、水盆（HSV蓝色）
    ↓
区域重叠计算 → 判断进食/饮水行为
    ↓
运动量计算 → IOU追踪 + 位移统计
    ↓
事件去重 → 基于冷却时间避免重复上报
    ↓
结构化 Events 流
```

## ✅ 验证结果

运行 `quick_test.py` 输出：

```
✅ 检测器初始化成功

模拟处理视频帧序列...
  帧 0: 动物=0, 运动=0.0, 新事件=0
  帧 1: 动物=2, 运动=0.0, 新事件=0
  ...
  帧 6: 动物=2, 运动=20.0, 新事件=1
  帧 8: 动物=1, 运动=28.0, 新事件=1

✅ 共生成 3 个原子事件

事件统计:
  - movement: 1
  - eating: 1
  - resting: 1
```

## 🔮 后续优化

1. **YOLOv8 迁移学习** - 使用 COCO 预训练权重提升检测精度
2. **时序模型** - 添加 LSTM/Transformer 分析行为序列
3. **多目标跟踪** - DeepSORT 实现个体识别
4. **在线学习** - 根据反馈持续优化检测器

## 📁 文件结构

```
algorithm/
├── cold_start_detector.py    # 核心检测器
├── quick_test.py              # 快速验证
├── demo_cold_start.py         # 完整演示
└── README.md                  # 本文档
```

## 📝 注意事项

1. **食槽/水盆区域** - 首次使用需要手动标注或自动检测
2. **光照变化** - 背景减除对光照敏感，可能需要定期更新背景模型
3. **遮挡处理** - 动物重叠时检测精度会下降

## 🏆 优势

- ✅ **零标注成本** - 无需人工标注数据
- ✅ **即开即用** - 无需训练，直接运行
- ✅ **可解释性强** - 基于规则的检测逻辑清晰
- ✅ **易于部署** - 纯Python + OpenCV，无复杂依赖
