# 海康互联开放平台 API 接入指南

## 一、认证方式

海康互联使用 **AK/SK** (Access Key / Secret Key) 进行 API 认证。

### 1.1 认证流程

```python
import hashlib
import hmac
import base64
from datetime import datetime

def sign_request(ak, sk, method, uri, params=None, body=None):
    """
    生成海康互联 API 请求签名
    
    Args:
        ak: Access Key
        sk: Secret Key (Base64 解码后的字节)
        method: HTTP 方法 (GET/POST)
        uri: 请求路径
        params: URL 参数
        body: 请求体
    
    Returns:
        headers: 包含签名的请求头
    """
    # 1. 时间戳
    timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # 2. 构建签名字符串
    string_to_sign = f"{method}\n{uri}\n{timestamp}\n"
    if params:
        string_to_sign += "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    if body:
        string_to_sign += "\n" + body
    
    # 3. HMAC-SHA256 签名
    sk_bytes = base64.b64decode(sk)
    signature = hmac.new(sk_bytes, string_to_sign.encode('utf-8'), hashlib.sha256).digest()
    signature_b64 = base64.b64encode(signature).decode('utf-8')
    
    # 4. 构建请求头
    headers = {
        'Content-Type': 'application/json',
        'X-Ca-Key': ak,
        'X-Ca-Signature': signature_b64,
        'X-Ca-Timestamp': timestamp,
    }
    
    return headers
```

## 二、核心 API 接口

### 2.1 获取设备列表

```http
GET https://openapi.hikiot.com/v1/devices
Headers:
  X-Ca-Key: {your_ak}
  X-Ca-Signature: {signature}
  X-Ca-Timestamp: {timestamp}
```

响应示例:
```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 10,
    "list": [
      {
        "deviceId": "D123456789",
        "deviceName": "养殖场摄像头01",
        "deviceType": "IPC",
        "status": "online",
        "channels": [
          {
            "channelNo": 1,
            "channelName": "通道1"
          }
        ]
      }
    ]
  }
}
```

### 2.2 获取实时预览地址

```http
POST https://openapi.hikiot.com/v1/devices/{deviceId}/preview
Headers:
  X-Ca-Key: {your_ak}
  X-Ca-Signature: {signature}
  X-Ca-Timestamp: {timestamp}
  Content-Type: application/json

Body:
{
  "channelNo": 1,
  "protocol": "hls",  // hls, webrtc, flv
  "streamType": 0     // 0:主码流, 1:子码流
}
```

### 2.3 获取设备截图

```http
GET https://openapi.hikiot.com/v1/devices/{deviceId}/snapshot?channelNo=1
Headers:
  X-Ca-Key: {your_ak}
  X-Ca-Signature: {signature}
  X-Ca-Timestamp: {timestamp}
```

### 2.4 云台控制

```http
POST https://openapi.hikiot.com/v1/devices/{deviceId}/ptz
Headers:
  X-Ca-Key: {your_ak}
  X-Ca-Signature: {signature}
  X-Ca-Timestamp: {timestamp}
  Content-Type: application/json

Body:
{
  "channelNo": 1,
  "command": "UP",      // UP, DOWN, LEFT, RIGHT, ZOOM_IN, ZOOM_OUT
  "speed": 50,          // 1-100
  "duration": 500       // 持续时间(毫秒)
}
```

## 三、Python SDK 封装

