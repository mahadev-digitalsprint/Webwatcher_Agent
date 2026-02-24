from webwatcher.financial.canonical_map import canonicalize_metric_name


def test_canonical_map_handles_synonyms() -> None:
    assert canonicalize_metric_name("Net Sales") == "revenue"
    assert canonicalize_metric_name("Profit After Tax") == "net_profit"
    assert canonicalize_metric_name("EBITDA Margin") == "ebitda"
    assert canonicalize_metric_name("Unknown Label") is None

