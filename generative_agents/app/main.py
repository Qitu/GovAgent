from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
import os
import json
import subprocess
import threading
import time
import logging
from .auth import login_required
from .utils import get_simulation_list, get_recent_activities, get_analytics_data
from .simulation_status import simulation_status

# 从start.py导入personas
import sys
sys.path.append('..')
from start import personas

# 导入compress模块的常量
try:
    from compress import frames_per_step, file_movement
except ImportError:
    # 如果无法导入，使用默认值
    frames_per_step = 60
    file_movement = "movement.json"

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
@login_required
def dashboard():
    """Dashboard - System Overview"""
    # Get simulation statistics
    simulations = get_simulation_list()
    agents_count = len(personas)
    
    # Get recent simulation activities
    recent_activities = get_recent_activities()
    
    # System status
    system_status = {
        'total_simulations': len(simulations),
        'active_agents': agents_count,
        'running_simulation': simulation_status['running'],
        'current_simulation': simulation_status.get('current_simulation', 'None')
    }
    
    return render_template('crm/dashboard.html', 
                         system_status=system_status,
                         recent_activities=recent_activities,
                         simulations=simulations[:5])  # Show recent 5 simulations

@main_bp.route('/agents')
@login_required
def agents_management():
    """Agent Management Page"""
    agents_data = []
    
    for persona in personas:
        agent_path = f"frontend/static/assets/village/agents/{persona}/agent.json"
        if os.path.exists(agent_path):
            with open(agent_path, 'r', encoding='utf-8') as f:
                agent_data = json.load(f)
                agents_data.append({
                    'name': persona,
                    'age': agent_data.get('scratch', {}).get('age', 'Unknown'),
                    'innate': agent_data.get('scratch', {}).get('innate', 'Unknown'),
                    'lifestyle': agent_data.get('scratch', {}).get('lifestyle', 'Unknown'),
                    'currently': agent_data.get('currently', 'Unknown'),
                    'portrait': f"/static/assets/village/agents/{persona}/portrait.png"
                })
    
    return render_template('crm/agents.html', agents=agents_data)

@main_bp.route('/agent/<agent_name>')
@login_required
def agent_detail(agent_name):
    """Agent Detail Page"""
    if agent_name not in personas:
        flash('Agent does not exist!', 'error')
        return redirect(url_for('main.agents_management'))
    
    agent_path = f"frontend/static/assets/village/agents/{agent_name}/agent.json"
    if not os.path.exists(agent_path):
        flash('Agent data file does not exist!', 'error')
        return redirect(url_for('main.agents_management'))
    
    with open(agent_path, 'r', encoding='utf-8') as f:
        agent_data = json.load(f)
    
    return render_template('crm/agent_detail.html', 
                         agent_name=agent_name, 
                         agent_data=agent_data)

@main_bp.route('/agent/create')
@login_required
def create_agent_page():
    """Create Agent Page"""
    return render_template('crm/agent_create.html')

@main_bp.route('/agent/<agent_name>/edit')
@login_required
def edit_agent_page(agent_name):
    """Edit Agent Page"""
    if agent_name not in personas:
        flash('Agent does not exist!', 'error')
        return redirect(url_for('main.agents_management'))
    
    agent_path = f"frontend/static/assets/village/agents/{agent_name}/agent.json"
    if not os.path.exists(agent_path):
        flash('Agent data file does not exist!', 'error')
        return redirect(url_for('main.agents_management'))
    
    with open(agent_path, 'r', encoding='utf-8') as f:
        agent_data = json.load(f)
    
    return render_template('crm/agent_edit.html', 
                         agent_name=agent_name, 
                         agent_data=agent_data)

@main_bp.route('/simulations')
@login_required
def simulations_management():
    """Simulation Management Page"""
    simulations = get_simulation_list()
    return render_template('crm/simulations.html', simulations=simulations)

