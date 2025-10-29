import datetime

from generative_agents.modules.utils.timer import to_date, daily_duration, Timer
from generative_agents.modules.utils.namespace import (
    GenerativeAgentsMap,
    GenerativeAgentsKey,
)


def test_to_date_with_24_hour_edge():
    # When parsing %H:%M, leading 24: should be treated as 00:
    d = to_date("24:15", "%H:%M")
    assert d.hour == 0 and d.minute == 15


def test_daily_duration_modes():
    dt = datetime.datetime(2024, 1, 1, 3, 5, 0)
    assert daily_duration(dt, "hour") == 3
    assert daily_duration(dt, "minute") == 185
    assert isinstance(daily_duration(dt, "delta"), datetime.timedelta)


def test_timer_flow_and_delta():
    t = Timer(start="20240101-00:00")
    assert t.get_date("%Y%m%d-%H:%M") == "20240101-00:00"
    t.forward(90)  # +90 minutes
    assert t.get_date("%H:%M") == "01:30"
    start = to_date("20240101-00:00", "%Y%m%d-%H:%M")
    end = t.get_date()
    assert t.get_delta(start, end, "minute") == 90
    assert t.get_delta(start, end, "hour") == 2  # rounded


def test_timer_daily_helpers():
    t = Timer(start="20240101-00:00")
    # 10:30 timestamp
    d = t.daily_time(10 * 60 + 30)
    assert d.hour == 10 and d.minute == 30


def test_namespace_set_get_reset():
    GenerativeAgentsMap.reset()
    assert not GenerativeAgentsMap.contains(GenerativeAgentsKey.TIMER)
    GenerativeAgentsMap.set(GenerativeAgentsKey.TIMER, "v")
    assert GenerativeAgentsMap.contains(GenerativeAgentsKey.TIMER)
    assert GenerativeAgentsMap.get(GenerativeAgentsKey.TIMER) == "v"
    clone = GenerativeAgentsMap.clone(GenerativeAgentsKey.TIMER)
    assert clone == "v"
    GenerativeAgentsMap.delete(GenerativeAgentsKey.TIMER)
    assert not GenerativeAgentsMap.contains(GenerativeAgentsKey.TIMER)
