from webwatcher.financial.financial_extractor import FinancialExtractor
from webwatcher.intelligence.change_detector import ChangeDetector


def test_financial_metric_change_detected() -> None:
    extractor = FinancialExtractor()
    old = extractor.extract("Revenue: INR 100 Cr\nProfit After Tax: INR 10 Cr")
    new = extractor.extract("Revenue: INR 130 Cr\nProfit After Tax: INR 12 Cr")
    result = ChangeDetector().detect(
        old_snapshot={"page_hash": "a"},
        new_snapshot={"page_hash": "b"},
        old_financial=old.metrics,
        new_financial=new.metrics,
        pdf_changed=False,
    )
    assert result.change_type == "FINANCIAL"
    assert result.score >= 0.2

