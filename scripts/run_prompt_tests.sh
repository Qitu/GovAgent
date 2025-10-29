#!/usr/bin/env bash
set -euo pipefail

# 要求已设置 OPENAI_API_KEY 环境变量
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "ERROR: 请先设置 OPENAI_API_KEY 环境变量，例如：export OPENAI_API_KEY=sk-xxx"
  exit 1
fi

mkdir -p results/promptfoo

echo "==> Running generate_chat (promptfoo.yaml)"
promptfoo eval -c promptfoo.yaml --format json --output results/promptfoo/generate_chat.json

echo "==> Running decide_chat (promptfoo.decide_chat.yaml)"
promptfoo eval -c promptfoo.decide_chat.yaml --format json --output results/promptfoo/decide_chat.json

echo "==> Running decide_wait (promptfoo.decide_wait.yaml)"
promptfoo eval -c promptfoo.decide_wait.yaml --format json --output results/promptfoo/decide_wait.json

echo "==> Running generate_chat_check_repeat (promptfoo.generate_chat_check_repeat.yaml)"
promptfoo eval -c promptfoo.generate_chat_check_repeat.yaml --format json --output results/promptfoo/generate_chat_check_repeat.json

echo "==> Running summarize_chats (promptfoo.summarize_chats.yaml)"
promptfoo eval -c promptfoo.summarize_chats.yaml --format json --output results/promptfoo/summarize_chats.json

echo "==> Done. Reports saved under results/promptfoo/"