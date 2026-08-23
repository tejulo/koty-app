from crew.crew import KotyAppCrew
from crewai.tools.tool_failure import ToolFailurePolicy


def test_analyst_solo_recibe_tools_linear_de_inicio(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "test")
    monkeypatch.setenv("ZEN_ANALYST_MODEL", "openai/gpt-4o-mini")

    agent = KotyAppCrew().analyst()

    assert {tool.name for tool in agent.tools} == {
        "Buscar Tarea en Linear",
        "Marcar Tarea en Progreso",
    }


def test_reviewer_recibe_completar_linear(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "test")
    monkeypatch.setenv("ZEN_REVIEWER_MODEL", "openai/gpt-4o-mini")

    agent = KotyAppCrew().reviewer()

    assert "Completar Tarea en Linear" in {tool.name for tool in agent.tools}
    assert "Marcar Tarea en Progreso" not in {tool.name for tool in agent.tools}


def test_analyst_y_reviewer_elevan_fallos_de_herramientas(monkeypatch):
    monkeypatch.setenv("OPENCODE_API_KEY", "test")
    monkeypatch.setenv("ZEN_ANALYST_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("ZEN_REVIEWER_MODEL", "openai/gpt-4o-mini")

    crew = KotyAppCrew()

    assert crew.analyst().tool_failure_policy is ToolFailurePolicy.RAISE
    assert crew.reviewer().tool_failure_policy is ToolFailurePolicy.RAISE


def test_arquitect_y_programer_no_reciben_tools_de_mutacion_linear(
    monkeypatch,
):
    monkeypatch.setenv("OPENCODE_API_KEY", "test")
    monkeypatch.setenv("ZEN_ARCHITECT_MODEL", "openai/gpt-4o-mini")
    monkeypatch.setenv("ZEN_CODER_MODEL", "openai/gpt-4o-mini")

    crew = KotyAppCrew()
    forbidden_tools = {
        "Marcar Tarea en Progreso",
        "Completar Tarea en Linear",
    }

    assert not forbidden_tools.intersection(
        tool.name for tool in crew.arquitect().tools
    )
    assert not forbidden_tools.intersection(
        tool.name for tool in crew.programer().tools
    )
