import re
from dataclasses import dataclass
from io import BytesIO

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional dependency
    PdfReader = None


@dataclass
class ParsedPdf:
    text: str
    report_type: str | None
    headings: list[str]


REPORT_PATTERNS = {
    "annual_report": re.compile(r"\bannual report\b", re.IGNORECASE),
    "quarterly_results": re.compile(r"\bquarter(?:ly)? results?\b", re.IGNORECASE),
    "investor_presentation": re.compile(r"\binvestor presentation\b", re.IGNORECASE),
}


class PdfParser:
    def parse(self, pdf_bytes: bytes) -> ParsedPdf:
        text = ""
        if PdfReader is not None:
            reader = PdfReader(BytesIO(pdf_bytes))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        report_type = None
        for name, pattern in REPORT_PATTERNS.items():
            if pattern.search(text):
                report_type = name
                break
        headings = [line.strip() for line in text.splitlines() if len(line.strip()) > 10][:25]
        return ParsedPdf(text=text, report_type=report_type, headings=headings)

