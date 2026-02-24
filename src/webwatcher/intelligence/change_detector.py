from dataclasses import dataclass
from typing import Any

from webwatcher.db.models import ChangeType


@dataclass
class ChangeDetectionResult:
    change_type: str
    summary: str
    details: dict[str, Any]
    score: float


class ChangeDetector:
    def detect(
        self,
        old_snapshot: dict[str, Any] | None,
        new_snapshot: dict[str, Any],
        old_financial: dict[str, float] | None,
        new_financial: dict[str, float],
        pdf_changed: bool,
    ) -> ChangeDetectionResult:
        if old_financial and new_financial:
            delta = self._financial_delta(old_financial, new_financial)
            if delta["max_change"] > 0.02:
                return ChangeDetectionResult(
                    change_type=ChangeType.financial.value,
                    summary="Financial metrics changed",
                    details=delta,
                    score=min(1.0, delta["max_change"]),
                )
        if pdf_changed:
            return ChangeDetectionResult(
                change_type=ChangeType.document.value,
                summary="Document update detected",
                details={"pdf_changed": True},
                score=0.6,
            )
        old_hash = (old_snapshot or {}).get("page_hash")
        new_hash = new_snapshot.get("page_hash")
        if old_hash != new_hash:
            return ChangeDetectionResult(
                change_type=ChangeType.text.value,
                summary="Textual content changed",
                details={"old_hash": old_hash, "new_hash": new_hash},
                score=0.35,
            )
        return ChangeDetectionResult(
            change_type=ChangeType.text.value,
            summary="No meaningful change",
            details={},
            score=0.0,
        )

    def _financial_delta(self, old: dict[str, float], new: dict[str, float]) -> dict[str, Any]:
        deltas: dict[str, float] = {}
        max_change = 0.0
        for key, new_value in new.items():
            old_value = old.get(key)
            if old_value is None or old_value == 0:
                continue
            change = abs(new_value - old_value) / abs(old_value)
            deltas[key] = change
            max_change = max(max_change, change)
        return {"deltas": deltas, "max_change": max_change}

