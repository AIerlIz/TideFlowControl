# -*- coding: utf-8 -*-

import time
import json
import os
import logging
from datetime import datetime

import config

logger = logging.getLogger(__name__)

class SharedState:
    """
    一个用于管理所有进程共享状态的类，确保线程安全。
    """
    def __init__(self, manager):
        self._manager = manager
        self._lock = manager.Lock()
        self._bytes_downloaded = manager.Value('d', 0.0)
        self._is_paused = manager.Value('b', False)
        self._last_reset_time = manager.Value('d', time.time())
        # 新增：用于存储每个进程的瞬时速度 (MB/s)
        self._process_speeds = manager.dict()

    def add_bytes(self, num_bytes):
        with self._lock:
            self._bytes_downloaded.value += num_bytes

    def get_bytes(self):
        with self._lock:
            return self._bytes_downloaded.value

    def is_paused(self):
        with self._lock:
            return self._is_paused.value

    def pause(self):
        with self._lock:
            if not self._is_paused.value:
                self._is_paused.value = True
                logger.info("执行已暂停。")

    def resume(self):
        with self._lock:
            if self._is_paused.value:
                self._is_paused.value = False
                logger.info("执行已恢复。")

    def reset(self):
        with self._lock:
            self._bytes_downloaded.value = 0.0
            self._last_reset_time.value = time.time()
            self._process_speeds.clear() # 重置时也清空速度字典
            logger.info("下载量已重置。")

    def save_state(self):
        with self._lock:
            state = {
                'bytes_downloaded': self._bytes_downloaded.value,
                'last_reset_time': self._last_reset_time.value
            }
            with open(config.STATE_FILE, 'w') as f:
                json.dump(state, f)
            logger.debug(f"状态已保存: {state}")

    def load_state(self):
        if os.path.exists(config.STATE_FILE):
            with self._lock:
                with open(config.STATE_FILE, 'r') as f:
                    state = json.load(f)
                    self._bytes_downloaded.value = state.get('bytes_downloaded', 0.0)
                    self._last_reset_time.value = state.get('last_reset_time', time.time())
                logger.info(f"状态已加载：已下载 {self._bytes_downloaded.value / (1024**3):.2f} GB，上次重置于 {datetime.fromtimestamp(self._last_reset_time.value)}")

    def update_speed(self, process_id, speed_mbps):
        with self._lock:
            self._process_speeds[process_id] = speed_mbps

    def get_total_speed_mbps(self):
        with self._lock:
            return sum(self._process_speeds.values())
