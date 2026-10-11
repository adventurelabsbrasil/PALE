from pathlib import Path


ROOT = Path(__file__).parents[1]
HTML = ROOT / "src/acoustic_lab/web/experiment2/experiment2.html"
EXPERIENCE = ROOT / "src/acoustic_lab/web/experiment2/experiment2.js"


def test_experiment2_starts_with_balanced_world_first_hierarchy():
    source = HTML.read_text(encoding="utf-8")

    assert "Som vira mundo" in source
    assert 'id="panelToggle"' in source
    assert 'id="inspector"' in source
    assert 'data-panel-tab="understand"' in source
    assert 'data-panel-tab="investigate"' in source
    assert 'data-panel-tab="create"' in source
    assert 'id="transport"' not in source
    assert "Áudio processado localmente" in source
    assert "Three.js local · pontos sem linhas · áudio não enviado" not in source


def test_experiment2_keeps_advanced_capabilities_in_drawer_sections():
    source = HTML.read_text(encoding="utf-8")

    for element_id in ("observatoryPlot", "didacticToggle", "piano", "createEvent", "saveArtifact"):
        assert f'id="{element_id}"' in source
    assert 'id="panelUnderstand"' in source
    assert 'id="panelInvestigate"' in source
    assert 'id="panelCreate"' in source


def test_experiment2_uses_coherent_transport_feedback_and_finite_percentages():
    source = EXPERIENCE.read_text(encoding="utf-8")

    assert "const safePercent" in source
    assert "repetição detectada" in source
    assert "setFeedback" in source
    assert "renderTransportStatus" in source
    assert "analysis.frameCount ?? analysis.frame_count" in source
    assert 'playButton.textContent = "Explorar"' in source


def test_experiment2_visual_core_has_structure_and_event_layers():
    source = EXPERIENCE.read_text(encoding="utf-8")

    assert 'spectralField.add(spectrumTrails, spectrumLine, spectrumCloud, spectrumPoints)' in source
    assert "const rawImpact" in source
    assert "const silence = clamp(currentFeatures.silence)" in source
    assert "burstCloud.material.opacity" in source
    assert "pulseShell.material.opacity" in source


def test_experiment2_keeps_semantic_model_out_of_visual_dominance():
    source = EXPERIENCE.read_text(encoding="utf-8")

    assert "createPersistentForm" in source
    assert "updatePersistentForm" in source
    assert "updateRelationSignals" in source
    assert "persistent-form" in source
    assert "event-dance" in source
    assert "new THREE.IcosahedronGeometry(.12" not in source
    assert "semanticWorld.add(new THREE.Line" not in source
