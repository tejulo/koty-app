import re
from pathlib import Path

import pytest
from crew.crew import KotyAppCrew
from crew.models import (
    PlanDraft,
    ReviewVerdict,
    TesterResult as BrowserTesterResult,
    TicketContract,
)
from crewai import Process
from crewai.tools.tool_failure import ToolFailurePolicy
from crewai.utilities.constants import NOT_SPECIFIED


DOCUMENTED_TOKEN_DEFAULTS = {
    "ZEN_ANALYST_MAX_TOKENS": "2000",
    "ZEN_ARCHITECT_MAX_TOKENS": "4000",
    "ZEN_CODER_MAX_TOKENS": "2500",
    "ZEN_TESTER_MAX_TOKENS": "600",
    "ZEN_REVIEWER_MAX_TOKENS": "800",
}


def configure_models(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "test")
    for model_env in (
        "ZEN_ANALYST_MODEL",
        "ZEN_ARCHITECT_MODEL",
        "ZEN_CODER_MODEL",
        "ZEN_TESTER_MODEL",
        "ZEN_REVIEWER_MODEL",
    ):
        monkeypatch.setenv(model_env, "openai/gpt-4o-mini")
    for max_tokens_env in DOCUMENTED_TOKEN_DEFAULTS:
        monkeypatch.delenv(max_tokens_env, raising=False)


def test_analyst_solo_recibe_tools_linear_de_inicio(monkeypatch):
    configure_models(monkeypatch)

    agent = KotyAppCrew().analyst()

    assert {tool.name for tool in agent.tools} == {
        "Buscar Tarea en Linear",
    }


def test_reviewer_no_recibe_gates_autoritativas(monkeypatch):
    configure_models(monkeypatch)

    agent = KotyAppCrew().reviewer()

    tool_names = {tool.name for tool in agent.tools}

    assert "Ejecutar Verificacion" not in tool_names
    assert "Ejecutar OpenSpec" not in tool_names
    assert "Buscar Tarea en Linear" not in tool_names


def test_review_task_returns_a_qualitative_verdict(monkeypatch):
    configure_models(monkeypatch)

    assert KotyAppCrew().review_task().output_pydantic is ReviewVerdict


def test_analyst_eleva_fallos_de_herramientas(monkeypatch):
    configure_models(monkeypatch)
    crew = KotyAppCrew()

    assert crew.analyst().tool_failure_policy is ToolFailurePolicy.RAISE


def test_arquitect_y_programer_no_reciben_tools_de_mutacion_linear(
    monkeypatch,
):
    configure_models(monkeypatch)

    crew = KotyAppCrew()
    forbidden_tools = {
        "Buscar Tarea en Linear",
    }

    assert not forbidden_tools.intersection(
        tool.name for tool in crew.arquitect().tools
    )
    assert not forbidden_tools.intersection(
        tool.name for tool in crew.programer().tools
    )


def test_architect_has_no_filesystem_tools(monkeypatch):
    configure_models(monkeypatch)

    assert KotyAppCrew().arquitect().tools == []


@pytest.mark.parametrize(
    ("crew_method", "task_name"),
    [
        ("analyst_crew", "analysis_task"),
        ("architect_crew", "architecture_task"),
        ("programmer_crew", "coding_task"),
        ("tester_crew", "testing_task"),
        ("reviewer_crew", "review_task"),
    ],
)
def test_each_role_runs_in_an_isolated_one_task_crew(
    monkeypatch,
    crew_method,
    task_name,
):
    configure_models(monkeypatch)

    crew = getattr(KotyAppCrew(), crew_method)()

    assert [task.name for task in crew.tasks] == [task_name]
    assert crew.process is Process.sequential
    assert crew.manager_agent is None
    assert crew.manager_llm is None
    assert crew.planning is False
    assert crew.tasks[0].context is NOT_SPECIFIED
    assert crew.tasks[0].agent.allow_delegation is False


