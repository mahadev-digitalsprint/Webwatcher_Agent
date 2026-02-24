from dataclasses import dataclass

from webwatcher.core.config import get_settings
from webwatcher.db.models import Severity


@dataclass
class MaterialityResult:
    severity: str
    score: float


class MaterialityEngine:
    def __init__(self) -> None:
        settings = get_settings()
        self.minor = settings.webwatch_materiality_minor
        self.moderate = settings.webwatch_materiality_moderate
        self.significant = settings.webwatch_materiality_significant
        self.critical = settings.webwatch_materiality_critical

    def score(self, raw_score: float) -> MaterialityResult:
        score = max(0.0, min(raw_score, 1.0))
        if score >= self.critical:
            severity = Severity.critical.value
        elif score >= self.significant:
            severity = Severity.significant.value
        elif score >= self.moderate:
            severity = Severity.moderate.value
        else:
            severity = Severity.minor.value
        return MaterialityResult(severity=severity, score=score)

