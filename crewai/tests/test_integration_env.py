import crew.integration_env as integration_env


def test_environment_reads_project_dotenv_without_overriding_process_values(
    tmp_path,
    monkeypatch,
):
    (tmp_path / ".env").write_text(
        "DATABASE_URL=postgresql://from-file\nEMPTY=\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DATABASE_URL", "postgresql://from-process")

    environment = integration_env.environment(tmp_path)

    assert environment["DATABASE_URL"] == "postgresql://from-process"
    assert "EMPTY" not in environment