@pytest.mark.parametrize(
    ("agent_method", "max_iter", "max_tokens"),
    [
        ("analyst", 4, 2000),
        ("arquitect", 1, 4000),
        ("programer", 20, 2500),
        ("tester", 8, 600),
        ("reviewer", 8, 800),
    ],
)
def test_each_role_uses_its_documented_default_limits(
    monkeypatch,
    agent_method,
    max_iter,
    max_tokens,
):
    configure_models(monkeypatch)

    agent = getattr(KotyAppCrew(), agent_method)()

    assert agent.max_iter == max_iter
    assert agent.llm.max_tokens == max_tokens
    assert agent.llm.temperature == 0.2
    assert agent.respect_context_window is True
    assert agent.allow_delegation is False


@pytest.mark.parametrize(
    ("agent_method", "max_tokens_env"),
    [
        ("analyst", "ZEN_ANALYST_MAX_TOKENS"),
        ("arquitect", "ZEN_ARCHITECT_MAX_TOKENS"),
        ("programer", "ZEN_CODER_MAX_TOKENS"),
        ("tester", "ZEN_TESTER_MAX_TOKENS"),
        ("reviewer", "ZEN_REVIEWER_MAX_TOKENS"),
    ],
)
def test_each_role_honors_its_configured_token_limit(
    monkeypatch,
    agent_method,
    max_tokens_env,
):
    configure_models(monkeypatch)
    monkeypatch.setenv(max_tokens_env, "777")

    agent = getattr(KotyAppCrew(), agent_method)()

    assert agent.llm.max_tokens == 777


def test_tasks_bind_structured_contract_outputs(monkeypatch):
    configure_models(monkeypatch)
    crew = KotyAppCrew()

    assert crew.analysis_task().output_pydantic is TicketContract
    assert crew.architecture_task().output_pydantic is PlanDraft
    assert crew.testing_task().output_pydantic is BrowserTesterResult


def test_architecture_task_documents_structured_plan_draft(monkeypatch):
    configure_models(monkeypatch)
    description = KotyAppCrew().architecture_task().description

    assert "{ticket_contract_json}" in description
    assert "{project_context}" in description
    assert "PlanDraft" in description
    assert "No uses herramientas" in description
    assert "## ADDED Requirements" in description


def test_env_example_documents_all_role_token_defaults():
    env_example = Path(__file__).parents[1] / ".env.example"
    values = {
        name: value
        for name, value in (
            line.split("=", maxsplit=1)
            for line in env_example.read_text(encoding="utf-8").splitlines()
            if line.startswith("ZEN_") and "=" in line
        )
        if name in DOCUMENTED_TOKEN_DEFAULTS
    }

    assert values == DOCUMENTED_TOKEN_DEFAULTS


def test_role_tasks_accept_their_phase_contract_paths_and_authoritative_hashes(monkeypatch):
    configure_models(monkeypatch)
    crew = KotyAppCrew()

    assert set(re.findall(r"{([A-Za-z_][A-Za-z0-9_-]*)}", crew.analysis_task().description)) == {
        "ticket_id",
        "change_id",
        "ticket_sha256",
    }
    assert set(re.findall(r"{([A-Za-z_][A-Za-z0-9_-]*)}", crew.architecture_task().description)) == {
        "ticket_contract_json",
        "project_context",
    }
    assert set(re.findall(r"{([A-Za-z_][A-Za-z0-9_-]*)}", crew.coding_task().description)) == {
        "plan_manifest_path",
        "repair_pack_path",
    }
    assert set(re.findall(r"{([A-Za-z_][A-Za-z0-9_-]*)}", crew.testing_task().description)) == {
        "verification_profile_path",
        "scenario_paths",
    }
    assert set(re.findall(r"{([A-Za-z_][A-Za-z0-9_-]*)}", crew.review_task().description)) == {
        "review_pack_path",
    }


def test_programmer_does_not_receive_authoritative_gate_control(monkeypatch):
    configure_models(monkeypatch)
    crew = KotyAppCrew()

    assert "Ejecutar Verificacion" not in {
        tool.name for tool in crew.programer().tools
    }
    assert "python" not in crew.coding_task().description
    assert "integration" not in crew.coding_task().description


def test_analyst_crew_writes_task_output_to_configured_log(monkeypatch):
    configure_models(monkeypatch)
    monkeypatch.setenv("CREWAI_OUTPUT_LOG_FILE", "/tmp/crew.log")

    crew = KotyAppCrew().analyst_crew()

    assert crew.output_log_file == "/tmp/crew.log"
