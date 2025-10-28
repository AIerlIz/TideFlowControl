# ---- 1. 构建阶段 ----
FROM python:3.9-alpine AS builder

# 安装编译时所需的系统依赖
RUN apk add --no-cache \
    libtorrent-rasterbar-dev \
    g++ \
    build-base

# 创建一个目录用于存放安装好的Python包
WORKDIR /install

# 复制依赖文件并安装
# 使用 --prefix 将包安装到指定目录，而不是系统目录
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix="/install" -r requirements.txt


# ---- 2. 最终镜像阶段 ----
FROM python:3.9-alpine

# 安装运行时所需的系统依赖
RUN apk add --no-cache libtorrent-rasterbar tzdata

# 设置时区
ENV TZ Asia/Shanghai

# 设置工作目录
WORKDIR /app

# 从构建阶段复制已安装的Python包
COPY --from=builder /install /usr/local

# 复制项目文件
COPY . .

# 暴露Web仪表盘端口
EXPOSE 5245

# 容器启动时执行的命令
CMD ["python", "main.py"]
