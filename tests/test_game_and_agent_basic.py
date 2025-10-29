import json

from generative_agents.modules.game import Game
from generative_agents.modules.maze import Maze
from generative_agents.modules.agent import Agent
from generative_agents.modules.memory.event import Event
from generative_agents.modules.utils.timer import set_timer
from generative_agents.modules.utils.log import create_io_logger


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


def test_agent_llm_available_and_to_dict(monkeypatch, tmp_path):
    set_timer("20240101-00:00")
    logger = create_io_logger("info")
    maze = Maze(minimal_maze_config(), logger)

    # Patch Agent.reset to avoid creating real LLM client
    def fake_reset(self):
        class DummyLLM:
            def is_available(self):
                return True
            def get_summary(self):
                return {"model": "m", "summary": {"total": "S:0,F:0/R:0"}}
        self._llm = DummyLLM()
    monkeypatch.setattr(Agent, "reset", fake_reset)

    cfg = minimal_agent_config("A")
    cfg["storage_root"] = str(tmp_path / "storage")
    agent = Agent(cfg, maze, conversation={}, logger=logger)
    agent.reset()
    assert agent.llm_available()
    info = agent.to_dict()
    assert "action" in info and "schedule" in info


def test_game_agent_think_stubbed(monkeypatch, tmp_path):
    set_timer("20240101-00:00")
    logger = create_io_logger("info")

    # Stub Maze.load_static within Game to return minimal maze config
    from generative_agents.modules.game import Game as GameClass

    def fake_load_static(self, path):
        if path.endswith('.json') or isinstance(path, str):
            return minimal_maze_config()
        return {}
    monkeypatch.setattr(GameClass, "load_static", fake_load_static)

    # Build a minimal game config with one agent
    cfg = {
        "maze": {"path": "maze.json"},
        "agents": {
            "A": {"config_path": "agent.json", **minimal_agent_config("A")}
        },
        "time": {},
    }

    # Stub Agent.reset and Agent.think to avoid complex flows
    def fake_reset(self):
        class DummyLLM:
            def is_available(self):
                return True
            def get_summary(self):
                return {"model": "m", "summary": {}}
        self._llm = DummyLLM()
    monkeypatch.setattr(Agent, "reset", fake_reset)

    def fake_think(self, status, agents):
        self.action = self.action  # keep existing action
        return {"name": self.name, "path": [], "emojis": {}}
    monkeypatch.setattr(Agent, "think", fake_think)

    g = Game("n", static_root=".", config=cfg, conversation={}, logger=logger)
    g.reset_game()
    out = g.agent_think("A", {"coord": [0, 0]})
    assert "plan" in out and "info" in out
