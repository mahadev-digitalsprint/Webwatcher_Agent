import hashlib
import re
from dataclasses import asdict, dataclass

from bs4 import BeautifulSoup

from webwatcher.normalization.url_utils import normalize_url

_NUM_RE = re.compile(r"\b\d[\d,.\-]*\b")
_TIMESTAMP_RE = re.compile(r"\b(?:\d{1,2}[:/.-]){2,}\d{2,4}\b")


@dataclass
class NormalizedPage:
    clean_text: str
    structured_sections: list[dict[str, str]]
    pdf_links: list[str]
    numbers: list[str]
    page_hash: str
    section_hashes: dict[str, str]
    numbers_hash: str

    def as_json(self) -> dict:
        return asdict(self)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def normalize_html(html: str, source_url: str) -> NormalizedPage:
    soup = BeautifulSoup(html, "lxml")

    for tag_name in ["script", "style", "nav", "footer", "header", "noscript"]:
        for node in soup.find_all(tag_name):
            node.decompose()

    sections: list[dict[str, str]] = []
    for node in soup.find_all(["h1", "h2", "h3", "p", "li"]):
        text = " ".join(node.get_text(" ", strip=True).split())
        if not text:
            continue
        text = _TIMESTAMP_RE.sub("", text).strip()
        if len(text) < 3:
            continue
        sections.append({"type": node.name, "text": text})

    clean_text = "\n".join(item["text"] for item in sections)
    numbers = _NUM_RE.findall(clean_text)
    pdf_links: list[str] = []
    for a in soup.find_all("a"):
        href = (a.get("href") or "").strip()
        if not href:
            continue
        full = normalize_url(href, base_url=source_url)
        if full.lower().endswith(".pdf"):
            pdf_links.append(full)
    pdf_links = sorted(set(pdf_links))

    section_hashes = {
        str(index): _sha256(f"{item['type']}::{item['text']}")
        for index, item in enumerate(sections)
    }
    page_hash = _sha256(clean_text)
    numbers_hash = _sha256("|".join(numbers))

    return NormalizedPage(
        clean_text=clean_text,
        structured_sections=sections,
        pdf_links=pdf_links,
        numbers=numbers,
        page_hash=page_hash,
        section_hashes=section_hashes,
        numbers_hash=numbers_hash,
    )

