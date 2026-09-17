from datetime import UTC, datetime

import pandas as pd
import yfinance as yf

from app.plugins.datasources.base import DataSourcePlugin, IngestRecord, QuotaInfo


class YFinancePlugin(DataSourcePlugin):
    source_name = "yfinance"
    source_type = "earnings"
    feature_flag = "datasource.yfinance"

    async def fetch(self, symbols: list[str], since: datetime) -> list[IngestRecord]:
        records: list[IngestRecord] = []

        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                earnings_dates = ticker.earnings_dates
                if earnings_dates is None or earnings_dates.empty:
                    continue

                for idx, row in earnings_dates.iterrows():
                    # idx is the Earnings Date which is a Timestamp
                    if pd.isna(idx):
                        continue

                    # YFinance often returns timezone aware timestamps
                    # We compare using UTC
                    try:
                        dt = idx.to_pydatetime()
                        if dt.tzinfo is not None:
                            dt = dt.astimezone(UTC)
                        else:
                            dt = dt.replace(tzinfo=UTC)
                    except Exception:
                        continue

                    if dt < since:
                        continue

                    eps_estimate = row.get("EPS Estimate")
                    reported_eps = row.get("Reported EPS")

                    eps_est_val = float(eps_estimate) if not pd.isna(eps_estimate) else None
                    reported_eps_val = float(reported_eps) if not pd.isna(reported_eps) else None

                    # Also include surprise if available
                    surprise = row.get("Surprise(%)")
                    surprise_val = float(surprise) if not pd.isna(surprise) else None

                    payload = {
                        "report_date": dt.isoformat(),
                        "estimated_eps": eps_est_val,
                        "actual_eps": reported_eps_val,
                        "surprise_percent": surprise_val,
                    }

                    raw_id = f"{symbol}_{dt.strftime('%Y%m%d')}"

                    record = IngestRecord(
                        source_name=self.source_name,
                        record_type="earnings",
                        ticker_symbols=[symbol],
                        timestamp=dt,
                        payload=payload,
                        raw_id=raw_id,
                    )
                    records.append(record)

            except Exception:
                # Silently skip on error for one symbol
                continue

        return records

    def get_quota_info(self) -> QuotaInfo | None:
        return QuotaInfo(
            source_name=self.source_name,
            daily_limit=2000,
            monthly_limit=None,
            resets_at_midnight_utc=True,
        )
