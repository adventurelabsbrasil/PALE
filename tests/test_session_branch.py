from pathlib import Path


ROOT = Path(__file__).parents[1]
MODULE = ROOT / "src/acoustic_lab/web/experiment2/session_branch.js"


def test_session_branch_module_declares_reversible_contract():
    source = MODULE.read_text(encoding="utf-8")
    assert 'SESSION_VERSION = "pale-session-v1"' in source
    for intervention in ("solo", "mute", "select", "seek", "freeze", "create"):
        assert f'"{intervention}"' in source
    assert "serializeSession" in source
    assert "importSession" in source
    assert "replayInterventions" in source


def test_session_events_have_deterministic_ids_and_ordering():
    source = MODULE.read_text(encoding="utf-8")
    assert 'id: `user-${String(sequence).padStart(6, "0")}`' in source
    assert "sort((a, b) => a.sequence - b.sequence)" in source
