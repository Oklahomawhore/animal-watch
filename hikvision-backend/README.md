# 海康互联开放平台后端服务

独立的 Flask 后端，用于接收海康云回调、管理设备、处理动物检测。

## 目录结构

```
hikvision-backend/
├── app.py                 # Flask 主应用
├── config.py              # 配置文件
├── models.py              # 数据库模型
├── requirements.txt       # Python 依赖
├── routes/
│   ├── __init__.py
│   ├── callback.py        # 回调处理
│   ├── device.py          # 设备管理
│   └── detection.py       # 检测接口
├── services/
│   ├── __init__.py
│   ├── hikcloud.py        # 海康云 API 客户端
│   └── detector.py        # 动物检测服务
└── utils/
    ├── __init__.py
    └── helpers.py         # 工具函数
```

## 快速开始

```bash
cd hikvision-backend
pip install -r requirements.txt
python app.py
```

## API 接口

### 回调接口
- `POST /api/callback` - 接收海康云事件推送
- `GET /api/callback` - 验证回调地址

### 设备管理
- `GET /api/devices` - 获取设备列表
- `POST /api/devices/:id/capture` - 设备抓拍

### 检测服务
- `GET /api/detection/status` - 获取检测状态
- `POST /api/detection/start` - 开始检测
- `POST /api/detection/stop` - 停止检测
