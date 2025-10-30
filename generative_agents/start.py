import os
import copy
import json
import argparse
import datetime
import random

from dotenv import load_dotenv, find_dotenv

from modules.game import create_game, get_game
from modules import utils

personas = [
    "Crowd", "Police", "Orchestra"
]


class SimulateServer:
    def __init__(self, name, static_root, checkpoints_folder, config, start_step=0, verbose="info", log_file=""):
        self.name = name
        self.static_root = static_root
        self.checkpoints_folder = checkpoints_folder

        # 历史存档数据（用于断点恢复）
        self.config = config

        os.makedirs(checkpoints_folder, exist_ok=True)

        # 载入历史对话数据（用于断点恢复）
        self.conversation_log = f"{checkpoints_folder}/conversation.json"
        if os.path.exists(self.conversation_log):
            with open(self.conversation_log, "r", encoding="utf-8") as f:
                conversation = json.load(f)
        else:
            conversation = {}

        if len(log_file) > 0:
            self.logger = utils.create_file_logger(f"{checkpoints_folder}/{log_file}", verbose)
        else:
            self.logger = utils.create_io_logger(verbose)

        # 创建游戏
        game = create_game(name, static_root, config, conversation, logger=self.logger)
        game.reset_game()

        self.game = get_game()
        self.tile_size = self.game.maze.tile_size
        self.agent_status = {}
        # 全局协调与疏散状态
        self.dispatch_targets = {}  # {police_name: {"area": area_key, "coord": (x,y)}}
        self.evac_state = {}        # {area_key: {"count": int}}
        # 参数可调
        self.crowd_baseline = 30    # 人群基线人数（示意）
        self.crowd_min = 5          # 疏散后最低人数
        self.evac_rate = 5          # 每 step 疏散人数
        self.crowded_ratio = 20     # 触发拥挤的阈值： crowd / max(1, police) > crowded_ratio
        self.max_assign_per_step = 1
        if "agent_base" in config:
            agent_base = config["agent_base"]
        else:
            agent_base = {}
        for agent_name, agent in config["agents"].items():
            agent_config = copy.deepcopy(agent_base)
            agent_config.update(self.load_static(agent["config_path"]))
            self.agent_status[agent_name] = {
                "coord": agent_config["coord"],
                "path": [],
            }
        self.think_interval = max(
            a.think_config["interval"] for a in self.game.agents.values()
        )
        self.start_step = start_step

    def simulate(self, step, stride=0):
        timer = utils.get_timer()
        for i in range(self.start_step, self.start_step + step):
            title = "Simulate Step[{}/{}, time: {}]".format(i+1, self.start_step + step, timer.get_date())
            self.logger.info("\n" + utils.split_line(title, "="))

            # 1) 全局统计与协调者调度
            area_stats = self._compute_area_stats()
            self._update_evac(area_stats)
            self._coordinator_dispatch(area_stats)

            # 2) 执行每个 Agent 的一步
            for name, status in self.agent_status.items():
                # 若是被调度的警察，则注入一步朝目标区域的移动
                if self._is_police(name) and name in self.dispatch_targets:
                    next_coord = self._next_step_towards(name, self.dispatch_targets[name]["coord"])
                    if next_coord:
                        status["coord"] = next_coord
                        status["path"] = []

                plan = self.game.agent_think(name, status)["plan"]
                agent = self.game.get_agent(name)
                if name not in self.config["agents"]:
                    self.config["agents"][name] = {}
                self.config["agents"][name].update(agent.to_dict())
                if plan.get("path"):
                    status["coord"], status["path"] = plan["path"][-1], []
                self.config["agents"][name].update({"coord": status["coord"]})

                # 若警察抵达目标区域，则保持驻守并清理一次性调度目标
                if self._is_police(name) and name in self.dispatch_targets:
                    area_key = self._area_key(self.game.maze.tile_at(status["coord"]))
                    if area_key == self.dispatch_targets[name]["area"]:
                        # 抵达，留在该区域驻守
                        self.logger.info(f"[Coordinator] {name} 已抵达 {area_key}，开始驻守监管。")
                        self.dispatch_targets.pop(name, None)

            sim_time = timer.get_date("%Y%m%d-%H:%M")
            self.config.update(
                {
                    "time": sim_time,
                    "step": i + 1,
                }
            )
            # 保存Agent活动数据
            with open(f"{self.checkpoints_folder}/simulate-{sim_time.replace(':', '')}.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(self.config, indent=2, ensure_ascii=False))
            # 保存对话数据
            with open(f"{self.checkpoints_folder}/conversation.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(self.game.conversation, indent=2, ensure_ascii=False))

            if stride > 0:
                timer.forward(stride)

    def load_static(self, path):
        return utils.load_dict(os.path.join(self.static_root, path))

    # ---------- 协调者与区域统计逻辑 ----------
    def _is_police(self, name: str) -> bool:
        return "警察" in name or "Police" in name

    def _is_crowd(self, name: str) -> bool:
        return "人群" in name or "Crowd" in name

    def _is_coordinator(self, name: str) -> bool:
        return "协调者" in name or "Coordinator" in name

    def _area_key(self, tile) -> str:
        # 使用 arena 级地址作为区域键
        try:
            return tile.get_address("arena", as_list=False)
        except Exception:
            # 回退到 sector
            return tile.get_address("sector", as_list=False)

    def _compute_area_stats(self):
        # 统计每个区域的 crowd/police 数量与代表坐标
        stats = {}  # area_key -> {"crowd": int, "police": int, "crowd_coords": set(), "police_coords": set()}
        for name, agent in self.game.agents.items():
            tile = self.game.maze.tile_at(agent.coord)
            area = self._area_key(tile)
            s = stats.setdefault(area, {"crowd": 0, "police": 0, "crowd_coords": set(), "police_coords": set()})
            if self._is_crowd(name):
                s["crowd"] += 1  # 以“人群智能体”作为存在标记
                s["crowd_coords"].add(tuple(agent.coord))
            elif self._is_police(name):
                s["police"] += 1
                s["police_coords"].add(tuple(agent.coord))
        return stats

    def _update_evac(self, area_stats):
        # 当有警察覆盖的区域启动疏散冷却；每步衰减模拟人数
        for area, s in area_stats.items():
            has_crowd = s["crowd"] > 0
            has_police = s["police"] > 0
            # 初始化或维持当前区域的计数
            if area not in self.evac_state:
                # 初始认为该区域若有人群，则为基线人数
                self.evac_state[area] = {"count": self.crowd_baseline if has_crowd else 0}
            # 有人群但无警力，不变化（或轻微波动）
            if has_crowd and not has_police:
                # 微小噪声模拟：±1
                if self.evac_state[area]["count"] > 0:
                    self.evac_state[area]["count"] += random.choice([-1, 0, 1])
                    self.evac_state[area]["count"] = max(self.evac_state[area]["count"], self.crowd_min)
            # 有人群且有警力，进行疏散衰减
            if has_crowd and has_police:
                self.evac_state[area]["count"] = max(self.crowd_min, self.evac_state[area]["count"] - self.evac_rate)

    def _coordinator_dispatch(self, area_stats):
        # 协调者“看到”全局：选择拥挤区域，调度空闲警察前往
        # 拥挤判定： crowd_count / max(1, police) > crowded_ratio
        # 注意：crowd_count 用 evac_state[area]["count"]，若为 0 则不拥挤
        # 简单策略：每步最多分派 max_assign_per_step 名警察
        crowded_areas = []
        for area, s in area_stats.items():
            c = self.evac_state.get(area, {"count": 0})["count"]
            if c <= 0:
                continue
            ratio = c / max(1, s["police"])
            if ratio > self.crowded_ratio:
                crowded_areas.append((area, c, s))
        if not crowded_areas:
            return
        crowded_areas.sort(key=lambda x: x[1], reverse=True)  # 优先人数更多的区域

        # 找出可用警察（未被派遣或当前没有目标）
        available_police = [n for n in self.game.agents.keys() if self._is_police(n) and n not in self.dispatch_targets]
        if not available_police:
            return

        assigned = 0
        for area, _, s in crowded_areas:
            if assigned >= self.max_assign_per_step:
                break
            # 选择一个代表性目标坐标：优先该区域内的人群坐标，否则区域任意 tile
            target_coord = None
            if s["crowd_coords"]:
                target_coord = min(s["crowd_coords"], key=lambda c: c[0] + c[1])
            else:
                # 取该区域任意一个 tile 作为目标
                tiles = list(self.game.maze.address_tiles.get(area, []))
                if tiles:
                    target_coord = random.choice(tiles)
            if not target_coord:
                continue

            # 选择距离目标最近的可用警察
            def _dist(n):
                a = self.game.get_agent(n)
                return abs(a.coord[0] - target_coord[0]) + abs(a.coord[1] - target_coord[1])

            police_name = min(available_police, key=_dist)
            available_police.remove(police_name)
            self.dispatch_targets[police_name] = {"area": area, "coord": target_coord}
            self.logger.info(f"[Coordinator] 调度 {police_name} 前往 {area} 支援，目标 {target_coord}")
            assigned += 1

    def _next_step_towards(self, name, target_coord):
        # 计算从 agent 当前坐标到目标的一步
        agent = self.game.get_agent(name)
        if tuple(agent.coord) == tuple(target_coord):
            return agent.coord
        try:
            path = self.game.maze.find_path(agent.coord, target_coord)
            if len(path) >= 2:
                return path[1]
        except Exception:
            return None
        return None


# 从存档数据中载入配置，用于断点恢复
def get_config_from_log(checkpoints_folder):
    files = sorted(os.listdir(checkpoints_folder))

    json_files = list()
    for file_name in files:
        if file_name.endswith(".json") and file_name != "conversation.json":
            json_files.append(os.path.join(checkpoints_folder, file_name))

    if len(json_files) < 1:
        return None

    with open(json_files[-1], "r", encoding="utf-8") as f:
        config = json.load(f)

    assets_root = os.path.join("assets", "village")

    start_time = datetime.datetime.strptime(config["time"], "%Y%m%d-%H:%M")
    start_time += datetime.timedelta(minutes=config["stride"])
    config["time"] = {"start": start_time.strftime("%Y%m%d-%H:%M")}
    agents = config["agents"]
    for a in agents:
        config["agents"][a]["config_path"] = os.path.join(assets_root, "agents", a.replace(" ", "_"), "agent.json")

    return config


# 为新游戏创建配置
def get_config(start_time="20240213-09:30", stride=15, agents=None):
    # 读取基础 Agent 公共配置
    with open("data/config.json", "r", encoding="utf-8") as f:
        json_data = json.load(f)
        agent_config = json_data["agent"]

    assets_root = os.path.join("assets", "village")
    config = {
        "stride": stride,
        "time": {"start": start_time},
        "maze": {"path": os.path.join(assets_root, "maze.json")},
        "agent_base": agent_config,
        "agents": {},
    }

    # 扩展规则：警察=10、人群=13、协调者=1（共享各自配置文件）
    expand_counts = {
        "警察智能体": 10,
        "人群智能体": 13,
        "协调者智能体": 1,
    }

    # 目标区域列表（轮询分配警察与人群）
    target_areas = [
        "金沙酒店","CBD区","克拉码头","国家美术馆","摩天轮",
        "滨海湾花园","鱼尾狮公园","艺术科学博物馆","市区街道",
        "Funan购物中心","牛车水","赞美广场","1街区"
    ]
    coordinator_area = "滨海湾花园"

    # 从 maze.json 收集各区域的可用坐标
    try:
        with open(os.path.join("frontend/static", "assets", "village", "maze.json"), "r", encoding="utf-8") as mf:
            maze_data = json.load(mf)
    except Exception:
        maze_data = {}

    area_tiles = {area: [] for area in target_areas}
    tiles = maze_data.get("tiles", [])
    for t in tiles:
        addr = t.get("address", [])
        if not addr:
            continue
        area_name = addr[0]
        if area_name in area_tiles:
            c = t.get("coord", [])
            if isinstance(c, list) and len(c) == 2:
                area_tiles[area_name].append(tuple(c))

    # 若某区域没有枚举到 tiles，则回退到“市区街道”或公共街区范围
    fallback_street = area_tiles.get("市区街道", [])
    if not fallback_street:
        spawn_x = list(range(9, 22))
        spawn_y = list(range(32, 39))
        fallback_street = [(x, y) for y in spawn_y for x in spawn_x]

    def pick_coord(area_list, idx):
        # 从指定区域轮询选择坐标，若为空则回退到街区
        area = area_list[idx % len(area_list)]
        coords = area_tiles.get(area, [])
        if not coords:
            coords = fallback_street
        return area, list(coords[(idx // len(area_list)) % len(coords)])

    agents = agents or ["人群智能体", "警察智能体", "协调者智能体"]

    def add_instances(base_name: str, count: int):
        base_cfg_path = os.path.join(
            assets_root, "agents", base_name.replace(" ", "_"), "agent.json"
        )
        for idx in range(count):
            name = base_name if count == 1 else f"{base_name}-{idx+1:02d}"
            if "协调者" in base_name or "Coordinator" in base_name:
                # 协调者固定在“滨海湾花园”
                area = coordinator_area
                coords = area_tiles.get(area, [])
                coord = list(coords[0]) if coords else list(fallback_street[0])
            else:
                # 警察与人群分布到多个区域（轮询）
                area, coord = pick_coord(target_areas, idx)

            config["agents"][name] = {
                "config_path": base_cfg_path,
                "name": name,
                "coord": coord,
            }

    for a in agents:
        c = expand_counts.get(a, 1)
        add_instances(a, c)

    return config


load_dotenv(find_dotenv())

parser = argparse.ArgumentParser(description="console for village")
parser.add_argument("--name", type=str, default="", help="The simulation name")
parser.add_argument("--start", type=str, default="20240213-09:30", help="The starting time of the simulated ville")
parser.add_argument("--resume", action="store_true", help="Resume running the simulation")
parser.add_argument("--step", type=int, default=10, help="The simulate step")
parser.add_argument("--stride", type=int, default=10, help="The step stride in minute")
parser.add_argument("--verbose", type=str, default="debug", help="The verbose level")
parser.add_argument("--log", type=str, default="", help="Name of the log file")
args = parser.parse_args()


if __name__ == "__main__":
    checkpoints_path = "results/checkpoints"

    name = args.name
    if len(name) < 1:
        name = input("Please enter a simulation name (e.g. sim-test): ")

    resume = args.resume
    if resume:
        while not os.path.exists(f"{checkpoints_path}/{name}"):
            name = input(f"'{name}' doesn't exists, please re-enter the simulation name: ")
    else:
        while os.path.exists(f"{checkpoints_path}/{name}"):
            name = input(f"The name '{name}' already exists, please enter a new name: ")

    checkpoints_folder = f"{checkpoints_path}/{name}"

    start_time = args.start
    if resume:
        sim_config = get_config_from_log(checkpoints_folder)
        if sim_config is None:
            print("No checkpoint file found to resume running.")
            exit(0)
        start_step = sim_config["step"]
    else:
        sim_config = get_config(start_time, args.stride, personas)
        start_step = 0

    static_root = "frontend/static"

    server = SimulateServer(name, static_root, checkpoints_folder, sim_config, start_step, args.verbose, args.log)
    server.simulate(args.step, args.stride)
