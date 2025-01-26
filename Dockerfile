# 使用 Python 基础镜像
FROM python:3.9-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    wget \
    xdg-utils \
    xz-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制整个项目
COPY . .

# 安装 Python 依赖
RUN pip install -r backend/requirements.txt

# 安装 Calibre
RUN wget -nv -O- https://download.calibre-ebook.com/linux-installer.sh | sh /dev/stdin

# 暴露端口
EXPOSE 5001

# 启动命令
CMD ["python", "backend/app.py"] 