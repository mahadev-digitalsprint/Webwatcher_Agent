from webwatcher.financial.unit_normalizer import normalize_numeric_value


def test_unit_normalization_for_crore() -> None:
    result = normalize_numeric_value(10, "Cr", "INR")
    assert result.base_value == 100000000
    assert result.detected_unit == "cr"
    assert result.currency == "INR"

