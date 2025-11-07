"""Data access helpers for simulations in MySQL."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional
from pathlib import Path

from sqlalchemy import Select, func, select
from sqlalchemy.orm import joinedload

from .models import ConversationEntry, SimulationRun, SimulationStep
from .session import session_scope


def get_or_create_run(name: str, start_time: Optional[str], stride: int) -> SimulationRun:
    with session_scope() as session:
        stmt = select(SimulationRun).where(SimulationRun.name == name)
        run = session.scalars(stmt).one_or_none()
        if run is None:
            run = SimulationRun(name=name, start_time=start_time, stride_minutes=stride)
            session.add(run)
            session.flush()
        return run


def update_run_metadata(run_id: int, start_time: Optional[str], stride: int) -> None:
    with session_scope() as session:
        run = session.get(SimulationRun, run_id)
        if run:
            if start_time:
                run.start_time = start_time
            run.stride_minutes = stride


def add_step(run_id: int, step_index: int, sim_time: str, state: Dict[str, Any]) -> None:
    with session_scope() as session:
        step = SimulationStep(run_id=run_id, step_index=step_index, sim_time=sim_time, state=state)
        session.add(step)


def add_steps(run_id: int, steps: Iterable[SimulationStep]) -> None:
    with session_scope() as session:
        session.add_all(list(steps))


def get_latest_step(name: str) -> Optional[SimulationStep]:
    with session_scope() as session:
        stmt = (
            select(SimulationStep)
            .join(SimulationRun, SimulationRun.id == SimulationStep.run_id)
            .where(SimulationRun.name == name)
            .order_by(SimulationStep.step_index.desc())
            .limit(1)
        )
        return session.scalars(stmt).one_or_none()


def upsert_conversation(run_id: int, step_time: str, payload: Dict[str, Any]) -> None:
    with session_scope() as session:
        stmt = (
            select(ConversationEntry)
            .where(
                ConversationEntry.run_id == run_id,
                ConversationEntry.step_time == step_time,
            )
        )
        entry = session.scalars(stmt).one_or_none()
        if entry:
            entry.payload = payload
        else:
            session.add(ConversationEntry(run_id=run_id, step_time=step_time, payload=payload))


def list_runs() -> List[SimulationRun]:
    with session_scope() as session:
        stmt = select(SimulationRun).order_by(SimulationRun.created_at.desc())
        return list(session.scalars(stmt).all())


def get_run_with_details(name: str) -> Optional[SimulationRun]:
    with session_scope() as session:
        stmt = (
            select(SimulationRun)
            .options(joinedload(SimulationRun.steps), joinedload(SimulationRun.conversation_entries))
            .where(SimulationRun.name == name)
        )
        return session.scalars(stmt).one_or_none()


def delete_run(name: str) -> bool:
    with session_scope() as session:
        stmt = select(SimulationRun).where(SimulationRun.name == name)
        run = session.scalars(stmt).one_or_none()
        if run:
            session.delete(run)
            return True
        return False


def get_conversation_map(name: str) -> Dict[str, Any]:
    with session_scope() as session:
        stmt = (
            select(ConversationEntry.step_time, ConversationEntry.payload)
            .join(SimulationRun, SimulationRun.id == ConversationEntry.run_id)
            .where(SimulationRun.name == name)
        )
        data: Dict[str, Any] = {}
        for step_time, payload in session.execute(stmt):
            data[step_time] = payload
        return data


def has_conversation(name: str) -> bool:
    with session_scope() as session:
        stmt = (
            select(func.count())
            .select_from(ConversationEntry)
            .join(SimulationRun, SimulationRun.id == ConversationEntry.run_id)
            .where(SimulationRun.name == name)
        )
        return (session.scalar(stmt) or 0) > 0


def get_steps_for_run(name: str) -> List[SimulationStep]:
    with session_scope() as session:
        stmt = (
            select(SimulationStep)
            .join(SimulationRun, SimulationRun.id == SimulationStep.run_id)
            .where(SimulationRun.name == name)
            .order_by(SimulationStep.step_index.asc())
        )
        return list(session.scalars(stmt).all())


def count_steps_for_run(name: str) -> int:
    with session_scope() as session:
        stmt = (
            select(func.count())
            .select_from(SimulationStep)
            .join(SimulationRun, SimulationRun.id == SimulationStep.run_id)
            .where(SimulationRun.name == name)
        )
        return session.scalar(stmt) or 0
