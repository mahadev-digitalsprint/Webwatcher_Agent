CANONICAL_METRIC_MAP: dict[str, str] = {
    "revenue": "revenue",
    "net sales": "revenue",
    "turnover": "revenue",
    "income from operations": "revenue",
    "net profit": "net_profit",
    "profit after tax": "net_profit",
    "pat": "net_profit",
    "ebitda": "ebitda",
    "eps": "eps",
    "earnings per share": "eps",
}


def canonicalize_metric_name(name: str) -> str | None:
    key = " ".join(name.lower().split())
    for alias, canonical in CANONICAL_METRIC_MAP.items():
        if alias in key:
            return canonical
    return None

