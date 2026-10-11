from pathlib import Path


ROOT = Path(__file__).parents[1]
LENSES = ROOT / "src/acoustic_lab/web/experiment2/visual_lenses.js"
EXPERIENCE = ROOT / "src/acoustic_lab/web/experiment2/experiment2.js"


def test_visual_lenses_are_renderers_over_one_shared_timeline():
    source = LENSES.read_text(encoding="utf-8")
    assert 'LENS_VERSION = "pale-lens-v1"' in source
    assert 'id: "organism"' in source
    assert 'id: "constellation"' in source
    assert "renderLens" in source
    assert "features" in source
    assert "analysis" not in source


def test_experience_switches_lens_without_reanalysis_and_exposes_comparison():
    source = EXPERIENCE.read_text(encoding="utf-8")
    assert 'import { LENS_VERSION, VISUAL_LENSES, getVisualLens, renderLens }' in source
    assert "lensSelect.addEventListener" in source
    assert "drawLensComparison" in source
    assert "same" not in source.lower() or "mesma linha do tempo" in source
    assert "decodeAndAnalyze" not in source[source.index("lensSelect.addEventListener"):source.index("lensSelect.addEventListener") + 500]
