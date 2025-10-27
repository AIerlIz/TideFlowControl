# -*- coding: utf-8 -*-

import time
import libtorrent as lt
import logging

logger = logging.getLogger(__name__)

def download_torrent(magnet_link: str, shared_state, process_id: int):
    """
    执行单个磁力链接下载任务的函数，设计为在单独的进程中运行。

    :param magnet_link: 要下载的磁力链接
    :param shared_state: multiprocessing.Manager创建的共享状态对象
    :param process_id: 当前进程的ID，用于日志记录
    """
    logger.info(f"[进程-{process_id}] 开始 Torrent 下载: {magnet_link[:30]}...")

    ses = lt.session({'listen_interfaces': '0.0.0.0:6881'})
    params = lt.parse_magnet_uri(magnet_link)
    # 将文件“下载”到内存中，避免写入磁盘
    params.save_path = '/dev/shm' 
    handle = ses.add_torrent(params)

    start_time = time.time()
    last_payload_download = 0
    is_paused_by_controller = False

    try:
        while not handle.status().is_seeding:
            s = handle.status()
            
            # 1. 检查是否需要暂停或恢复
            if shared_state.is_paused() and not is_paused_by_controller:
                handle.pause()
                is_paused_by_controller = True
                logger.info(f"[进程-{process_id}] 暂停 Torrent 下载。")
            elif not shared_state.is_paused() and is_paused_by_controller:
                handle.resume()
                is_paused_by_controller = False
                logger.info(f"[进程-{process_id}] 恢复 Torrent 下载。")

            # 如果被控制器暂停，则在此处循环等待
            if is_paused_by_controller:
                time.sleep(1)
                continue

            # 2. 更新共享的下载总量
            current_download = s.total_done
            if current_download > last_payload_download:
                delta = current_download - last_payload_download
                shared_state.add_bytes(delta)
                last_payload_download = current_download

            # 汇报瞬时速度 (MB/s)
            speed_mbps = s.download_rate / (1024 * 1024)
            shared_state.update_speed(process_id, speed_mbps)
            
            time.sleep(2) # 每2秒更新一次状态

        # 下载结束，将自己的速度清零
        shared_state.update_speed(process_id, 0)
        end_time = time.time()
        duration = end_time - start_time
        total_downloaded_mb = last_payload_download / (1024 * 1024)
        if duration > 0:
            speed_mbps = (last_payload_download * 8) / (duration * 1024 * 1024)
            logger.info(f"[进程-{process_id}] 完成 Torrent 下载: {handle.name()}。"
                         f"已下载 {total_downloaded_mb:.2f} MB，用时 {duration:.2f}秒。"
                         f"平均速度: {speed_mbps:.2f} Mbps")
        else:
            logger.info(f"[进程-{process_id}] 瞬间完成 Torrent 下载: {handle.name()}。")

    except Exception as e:
        logger.error(f"[进程-{process_id}] Torrent 下载期间发生意外错误: {e}")
