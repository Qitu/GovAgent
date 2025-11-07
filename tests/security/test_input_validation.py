import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from evaluation.security_tests.run_security_checks import CaseSchema, ConfigSchema


def test_case_schema_requires_minimum_fields(tmp_path: Path):
    with pytest.raises(ValidationError):
        CaseSchema.model_validate({})

    valid = {
        "id": "test",
        "roleA": "A",
        "roleB": "B",
        "prompt": "Do X",
        "context": "Context details",
        "tags": ["tag1"],
    }
    model = CaseSchema.model_validate(valid)
    assert model.id == "test"


def test_config_schema_requires_sections(tmp_path: Path):
    with pytest.raises(ValidationError):
        ConfigSchema.model_validate({})

    data = {
        "provider": {"model": "gpt"},
        "thresholds": {"hallucination_fail_threshold": 0.5},
        "output": {"dir": "results"},
    }
    model = ConfigSchema.model_validate(data)
    assert model.output["dir"] == "results"
