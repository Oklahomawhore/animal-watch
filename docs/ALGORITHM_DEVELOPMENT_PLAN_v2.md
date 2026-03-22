# 林麝健康检测 - 算法开发计划 v2.0

**项目**: animal-watch / lin-she-health-monitor  
**分支**: feature/algorithm-development  
**更新时间**: 2026-03-22  
**目标**: 完整算法 Pipeline + 小程序日报系统

---

## 🎯 项目目标更新

基于客户需求，算法系统需要支持：
1. **秒级事件流** - 每1秒抓取摄像头帧，实时检测动物行为
2. **事件入库** - 原子事件（movement/eating/drinking/resting）持久化存储
3. **小时聚合** - 按小时统计活动量、进食、饮水数据
4. **日报生成** - 每日自动生成动物健康日报
5. **小程序展示** - 支持耳标级个体数据查看、诊疗记录、饲养记录

---

## 📊 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        数据采集层                                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │ 海康摄像头   │───▶│ 1s帧抓取    │───▶│ 算法推理    │         │
│  │ (RTSP/截图) │    │ 服务        │    │ 引擎        │         │
│  └─────────────┘    └─────────────┘    └──────┬──────┘         │
└────────────────────────────────────────────────┼────────────────┘
                                                 │
                    ┌────────────────────────────┼────────────────────────────┐
                    │                            │                            │
                    ▼                            ▼                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          数据处理层                                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ 秒级事件入库     │  │ 实时告警检测     │  │ 小时聚合统计     │             │
│  │ (events表)      │  │ (alert_rules)   │  │ (hourly_stats)  │             │
│  └────────┬────────┘  └─────────────────┘  └────────┬────────┘             │
│           │                                          │                      │
│           ▼                                          ▼                      │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │                      日报生成器 (Daily Reporter)                 │       │
│  │  - 24小时数据聚合  - 活动评分计算  - 告警摘要生成                 │       │
│  └──────────────────────────────┬──────────────────────────────────┘       │
└─────────────────────────────────┼───────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          应用层 (小程序 API)                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ GET /mp/daily-  │  │ GET /mp/animals/│  │ POST /mp/care-  │             │
│  │ reports         │  │ :id/daily       │  │ records         │             │
│  │ - 日报列表       │  │ - 动物详情       │  │ - 添加记录       │             │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🗄️ 数据库设计

### 1. 原子事件表 (events)
存储每秒检测到的原子事件

```sql
CREATE TABLE events (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    client_id BIGINT NOT NULL COMMENT '租户ID',
    enclosure_id BIGINT NOT NULL COMMENT '圈舍ID',
    animal_id VARCHAR(32) COMMENT '动物耳标号（个体识别后）',
    camera_id VARCHAR(64) COMMENT '摄像头ID',
    channel_no INT COMMENT '通道号',
    
    event_type VARCHAR(32) NOT NULL COMMENT '事件类型: movement,eating,drinking,resting,alert',
    confidence FLOAT COMMENT '置信度 0-1',
    
    -- 位置信息
    bbox_x1 FLOAT, bbox_y1 FLOAT, bbox_x2 FLOAT, bbox_y2 FLOAT,
    
    metadata JSON COMMENT '事件元数据: overlap_ratio, movement_score等',
    event_time DATETIME(3) NOT NULL COMMENT '事件发生时间（毫秒精度）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_client_time (client_id, event_time),
    INDEX idx_enclosure_time (enclosure_id, event_time),
    INDEX idx_event_type (event_type, event_time)
) COMMENT='原子事件表 - 算法秒级输出';
```

### 2. 小时统计表 (event_hourly_stats)
小时级聚合数据，用于日报生成

