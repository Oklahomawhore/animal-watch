# 林麝健康监测系统 - 全云端多租户架构设计

## 架构概览

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           接入层 (Load Balancer)                            │
│                    Nginx / AWS ALB / 阿里云SLB                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                          API Gateway (Kong/AWS API GW)                       │
│  • 租户身份认证 (API Key + Tenant ID)                                        │
│  • 限流 (Rate Limiting per Tenant)                                           │
│  • 路由分发                                                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                         消息队列 (Apache Kafka)                              │
│  Topic: hikvision-events-{tenant_id}                                        │
│  • 削峰填谷，处理高并发事件流                                                │
│  • 数据持久化，支持重放                                                       │
│  • 分区并行处理 (Partition per camera group)                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                      计算层 (Kubernetes StatefulSet)                         │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                      │
│  │ Event        │  │ Activity     │  │ Alert        │                      │
│  │ Processor    │  │ Calculator   │  │ Engine       │                      │
│  │ (事件解析)    │  │ (活动量计算)  │  │ (异常检测)    │                      │
│  └──────────────┘  └──────────────┘  └──────────────┘                      │
│                                                                              │
│  • 无状态设计，水平扩展 (HPA)                                                 │
│  • 租户上下文传递 (Tenant Context Propagation)                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                           数据层 (Multi-Tenant)                              │
│                                                                              │
│  ┌──────────────────┐    ┌──────────────────┐                               │
│  │ 时序数据库        │    │ 关系数据库        │                               │
│  │ (InfluxDB/TDengine)│   │ (PostgreSQL)     │                               │
│  │ 活动量数据        │    │ 租户配置/用户     │                               │
│  └──────────────────┘    └──────────────────┘                               │
│                                                                              │
│  租户隔离策略：Schema-per-Tenant + Row Level Security                        │
└─────────────────────────────────────────────────────────────────────────────┘
                                      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│                           应用层 (多租户SaaS)                                 │
│                                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                      │
│  │ 小程序服务    │  │ 管理后台      │  │ 开放API      │                      │
│  │ (微信/支付宝) │  │ (Vue3/React)  │  │ (REST/GraphQL)│                      │
│  └──────────────┘  └──────────────┘  └──────────────┘                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 多租户数据隔离方案

### 方案对比

| 方案 | 隔离级别 | 复杂度 | 成本 | 适用场景 |
|------|---------|--------|------|----------|
| **Schema-per-Tenant** | ⭐⭐⭐ 高 | 中 | 中 | 中小规模，数据敏感 |
| **Database-per-Tenant** | ⭐⭐⭐⭐⭐ 最高 | 高 | 高 | 大客户，合规要求 |
| **Shared DB + RLS** | ⭐⭐ 中 | 低 | 低 | 大规模，成本敏感 |

### 推荐：Schema-per-Tenant + 共享时序数据库

```sql
-- PostgreSQL Schema 设计
-- 每个租户一个Schema
CREATE SCHEMA tenant_farm_001;
CREATE SCHEMA tenant_farm_002;

-- 租户Schema中的表
CREATE TABLE tenant_farm_001.cameras (
    camera_id UUID PRIMARY KEY,
    device_serial VARCHAR(50),
    name VARCHAR(100),
    location JSONB,
    config JSONB,
    created_at TIMESTAMP
);

CREATE TABLE tenant_farm_001.activity_logs (
    id BIGSERIAL,
    camera_id UUID,
    event_time TIMESTAMP,
    activity_score INT,
    event_data JSONB,
    PRIMARY KEY (id, event_time)
) PARTITION BY RANGE (event_time);

-- 时序数据库 (InfluxDB)
-- 使用Tag区分租户
-- measurement: activity_metrics
-- tags: tenant_id, camera_id, shed_id
-- fields: activity_score, motion_count, region_coverage
```

## 事件处理流水线

