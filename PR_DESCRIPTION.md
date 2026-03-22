# 算法 Pipeline 后端基础设施实现

## 概述
本 PR 实现了林麝健康监测系统的算法 Pipeline 后端基础设施，包括数据库设计、核心服务模块和小程序 API。

## 实现内容

### 1. 数据库表创建（5张表）

| 表名 | 用途 | 关键字段 |
|------|------|----------|
| `events` | 原子事件表 | event_type, confidence, bbox, event_time |
| `event_hourly_stats` | 小时统计表 | movement_count, eating_duration, activity_score |
| `daily_reports` | 日报表 | activity_score, eating_status, water_consumption |
| `medical_records_v2` | 诊疗记录表 | diagnosis, medications, treatment_day |
| `care_records` | 饲养记录表 | record_type, category, content, scheduled_date |

### 2. 核心服务模块

#### capture_service.py - 1秒帧抓取服务
- 每1秒并行抓取所有摄像头帧
- 支持异步并发处理（asyncio + aiohttp）
- 秒级事件入库
- 实时告警检测
- 统计信息追踪

#### hourly_aggregator.py - 小时聚合器
- 每小时聚合事件数据
- 计算活动/进食/饮水/休息统计
- 活动评分算法（0-100分）
- 支持历史数据批量聚合

#### daily_reporter.py - 日报生成器
- 每天凌晨生成前一天的日报
- 聚合24小时统计数据
- 生成7天活动趋势
- 整合诊疗记录和告警信息
- 健康状态评估（绿/黄/红）

### 3. 小程序 API（3个接口）

| 接口 | 方法 | 描述 |
|------|------|------|
| `/api/v2/mp/daily-reports` | GET | 获取日报列表，支持分页和日期筛选 |
| `/api/v2/mp/animals/:id/daily` | GET | 获取动物详情，含诊疗和饲养记录 |
| `/api/v2/mp/care-records` | POST | 添加饲养记录（观察/任务/测量） |

### 4. 定时任务调度器

- **小时聚合**: 每小时第5分钟运行
- **日报生成**: 每天凌晨1:00运行
- 支持手动触发任务
- 任务执行日志记录

## 技术栈
- Python 3.10+
- Flask + SQLAlchemy
- MySQL/PostgreSQL
- asyncio + aiohttp
- APScheduler

## 文件结构
```
hikvision-backend/
├── models_algorithm.py              # 算法模型定义
├── algorithm_pipeline/
│   ├── __init__.py
│   ├── capture_service.py           # 帧抓取服务
│   ├── hourly_aggregator.py         # 小时聚合器
│   └── daily_reporter.py            # 日报生成器
├── routes/
│   └── reports.py                   # 小程序 API 路由
├── services/
│   └── scheduler.py                 # 定时任务调度器
└── migrations/
    ├── 001_add_events_table.sql
    ├── 002_add_hourly_stats_table.sql
    ├── 003_add_daily_reports_table.sql
    ├── 004_add_medical_records_v2_table.sql
    └── 005_add_care_records_table.sql
```

## 数据库迁移

执行以下 SQL 文件创建新表：
```bash
mysql -u user -p database < migrations/001_add_events_table.sql
mysql -u user -p database < migrations/002_add_hourly_stats_table.sql
mysql -u user -p database < migrations/003_add_daily_reports_table.sql
mysql -u user -p database < migrations/004_add_medical_records_v2_table.sql
mysql -u user -p database < migrations/005_add_care_records_table.sql
```

## 启动定时任务

```python
from services.scheduler import start_scheduler

# 在 Flask 应用启动时
scheduler = start_scheduler(app)
```

## 测试

各模块提供独立的测试入口：
```bash
# 测试帧抓取服务
python algorithm_pipeline/capture_service.py

# 测试小时聚合器
python algorithm_pipeline/hourly_aggregator.py

# 测试日报生成器
python algorithm_pipeline/daily_reporter.py
```

## 后续工作

1. 接入实际算法引擎（替换模拟推理）
2. 实现海康API快照获取
3. 添加 WebSocket 实时告警推送
4. 性能优化（数据库索引、缓存）
5. 部署和监控

## 关联文档

- [算法开发计划 v2.0](../docs/ALGORITHM_DEVELOPMENT_PLAN_v2.md)
