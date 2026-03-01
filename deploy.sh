#!/bin/bash
# 部署脚本

set -e

echo "🚀 海康互联后端服务部署"
echo "========================"

# 检查环境
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装"
    exit 1
fi

echo "✅ Docker 环境检查通过"

# 创建环境变量文件
if [ ! -f .env ]; then
    echo "📝 创建环境变量文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件，设置正确的 AK/SK"
fi

# 创建数据目录
mkdir -p data nginx/ssl

echo "🐳 启动服务..."
docker-compose up -d --build

echo ""
echo "⏳ 等待服务启动..."
sleep 5

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose ps

echo ""
echo "✅ 部署完成！"
echo ""
echo "📋 访问地址："
echo "   - API 服务: http://localhost:5000"
echo "   - Nginx: http://localhost:80"
echo ""
echo "📝 常用命令："
echo "   查看日志: docker-compose logs -f"
echo "   停止服务: docker-compose down"
echo "   重启服务: docker-compose restart"
