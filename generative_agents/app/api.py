from flask import Blueprint, request, jsonify
import subprocess
import os
import json
import threading
from datetime import datetime
from .auth import login_required
from .simulation_status import simulation_status

api_bp = Blueprint('api', __name__)

@api_bp.route('/start_simulation', methods=['POST'])
@login_required
def start_simulation():
    """Start Simulation API"""
    if simulation_status['running']:
        return jsonify({'status': 'error', 'message': 'A simulation is already running'})
    
    try:
        if not request.is_json:
            return jsonify({'status': 'error', 'message': 'Please use application/json format'})
            
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'Invalid request data'})
            
        name = str(data.get('name', 'sim-test'))
        steps = int(data.get('steps', 10))
        stride = int(data.get('stride', 10))
        
        if not name:
            return jsonify({'status': 'error', 'message': 'Simulation name cannot be empty'})

        # Build command path, ensure using absolute path
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cmd = f"python {os.path.join(base_dir, 'start.py')} --name {name} --step {steps} --stride {stride}"
        
        def run_simulation():
            try:
                # Reset status
                simulation_status['running'] = True
                simulation_status['current_simulation'] = name
                simulation_status['last_output'] = f"Executing command: {cmd}\n"
                simulation_status['last_error'] = ''
                simulation_status['progress'] = 0
                
                # Execute command and capture output
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
                simulation_status['progress'] = 100
                    
            except subprocess.CalledProcessError as e:
                simulation_status['last_error'] = f"Command execution failed: {e.stderr}"
                simulation_status['last_output'] += f"\nError output: {e.stdout}"
            except Exception as e:
                simulation_status['last_error'] = f"Runtime error: {str(e)}"
            finally:
                simulation_status['running'] = False
                simulation_status['current_simulation'] = None
        
        thread = threading.Thread(target=run_simulation)
        thread.daemon = True
        thread.start()
        
        return jsonify({'status': 'success', 'message': 'Simulation started'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed to start simulation: {str(e)}'})

@api_bp.route('/compress_data', methods=['POST'])
@login_required
def compress_data():
    """Compress Data API"""
    try:
        if not request.is_json:
            return jsonify({'status': 'error', 'message': 'Please use application/json format'})
            
        name = request.get_json().get('name')
        if not name:
            return jsonify({'status': 'error', 'message': 'Simulation name cannot be empty'})

        # Check if simulation exists
        checkpoints_path = f"results/checkpoints/{name}"
        if not os.path.exists(checkpoints_path):
            return jsonify({'status': 'error', 'message': f'Simulation "{name}" does not exist'})
        
        # Check if simulation is completed (has conversation.json file)
        conversation_file = os.path.join(checkpoints_path, 'conversation.json')
        if not os.path.exists(conversation_file):
            return jsonify({'status': 'error', 'message': f'Simulation "{name}" is not completed, cannot compress'})

        # Check if already compressed
        compressed_path = f"results/compressed/{name}"
        if os.path.exists(compressed_path):
            movement_file = os.path.join(compressed_path, 'movement.json')
            md_file = os.path.join(compressed_path, 'simulation.md')
            if os.path.exists(movement_file) and os.path.exists(md_file):
                return jsonify({'status': 'error', 'message': f'Simulation "{name}" has already been compressed'})

        # Build command path, ensure using absolute path
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cmd = f"python3 compress.py --name {name}"
        
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=base_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=300  # 5分钟超时
        )
        
        if result.returncode == 0:
            return jsonify({
                'status': 'success',
                'message': f'模拟 "{name}" 压缩成功',
                'output': result.stdout.strip() if result.stdout else '压缩完成'
            })
        else:
            error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
            return jsonify({
                'status': 'error',
                'message': f'压缩失败',
                'output': error_msg or '未知错误'
            })
    except subprocess.TimeoutExpired:
        return jsonify({
            'status': 'error',
            'message': '压缩超时',
            'output': '压缩过程超过5分钟，已取消操作'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Error occurred during compression',
            'output': f'Error details: {str(e)}'
        })

@api_bp.route('/delete_simulation', methods=['POST'])
@login_required
def delete_simulation():
    """Delete Simulation API"""
    try:
        if not request.is_json:
            return jsonify({'status': 'error', 'message': 'Please use application/json format'})
            
        name = request.get_json().get('name')
        if not name:
            return jsonify({'status': 'error', 'message': 'Simulation name cannot be empty'})

        # Check if simulation exists
        checkpoints_path = f"results/checkpoints/{name}"
        if not os.path.exists(checkpoints_path):
            return jsonify({'status': 'error', 'message': f'Simulation "{name}" does not exist'})

        import shutil
        
        # Delete checkpoints directory
        if os.path.exists(checkpoints_path):
            shutil.rmtree(checkpoints_path)
        
        # Delete compressed directory (if exists)
        compressed_path = f"results/compressed/{name}"
        if os.path.exists(compressed_path):
            shutil.rmtree(compressed_path)
        
        return jsonify({
            'status': 'success',
            'message': f'Simulation "{name}" has been successfully deleted'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Error occurred while deleting simulation',
            'details': str(e)
        })

@api_bp.route('/get_status')
@login_required
def get_status():
    """Get System Status API"""
    return jsonify({
        'running': simulation_status['running'],
        'current_simulation': simulation_status.get('current_simulation'),
        'progress': simulation_status.get('progress', 0),
        'last_output': simulation_status['last_output'],
        'last_error': simulation_status['last_error'],
        'timestamp': datetime.now().isoformat()
    })

@api_bp.route('/stop_simulation', methods=['POST'])
@login_required
def stop_simulation():
    """Stop Simulation API"""
    if simulation_status['running'] and simulation_status['process']:
        try:
            simulation_status['process'].terminate()
            simulation_status['running'] = False
            simulation_status['current_simulation'] = None
            simulation_status['last_output'] += '\nSimulation manually stopped\n'
            return jsonify({'status': 'success'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': f'Failed to stop simulation: {str(e)}'})
    return jsonify({'status': 'error', 'message': 'No running simulation found'})

# ==================== Agent Management API ====================

@api_bp.route('/agents', methods=['GET'])
@login_required
def get_agents():
    """Get All Agents List"""
    try:
        from start import personas
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
        
        return jsonify({'status': 'success', 'data': agents_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed to get agents list: {str(e)}'})

@api_bp.route('/agents/<agent_name>', methods=['GET'])
@login_required
def get_agent(agent_name):
    """Get Single Agent Details"""
    try:
        from start import personas
        
        if agent_name not in personas:
            return jsonify({'status': 'error', 'message': 'Agent does not exist'})
        
        agent_path = f"frontend/static/assets/village/agents/{agent_name}/agent.json"
        if not os.path.exists(agent_path):
            return jsonify({'status': 'error', 'message': 'Agent data file does not exist'})
        
        with open(agent_path, 'r', encoding='utf-8') as f:
            agent_data = json.load(f)
        
        return jsonify({'status': 'success', 'data': agent_data})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed to get agent details: {str(e)}'})

@api_bp.route('/agents', methods=['POST'])
@login_required
def create_agent():
    """Create New Agent"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['name', 'age', 'innate', 'lifestyle', 'currently']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'status': 'error', 'message': f'Missing required field: {field}'})
        
        agent_name = data['name']
        
        # Check if agent already exists
        agent_dir = f"frontend/static/assets/village/agents/{agent_name}"
        if os.path.exists(agent_dir):
            return jsonify({'status': 'error', 'message': 'Agent already exists'})
        
        # Create agent directory
        os.makedirs(agent_dir, exist_ok=True)
        
        # Create agent configuration file
        agent_config = {
            "name": agent_name,
            "currently": data['currently'],
            "scratch": {
                "age": data['age'],
                "innate": data['innate'],
                "lifestyle": data['lifestyle'],
                "living_area": data.get('living_area', 'Unknown'),
                "daily_schedule_hourly_org": data.get('daily_schedule', ''),
                "memory_stream": []
            }
        }
        
        agent_path = f"{agent_dir}/agent.json"
        with open(agent_path, 'w', encoding='utf-8') as f:
            json.dump(agent_config, f, ensure_ascii=False, indent=2)
        
        # Create default portrait (if not provided)
        portrait_path = f"{agent_dir}/portrait.png"
        if not os.path.exists(portrait_path):
            # Copy default portrait
            default_portrait = "frontend/static/assets/village/agents/default_portrait.png"
            if os.path.exists(default_portrait):
                import shutil
                shutil.copy2(default_portrait, portrait_path)
        
        # Update personas list
        import sys
        sys.path.append('..')
        from start import personas
        if agent_name not in personas:
            personas.append(agent_name)
        
        return jsonify({'status': 'success', 'message': 'Agent created successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed to create agent: {str(e)}'})

@api_bp.route('/agents/<agent_name>', methods=['PUT'])
@login_required
def update_agent(agent_name):
    """Update Agent Information"""
    try:
        from start import personas
        
        if agent_name not in personas:
            return jsonify({'status': 'error', 'message': 'Agent does not exist'})
        
        data = request.get_json()
        agent_path = f"frontend/static/assets/village/agents/{agent_name}/agent.json"
        
        if not os.path.exists(agent_path):
            return jsonify({'status': 'error', 'message': 'Agent data file does not exist'})
        
        # Read existing configuration
        with open(agent_path, 'r', encoding='utf-8') as f:
            agent_config = json.load(f)
        
        # Update configuration
        if 'currently' in data:
            agent_config['currently'] = data['currently']
        
        if 'scratch' in data:
            for key, value in data['scratch'].items():
                if key in agent_config['scratch']:
                    agent_config['scratch'][key] = value
        
        # Update top-level fields directly
        updatable_fields = ['age', 'innate', 'lifestyle', 'living_area', 'daily_schedule']
        for field in updatable_fields:
            if field in data:
                if field == 'daily_schedule':
                    agent_config['scratch']['daily_schedule_hourly_org'] = data[field]
                else:
                    agent_config['scratch'][field] = data[field]
        
        # Save updated configuration
        with open(agent_path, 'w', encoding='utf-8') as f:
            json.dump(agent_config, f, ensure_ascii=False, indent=2)
        
        return jsonify({'status': 'success', 'message': 'Agent updated successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed to update agent: {str(e)}'})

@api_bp.route('/agents/<agent_name>', methods=['DELETE'])
@login_required
def delete_agent(agent_name):
    """Delete Agent"""
    try:
        from start import personas
        
        if agent_name not in personas:
            return jsonify({'status': 'error', 'message': 'Agent does not exist'})
        
        # Delete agent directory
        agent_dir = f"frontend/static/assets/village/agents/{agent_name}"
        if os.path.exists(agent_dir):
            import shutil
            shutil.rmtree(agent_dir)
        
        # Remove from personas list
        if agent_name in personas:
            personas.remove(agent_name)
        
        return jsonify({'status': 'success', 'message': 'Agent deleted successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed to delete agent: {str(e)}'})

@api_bp.route('/agents/<agent_name>/memory', methods=['POST'])
@login_required
def add_agent_memory(agent_name):
    """Add Memory to Agent"""
    try:
        from start import personas
        
        if agent_name not in personas:
            return jsonify({'status': 'error', 'message': 'Agent does not exist'})
        
        data = request.get_json()
        description = data.get('description')
        
        if not description:
            return jsonify({'status': 'error', 'message': 'Memory description cannot be empty'})
        
        agent_path = f"frontend/static/assets/village/agents/{agent_name}/agent.json"
        
        if not os.path.exists(agent_path):
            return jsonify({'status': 'error', 'message': 'Agent data file does not exist'})
        
        # Read existing configuration
        with open(agent_path, 'r', encoding='utf-8') as f:
            agent_config = json.load(f)
        
        # Add memory
        memory_item = {
            'description': description,
            'created': datetime.now().isoformat(),
            'type': data.get('type', 'manual')
        }
        
        if 'memory_stream' not in agent_config['scratch']:
            agent_config['scratch']['memory_stream'] = []
        
        agent_config['scratch']['memory_stream'].append(memory_item)
        
        # Keep only the latest 100 memories
        if len(agent_config['scratch']['memory_stream']) > 100:
            agent_config['scratch']['memory_stream'] = agent_config['scratch']['memory_stream'][-100:]
        
        # Save configuration
        with open(agent_path, 'w', encoding='utf-8') as f:
            json.dump(agent_config, f, ensure_ascii=False, indent=2)
        
        return jsonify({'status': 'success', 'message': 'Memory added successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed to add memory: {str(e)}'})