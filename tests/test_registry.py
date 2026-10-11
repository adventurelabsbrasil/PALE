import pytest

from acoustic_lab.registry import format_catalog, get_experiment, list_experiments, run_registered


def test_catalog_has_stable_umbrella_entries():
    experiments = list_experiments()

    assert [item.experiment_id for item in experiments] == ["exp-001", "exp-002"]
    assert "PALE · experimentos locais" in format_catalog()
    assert "exp-001" in format_catalog()
    assert "exp-002" in format_catalog()


def test_unknown_experiment_reports_available_entries():
    with pytest.raises(ValueError, match="available: exp-001, exp-002"):
        get_experiment("exp-999")


def test_exp_002_requires_audio_before_dispatch(tmp_path):
    with pytest.raises(ValueError, match="requires --audio"):
        run_registered("exp-002", output=tmp_path / "output", serve=False)
