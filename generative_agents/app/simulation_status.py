"""
模拟状态管理模块
用于跟踪和管理模拟进程的状态
"""

import threading
from datetime import datetime

# 全局模拟状态
simulation_status = {
    'running': False,
    'current_simulation': None,
    'last_output': '',
    'last_error': '',
    'progress': 0,
    'start_time': None,
    'process': None
}

# 线程锁
status_lock = threading.Lock()

def update_status(key, value):
    """线程安全地更新状态"""
    with status_lock:
        simulation_status[key] = value

def get_status():
    """线程安全地获取状态"""
    with status_lock:
        return simulation_status.copy()

def reset_status():
    """重置模拟状态"""
    with status_lock:
        simulation_status.update({
            'running': False,
            'current_simulation': None,
            'last_output': '',
            'last_error': '',
            'progress': 0,
            'start_time': None,
            'process': None
        })

def is_running():
    """检查模拟是否正在运行"""
    with status_lock:
        return simulation_status['running']

def set_running(simulation_name=None):
    """设置模拟为运行状态"""
    with status_lock:
        simulation_status['running'] = True
        simulation_status['current_simulation'] = simulation_name
        simulation_status['start_time'] = datetime.now()
        simulation_status['progress'] = 0

def set_stopped():
    """设置模拟为停止状态"""
    with status_lock:
        simulation_status['running'] = False
        simulation_status['current_simulation'] = None
        simulation_status['process'] = None