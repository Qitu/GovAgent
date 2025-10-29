#!/usr/bin/env bash
set -euo pipefail

# Allow .env override
if [ -f .env ]; then
  # shellcheck disable=SC2046
  export $(grep -v '^#' .env | xargs -I {} echo {})
fi

python -m evaluation.run_model_evaluation
