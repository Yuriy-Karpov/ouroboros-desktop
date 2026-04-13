"""Process-control helpers for the self-editable server entrypoint."""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
from typing import Any

from ouroboros.config import load_settings
from ouroboros.python_env import build_python_env_vars, resolve_python_env


def restart_current_process(host: str, port: int, *, repo_dir: pathlib.Path, log: Any) -> None:
    settings = load_settings()
    env_state = resolve_python_env(repo_dir, base_python=sys.executable, settings=settings)
    env = build_python_env_vars(env_state, env=os.environ.copy(), pythonpath=repo_dir)
    env["OUROBOROS_SERVER_HOST"] = str(host)
    env["OUROBOROS_SERVER_PORT"] = str(port)
    env.pop("OUROBOROS_MANAGED_BY_LAUNCHER", None)
    argv = [env_state.runtime_python, *sys.argv]
    log.info("Re-executing direct server mode on %s:%d via %s", host, port, env_state.runtime_python)
    try:
        os.execvpe(env_state.runtime_python, argv, env)
    except Exception:
        log.exception("Direct re-exec failed; attempting spawned restart fallback.")
        try:
            subprocess.Popen(argv, env=env, cwd=str(repo_dir))
            log.info("Spawned replacement server process after exec failure.")
        except Exception:
            log.exception("Spawned restart fallback failed; exiting with restart code only.")


def execute_panic_stop(
    consciousness: Any,
    kill_workers_fn,
    *,
    data_dir: pathlib.Path,
    panic_exit_code: int,
    log: Any,
) -> None:
    """Full emergency stop: kill everything, write panic flag, hard-exit."""
    log.critical("PANIC STOP initiated.")
    try:
        consciousness.stop()
    except Exception:
        pass

    try:
        from supervisor.state import load_state, save_state

        st = load_state()
        st["evolution_mode_enabled"] = False
        st["bg_consciousness_enabled"] = False
        save_state(st)
    except Exception:
        pass

    try:
        panic_flag = data_dir / "state" / "panic_stop.flag"
        panic_flag.parent.mkdir(parents=True, exist_ok=True)
        panic_flag.write_text("panic", encoding="utf-8")
    except Exception:
        pass

    try:
        from ouroboros.local_model import get_manager

        get_manager().stop_server()
    except Exception:
        pass

    try:
        from ouroboros.tools.shell import kill_all_tracked_subprocesses

        kill_all_tracked_subprocesses()
    except Exception:
        pass

    try:
        kill_workers_fn(force=True)
    except Exception:
        pass

    try:
        import multiprocessing
        from ouroboros.platform_layer import force_kill_pid, kill_process_on_port

        for child in multiprocessing.active_children():
            try:
                force_kill_pid(child.pid)
            except (ProcessLookupError, PermissionError):
                pass
        kill_process_on_port(8765)
        kill_process_on_port(8766)
    except Exception:
        pass

    log.critical("PANIC STOP complete — hard exit with code %d.", panic_exit_code)
    os._exit(panic_exit_code)
