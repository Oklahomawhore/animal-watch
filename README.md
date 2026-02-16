# 林麝健康监测系统

基于 AI 视觉的智能林麝养殖监测解决方案。

## 项目结构

```
lin-she-health-monitor/
├── mini-program/              # 微信小程序前端
│   ├── pages/                 # 页面代码
│   │   ├── index/            # 首页概览
│   │   ├── monitor/          # 实时监控
│   │   ├── alerts/           # 报警记录
│   │   └── profile/          # 个人中心
│   ├── components/           # 公共组件
│   ├── utils/                # 工具函数
│   └── services/             # API 服务
├── admin-web/                # 后台管理系统 (Vue 3)
│   ├── src/
│   │   ├── views/           # 页面视图
│   │   ├── components/      # 公共组件
│   │   ├── router/          # 路由配置
│   │   └── store/           # 状态管理
│   └── package.json
├── backend/                  # 后端 API 服务 (Node.js)
│   ├── src/
│   │   ├── routes/          # API 路由
│   │   ├── models/          # 数据模型
│   │   ├── middleware/      # 中间件
│   │   └── controllers/     # 控制器
│   └── package.json
├── microservices/            # 微服务
│   ├── ai-detection/        # AI 检测服务
│   ├── data-processor/      # 数据处理服务
│   └── notification/        # 通知服务
├── cloud-functions/          # 云函数
│   ├── wx-login/            # 微信登录
│   ├── alert-push/          # 报警推送
│   ├── data-sync/           # 数据同步
│   └── report-generator/    # 报表生成
├── shared/                   # 共享代码
│   ├── types/               # TypeScript 类型
│   ├── constants/           # 常量定义
│   └── utils/               # 通用工具
├── database/                 # 数据库
│   ├── migrations/          # 迁移文件
│   └── seeds/               # 种子数据
└── docs/                     # 文档
    ├── api/                  # API 文档
    ├── design/               # 设计规范
    └── deployment/           # 部署文档
```

## 技术栈

### 小程序
- 微信小程序原生开发
- WXML + WXSS + JavaScript

### 后台管理
- Vue 3 + TypeScript
- Element Plus UI 框架
- Pinia 状态管理
- Vue Router 路由管理
- ECharts 图表库

### 后端服务
- Node.js + Express
- MongoDB 数据库
- JWT 认证
- Socket.io 实时通信

### AI 检测
- Python + FastAPI
- YOLOv8 目标检测
- OpenCV 图像处理

## 快速开始

### 1. 克隆项目
```bash
git clone <repository-url>
cd lin-she-health-monitor
```

### 2. 启动后端服务
```bash
cd backend
npm install
cp .env.example .env
npm run dev
```

### 3. 启动后台管理系统
```bash
cd admin-web
npm install
npm run dev
```

### 4. 开发小程序
使用微信开发者工具打开 `mini-program` 目录。

## 环境变量

### 后端 (.env)
```
PORT=3000
MONGODB_URI=mongodb://localhost:27017/linshe
JWT_SECRET=your-secret-key
```

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/xxx`)
3. 提交更改 (`git commit -m 'feat: add xxx'`)
4. 推送到分支 (`git push origin feature/xxx`)
5. 创建 Pull Request

## 许可证

MIT