```sql
CREATE TABLE event_hourly_stats (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    client_id BIGINT NOT NULL,
    enclosure_id BIGINT NOT NULL,
    animal_id VARCHAR(32) COMMENT '耳标号，为空表示群体统计',
    
    stat_date DATE NOT NULL COMMENT '统计日期',
    hour TINYINT NOT NULL COMMENT '小时 0-23',
    
    -- 活动统计
    movement_count INT DEFAULT 0 COMMENT '移动次数',
    movement_duration INT DEFAULT 0 COMMENT '移动总时长(秒)',
    avg_movement_score FLOAT COMMENT '平均运动强度',
    
    -- 进食统计
    eating_count INT DEFAULT 0 COMMENT '进食次数',
    eating_duration INT DEFAULT 0 COMMENT '进食时长(秒)',
    feed_consumption_percent FLOAT COMMENT '饲料消耗百分比估算',
    
    -- 饮水统计
    drinking_count INT DEFAULT 0 COMMENT '饮水次数',
    drinking_duration INT DEFAULT 0 COMMENT '饮水时长(秒)',
    water_consumption_liters FLOAT COMMENT '饮水量估算',
    
    -- 休息统计
    resting_duration INT DEFAULT 0 COMMENT '休息时长(秒)',
    
    -- 异常统计
    alert_count INT DEFAULT 0 COMMENT '告警次数',
    alert_types JSON COMMENT '告警类型列表',
    
    -- 综合评分
    activity_score INT COMMENT '活动评分 0-100',
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_enclosure_hour (enclosure_id, animal_id, stat_date, hour),
    INDEX idx_date (stat_date, hour)
) COMMENT='小时级事件统计';
```

### 3. 日报表 (daily_reports)
每日生成的动物健康报告

```sql
CREATE TABLE daily_reports (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    client_id BIGINT NOT NULL,
    enclosure_id BIGINT NOT NULL,
    animal_id VARCHAR(32) NOT NULL COMMENT '耳标号如 LS-B2-025',
    report_date DATE NOT NULL COMMENT '报告日期',
    
    -- 基础信息（快照）
    ear_tag VARCHAR(32) COMMENT '耳标号',
    gender VARCHAR(8) COMMENT '雌/雄',
    age VARCHAR(16) COMMENT '年龄如 1岁',
    health_status TINYINT DEFAULT 0 COMMENT '0:绿 1:黄 2:红',
    
    -- 活动数据
    activity_score INT COMMENT '活动评分如 82分',
    activity_level VARCHAR(16) COMMENT '正常/偏低/偏高',
    activity_trend JSON COMMENT '7天趋势 [78,82,75,80,82,79,82]',
    
    -- 进食数据
    feed_main_remain_percent FLOAT COMMENT '主槽剩余%如 35',
    feed_aux_remain_percent FLOAT COMMENT '辅槽剩余%如 72',
    eating_status VARCHAR(32) COMMENT '慢食/正常/快食/未进食',
    
    -- 饮水数据
    water_consumption_liters FLOAT COMMENT '饮水量如 6.8L',
    drinking_status VARCHAR(32) COMMENT '偏多/正常/偏少',
    
    -- 告警摘要
    alerts_summary JSON COMMENT '[{type,message,level,time}]',
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    UNIQUE KEY uk_animal_date (animal_id, report_date),
    INDEX idx_enclosure_date (enclosure_id, report_date)
) COMMENT='动物健康日报';
```

### 4. 诊疗记录表 (medical_records)

```sql
CREATE TABLE medical_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    client_id BIGINT NOT NULL,
    animal_id VARCHAR(32) NOT NULL COMMENT '耳标号',
    
    diagnosis VARCHAR(128) COMMENT '诊断如 肠炎',
    diagnosis_date DATE COMMENT '诊断日期',
    status VARCHAR(16) DEFAULT 'ongoing' COMMENT 'ongoing/resolved/chronic',
    
    medications JSON COMMENT '用药方案: [{name,dosage,route,remain_days}]',
    treatment_day INT DEFAULT 1 COMMENT '治疗第几天',
    
    veterinarian VARCHAR(64) COMMENT '兽医',
    notes TEXT,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_animal (animal_id),
    INDEX idx_status (status, diagnosis_date)
) COMMENT='诊疗记录';
```

### 5. 饲养记录表 (care_records)

```sql
CREATE TABLE care_records (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    client_id BIGINT NOT NULL,
    enclosure_id BIGINT,
    animal_id VARCHAR(32),
    
    record_type VARCHAR(32) NOT NULL COMMENT 'observation/task/measurement/photo',
    category VARCHAR(32) COMMENT '粪便/体温/蹄部/用药/喂食',
    
    content TEXT COMMENT '记录内容',
    status VARCHAR(16) DEFAULT 'completed' COMMENT 'pending/completed/cancelled',
    priority TINYINT DEFAULT 0 COMMENT '0:普通 1:优先 2:紧急',
    
    voice_url VARCHAR(512) COMMENT '语音URL',
    images JSON COMMENT '图片URL列表',
    
    operator_id BIGINT COMMENT '执行人ID',
    operator_name VARCHAR(64) COMMENT '执行人姓名',
    
    scheduled_date DATE COMMENT '计划日期（待办用）',
    completed_at DATETIME COMMENT '完成时间',
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_animal_date (animal_id, created_at),
    INDEX idx_scheduled (scheduled_date, status)
) COMMENT='饲养记录';
```

---

## 🔧 算法 Pipeline 模块

### 模块1: 帧抓取服务 (capture_service.py)

```python
class CaptureService:
    """1秒间隔帧抓取服务"""
    
    async def capture_loop(self):
        """主抓取循环"""
        while True:
            start_time = datetime.now()
            
            # 并行抓取所有摄像头
            tasks = [self.process_camera(cam) for cam in self.cameras]
            await asyncio.gather(*tasks, return_exceptions=True)
            
            # 精确1秒间隔
            elapsed = (datetime.now() - start_time).total_seconds()
            await asyncio.sleep(max(0, 1.0 - elapsed))
    
    async def process_camera(self, camera: Dict):
        """处理单个摄像头帧"""
        # 1. 抓取帧
        frame = await self.fetch_frame(camera)
        
        # 2. 算法推理
        result = detector.process_frame(frame)
        new_events = stream_gen.process_frame(frame)
        
        # 3. 秒级事件入库
        if new_events:
            await self.save_events(camera['camera_id'], new_events)
        
        # 4. 实时告警检测
        alerts = self.check_alerts(result, new_events)
        if alerts:
            await self.send_alerts(alerts)
```

### 模块2: 小时聚合器 (hourly_aggregator.py)

```python
class HourlyAggregator:
    """每小时运行一次，生成小时统计"""
    
    async def aggregate_hour(self, client_id, enclosure_id, stat_date, hour):
        """聚合指定小时的数据"""
        # 查询该小时所有事件
        events = await self.fetch_hour_events(client_id, enclosure_id, stat_date, hour)
        
        # 计算指标
        stats = {
            'movement_count': sum(1 for e in events if e.type == 'movement'),
            'eating_count': sum(1 for e in events if e.type == 'eating'),
            'drinking_count': sum(1 for e in events if e.type == 'drinking'),
            'activity_score': self.calculate_activity_score(events)
        }
        
        # 保存小时统计
        await self.save_hourly_stats(client_id, enclosure_id, stat_date, hour, stats)
```

### 模块3: 日报生成器 (daily_reporter.py)

```python
class DailyReporter:
    """每天凌晨生成前一天的日报"""
    
    async def generate_daily_report(self, client_id, enclosure_id, animal_id, report_date):
        """生成单只动物的日报"""
        # 1. 获取24小时统计
        hourly_stats = await self.fetch_hourly_stats(enclosure_id, animal_id, report_date)
        
        # 2. 计算日汇总
        daily_summary = self.aggregate_daily(hourly_stats)
        
        # 3. 获取7天趋势
        activity_trend = await self.fetch_7day_trend(animal_id, report_date)
        
        # 4. 获取诊疗记录
        medical = await self.fetch_medical_record(animal_id)
        
        # 5. 生成并保存日报
        report = DailyReport(
            activity_score=daily_summary['activity_score'],
            activity_trend=activity_trend,
            eating_status=daily_summary['eating_status'],
            water_consumption=daily_summary['water_consumption'],
            medical_summary=medical
        )
        await self.save_report(report)
```

---

## 📱 小程序 API 设计

