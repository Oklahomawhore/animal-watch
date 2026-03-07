# 林麝健康监测系统 - 数据库设计 V2

## 核心架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client (客户/租户)                        │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  User (RBAC权限系统)                                     │   │
│  │  - Admin: 全部权限 (账号管理、平台授权、查看)              │   │
│  │  - FactoryManager: 除账号管理外的全部权限                  │   │
│  │  - Breeder: 基础通知 + 被授权后可查看                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  CameraPlatform (多厂商支持)  ← Admin授权                │   │
│  │  - 海康威视 (HIKVISION)                                   │   │
│  │  - 大华 (预留)                                            │   │
│  │  - 宇视 (预留)                                            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Factory → Area → Enclosure (层级结构)                   │   │
│  │  (厂)      (区域)   (圈/个体)                             │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Camera ← 绑定到 Enclosure                               │   │
│  │  - 支持一键导入（摄像头名→圈名自动匹配）                    │   │
│  │  - 类型：圈监控/食槽/环境                                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Detection / AlarmRecord (检测与告警)                    │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 表结构说明

### 1. 客户管理 (Client)
多租户设计，每个客户完全隔离。新客户开通时创建一个Client记录，系统自动生成管理员账号。

```python
Client
├── id, name, code (唯一)
├── contact_name, contact_phone
├── config (JSON配置)
├── status (active/inactive)
└── 关联: users[], factories[], platforms[]
```

### 2. 用户与权限 (User)

**角色定义:**
| 角色 | 账号管理 | 平台授权 | 查看后台 | 接收通知 |
|------|----------|----------|----------|----------|
| Admin | ✅ | ✅ | ✅ | ✅ |
| FactoryManager | ❌ | ✅ | ✅ | ✅ |
| Breeder | ❌ | ❌ | 需授权 | ✅ |

**可视范围 (Visibility):**
```python
User.visibility_level  # factory / area / enclosure
User.visibility_scope_ids  # 具体可看的IDs列表
```

示例:
- 厂长A: `level='area', scope_ids=[1,2,3]` → 只能看区域1、2、3
- 饲养员B: `level='enclosure', scope_ids=[10,11,12]` → 只能看圈10、11、12

```python
User
├── client_id (所属客户)
├── username, password_hash, nickname
├── role (admin/factory_manager/breeder)
├── visibility_level, visibility_scope_ids
├── permissions (JSON细粒度权限)
└── created_by (谁创建的，用于追溯)
```

### 3. 摄像头平台 (CameraPlatform)
支持多平台、多账号。每个平台授权由Admin操作。

```python
CameraPlatform
├── client_id
├── provider (hikvision/dahua/uniview)
├── name (自定义名称，如"总部海康账号")
├── platform_account (平台登录账号)
├── access_token, refresh_token, token_expires_at
├── api_config (JSON: {appKey, appSecret, baseUrl})
├── authorized_by, authorized_at (谁授权的)
└── status (active/expired/revoked)
```

**扩展性:** 新增厂商时只需:
1. 在 `CameraProvider` 枚举添加新值
2. 实现对应的API客户端类
3. 前端添加授权入口

### 4. 层级结构 (Factory → Area → Enclosure)

```
Factory (养殖场)
  └── Area (A区、B区、繁殖区等)
        └── Enclosure (圈1、圈2、个体001等)
              └── Camera (摄像头)
```

```python
Factory / Area / Enclosure
├── client_id
├── name, code (厂/区域/圈内唯一)
├── location (地理坐标或平面图坐标)
└── animal_tags (圈级存储个体标签)
```

### 5. 摄像头 (Camera)

```python
Camera
├── client_id, platform_id, enclosure_id
├── platform_device_id, device_serial (平台侧ID)
├── name, camera_type (enclosure/feeding/environment)
├── status (online/offline/error/unbound)
├── snapshot_url (授权时抓取的快照)
├── is_auto_imported (是否一键导入)
└── position_in_enclosure (圈内位置: front/back/left/right/top)
```

**个体标签结构 (JSON):**
```json
[
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
```
状态: `healthy`/`sick`/`quarantine`/`dead`

**摄像头命名冲突解决:**
```python
# 格式: {provider}_{platform_account}_{device_name}
# 示例: hik_总部_圈A-01, hik_分部_圈A-01
unique_name = f"{provider}_{account}_{name}"
```

**一键导入逻辑:**
```python
# 授权后获取摄像头列表
for camera in platform_cameras:
    # 尝试匹配圈名
    enclosure = Enclosure.query.filter_by(
        client_id=client_id,
        name=camera['name']  # 摄像头名
    ).first()
    
    if enclosure:
        camera.enclosure_id = enclosure.id
        camera.is_auto_imported = True
```

### 6. 检测与告警 (Detection / AlarmRecord)

增加 `client_id` 和 `enclosure_id` 字段用于权限过滤。

## 海康设备API

**设备分页查询:**
```
GET https://open-api.hikiot.com/device/v1/page
Headers:
  App-Access-Token: {app_token}
  User-Access-Token: {user_token}
Params:
  page: 1
  size: 20
```

