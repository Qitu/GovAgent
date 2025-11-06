import os
import json
import argparse
from datetime import datetime
from pathlib import Path

from modules.maze import Maze
from start import personas
from db import repository
from db.session import ensure_engine

file_markdown = "simulation.md"
file_movement = "movement.json"

frames_per_step = 60  # 每个step包含的帧数


def load_history(sim_name: str, checkpoints_folder: Path):
    ensure_engine()
    steps = repository.get_steps_for_run(sim_name)
    if steps:
        history = [step.state for step in steps]
        conversation = repository.get_conversation_map(sim_name)
        return history, conversation

    conversation_file = checkpoints_folder / "conversation.json"
    conversation = {}
    if conversation_file.exists():
        conversation = json.loads(conversation_file.read_text(encoding="utf-8"))

    json_files = sorted([
        p for p in checkpoints_folder.glob("*.json") if p.name != "conversation.json"
    ])

    history = [json.loads(p.read_text(encoding="utf-8")) for p in json_files]
    return history, conversation


def get_stride(history):
    if not history:
        return 1
    return int(history[0].get("stride", 1))


def get_location(address):
    location = "，".join(address[1:])
    return location


def insert_frame0(init_pos, movement, agent_name):
    key = "0"
    if key not in movement:
        movement[key] = {}

    json_path = f"frontend/static/assets/village/agents/{agent_name}/agent.json"
    with open(json_path, "r", encoding="utf-8") as f:
        json_data = json.load(f)
        address = json_data["spatial"]["address"].get("living_area", [])
    location = get_location(address)
    coord = json_data["coord"]
    init_pos[agent_name] = coord
    movement[key][agent_name] = {
        "location": location,
        "movement": coord,
        "description": "正在Sleep",
    }
    movement.setdefault("description", {})[agent_name] = {
        "currently": json_data["currently"],
        "scratch": json_data["scratch"],
    }


