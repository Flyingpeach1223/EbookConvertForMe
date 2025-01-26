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

# 复制 requirements.txt
COPY backend/requirements.txt requirements.txt

# 安装 Python 依赖
RUN pip install -r requirements.txt

# 复制应用代码
COPY . .

# 安装 Calibre（使用非交互模式）
RUN wget -nv -O- https://raw.githubusercontent.com/kovidgoyal/calibre/master/setup/linux-installer.py | python -c "import sys; main=lambda:sys.stderr.write('Download failed\n'); exec(sys.stdin.read()); main()"

# 暴露端口
EXPOSE 3000

# 启动命令
CMD ["python", "backend/app.py"] 