#!/usr/bin/env bash
set -euo pipefail

# 要求已设置 OPENAI_API_KEY 环境变量
if [[ -z "${OPENAI_API_KEY:-}" ]]; then
  echo "ERROR: 请先设置 OPENAI_API_KEY 环境变量，例如：export OPENAI_API_KEY=sk-xxx"
  exit 1
fi

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <promptfoo-config> [output-name]"
  echo "Example: $0 promptfoo.yaml generate_chat.json"
  exit 1
fi

CONFIG="$1"
OUTPUT_NAME="${2:-$(basename "${CONFIG}" .yaml).json}"

if [[ ! -f "${CONFIG}" ]]; then
  echo "ERROR: Config file ${CONFIG} not found"
  exit 1
fi

mkdir -p results/promptfoo
OUTPUT_PATH="results/promptfoo/${OUTPUT_NAME}"

echo "==> Running promptfoo eval (${CONFIG})"
promptfoo eval -c "${CONFIG}" --output "${OUTPUT_PATH}"

echo "==> Done. Report saved to ${OUTPUT_PATH}"
