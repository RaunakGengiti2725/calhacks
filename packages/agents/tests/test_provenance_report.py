"""The cascade stamps honest per-stage provenance onto the report (no network)."""

from __future__ import annotations


def test_mock_cascade_reports_mock_provenance(monkeypatch) -> None:
    monkeypatch.setenv("DRYRUN_MODE", "mock")
    from dryrun_agents.shared.cascade import run_cascade

    report = run_cascade("TTCCPSIVARSNFNVCRLPGT", "stability", 500.0, 8)
    p = report.meta.providers
    assert report.meta.mode == "mock"
    assert report.meta.strict is False
    # External stages are mock by design; the cost model is real in-process logic.
    assert p["generation"] == "mock"
    assert p["viability"] == "mock"
    assert p["structure"] == "mock"
    assert p["llm"] == "mock"
    assert p["cost"] == "local"


def test_live_without_keys_reports_fallback_not_mock(monkeypatch) -> None:
    monkeypatch.setenv("DRYRUN_MODE", "live")
    monkeypatch.delenv("DRYRUN_STRICT", raising=False)
    for k in ("ASI_ONE_API_KEY", "NVIDIA_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    from dryrun_agents.shared.cascade import run_cascade

    report = run_cascade("TTCCPSIVARSNFNVCRLPGT", "stability", 500.0, 8)
    p = report.meta.providers
    # Live was requested but no keys -> honest "fallback", never silently "live".
    assert report.meta.mode == "live"
    assert p["generation"] == "fallback"
    assert p["viability"] == "fallback"
    assert p["structure"] == "fallback"
    assert p["llm"] == "fallback"
    assert p["cost"] == "local"
