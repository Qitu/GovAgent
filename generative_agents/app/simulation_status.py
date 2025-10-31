"""
Simulation status management module
Used to track and manage the state of simulation processes
"""

import threading
from datetime import datetime

# Global simulation status
simulation_status = {
    'running': False,
    'current_simulation': None,
    'last_output': '',
    'last_error': '',
    'progress': 0,
    'start_time': None,
    'process': None
}

# Thread lock
status_lock = threading.Lock()

def update_status(key, value):
    """Thread-safe status update"""
    with status_lock:
        simulation_status[key] = value

def get_status():
    """Thread-safe status retrieval"""
    with status_lock:
        return simulation_status.copy()

def reset_status():
    """Reset simulation status"""
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
    """Check whether a simulation is running"""
    with status_lock:
        return simulation_status['running']

def set_running(simulation_name=None):
    """Mark simulation as running"""
    with status_lock:
        simulation_status['running'] = True
        simulation_status['current_simulation'] = simulation_name
        simulation_status['start_time'] = datetime.now()
        simulation_status['progress'] = 0

def set_stopped():
    """Mark simulation as stopped"""
    with status_lock:
        simulation_status['running'] = False
        simulation_status['current_simulation'] = None
        simulation_status['process'] = None