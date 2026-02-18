# 林麝食量监控 MVP

快速验证剩料量化技术方案的原型系统。

## 目录结构

```
mvp/
├── grass_monitor.py           # 核心食量分析算法 (OpenCV)
├── hikcloud_grass_monitor.py  # 海康云 API 集成
├── README.md                  # 本文档
└── requirements.txt           # Python 依赖
```

## 快速开始

### 1. 安装依赖

```bash
cd mvp
pip install -r requirements.txt
```

### 2. 运行演示模式

无需真实摄像头，使用模拟数据测试算法：

```bash
python grass_monitor.py demo
```

输出示例：
```
============================================================
林麝食量监控系统 MVP - 演示模式
============================================================

[1] 生成模拟基准图...
   ✓ 基准图已生成

[2] 初始化监控系统...
   ✓ 监控器已初始化

[3] 模拟进食过程...
   [ 1] 覆盖率:  95.0% | 状态: high     | 置信度: 0.85
   [ 2] 覆盖率:  80.0% | 状态: high     | 置信度: 0.82
   [ 3] 覆盖率:  65.0% | 状态: medium   | 置信度: 0.78
   [ 4] 覆盖率:  50.0% | 状态: medium   | 置信度: 0.80
   ...
   [10] 覆盖率:   1.0% | 状态: empty    | 置信度: 0.88

[4] 生成监控报告...
   监控报告 (trough_A01):
   - 记录数: 10
   - 平均覆盖率: 42.8%
   - 最低/最高: 1.0% / 95.0%
   - 当前状态: 1.0%
   - 建议: 食槽已空，建议立即补充饲料

[5] 生成趋势图...
   ✓ 趋势图已保存: demo/output/trend.png
```

### 3. 连接真实摄像头 (海康云)

#### 3.1 配置食槽信息

编辑 `cloud_troughs.json`：

```json
{
  "trough_A01": {
    "device_id": "D123456789",
    "channel_no": 1,
    "name": "A01号食槽",
    "roi": [200, 150, 400, 300],
    "empty_green_ratio": 0.05,
    "full_green_ratio": 0.60
  }
}
```

- `device_id`: 海康云设备ID
- `roi`: 食槽区域 [x, y, width, height]
- `*_green_ratio`: 校准值（通过校准步骤获取）

#### 3.2 校准基准图

**步骤1**: 清空食槽，拍摄空槽照片
```bash
python hikcloud_grass_monitor.py \
  --ak YOUR_AK \
  --sk YOUR_SK \
  --device-id D123456789 \
  --calibrate empty \
  --trough-id trough_A01
```

**步骤2**: 加满饲料，拍摄满槽照片
```bash
python hikcloud_grass_monitor.py \
  --ak YOUR_AK \
  --sk YOUR_SK \
  --device-id D123456789 \
  --calibrate full \
  --trough-id trough_A01
```

#### 3.3 启动监控

```python
from hikcloud_grass_monitor import CloudGrassMonitor

monitor = CloudGrassMonitor(
    ak="2023987187632369716",
    sk="MIICdgIBADANBgkqhkiG9w0BAQE..."
)

# 分析单个食槽
result = monitor.analyze_trough("trough_A01")
print(f"覆盖率: {result['coverage_ratio']}%")
print(f"状态: {result['status']}")
```

## 算法说明

### 核心原理

使用 **HSV 色彩空间** 检测绿色像素占比：

```
食槽图像 → 提取 ROI → HSV 转换 → 绿色掩码 → 计算占比 → 归一化到 0-100%
```

### 覆盖率计算公式

```
coverage = (current_green - empty_green) / (full_green - empty_green) × 100%
```

### 状态判定

| 覆盖率 | 状态 | 说明 |
|--------|------|------|
| < 10% | empty | 空槽，需补充 |
| 10-30% | low | 少量剩余 |
| 30-60% | medium | 中等量 |
| 60-90% | high | 较多 |
| > 90% | full | 满槽 |

## 算法优缺点

### ✅ 优点
- **成本低**: 无需 AI 训练，OpenCV 即可
- **速度快**: 单张图分析 < 100ms
- **可解释**: 绿色像素占比直观可见
- **易调试**: 可输出中间结果可视化

### ⚠️ 局限
- **受光照影响**: 强光/阴影会影响绿色检测
- **草料类型依赖**: 不同草料绿色范围不同
- **无法区分个体**: 只能监测食槽整体

## 迭代路线图

### Phase 1 (当前 MVP)
- ✅ HSV 绿色检测
- ✅ 基准图比对
- ✅ 简单状态判定

### Phase 2 (优化)
- [ ] 光照补偿算法
- [ ] 多时相变化检测
- [ ] 异常值过滤

### Phase 3 (深度学习)
- [ ] 语义分割模型 (U-Net)
- [ ] 草料类型自适应
- [ ] 个体识别辅助

## 调试技巧

### 1. 可视化 ROI 区域

```python
from grass_monitor import GrassCoverageAnalyzer, TroughConfig

config = TroughConfig(...)
analyzer = GrassCoverageAnalyzer(config)

# 分析并可视化
result = analyzer.analyze("current.jpg")
output = analyzer.visualize("current.jpg", result, "output.jpg")
```

### 2. 调整绿色检测范围

如果检测效果不佳，调整 HSV 范围：

```python
# grass_monitor.py 中修改
self.lower_green = np.array([35, 40, 40])  # H, S, V 下限
self.upper_green = np.array([85, 255, 255])  # H, S, V 上限
```

### 3. 查看中间结果

```python
# 保存绿色掩码
hsv = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
mask = cv2.inRange(hsv, lower_green, upper_green)
cv2.imwrite("mask.jpg", mask)  # 查看哪些像素被识别为绿色
```

## 常见问题

**Q: 为什么检测结果是负数或超过100%？**
A: 基准图校准不准确，重新执行校准步骤。

**Q: 夜间/低光照下效果如何？**
A: 效果会下降，建议开启摄像头红外补光。

**Q: 能否检测非绿色饲料？**
A: 需要调整 HSV 范围或使用深度学习方案。

## 联系

如有问题，请联系开发团队。
