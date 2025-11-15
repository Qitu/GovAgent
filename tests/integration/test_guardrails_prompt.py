import re
import pytest

from guardrails import Guard
from guardrails.errors import ValidationError
from guardrails.validators import (
    register_validator,
    Validator,
    ValidationResult,
    FailResult,
)

from generative_agents.modules.prompt.scratch import Scratch
from generative_agents.modules.memory.event import Event
from generative_agents.modules.memory.schedule import Schedule
from generative_agents.modules.memory.action import Action
from generative_agents.modules.utils.timer import set_timer


@register_validator(name="regex_allowlist", data_type="string")
class RegexAllowlist(Validator):
    def __init__(self, pattern: str):
        super().__init__(name="regex_allowlist")
        self.pattern = re.compile(pattern, re.DOTALL)

    def _normalize(self, value):
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return str(value)

    def _validate(self, value, metadata):
        metadata = metadata or {}
        normalized = self._normalize(value)
        if self.pattern.fullmatch(normalized):
            return ValidationResult(
                outcome="pass",
                metadata=metadata,
                validated_chunk=normalized,
            )
        return FailResult(
            error_message=f"Value '{normalized}' failed regex {self.pattern.pattern}",
            metadata=metadata,
            validated_chunk=normalized,
        )


def build_scratch(monkeypatch):
    set_timer("20240101-00:00")
    scratch = Scratch(
        name="Alice",
        currently="Reading",
        config={
            "age": 25,
            "innate": "curious",
            "learned": "CS",
            "lifestyle": "early bird",
            "daily_plan": "study, exercise",
        },
    )
    monkeypatch.setattr(scratch, "build_prompt", lambda template, data: "[PROMPT]" + template)
    return scratch


@pytest.fixture()
def schedule_with_action(monkeypatch):
    scratch = build_scratch(monkeypatch)
    schedule = Schedule()
    plan = schedule.add_plan("work", 60)
    action = Action(Event("Alice", describe="Alice coding"), duration=10)
    return scratch, plan, schedule, action


def test_prompt_schedule_revise_guardrails_pass(schedule_with_action):
    scratch, plan, schedule, action = schedule_with_action
    guard = Guard().use(RegexAllowlist(r"^[^{}<>]*$"))

    hook = scratch.prompt_schedule_revise(action, schedule)
    response = "[08:00 - 08:15] 阅读\n[08:15 - 08:25] Coding\n[08:25 - 08:55] Planning"
    assert guard.parse(response).validation_passed
    parsed = hook["callback"](response)
    assert parsed


@pytest.mark.parametrize(
    "response",
    [
        "[08:00 - 08:15] 阅读\n[08:15 - 08:25] Coding <IGNORED>\n[08:25 - 08:55] Planning",
        "<script>alert('xss')</script>",
    ],
)
def test_prompt_schedule_revise_guardrails_block(schedule_with_action, response):
    scratch, plan, schedule, action = schedule_with_action
    guard = Guard().use(RegexAllowlist(r"^[^{}<>]*$"))

    with pytest.raises(ValidationError):
        guard.parse(response)
