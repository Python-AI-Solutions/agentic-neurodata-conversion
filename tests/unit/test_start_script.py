import pytest


def test_require_dotenv_files_errors_when_missing_env(capsys, tmp_path):
    from scripts.startup.start_app import require_dotenv_files

    missing_env = tmp_path / ".env"
    with pytest.raises(SystemExit):
        require_dotenv_files(str(missing_env), require_docker_env=False)

    out = capsys.readouterr().out
    assert "Missing env file" in out
    assert "cp .env.example .env" in out


def test_require_dotenv_files_allows_missing_docker_env_when_not_using_docker(capsys, tmp_path):
    from scripts.startup.start_app import require_dotenv_files

    env_path = tmp_path / ".env"
    env_path.write_text("CORE__ALLOW_MISSING_ANTHROPIC_API_KEY=true\n")

    require_dotenv_files(str(env_path), require_docker_env=False)

    out = capsys.readouterr().out
    assert "Missing docker env overrides" not in out


def test_require_dotenv_files_errors_when_missing_docker_env_and_using_docker(capsys, tmp_path):
    from scripts.startup.start_app import require_dotenv_files

    env_path = tmp_path / ".env"
    env_path.write_text("CORE__ALLOW_MISSING_ANTHROPIC_API_KEY=true\n")

    with pytest.raises(SystemExit):
        require_dotenv_files(str(env_path), require_docker_env=True)

    out = capsys.readouterr().out
    assert "Missing docker env overrides" in out
    assert "cp .env.docker.example .env.docker" in out


def test_validate_configuration_allows_missing_anthropic_key_without_warning(capsys, monkeypatch):
    from scripts.startup.start_app import validate_configuration

    monkeypatch.delenv("ENV_FILE", raising=False)
    monkeypatch.delenv("CORE__ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("CORE__ALLOW_MISSING_ANTHROPIC_API_KEY", "true")
    validate_configuration()

    out = capsys.readouterr().out
    assert "Missing CORE__ANTHROPIC_API_KEY" not in out
    assert "⚠" not in out


def test_validate_configuration_errors_when_missing_anthropic_key(capsys, monkeypatch):
    from scripts.startup.start_app import validate_configuration

    monkeypatch.delenv("ENV_FILE", raising=False)
    monkeypatch.delenv("CORE__ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CORE__ALLOW_MISSING_ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(SystemExit):
        validate_configuration()

    out = capsys.readouterr().out
    assert "Missing CORE__ANTHROPIC_API_KEY" in out
    assert "cp .env.example .env" in out


def test_docker_daemon_unavailable_prints_help(capsys, monkeypatch):
    from scripts.startup import start_app

    class Result:
        returncode = 1
        stdout = ""
        stderr = "Cannot connect"

    monkeypatch.setattr(start_app.subprocess, "run", lambda *a, **k: Result())

    assert start_app.docker_daemon_available() is False
    start_app.print_docker_help()

    out = capsys.readouterr().out
    assert "Docker daemon is not reachable" in out
    assert "docker info" in out
