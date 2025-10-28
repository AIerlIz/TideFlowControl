# -*- coding: utf-8 -*-

import time
import requests
import logging
from config import CHUNK_SIZE

logger = logging.getLogger(__name__)

def download_http(url: str, shared_state, process_id: int):
    """
    执行单个HTTP下载任务的函数，设计为在单独的进程中运行。

    :param url: 要下载的文件的URL
    :param shared_state: multiprocessing.Manager创建的共享状态对象
    :param process_id: 当前进程的ID，用于日志记录
    """
    logger.info(f"[进程-{process_id}] 开始 HTTP 下载: {url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    start_time = time.time()
    try:
        with requests.get(url, stream=True, timeout=30, headers=headers) as r:
            r.raise_for_status()
            
            bytes_downloaded_session = 0
            last_report_time = time.time()
            bytes_since_last_report = 0

            for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
                # 1. 检查是否需要暂停
                while shared_state.is_paused():
                    shared_state.update_speed(process_id, 0) # 暂停时速度为0
                    time.sleep(1)
                    last_report_time = time.time() # 重置计时器

                # 2. 更新共享的下载总量
                if chunk:
                    chunk_len = len(chunk)
                    shared_state.add_bytes(chunk_len)
                    bytes_downloaded_session += chunk_len
                    bytes_since_last_report += chunk_len

                # 3. 定期计算并汇报速度
                current_time = time.time()
                if current_time - last_report_time >= 2: # 每2秒汇报一次
                    duration = current_time - last_report_time
                    speed_mbps = (bytes_since_last_report / (1024*1024)) / duration
                    shared_state.update_speed(process_id, speed_mbps)
                    
                    # 重置计数器
                    last_report_time = current_time
                    bytes_since_last_report = 0

            # 下载结束，将自己的速度清零
            shared_state.update_speed(process_id, 0)
            end_time = time.time()
            duration = end_time - start_time
            if duration > 0:
                speed_mbps = (bytes_downloaded_session * 8) / (duration * 1024 * 1024)
                logger.info(f"[进程-{process_id}] 完成下载: {url}。"
                             f"已下载 {bytes_downloaded_session / (1024*1024):.2f} MB "
                             f"用时 {duration:.2f}秒。平均速度: {speed_mbps:.2f} Mbps")
            else:
                logger.info(f"[进程-{process_id}] 瞬间完成下载: {url}。")

    except requests.exceptions.RequestException as e:
        logger.error(f"[进程-{process_id}] HTTP 下载错误 ({url}): {e}")
    except Exception as e:
        logger.error(f"[进程-{process_id}] HTTP 下载期间发生意外错误 ({url}): {e}")
