import types

from generative_agents.modules.prompt.scratch import Scratch
from generative_agents.modules.memory.event import Event
from generative_agents.modules.memory.schedule import Schedule
from generative_agents.modules.memory.action import Action
from generative_agents.modules.utils.timer import set_timer


def make_scratch(monkeypatch):
    set_timer("20240101-00:00")
    s = Scratch(
        name="Alice",
        currently="Reading a book",
        config={
            "age": 25,
            "innate": "curious",
            "learned": "CS",
            "lifestyle": "early bird",
            "daily_plan": "study, exercise",
        },
    )
    # Avoid file IO by mocking build_prompt to return a static template string
    monkeypatch.setattr(s, "build_prompt", lambda template, data: f"TPL:{template}")
    return s


def test_prompt_wake_up_callback(monkeypatch):
    s = make_scratch(monkeypatch)
    cfg = s.prompt_wake_up()
    # Response with hour beyond 11 should clamp to 11
    assert cfg["callback"]("13:00") == 11
    # Normal hours should parse
    assert cfg["callback"]("7") == 7


def test_prompt_schedule_init_callback(monkeypatch):
    s = make_scratch(monkeypatch)
    cfg = s.prompt_schedule_init(6)
    resp = "1. task A。\n2) task B\n3) task C。"
    out = cfg["callback"](resp)
    assert out == ["task A", "task B", "task C"]


def test_prompt_schedule_daily_callback(monkeypatch):
    s = make_scratch(monkeypatch)
    cfg = s.prompt_schedule_daily(6, ["A", "B"])
    resp = """[06:00] Alice sleeping\n[07:00] Alice breakfast\n[08:00] reading。\n[09:00] Alice working\n[10:00] Alice study"""
    out = cfg["callback"](resp)
    assert out["06:00"] and out["07:00"] and out["08:00"] and out["09:00"] and out["10:00"]


def test_prompt_schedule_decompose_callback(monkeypatch):
    s = make_scratch(monkeypatch)
    # Minimal plan and schedule to call callback
    schedule = Schedule()
    plan = schedule.add_plan("do work", 30)
    cfg = s.prompt_schedule_decompose(plan, schedule)
    resp = "1) ...*计划* Writing code（耗时:10, 剩余:20）\n2) ...*计划* Review（耗时:10, 剩余:10）"
    out = cfg["callback"](resp)
    assert out[0] == ("Writing code", 10) and out[1] == ("Review", 10)


def test_prompt_schedule_revise_callback(monkeypatch):
    s = make_scratch(monkeypatch)
    schedule = Schedule()
    p = schedule.add_plan("work", 60, decompose=[{"idx":0,"describe":"read","start":0,"duration":30},{"idx":1,"describe":"plan","start":30,"duration":30}])
    action = Action(Event("Alice", describe="Alice coding"), duration=10)
    cfg = s.prompt_schedule_revise(action, schedule)
    resp = """[08:00 - 08:15] read\n[08:15 ~ 08:25] coding\n[08:25 至 09:00] plan"""
    out = cfg["callback"](resp)
    assert len(out) == 3 and out[1]["describe"].endswith("coding")
