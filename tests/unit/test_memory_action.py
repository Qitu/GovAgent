import datetime

from generative_agents.modules.memory.action import Action
from generative_agents.modules.memory.event import Event
from generative_agents.modules.utils.timer import set_timer, get_timer


def test_action_finished_with_zero_duration():
    set_timer("20240101-00:00")
    a = Action(Event("Alice"), duration=0)
    assert a.finished()  # zero duration considered finished


def test_action_finished_over_time():
    set_timer("20240101-00:00")
    # start 10 minutes in the future to guard against flakiness
    future_start = get_timer().get_date() + datetime.timedelta(minutes=10)
    a = Action(Event("Alice", address=["loc"]) , duration=30, start=future_start)
    # advance time beyond end
    get_timer().forward(41)
    assert a.finished()


def test_action_to_dict_roundtrip():
    set_timer("20240101-00:00")
    a = Action(Event("Alice", "does", "work", address=["home"]))
    d = a.to_dict()
    a2 = Action.from_dict(d)
    assert a2.duration == a.duration
    assert a2.event.subject == a.event.subject and a2.event.object == a.event.object
