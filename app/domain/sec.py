from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum


class FormType(StrEnum):
    """Common SEC form types relevant to equity analysis."""

    FORM_10K = "10-K"  # Annual Report
    FORM_10Q = "10-Q"  # Quarterly Report
    FORM_8K = "8-K"  # Current report (material events)
    FORM_4 = "4"  # Insider transaction (ownership change)
    FORM_S1 = "S-1"  # IPO Registration
    FORM_DEF14A = "DEF 14A"  # Proxy Statement (executive compensation)
    FORM_SC13G = "SC 13G"  # Passive Ownership >5%
    FORM_SC13D = "SC 13D"  # Active Ownership >5% (activist)

    @classmethod
    def is_insider(cls, value: str) -> bool:
        return value in {cls.FORM_4}

    @classmethod
    def is_periodic(cls, value: str) -> bool:
        return value in {cls.FORM_10K, cls.FORM_10Q}


@dataclass
class SECFiling:
    """A single SEC EDGAR filing.

    Fields
    ------
    filing_id
        EDGAR accession number with dashes stripped, e.g. "0000320193-24-000123"
        → "0000320193-24-000123".  Used as the unique key in MongoDB.
    ticker
        Primary ticker associated with the filer (CIK → ticker lookup).
    cik
        SEC Central Index Key — the filer's unique EDGAR identifier.
    form_type
        Form type string, e.g. "10-K", "8-K", "4".
    filed_at
        UTC date the filing was accepted by EDGAR.
    period_of_report
        The period the report covers (end date). None for event-driven forms.
    content
        Full extracted text of the primary document.  May be truncated for
        very large filings (10-K can exceed 500k tokens).
    summary
        LLM-generated plain-English summary. None until processed.
    filing_url
        Direct URL to the filing index on EDGAR.
    document_url
        Direct URL to the primary HTML/text document.
    is_amendment
        True for amended filings (10-K/A, 8-K/A, etc.).
    """

    filing_id: str
    ticker: str
    cik: str
    form_type: str
    filed_at: datetime
    content: str
    period_of_report: datetime | None = None
    summary: str = ""
    filing_url: str = ""
    document_url: str = ""
    is_amendment: bool = False

    @property
    def is_summarised(self) -> bool:
        return bool(self.summary)

    @property
    def is_insider_filing(self) -> bool:
        return FormType.is_insider(self.form_type)

    @property
    def is_periodic_report(self) -> bool:
        return FormType.is_periodic(self.form_type)

    @property
    def word_count(self) -> int:
        return len(self.content.split())

    def truncated_content(self, max_tokens: int = 8000) -> str:
        """Return content truncated to approximately *max_tokens* words.

        Used when passing filing content to an LLM with a context limit.
        A rough approximation: 1 token = 0.75 words
        """
        max_words = int(max_tokens * 0.75)
        words = self.content.split()
        if len(words) <= max_words:
            return self.content
        return " ".join(words[:max_words]) + "\n\n[TRUNCATED]"

    def to_mongo_doc(self) -> dict:
        return {
            "filing_id": self.filing_id,
            "ticker": self.ticker,
            "cik": self.cik,
            "form_type": self.form_type,
            "filed_at": self.filed_at,
            "period_of_report": self.period_of_report,
            "content": self.content,
            "summary": self.summary,
            "filing_url": self.filing_url,
            "document_url": self.document_url,
            "is_amendment": self.is_amendment,
        }

    @classmethod
    def from_mongo_doc(cls, doc: dict) -> SECFiling:
        doc = {k: v for k, v in doc.items() if k != "_id"}
        return cls(**doc)

    @classmethod
    def from_edgar_api(cls, data: dict, content: str) -> SECFiling:
        """Construct from a parsed EDGAR full-text search API response.

        The EDGAR full-text search API (efts.sec.gov) return JSON with
        a slightly different field naming convention than the filing index.

        Usage:
            import httpx
            resp = httpx.get("https://efts.sec.gov/LATEST/search-index?q=...")
            for hit in resp.json()["hits"]["hits"]
                filing = SECFiling.from_edgar_api(hit["_source"], content=text)
        """
        return cls(
            filing_id=data.get("file_num", data.get("accession_no", "")),
            ticker=data.get("ticker", ""),
            cik=str(data.get("entity_id", "")),
            form_type=data.get("form_type", ""),
            filed_at=(
                datetime.fromisoformat(data["file_date"])
                if "file_date" in data
                else datetime.now(UTC)
            ),
            content=content,
            filing_url=data.get("file_url", ""),
            document_url=data.get("document_url", ""),
        )
