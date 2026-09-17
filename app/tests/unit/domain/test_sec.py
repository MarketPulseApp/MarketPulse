from __future__ import annotations

from datetime import datetime

from domain.sec import FormType, SECFiling


def make_filing(**kwargs) -> SECFiling:
    defaults = dict(
        filing_id="0000320193-24-000123",
        ticker="AAPL",
        cik="0000320193",
        form_type="10-K",
        filed_at=datetime(2024, 11, 1),
        content="This is the annual report content " * 100,
    )
    defaults.update(kwargs)
    return SECFiling(**defaults)


# ── FormType ─────────────────────────────────────────────────────────────────


def test_form_type_is_insider_form4():
    assert FormType.is_insider("4") is True


def test_form_type_is_insider_rejects_10k():
    assert FormType.is_insider("10-K") is False


def test_form_type_is_periodic_10k_10q():
    assert FormType.is_periodic("10-K") is True
    assert FormType.is_periodic("10-Q") is True


def test_form_type_is_periodic_rejects_8k():
    assert FormType.is_periodic("8-K") is False


def test_form_type_str_enum():
    assert FormType.FORM_10K == "10-K"
    assert FormType.FORM_4 == "4"


# ── SECFiling properties ──────────────────────────────────────────────────────


def test_is_summarised_false_when_no_summary():
    # Real SECFiling defaults summary to "" (empty string), not None.
    # is_summarised returns False when summary is falsy (None or "").
    f = make_filing()
    assert not f.is_summarised


def test_is_summarised_false_explicit_none():
    f = make_filing(summary=None)
    assert not f.is_summarised


def test_is_summarised_true_when_set():
    assert make_filing(summary="Summary text").is_summarised is True


def test_is_insider_filing_form4():
    assert make_filing(form_type="4").is_insider_filing is True


def test_is_insider_filing_10k_false():
    assert make_filing(form_type="10-K").is_insider_filing is False


def test_is_periodic_report():
    assert make_filing(form_type="10-K").is_periodic_report is True
    assert make_filing(form_type="10-Q").is_periodic_report is True
    assert make_filing(form_type="8-K").is_periodic_report is False


def test_word_count():
    f = make_filing(content="one two three")
    assert f.word_count == 3


# ── truncated_content ─────────────────────────────────────────────────────────


def test_truncated_content_short_returns_full():
    f = make_filing(content="short content")
    assert f.truncated_content(max_tokens=8000) == "short content"


def test_truncated_content_long_is_truncated():
    words = ["word"] * 10000
    f = make_filing(content=" ".join(words))
    result = f.truncated_content(max_tokens=100)
    assert result.endswith("[TRUNCATED]")
    assert len(result.split()) < 10000


def test_truncated_content_boundary():
    # max_tokens=10 → max_words=7
    words = ["w"] * 8
    f = make_filing(content=" ".join(words))
    result = f.truncated_content(max_tokens=10)
    assert "[TRUNCATED]" in result


# ── to_mongo_doc / from_mongo_doc ─────────────────────────────────────────────


def test_to_mongo_doc_contains_expected_keys():
    doc = make_filing().to_mongo_doc()
    for key in ("filing_id", "ticker", "cik", "form_type", "filed_at", "content"):
        assert key in doc


def test_from_mongo_doc_drops_id():
    doc = make_filing().to_mongo_doc()
    doc["_id"] = "mongo-id"
    f = SECFiling.from_mongo_doc(doc)
    assert f.filing_id == "0000320193-24-000123"


def test_from_mongo_doc_roundtrip():
    original = make_filing(summary="Generated summary", is_amendment=True)
    restored = SECFiling.from_mongo_doc(original.to_mongo_doc())
    assert restored.filing_id == original.filing_id
    assert restored.summary == original.summary
    assert restored.is_amendment is True


# ── from_edgar_api ────────────────────────────────────────────────────────────


def test_from_edgar_api_basic():
    data = {
        "accession_no": "0000320193-24-000123",
        "ticker": "AAPL",
        "entity_id": 320193,
        "form_type": "10-K",
        "file_date": "2024-11-01",
        "file_url": "https://sec.gov/...",
    }
    f = SECFiling.from_edgar_api(data, content="Report content")
    assert f.ticker == "AAPL"
    assert f.form_type == "10-K"
    assert f.content == "Report content"
    assert f.filed_at == datetime(2024, 11, 1)
