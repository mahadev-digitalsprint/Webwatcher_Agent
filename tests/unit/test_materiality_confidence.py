from webwatcher.intelligence.confidence_engine import ConfidenceEngine
from webwatcher.intelligence.materiality_engine import MaterialityEngine


def test_materiality_thresholds() -> None:
    engine = MaterialityEngine()
    assert engine.score(0.1).severity == "Minor"
    assert engine.score(0.45).severity in {"Moderate", "Significant", "Critical"}


def test_confidence_snapshot_score_range() -> None:
    result = ConfidenceEngine().score(
        has_tables=True,
        heading_match_ratio=0.8,
        unit_consistency=0.9,
        llm_agreement=0.7,
        metrics={"revenue": 100.0},
    )
    assert 0.0 <= result.snapshot_confidence <= 1.0
    assert "revenue" in result.metric_confidence

