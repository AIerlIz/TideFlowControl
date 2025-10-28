# -*- coding: utf-8 -*-

import logging
from datetime import datetime, time as dt_time, timedelta

logger = logging.getLogger(__name__)

def is_in_time_window(allowed_time_windows: list[list[str]]):
    """检查当前时间是否在允许的下载时间窗口内"""
    now = datetime.now().time()
    if not allowed_time_windows:
        return True # 如果没有配置时间窗口，则默认全天允许

    for start_str, end_str in allowed_time_windows:
        try:
            start_time = dt_time.fromisoformat(start_str)
            end_time = dt_time.fromisoformat(end_str)
            if start_time <= end_time:
                if start_time <= now < end_time:
                    return True
            else:  # 跨天的时间段
                if now >= start_time or now < end_time:
                    return True
        except ValueError:
            logger.warning(f"跳过无效的时间窗口格式: {start_str}-{end_str}")
            continue
    return False

def get_next_allowed_time_start(allowed_time_windows: list[list[str]]):
    """
    计算下一个允许下载时间窗口的开始时间。
    """
    now = datetime.now()
    next_starts = []

    if not allowed_time_windows:
        # 如果没有配置时间窗口，默认明天凌晨开始
        return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    for start_str, _ in allowed_time_windows:
        try:
            start_time_obj = dt_time.fromisoformat(start_str)
        except ValueError:
            logger.warning(f"跳过无效的时间窗口开始时间格式: {start_str}")
            continue
        
        
        # 尝试今天的开始时间
        today_start = now.replace(
            hour=start_time_obj.hour,
            minute=start_time_obj.minute,
            second=0, microsecond=0
        )
        if today_start > now:
            next_starts.append(today_start)
        
        # 尝试明天的开始时间 (如果今天的已经过了)
        tomorrow_start = (now + timedelta(days=1)).replace(
            hour=start_time_obj.hour,
            minute=start_time_obj.minute,
            second=0, microsecond=0
        )
        next_starts.append(tomorrow_start)
    
    if not next_starts:
        # 如果没有配置时间窗口，或者解析失败，默认明天凌晨开始
        logger.warning("未配置有效的时间窗口。默认将在明天 00:00 恢复。")
        return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    return min(next_starts)