### 1. 获取日报列表
```http
GET /api/v2/mp/daily-reports?enclosure_id=123&date=2026-03-22
Authorization: Bearer <token>

Response:
{
  "code": 0,
  "data": {
    "date": "2026-03-22",
    "animals": [
      {
        "ear_tag": "LS-B2-025",
        "gender": "雌性",
        "age": "1岁",
        "health_status": 0,
        "activity_score": 82,
        "activity_level": "正常",
        "activity_trend": [78, 82, 75, 80, 82, 79, 82],
        "feed_main_remain": 35,
        "feed_aux_remain": 72,
        "eating_status": "慢食",
        "water_consumption": 6.8,
        "drinking_status": "偏多"
      }
    ]
  }
}
```

### 2. 获取动物详情（含诊疗、饲养记录）
```http
GET /api/v2/mp/animals/:ear_tag/daily?date=2026-03-22

Response:
{
  "code": 0,
  "data": {
    "basic": {
      "ear_tag": "LS-B2-025",
      "gender": "雌性",
      "age": "1岁",
      "health_status": 0,
      "enclosure": "B区2排3号"
    },
    "daily_data": { ... },
    "medical": {
      "diagnosis": "肠炎",
      "treatment_day": 3,
      "medications": [
        {"name": "消炎针", "dosage": "每天1次", "remain_days": 2},
        {"name": "益生菌", "dosage": "拌料", "remain_days": 5}
      ]
    },
    "care_records": {
      "today": [
        {"content": "粪便稍软（已送检）", "status": "completed", "priority": 0},
        {"content": "右后蹄拍照", "status": "completed", "priority": 0}
      ],
      "tomorrow": [
        {"content": "加维生素B", "status": "pending", "priority": 1},
        {"content": "量体温", "status": "pending", "priority": 0}
      ]
    }
  }
}
```

### 3. 添加饲养记录
```http
POST /api/v2/mp/care-records
{
  "animal_id": "LS-B2-025",
  "record_type": "observation",
  "category": "粪便",
  "content": "粪便稍软（已送检）",
  "priority": 0,
  "voice_url": "",
  "images": []
}
```

---

## 📅 开发计划 (4周)

### Week 1: 数据库 + 基础 Pipeline
- [ ] Day 1-2: 创建5张数据库表
- [ ] Day 3-4: 实现 capture_service.py（帧抓取）
- [ ] Day 5-7: 实现 hourly_aggregator.py（小时聚合）

### Week 2: 日报生成 + API
- [ ] Day 8-10: 实现 daily_reporter.py（日报生成）
- [ ] Day 11-12: 实现小程序日报查询 API
- [ ] Day 13-14: 实现动物详情 API（含诊疗、饲养记录）

### Week 3: 小程序前端
- [ ] Day 15-17: 日报列表页面（支持左右滑动看7天）
- [ ] Day 18-19: 动物详情页面（基础信息+数据看板）
- [ ] Day 20-21: 诊疗记录 + 饲养记录展示

### Week 4: 集成测试 + 优化
- [ ] Day 22-24: 端到端联调测试
- [ ] Day 25-26: 性能优化（数据库索引、缓存）
- [ ] Day 27-28: 部署上线 + 监控

---

## 📁 新增文件结构

```
hikvision-backend/
├── models_v2.py                    # 更新：添加新表模型
├── algorithm_pipeline/
│   ├── __init__.py
│   ├── capture_service.py          # 帧抓取服务
│   ├── hourly_aggregator.py        # 小时聚合器
│   ├── daily_reporter.py           # 日报生成器
│   └── alert_detector.py           # 实时告警检测
├── routes/
│   ├── miniprogram.py              # 更新：添加日报API
│   └── reports.py                  # 新增：日报相关API
├── services/
│   └── scheduler.py                # 新增：定时任务调度
└── migrations/
    ├── 001_add_events_table.sql
    ├── 002_add_hourly_stats_table.sql
    ├── 003_add_daily_reports_table.sql
    ├── 004_add_medical_records_table.sql
    └── 005_add_care_records_table.sql
```

---

## 🔗 相关文档

- **飞书进度文档**: https://feishu.cn/docx/YJCldtSwNoaM6Cxda0dc2R0En7c
- **GitHub分支**: feature/algorithm-development
- **数据库设计**: 本文档第3节
- **API文档**: 本文档第5节

---

**更新人**: AI助手  
**更新时间**: 2026-03-22  
**版本**: v2.0
