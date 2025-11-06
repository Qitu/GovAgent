import os
import copy
import json
import argparse
import datetime
from pathlib import Path

from dotenv import load_dotenv, find_dotenv

from modules.game import create_game, get_game
from modules import utils
from db import repository
from db.session import ensure_engine

ASSETS_ROOT = os.path.join("assets", "village")

personas = [
    "Crowd", "Crowd2", "Crowd3", "Crowd4", "Crowd5", "Police", "Police2", "Orchestra"
]


class SimulateServer:
    def __init__(self, name, static_root, checkpoints_folder, config, start_step=0, verbose="info", log_file=""):
        ensure_engine()
        self.name = name
        self.static_root = static_root
        self.checkpoints_folder = checkpoints_folder

        run_stride = int(config.get("stride", 10))
        run_start = self._extract_start_time(config)
        run = repository.get_or_create_run(name, run_start, run_stride)
        repository.update_run_metadata(run.id, run_start, run_stride)
        self.run_id = run.id

        latest = repository.get_latest_step(name)
        self.resume_from_db = latest is not None and start_step == 0
        if self.resume_from_db:
            start_step = latest.step_index
            conversation = repository.get_conversation_map(name)
            config = copy.deepcopy(latest.state)
        else:
            conversation = {}

        self.static_root = static_root
        self.checkpoints_folder = checkpoints_folder
        self.config = config

        self.conversation_log = Path(checkpoints_folder) / "conversation.json"
        if conversation:
            self.conversation_log.write_text(json.dumps(conversation, indent=2, ensure_ascii=False), encoding="utf-8")
        elif self.conversation_log.exists():
            conversation = json.loads(self.conversation_log.read_text(encoding="utf-8"))
        else:
            conversation = {}

        log_path = Path(log_file) if log_file else Path(checkpoints_folder) / "simulation.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = utils.create_file_logger(str(log_path), verbose)

        game = create_game(name, static_root, config, conversation, logger=self.logger)
        game.reset_game()

        self.game = get_game()
        self.tile_size = self.game.maze.tile_size
        self.agent_status = {}
        agent_base = config.get("agent_base", {})
        for agent_name, agent in config["agents"].items():
            agent_config = copy.deepcopy(agent_base)
            agent_config.update(self.load_static(agent["config_path"]))
            self.agent_status[agent_name] = {"coord": agent_config["coord"], "path": []}
        self.think_interval = max(a.think_config["interval"] for a in self.game.agents.values())
        self.start_step = start_step

    def simulate(self, step, stride=0):
        timer = utils.get_timer()
        for i in range(self.start_step, self.start_step + step):
            title = "Simulate Step[{}/{}, time: {}]".format(i+1, self.start_step + step, timer.get_date())
            self.logger.info("\n" + utils.split_line(title, "="))
            for name, status in self.agent_status.items():
                plan = self.game.agent_think(name, status)["plan"]
                agent = self.game.get_agent(name)
                if name not in self.config["agents"]:
                    self.config["agents"][name] = {}
                self.config["agents"][name].update(agent.to_dict())
                if plan.get("path"):
                    status["coord"], status["path"] = plan["path"][-1], []
                self.config["agents"][name].update({"coord": status["coord"]})

            sim_time = timer.get_date("%Y%m%d-%H:%M")
            self.config.update({"time": sim_time, "step": i + 1})

            repository.add_step(self.run_id, i + 1, sim_time, copy.deepcopy(self.config))
            conv_payload = self.game.conversation.get(sim_time)
            if conv_payload is not None:
                repository.upsert_conversation(self.run_id, sim_time, conv_payload)

            if self.conversation_log:
                self.conversation_log.write_text(
                    json.dumps(self.game.conversation, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )

            if stride > 0:
                timer.forward(stride)

    def load_static(self, path):
        return utils.load_dict(os.path.join(self.static_root, path))

    @staticmethod
    def _extract_start_time(config):
        time_cfg = config.get("time")
        if isinstance(time_cfg, dict):
            return time_cfg.get("start")
        if isinstance(time_cfg, str):
            return time_cfg
        return None


# 从存档数据中载入配置（兼容旧流程）
def load_config_from_files(checkpoints_folder):
    files = sorted(os.listdir(checkpoints_folder))

    json_files = [
        os.path.join(checkpoints_folder, file_name)
        for file_name in files
        if file_name.endswith(".json") and file_name != "conversation.json"
    ]

    if not json_files:
        return None, 0

    with open(json_files[-1], "r", encoding="utf-8") as f:
        config = json.load(f)

    start_time = datetime.datetime.strptime(config["time"], "%Y%m%d-%H:%M")
    start_time += datetime.timedelta(minutes=config["stride"])
    config["time"] = {"start": start_time.strftime("%Y%m%d-%H:%M")}
    agents = config.get("agents", {})
    for a in agents:
        agents[a]["config_path"] = os.path.join(ASSETS_ROOT, "agents", a.replace(" ", "_"), "agent.json")

    return config, config.get("step", 0)


def load_config_from_db(name):
    latest = repository.get_latest_step(name)
    if latest is None:
        return None, 0
    config = copy.deepcopy(latest.state)
    config["time"] = {"start": latest.sim_time}
    agents = config.get("agents", {})
    for a in agents:
        agents[a]["config_path"] = os.path.join(ASSETS_ROOT, "agents", a.replace(" ", "_"), "agent.json")
    return config, latest.step_index


# 为新游戏创建配置
def get_config(start_time="20240213-09:30", stride=15, agents=None):
    with open("data/config.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)
        agent_config = json_data["agent"]

    config = {
        "stride": stride,
        "time": {"start": start_time},
        "maze": {"path": os.path.join(ASSETS_ROOT, "maze.json")},
        "agent_base": agent_config,
        "agents": {},
    }
    for a in agents:
        config["agents"][a] = {
            "config_path": os.path.join(
                ASSETS_ROOT, "agents", a.replace(" ", "_"), "agent.json"
            ),
        }
    return config


load_dotenv(find_dotenv())

parser = argparse.ArgumentParser(description="console for village")
parser.add_argument("--name", type=str, default="", help="The simulation name")
parser.add_argument("--start", type=str, default="20240213-09:30", help="The starting time of the simulated ville")
parser.add_argument("--resume", action="store_true", help="Resume running the simulation")
parser.add_argument("--step", type=int, default=10, help="The simulate step")
parser.add_argument("--stride", type=int, default=10, help="The step stride in minute")
parser.add_argument("--verbose", type=str, default="debug", help="The verbose level")
parser.add_argument("--log", type=str, default="", help="Log file path (defaults to results/checkpoints/<name>/simulation.log)")
args = parser.parse_args()


if __name__ == "__main__":
    checkpoints_path = "results/checkpoints"

    name = args.name
    if len(name) < 1:
        name = input("Please enter a simulation name (e.g. sim-test): ")

    resume = args.resume
    checkpoints_folder = f"{checkpoints_path}/{name}"

    if resume:
        config_db, step_db = load_config_from_db(name)
        if config_db is not None:
            sim_config = config_db
            start_step = step_db
        else:
            sim_config, step_files = load_config_from_files(checkpoints_folder)
            if sim_config is None:
                print("No checkpoint data found to resume.")
                exit(0)
            start_step = step_files
    else:
        while os.path.exists(checkpoints_folder):
            name = input(f"The name '{name}' already exists, please enter a new name: ")
            checkpoints_folder = f"{checkpoints_path}/{name}"
        sim_config = get_config(args.start, args.stride, personas)
        start_step = 0
        # 清理同名残留数据库记录
        repository.delete_run(name)
        run = repository.get_or_create_run(name, args.start, args.stride)
        repository.update_run_metadata(run.id, args.start, args.stride)

    static_root = "frontend/static"

    server = SimulateServer(name, static_root, checkpoints_folder, sim_config, start_step, args.verbose, args.log)
    server.simulate(args.step, args.stride)
