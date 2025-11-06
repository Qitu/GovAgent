"""Utility helper functions with MySQL backing."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, List
import json

from db import repository
from db.session import ensure_engine
from start import personas


def get_simulation_list() -> List[Dict]:
    ensure_engine()
    sims = repository.list_runs()
    simulations: List[Dict] = []
    for run in sims:
        latest_step = repository.get_latest_step(run.name)
        steps = repository.get_steps_for_run(run.name)
        has_conversation = bool(repository.get_conversation_map(run.name))
        is_compressed = False  # TBD: detect based on DB once movement stored
        status = "running"
        if has_conversation and is_compressed:
            status = "completed_compressed"
        elif has_conversation:
            status = "completed_uncompressed"

        simulations.append(
            {
                "name": run.name,
                "files_count": len(steps),
                "has_conversation": has_conversation,
                "created_time": run.created_at,
                "has_compressed": is_compressed,
                "is_compressed": is_compressed,
                "status": status,
                "latest_step": latest_step.step_index if latest_step else 0,
                "latest_time": latest_step.sim_time if latest_step else None,
            }
        )
    return sorted(simulations, key=lambda x: x["created_time"], reverse=True)


def get_recent_activities() -> List[Dict]:
    activities = []
    for sim in get_simulation_list()[:10]:
        activities.append(
            {
                "type": "simulation_created",
                "message": f"New simulation created: {sim['name']}",
                "timestamp": sim["created_time"],
                "icon": "fas fa-play-circle",
            }
        )
    return activities


def get_analytics_data() -> Dict:
    ensure_engine()
    sims = get_simulation_list()
    monthly_stats: Dict[str, int] = {}
    for sim in sims:
        month_key = sim["created_time"].strftime("%Y-%m")
        monthly_stats[month_key] = monthly_stats.get(month_key, 0) + 1
    return {
        "total_simulations": len(sims),
        "total_agents": len(personas),
        "monthly_stats": monthly_stats,
        "agent_distribution": {persona: 1 for persona in personas},
    }


def load_agent_data(agent_name: str):
    agent_path = f"frontend/static/assets/village/agents/{agent_name}/agent.json"
    try:
        with open(agent_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def get_simulation_info(sim_name: str):
    ensure_engine()
    run = repository.get_run_with_details(sim_name)
    if run is None:
        return None
    steps = sorted(run.steps, key=lambda s: s.step_index)
    latest_step = steps[-1] if steps else None
    return {
        "name": sim_name,
        "files_count": len(steps),
        "has_conversation": bool(run.conversation_entries),
        "created_time": run.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "current_step": latest_step.step_index if latest_step else 0,
        "current_time": latest_step.sim_time if latest_step else "Unknown",
        "stride": run.stride_minutes,
    }
