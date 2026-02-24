import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from webwatcher.core.config import get_settings
from webwatcher.crawler.fetcher import Fetcher
from webwatcher.db.models import Document
from webwatcher.pdf.pdf_parser import PdfParser
from webwatcher.security.security_utils import validate_content_type, validate_file_size
from webwatcher.storage.storage_service import StorageService


@dataclass
class PdfMonitorResult:
    downloaded: int
    changed: int
    parsed_texts: list[str]


class PdfMonitor:
    def __init__(self, fetcher: Fetcher, storage_service: StorageService, parser: PdfParser) -> None:
        self.fetcher = fetcher
        self.storage = storage_service
        self.parser = parser
        self.settings = get_settings()

    @staticmethod
    def _sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    async def _latest_doc(self, session: AsyncSession, company_id: int, url: str) -> Document | None:
        stmt = (
            select(Document)
            .where(Document.company_id == company_id, Document.url == url)
            .order_by(desc(Document.created_at))
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def process_pdf_links(
        self,
        session: AsyncSession,
        company_id: int,
        snapshot_id: int | None,
        links: list[str],
    ) -> PdfMonitorResult:
        downloaded = 0
        changed = 0
        parsed_texts: list[str] = []

        for link in links:
            try:
                head = await self.fetcher.head(link)
            except Exception:
                continue
            if not validate_content_type(head.get("content_type"), {"application/pdf"}):
                continue
            if not validate_file_size(head.get("content_length"), self.settings.webwatch_max_file_size_mb):
                continue
            response = await self.fetcher.get(link)
            if response.status_code >= 400:
                continue
            downloaded += 1

            file_hash = self._sha256(response.content)
            latest = await self._latest_doc(session, company_id, link)
            if latest and latest.doc_hash == file_hash:
                continue
            changed += 1

            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            relative = self.storage.build_path(company_id, timestamp, "document.pdf")
            storage_path = self.storage.upload("docs", relative, response.content)

            parsed = self.parser.parse(response.content)
            if parsed.text:
                parsed_texts.append(parsed.text)

            doc = Document(
                company_id=company_id,
                snapshot_id=snapshot_id,
                url=link,
                doc_hash=file_hash,
                file_size=len(response.content),
                content_type=head.get("content_type"),
                storage_path=storage_path,
            )
            session.add(doc)
        await session.flush()
        return PdfMonitorResult(downloaded=downloaded, changed=changed, parsed_texts=parsed_texts)