@main_bp.route('/simulation/<sim_name>')
@login_required
def simulation_detail(sim_name):
    """Simulation Detail Page"""
    sim_path = f"results/checkpoints/{sim_name}"
    if not os.path.exists(sim_path):
        flash('Simulation does not exist!', 'error')
        return redirect(url_for('main.simulations_management'))
    
    # 获取模拟文件列表
    files = sorted(os.listdir(sim_path))
    json_files = [f for f in files if f.endswith('.json') and f != 'conversation.json']
    
    simulation_info = {
        'name': sim_name,
        'files_count': len(json_files),
        'has_conversation': 'conversation.json' in files,
        'created_time': datetime.fromtimestamp(os.path.getctime(sim_path)).strftime('%Y-%m-%d %H:%M:%S')
    }
    
    # 获取最新的模拟状态
    if json_files:
        latest_file = os.path.join(sim_path, json_files[-1])
        with open(latest_file, 'r', encoding='utf-8') as f:
            latest_data = json.load(f)
            simulation_info.update({
                'current_step': latest_data.get('step', 0),
                'current_time': latest_data.get('time', 'Unknown'),
                'stride': latest_data.get('stride', 0)
            })
    
    return render_template('crm/simulation_detail.html', 
                         simulation=simulation_info,
                         files=json_files)

@main_bp.route('/analytics')
@login_required
def analytics():
    """Data Analytics Page"""
    # Get analytics data
    analytics_data = get_analytics_data()
    return render_template('crm/analytics.html', analytics=analytics_data)

@main_bp.route('/settings')
@login_required
def settings():
    """System Settings Page"""
    return render_template('crm/settings.html')

@main_bp.route('/replay', methods=['GET'])
def replay():
    """Replay Page - 完整的回放功能，与replay.py完全一致"""
    name = request.args.get("name", "")          # 记录名称
    step = int(request.args.get("step", 0))      # 回放起始步数
    speed = int(request.args.get("speed", 2))    # 回放速度（0~5）
    zoom = float(request.args.get("zoom", 0.8))  # 画面缩放比例

    if len(name) > 0:
        compressed_folder = f"results/compressed/{name}"
    else:
        return f"Invalid name of the simulation: '{name}'"

    replay_file = f"{compressed_folder}/{file_movement}"
    if not os.path.exists(replay_file):
        return f"The data file doesn't exist: '{replay_file}'<br />Run compress.py to generate the data first."

    with open(replay_file, "r", encoding="utf-8") as f:
        params = json.load(f)

    if step < 1:
        step = 1
    if step > 1:
        # 重新设置回放的起始时间
        t = datetime.fromisoformat(params["start_datetime"])
        dt = t + timedelta(minutes=params["stride"]*(step-1))
        params["start_datetime"] = dt.isoformat()
        step = (step-1) * frames_per_step + 1
        if step >= len(params["all_movement"]):
            step = len(params["all_movement"])-1

        # 重新设置Agent的初始位置
        for agent in params["persona_init_pos"].keys():
            persona_init_pos = params["persona_init_pos"]
            persona_step_pos = params["all_movement"][f"{step}"]
            persona_init_pos[agent] = persona_step_pos[agent]["movement"]

    if speed < 0:
        speed = 0
    elif speed > 5:
        speed = 5
    speed = 2 ** speed

    return render_template(
        "replay_standalone.html",
        persona_names=personas,
        step=step,
        play_speed=speed,
        zoom=zoom,
        **params
    )

@main_bp.route('/test_images', methods=['GET'])
def test_images():
    """Test image loading"""
    name = request.args.get("name", "sim-test3")
    
    compressed_folder = f"results/compressed/{name}"
    replay_file = f"{compressed_folder}/movement.json"
    
    if os.path.exists(replay_file):
        with open(replay_file, "r", encoding="utf-8") as f:
            params = json.load(f)
        persona_names = list(params.get("persona_init_pos", {}).keys())
    else:
        persona_names = ["阿伊莎", "克劳斯", "玛丽亚"]  # 默认测试名称
    
    return render_template('crm/test_images.html', persona_names=persona_names)

@main_bp.route('/replay_debug', methods=['GET'])
def replay_debug():
    """Debug version of replay page"""
    from datetime import timedelta
    
    name = request.args.get("name", "sim-test3")  # Default to sim-test3
    step = int(request.args.get("step", 1))
    speed = int(request.args.get("speed", 2))
    zoom = float(request.args.get("zoom", 0.8))

    compressed_folder = f"results/compressed/{name}"
    replay_file = f"{compressed_folder}/movement.json"
    
    if not os.path.exists(replay_file):
        return f"Replay data file doesn't exist: {replay_file}"

    try:
        with open(replay_file, "r", encoding="utf-8") as f:
            params = json.load(f)

        persona_names = list(params.get("persona_init_pos", {}).keys())
        
        return render_template('crm/replay_debug.html', 
                             simulation_name=name,
                             sim_name=name,
                             persona_names=persona_names,
                             step=step,
                             speed=speed,
                             zoom=zoom,
                             sec_per_step=params.get("sec_per_step", 10),
                             play_speed=params.get("play_speed", 4),
                             all_movement=params.get("all_movement", {}),
                             start_datetime=params.get("start_datetime", "2025-02-13T09:30:00"),
                             persona_init_pos=params.get("persona_init_pos", {}))
                             
    except Exception as e:
        return f"Error loading replay data: {str(e)}"

