# 海康互联 API RSA 加密修复说明

## 问题描述

回调失败，提示：**"无法获取到加密参数，请按照API调用规范对请求加密"**

## 根本原因

根据海康互联开放平台的 API 调用规范，**除以下三个接口外，所有服务端 API 的请求都需要进行 RSA 加密**：

1. `/auth/exchangeAppToken` - 获取应用访问凭证
2. `/auth/refreshAppToken` - 刷新应用访问凭证  
3. `/auth/third/applyAuthCode` - 申请授权码

之前的代码只处理了回调消息的**解密**（AES），但没有对**发送给海康的请求**进行 RSA 加密。

## 解决方案

### 1. 新增 RSA 加密模块

创建了 `services/rsa_encryptor.py`，提供以下功能：

- **GET 请求参数加密**: 将参数拼接成 `key=value&key2=value2` 格式，RSA 加密后作为 `querySecret` 参数
- **POST 请求体加密**: 将 JSON body RSA 加密后作为 `bodySecret` 字段
- **响应解密**: 解密海康返回的加密 `data` 字段

### 2. 更新 API 客户端

更新了 `services/hikcloud.py`：

- 新增 `HikvisionCloudAPI` 类（支持 RSA 加密）
- 保留 `HikvisionCloudAPIV1` 类（向后兼容，不加密）
- 自动判断是否需要加密（排除三个特殊接口）

### 3. 配置方式

**无需额外配置！** RSA 私钥就是 `HIK_APP_SECRET`，代码会自动使用它进行加密。

如果你希望使用不同的私钥，可以设置 `HIK_PRIVATE_KEY` 环境变量（优先级高于 `HIK_APP_SECRET`）：

```bash
# 可选：使用不同的 RSA 私钥
HIK_PRIVATE_KEY=your_rsa_private_key_here
```

## 私钥说明

RSA 私钥就是 `HIK_APP_SECRET`，无需额外获取。

如果你需要查看：
1. 登录海康互联开放平台: https://open.hikiot.com
2. 进入你的应用管理页面
3. 选择 **"凭证&基础信息"** → **"应用秘钥"** 页签
4. **Secret** 字段的内容就是 RSA 私钥

## 测试验证

运行测试脚本验证加密功能：

```bash
cd hikvision-backend
python test_rsa.py
```

## 代码使用示例

### 初始化 API 客户端

```python
from services.hikcloud import HikvisionCloudAPI
import os

# 方式1: 从环境变量读取私钥
api = HikvisionCloudAPI(
    app_key=os.getenv('HIK_APP_KEY'),
    app_secret=os.getenv('HIK_APP_SECRET')
)

# 方式2: 直接传入私钥
api = HikvisionCloudAPI(
    app_key='your_app_key',
    app_secret='your_app_secret',
    private_key='your_private_key_pem'
)
```

### 调用 API（自动加密）

```python
# GET 请求 - 参数会自动加密
devices = api.get_device_list(page=1, page_size=20)

# POST 请求 - body 会自动加密
pic_url = api.capture_device(device_serial='D12345678', channel_no=1)
```

## 加密流程说明

### GET 请求加密流程

```
原始参数: {"departNos": "BM0001", "beginDate": "2024-08-01"}
    ↓
拼接字符串: "beginDate=2024-08-01&departNos=BM0001"
    ↓
URL encode: "beginDate%3D2024-08-01%26departNos%3DBM0001"
    ↓
RSA 私钥加密（分段，每段117字节）
    ↓
Base64 编码
    ↓
URL encode
    ↓
最终 querySecret: "pmttDL8cTHDp8SRRFnBL69EdlyDVkASZ..."
```

最终请求 URL：
```
https://open-api.hikiot.com/attendance/export/v1/card/report?querySecret=pmttDL8cTHDp8SRR...
```

### POST 请求加密流程

```
原始 body: {"holidayType": "年假", "holidayUnit": 1}
    ↓
JSON 字符串: '{"holidayType":"年假","holidayUnit":1}'
    ↓
URL encode
    ↓
RSA 私钥加密
    ↓
Base64 编码
    ↓
最终请求体: {"bodySecret": "WJwqoyzxmp1czh7eUI3GcTI4zTLlNePI..."}
```

## 注意事项

1. **私钥安全**: RSA 私钥是敏感信息，不要提交到代码仓库，仅通过环境变量配置
2. **依赖库**: 需要安装 `pycryptodome` 或 `cryptography` 库
   ```bash
   pip install pycryptodome
   # 或
   pip install cryptography
   ```
3. **向后兼容**: 如果没有配置 `HIK_PRIVATE_KEY`，API 客户端会回退到不加密模式（但海康会返回错误）

## 相关文件

- `services/rsa_encryptor.py` - RSA 加密模块
- `services/hikcloud.py` - 更新后的 API 客户端
- `test_rsa.py` - 测试脚本
- `.env.example` - 环境变量示例
