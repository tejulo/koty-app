from crew.crew import KotyAppCrew
from crew.models import ReviewVerdict
from crewai.tools.tool_failure import ToolFailurePolicy


def test_analyst_solo_recibe_tools_linear_de_inicio(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "test")
    monkeypatch.setenv("ZEN_ANALYST_MODEL", "openai/gpt-4o-mini")

    agent = KotyAppCrew().analyst()

    assert {tool.name for tool in agent.tools} == {
        "Buscar Tarea en Linear",
    }


def test_reviewer_no_recibe_gates_autoritativas(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "test")
    monkeypatch.setenv("ZEN_REVIEWER_MODEL", "openai/gpt-4o-mini")

    agent = KotyAppCrew().reviewer()

    tool_names = {tool.name for tool in agent.tools}

    assert "Ejecutar Verificacion" not in tool_names
    assert "Ejecutar OpenSpec" not in tool_names
    assert "Buscar Tarea en Linear" not in tool_names


def test_review_task_returns_a_qualitative_verdict(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "test")
    monkeypatch.setenv("ZEN_REVIEWER_MODEL", "openai/gpt-4o-mini")

    assert KotyAppCrew().review_task().output_pydantic is ReviewVerdict


def test_review_task_does_not_request_gate_evidence(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "test")
    monkeypatch.setenv("ZEN_REVIEWER_MODEL", "openai/gpt-4o-mini")

    description = KotyAppCrew().review_task().description

    assert "Evidence:" not in description
    assert "Resultado estructurado con ticket_id, change_id, status" in (
        KotyAppCrew().review_task().expected_output
    )


def test_analyst_eleva_fallos_de_herramientas(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "test")
    monkeypatch.setenv("ZEN_ANALYST_MODEL", "openai/gpt-4o-mini")
    crew = KotyAppCrew()

    assert crew.analyst().tool_failure_policy is ToolFailurePolicy.RAISE


def test_arquitect_y_programer_no_reciben_tools_de_mutacion_linear(
    monkeypatch,
):
    monkeypatch.setenv("OPENCODE_API_KEY", "test")
    monkeypatch.setenv("ZEN_ARCHITECT_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("ZEN_CODER_MODEL", "openai/gpt-4o-mini")

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


def test_task_prompts_forbid_deferring_required_implementation(
    monkeypatch,
):
    monkeypatch.setenv("OPENCODE_API_KEY", "test")
    monkeypatch.setenv("ZEN_ARCHITECT_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("ZEN_CODER_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("ZEN_REVIEWER_MODEL", "openai/gpt-4o-mini")
    crew = KotyAppCrew()

    assert "No declares fuera de alcance" in (
        crew.architecture_task().description
    )
    assert "No aceptes tareas" in crew.coding_task().description
    assert "Rechaza como retryable_failure" in (
        crew.review_task().description
    )


def test_coder_and_reviewer_receive_shared_integration_repair_policy(
    monkeypatch,
):
    monkeypatch.setenv("OPENCODE_API_KEY", "test")
    monkeypatch.setenv("ZEN_CODER_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("ZEN_REVIEWER_MODEL", "openai/gpt-4o-mini")
    crew = KotyAppCrew()

    assert "{last_repair_diagnosis_path}" in crew.coding_task().description
    assert "repairScope" in crew.coding_task().description
    assert "repairScope" in crew.review_task().description


def test_crew_writes_task_output_to_configured_log(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "test")
    monkeypatch.setenv("ZEN_ARCHITECT_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("ZEN_CODER_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("ZEN_REVIEWER_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("CREWAI_OUTPUT_LOG_FILE", "/tmp/crew.log")

    crew = KotyAppCrew().crew()

    assert crew.output_log_file == "/tmp/crew.log"


def test_crews_split_planning_from_delivery(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "test")
    monkeypatch.setenv("ZEN_ANALYST_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("ZEN_ARCHITECT_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("ZEN_CODER_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("ZEN_REVIEWER_MODEL", "openai/gpt-4o-mini")

    crew = KotyAppCrew()

    assert [task.name for task in crew.planning_crew().tasks] == [
        "analysis_task",
        "architecture_task",
    ]
    assert [task.name for task in crew.delivery_crew().tasks] == [
        "coding_task",
        "testing_task",
        "review_task",
    ]
