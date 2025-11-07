"""Converters between legacy JSON files and MySQL storage."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .repository import add_step, get_or_create_run, upsert_conversation


def import_checkpoint_folder(sim_name: str, checkpoints_dir: Path) -> None:
    folder = checkpoints_dir / sim_name
    if not folder.exists():
        raise FileNotFoundError(f"checkpoint folder {folder} not found")

    conversation_path = folder / "conversation.json"
    conversation_data: Dict[str, List] = {}
    if conversation_path.exists():
        conversation_data = json.loads(conversation_path.read_text(encoding="utf-8"))

    json_files = sorted([p for p in folder.glob("*.json") if p.name != "conversation.json"])
    if not json_files:
        return

    stride = 10
    start_time = None

    for file_path in json_files:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        stride = int(data.get("stride", stride))
        if start_time is None:
            start_time = datetime.strptime(data["time"], "%Y%m%d-%H:%M").strftime("%Y-%m-%dT%H:%M:%S")

    run = get_or_create_run(sim_name, start_time, stride)

    for file_path in json_files:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        step = int(data.get("step", 0))
        sim_time = data.get("time", "")
        add_step(run.id, step, sim_time, data)

    for step_time, payload in conversation_data.items():
        upsert_conversation(run.id, step_time, payload)
