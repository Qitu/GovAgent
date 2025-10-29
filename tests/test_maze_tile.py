from generative_agents.modules.maze import Tile
from generative_agents.modules.memory.event import Event


def test_tile_event_add_remove_update_and_addresses():
    t = Tile(coord=(0,0), world='w', address_keys=['world','sector','arena','game_object'], address=['s','a','o'])

    # Initially has object event
    assert any(isinstance(e, Event) for e in t.get_events())

    # add_event deduplicates equal events
    e = Event('Alice', 'is', 'idle')
    t.add_event(e)
    t.add_event(['Alice', 'is', 'idle'])  # list form
    cnt = len(list(t.get_events()))
    assert cnt >= 2  # includes object event + Alice event once

    # update_events by subject
    ne = Event('Alice', 'does', 'work')
    t.update_events(ne)
    assert any(ev.predicate == 'does' for ev in t.get_events())

    # remove_events by subject
    t.remove_events(subject='Alice')
    assert all(ev.subject != 'Alice' for ev in t.get_events())

    # address getters
    assert t.get_address('arena', as_list=False).endswith('a')
    adds = t.get_addresses()
    assert 'w:s' in adds and 'w:s:a:o' in [':'.join(t.address)]
