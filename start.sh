#!/bin/bash

# 林麝健康监测系统 - 快速启动脚本

set -e

echo "🦌 林麝健康监测系统 - 快速启动"
echo "================================"

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

echo "✅ Docker 环境检查通过"

# 创建环境变量文件
if [ ! -f .env ]; then
    echo "📝 创建环境变量文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件，设置安全密码后再启动"
    exit 1
fi

echo "✅ 环境变量文件已存在"

# 创建必要目录
echo "📁 创建数据目录..."
mkdir -p data/mysql
mkdir -p data/influxdb
mkdir -p data/kafka
mkdir -p data/redis
mkdir -p logs

# 启动服务
echo "🚀 启动服务..."
docker-compose up -d

echo ""
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose ps

echo ""
echo "✅ 服务启动完成！"
echo ""
echo "📋 访问地址："
echo "   - API 服务: http://localhost:3000"
echo "   - 管理后台: http://localhost:8080"
echo "   - InfluxDB: http://localhost:8086"
echo ""
echo "📝 常用命令："
echo "   查看日志: docker-compose logs -f"
echo "   停止服务: docker-compose down"
echo "   重启服务: docker-compose restart"
echo ""
echo "🔐 默认登录信息："
echo "   用户名: admin"
echo "   密码: admin123"
echo ""
echo "⚠️  生产环境请务必修改默认密码！"
