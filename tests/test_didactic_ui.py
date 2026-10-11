from pathlib import Path


ROOT = Path(__file__).parents[1]
EXPERIENCE = ROOT / "src/acoustic_lab/web/experiment2/experiment2.js"
HTML = ROOT / "src/acoustic_lab/web/experiment2/experiment2.html"
DIDACTIC = ROOT / "src/acoustic_lab/web/experiment2/didactic.js"


def test_didactic_layer_is_optional_and_does_not_reanalyze():
    source = EXPERIENCE.read_text(encoding="utf-8")
    html = HTML.read_text(encoding="utf-8")
    didactic = DIDACTIC.read_text(encoding="utf-8")

    assert 'DIDACTIC_VERSION, explainEvent, provenanceFor' in source
    assert 'didacticToggle.addEventListener("change"' in source
    assert "didacticEnabled" in source
    assert "universo intacto" in source
    assert 'id="didacticToggle"' in html
    assert 'id="didacticPanel"' in html
    assert 'DIDACTIC_VERSION = "pale-didactic-v1"' in didactic
    assert "not_claimed" in didactic
    assert "não há rastreamento de notas ou acorde" in didactic
