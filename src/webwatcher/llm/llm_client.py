import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any

from openai import AzureOpenAI

from webwatcher.core.config import get_settings


@dataclass
class LlmResult:
    payload: dict[str, Any]
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_ms: int
    input_hash: str


class LlmClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.settings = settings
        self.client = None
        if settings.azure_openai_endpoint and settings.azure_openai_key:
            self.client = AzureOpenAI(
                api_key=settings.azure_openai_key,
                api_version=settings.azure_openai_api_version,
                azure_endpoint=settings.azure_openai_endpoint,
            )

    def enabled(self) -> bool:
        return self.client is not None

    def complete_json(self, system_prompt: str, user_prompt: str) -> LlmResult:
        if not self.client:
            raise RuntimeError("Azure OpenAI client is not configured.")
        content = f"{system_prompt}\n{user_prompt}"
        payload_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        start = time.perf_counter()
        response = self.client.chat.completions.create(
            model=self.settings.azure_openai_deployment,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        latency_ms = int((time.perf_counter() - start) * 1000)
        raw = response.choices[0].message.content or "{}"
        parsed = json.loads(raw)
        usage = response.usage
        return LlmResult(
            payload=parsed,
            prompt_tokens=getattr(usage, "prompt_tokens", None),
            completion_tokens=getattr(usage, "completion_tokens", None),
            latency_ms=latency_ms,
            input_hash=payload_hash,
        )

