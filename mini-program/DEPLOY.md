# 小程序部署指南

## 1. 配置后端服务地址

在 `app.js` 中修改 `apiBaseUrl` 为实际的后端服务地址：

```javascript
// app.js
globalData: {
  apiBaseUrl: 'http://YOUR_SERVER_IP:5001/api/v2',  // 修改这里
}
```

### 后端服务选项

| 环境 | 地址 | 说明 |
|------|------|------|
| 本地开发 | `http://localhost:5001/api/v2` | 本地Flask后端 |
| 局域网测试 | `http://192.168.x.x:5001/api/v2` | 内网服务器IP |
| 生产环境 | `https://your-domain.com/api/v2` | 域名+HTTPS |

## 2. 准备上传密钥

从微信小程序后台下载上传密钥：

1. 登录 [微信公众平台](https://mp.weixin.qq.com/)
2. 进入开发管理 → 开发设置 → 小程序代码上传
3. 下载上传密钥文件（`private.key`）
4. 将密钥文件保存到项目目录（如 `scripts/private.key`）

## 3. 配置环境变量

```bash
# 小程序 AppID
export WECHAT_APPID=wx YOUR_APPID_HERE

# 上传密钥路径
export WECHAT_PRIVATE_KEY_PATH=./scripts/private.key

# 版本信息
export VERSION=1.0.0
export VERSION_DESC="林麝健康监测小程序初版"
```

## 4. 上传小程序

### 方式一：使用脚本上传

```bash
cd /Users/wangshuzhu/.openclaw/workspace/lin-she-health-monitor

# 配置环境变量后执行
node scripts/upload-miniprogram.js upload
```

### 方式二：使用微信开发者工具

1. 打开微信开发者工具
2. 导入项目：`mini-program` 目录
3. 点击右上角「上传」按钮
4. 填写版本号和项目备注
5. 确认上传

## 5. 在微信后台设置体验版

1. 登录 [微信公众平台](https://mp.weixin.qq.com/)
2. 进入版本管理 → 开发版本
3. 找到刚上传的版本，点击「选为体验版」
4. 扫描二维码添加体验成员

## 6. 配置服务器域名

在小程序后台配置合法域名：

1. 开发管理 → 开发设置 → 服务器域名
2. 添加 request 合法域名：
   - `https://your-domain.com` (生产环境)
   - 或开发阶段勾选「不校验合法域名」

## 常见问题

### Q: 上传失败，提示私钥错误？
- 确认从微信后台下载的密钥文件正确
- 确认密钥文件路径配置正确
- 确认 AppID 与密钥匹配

### Q: 小程序无法连接后端？
- 检查 `app.js` 中的 `apiBaseUrl` 配置
- 确认后端服务已启动且可访问
- 开发阶段可在开发者工具中勾选「不校验合法域名」

### Q: 如何更新后端地址？
修改 `mini-program/app.js` 中的 `apiBaseUrl`，重新上传即可。

## 当前配置状态

- [ ] 后端服务地址已配置
- [ ] 微信 AppID 已获取
- [ ] 上传密钥已下载
- [ ] 小程序已上传
- [ ] 体验版已设置
