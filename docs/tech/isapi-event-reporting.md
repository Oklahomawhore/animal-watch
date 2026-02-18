# ISAPI事件上报接口实现说明

## 一、整体数据流

```
海康摄像头(ISAPI)
       ↓  HTTP GET /ISAPI/Event/notification/alertStream
Data Collector (Go)
       ↓  写入InfluxDB + 可选发送到Kafka
InfluxDB (raw_events bucket)
       ↓  Kafka Consumer 消费
Event Processor (Go)
       ↓  5分钟滑动窗口计算
活动量指标 (activity_metrics bucket)
       ↓
异常检测 / 告警系统
```

---

## 二、Data Collector 实现

### 2.1 ISAPI接口调用

```go
// 请求海康摄像头事件流
URL: http://{ip}:{port}/ISAPI/Event/notification/alertStream
Method: GET
Auth: Basic Auth (username/password)

// 查询参数
startTime: 2024-01-15T08:00:00+08:00
endTime:   2024-01-15T08:01:00+08:00
```

### 2.2 ISAPI事件XML格式

```xml
<EventNotificationAlert version="2.0">
    <ipAddress>192.168.1.101</ipAddress>
    <portNo>80</portNo>
    <protocol>HTTP</protocol>
    <macAddress>44:19:b6:66:ab:27</macAddress>
    <channelID>1</channelID>
    <dateTime>2024-01-15T08:30:25+08:00</dateTime>
    <activePostCount>1</activePostCount>
    <eventType>linedetection</eventType>  <!-- 越线检测 -->
    <eventState>active</eventState>
    <DetectionRegionList>
        <DetectionRegion>
            <regionID>1</regionID>
            <sensitivity>50</sensitivity>  <!-- 灵敏度0-100 -->
            <RegionCoordinatesList>
                <RegionCoordinates>
                    <positionX>100</positionX>
                    <positionY>200</positionY>
                </RegionCoordinates>
                <!-- 更多坐标点... -->
            </RegionCoordinatesList>
        </DetectionRegion>
    </DetectionRegionList>
</EventNotificationAlert>
```

### 2.3 存储结构 (InfluxDB)

```go
// Measurement: hikvision_events
Point: {
    Measurement: "hikvision_events",
    Tags: {
        tenant_id:  "tenant_001",
        shed_id:    "shed_A1",
        camera_id:  "CAM_001",
        event_type: "linedetection",
    },
    Fields: {
        region_count:      1,        // 触发区域数
        sensitivity:       50,       // 灵敏度
        active_post_count: 1,
        ip_address:        "192.168.1.101",
    },
    Timestamp: 2024-01-15T08:30:25Z
}
```

### 2.4 采集频率

```go
collectInterval: 30 * time.Second  // 每30秒轮询一次

// 每次查询时间范围
startTime: now - 2*collectInterval  // 稍微重叠避免遗漏
endTime:   now
```

---

## 三、Event Processor 实现

### 3.1 5分钟滑动窗口计算

```go
type ActivityWindow struct {
    CameraID   string
    TenantID   string
    ShedID     string
    Events     []ProcessedEvent  // 窗口内所有事件
    StartTime  time.Time         // 窗口开始时间
    LastUpdate time.Time         // 最后更新时间
}

windowDuration: 5 * time.Minute  // 每个窗口5分钟
```

### 3.2 活动量评分算法

```
活动量评分 = min(100,
    频率(次/分) × 2 +        // 40分权重
    事件数 × 0.6 +           // 30分权重
    区域数 × 5 +             // 20分权重
    灵敏度/10)               // 10分权重
```

### 3.3 存储结构 (InfluxDB)

```go
// Measurement: activity_metrics
Point: {
    Measurement: "activity_metrics",
    Tags: {
        tenant_id:     "tenant_001",
        camera_id:     "CAM_001",
        shed_id:       "shed_A1",
    },
    Fields: {
        activity_score:   45.5,      // 0-100 活动量评分
        activity_level:   "moderate", // idle/low/moderate/high/very_high
        event_count:      12,         // 5分钟内事件数
        event_frequency:  2.4,        // 次/分钟
        region_coverage:  3,          // 覆盖区域数
        avg_sensitivity:  52.5,       // 平均灵敏度
    },
    Timestamp: 2024-01-15T08:30:00Z
}
```

---

## 四、关键配置

### 4.1 摄像头配置 (cameras.json)

```json
[
  {
    "id": "CAM_001",
    "tenant_id": "tenant_001",
    "shed_id": "shed_A1",
    "ip": "192.168.1.101",
    "port": 80,
    "username": "admin",
    "password": "admin123",
    "protocol": "http"
  }
]
```

### 4.2 环境变量

```bash
# Data Collector
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=your-token
USE_MOCK=true  # 是否使用模拟数据

# Event Processor
KAFKA_BROKERS=localhost:9092
KAFKA_INPUT_TOPIC=hikvision-events-raw
KAFKA_OUTPUT_TOPIC=activity-metrics
INFLUX_URL=http://localhost:8086
INFLUX_TOKEN=your-token
INFLUX_ORG=linshe
INFLUX_BUCKET=activity_metrics
```

---

## 五、数据上报特点

| 特点 | 说明 |
|------|------|
| **事件驱动** | 只有检测到运动时才上报，非连续视频流 |
| **数据量小** | 单个事件XML约1KB，100摄像头/天约10MB |
| **实时性** | 延迟约30秒（采集间隔）+ 5分钟窗口 |
| **低带宽** | 相比RTSP视频流，带宽降低99.6% |
| **私有化** | 数据直接存入本地InfluxDB，不上公网 |

---

## 六、与V3.0剩料量化的关系

### 当前方案局限性
- 只能检测"有没有运动"
- 无法区分"麝在运动"还是"风吹草动"
- 无法量化"食槽里还剩多少草"

### V3.0升级方向
```
当前: ISAPI事件 → 运动检测 → 活动量评分
         ↓
V3.0: RTSP截图 → 图像分析 → 草量覆盖率
         ↓
融合: 运动检测 + 草量变化 = 确认进食事件
```

**保留现有架构，新增图像分析模块**
