# -*- coding: utf-8 -*-
import os

# 配置现在将直接从容器的环境变量中读取
# Docker Compose 会负责从 .env 文件加载这些变量

def parse_urls(env_var: str) -> list[str]:
    """解析逗号分隔的URL字符串"""
    if not env_var:
        return []
    return [url.strip() for url in env_var.split(',') if url.strip()]

def parse_time_windows(env_var: str) -> list[tuple[str, str]]:
    """解析时间窗口字符串 "HH:MM-HH:MM,..." """
    if not env_var:
        return [("00:00", "23:59")]
    windows = []
    parts = [part.strip() for part in env_var.split(',') if part.strip()]
    for part in parts:
        try:
            start, end = part.split('-')
            windows.append((start.strip(), end.strip()))
        except ValueError:
            print(f"警告：跳过无效的时间窗口格式: {part}")
    return windows if windows else [("00:00", "23:59")]

# 1. 要测试的链接列表 (从环境变量读取)
HTTP_URLS = parse_urls(os.getenv("HTTP_URLS", ""))
MAGNET_LINKS = parse_urls(os.getenv("MAGNET_LINKS", ""))

# 2. 并发设置
CONCURRENT_DOWNLOADS = int(os.getenv("CONCURRENT_DOWNLOADS", 5))

# 3. 流量控制
DOWNLOAD_LIMIT_GB = int(os.getenv("DOWNLOAD_LIMIT_GB", 500))

# 4. 重置时间点
RESET_TIME = os.getenv("RESET_TIME", "03:00")

# 5. 允许下载的时间段
ALLOWED_TIME_WINDOWS = parse_time_windows(os.getenv("ALLOWED_TIME_WINDOWS", "00:00-23:59"))

# 6. 状态持久化文件
# 将其指向容器内的一个挂载卷
STATE_FILE = "/app/data/download_state.json"

# 7. 下载块大小 (Bytes)
CHUNK_SIZE = 1024 * 1024  # 1 MB
