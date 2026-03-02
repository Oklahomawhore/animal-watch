# VideoPPT + Animal Watch 联合部署指南

## 架构说明

```
┌─────────────────────────────────────────────────────────┐
│                      阿里云服务器                         │
│                                                          │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │   Nginx     │────│  VideoPPT   │    │ AnimalWatch │ │
│  │  (反代入口)  │    │   (业务一)   │    │   (业务二)   │ │
│  └─────────────┘    └─────────────┘    └─────────────┘ │
│         │                                               │
│    ┌────┴────┐                                          │
│    │conf.d   │  ← 外挂配置目录                             │
│    │videoppt │                                          │
│    │animal   │                                          │
│    └─────────┘                                          │
└─────────────────────────────────────────────────────────┘
```

## 部署步骤

### 1. 启动 VideoPPT（业务一）

```bash
# 进入 VideoPPT 目录
cd /path/to/VideoPPT

# 确保 external-conf.d 目录存在
mkdir -p external-conf.d

# 启动业务一
docker-compose up -d

# 检查状态
docker-compose ps
```

### 2. 启动 Animal Watch（业务二）

```bash
# 进入 Animal Watch 目录
cd /path/to/animal-watch

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 HIK_APP_KEY 和 HIK_APP_SECRET

# 启动业务二（会自动加入 videoppt-network 网络）
docker-compose up -d

# 检查状态
docker-compose ps
```

### 3. 外挂业务二配置到 VideoPPT 的 Nginx

```bash
# 将业务二的配置文件复制到 VideoPPT 的 external-conf.d 目录
cp /path/to/animal-watch/animalwatch.conf /path/to/VideoPPT/external-conf.d/

# 重启 VideoPPT 的 Nginx 容器（加载新配置）
cd /path/to/VideoPPT
docker-compose restart nginx

# 验证配置
docker-compose exec nginx nginx -t
```

## 访问地址

| 业务 | 地址 | 说明 |
|------|------|------|
| VideoPPT | http://localhost | 业务一（视频转PPT） |
| Animal Watch | http://localhost/api/callback | 业务二（海康互联回调） |
| Animal Watch API | http://localhost/api/devices | 设备管理接口 |

## 常用命令

```bash
# 查看所有容器状态
docker ps

# 查看 Nginx 日志
cd /path/to/VideoPPT
docker-compose logs -f nginx

# 重启单个业务
cd /path/to/VideoPPT && docker-compose restart
cd /path/to/animal-watch && docker-compose restart

# 更新业务二配置后重新加载
cd /path/to/VideoPPT
docker-compose exec nginx nginx -s reload
```

## 故障排查

### 1. 业务二无法访问

检查容器是否加入同一网络：
```bash
docker network ls
docker network inspect videoppt-network
```

### 2. Nginx 配置错误

检查配置文件语法：
```bash
cd /path/to/VideoPPT
docker-compose exec nginx nginx -t
```

### 3. 端口冲突

确保没有端口被占用：
```bash
netstat -tlnp | grep 80
netstat -tlnp | grep 443
```

## 注意事项

1. **网络名称**：确保 animal-watch 的 docker-compose.yml 中网络名是 `videoppt-network`（与 VideoPPT 创建的网络名一致）

2. **服务名称**：animal-watch 中的服务名是 `animalwatch`（与 nginx 配置中的 upstream 一致）

3. **配置文件权限**：确保 external-conf.d 目录有读取权限

4. **重启顺序**：先启动 VideoPPT，再启动 Animal Watch，最后复制配置并重启 Nginx
