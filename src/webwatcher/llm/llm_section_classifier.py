from dataclasses import dataclass

from webwatcher.llm.llm_client import LlmClient


@dataclass
class SectionClassification:
    summary: str
    is_meaningful: bool
    confidence: float


class LlmSectionClassifier:
    def __init__(self, client: LlmClient) -> None:
        self.client = client

    def classify_diff(self, old_text: str, new_text: str) -> SectionClassification:
        if not self.client.enabled():
            return SectionClassification(summary="LLM disabled", is_meaningful=True, confidence=0.5)
        system = (
            "Classify whether a textual change is business meaningful. Return JSON: "
            "{summary, is_meaningful, confidence}."
        )
        user = f"OLD:\n{old_text[:6000]}\n\nNEW:\n{new_text[:6000]}"
        result = self.client.complete_json(system, user)
        payload = result.payload
        return SectionClassification(
            summary=str(payload.get("summary", "")),
            is_meaningful=bool(payload.get("is_meaningful", False)),
            confidence=float(payload.get("confidence", 0.0)),
        )

