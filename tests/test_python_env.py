import os
import pathlib
import sys

from ouroboros.python_env import (
    ENV_MODE_GLOBAL,
    ENV_MODE_UV,
    build_python_env_vars,
    normalize_env_mode,
    read_repo_env_mode,
    resolve_python_env,
    write_repo_env_mode,
)


def test_normalize_env_mode_supports_uv_aliases():
    assert normalize_env_mode("global") == ENV_MODE_GLOBAL
    assert normalize_env_mode("pip") == ENV_MODE_GLOBAL
    assert normalize_env_mode("uv") == ENV_MODE_UV
    assert normalize_env_mode("venv") == ENV_MODE_UV
    assert normalize_env_mode("uv-venv") == ENV_MODE_UV


def test_resolve_python_env_prefers_repo_venv_when_enabled(tmp_path):
    bin_dir = "Scripts" if sys.platform == "win32" else "bin"
    python_name = "python.exe" if sys.platform == "win32" else "python"
    venv_python = tmp_path / ".venv" / bin_dir / python_name
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("", encoding="utf-8")

    state = resolve_python_env(
        tmp_path,
        base_python="/usr/bin/python3",
        settings={"OUROBOROS_PYTHON_ENV_MODE": "uv"},
    )

    assert state.mode == ENV_MODE_UV
    assert state.runtime_python == str(venv_python)


def test_build_python_env_vars_exports_virtualenv(tmp_path):
    venv_dir = tmp_path / ".venv"
    bin_dir = "Scripts" if sys.platform == "win32" else "bin"
    python_name = "python.exe" if sys.platform == "win32" else "python"
    venv_python = venv_dir / bin_dir / python_name
    venv_python.parent.mkdir(parents=True)
    venv_python.write_text("", encoding="utf-8")

    state = resolve_python_env(
        tmp_path,
        base_python="/usr/bin/python3",
        settings={"OUROBOROS_PYTHON_ENV_MODE": "uv"},
    )
    env = build_python_env_vars(state, env={"PATH": "/usr/bin"})

    assert env["VIRTUAL_ENV"] == str(venv_dir)
    assert env["UV_PROJECT_ENVIRONMENT"] == str(venv_dir)
    assert env["PATH"].split(os.pathsep)[0] == str(venv_python.parent)


def test_resolve_python_env_reads_repo_mode_file(tmp_path):
    write_repo_env_mode(tmp_path, "uv")

    state = resolve_python_env(
        tmp_path,
        base_python="/usr/bin/python3",
    )

    assert read_repo_env_mode(tmp_path) == ENV_MODE_UV
    assert state.mode == ENV_MODE_UV