```python
import requests
import hashlib
import hmac
import base64
import json
from datetime import datetime
from typing import Optional, Dict, Any

class HikvisionCloudClient:
    """海康互联开放平台客户端"""
    
    BASE_URL = "https://openapi.hikiot.com"
    
    def __init__(self, ak: str, sk: str):
        self.ak = ak
        self.sk = sk
        self.session = requests.Session()
    
    def _sign(self, method: str, uri: str, params: dict = None, body: str = None) -> dict:
        """生成签名"""
        timestamp = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # 构建签名字符串
        parts = [method.upper(), uri, timestamp]
        if params:
            query = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
            parts.append(query)
        if body:
            parts.append(body)
        
        string_to_sign = "\n".join(parts)
        
        # HMAC-SHA256
        sk_bytes = base64.b64decode(self.sk)
        signature = hmac.new(
            sk_bytes, 
            string_to_sign.encode('utf-8'), 
            hashlib.sha256
        ).digest()
        
        return {
            'Content-Type': 'application/json',
            'X-Ca-Key': self.ak,
            'X-Ca-Signature': base64.b64encode(signature).decode('utf-8'),
            'X-Ca-Timestamp': timestamp,
        }
    
    def _request(self, method: str, path: str, **kwargs) -> dict:
        """发送请求"""
        uri = path
        url = f"{self.BASE_URL}{path}"
        
        params = kwargs.get('params')
        body = kwargs.get('data')
        if body and isinstance(body, dict):
            body = json.dumps(body)
            kwargs['data'] = body
        
        headers = self._sign(method, uri, params, body)
        kwargs['headers'] = headers
        
        resp = self.session.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp.json()
    
    # ============ 设备管理 ============
    
    def get_devices(self, page: int = 1, page_size: int = 20) -> dict:
        """获取设备列表"""
        return self._request('GET', '/v1/devices', params={
            'page': page,
            'pageSize': page_size
        })
    
    def get_device_info(self, device_id: str) -> dict:
        """获取设备详情"""
        return self._request('GET', f'/v1/devices/{device_id}')
    
    # ============ 视频相关 ============
    
    def get_preview_url(self, device_id: str, channel_no: int = 1, 
                       protocol: str = 'hls', stream_type: int = 0) -> dict:
        """获取实时预览地址"""
        return self._request('POST', f'/v1/devices/{device_id}/preview', data={
            'channelNo': channel_no,
            'protocol': protocol,
            'streamType': stream_type
        })
    
    def get_snapshot(self, device_id: str, channel_no: int = 1) -> bytes:
        """获取设备截图"""
        headers = self._sign('GET', f'/v1/devices/{device_id}/snapshot', 
                            params={'channelNo': channel_no})
        url = f"{self.BASE_URL}/v1/devices/{device_id}/snapshot?channelNo={channel_no}"
        resp = self.session.get(url, headers=headers)
        return resp.content
    
    # ============ PTZ 控制 ============
    
    def ptz_control(self, device_id: str, command: str, channel_no: int = 1,
                   speed: int = 50, duration: int = 500) -> dict:
        """云台控制"""
        return self._request('POST', f'/v1/devices/{device_id}/ptz', data={
            'channelNo': channel_no,
            'command': command,
            'speed': speed,
            'duration': duration
        })
```

## 四、错误码说明

| 错误码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 认证失败 |
| 403 | 无权限访问 |
| 404 | 设备不存在 |
| 429 | 请求过于频繁 |
| 500 | 服务器内部错误 |
| 503 | 设备离线 |

## 五、使用示例

```python
# 初始化客户端
client = HikvisionCloudClient(
    ak="2023987187632369716",
    sk="MIICdgIBADANBgkqhkiG9w0BAQE..."
)

# 获取设备列表
devices = client.get_devices()
print(f"共有 {devices['data']['total']} 个设备")

# 获取第一个设备的截图
device_id = devices['data']['list'][0]['deviceId']
snapshot = client.get_snapshot(device_id)
with open('snapshot.jpg', 'wb') as f:
    f.write(snapshot)

# 获取预览地址
preview = client.get_preview_url(device_id, protocol='hls')
print(f"预览地址: {preview['data']['url']}")
```

## 六、注意事项

1. **签名有效期**: 签名使用 UTC 时间戳，有效期为 5 分钟
2. **频率限制**: 默认每秒最多 10 次请求
3. **截图限制**: 单个设备每分钟最多截图 10 次
4. **重试机制**: 遇到 429 错误时，建议等待 1 秒后重试
