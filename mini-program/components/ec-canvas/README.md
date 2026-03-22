# ECharts 组件说明

## 安装方式

本项目使用 npm 管理 ECharts 依赖，不再直接将 echarts.js 提交到 Git。

### 首次设置

```bash
cd mini-program
npm install
```

`postinstall` 脚本会自动将 echarts 复制到 `components/ec-canvas/` 目录。

### 更新 ECharts

```bash
npm update echarts
```

### 手动复制（如果需要）

```bash
npm run copy:echarts
```

## 使用的版本

- **包**: echarts (npm)
- **文件**: `echarts.simple.min.js` (精简版，约 493KB)
- **完整版**: 如需完整版，修改 `package.json` 中的 `copy:echarts` 脚本

## 为什么这样设计？

1. **版本管理**: 通过 package.json 锁定 ECharts 版本
2. **Git 瘦身**: 不提交大文件到 Git 仓库
3. **自动同步**: npm install 时自动复制到正确位置
4. **微信小程序兼容**: 使用 simple 版本，体积更小

## 注意事项

- `components/ec-canvas/echarts.js` 已被加入 `.gitignore`
- 部署时需要先运行 `npm install`
- 微信开发者工具中需要开启"使用 npm 模块"并构建 npm
