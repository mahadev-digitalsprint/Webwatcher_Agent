from webwatcher.financial.financial_extractor import FinancialExtractor


def test_financial_extractor_parses_core_metrics() -> None:
    text = """
    Consolidated quarterly results Q1 FY25
    Revenue: INR 150 Cr
    Profit After Tax: INR 20 Cr
    EBITDA: INR 30 Cr
    EPS: INR 5
    """
    extracted = FinancialExtractor().extract(text)
    assert extracted.metrics["revenue"] == 150 * 10_000_000
    assert extracted.metrics["net_profit"] == 20 * 10_000_000
    assert extracted.metrics["ebitda"] == 30 * 10_000_000
    assert extracted.metrics["eps"] == 5
    assert extracted.report_type == "consolidated"

