# API V2 接口文档

## 认证方式

所有V2接口使用 **JWT Bearer Token** 认证：

```
Authorization: Bearer <token>
```

Token通过 `/api/v2/auth/login` 获取。

---

## 认证接口

### POST /api/v2/auth/login
用户登录

**请求参数:**
```json
{
  "username": "admin",
  "password": "123456",
  "clientCode": "client001"  // 可选
}
```

**响应:**
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "user": { ... }
  }
}
```

### GET /api/v2/auth/me
获取当前用户信息

### POST /api/v2/auth/change-password
修改密码

---

## 用户管理（仅Admin）

### GET /api/v2/users
获取用户列表

**查询参数:**
- page: 页码，默认1
- size: 每页数量，默认20

### POST /api/v2/users
创建用户

**请求参数:**
```json
{
  "username": "breeder01",
  "password": "123456",
  "nickname": "张饲养员",
  "role": "breeder",           // factory_manager/breeder
  "visibilityLevel": "area",   // factory/area/enclosure
  "visibilityScopeIds": [1, 2] // 可看的区域ID列表
}
```

### PUT /api/v2/users/:id
更新用户信息

### POST /api/v2/users/:id/reset-password
重置用户密码

### DELETE /api/v2/users/:id
删除用户

---

## 平台授权（仅Admin）

### GET /api/v2/platforms
获取平台授权列表

### POST /api/v2/platforms
添加平台

**请求参数:**
```json
{
  "name": "总部海康账号",
  "provider": "hikvision"
}
```

### GET /api/v2/auth/hikvision/login-url
获取海康OAuth授权链接（需要Admin权限）

**响应:**
```json
{
  "code": 0,
  "data": {
    "loginUrl": "https://open.hikiot.com/oauth/thirdpart?appKey=xxx&...",
    "state": "1|2"
  }
}
```

用户打开此链接完成授权后，海康会回调到 `/api/v2/platforms/:id/oauth-callback`

### POST /api/v2/platforms/:id/sync
手动同步设备列表

### DELETE /api/v2/platforms/:id
删除平台授权

---

## 厂区/区域/圈管理

### 厂区 Factory

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | /api/v2/factories | 登录用户 | 列表 |
| POST | /api/v2/factories | Manager+ | 创建 |
| GET | /api/v2/factories/:id | 登录用户 | 详情（含区域）|
| PUT | /api/v2/factories/:id | Manager+ | 更新 |
| DELETE | /api/v2/factories/:id | Admin | 删除 |

### 区域 Area

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | /api/v2/areas | 登录用户 | 列表（?factoryId=）|
| POST | /api/v2/areas | Manager+ | 创建（需factoryId）|
| GET | /api/v2/areas/:id | 登录用户 | 详情（含圈）|
| PUT | /api/v2/areas/:id | Manager+ | 更新 |
| DELETE | /api/v2/areas/:id | Admin | 删除 |

### 圈 Enclosure

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | /api/v2/enclosures | 登录用户 | 列表（?factoryId=&areaId=）|
| POST | /api/v2/enclosures | Manager+ | 创建 |
| GET | /api/v2/enclosures/:id | 登录用户 | 详情（含摄像头、个体信息）|
| PUT | /api/v2/enclosures/:id | Manager+ | 更新 |
| DELETE | /api/v2/enclosures/:id | Admin | 删除 |

**个体标签格式:**
```json
{
  "animalTags": [
    {
      "tag": "001",
      "name": "小白",
      "gender": "female",
      "birth_date": "2023-01-15",
      "status": "healthy",
      "status_note": "",
      "entry_date": "2023-03-01"
    }
  ]
}
```

---

## 摄像头管理

### GET /api/v2/cameras
获取摄像头列表（带权限过滤）

**查询参数:**
- enclosureId: 按圈筛选
- platformId: 按平台筛选
- status: 按状态筛选 (online/offline/error/unbound)
- bound: true/false 是否已绑定
- page: 页码
- size: 每页数量

### GET /api/v2/cameras/:id
获取摄像头详情

### POST /api/v2/cameras/:id/bind
绑定摄像头到圈

**请求参数:**
```json
{
  "enclosureId": 1,
  "cameraType": "enclosure",     // enclosure/feeding/environment
  "positionInEnclosure": "front" // front/back/left/right/top
}
```

### POST /api/v2/cameras/:id/unbind
解绑摄像头

### POST /api/v2/cameras/auto-import
一键导入（根据名字自动匹配圈）

**请求参数:**
```json
{
  "platformId": 1,    // 可选，默认全部
  "dryRun": true      // 可选，true时只预览不执行
}
```

**响应:**
```json
{
  "code": 0,
  "data": {
    "dryRun": true,
    "matchedCount": 5,
    "unmatchedCount": 3,
    "matched": [...],
    "unmatched": [...]
  }
}
```

### POST /api/v2/cameras/:id/snapshot
手动抓取快照

---

## 权限说明

| 角色 | 账号管理 | 平台授权 | 层级管理 | 摄像头管理 | 查看范围 |
|------|----------|----------|----------|------------|----------|
| Admin | ✅ | ✅ | ✅ | ✅ | 全部 |
| FactoryManager | ❌ | ✅ | ✅ | ✅ | 全部 |
| Breeder | ❌ | ❌ | ❌ | ❌ | visibility_scope |

**Breeder可视范围:**
- visibilityLevel = factory: 看指定厂的全部
- visibilityLevel = area: 看指定区域的全部圈
- visibilityLevel = enclosure: 看指定的圈

---

## 错误码

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未登录或Token无效 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
