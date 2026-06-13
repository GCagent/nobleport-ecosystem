from pathlib import Path

from core.gateway import operational_truth as ot
from core.gateway.config import settings


def test_matrix_internally_consistent():
    ot.validate()


def test_status_counts_total_features():
    counts = ot.summary()
    assert sum(counts.values()) == len(ot.FEATURES)
    assert set(counts) == set(ot.STATUSES)


def test_every_evidence_path_exists_in_repo():
    repo_root = Path(__file__).resolve().parents[3]
    for f in ot.FEATURES:
        target = repo_root / f.evidence
        assert target.exists(), f"{f.key} evidence missing: {f.evidence}"


def test_no_inflation_reasonable_feature_count():
    # Honest matrix — not hundreds. Guards against silent inflation.
    assert 10 <= len(ot.FEATURES) <= 60


def test_frozen_commands_include_red_scopes():
    frozen = ot.load_frozen_commands(settings.launch_gates_path)
    keys = {c["command"] for c in frozen}
    assert "nbpt_sale" in keys                     # from launch-gates RED
    assert "autonomous_payment_disbursement" in keys  # human-gate freeze
    assert len(frozen) >= 5


def test_report_shape():
    rep = ot.report(settings.launch_gates_path)
    assert rep["total_features"] == len(ot.FEATURES)
    assert "status_counts" in rep
    assert "label_definitions" in rep
    assert rep["frozen_commands"]["count"] == len(rep["frozen_commands"]["commands"])
    assert "disclaimer" in rep
