# -*- coding: utf-8 -*-

import json
import logging
import os

logger = logging.getLogger(__name__)

class SharedConfig:
    """
    管理所有进程共享的配置，确保线程安全并支持动态更新。
    """
    def __init__(self, manager, config_path='data/config.json'):
        self._manager = manager
        self._lock = manager.Lock()
        self._config_path = config_path
        self._config_data = manager.dict()
        self.load_config()

    def get(self, key, default=None):
        with self._lock:
            return self._config_data.get(key, default)

    def get_all(self):
        with self._lock:
            # 返回字典的深拷贝，以避免外部修改
            return dict(self._config_data)

    def set(self, key, value):
        with self._lock:
            self._config_data[key] = value

    def save_config(self):
        with self._lock:
            try:
                # 确保目录存在
                os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
                with open(self._config_path, 'w') as f:
                    json.dump(self.get_all(), f, indent=2)
                logger.info("配置已成功保存。")
                return True
            except Exception as e:
                logger.error(f"保存配置时出错: {e}")
                return False

    def load_config(self):
        with self._lock:
            try:
                if os.path.exists(self._config_path):
                    with open(self._config_path, 'r') as f:
                        data = json.load(f)
                        self._config_data.update(data)
                    logger.info("配置已加载。")
                else:
                    logger.warning("配置文件不存在，将使用默认值。")
                    # 如果文件不存在，可以在这里设置一些默认值
                    default_config = {
                        "HTTP_URLS": [],
                        "MAGNET_LINKS": [],
                        "CONCURRENT_DOWNLOADS": 5,
                        "DOWNLOAD_LIMIT_GB": 500,
                        "RESET_TIME": "03:00",
                        "ALLOWED_TIME_WINDOWS": [["00:00", "23:59"]]
                    }
                    self._config_data.update(default_config)
                    self.save_config() # 保存默认配置
            except Exception as e:
                logger.error(f"加载配置时出错: {e}")
