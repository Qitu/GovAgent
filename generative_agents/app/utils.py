"""Utility helper functions"""
import os
import json
from datetime import datetime

def get_simulation_list():
    """Retrieve list of simulations"""
    simulations = []
    checkpoints_path = "results/checkpoints"
    
    if os.path.exists(checkpoints_path):
        for sim_name in os.listdir(checkpoints_path):
            sim_path = os.path.join(checkpoints_path, sim_name)
            if os.path.isdir(sim_path):
                files = os.listdir(sim_path)
                json_files = [f for f in files if f.endswith('.json') and f != 'conversation.json']
                
                sim_info = {
                    'name': sim_name,
                    'files_count': len(json_files),
                    'has_conversation': 'conversation.json' in files,
                    'created_time': datetime.fromtimestamp(os.path.getctime(sim_path)),
                }
                
                compressed_path = f"results/compressed/{sim_name}"
                is_compressed = (os.path.exists(compressed_path) and 
                               os.path.exists(os.path.join(compressed_path, 'movement.json')) and
                               os.path.exists(os.path.join(compressed_path, 'simulation.md')))
                
                sim_info['has_compressed'] = is_compressed
                sim_info['is_compressed'] = is_compressed
                
                if sim_info['has_conversation'] and is_compressed:
                    sim_info['status'] = 'completed_compressed'
                elif sim_info['has_conversation'] and not is_compressed:
                    sim_info['status'] = 'completed_uncompressed'
                else:
                    sim_info['status'] = 'running'
                
                simulations.append(sim_info)
    
    return sorted(simulations, key=lambda x: x['created_time'], reverse=True)

def get_recent_activities():
    """Retrieve recent activities"""
    activities = []
    
    simulations = get_simulation_list()
    for sim in simulations[:10]:
        activities.append({
            'type': 'simulation_created',
            'message': f'New simulation created: {sim["name"]}',
            'timestamp': sim['created_time'],
            'icon': 'fas fa-play-circle'
        })
    
    return activities

def get_analytics_data():
    """Retrieve analytics data"""
    import sys
    sys.path.append('..')
    from start import personas
    
    simulations = get_simulation_list()
    
    total_simulations = len(simulations)
    total_agents = len(personas)
    
    monthly_stats = {}
    for sim in simulations:
        month_key = sim['created_time'].strftime('%Y-%m')
        monthly_stats[month_key] = monthly_stats.get(month_key, 0) + 1
    
    return {
        'total_simulations': total_simulations,
        'total_agents': total_agents,
        'monthly_stats': monthly_stats,
        'agent_distribution': {persona: 1 for persona in personas}
    }

def load_agent_data(agent_name):
    """Load agent data"""
    agent_path = f"frontend/static/assets/village/agents/{agent_name}/agent.json"
    if os.path.exists(agent_path):
        with open(agent_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def get_simulation_info(sim_name):
    """Retrieve detailed simulation info"""
    sim_path = f"results/checkpoints/{sim_name}"
    if not os.path.exists(sim_path):
        return None
    
    files = sorted(os.listdir(sim_path))
    json_files = [f for f in files if f.endswith('.json') and f != 'conversation.json']
    
    simulation_info = {
        'name': sim_name,
        'files_count': len(json_files),
        'has_conversation': 'conversation.json' in files,
        'created_time': datetime.fromtimestamp(os.path.getctime(sim_path)).strftime('%Y-%m-%d %H:%M:%S')
    }
    
    if json_files:
        latest_file = os.path.join(sim_path, json_files[-1])
        with open(latest_file, 'r', encoding='utf-8') as f:
            latest_data = json.load(f)
            simulation_info.update({
                'current_step': latest_data.get('step', 0),
                'current_time': latest_data.get('time', 'Unknown'),
                'stride': latest_data.get('stride', 0)
            })
    
    return simulation_info