@main_bp.route('/replay_fixed', methods=['GET'])
def replay_fixed():
    """Fixed version of replay page"""
    from datetime import timedelta
    
    name = request.args.get("name", "sim-test3")
    step = int(request.args.get("step", 1))
    speed = int(request.args.get("speed", 2))
    zoom = float(request.args.get("zoom", 0.8))

    compressed_folder = f"results/compressed/{name}"
    replay_file = f"{compressed_folder}/movement.json"
    
    if not os.path.exists(replay_file):
        flash(f"Replay data file doesn't exist for '{name}'. Please compress the simulation first.", 'error')
        return redirect(url_for('main.simulations_management'))

    try:
        with open(replay_file, "r", encoding="utf-8") as f:
            params = json.load(f)

        persona_names = list(params.get("persona_init_pos", {}).keys())
        
        return render_template('crm/replay_fixed.html', 
                             simulation_name=name,
                             sim_name=name,
                             persona_names=persona_names,
                             step=step,
                             speed=speed,
                             zoom=zoom,
                             sec_per_step=params.get("sec_per_step", 10),
                             play_speed=params.get("play_speed", 4),
                             start_datetime=params.get("start_datetime", "2025-02-13T09:30:00"),
                             persona_init_pos=params.get("persona_init_pos", {}))
                             
    except Exception as e:
        flash(f"Error loading replay data: {str(e)}", 'error')
        return redirect(url_for('main.simulations_management'))

# Global variables to store simulation process and output
simulation_process = None
simulation_output = []
simulation_lock = threading.Lock()

@main_bp.route('/create_simulation')
@login_required
def create_simulation():
    """Create Simulation Page"""
    return render_template('crm/create_simulation.html')

@main_bp.route('/start_simulation', methods=['POST'])
@login_required
def start_simulation():
    """Start Simulation"""
    global simulation_process, simulation_output
    
    # Get form data
    name = request.form.get('name', 'sim-test')
    start_time = request.form.get('start_time', '20250213-09:30')
    step = request.form.get('step', '10')
    stride = request.form.get('stride', '10')
    
    # Validate input
    if not name or not start_time:
        return jsonify({'success': False, 'message': 'Please fill in required parameters'})
    
    # 如果同名目录已存在，自动追加时间戳后缀，避免 start.py 进入 input 阻塞
    checkpoints_dir = os.path.join('results', 'checkpoints')
    os.makedirs(checkpoints_dir, exist_ok=True)
    orig_name = name
    sim_path = os.path.join(checkpoints_dir, name)
    if os.path.exists(sim_path):
        suffix = datetime.now().strftime("-%Y%m%d-%H%M%S")
        name = f"{name}{suffix}"
    
    # Check if simulation is already running
    with simulation_lock:
        if simulation_process and simulation_process.poll() is None:
            return jsonify({'success': False, 'message': '已有模拟在运行中'})
        
        # 清空之前的输出
        simulation_output = []
        
        # 构建命令（注意：name 可能已被追加后缀）
        cmd = [
            'python3', 'start.py',
            '--name', name,
            '--start', start_time,
            '--step', step,
            '--stride', stride
        ]
        
        try:
            # 清空之前的输出
            simulation_output.clear()
            
            # 设置环境变量禁用Python缓冲
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            env['PYTHONIOENCODING'] = 'utf-8'
            
            # 启动模拟进程
            simulation_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,  # 防止任何交互式输入导致阻塞
                universal_newlines=True,
                bufsize=0,  # 无缓冲，实时输出
                env=env,    # 传递环境变量
                cwd=os.getcwd()  # 确保在正确的工作目录
            )
            
            # 更新模拟状态
            simulation_status['running'] = True
            simulation_status['current_simulation'] = name
            
            # 启动输出监控线程
            output_thread = threading.Thread(target=monitor_simulation_output)
            output_thread.daemon = True
            output_thread.start()
            
            return jsonify({
                'success': True, 
                'message': f'模拟 "{name}" 已开始启动，正在初始化环境...',
                'simulation_name': name
            })
            
        except Exception as e:
            return jsonify({'success': False, 'message': f'启动失败: {str(e)}'})

