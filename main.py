# -*- coding: utf-8 -*-

import multiprocessing
import time
import random
import logging
from datetime import datetime, time as dt_time, timedelta

import config
from downloader import download_http, download_torrent
from shared_state import SharedState
from time_utils import is_in_time_window, get_next_allowed_time_start

# 在主模块中进行一次全局日志配置
logging.basicConfig(
    level=config.LOG_LEVEL,
    format='%(asctime)s - %(processName)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def worker_process(process_id, shared_state):
    """
    工作进程的执行体。会不断随机选择任务并执行。
    """
    logger.info(f"工作进程-{process_id} 已启动。")
    all_tasks = []
    if config.HTTP_URLS:
        all_tasks.extend([('http', url) for url in config.HTTP_URLS])
    if config.MAGNET_LINKS:
        all_tasks.extend([('torrent', link) for link in config.MAGNET_LINKS])

    if not all_tasks:
        logger.warning(f"工作进程-{process_id}：未配置下载链接。正在退出。")
        return

    while True:
        task_type, link = random.choice(all_tasks)
        try:
            if task_type == 'http':
                download_http(link, shared_state, process_id)
            elif task_type == 'torrent':
                download_torrent(link, shared_state, process_id)
        except Exception as e:
            logger.error(f"工作进程-{process_id} 捕获到异常：{e}")
        
        logger.info(f"工作进程-{process_id} 完成了一个任务。5秒后将使用新的随机任务重新启动。")
        time.sleep(5)


def main():
    # 设置多进程启动方式，这在某些平台上可以提高稳定性
    multiprocessing.set_start_method("fork", force=True)
    
    manager = multiprocessing.Manager()
    shared_state = SharedState(manager)
    shared_state.load_state()

    # 在启动工作进程前，先强制进入暂停状态，等待主循环进行状态检查
    shared_state.pause()
    logger.info("正在进行初始状态检查，下载进程将等待所有状态检查完毕后启动。")

    # 启动工作进程
    processes = []
    for i in range(config.CONCURRENT_DOWNLOADS):
        p = multiprocessing.Process(
            target=worker_process,
            args=(i, shared_state),
            name=f"Worker-{i}" # 为进程命名
        )
        processes.append(p)
        p.start()

    logger.info(f"{config.CONCURRENT_DOWNLOADS} 个工作进程已启动。")

    # 主控制循环
    last_summary_time = time.time()
    
    try:
        while True:
            # 1. 检查并执行每日重置
            now = datetime.now()
            last_reset_dt = datetime.fromtimestamp(shared_state._last_reset_time.value)
            reset_time_obj = dt_time.fromisoformat(config.RESET_TIME)
            today_reset_dt = now.replace(hour=reset_time_obj.hour, minute=reset_time_obj.minute, second=0, microsecond=0)

            if now >= today_reset_dt and last_reset_dt < today_reset_dt:
                logger.info("已到达每日重置时间。")
                shared_state.reset()
                shared_state.save_state()

            # 2. 确定当前是否应该处于暂停状态
            limit_bytes = config.DOWNLOAD_LIMIT_GB * (1024 ** 3)
            current_bytes = shared_state.get_bytes()
            in_window = is_in_time_window()
            should_be_paused = (current_bytes >= limit_bytes) or not in_window

            # 3. 根据状态执行操作
            if should_be_paused:
                # 如果应该暂停
                if not shared_state.is_paused():
                    shared_state.pause()
                    # 组合暂停原因
                    pause_reasons = []
                    if not in_window:
                        pause_reasons.append("不在允许的时间窗口内")
                    if current_bytes >= limit_bytes:
                        pause_reasons.append(f"已达到下载限制: {current_bytes / (1024**3):.2f}/{config.DOWNLOAD_LIMIT_GB} GB")
                    logger.info(f"{' 且 '.join(pause_reasons)}。正在暂停。")

                # 计算下一个可能的恢复时间
                possible_resume_times = []
                now_dt = datetime.now()

                # 如果是因为超出时间窗口，计算下一个窗口的开始时间
                if not in_window:
                    possible_resume_times.append(get_next_allowed_time_start())

                # 如果是因为达到下载限制，计算下一个重置时间
                if current_bytes >= limit_bytes:
                    reset_time_obj = dt_time.fromisoformat(config.RESET_TIME)
                    next_reset_dt = now_dt.replace(hour=reset_time_obj.hour, minute=reset_time_obj.minute, second=0, microsecond=0)
                    if now_dt >= next_reset_dt:
                        next_reset_dt += timedelta(days=1)
                    possible_resume_times.append(next_reset_dt)
                
                # 如果没有可行的恢复时间（理论上不应发生），则短暂休眠后重试
                if not possible_resume_times:
                    logger.warning("无法确定恢复时间，将在60秒后重试。")
                    time.sleep(60)
                    continue

                # 选择最晚的时间点，以确保所有暂停条件都已解除
                next_resume_time = max(possible_resume_times)
                sleep_duration = (next_resume_time - now_dt).total_seconds()

                if sleep_duration > 0:
                    total_downloaded_gb = shared_state.get_bytes() / (1024**3)
                    logger.info(
                        f"[暂停] 总下载量: {total_downloaded_gb:.2f} GB | "
                        f"计划下次恢复时间: {next_resume_time.strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    shared_state.save_state()
                    time.sleep(sleep_duration)
                
                # 休眠结束后，重新开始循环以评估新状态
                continue
            
            else:
                # 如果应该恢复
                if shared_state.is_paused():
                    shared_state.resume()

                # 检查工作进程存活状态
                alive_processes = [p for p in processes if p.is_alive()]
                if len(alive_processes) < len(processes):
                    logger.warning("一个或多个工作进程已退出。请检查日志以获取错误信息。")
                if not alive_processes:
                    logger.error("所有工作进程均已终止。正在关闭。")
                    break

                # 定期打印状态报告
                current_time = time.time()
                if current_time - last_summary_time >= 5:
                    total_speed = shared_state.get_total_speed_mbps()
                    total_downloaded_gb = shared_state.get_bytes() / (1024**3)
                    active_downloads = len([s for s in shared_state._process_speeds.values() if s > 0])
                    
                    logger.info(
                        f"[下载] 总速度: {total_speed:.2f} MB/s | "
                        f"活动连接: {active_downloads}/{config.CONCURRENT_DOWNLOADS} | "
                        f"总下载量: {total_downloaded_gb:.2f} GB"
                    )
                    last_summary_time = current_time
                    shared_state.save_state()

            # 短暂休眠，避免CPU空转
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("收到关闭信号。正在终止工作进程。")
        for p in processes:
            p.terminate()
            p.join()
        shared_state.save_state()
        logger.info("关闭完成。")

if __name__ == "__main__":
    main()
