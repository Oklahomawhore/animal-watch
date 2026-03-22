#!/bin/bash
# 小程序快速配置脚本
# 用法: ./configure-miniprogram.sh <后端服务器IP或域名>

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查参数
if [ $# -eq 0 ]; then
    echo -e "${RED}错误: 请提供后端服务器地址${NC}"
    echo "用法: $0 <服务器IP或域名>"
    echo "示例:"
    echo "  $0 192.168.1.100        # 使用IP地址"
    echo "  $0 api.linshe.com       # 使用域名"
    exit 1
fi

SERVER_ADDRESS=$1

# 判断是IP还是域名
if [[ $SERVER_ADDRESS =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    # IP地址，使用HTTP
    API_URL="http://${SERVER_ADDRESS}:5001/api/v2"
    echo -e "${YELLOW}检测到IP地址，使用HTTP协议${NC}"
else
    # 域名，使用HTTPS
    API_URL="https://${SERVER_ADDRESS}/api/v2"
    echo -e "${YELLOW}检测到域名，使用HTTPS协议${NC}"
fi

echo ""
echo "=========================================="
echo "📝 小程序后端地址配置"
echo "=========================================="
echo ""
echo "后端地址: $API_URL"
echo ""

# 小程序 app.js 路径
APP_JS_PATH="$(dirname "$0")/../mini-program/app.js"

# 检查文件是否存在
if [ ! -f "$APP_JS_PATH" ]; then
    echo -e "${RED}错误: 找不到 app.js 文件${NC}"
    echo "路径: $APP_JS_PATH"
    exit 1
fi

# 备份原文件
cp "$APP_JS_PATH" "${APP_JS_PATH}.backup"
echo "✅ 已备份原文件: app.js.backup"

# 替换后端地址
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s|apiBaseUrl: '.*'|apiBaseUrl: '${API_URL}'|" "$APP_JS_PATH"
else
    # Linux
    sed -i "s|apiBaseUrl: '.*'|apiBaseUrl: '${API_URL}'|" "$APP_JS_PATH"
fi

echo "✅ 已更新后端地址配置"

# 验证修改
if grep -q "$API_URL" "$APP_JS_PATH"; then
    echo -e "${GREEN}✅ 配置成功!${NC}"
    echo ""
    echo "当前配置:"
    grep "apiBaseUrl:" "$APP_JS_PATH" | head -1
    echo ""
    echo "=========================================="
    echo "下一步操作:"
    echo "=========================================="
    echo "1. 确保后端服务已启动:"
    echo "   cd hikvision-backend && python app.py"
    echo ""
    echo "2. 使用微信开发者工具上传小程序，或运行:"
    echo "   node scripts/upload-miniprogram.js upload"
    echo ""
else
    echo -e "${RED}❌ 配置失败，请手动检查 app.js${NC}"
    exit 1
fi
