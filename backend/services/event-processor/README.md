# Event Processor - 事件处理器

林麝健康监测系统核心组件，负责处理海康ISAPI事件并计算活动量。

## 功能特性

- ✅ **ISAPI事件解析**: 解析海康摄像头XML事件格式
- ✅ **滑动窗口计算**: 5分钟滑动窗口实时计算活动量
- ✅ **多租户支持**: 基于Kafka Headers的租户隔离
- ✅ **高并发处理**: Go语言实现，支持水平扩展
- ✅ **时序存储**: 自动写入InfluxDB
- ✅ **事件模拟器**: 支持生成测试数据

## 活动量算法

### 计算公式

```
活动量评分 = min(100, 
    频率分 + 数量分 + 区域分 + 灵敏度分)

频率分 = min(频率(次/分钟) × 2, 40)
数量分 = min(事件数量 × 0.6, 30)
区域分 = 覆盖区域数 × 5
灵敏度分 = 平均灵敏度 / 100 × 10
```

### 活动等级

| 评分 | 等级 | 说明 |
|------|------|------|
| 0-15 | idle | 静止 |
| 15-35 | low | 低活动 |
| 35-55 | moderate | 中等活动 |
| 55-80 | high | 高活动 |
| 80-100 | very_high | 极高活动 |

## 快速开始

### 1. 安装依赖

```bash
cd backend/services/event-processor
go mod download
```

### 2. 启动依赖服务

```bash
# 使用 Docker Compose 启动 Kafka 和 InfluxDB
docker-compose up -d
```

### 3. 运行服务

```bash
export KAFKA_BROKERS=localhost:9092
export INFLUX_URL=http://localhost:8086
export INFLUX_TOKEN=your-token

go run .
```

### 4. 运行测试

```bash
# 单元测试
go test -v

# 基准测试
go test -bench=BenchmarkProcessEvent -benchmem
```

### 5. 生成模拟数据

```bash
go run simulator.go
```

## 事件模拟器

### 支持的活动模式

| 模式 | 说明 | 事件频率 |
|------|------|----------|
| PatternIdle | 静止 | < 5次/小时 |
| PatternLowActivity | 低活动 | 10-30次/小时 |
| PatternNormal | 正常活动 | 50-100次/小时 |
| PatternHighActivity | 高活动 | 150-300次/小时 |
| PatternAbnormalDrop | 异常骤降 | 前高后低 |
| PatternAbnormalSpike | 异常激增 | 前低后高 |

### 生成林麝一天活动数据

```go
sim := NewEventSimulator("CAM_001", "tenant_001", "shed_A1")
events := sim.GenerateDayData()
```

活动模式模拟真实林麝作息：
- 06:00-09:00: 清晨进食（高活动）
- 09:00-12:00: 上午休息（低活动）
- 12:00-14:00: 午间进食（中等活动）
- 14:00-17:00: 下午休息（低活动）
- 17:00-19:00: 傍晚进食（高活动）
- 19:00-06:00: 夜间休息（静止）

## API 示例

### ISAPI 事件格式

```xml
<?xml version="1.0" encoding="UTF-8"?>
<EventNotificationAlert version="2.0">
    <ipAddress>192.168.1.100</ipAddress>
    <portNo>80</portNo>
    <macAddress>00:23:45:67:89:AB</macAddress>
    <channelID>1</channelID>
    <dateTime>2025-02-16T10:23:15+08:00</dateTime>
    <activePostCount>3</activePostCount>
    <eventType>motionDetection</eventType>
    <eventState>active</eventState>
    <DetectionRegionList>
        <DetectionRegion>
            <regionID>1</regionID>
            <sensitivity>80</sensitivity>
            <RegionCoordinatesList>
                <RegionCoordinates>
                    <positionX>120</positionX>
                    <positionY>200</positionY>
                </RegionCoordinates>
            </RegionCoordinatesList>
        </DetectionRegion>
    </DetectionRegionList>
</EventNotificationAlert>
```

### 输出指标格式

```json
{
  "tenant_id": "tenant_001",
  "camera_id": "00:23:45:67:89:AB_ch1",
  "shed_id": "shed_A1",
  "timestamp": "2025-02-16T10:25:00Z",
  "window_start": "2025-02-16T10:20:00Z",
  "window_end": "2025-02-16T10:25:00Z",
  "activity_score": 65.5,
  "activity_level": "high",
  "event_count": 25,
  "event_frequency": 5.0,
  "region_coverage": 3,
  "avg_sensitivity": 75.0
}
```

## 性能指标

- **处理能力**: 10,000+ 事件/秒/实例
- **内存占用**: < 512MB
- **延迟**: P99 < 100ms (事件到指标)
- **水平扩展**: 支持 3-20 实例 (K8s HPA)

## 配置参数

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| KAFKA_BROKERS | localhost:9092 | Kafka地址 |
| KAFKA_INPUT_TOPIC | hikvision-events-raw | 输入Topic |
| KAFKA_OUTPUT_TOPIC | activity-metrics | 输出Topic |
| INFLUX_URL | http://localhost:8086 | InfluxDB地址 |
| INFLUX_TOKEN | - | InfluxDB Token |
| INFLUX_BUCKET | activity_metrics | 存储Bucket |
| WORKER_COUNT | 10 | 并发工作数 |
| BATCH_SIZE | 100 | 批量写入大小 |

## 测试覆盖

```bash
$ go test -v
=== RUN   TestParseISAPIEvent
--- PASS: TestParseISAPIEvent (0.00s)
=== RUN   TestCalculateActivityMetrics
--- PASS: TestCalculateActivityMetrics (0.00s)
=== RUN   TestClassifyActivityLevel
--- PASS: TestClassifyActivityLevel (0.00s)
=== RUN   TestSimulator
--- PASS: TestSimulator (0.00s)
```

## 后续优化方向

1. **异常检测算法**: 基于历史基线的动态阈值
2. **进食行为识别**: 结合区域停留时间的模式识别
3. **个体识别**: 集成边缘AI设备的特征数据
4. **实时告警**: WebSocket推送异常事件
