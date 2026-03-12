# 前端接收海康 OAuth 授权成功通知

## 方案概述

授权成功页面会通过以下三种方式通知前端：
1. **postMessage** - 适用于 popup/iframe 方式打开授权窗口
2. **BroadcastChannel** - 适用于同域多标签页通信
3. **localStorage** - 兼容性最好的方案

---

## 前端集成示例

### 方式1: postMessage（推荐用于 popup）

```javascript
// 打开授权窗口
const authWindow = window.open('/api/v2/platforms/1/login-url', 'hikvision_auth', 'width=800,height=600');

// 监听授权成功消息
window.addEventListener('message', (event) => {
    // 验证消息来源（可选）
    // if (event.origin !== 'https://your-domain.com') return;
    
    const data = event.data;
    if (data.type === 'HIKVISION_AUTH_SUCCESS') {
        console.log('授权成功:', data);
        
        // 刷新平台列表
        refreshPlatformList();
        
        // 显示成功提示
        showNotification(`平台 ${data.platformName} 授权成功！`);
        
        // 关闭 popup（如果还在）
        if (authWindow && !authWindow.closed) {
            authWindow.close();
        }
    }
});
```

### 方式2: BroadcastChannel（推荐用于多标签页）

```javascript
// 创建 BroadcastChannel
const authChannel = new BroadcastChannel('hikvision_auth');

// 监听授权成功消息
authChannel.addEventListener('message', (event) => {
    const data = event.data;
    if (data.type === 'HIKVISION_AUTH_SUCCESS') {
        console.log('授权成功:', data);
        
        // 刷新平台列表
        refreshPlatformList();
        
        // 显示成功提示
        showNotification(`平台 ${data.platformName} 授权成功！同步了 ${data.deviceCount} 个设备`);
    }
});

// 页面卸载时关闭 channel
window.addEventListener('beforeunload', () => {
    authChannel.close();
});
```

### 方式3: localStorage（兼容性最好）

```javascript
// 监听 localStorage 变化
window.addEventListener('storage', (event) => {
    if (event.key === 'hikvision_auth_event' && event.newValue) {
        try {
            const data = JSON.parse(event.newValue);
            if (data.type === 'HIKVISION_AUTH_SUCCESS') {
                console.log('授权成功:', data);
                
                // 刷新平台列表
                refreshPlatformList();
                
                // 显示成功提示
                showNotification(`平台 ${data.platformName} 授权成功！`);
            }
        } catch (e) {
            console.error('解析授权消息失败:', e);
        }
    }
});
```

### 完整集成方案（推荐）

```javascript
class HikvisionAuthHandler {
    constructor() {
        this.authWindow = null;
        this.bc = null;
        this.init();
    }
    
    init() {
        // 方式1: postMessage
        window.addEventListener('message', this.handleMessage.bind(this));
        
        // 方式2: BroadcastChannel
        if ('BroadcastChannel' in window) {
            this.bc = new BroadcastChannel('hikvision_auth');
            this.bc.addEventListener('message', this.handleMessage.bind(this));
        }
        
        // 方式3: localStorage
        window.addEventListener('storage', this.handleStorage.bind(this));
    }
    
    handleMessage(event) {
        const data = event.data;
        if (data && data.type === 'HIKVISION_AUTH_SUCCESS') {
            this.onAuthSuccess(data);
        }
    }
    
    handleStorage(event) {
        if (event.key === 'hikvision_auth_event' && event.newValue) {
            try {
                const data = JSON.parse(event.newValue);
                if (data.type === 'HIKVISION_AUTH_SUCCESS') {
                    this.onAuthSuccess(data);
                }
            } catch (e) {
                console.error('解析授权消息失败:', e);
            }
        }
    }
    
    onAuthSuccess(data) {
        console.log('[HikvisionAuth] 授权成功:', data);
        
        // 关闭授权窗口
        if (this.authWindow && !this.authWindow.closed) {
            this.authWindow.close();
            this.authWindow = null;
        }
        
        // 刷新平台列表
        this.refreshPlatforms();
        
        // 显示成功提示
        this.showNotification({
            type: 'success',
            title: '授权成功',
            message: `平台 "${data.platformName}" 已授权，同步了 ${data.deviceCount} 个设备`
        });
        
        // 触发自定义事件
        window.dispatchEvent(new CustomEvent('hikvision:auth:success', { detail: data }));
    }
    
    openAuthWindow(platformId) {
        const url = `/api/v2/auth/hikvision/login-url?platformId=${platformId}`;
        this.authWindow = window.open(url, 'hikvision_auth', 'width=800,height=600,scrollbars=yes');
        
        // 检查窗口是否被拦截
        if (!this.authWindow || this.authWindow.closed) {
            alert('请允许弹出窗口以完成授权');
            return false;
        }
        
        return true;
    }
    
    refreshPlatforms() {
        // 调用你的 API 刷新平台列表
        fetch('/api/v2/platforms')
            .then(res => res.json())
            .then(data => {
                if (data.code === 0) {
                    updatePlatformList(data.data);
                }
            });
    }
    
    showNotification(options) {
        // 使用你的 UI 组件显示通知
        // 例如：Element UI、Ant Design、自定义组件等
        console.log('[Notification]', options);
    }
    
    destroy() {
        window.removeEventListener('message', this.handleMessage.bind(this));
        window.removeEventListener('storage', this.handleStorage.bind(this));
        if (this.bc) {
            this.bc.close();
        }
    }
}

// 使用示例
const authHandler = new HikvisionAuthHandler();

// 点击授权按钮
document.getElementById('auth-btn').addEventListener('click', () => {
    authHandler.openAuthWindow(1); // platformId = 1
});

// 监听授权成功事件（用于执行额外操作）
window.addEventListener('hikvision:auth:success', (event) => {
    console.log('收到授权成功事件:', event.detail);
    // 可以在这里执行额外的业务逻辑
});
```

---

## 消息格式

```typescript
interface HikvisionAuthSuccessMessage {
    type: 'HIKVISION_AUTH_SUCCESS';
    platformId: number;
    platformName: string;
    account: string;
    deviceCount: number;
    isDuplicate: boolean;  // 是否是重复请求
    timestamp: string;     // ISO 8601 格式
}
```

---

## 注意事项

1. **跨域问题**: 如果授权页面和前端页面不同域，postMessage 需要验证 origin
2. **浏览器兼容性**: BroadcastChannel 不支持 IE 和 Safari < 15.4
3. **localStorage 限制**: 同域下才能触发 storage 事件
4. **自动关闭**: 授权成功页面会在 3 秒后自动关闭

---

## 调试技巧

```javascript
// 在控制台模拟授权成功消息
window.postMessage({
    type: 'HIKVISION_AUTH_SUCCESS',
    platformId: 1,
    platformName: '凤县基地',
    account: 'ZHA1855899027284189256',
    deviceCount: 5,
    isDuplicate: false,
    timestamp: new Date().toISOString()
}, '*');
```
