from flask import Flask, render_template, request, jsonify
import subprocess
import os
import threading
from datetime import datetime, timedelta
import json

app = Flask(
    __name__,
    template_folder="frontend/templates",
    static_folder="frontend/static",
    static_url_path="/static",
)
app.config['JSON_AS_ASCII'] = False

# 模拟状态跟踪
simulation_status = {
    'running': False,
    'process': None,
    'last_output': '',
    'last_error': ''
}

# 从start.py导入personas
from start import personas

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/start_simulation', methods=['POST'])
def start_simulation():
    if simulation_status['running']:
        return jsonify({'status': 'error', 'message': '已有模拟在运行'})
    
    try:
        if not request.is_json:
            return jsonify({'status': 'error', 'message': '请使用application/json格式'})
            
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': '请求数据无效'})
            
        name = str(data.get('name', 'sim-test'))
        steps = int(data.get('steps', 10))
        stride = int(data.get('stride', 10))
        
        if not name:
            return jsonify({'status': 'error', 'message': '模拟名称不能为空'})

        # 构建命令路径，确保使用绝对路径
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cmd = f"python {os.path.join(base_dir, 'start.py')} --name {name} --step {steps} --stride {stride}"
        
        def run_simulation():
            try:
                # 重置状态
                simulation_status['running'] = True
                simulation_status['last_output'] = f"执行命令: {cmd}\n"
                simulation_status['last_error'] = ''
                
                # 执行命令并捕获输出
                result = subprocess.run(
                    cmd,
                    shell=True,
                    cwd=base_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace'
                )
                
                # 保存输出
                simulation_status['last_output'] += result.stdout
                if result.stderr:
                    simulation_status['last_error'] = result.stderr
                    
            except subprocess.CalledProcessError as e:
                simulation_status['last_error'] = f"命令执行失败: {e.stderr}"
                simulation_status['last_output'] += f"\n错误输出: {e.stdout}"
            except Exception as e:
                simulation_status['last_error'] = f"运行时错误: {str(e)}"
            finally:
                simulation_status['running'] = False
        
        thread = threading.Thread(target=run_simulation)
        thread.daemon = True
        thread.start()
        
        return jsonify({'status': 'success', 'message': '模拟已启动'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'启动模拟失败: {str(e)}'})

@app.route('/compress_data', methods=['POST'])
def compress_data():
    try:
        if not request.is_json:
            return jsonify({'status': 'error', 'message': '请使用application/json格式'})
            
        name = request.get_json().get('name', 'sim-test')
        if not name:
            return jsonify({'status': 'error', 'message': '模拟名称不能为空'})

        # 构建命令路径，确保使用绝对路径
        base_dir = os.path.dirname(os.path.abspath(__file__))
        cmd = f"python {os.path.join(base_dir, 'compress.py')} --name {name}"
        
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=base_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        if result.returncode == 0:
            return jsonify({
                'status': 'success',
                'output': result.stdout
            })
        else:
            return jsonify({
                'status': 'error',
                'output': result.stderr or result.stdout
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'output': f'压缩数据时出错: {str(e)}'
        })

@app.route('/get_status')
def get_status():
    return jsonify({
        'running': simulation_status['running'],
        'last_output': simulation_status['last_output'],
        'last_error': simulation_status['last_error'],
        'timestamp': datetime.now().isoformat()
    })

@app.route('/stop_simulation', methods=['POST'])
def stop_simulation():
    if simulation_status['running'] and simulation_status['process']:
        try:
            simulation_status['process'].terminate()
            simulation_status['running'] = False
            simulation_status['last_output'] += '\n模拟已手动停止\n'
            return jsonify({'status': 'success'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'停止模拟失败: {str(e)}'})
    return jsonify({'status': 'error', 'message': '没有正在运行的模拟'})

@app.route('/replay', methods=['GET'])
def replay():
    name = request.args.get("name", "")          # 记录名称
    step = int(request.args.get("step", 0))      # 回放起始步数
    speed = int(request.args.get("speed", 2))    # 回放速度（0~5）
    zoom = float(request.args.get("zoom", 0.8))  # 画面缩放比例

    if not name:
        return f"Invalid name of the simulation: '{name}'"

    compressed_folder = f"results/compressed/{name}"
    replay_file = f"{compressed_folder}/movement.json"
    
    if not os.path.exists(replay_file):
        return f"The data file doesn‘t exist: '{replay_file}'<br />Run compress.py to generate the data first."

    with open(replay_file, "r", encoding="utf-8") as f:
        params = json.load(f)

    if step < 1:
        step = 1
    if step > 1:
        # 重新设置回放的起始时间
        t = datetime.fromisoformat(params["start_datetime"])
        dt = t + timedelta(minutes=params["stride"]*(step-1))
        params["start_datetime"] = dt.isoformat()
        step = (step-1) * 60 + 1  # frames_per_step=60
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
        "index.html",
        persona_names=personas,
        step=step,
        play_speed=speed,
        zoom=zoom,
        **params
    )

if __name__ == '__main__':
    app.run(
        debug=True,
        use_reloader=False,
        threaded=True
    )