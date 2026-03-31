"""Guardrails for README and architecture docs after UI/routing overhaul."""

import os
import pathlib

REPO = pathlib.Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _read(rel: str) -> str:
    return (REPO / rel).read_text(encoding="utf-8")


def test_readme_mentions_multistep_wizard_and_live_task_ui():
    readme = _read("README.md")

    assert "wizard is now multi-step" in readme
    assert "choose a setup path first" in readme
    assert "review visible model lanes second" in readme
    assert "Focused Task UX" in readme
    assert "live task card" in readme


def test_architecture_mentions_shared_log_grouping_and_openai_review_fallback():
    arch = _read("docs/ARCHITECTURE.md")

    assert "log_events.js" in arch
    assert "live task card" in arch
    assert "grouped task cards" in arch
    assert "OpenAI-only review fallback" in arch
