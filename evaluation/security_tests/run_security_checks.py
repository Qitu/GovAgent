"""Automated AI security checks for generative_agents project."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml
from pydantic import BaseModel, Field, ValidationError, constr

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVAL_ROOT = PROJECT_ROOT / "evaluation"
SECURITY_ROOT = PROJECT_ROOT / "evaluation" / "security_tests"


class CaseSchema(BaseModel):
    id: constr(strip_whitespace=True, min_length=1)
    roleA: constr(strip_whitespace=True, min_length=1)
    roleB: constr(strip_whitespace=True, min_length=1)
    prompt: constr(strip_whitespace=True, min_length=1)
    context: constr(strip_whitespace=True, min_length=1) | None = None
    tags: List[constr(strip_whitespace=True, min_length=1)] = Field(default_factory=list)


class ConfigSchema(BaseModel):
    provider: Dict[str, Any]
    thresholds: Dict[str, Any]
    output: Dict[str, Any]


def run_subprocess(cmd: List[str], cwd: Path | None = None, env: Dict[str, str] | None = None) -> None:
    print(f"[run] {' '.join(cmd)}")
    process = subprocess.Popen(cmd, cwd=cwd, env=env)
    try:
        returncode = process.wait()
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        raise
    if returncode != 0:
        raise SystemExit(returncode)


def validate_cases() -> None:
    cases_path = EVAL_ROOT / "cases.json"
    with cases_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list) or not data:
        raise SystemExit("cases.json must be a non-empty list")
    for item in data:
        try:
            CaseSchema.model_validate(item)
        except ValidationError as exc:
            raise SystemExit(f"Invalid case entry: {exc}")
    print(f"[ok] {len(data)} evaluation cases validated")


def validate_config() -> None:
    config_path = EVAL_ROOT / "config.yaml"
    with config_path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    try:
        ConfigSchema.model_validate(data)
    except ValidationError as exc:
        raise SystemExit(f"Invalid config.yaml: {exc}")
    print("[ok] config.yaml validated")


def run_pytest_security() -> None:
    ini = SECURITY_ROOT / "pytest-security.ini"
    env = os.environ.copy()
    env.pop("PYTEST_ADDOPTS", None)
    run_subprocess(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            str(ini),
        ],
        cwd=PROJECT_ROOT,
        env=env,
    )


def run_prompt_tests() -> None:
    promptfoo_yaml = PROJECT_ROOT / "promptfoo.decide_chat.yaml"
    if promptfoo_yaml.exists():
        run_subprocess(["promptfoo", "eval", str(promptfoo_yaml)], cwd=PROJECT_ROOT)
    else:
        print("[skip] promptfoo.decide_chat.yaml not found")


def run_evaluation_hardening() -> None:
    script = EVAL_ROOT / "run_model_evaluation.py"
    run_subprocess([sys.executable, str(script)], cwd=PROJECT_ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AI security checks")
    parser.add_argument("--skip-prompt", action="store_true", help="Skip prompt injection tests")
    parser.add_argument("--skip-eval", action="store_true", help="Skip evaluation pipeline hardening run")
    args = parser.parse_args()

    validate_cases()
    validate_config()

    run_pytest_security()

    if not args.skip_prompt:
        run_prompt_tests()

    if not args.skip_eval:
        run_evaluation_hardening()

    print("[done] security checks completed")


if __name__ == "__main__":
    main()
