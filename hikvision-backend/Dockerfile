# 使用 Python 3.11 作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 彻底清除所有旧源配置
RUN echo "" > /etc/apt/sources.list && \
    rm -rf /etc/apt/sources.list.d/*

# 添加阿里云 Debian 13（trixie）镜像源
RUN echo "deb http://mirrors.aliyun.com/debian/ trixie main non-free contrib" >> /etc/apt/sources.list && \
    echo "deb-src http://mirrors.aliyun.com/debian/ trixie main non-free contrib" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security/ trixie-security main" >> /etc/apt/sources.list && \
    echo "deb-src http://mirrors.aliyun.com/debian-security/ trixie-security main" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ trixie-updates main non-free contrib" >> /etc/apt/sources.list && \
    echo "deb-src http://mirrors.aliyun.com/debian/ trixie-updates main non-free contrib" >> /etc/apt/sources.list

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖（使用阿里云 PyPI 镜像）
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

# 复制应用代码
COPY . .

# 创建数据目录并设置权限
RUN mkdir -p /app/data && chmod 777 /app/data

# 暴露端口
EXPOSE 5000

# 设置环境变量
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1

# 启动命令
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
