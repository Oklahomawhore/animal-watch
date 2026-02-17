# 林麝健康监测系统 - 部署指南

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        用户层                                │
│  微信小程序  │  管理后台(Vue3)  │  开放API                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                        接入层                                │
│  Nginx (反向代理/负载均衡)                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                        服务层                                │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐      │
│  │ Backend  │  │EventProcessor│  │AnomalyDetector   │      │
│  │ (Node.js)│  │ (Go)         │  │ (Go)             │      │
│  └──────────┘  └──────────────┘  └──────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                        数据层                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ MySQL    │  │InfluxDB  │  │ Kafka    │  │ Redis    │   │
│  │ (关系型) │  │(时序数据) │  │ (消息)   │  │ (缓存)   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 快速启动

### 1. 环境要求

- Docker >= 20.10
- Docker Compose >= 2.0
- 内存 >= 4GB
- 磁盘 >= 20GB

### 2. 一键启动

```bash
# 克隆项目
git clone <repository-url>
cd lin-she-health-monitor

# 启动（自动创建环境变量）
./start.sh
```

### 3. 手动启动

```bash
# 1. 复制环境变量
cp .env.example .env

# 2. 编辑环境变量，设置安全密码
vim .env

# 3. 启动服务
docker-compose up -d

# 4. 查看日志
docker-compose logs -f
```

## 服务端口

| 服务 | 端口 | 说明 |
|------|------|------|
| Nginx | 80/443 | Web入口 |
| Backend API | 3000 | REST API |
| MySQL | 3306 | 关系数据库 |
| InfluxDB | 8086 | 时序数据库 |
| Kafka | 9092 | 消息队列 |
| Redis | 6379 | 缓存 |

## 数据持久化

数据存储在 Docker Volumes 中：

```
volumes/
├── mysql-data/     # MySQL数据
├── influxdb-data/  # InfluxDB数据
├── kafka-data/     # Kafka数据
└── redis-data/     # Redis数据
```

备份数据：
```bash
# 备份 MySQL
docker exec linshe-mysql mysqldump -u root -p linshe > backup.sql

# 备份 InfluxDB
docker exec linshe-influxdb influx backup /backup
```

## 生产部署

### 1. 修改环境变量

```bash
# .env
MYSQL_ROOT_PASSWORD=your_secure_root_password
MYSQL_PASSWORD=your_secure_mysql_password
INFLUX_PASSWORD=your_secure_influx_password
INFLUX_TOKEN=your_secure_influx_token
JWT_SECRET=your_super_secret_jwt_key
```

### 2. 配置SSL证书

```bash
# 将证书放入 nginx/ssl/
mkdir -p nginx/ssl
cp your.crt nginx/ssl/
cp your.key nginx/ssl/
```

### 3. 启动生产环境

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### 4. 配置反向代理（可选）

如果使用外部 Nginx：

```nginx
upstream linshe_backend {
    server localhost:3000;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.crt;
    ssl_certificate_key /path/to/cert.key;
    
    location / {
        proxy_pass http://linshe_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 监控与维护

### 查看服务状态

```bash
docker-compose ps
docker-compose top
```

### 查看日志

```bash
# 全部日志
docker-compose logs -f

# 指定服务
docker-compose logs -f backend
docker-compose logs -f event-processor
```

### 重启服务

```bash
# 重启全部
docker-compose restart

# 重启指定服务
docker-compose restart backend
docker-compose restart event-processor
```

### 更新部署

```bash
# 拉取最新代码
git pull

# 重建并重启
docker-compose down
docker-compose up -d --build
```

## 故障排查

### 服务无法启动

```bash
# 检查端口占用
netstat -tlnp | grep 3306

# 检查日志
docker-compose logs mysql
```

### 数据库连接失败

```bash
# 检查 MySQL 状态
docker exec linshe-mysql mysqladmin -u root -p ping

# 检查网络
docker network inspect linshe-network
```

### 重置数据

```bash
# 停止服务
docker-compose down

# 删除数据卷
docker-compose down -v

# 重新启动
docker-compose up -d
```

## 扩展部署

### 水平扩展 Backend

```yaml
# docker-compose.override.yml
version: '3.8'
services:
  backend:
    deploy:
      replicas: 3
```

### 使用外部数据库

```yaml
# docker-compose.override.yml
version: '3.8'
services:
  backend:
    environment:
      DB_HOST: your-rds-endpoint.amazonaws.com
      DB_PORT: 3306
```

## 安全建议

1. **修改默认密码**: 所有服务的默认密码必须在生产环境修改
2. **启用防火墙**: 只开放必要的端口
3. **定期备份**: 设置自动备份任务
4. **更新镜像**: 定期更新基础镜像版本
5. **使用HTTPS**: 生产环境必须使用SSL证书
6. **监控告警**: 配置系统监控和告警

## 性能优化

### 数据库优化

```sql
-- MySQL 配置优化
SET GLOBAL innodb_buffer_pool_size = 2147483648;  -- 2GB
SET GLOBAL max_connections = 500;
```

### InfluxDB 优化

```sql
-- 设置保留策略
CREATE RETENTION POLICY "30d" ON "linshe" DURATION 30d REPLICATION 1 DEFAULT;
```

## 常见问题

**Q: 如何修改服务端口？**
A: 编辑 `docker-compose.yml` 中的 ports 映射

**Q: 如何升级数据库？**
A: 执行 `database/migrations/` 中的 SQL 脚本

**Q: 如何查看 API 文档？**
A: 访问 `http://localhost:3000/api-docs`

## 技术支持

- 文档: https://docs.linshe.com
- 问题反馈: https://github.com/linshe/issues
- 邮箱: support@linshe.com
