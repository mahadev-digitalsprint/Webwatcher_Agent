from dataclasses import dataclass

UNIT_MULTIPLIERS = {
    "cr": 10_000_000,
    "crore": 10_000_000,
    "mn": 1_000_000,
    "million": 1_000_000,
    "bn": 1_000_000_000,
    "billion": 1_000_000_000,
}


@dataclass
class NormalizedValue:
    base_value: float
    detected_unit: str | None
    currency: str | None


def normalize_numeric_value(raw_value: float, raw_unit: str | None, currency: str | None) -> NormalizedValue:
    if not raw_unit:
        return NormalizedValue(base_value=raw_value, detected_unit=None, currency=currency)
    unit_key = raw_unit.strip().lower()
    multiplier = UNIT_MULTIPLIERS.get(unit_key, 1)
    return NormalizedValue(base_value=raw_value * multiplier, detected_unit=unit_key, currency=currency)

