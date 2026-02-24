import re
from dataclasses import dataclass

from webwatcher.financial.canonical_map import canonicalize_metric_name
from webwatcher.financial.unit_normalizer import normalize_numeric_value

LINE_RE = re.compile(
    r"(?P<label>[A-Za-z ()/-]{3,})[:\-]?\s*(?P<currency>INR|USD|EUR|Rs\.?|₹|\$|€)?\s*"
    r"(?P<value>\d[\d,]*(?:\.\d+)?)\s*(?P<unit>Cr|Crore|Mn|Million|Bn|Billion)?",
    re.IGNORECASE,
)
PERIOD_RE = re.compile(r"\b(Q[1-4]\s*FY\d{2,4}|FY\d{2,4}|quarter ended)\b", re.IGNORECASE)
REPORT_RE = re.compile(r"\b(consolidated|standalone)\b", re.IGNORECASE)


@dataclass
class ExtractedFinancial:
    metrics: dict[str, float]
    currency: str | None
    quarter: str | None
    report_type: str | None


class FinancialExtractor:
    def extract(self, text: str) -> ExtractedFinancial:
        metrics: dict[str, float] = {}
        currency: str | None = None
        for line in text.splitlines():
            match = LINE_RE.search(line)
            if not match:
                continue
            canonical = canonicalize_metric_name(match.group("label"))
            if not canonical:
                continue
            raw_value = float(match.group("value").replace(",", ""))
            parsed_currency = match.group("currency")
            if parsed_currency and not currency:
                currency = parsed_currency.replace("Rs.", "INR").replace("₹", "INR")
            normalized = normalize_numeric_value(raw_value, match.group("unit"), currency)
            metrics[canonical] = normalized.base_value

        period_match = PERIOD_RE.search(text)
        report_match = REPORT_RE.search(text)
        return ExtractedFinancial(
            metrics=metrics,
            currency=currency,
            quarter=period_match.group(1) if period_match else None,
            report_type=report_match.group(1).lower() if report_match else None,
        )

