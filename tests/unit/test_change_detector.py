from webwatcher.intelligence.change_detector import ChangeDetector


def test_change_detector_financial_change_priority() -> None:
    result = ChangeDetector().detect(
        old_snapshot={"page_hash": "a"},
        new_snapshot={"page_hash": "b"},
        old_financial={"revenue": 100.0},
        new_financial={"revenue": 130.0},
        pdf_changed=True,
    )
    assert result.change_type == "FINANCIAL"
    assert result.score > 0.2

