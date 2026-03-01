# 林麝健康监测系统

基于 AI 视觉的智能林麝养殖监测解决方案。

## 项目概览

```
lin-she-health-monitor/
├── 📱 mini-program/          # 微信小程序前端
├── 🖥️  admin-web/            # 后台管理系统 (Vue3)
├── 🔧 backend/               # 后端服务
│   ├── src/                  # API服务 (Node.js)
│   └── services/
│       ├── event-processor/  # 事件处理器 (Go)
│       └── anomaly-detector/ # 异常检测器 (Go)
├── 🗄️  database/             # 数据库Schema
├── 📖 docs/                  # 文档
│   ├── architecture/         # 架构设计
│   └── deployment/           # 部署指南
├── 🐳 docker-compose.yml     # Docker部署配置
└── 🚀 start.sh               # 快速启动脚本
```

## 核心功能

| 模块 | 技术 | 功能 |
|------|------|------|
| **数据收集** | Go + ISAPI | 从海康摄像头抓取事件 |
| **活动量计算** | Go + 滑动窗口 | 实时计算活动量评分 |
| **异常检测** | Go + 统计学习 | 动态基线 + 无监督检测 |
| **后端API** | Node.js + Express | RESTful API |
| **小程序** | 微信小程序 | 移动端监控 |
| **管理后台** | Vue3 + Element Plus | Web管理界面 |

## 快速开始

### 1. 环境要求

- Docker >= 20.10
- Docker Compose >= 2.0
- 内存 >= 4GB

### 2. 一键启动

```bash
# 克隆项目
git clone <repository-url>
cd lin-she-health-monitor

# 启动（自动配置环境）
./start.sh
```

### 3. 访问服务

| 服务 | 地址 | 说明 |
|------|------|------|
| API 文档 | http://localhost:3000/api-docs | Swagger文档 |
| 管理后台 | http://localhost:8080 | Web管理界面 |
| InfluxDB | http://localhost:8086 | 时序数据库 |

### 4. 默认登录

- 用户名: `admin`
- 密码: `admin123`

## 核心算法

### 活动量计算

```
活动量评分 = min(100,
    频率(次/分) × 2 +       // 40分
    事件数 × 0.6 +          // 30分
    区域数 × 5 +            // 20分
    灵敏度 / 10)            // 10分
```

### 异常检测

| 方法 | 公式 | 阈值 |
|------|------|------|
| Z-Score | `(x - μ) / σ` | \|Z\| > 2.5 |
| IQR | `P75 - P25` | 超出 [Q1-1.5IQR, Q3+1.5IQR] |
| 极端百分位 | 直接比较 | < P1 或 > P99 |

## 技术栈

### 后端
- **Node.js** - API服务
- **Go** - 高性能数据处理
- **MySQL** - 关系数据
- **InfluxDB** - 时序数据
- **Kafka** - 消息队列
- **Redis** - 缓存

### 前端
- **微信小程序** - 移动端
- **Vue3** - 管理后台
- **Element Plus** - UI组件库

### 部署
- **Docker** - 容器化
- **Docker Compose** - 编排
- **Nginx** - 反向代理

## 项目状态

| 模块 | 状态 | 完成度 |
|------|------|--------|
| 数据库Schema | ✅ | 100% |
| 后端API | ✅ | 80% |
| Event Processor | ✅ | 100% |
| Anomaly Detector | ✅ | 100% |
| 小程序前端 | 🚧 | 60% |
| 管理后台 | 🚧 | 40% |
| Docker部署 | ✅ | 100% |
| 海康互联后端 | ✅ | 90% |

## 海康互联后端服务

独立的海康互联开放平台对接服务，支持设备管理、回调接收、动物检测。

### 部署海康互联后端

```bash
# 进入项目目录
cd lin-she-health-monitor

# 1. 配置环境变量
cp hikvision-backend/.env.example .env
# 编辑 .env，填写 HIK_APP_KEY 和 HIK_APP_SECRET

# 2. 一键部署
./deploy.sh

# 或使用 docker-compose 手动部署
docker-compose up -d --build
```

### 海康互联后端 API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/api/callback` | POST | 接收海康云回调 |
| `/api/callback` | GET | 验证回调地址 |
| `/api/devices` | GET | 获取设备列表 |
| `/api/devices` | POST | 添加设备 |
| `/api/devices/:id/capture` | POST | 设备抓拍 |
| `/api/detection/start` | POST | 开始检测 |
| `/api/detection/stop` | POST | 停止检测 |

### 配置海康互联回调

在海康互联开放平台配置回调地址：
```
https://your-domain.com/api/callback
```

## 开发计划

- [x] 核心架构设计
- [x] 数据库模型
- [x] 事件处理服务
- [x] 异常检测服务
- [x] Docker部署
- [ ] 小程序UI优化
- [ ] 管理后台功能完善
- [ ] 摄像头接入测试
- [ ] 算法调优

## 文档

- [架构设计](docs/architecture/cloud-native-multi-tenant.md)
- [部署指南](docs/deployment/README.md)
- [API文档](backend/src/routes/api.js)
- [Event Processor](backend/services/event-processor/README.md)
- [Anomaly Detector](backend/services/anomaly-detector/README.md)

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT
