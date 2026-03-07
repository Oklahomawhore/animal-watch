#!/bin/bash
# 启动脚本 - 在8083端口运行

cd "$(dirname "$0")/hikvision-backend"

# 设置端口
export PORT=8083

# 检查虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# 启动服务
echo "Starting server on port $PORT..."
python app.py
