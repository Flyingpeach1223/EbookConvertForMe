# 使用 Python 基础镜像
FROM python:3.9-slim

# 安装系统依赖和 Calibre
RUN apt-get update && apt-get install -y \
    wget \
    xdg-utils \
    xz-utils \
    && wget -nv -O- https://download.calibre-ebook.com/linux-installer.sh | sh /dev/stdin \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件
COPY backend/requirements.txt .

# 安装 Python 依赖
RUN pip install -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 5001

# 启动命令
CMD ["python", "backend/app.py"] 