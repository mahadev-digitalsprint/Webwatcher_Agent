from dataclasses import dataclass
from typing import Any

from webwatcher.llm.llm_client import LlmClient


@dataclass
class FinancialValidationResult:
    merged_metrics: dict[str, float]
    agreement_score: float
    llm_payload: dict[str, Any] | None


class LlmFinancialValidator:
    def __init__(self, client: LlmClient) -> None:
        self.client = client

    def validate(self, text: str, deterministic: dict[str, float]) -> FinancialValidationResult:
        if not self.client.enabled():
            return FinancialValidationResult(
                merged_metrics=deterministic,
                agreement_score=0.0,
                llm_payload=None,
            )
        prompt = (
            "Extract JSON with keys revenue, net_profit, ebitda, eps when present. "
            "Return numbers only."
        )
        result = self.client.complete_json(prompt, text[:12000])
        llm_metrics = {k: float(v) for k, v in result.payload.items() if _is_number(v)}
        if not deterministic:
            return FinancialValidationResult(llm_metrics, 0.5, result.payload)
        overlap = set(deterministic).intersection(llm_metrics)
        if not overlap:
            return FinancialValidationResult(deterministic, 0.1, result.payload)
        agreements = []
        for key in overlap:
            a = deterministic[key]
            b = llm_metrics[key]
            if a == 0:
                agreements.append(0.0)
            else:
                agreements.append(max(0.0, 1 - abs(a - b) / abs(a)))
        score = sum(agreements) / len(agreements)
        merged = deterministic.copy()
        for key, value in llm_metrics.items():
            merged.setdefault(key, value)
        return FinancialValidationResult(merged, score, result.payload)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) or (isinstance(value, str) and value.replace(".", "", 1).isdigit())

