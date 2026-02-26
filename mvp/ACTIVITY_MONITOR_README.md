# 海康云运动量检测系统

基于海康互联开放 API 的运动量检测方案，使用 YOLO/背景差分检测动物矩形框并计算活动量。

## 特性

- ✅ **海康云 API 集成** - Token 认证 + 设备抓拍
- ✅ **实时检测** - 每秒抓拍分析
- ✅ **YOLO 检测** - 支持 YOLO 模型或背景差分
- ✅ **活动量计算** - 速度、移动距离、活动等级
- ✅ **可视化** - 矩形框标注 + 状态显示

## 快速开始

### 1. 安装依赖

```bash
pip3 install opencv-python numpy requests
```

### 2. 运行检测

```bash
python3 activity_monitor.py \
  --ak YOUR_APP_KEY \
  --sk YOUR_APP_SECRET \
  --device-id YOUR_DEVICE_SERIAL \
  --interval 1.0
```

### 3. 查看结果

检测结果保存到 `output/` 目录，包含：
- 带标注的图片
- 活动量日志

## 核心功能

### Token 认证流程

```python
# 1. 使用 AK/SK 换取 AccessToken
sign = MD5(appKey + appSecret + timestamp)
token = api.post("/v1/token/get", {...})

# 2. 使用 Token 调用 API
headers = {'accessToken': token}
image = api.post("/v1/device/capture", headers=headers)
```

### 动物检测算法

```python
# 方案1: YOLO (如果有模型)
detections = yolo.detect(frame)

# 方案2: 背景差分 (默认)
fg_mask = bg_subtractor.apply(frame)
contours = find_contours(fg_mask)
```

### 活动量计算

```
活动量 = 移动距离 / 时间
速度 = 像素位移 / 秒

活动等级:
- idle:  < 5 px/s
- low:   5-20 px/s
- medium: 20-50 px/s
- high:  > 50 px/s
```

## API 端点说明

| 功能 | 端点 | 方法 |
|------|------|------|
| 获取 Token | /v1/token/get | POST |
| 设备列表 | /v1/device/list | GET |
| 设备抓拍 | /v1/device/capture | POST |

## 输出示例

```
[2024-01-15 10:30:25] 检测到 1 只动物, 活动等级: medium, 速度: 35.2 px/s
[2024-01-15 10:30:26] 检测到 1 只动物, 活动等级: high, 速度: 68.5 px/s
[2024-01-15 10:30:27] 检测到 0 只动物, 活动等级: idle, 速度: 0.0 px/s
```

## 注意事项

1. **API 频率限制** - 每秒最多 10 次请求
2. **Token 有效期** - 默认 2 小时，自动刷新
3. **网络要求** - 需要能访问海康云 API
4. **设备要求** - 设备需在线且支持抓拍功能

## 下一步

- [ ] 接入 YOLO 模型提高检测精度
- [ ] 添加食槽区域 ROI 检测
- [ ] 集成到后端服务
- [ ] 添加告警推送
