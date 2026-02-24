from collections import deque
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from webwatcher.crawler.fetcher import Fetcher
from webwatcher.normalization.url_utils import normalize_url, same_domain

IR_PATH_HINTS = (
    "investor",
    "investors",
    "results",
    "financial",
    "annual-report",
    "quarterly",
    "earnings",
)


class CrawlerController:
    def __init__(self, fetcher: Fetcher, max_depth: int = 2, max_pages: int = 50) -> None:
        self.fetcher = fetcher
        self.max_depth = max_depth
        self.max_pages = max_pages

    async def crawl_targeted(self, root_url: str) -> list[str]:
        root = normalize_url(root_url)
        domain = urlparse(root).netloc.lower()
        queue = deque([(root, 0)])
        visited: set[str] = set()
        discovered: list[str] = []

        while queue and len(discovered) < self.max_pages:
            url, depth = queue.popleft()
            if url in visited or depth > self.max_depth:
                continue
            visited.add(url)
            try:
                response = await self.fetcher.get(url)
            except Exception:
                continue
            if response.status_code >= 400:
                continue
            discovered.append(url)
            if depth == self.max_depth:
                continue

            soup = BeautifulSoup(response.text, "lxml")
            for anchor in soup.find_all("a"):
                href = (anchor.get("href") or "").strip()
                if not href:
                    continue
                candidate = normalize_url(href, base_url=url)
                if not same_domain(candidate, root):
                    continue
                path = urlparse(candidate).path.lower()
                if not any(hint in path for hint in IR_PATH_HINTS) and depth > 0:
                    continue
                if urlparse(candidate).netloc.lower() != domain:
                    continue
                if candidate not in visited:
                    queue.append((candidate, depth + 1))
        return discovered
