# -*- coding: utf-8 -*-

import logging
from flask import Flask, jsonify, render_template, request
from multiprocessing import Manager

# 假设 shared_state 和 shared_config 在父目录中
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared_state import SharedState
from shared_config import SharedConfig

logger = logging.getLogger(__name__)

# 全局变量，将在启动时被注入
shared_state_ref = None
shared_config_ref = None

app = Flask(__name__, template_folder='templates')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/api/status')
def api_status():
    if not shared_state_ref:
        return jsonify({"error": "Shared state not initialized"}), 500
    
    total_speed_mbps = shared_state_ref.get_total_speed_mbps()
    total_downloaded_gb = shared_state_ref.get_bytes() / (1024**3)
    is_paused = shared_state_ref.is_paused()
    
    # 获取每个进程的速度详情
    process_speeds = dict(shared_state_ref._process_speeds)
    active_connections = len([s for s in process_speeds.values() if s > 0])

    return jsonify({
        "total_speed_mbps": total_speed_mbps,
        "total_downloaded_gb": total_downloaded_gb,
        "is_paused": is_paused,
        "active_connections": active_connections,
        "concurrent_downloads": shared_config_ref.get("CONCURRENT_DOWNLOADS", 0)
    })

@app.route('/api/settings', methods=['GET'])
def get_settings():
    if not shared_config_ref:
        return jsonify({"error": "Shared config not initialized"}), 500
    return jsonify(shared_config_ref.get_all())

@app.route('/api/settings', methods=['POST'])
def update_settings():
    if not shared_config_ref:
        return jsonify({"error": "Shared config not initialized"}), 500
    
    new_settings = request.json
    if not new_settings:
        return jsonify({"error": "Invalid data"}), 400

    try:
        # 验证和更新配置
        # 注意：对于需要重启才能生效的配置，前端应给出提示
        shared_config_ref.set("DOWNLOAD_LIMIT_GB", int(new_settings.get("DOWNLOAD_LIMIT_GB")))
        shared_config_ref.set("RESET_TIME", str(new_settings.get("RESET_TIME")))
        
        # 解析时间窗口
        windows_raw = new_settings.get("ALLOWED_TIME_WINDOWS", [])
        windows = []
        if isinstance(windows_raw, list):
            for w in windows_raw:
                if isinstance(w, list) and len(w) == 2:
                    windows.append([str(w[0]), str(w[1])])
        shared_config_ref.set("ALLOWED_TIME_WINDOWS", windows)

        # 需要重启的配置
        shared_config_ref.set("CONCURRENT_DOWNLOADS", int(new_settings.get("CONCURRENT_DOWNLOADS")))
        shared_config_ref.set("HTTP_URLS", [str(url) for url in new_settings.get("HTTP_URLS", [])])
        shared_config_ref.set("MAGNET_LINKS", [str(link) for link in new_settings.get("MAGNET_LINKS", [])])

        if shared_config_ref.save_config():
            return jsonify({"success": True, "message": "Settings updated successfully."})
        else:
            return jsonify({"success": False, "message": "Failed to save settings."}), 500
            
    except (ValueError, TypeError) as e:
        return jsonify({"error": f"Invalid data format: {e}"}), 400

def run_web_server(shared_state, shared_config, host='0.0.0.0', port=5245):
    global shared_state_ref, shared_config_ref
    shared_state_ref = shared_state
    shared_config_ref = shared_config
    
    # 禁用 Flask 的默认日志，以避免与主日志冲突
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    logger.info(f"Web 服务器正在启动，访问 http://{host}:{port}")
    app.run(host=host, port=port, debug=False)

if __name__ == '__main__':
    # 这是一个用于测试的简单示例
    # 在实际应用中，run_web_server 将由 main.py 在一个单独的线程中调用
    manager = Manager()
    mock_state = SharedState(manager)
    mock_config = SharedConfig(manager)
    
    # 模拟一些数据
    mock_state.add_bytes(1024**3 * 5.5) # 5.5 GB
    mock_state.update_speed(0, 1.2)
    mock_state.update_speed(1, 0.8)

    run_web_server(mock_state, mock_config)
