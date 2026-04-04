"""Tests for ouroboros.deep_self_review module."""

from __future__ import annotations

import os
import pathlib
from unittest import mock

import pytest

from ouroboros.deep_self_review import (
    build_review_pack,
    is_review_available,
    run_deep_self_review,
)


@pytest.fixture
def tmp_repo(tmp_path):
    """Create a minimal git repo with tracked files."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "main.py").write_text("print('hello')\n")
    (repo / "lib.py").write_text("def add(a, b): return a + b\n")
    return repo


@pytest.fixture
def tmp_drive(tmp_path):
    """Create a drive root with some memory files."""
    drive = tmp_path / "drive"
    drive.mkdir()
    mem = drive / "memory"
    mem.mkdir()
    (mem / "identity.md").write_text("I am Ouroboros.\n")
    (mem / "scratchpad.md").write_text("Working notes.\n")
    know = mem / "knowledge"
    know.mkdir()
    (know / "patterns.md").write_text("## Patterns\n- Error class A\n")
    return drive


class TestBuildReviewPack:
    def test_reads_tracked_files(self, tmp_repo, tmp_drive):
        """git ls-files output determines which repo files are included."""
        git_output = "main.py\nlib.py\n"
        with mock.patch("ouroboros.deep_self_review.subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(stdout=git_output, returncode=0)
            pack, stats = build_review_pack(tmp_repo, tmp_drive)

        assert "## FILE: main.py" in pack
        assert "## FILE: lib.py" in pack
        assert "print('hello')" in pack
        assert stats["file_count"] >= 2

    def test_includes_memory_whitelist(self, tmp_repo, tmp_drive):
        """Memory whitelist files from drive_root are included."""
        with mock.patch("ouroboros.deep_self_review.subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(stdout="main.py\n", returncode=0)
            pack, stats = build_review_pack(tmp_repo, tmp_drive)

        assert "## FILE: drive/memory/identity.md" in pack
        assert "I am Ouroboros." in pack
        assert "## FILE: drive/memory/scratchpad.md" in pack
        assert "## FILE: drive/memory/knowledge/patterns.md" in pack

    def test_skips_missing_memory(self, tmp_repo, tmp_drive):
        """Missing memory files are silently skipped."""
        with mock.patch("ouroboros.deep_self_review.subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(stdout="main.py\n", returncode=0)
            pack, stats = build_review_pack(tmp_repo, tmp_drive)

        # registry.md, WORLD.md, index-full.md don't exist — should not appear
        assert "registry.md" not in pack
        assert "WORLD.md" not in pack
        assert "index-full.md" not in pack


class TestIsReviewAvailable:
    def test_openrouter(self):
        with mock.patch.dict(os.environ, {"OPENROUTER_API_KEY": "sk-or-test"}, clear=False):
            available, model = is_review_available()
        assert available is True
        assert model == "openai/gpt-5.4-pro"

    def test_openai(self):
        env = {"OPENAI_API_KEY": "sk-test"}
        with mock.patch.dict(os.environ, env, clear=False):
            # Ensure OPENROUTER_API_KEY and OPENAI_BASE_URL are not set
            os.environ.pop("OPENROUTER_API_KEY", None)
            os.environ.pop("OPENAI_BASE_URL", None)
            available, model = is_review_available()
        assert available is True
        assert model == "openai::gpt-5.4-pro"

    def test_none(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            available, model = is_review_available()
        assert available is False
        assert model is None


class TestRequestToolEmitsEvent:
    def test_emits_correct_event(self):
        """_request_deep_self_review emits a deep_self_review_request event."""
        from ouroboros.tools.control import _request_deep_self_review

        class FakeCtx:
            pending_events = []

        ctx = FakeCtx()
        with mock.patch(
            "ouroboros.deep_self_review.is_review_available",
            return_value=(True, "openai/gpt-5.4-pro"),
        ):
            result = _request_deep_self_review(ctx, "test reason")
        assert len(ctx.pending_events) == 1
        evt = ctx.pending_events[0]
        assert evt["type"] == "deep_self_review_request"
        assert evt["reason"] == "test reason"
        assert evt["model"] == "openai/gpt-5.4-pro"
        assert "Deep self-review" in result

    def test_unavailable_returns_error(self):
        """When no API key is available, returns error without emitting event."""
        from ouroboros.tools.control import _request_deep_self_review

        class FakeCtx:
            pending_events = []

        ctx = FakeCtx()
        with mock.patch(
            "ouroboros.deep_self_review.is_review_available",
            return_value=(False, None),
        ):
            result = _request_deep_self_review(ctx, "test reason")
        assert len(ctx.pending_events) == 0
        assert "unavailable" in result


class TestVendoredFilesExcluded:
    def test_minified_js_skipped(self, tmp_repo, tmp_drive):
        """Files with .min.js suffix are excluded from the review pack."""
        (tmp_repo / "lib.min.js").write_text("!function(){var a=1;}()\n")
        git_output = "main.py\nlib.min.js\n"
        with mock.patch("ouroboros.deep_self_review.subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(stdout=git_output, returncode=0)
            pack, stats = build_review_pack(tmp_repo, tmp_drive)

        assert "lib.min.js" not in pack or "vendored/minified" in str(stats["skipped"])
        assert "## FILE: lib.min.js" not in pack

    def test_chart_umd_skipped(self, tmp_repo, tmp_drive):
        """chart.umd.min.js (vendored Chart.js) is excluded by name and appears in OMITTED section."""
        (tmp_repo / "chart.umd.min.js").write_text("!function(t,e){/* chart.js minified */}()\n")
        git_output = "main.py\nchart.umd.min.js\n"
        with mock.patch("ouroboros.deep_self_review.subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(stdout=git_output, returncode=0)
            pack, stats = build_review_pack(tmp_repo, tmp_drive)

        assert "## FILE: chart.umd.min.js" not in pack
        assert any("chart.umd.min.js" in s for s in stats["skipped"])
        # Omission section must be present and mention the file
        assert "## OMITTED FILES" in pack
        assert "chart.umd.min.js" in pack

    def test_min_css_skipped(self, tmp_repo, tmp_drive):
        """Files with .min.css suffix are excluded."""
        (tmp_repo / "style.min.css").write_text("body{margin:0}a{color:red}\n")
        git_output = "main.py\nstyle.min.css\n"
        with mock.patch("ouroboros.deep_self_review.subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(stdout=git_output, returncode=0)
            pack, stats = build_review_pack(tmp_repo, tmp_drive)

        assert "## FILE: style.min.css" not in pack
        assert any("style.min.css" in s for s in stats["skipped"])

    def test_regular_js_included(self, tmp_repo, tmp_drive):
        """Regular (non-minified) JS files are NOT excluded."""
        (tmp_repo / "app.js").write_text("console.log('hello');\n")
        git_output = "main.py\napp.js\n"
        with mock.patch("ouroboros.deep_self_review.subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(stdout=git_output, returncode=0)
            pack, stats = build_review_pack(tmp_repo, tmp_drive)

        assert "## FILE: app.js" in pack
        assert not any("app.js" in s for s in stats["skipped"])

    def test_omission_section_after_memory_whitelist(self, tmp_repo, tmp_drive):
        """OMITTED FILES section is appended after both repo and memory passes, capturing all skips.

        Simulates a memory-whitelist read error by patching pathlib.Path.read_text so that
        identity.md raises PermissionError, ensuring it lands in skipped and the OMITTED section.
        """
        (tmp_repo / "lib.min.js").write_text("minified\n")
        git_output = "main.py\nlib.min.js\n"
        (tmp_drive / "memory" / "identity.md").write_text("I am Ouroboros.\n")
        target_path = str(tmp_drive / "memory" / "identity.md")

        original_read_text = pathlib.Path.read_text

        def patched_read_text(self, encoding="utf-8", errors="replace"):
            if str(self) == target_path:
                raise PermissionError("mocked read error")
            return original_read_text(self, encoding=encoding, errors=errors)

        with mock.patch("ouroboros.deep_self_review.subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(stdout=git_output, returncode=0)
            with mock.patch("pathlib.Path.read_text", patched_read_text):
                pack, stats = build_review_pack(tmp_repo, tmp_drive)

        assert "## OMITTED FILES" in pack
        omitted_section_pos = pack.index("## OMITTED FILES")
        # Vendored file listed in omitted section
        assert "lib.min.js" in pack[omitted_section_pos:]
        # Memory read error captured in skipped
        memory_errors = [s for s in stats["skipped"] if "identity.md" in s and "read error" in s]
        assert memory_errors, "identity.md read error should appear in skipped"
        # And it appears in the OMITTED section too
        assert "identity.md" in pack[omitted_section_pos:]


class TestReviewPackOverflow:
    def test_explicit_error_on_overflow(self, tmp_repo, tmp_drive):
        """When pack exceeds ~900K tokens, run_deep_self_review returns an error."""
        # Create a pack that's way too large (> 3.15M chars ≈ 900K tokens)
        huge_pack = "x" * 4_000_000
        mock_llm = mock.Mock()

        with mock.patch(
            "ouroboros.deep_self_review.build_review_pack",
            return_value=(huge_pack, {"file_count": 100, "total_chars": 4_000_000, "skipped": []}),
        ):
            result, usage = run_deep_self_review(
                repo_dir=tmp_repo,
                drive_root=tmp_drive,
                llm=mock_llm,
                emit_progress=lambda x: None,
                event_queue=None,
                model="test-model",
            )

        assert "too large" in result
        assert "900,000" in result
        assert usage == {}
        mock_llm.chat.assert_not_called()
