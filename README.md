# 灵麝健康监测系统

基于 AI 视觉的智能林麝养殖监测解决方案。

## 项目结构

```
lin-she-project/
├── mini-program/          # 微信小程序前端
│   ├── pages/            # 页面代码
│   ├── components/       # 公共组件
│   ├── utils/            # 工具函数
│   └── app.js            # 小程序入口
├── admin-web/            # 后台管理系统
│   ├── src/              # 源码目录
│   ├── public/           # 静态资源
│   └── package.json      # 项目配置
├── backend/              # 后端 API 服务
│   ├── src/              # 源码目录
│   ├── config/           # 配置文件
│   └── package.json      # 项目配置
└── docs/                 # 项目文档
    ├── design/           # 设计规范
    └── api/              # API 文档
```

## 技术栈

- **小程序**: 微信小程序原生开发
- **后台管理**: Vue 3 + Element Plus
- **后端服务**: Node.js + Express + MongoDB
- **AI 视觉**: YOLOv8 + OpenCV

## 快速开始

### 小程序开发
```bash
cd mini-program
# 使用微信开发者工具打开此目录
```

### 后台管理系统
```bash
cd admin-web
npm install
npm run dev
```

### 后端服务
```bash
cd backend
npm install
npm run dev
```

## 文档

- [设计规范](./docs/design/design-system.md)
- [API 文档](./docs/api/README.md)

## 许可证

MIT
