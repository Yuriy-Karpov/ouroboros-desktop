"""Helpers for resolving and syncing the project Python environment."""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Iterable, Optional


ENV_MODE_GLOBAL = "global"
ENV_MODE_UV = "uv"
_ENV_MODE_ALIASES = {
    "": ENV_MODE_GLOBAL,
    "global": ENV_MODE_GLOBAL,
    "pip": ENV_MODE_GLOBAL,
    "system": ENV_MODE_GLOBAL,
    "uv": ENV_MODE_UV,
    "venv": ENV_MODE_UV,
    "uv-venv": ENV_MODE_UV,
}
_DEFAULT_RUNTIME_EXTRAS = ("browser",)
MODE_FILE_NAME = ".ouroboros-python-env"


@dataclass(frozen=True)
class PythonEnvState:
    mode: str
    repo_dir: pathlib.Path
    base_python: str
    runtime_python: str
    venv_dir: pathlib.Path
    venv_bin_dir: pathlib.Path
    uv_bin: str

    @property
    def uses_uv(self) -> bool:
        return self.mode == ENV_MODE_UV

    @property
    def venv_exists(self) -> bool:
        return pathlib.Path(self.runtime_python).exists() and self.runtime_python.startswith(str(self.venv_dir))


def normalize_env_mode(value: str | None) -> str:
    return _ENV_MODE_ALIASES.get(str(value or "").strip().lower(), ENV_MODE_GLOBAL)


def mode_file_path(repo_dir: pathlib.Path) -> pathlib.Path:
    return pathlib.Path(repo_dir) / MODE_FILE_NAME


def read_repo_env_mode(repo_dir: pathlib.Path) -> str:
    path = mode_file_path(repo_dir)
    try:
        if path.exists():
            return normalize_env_mode(path.read_text(encoding="utf-8").strip())
    except Exception:
        pass
    return ENV_MODE_GLOBAL


def write_repo_env_mode(repo_dir: pathlib.Path, mode: str) -> pathlib.Path:
    path = mode_file_path(repo_dir)
    path.write_text(normalize_env_mode(mode) + "\n", encoding="utf-8")
    return path


def current_env_mode(
    repo_dir: pathlib.Path,
    settings: Optional[dict] = None,
    env: Optional[dict] = None,
) -> str:
    return read_repo_env_mode(repo_dir)


def _venv_bin_dir(venv_dir: pathlib.Path) -> pathlib.Path:
    return venv_dir / ("Scripts" if sys.platform == "win32" else "bin")


def venv_python_path(venv_dir: pathlib.Path) -> pathlib.Path:
    bin_dir = _venv_bin_dir(venv_dir)
    return bin_dir / ("python.exe" if sys.platform == "win32" else "python")


def find_uv_bin(env: Optional[dict] = None) -> str:
    env_map = env or os.environ
    explicit = str(env_map.get("OUROBOROS_UV_BIN", "") or "").strip()
    if explicit:
        return explicit
    return shutil.which("uv") or ""


def resolve_python_env(
    repo_dir: pathlib.Path,
    *,
    base_python: str = "",
    settings: Optional[dict] = None,
    env: Optional[dict] = None,
) -> PythonEnvState:
    repo_root = pathlib.Path(repo_dir)
    mode = current_env_mode(repo_root)
    base = str(pathlib.Path(base_python or sys.executable))
    venv_dir = repo_root / ".venv"
    runtime = base
    venv_python = venv_python_path(venv_dir)
    if mode == ENV_MODE_UV and venv_python.exists():
        runtime = str(venv_python)
    return PythonEnvState(
        mode=mode,
        repo_dir=repo_root,
        base_python=base,
        runtime_python=runtime,
        venv_dir=venv_dir,
        venv_bin_dir=_venv_bin_dir(venv_dir),
        uv_bin=find_uv_bin(env=env),
    )


