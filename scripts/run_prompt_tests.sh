#!/usr/bin/env bash
set -euo pipefail

# Require provider-specific API key environment variable
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
PROJECT_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
CONFIG_PATH="$PROJECT_ROOT/evaluation/config.yaml"
if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "ERROR: Missing evaluation config at $CONFIG_PATH"
  exit 1
fi
API_KEY_ENV=$(python3 - <<'PY'
import sys
import yaml
from pathlib import Path
config_path = Path(sys.argv[1])
with config_path.open("r", encoding="utf-8") as stream:
    cfg = yaml.safe_load(stream) or {}
provider = cfg.get("provider", {}) if isinstance(cfg, dict) else {}
print(provider.get("api_key_env", "OPENAI_API_KEY"))
PY
"$CONFIG_PATH")
if [[ -z "$API_KEY_ENV" ]]; then
  API_KEY_ENV="OPENAI_API_KEY"
fi
if [[ -z "${!API_KEY_ENV:-}" ]]; then
  echo "ERROR: Please set $API_KEY_ENV environment variable, e.g., export $API_KEY_ENV=sk-xxx"
  exit 1
fi

mkdir -p results/promptfoo

echo "==> Running generate_chat (promptfoo.yaml)"
promptfoo eval -c promptfoo.yaml --output results/promptfoo/generate_chat.json

# echo "==> Running decide_chat (promptfoo.decide_chat.yaml)"
# promptfoo eval -c promptfoo.decide_chat.yaml --output results/promptfoo/decide_chat.json

# echo "==> Running decide_wait (promptfoo.decide_wait.yaml)"
# promptfoo eval -c promptfoo.decide_wait.yaml --output results/promptfoo/decide_wait.json

# echo "==> Running generate_chat_check_repeat (promptfoo.generate_chat_check_repeat.yaml)"
# promptfoo eval -c promptfoo.generate_chat_check_repeat.yaml --output results/promptfoo/generate_chat_check_repeat.json

# echo "==> Running summarize_chats (promptfoo.summarize_chats.yaml)"
# promptfoo eval -c promptfoo.summarize_chats.yaml --output results/promptfoo/summarize_chats.json

echo "==> Done. Reports saved under results/promptfoo/"