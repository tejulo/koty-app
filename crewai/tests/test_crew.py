import re
from pathlib import Path

import pytest
from crew.crew import KotyAppCrew
from crew.models import (
    PlanArtifactUnit,
    PlanOutline,
    ReviewVerdict,
    TesterResult as BrowserTesterResult,
    TicketContract,
)
from crewai import Process
from crewai.tools.tool_failure import ToolFailurePolicy
from crewai.utilities.constants import NOT_SPECIFIED


DOCUMENTED_ZEN_DEFAULTS = {
    "ZEN_ANALYST_MAX_TOKENS": "2000",
    "ZEN_ARCHITECT_OUTLINE_MAX_TOKENS": "4000",
    "ZEN_ARCHITECT_ARTIFACT_MAX_TOKENS": "8000",
    "ZEN_ARCHITECT_RETRY_MAX_TOKENS": "16000",
    "ZEN_ARCHITECT_LENGTH_RETRIES": "1",
    "ZEN_ARCHITECT_MAX_CONTEXT_REFS": "12",
    "ZEN_ARCHITECT_MAX_CONTEXT_CHARS": "48000",
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
    for setting in DOCUMENTED_ZEN_DEFAULTS:
        monkeypatch.delenv(setting, raising=False)
    monkeypatch.delenv("ZEN_ARCHITECT_MAX_TOKENS", raising=False)


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

    for architect_crew in (
        crew.architect_outline_crew(),
        crew.architect_artifact_crew(),
    ):
        assert not forbidden_tools.intersection(
            tool.name for tool in architect_crew.agents[0].tools
        )
    assert not forbidden_tools.intersection(
        tool.name for tool in crew.programer().tools
    )


def test_architect_has_no_filesystem_tools(monkeypatch):
    configure_models(monkeypatch)

    crew = KotyAppCrew()

    assert crew.architect_outline_crew().agents[0].tools == []
    assert crew.architect_artifact_crew().agents[0].tools == []


@pytest.mark.parametrize(
    ("crew_method", "task_name"),
    [
        ("analyst_crew", "analysis_task"),
        ("architect_outline_crew", "architect_outline_task"),
        ("architect_artifact_crew", "architect_artifact_task"),
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
    assert agent.llm.max_retries == 2


@pytest.mark.parametrize(
    ("crew_method", "kwargs", "max_tokens", "output_pydantic"),
    [
        ("architect_outline_crew", {}, 4000, PlanOutline),
        ("architect_artifact_crew", {}, 8000, PlanArtifactUnit),
        ("architect_artifact_crew", {"retry": True}, 16000, PlanArtifactUnit),
    ],
)
def test_architect_crews_disable_hidden_calls_and_remain_isolated(
    monkeypatch,
    crew_method,
    kwargs,
    max_tokens,
    output_pydantic,
):
    configure_models(monkeypatch)
    crew = getattr(KotyAppCrew(), crew_method)(**kwargs)
    agent = crew.agents[0]
    task = crew.tasks[0]

    assert len(crew.agents) == 1
    assert len(crew.tasks) == 1
    assert task.agent is agent
    assert task.output_pydantic is output_pydantic
    assert task.context is NOT_SPECIFIED
    assert crew.process is Process.sequential
    assert crew.manager_agent is None
    assert crew.manager_llm is None
    assert crew.planning is False
    assert agent.tools == []
    assert agent.allow_delegation is False
    assert agent.max_iter == 1
    assert agent.max_retry_limit == 0
    assert agent.llm.max_tokens == max_tokens
    assert agent.llm.reasoning_effort == "low"
    assert agent.llm.max_retries == 0
    assert agent.respect_context_window is False


def test_legacy_architect_entry_point_is_removed_after_supervisor_migration(monkeypatch):
    configure_models(monkeypatch)

    crew = KotyAppCrew()

    assert not hasattr(crew, "architect_crew")
    assert not hasattr(crew, "architecture_task")


@pytest.mark.parametrize(
    ("agent_method", "max_tokens_env"),
    [
        ("analyst", "ZEN_ANALYST_MAX_TOKENS"),
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


def test_architect_crews_honor_independent_configured_token_limits(monkeypatch):
    configure_models(monkeypatch)
    monkeypatch.setenv("ZEN_ARCHITECT_OUTLINE_MAX_TOKENS", "4100")
    monkeypatch.setenv("ZEN_ARCHITECT_ARTIFACT_MAX_TOKENS", "8200")
    monkeypatch.setenv("ZEN_ARCHITECT_RETRY_MAX_TOKENS", "16400")
    crew = KotyAppCrew()

    outline = crew.architect_outline_crew()
    artifact = crew.architect_artifact_crew()
    retry = crew.architect_artifact_crew(retry=True)

    assert outline.agents[0].llm.max_tokens == 4100
    assert artifact.agents[0].llm.max_tokens == 8200
    assert retry.agents[0].llm.max_tokens == 16400
    assert crew.architect_artifact_crew().agents[0].llm.max_tokens == 8200


def test_tasks_bind_structured_contract_outputs(monkeypatch):
    configure_models(monkeypatch)
    crew = KotyAppCrew()

    assert crew.analysis_task().output_pydantic is TicketContract
    assert crew.architect_outline_crew().tasks[0].output_pydantic is PlanOutline
    assert crew.architect_artifact_crew().tasks[0].output_pydantic is PlanArtifactUnit
    assert crew.testing_task().output_pydantic is BrowserTesterResult


def test_architect_tasks_receive_only_their_staged_inputs(monkeypatch):
    configure_models(monkeypatch)
    crew = KotyAppCrew()
    outline = crew.architect_outline_crew().tasks[0]
    artifact = crew.architect_artifact_crew().tasks[0]

    assert set(re.findall(r"{([A-Za-z_][A-Za-z0-9_-]*)}", outline.description)) == {
        "ticket_contract_json",
        "context_index",
    }
    assert set(re.findall(r"{([A-Za-z_][A-Za-z0-9_-]*)}", artifact.description)) == {
        "ticket_contract_json",
        "plan_outline_json",
        "plan_unit_outline_json",
        "project_context",
    }
    assert "PlanOutline" in outline.description
    assert "PlanArtifactUnit" in artifact.description
    assert "No uses herramientas" in outline.description
    assert "No uses herramientas" in artifact.description


def test_architect_artifact_prompt_requires_exact_design_and_spec_contracts(
    monkeypatch,
):
    configure_models(monkeypatch)

    description = KotyAppCrew().architect_artifact_crew().tasks[0].description

    assert "exactamente un verification_profile" in description
    assert "PlanOutline.profile" in description
    assert "Browser E2E: required" in description
    assert "Browser E2E: not_required" in description
    assert "## ADDED Requirements" in description
    assert "## MODIFIED Requirements" in description
    assert "## REMOVED Requirements" in description
    assert "## RENAMED Requirements" in description
    assert "#### Scenario:" in description


def test_env_example_documents_staged_architect_defaults():
    env_example = Path(__file__).parents[1] / ".env.example"
    values = {
        name: value
        for name, value in (
            line.split("=", maxsplit=1)
            for line in env_example.read_text(encoding="utf-8").splitlines()
            if line.startswith("ZEN_") and "=" in line
        )
        if name in DOCUMENTED_ZEN_DEFAULTS
    }

    assert values == DOCUMENTED_ZEN_DEFAULTS
    assert "ZEN_ARCHITECT_MAX_TOKENS=" not in env_example.read_text(encoding="utf-8")


def test_role_tasks_accept_their_phase_contract_paths_and_authoritative_hashes(monkeypatch):
    configure_models(monkeypatch)
    crew = KotyAppCrew()

    assert set(re.findall(r"{([A-Za-z_][A-Za-z0-9_-]*)}", crew.analysis_task().description)) == {
        "ticket_id",
        "change_id",
        "ticket_sha256",
    }
    assert set(re.findall(r"{([A-Za-z_][A-Za-z0-9_-]*)}", crew.architect_outline_crew().tasks[0].description)) == {
        "ticket_contract_json",
        "context_index",
    }
    assert set(re.findall(r"{([A-Za-z_][A-Za-z0-9_-]*)}", crew.architect_artifact_crew().tasks[0].description)) == {
        "ticket_contract_json",
        "plan_outline_json",
        "plan_unit_outline_json",
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
