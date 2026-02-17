# Anomaly Detector - 无监督异常检测服务

基于统计学习的动态基线异常检测系统，用于林麝活动量异常检测。

## 核心算法

### 1. 动态基线学习

```
基线统计量 = f(最近7天历史数据)

包括：
- 基本统计：均值、中位数、标准差、方差、极差
- 百分位数：P25、P50、P75、P90、P95、P99
- 分布特征：偏度、峰度、变异系数(CV)
- IQR边界：用于异常值检测
```

### 2. 异常检测方法

#### 方法1: Z-Score (标准分数)

```
Z = (当前值 - 均值) / 标准差

阈值：
- |Z| > 2.5: 警告 (warning)
- |Z| > 3.5: 严重 (critical)
```

#### 方法2: IQR (四分位距)

```
IQR = P75 - P25
下界 = P25 - 1.5 × IQR
上界 = P75 + 1.5 × IQR

当前值超出边界 → 异常
```

#### 方法3: 极端百分位

```
当前值 > P99 或 当前值 < P1 → 异常
```

### 3. 异常评分

```
异常评分 = min(100, |Z-Score| / 2.5 × 50)

0-30: 正常
30-60: 警告
60-100: 严重
```

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                    数据收集层                             │
│  Data Collector (从摄像头API抓取ISAPI事件)                │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    存储层                                 │
│  InfluxDB (raw_events / activity_metrics)               │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    异常检测层                             │
│  1. CalculateBaseline() - 计算基线统计量                  │
│  2. DetectAnomaly() - 检测异常                           │
│  3. UpdateBaseline() - 定时更新基线                       │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    应用层                                 │
│  告警通知 / 管理后台展示 / 小程序推送                      │
└─────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 安装依赖

```bash
cd backend/services/anomaly-detector
go mod download
```

### 2. 启动InfluxDB

```bash
docker run -d \
  -p 8086:8086 \
  -v influxdb-data:/var/lib/influxdb2 \
  influxdb:2.7
```

### 3. 运行测试

```bash
go run scheduler.go
```

输出示例：
```
=== 无监督异常检测算法测试 ===

【基线统计结果】
样本数: 168
平均值: 32.15
中位数: 28.50
标准差: 18.42
最小值: 10.05
最大值: 78.92
P25: 18.20, P75: 45.80, IQR: 27.60
变异系数: 0.57
偏度: 0.82, 峰度: -0.34

【异常检测测试】
✅ Value: 32.15 | Z: 0.00 | Level: normal | Score: 0.0 | Method: none
   活动量正常

✅ Value: 50.57 | Z: 1.00 | Level: normal | Score: 0.0 | Method: none
   活动量正常

🚨 Value: 87.42 | Z: 3.00 | Level: warning | Score: 60.0 | Method: z_score
   活动量异常偏高: 87.4 vs 基线32.2

🚨 Value: -23.11 | Z: -3.00 | Level: critical | Score: 60.0 | Method: z_score
   活动量异常偏低: -23.1 vs 基线32.2
```

### 4. 运行完整调度器

```bash
export INFLUX_URL=http://localhost:8086
export INFLUX_TOKEN=your-token
go run scheduler.go
```

## API 使用

### 计算基线

```go
detector := NewAnomalyDetector(influxURL, influxToken)

// 计算摄像头基线
baseline, err := detector.CalculateBaseline(ctx, "CAM_001", "tenant_001")

fmt.Printf("均值: %.2f\n", baseline.Mean)
fmt.Printf("标准差: %.2f\n", baseline.StdDev)
fmt.Printf("P95: %.2f\n", baseline.P95)
```

### 检测异常

```go
// 检测当前值是否异常
result, err := detector.DetectAnomaly("CAM_001", "tenant_001", "shed_A1", 75.5)

if result.AnomalyLevel != "normal" {
    log.Printf("异常! 等级: %s, 评分: %.1f", 
        result.AnomalyLevel, result.AnomalyScore)
    log.Printf("Z-Score: %.2f, 百分位: %.1f%%", 
        result.ZScore, result.Percentile)
}
```

### 批量检测

```go
// 检测租户下所有摄像头
anomalies, err := detector.BatchDetect(ctx, "tenant_001", 5*time.Minute)

for _, a := range anomalies {
    if a.AnomalyLevel != "normal" {
        fmt.Printf("%s: %s (%.1f)\n", 
            a.CameraID, a.AnomalyLevel, a.AnomalyScore)
    }
}
```

## 调度策略

| 任务 | 频率 | 说明 |
|------|------|------|
| 数据收集 | 30秒 | 从摄像头API拉取事件 |
| 异常检测 | 5分钟 | 基于基线检测异常 |
| 基线更新 | 1小时 | 滚动更新7天基线 |
| 日报生成 | 24小时 | 生成每日统计报表 |

## 基线统计指标说明

| 指标 | 用途 |
|------|------|
| Mean | 平均活动水平 |
| Median | 中位数（抗异常值干扰） |
| StdDev | 活动量波动程度 |
| CV | 变异系数（标准化波动） |
| P95/P99 | 正常活动上限参考 |
| IQR | 异常值检测边界 |
| Skewness | 分布偏斜程度 |
| Kurtosis | 分布尾部厚度 |

## 异常类型

| 类型 | 说明 | 可能原因 |
|------|------|----------|
| 活动量骤降 | Z < -2.5 | 疾病、应激、设备故障 |
| 活动量激增 | Z > 2.5 | 受惊、打斗、环境干扰 |
| 持续静止 | 长时间无活动 | 重病、死亡、遮挡 |
| 节律异常 | 昼夜模式改变 | 环境变化、健康问题 |

## 优势

1. **无监督学习**: 无需标注数据，自动学习正常模式
2. **个性化基线**: 每个摄像头独立学习，适应个体差异
3. **动态更新**: 基线随季节/年龄变化自动调整
4. **多维检测**: Z-Score + IQR + 百分位多重验证
5. **可解释性**: 输出Z分数和百分位，便于理解

## 后续优化

1. **时序模型**: 引入LSTM/Prophet预测预期活动量
2. **群体对比**: 同圈舍多摄像头交叉验证
3. **季节调整**: 考虑季节因素的自适应基线
4. **迁移学习**: 相似圈舍间基线迁移
