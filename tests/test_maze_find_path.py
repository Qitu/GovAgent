from generative_agents.modules.maze import Maze
from generative_agents.modules.utils.log import create_io_logger


def test_find_path_small_grid():
    cfg = {
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
    m = Maze(cfg, create_io_logger('info'))
    path = m.find_path([0,0], [1,1])
    assert isinstance(path, list) and len(path) >= 2
