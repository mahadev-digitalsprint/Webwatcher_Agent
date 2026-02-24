from dataclasses import dataclass


@dataclass
class ConfidenceResult:
    metric_confidence: dict[str, float]
    snapshot_confidence: float


class ConfidenceEngine:
    def score(
        self,
        has_tables: bool,
        heading_match_ratio: float,
        unit_consistency: float,
        llm_agreement: float,
        metrics: dict[str, float],
    ) -> ConfidenceResult:
        base = 0.3
        if has_tables:
            base += 0.2
        base += max(0.0, min(heading_match_ratio, 1.0)) * 0.2
        base += max(0.0, min(unit_consistency, 1.0)) * 0.2
        base += max(0.0, min(llm_agreement, 1.0)) * 0.1
        snapshot_confidence = max(0.0, min(base, 1.0))
        metric_confidence = {
            key: max(0.0, min(snapshot_confidence - 0.05, 1.0))
            for key in metrics
        }
        return ConfidenceResult(
            metric_confidence=metric_confidence,
            snapshot_confidence=snapshot_confidence,
        )

