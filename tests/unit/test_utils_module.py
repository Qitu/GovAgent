import json
import os
from datetime import datetime

import pytest

from generative_agents.app.utils import (
    get_simulation_list,
    get_recent_activities,
    get_analytics_data,
    load_agent_data,
    get_simulation_info,
)


def test_get_simulation_list_and_recent_activities(monkeypatch, tmp_path):
    # Prepare checkpoints directory with fake data
    cp = tmp_path / 'results' / 'checkpoints' / 'sim1'
    cp.mkdir(parents=True)
    (cp / 'a.json').write_text('{}', encoding='utf-8')
    (cp / 'conversation.json').write_text('{}', encoding='utf-8')

    # compressed present
    comp = tmp_path / 'results' / 'compressed' / 'sim1'
    comp.mkdir(parents=True)
    (comp / 'movement.json').write_text('{}', encoding='utf-8')
    (comp / 'simulation.md').write_text('# doc', encoding='utf-8')

    import os as _os
    orig_exists = _os.path.exists
    orig_listdir = _os.listdir
    orig_isdir = _os.path.isdir
    orig_getctime = _os.path.getctime

    def fake_exists(path):
        path = str(path)
        path = path.replace('results/checkpoints', str(tmp_path / 'results' / 'checkpoints'))
        path = path.replace('results/compressed', str(tmp_path / 'results' / 'compressed'))
        return orig_exists(path)

    def fake_listdir(path):
        path = str(path)
        path = path.replace('results/checkpoints', str(tmp_path / 'results' / 'checkpoints'))
        return orig_listdir(path)

    def fake_getctime(path):
        path = str(path)
        path = path.replace('results/checkpoints/sim1', str(cp))
        return orig_getctime(path)

    monkeypatch.setattr(_os.path, 'exists', fake_exists)
    monkeypatch.setattr(_os, 'listdir', fake_listdir)
    
    def fake_isdir(path):
        path = str(path)
        path = path.replace('results/checkpoints/sim1', str(cp))
        return orig_isdir(path)
    monkeypatch.setattr(_os.path, 'isdir', fake_isdir)

    monkeypatch.setattr(_os.path, 'getctime', fake_getctime)

    sims = get_simulation_list()
    assert len(sims) == 1 and sims[0]['status'] == 'completed_compressed'

    recent = get_recent_activities()
    assert len(recent) >= 1 and recent[0]['type'] == 'simulation_created'


def test_get_analytics_data_and_load_agent(monkeypatch, tmp_path):
    # personas from dummy 'start' module provided in conftest
    # create minimal agent json
    agent_dir = tmp_path / 'frontend' / 'static' / 'assets' / 'village' / 'agents' / 'Alice'
    agent_dir.mkdir(parents=True)
    (agent_dir / 'agent.json').write_text(json.dumps({'scratch': {'age': 20}, 'currently': 'X'}), encoding='utf-8')

    import os as _os
    orig_exists = _os.path.exists

    def fake_exists(path):
        path = str(path)
        path = path.replace('frontend/static/assets/village/agents/Alice/agent.json', str(agent_dir / 'agent.json'))
        return orig_exists(path)

    monkeypatch.setattr(_os.path, 'exists', fake_exists)

    import builtins as _builtins
    orig_open = _builtins.open
    def fake_open(path, *args, **kwargs):
        p = str(path).replace('frontend/static/assets/village/agents/Alice/agent.json', str(agent_dir / 'agent.json'))
        return orig_open(p, *args, **kwargs)
    monkeypatch.setattr(_builtins, 'open', fake_open)

    from generative_agents.app.utils import load_agent_data
    data = load_agent_data('Alice')
    assert data and data.get('currently') == 'X'

    # The analytics uses start.personas; functions should not error
    from generative_agents.app.utils import get_analytics_data
    stats = get_analytics_data()
    assert 'total_simulations' in stats and 'total_agents' in stats


def test_get_simulation_info(monkeypatch, tmp_path):
    cp = tmp_path / 'results' / 'checkpoints' / 'simx'
    cp.mkdir(parents=True)
    (cp / 'a.json').write_text(json.dumps({'step': 3, 'time': 'T', 'stride': 1}), encoding='utf-8')

    import os as _os
    orig_exists = _os.path.exists
    orig_listdir = _os.listdir

    def fake_exists(path):
        path = str(path)
        path = path.replace('results/checkpoints/simx', str(cp))
        return orig_exists(path)

    def fake_listdir(path):
        path = str(path)
        path = path.replace('results/checkpoints/simx', str(cp))
        return orig_listdir(path)

    def fake_exists2(path):
        # For checking each inner file path
        path = str(path)
        path = path.replace('results/checkpoints/simx', str(cp))
        return orig_exists(path)

    monkeypatch.setattr(_os.path, 'exists', fake_exists2)
    monkeypatch.setattr(_os, 'listdir', fake_listdir)

    orig_getctime = _os.path.getctime
    def fake_getctime2(path):
        p = str(path).replace('results/checkpoints/simx', str(cp))
        return orig_getctime(p)
    monkeypatch.setattr(_os.path, 'getctime', fake_getctime2)

    import builtins as _builtins
    orig_open = _builtins.open
    def fake_open2(path, *args, **kwargs):
        p = str(path).replace('results/checkpoints/simx', str(cp))
        return orig_open(p, *args, **kwargs)
    monkeypatch.setattr(_builtins, 'open', fake_open2)

    info = get_simulation_info('simx')
    assert info and info['files_count'] == 1 and info['current_step'] == 3