```
海康摄像头
    ↓ HTTP POST (ISAPI Event)
API Gateway
    ↓ 验证Tenant ID
Kafka (Topic: events-raw)
    ↓ Consumer Group
Event Processor Service
    ↓ 解析XML → JSON
    ↓ 添加租户上下文
Kafka (Topic: events-processed)
    ↓ Consumer Group
Activity Calculator
    ↓ 滑动窗口计算
    ↓ 活动量评分
InfluxDB (存储时序数据)
    ↓
Alert Engine (异常检测)
    ↓
Webhook / 消息推送
```

## 核心服务设计

### 1. Event Processor Service

```go
// 事件处理服务 (Go语言，高并发)
package main

type ISAPIEvent struct {
    TenantID    string    `json:"tenant_id"`
    DeviceID    string    `json:"device_id"`
    CameraID    string    `json:"camera_id"`
    EventType   string    `json:"event_type"`
    Timestamp   time.Time `json:"timestamp"`
    RegionData  []Region  `json:"regions"`
    RawXML      string    `json:"raw_xml"`
}

func ProcessEvent(ctx context.Context, event ISAPIEvent) error {
    // 1. 租户上下文注入
    ctx = WithTenantContext(ctx, event.TenantID)
    
    // 2. 事件去重 (幂等性)
    if isDuplicate(ctx, event) {
        return nil
    }
    
    // 3. 解析区域坐标
    activityRegions := parseRegions(event.RegionData)
    
    // 4. 发送到下游
    return kafkaProducer.Send(ctx, "events-processed", EventMessage{
        TenantID: event.TenantID,
        CameraID: event.CameraID,
        Timestamp: event.Timestamp,
        ActivityRegions: activityRegions,
    })
}
```

### 2. Activity Calculator Service

```python
# 活动量计算服务 (Python，算法灵活性)
from datetime import datetime, timedelta
import pandas as pd
from influxdb_client import InfluxDBClient

class ActivityCalculator:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self.window_size = 300  # 5分钟滑动窗口
        
    def calculate_activity_score(self, camera_id: str, 
                                  start_time: datetime, 
                                  end_time: datetime) -> dict:
        """
        基于ISAPI事件计算活动量评分
        """
        # 查询事件数据
        events = self.query_events(camera_id, start_time, end_time)
        
        if not events:
            return {"score": 0, "level": "idle"}
        
        # 计算指标
        event_count = len(events)
        time_span = (end_time - start_time).total_seconds()
        frequency = event_count / time_span * 60  # 事件/分钟
        
        # 区域覆盖度
        unique_regions = set()
        for event in events:
            unique_regions.update(event.get('regions', []))
        coverage = len(unique_regions)
        
        # 计算评分 (0-100)
        score = min(
            frequency * 5 +           # 频率权重
            coverage * 10 +           # 覆盖权重
            min(event_count, 50),     # 基数
            100
        )
        
        # 分级
        level = self.classify_level(score)
        
        return {
            "tenant_id": self.tenant_id,
            "camera_id": camera_id,
            "timestamp": end_time,
            "score": score,
            "level": level,
            "frequency": frequency,
            "coverage": coverage,
            "event_count": event_count
        }
    
    def classify_level(self, score: int) -> str:
        if score < 20: return "idle"          # 静止
        elif score < 40: return "low"         # 低活动
        elif score < 60: return "moderate"    # 中等活动
        elif score < 80: return "high"        # 高活动
        else: return "very_high"              # 极高活动
```

### 3. Alert Engine (异常检测)

