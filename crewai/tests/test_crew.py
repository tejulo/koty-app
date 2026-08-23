from crew.crew import KotyAppCrew


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
