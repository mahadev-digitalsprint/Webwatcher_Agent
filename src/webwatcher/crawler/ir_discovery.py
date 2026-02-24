from dataclasses import dataclass
from urllib.parse import urlparse

from webwatcher.crawler.crawler_controller import CrawlerController

KEYWORDS = {
    "investor": 0.4,
    "relations": 0.3,
    "financial": 0.2,
    "results": 0.2,
    "annual": 0.1,
    "quarterly": 0.1,
}


@dataclass
class IRDiscoveryResult:
    ir_url: str | None
    confidence: float
    candidates: list[str]


class IRDiscovery:
    def __init__(self, crawler_controller: CrawlerController) -> None:
        self.crawler_controller = crawler_controller

    async def discover(self, company_url: str) -> IRDiscoveryResult:
        pages = await self.crawler_controller.crawl_targeted(company_url)
        scored: list[tuple[float, str]] = []
        for page in pages:
            path = urlparse(page).path.lower()
            score = 0.0
            for keyword, weight in KEYWORDS.items():
                if keyword in path:
                    score += weight
            if score > 0:
                scored.append((min(score, 1.0), page))
        scored.sort(key=lambda item: item[0], reverse=True)
        if not scored:
            return IRDiscoveryResult(ir_url=None, confidence=0.0, candidates=pages)
        confidence, ir_url = scored[0]
        return IRDiscoveryResult(ir_url=ir_url, confidence=confidence, candidates=pages)