def monitor_simulation_output():
    """监控模拟输出的线程函数（稳定版：逐行读取）"""
    global simulation_process, simulation_output

    if not simulation_process:
        return

    try:
        with simulation_lock:
            simulation_output.append({
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'content': '🚀 模拟进程已启动，正在初始化...'
            })

        # 逐行读取，避免 bytes/str 混用与复杂非阻塞
        # universal_newlines=True 已启用，stdout 为文本模式
        # 注意：readline 是阻塞的，但我们配合 poll() 与小睡眠实现近实时
        while True:
            # 若进程仍在运行，尽量按行读取
            if simulation_process.poll() is None:
                line = simulation_process.stdout.readline()
                if line:
                    line = line.rstrip('\n').strip()
                    if line:
                        with simulation_lock:
                            simulation_output.append({
                                'timestamp': datetime.now().strftime('%H:%M:%S'),
                                'content': line
                            })
                            if len(simulation_output) > 1000:
                                simulation_output[:] = simulation_output[-1000:]
                else:
                    # 没有新行，短暂休息
                    time.sleep(0.05)
            else:
                # 进程已结束，读尽剩余行
                remainder = simulation_process.stdout.read()
                if remainder:
                    for line in remainder.splitlines():
                        line = line.strip()
                        if line:
                            with simulation_lock:
                                simulation_output.append({
                                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                                    'content': line
                                })
                                if len(simulation_output) > 1000:
                                    simulation_output[:] = simulation_output[-1000:]
                exit_code = simulation_process.poll()
                with simulation_lock:
                    simulation_output.append({
                        'timestamp': datetime.now().strftime('%H:%M:%S'),
                        'content': f'✅ 模拟进程结束，退出码: {exit_code}'
                    })
                    simulation_status['running'] = False
                    simulation_status['current_simulation'] = None
                break

    except Exception as e:
        with simulation_lock:
            simulation_output.append({
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'content': f'❌ 监控输出时发生严重错误: {str(e)}'
            })
            simulation_status['running'] = False
            simulation_status['current_simulation'] = None

@main_bp.route('/simulation_output')
@login_required
def get_simulation_output():
    """获取模拟输出"""
    # 获取客户端最后接收的行数
    last_line = int(request.args.get('last_line', 0))
    
    with simulation_lock:
        output_count = len(simulation_output)
        is_running = simulation_process and simulation_process.poll() is None
        
        # 如果没有输出但有进程在运行，添加状态信息
        if output_count == 0 and is_running:
            return jsonify({
                'output': [{
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'content': '模拟进程正在启动中...',
                    'line_number': 0
                }],
                'running': True,
                'total_lines': 1,
                'has_new_data': True
            })
        elif output_count == 0:
            return jsonify({
                'output': [{
                    'timestamp': datetime.now().strftime('%H:%M:%S'),
                    'content': '等待模拟启动...',
                    'line_number': 0
                }],
                'running': False,
                'total_lines': 1,
                'has_new_data': last_line == 0
            })
        
        # 只返回新的输出行
        new_output = []
        if last_line < output_count:
            for i, line in enumerate(simulation_output[last_line:], start=last_line):
                new_line = dict(line)
                new_line['line_number'] = i
                new_output.append(new_line)
        
        return jsonify({
            'output': new_output,
            'running': is_running,
            'total_lines': output_count,
            'has_new_data': len(new_output) > 0
        })

@main_bp.route('/stop_simulation', methods=['POST'])
@login_required
def stop_simulation():
    """停止模拟"""
    global simulation_process
    
    with simulation_lock:
        if simulation_process and simulation_process.poll() is None:
            try:
                simulation_process.terminate()
                time.sleep(2)
                if simulation_process.poll() is None:
                    simulation_process.kill()
                
                simulation_status['running'] = False
                simulation_status['current_simulation'] = 'None'
                
                return jsonify({'success': True, 'message': '模拟已停止'})
            except Exception as e:
                return jsonify({'success': False, 'message': f'停止失败: {str(e)}'})
        else:
            return jsonify({'success': False, 'message': '没有运行中的模拟'})