```python
class AnomalyDetector:
    """
    基于统计和规则的异常检测
    """
    
    def detect_activity_anomaly(self, tenant_id: str, 
                                 camera_id: str,
                                 current_score: float) -> list:
        alerts = []
        
        # 1. 获取历史基线 (同时间段7天平均)
        baseline = self.get_baseline(tenant_id, camera_id)
        
        # 2. 骤降检测 (低于基线50%)
        if current_score < baseline * 0.5:
            alerts.append({
                "type": "activity_drop",
                "severity": "high",
                "message": f"活动量骤降，当前{current_score}，基线{baseline}",
                "suggestion": "建议检查林麝健康状况"
            })
        
        # 3. 持续静止检测 (超过2小时无活动)
        last_active = self.get_last_active_time(tenant_id, camera_id)
        if (datetime.now() - last_active).hours > 2:
            alerts.append({
                "type": "prolonged_idle",
                "severity": "medium",
                "message": "圈舍长时间无活动",
                "suggestion": "检查设备或动物状态"
            })
        
        # 4. 异常活跃检测 (高于基线3倍)
        if current_score > baseline * 3:
            alerts.append({
                "type": "abnormal_active",
                "severity": "medium", 
                "message": "异常活跃，可能存在应激",
                "suggestion": "检查环境干扰因素"
            })
        
        return alerts
```

## Kubernetes 部署架构

```yaml
# namespace 按环境划分
apiVersion: v1
kind: Namespace
metadata:
  name: linshe-prod
---
# Event Processor Deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: event-processor
  namespace: linshe-prod
spec:
  replicas: 3  # 水平扩展
  selector:
    matchLabels:
      app: event-processor
  template:
    metadata:
      labels:
        app: event-processor
    spec:
      containers:
      - name: processor
        image: registry.cn-hangzhou.aliyuncs.com/linshe/event-processor:v1.0
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        env:
        - name: KAFKA_BROKERS
          value: "kafka-0.kafka:9092,kafka-1.kafka:9092"
        - name: TENANT_CONTEXT_HEADER
          value: "X-Tenant-ID"
---
# HPA 自动扩缩容
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: event-processor-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: event-processor
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## 多租户安全隔离

### 1. 身份认证

```javascript
// API Gateway 认证中间件
const authenticateTenant = async (req, res, next) => {
    const apiKey = req.headers['x-api-key'];
    const tenantId = req.headers['x-tenant-id'];
    
    // 验证API Key和Tenant ID匹配
    const valid = await verifyTenantKey(apiKey, tenantId);
    if (!valid) {
        return res.status(401).json({ error: 'Invalid credentials' });
    }
    
    // 注入租户上下文
    req.tenantContext = {
        tenantId: tenantId,
        schema: `tenant_${tenantId}`,
        permissions: await getTenantPermissions(tenantId)
    };
    
    next();
};
```

### 2. 数据库层隔离 (PostgreSQL RLS)

```sql
-- 启用行级安全
ALTER TABLE activity_logs ENABLE ROW LEVEL SECURITY;

-- 创建租户隔离策略
CREATE POLICY tenant_isolation_policy ON activity_logs
    USING (tenant_id = current_setting('app.current_tenant')::UUID);

-- 应用层设置租户上下文
SET app.current_tenant = 'tenant_farm_001';
```

## 成本估算 (月)

| 资源 | 规格 | 单价 | 月费用 |
|------|------|------|--------|
| **K8s集群** | 3节点 × 4核8G | ¥200/节点 | ¥600 |
| **Kafka** | 3节点 × 2核4G | ¥150/节点 | ¥450 |
| **PostgreSQL** | 4核8G (RDS) | - | ¥800 |
| **InfluxDB** | 4核8G | - | ¥600 |
| **负载均衡** | ALB | - | ¥100 |
| **公网带宽** | 100Mbps | - | ¥800 |
| **总计** | | | **¥3,350/月** |

> 支持 **50-100个养殖场** (约1000-2000路摄像头)

## 扩展路径

```
阶段1 (0-6个月): 单集群 + Schema隔离
    支持 50 租户
    
阶段2 (6-12个月): 多可用区 + 读写分离
    支持 200 租户
    
阶段3 (12-24个月): 多区域部署 + 边缘缓存
    支持 1000+ 租户
```

这套架构满足你的全云端、可扩展、客户隔离需求吗？需要我详细展开哪个部分？