def build_python_env_vars(
    state: PythonEnvState,
    *,
    env: Optional[dict] = None,
    pythonpath: pathlib.Path | str | None = None,
) -> dict:
    merged = dict(env or os.environ.copy())
    if pythonpath is not None:
        merged["PYTHONPATH"] = str(pythonpath)
    if state.uses_uv:
        merged["VIRTUAL_ENV"] = str(state.venv_dir)
        merged["UV_PROJECT_ENVIRONMENT"] = str(state.venv_dir)
        current_path = str(merged.get("PATH", "") or "")
        merged["PATH"] = os.pathsep.join(
            part for part in (str(state.venv_bin_dir), current_path) if part
        )
    else:
        merged.pop("VIRTUAL_ENV", None)
        merged.pop("UV_PROJECT_ENVIRONMENT", None)
    return merged


def _run_subprocess(command: list[str], *, env: dict, cwd: pathlib.Path, **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(command, env=env, cwd=str(cwd), **kwargs)


def ensure_uv_venv(
    state: PythonEnvState,
    *,
    capture_output: bool = False,
    timeout: int = 180,
) -> PythonEnvState:
    if not state.uses_uv:
        return state
    if not state.uv_bin:
        raise FileNotFoundError("uv executable not found. Set OUROBOROS_UV_BIN or install uv.")
    env = build_python_env_vars(state)
    _run_subprocess(
        [
            state.uv_bin,
            "venv",
            "--allow-existing",
            "--python",
            state.base_python,
            str(state.venv_dir),
        ],
        env=env,
        cwd=state.repo_dir,
        timeout=timeout,
        capture_output=capture_output,
        check=True,
        text=True,
    )
    return resolve_python_env(state.repo_dir, base_python=state.base_python, env=env)


def sync_project_dependencies(
    state: PythonEnvState,
    *,
    capture_output: bool = False,
    quiet: bool = False,
    timeout: int = 300,
    runtime_extras: Iterable[str] = _DEFAULT_RUNTIME_EXTRAS,
) -> tuple[subprocess.CompletedProcess, str, PythonEnvState]:
    env = build_python_env_vars(state)
    if not state.uses_uv:
        requirements = state.repo_dir / "requirements.txt"
        command = [state.base_python, "-m", "pip", "install"]
        if quiet:
            command.append("-q")
        source = "fallback:minimal"
        if requirements.exists():
            command += ["-r", str(requirements)]
            source = f"requirements:{requirements}"
        else:
            command += ["openai>=1.0.0", "requests"]
        result = _run_subprocess(
            command,
            env=env,
            cwd=state.repo_dir,
            timeout=timeout,
            capture_output=capture_output,
            check=False,
            text=True,
        )
        return result, source, state

    state = ensure_uv_venv(state, capture_output=capture_output, timeout=timeout)
    env = build_python_env_vars(state)
    command = [state.uv_bin, "sync", "--active"]
    for extra in runtime_extras:
        if extra:
            command += ["--extra", str(extra)]
    if (state.repo_dir / "uv.lock").exists():
        command.append("--frozen")
    result = _run_subprocess(
        command,
        env=env,
        cwd=state.repo_dir,
        timeout=timeout,
        capture_output=capture_output,
        check=False,
        text=True,
    )
    return result, f"uv-sync:{state.repo_dir / 'pyproject.toml'}", state


def install_python_packages(
    state: PythonEnvState,
    packages: Iterable[str],
    *,
    capture_output: bool = False,
    timeout: int = 180,
    upgrade: bool = False,
) -> tuple[subprocess.CompletedProcess, PythonEnvState]:
    specs = [str(pkg) for pkg in packages if str(pkg).strip()]
    if not specs:
        raise ValueError("No packages specified")

    if state.uses_uv:
        state = ensure_uv_venv(state, capture_output=capture_output, timeout=timeout)
        env = build_python_env_vars(state)
        command = [state.uv_bin, "pip", "install", "--python", state.runtime_python]
        if upgrade:
            command.append("--upgrade")
        command += specs
        result = _run_subprocess(
            command,
            env=env,
            cwd=state.repo_dir,
            timeout=timeout,
            capture_output=capture_output,
            check=False,
            text=True,
        )
        return result, state

    env = build_python_env_vars(state)
    command = [state.base_python, "-m", "pip", "install"]
    if upgrade:
        command.append("--upgrade")
    command += specs
    result = _run_subprocess(
        command,
        env=env,
        cwd=state.repo_dir,
        timeout=timeout,
        capture_output=capture_output,
        check=False,
        text=True,
    )
    return result, state