**响应字段:**
- deviceSerial: 设备序列号
- name: 设备名称
- model: 设备型号
- status: 0-离线, 1-在线
- channelNum: 通道数

## 权限检查示例代码

```python
# 检查用户是否有权限查看某个圈
def can_view_enclosure(user, enclosure_id):
    if user.role == UserRole.ADMIN:
        return True
    
    if user.visibility_level == VisibilityLevel.FACTORY:
        enclosure = Enclosure.query.get(enclosure_id)
        return enclosure.factory_id in user.visibility_scope_ids
    
    elif user.visibility_level == VisibilityLevel.AREA:
        enclosure = Enclosure.query.get(enclosure_id)
        return enclosure.area_id in user.visibility_scope_ids
    
    elif user.visibility_level == VisibilityLevel.ENCLOSURE:
        return enclosure_id in user.visibility_scope_ids
    
    return False

# 查询用户可见的摄像头列表
def get_visible_cameras(user):
    query = Camera.query.filter_by(client_id=user.client_id)
    
    if user.role == UserRole.ADMIN:
        return query.all()
    
    if user.visibility_level == VisibilityLevel.FACTORY:
        enclosures = Enclosure.query.filter(
            Enclosure.factory_id.in_(user.visibility_scope_ids)
        ).all()
    elif user.visibility_level == VisibilityLevel.AREA:
        enclosures = Enclosure.query.filter(
            Enclosure.area_id.in_(user.visibility_scope_ids)
        ).all()
    else:  # ENCLOSURE
        return query.filter(Camera.enclosure_id.in_(user.visibility_scope_ids)).all()
    
    enclosure_ids = [e.id for e in enclosures]
    return query.filter(Camera.enclosure_id.in_(enclosure_ids)).all()
```

## 完整业务流程

### 1. 客户开通
```
创建 Client → 创建 Admin User → 配置初始密码
```

### 2. Admin登录与平台授权
```
Admin登录 → 进入"平台授权"页面
  ↓
点击"添加海康账号" → 调用 /api/auth/login-url
  ↓
在新窗口打开海康OAuth页面 → 完成授权
  ↓
回调 /api/auth/oauth-callback → 获取Token → 获取摄像头列表
  ↓
显示摄像头列表 → Admin可:
    - 一键导入（自动匹配圈名）
    - 手动绑定到圈
    - 设置摄像头类型（圈监控/食槽/环境）
```

### 3. 账号管理 (仅Admin)
```
Admin进入"账号管理"
  ↓
创建用户:
    - 设置角色 (FactoryManager/Breeder)
    - 设置可视范围 (Factory/Area/Enclosure + IDs)
    - 设置通知权限
  ↓
用户收到账号密码 → 登录系统
```

### 4. 日常监控
```
用户登录 → 根据角色和可视范围显示:
    - FactoryManager: 全厂/指定区域监控
    - Breeder: 指定圈监控 + 告警通知
```

## API端点规划

```
# 认证
POST   /api/v2/auth/login
POST   /api/v2/auth/logout
GET    /api/v2/auth/me

# 平台授权 (Admin)
GET    /api/v2/platforms              # 列表
POST   /api/v2/platforms              # 添加平台
GET    /api/v2/platforms/:id/auth-url # 获取授权URL
POST   /api/v2/platforms/:id/sync     # 同步摄像头
DELETE /api/v2/platforms/:id          # 删除授权

# 摄像头管理 (Admin/FactoryManager)
GET    /api/v2/cameras
POST   /api/v2/cameras/:id/bind       # 绑定到圈
POST   /api/v2/cameras/auto-import    # 一键导入

# 层级管理 (Admin/FactoryManager)
GET/POST/PUT/DELETE /api/v2/factories
GET/POST/PUT/DELETE /api/v2/areas
GET/POST/PUT/DELETE /api/v2/enclosures

# 用户管理 (仅Admin)
GET    /api/v2/users
POST   /api/v2/users                  # 创建用户
PUT    /api/v2/users/:id
DELETE /api/v2/users/:id

# 监控与告警
GET    /api/v2/cameras/:id/live       # 实时预览
GET    /api/v2/detections             # 检测记录
GET    /api/v2/alarms                 # 告警记录
POST   /api/v2/alarms/:id/handle      # 处理告警
```

## 迁移策略

1. **保留旧表** - `user_auths`, `devices`, `detections`, `alarm_records` 保留用于数据迁移
2. **新数据走V2表** - 新Client使用V2模型
3. **逐步迁移** - 开发数据迁移脚本，将旧Client数据导入新结构

## 待确认问题

1. **权限粒度** - Breeder的"被授权后查看"是指Admin单独授权，还是自动根据visibility_scope？
2. **多海康账号** - 同一Client下多个海康账号的摄像头是否有命名冲突处理？
3. **个体标签** - `Enclosure.animal_tags` 结构是怎样的？`["001", "002"]` 还是 `[{"tag": "001", "name": "小白"}]`？
