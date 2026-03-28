import importlib
import json
import pathlib
import sys

import pytest


def _reload_config(monkeypatch, tmp_path):
    settings_path = tmp_path / "settings.json"
    monkeypatch.setenv("OUROBOROS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OUROBOROS_SETTINGS_PATH", str(settings_path))
    import ouroboros.config as config_module

    return importlib.reload(config_module), settings_path


def _reload_server(monkeypatch, tmp_path):
    monkeypatch.setenv("OUROBOROS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("OUROBOROS_SETTINGS_PATH", str(tmp_path / "settings.json"))
    monkeypatch.delenv("OUROBOROS_MANAGED_BY_LAUNCHER", raising=False)
    import server as server_module

    return importlib.reload(server_module)


def test_load_settings_uses_env_fallback_for_missing_keys(monkeypatch, tmp_path):
    config_module, settings_path = _reload_config(monkeypatch, tmp_path)
    settings_path.write_text(json.dumps({"TOTAL_BUDGET": 7}), encoding="utf-8")
    file_root = tmp_path / "workspace"
    file_root.mkdir()
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-env")
    monkeypatch.setenv("OUROBOROS_FILE_BROWSER_DEFAULT", str(file_root))

    settings = config_module.load_settings()

    assert settings["TOTAL_BUDGET"] == 7.0
    assert settings["OPENAI_API_KEY"] == "sk-openai-env"
    assert settings["OUROBOROS_FILE_BROWSER_DEFAULT"] == str(file_root)


def test_load_settings_prefers_explicit_file_values_over_env(monkeypatch, tmp_path):
    config_module, settings_path = _reload_config(monkeypatch, tmp_path)
    file_root = tmp_path / "file-root"
    file_root.mkdir()
    settings_path.write_text(
        json.dumps(
            {
                "OPENAI_API_KEY": "sk-openai-file",
                "OUROBOROS_FILE_BROWSER_DEFAULT": str(file_root),
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-env")
    monkeypatch.setenv("OUROBOROS_FILE_BROWSER_DEFAULT", str(tmp_path / "env-root"))

    settings = config_module.load_settings()

    assert settings["OPENAI_API_KEY"] == "sk-openai-file"
    assert settings["OUROBOROS_FILE_BROWSER_DEFAULT"] == str(file_root)


def test_merge_settings_payload_preserves_masked_secrets(monkeypatch, tmp_path):
    server_module = _reload_server(monkeypatch, tmp_path)

    merged = server_module._merge_settings_payload(
        {
            "OPENAI_API_KEY": "sk-openai-real-secret",
            "OUROBOROS_MODEL": "openai::gpt-4.1",
        },
        {
            "OPENAI_API_KEY": "sk-opena...",
            "OUROBOROS_MODEL": "openai::gpt-5",
        },
    )

    assert merged["OPENAI_API_KEY"] == "sk-openai-real-secret"
    assert merged["OUROBOROS_MODEL"] == "openai::gpt-5"


def test_merge_settings_payload_allows_explicit_secret_clear(monkeypatch, tmp_path):
    server_module = _reload_server(monkeypatch, tmp_path)

    merged = server_module._merge_settings_payload(
        {"OPENAI_API_KEY": "sk-openai-real-secret"},
        {"OPENAI_API_KEY": ""},
    )

    assert merged["OPENAI_API_KEY"] == ""


def test_restart_current_process_reexecs_in_place(monkeypatch, tmp_path):
    server_module = _reload_server(monkeypatch, tmp_path)
    called = {}

    def _fake_execvpe(executable, argv, env):
        called["executable"] = executable
        called["argv"] = argv
        called["env"] = env
        raise RuntimeError("stop")

    monkeypatch.setattr(server_module.os, "execvpe", _fake_execvpe)

    with pytest.raises(RuntimeError, match="stop"):
        server_module._restart_current_process("127.0.0.1", 9032)

    assert called["executable"] == sys.executable
    assert called["argv"][0] == sys.executable
    assert called["env"]["OUROBOROS_SERVER_HOST"] == "127.0.0.1"
    assert called["env"]["OUROBOROS_SERVER_PORT"] == "9032"
    assert "OUROBOROS_MANAGED_BY_LAUNCHER" not in called["env"]


def test_launcher_marks_server_as_managed():
    launcher_source = (pathlib.Path(__file__).resolve().parents[1] / "launcher.py").read_text(encoding="utf-8")

    assert 'env["OUROBOROS_MANAGED_BY_LAUNCHER"] = "1"' in launcher_source
