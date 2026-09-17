import xml.etree.ElementTree as ET
from datetime import UTC, datetime

import httpx

from app.plugins.datasources.base import DataSourcePlugin, IngestRecord, QuotaInfo


class SECEdgarPlugin(DataSourcePlugin):
    source_name = "sec_edgar"
    source_type = "insider_trading"
    feature_flag = "datasource.sec_edgar"

    async def fetch(self, symbols: list[str], since: datetime) -> list[IngestRecord]:
        records: list[IngestRecord] = []
        headers = {"User-Agent": "MarketPulse/1.0 (contact@marketpulse.app)"}

        async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
            # 1. Map symbols to CIKs
            res = await client.get("https://www.sec.gov/files/company_tickers.json")
            res.raise_for_status()
            tickers_data = res.json()

            symbol_to_cik = {}
            for item in tickers_data.values():
                symbol_to_cik[item["ticker"].upper()] = str(item["cik_str"]).zfill(10)

            for symbol in symbols:
                symbol = symbol.upper()
                cik = symbol_to_cik.get(symbol)
                if not cik:
                    continue

                # 2. Get recent submissions for this CIK
                sub_res = await client.get(f"https://data.sec.gov/submissions/CIK{cik}.json")
                if sub_res.status_code != 200:
                    continue

                filings = sub_res.json().get("filings", {}).get("recent", {})
                forms = filings.get("form", [])
                accessions = filings.get("accessionNumber", [])
                filing_dates = filings.get("filingDate", [])

                for idx, form in enumerate(forms):
                    if form != "4":
                        continue

                    filing_date_str = filing_dates[idx]
                    try:
                        filing_date = datetime.strptime(filing_date_str, "%Y-%m-%d").replace(
                            tzinfo=UTC
                        )
                    except ValueError:
                        continue

                    if filing_date < since:
                        continue

                    accession_no = accessions[idx]
                    acc_no_no_dashes = accession_no.replace("-", "")

                    # 3. Get directory listing to find XML
                    dir_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{acc_no_no_dashes}/index.json"
                    dir_res = await client.get(dir_url)
                    if dir_res.status_code != 200:
                        continue

                    xml_file = None
                    for item in dir_res.json().get("directory", {}).get("item", []):
                        if item["name"].endswith(".xml") and not item["name"].endswith("_htm.xml"):
                            xml_file = item["name"]
                            break

                    if not xml_file:
                        continue

                    # 4. Fetch the XML
                    xml_url = f"https://www.sec.gov/Archives/edgar/data/{cik.lstrip('0')}/{acc_no_no_dashes}/{xml_file}"
                    xml_res = await client.get(xml_url)
                    if xml_res.status_code != 200:
                        continue

                    try:
                        root = ET.fromstring(xml_res.content)
                    except ET.ParseError:
                        continue

                    # 5. Extract data from XML
                    reporting_owner = root.find("reportingOwner")
                    if reporting_owner is None:
                        continue

                    owner_id = reporting_owner.find("reportingOwnerId")
                    owner_name = (
                        owner_id.findtext("rptOwnerName") if owner_id is not None else "Unknown"
                    )

                    rel = reporting_owner.find("reportingOwnerRelationship")
                    title = "Unknown"
                    if rel is not None:
                        if rel.findtext("officerTitle"):
                            title = rel.findtext("officerTitle")
                        elif rel.findtext("isDirector") in ["true", "1"]:
                            title = "Director"
                        elif rel.findtext("isTenPercentOwner") in ["true", "1"]:
                            title = "10% Owner"

                    non_deriv_table = root.find("nonDerivativeTable")
                    if non_deriv_table is None:
                        continue

                    for txn_idx, txn in enumerate(
                        non_deriv_table.findall("nonDerivativeTransaction")
                    ):
                        txn_date_elem = txn.find("transactionDate")
                        txn_date_str = (
                            txn_date_elem.findtext("value") if txn_date_elem is not None else None
                        )

                        txn_coding = txn.find("transactionCoding")
                        txn_type = (
                            txn_coding.findtext("transactionCode")
                            if txn_coding is not None
                            else "Unknown"
                        )

                        txn_amounts = txn.find("transactionAmounts")
                        if txn_amounts is None:
                            continue

                        shares_elem = txn_amounts.find("transactionShares")
                        shares = (
                            float(shares_elem.findtext("value"))
                            if shares_elem is not None and shares_elem.findtext("value")
                            else 0.0
                        )

                        price_elem = txn_amounts.find("transactionPricePerShare")
                        price = (
                            float(price_elem.findtext("value"))
                            if price_elem is not None and price_elem.findtext("value")
                            else 0.0
                        )

                        txn_timestamp = (
                            datetime.strptime(txn_date_str, "%Y-%m-%d").replace(tzinfo=UTC)
                            if txn_date_str
                            else filing_date
                        )

                        payload = {
                            "insider_name": owner_name,
                            "title": title,
                            "transaction_type": txn_type,
                            "quantity": shares,
                            "price": price,
                            "accession_number": accession_no,
                        }

                        raw_id = f"{accession_no}_{txn_idx}"

                        record = IngestRecord(
                            source_name=self.source_name,
                            record_type="insider_trading",
                            ticker_symbols=[symbol],
                            timestamp=txn_timestamp,
                            payload=payload,
                            raw_id=raw_id,
                        )
                        records.append(record)

        return records

    def get_quota_info(self) -> QuotaInfo | None:
        return QuotaInfo(
            source_name=self.source_name,
            daily_limit=None,
            monthly_limit=None,
            resets_at_midnight_utc=True,
        )