def generate_movement(sim_name, history, conversation, compressed_folder, compressed_file):
    movement_file = Path(compressed_folder) / compressed_file

    if not history:
        raise ValueError("No simulation history found")

    files_stride = get_stride(history)
    sec_per_step = files_stride

    result = {
        "start_datetime": "",
        "stride": files_stride,
        "sec_per_step": sec_per_step,
        "persona_init_pos": {},
        "all_movement": {"description": {}, "conversation": {}},
    }

    persona_init_pos = result["persona_init_pos"]
    all_movement = result["all_movement"]
    last_location = {}

    maze_path = "frontend/static/assets/village/maze.json"
    with open(maze_path, "r", encoding="utf-8") as f:
        maze = Maze(json.load(f), None)

    for step_state in history:
        step = int(step_state.get("step", 0))
        agents = step_state.get("agents", {})
        sim_time = step_state.get("time")

        if not result["start_datetime"] and sim_time:
            t = datetime.strptime(sim_time, "%Y%m%d-%H:%M")
            result["start_datetime"] = t.isoformat()

        for agent_name, agent_data in agents.items():
            if step == 1 and "0" not in all_movement:
                insert_frame0(persona_init_pos, all_movement, agent_name)

            source_coord = last_location.get(agent_name, all_movement["0"][agent_name])["movement"]
            target_coord = agent_data["coord"]
            location = get_location(agent_data["action"]["event"].get("address", []))
            if not location:
                location = last_location.get(agent_name, all_movement["0"][agent_name])["location"]
                path = [source_coord]
            else:
                path = maze.find_path(source_coord, target_coord)

            had_conversation = False
            step_conversation = ""
            persons_in_conversation = []
            chats_list = conversation.get(sim_time, []) if conversation else []
            for chats in chats_list:
                for persons, chat in chats.items():
                    persons_in_conversation.append(persons.split(" @ ")[0].split(" -> "))
                    step_conversation += f"\n地点：{persons.split(' @ ')[1]}\n\n"
                    for c in chat:
                        agent = c[0]
                        text = c[1]
                        step_conversation += f"{agent}：{text}\n"

            for i in range(frames_per_step):
                moving = len(path) > 1
                if path:
                    movement = list(path[0])
                    path = path[1:]
                    last_location.setdefault(agent_name, {})
                    last_location[agent_name]["movement"] = movement
                    last_location[agent_name]["location"] = location
                else:
                    movement = None

                if moving:
                    action = f"前往 {location}"
                elif movement is not None:
                    action = agent_data["action"]["event"].get("describe", "")
                    if not action:
                        action = f"{agent_data['action']['event'].get('predicate', '')}{agent_data['action']['event'].get('object', '')}"
                    for persons in persons_in_conversation:
                        if agent_name in persons:
                            had_conversation = True
                            break
                    if "Sleep" in action:
                        action = "😴 " + action
                    elif had_conversation:
                        action = "💬 " + action

                step_key = f"{(step - 1) * frames_per_step + 1 + i}"
                all_movement.setdefault(step_key, {})
                if movement is not None:
                    all_movement[step_key][agent_name] = {
                        "location": location,
                        "movement": movement,
                        "action": action,
                    }
            if step_conversation:
                all_movement["conversation"][sim_time] = step_conversation

    movement_file.parent.mkdir(parents=True, exist_ok=True)
    movement_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def generate_report(history, conversation, compressed_folder, compressed_file):
    markdown_path = Path(compressed_folder) / compressed_file
    last_state = {}

    def extract_description():
        markdown_content = "# Personality\n\n"
        for agent_name in personas:
            json_path = f"frontend/static/assets/village/agents/{agent_name}/agent.json"
            with open(json_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)
                markdown_content += f"## {agent_name}\n\n"
                markdown_content += f"Age：{json_data['scratch']['age']}岁  \n"
                markdown_content += f"Innate：{json_data['scratch']['innate']}  \n"
                markdown_content += f"Learned：{json_data['scratch']['learned']}  \n"
                markdown_content += f"Habit：{json_data['scratch']['lifestyle']}  \n"
                markdown_content += f"Status：{json_data['currently']}\n\n"
        return markdown_content

    def extract_action(step_state):
        markdown_content = ""
        agents = step_state.get("agents", {})
        for agent_name, agent_data in agents.items():
            if agent_name not in last_state:
                last_state[agent_name] = {"location": "", "action": ""}

            location = "，".join(agent_data["action"]["event"].get("address", []))
            action = agent_data["action"]["event"].get("describe", "")

            if location == last_state[agent_name]["location"] and action == last_state[agent_name]["action"]:
                continue

            last_state[agent_name]["location"] = location
            last_state[agent_name]["action"] = action

            if not markdown_content:
                markdown_content = f"# {step_state['time']}\n\n"
                markdown_content += "## Activities：\n\n"

            markdown_content += f"### {agent_name}\n"
            markdown_content += f"Location：{location}  \n"
            markdown_content += f"Activity：{action or 'Sleep'}  \n\n"

        step_time = step_state.get("time")
        if conversation and step_time in conversation:
            markdown_content += "## Conversation：\n\n"
            for chats in conversation[step_time]:
                for agents, chat in chats.items():
                    markdown_content += f"### {agents}\n\n"
                    for item in chat:
                        markdown_content += f"`{item[0]}`\n> {item[1]}\n\n"
        return markdown_content

    markdown_content = extract_description()
    for step_state in history:
        markdown_content += extract_action(step_state) + "\n\n"

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown_content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", type=str, default="", help="the name of the simulation")
    args = parser.parse_args()

    name = args.name or input("Please enter a simulation name: ")
    checkpoints_folder = Path(f"results/checkpoints/{name}")
    if not checkpoints_folder.exists():
        raise FileNotFoundError(f"Simulation '{name}' does not exist")

    compressed_folder = Path(f"results/compressed/{name}")
    compressed_folder.mkdir(parents=True, exist_ok=True)

    history, conversation = load_history(name, checkpoints_folder)
    generate_report(history, conversation, compressed_folder, file_markdown)
    generate_movement(name, history, conversation, compressed_folder, file_movement)


if __name__ == "__main__":
    main()
