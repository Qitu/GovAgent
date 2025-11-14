import random

from generative_agents.modules.agent import Agent
from generative_agents.modules.maze import Maze
from generative_agents.modules.memory.action import Action
from generative_agents.modules.memory.event import Event
from generative_agents.modules.utils.timer import set_timer
from generative_agents.modules.utils.log import create_io_logger

random.seed(42)


def minimal_maze_config():
    return {
        "size": [2, 2],
        "tile_size": 10,
        "tile_address_keys": ["world", "sector", "arena", "game_object"],
        "world": "w",
        "tiles": [
            {"coord": [0, 0], "address": ["s", "a", "o0"]},
            {"coord": [1, 0], "address": ["s", "a", "o1"]},
            {"coord": [0, 1], "address": ["s", "a", "o2"]},
            {"coord": [1, 1], "address": ["s", "a", "o3"]},
        ],
    }


def minimal_agent_config(name):
    return {
        "name": name,
        "percept": {},
        "think": {"llm": {"provider": "ollama", "api_key": "", "base_url": "http://x", "model": "m"}},
        "chat_iter": 1,
        "spatial": {"tree": {"living_area": {"room": ["bed"]}}, "address": {"living_area": ["w", "s", "a"]}},
        "schedule": {},
        "associate": {"embedding": {"provider": "openai", "base_url": "http://x", "api_key": "k", "model": "text-embedding"}},
        "status": {},
        "coord": [0, 0],
        "path": [],
        "scratch": {"age": 20, "innate": "", "learned": "", "lifestyle": "", "daily_plan": ""},
        "currently": "idle",
    }


def test_is_awake_and_move(monkeypatch, tmp_path):
    set_timer("20240101-00:00")
    logger = create_io_logger("info")
    maze = Maze(minimal_maze_config(), logger)

    cfg = minimal_agent_config("A")
    cfg["storage_root"] = str(tmp_path / "storage")
    agent = Agent(cfg, maze, conversation={}, logger=logger)

    # sleeping event (CN) -> not awake
    agent.action = Action(Event("A", "正在", "Sleep", address=["w","s","a","o0"]))
    assert not agent.is_awake()

    # set a non-sleeping event -> awake
    agent.action = Action(Event("A", "does", "work", address=["w","s","a","o0"]))
    assert agent.is_awake()

    # move to new tile should update events
    events = agent.move([1,0])
    assert isinstance(events, dict)
    assert agent.coord == [1,0]
