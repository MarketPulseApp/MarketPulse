import os
from datetime import UTC, datetime

import httpx

from app.plugins.datasources.base import DataSourcePlugin, IngestRecord, QuotaInfo


class FREDPlugin(DataSourcePlugin):
    source_name = "fred"
    source_type = "economic"
    feature_flag = "datasource.fred"

    async def fetch(self, symbols: list[str], since: datetime) -> list[IngestRecord]:
        api_key = os.environ.get("FRED_API_KEY", "demo")
        records = []
        since_str = since.strftime("%Y-%m-%d")
        
        async with httpx.AsyncClient() as client:
            for symbol in symbols:
                if symbol == "YIELD_CURVE":
                    url = "https://api.stlouisfed.org/fred/series/observations"
                    params_10y = {"series_id": "DGS10", "api_key": api_key, "file_type": "json", "observation_start": since_str}
                    params_2y = {"series_id": "DGS2", "api_key": api_key, "file_type": "json", "observation_start": since_str}
                    
                    resp_10y = await client.get(url, params=params_10y)
                    resp_2y = await client.get(url, params=params_2y)
                    
                    resp_10y.raise_for_status()
                    resp_2y.raise_for_status()
                    
                    obs_10y = resp_10y.json().get("observations", [])
                    obs_2y = resp_2y.json().get("observations", [])
                    
                    data_10y = {o["date"]: float(o["value"]) for o in obs_10y if o["value"] != "."}
                    data_2y = {o["date"]: float(o["value"]) for o in obs_2y if o["value"] != "."}
                    
                    common_dates = set(data_10y.keys()).intersection(set(data_2y.keys()))
                    for date_str in sorted(common_dates):
                        val_10y = data_10y[date_str]
                        val_2y = data_2y[date_str]
                        slope = val_10y - val_2y
                        
                        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
                        
                        payload = {"10y": val_10y, "2y": val_2y, "slope": slope}
                        
                        records.append(IngestRecord(
                            source_name=self.source_name,
                            record_type=self.source_type,
                            ticker_symbols=["YIELD_CURVE"],
                            timestamp=dt,
                            payload=payload,
                            raw_id=f"YIELD_CURVE-{date_str}"
                        ))
                else:
                    url = "https://api.stlouisfed.org/fred/series/observations"
                    params = {"series_id": symbol, "api_key": api_key, "file_type": "json", "observation_start": since_str}
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    obs = resp.json().get("observations", [])
                    
                    for o in obs:
                        if o["value"] == ".":
                            continue
                        dt = datetime.strptime(o["date"], "%Y-%m-%d").replace(tzinfo=UTC)
                        payload = {"value": float(o["value"])}
                        records.append(IngestRecord(
                            source_name=self.source_name,
                            record_type=self.source_type,
                            ticker_symbols=[symbol],
                            timestamp=dt,
                            payload=payload,
                            raw_id=f"{symbol}-{o['date']}"
                        ))
        return records

    def get_quota_info(self) -> QuotaInfo | None:
        return QuotaInfo(
            source_name="fred",
            daily_limit=500,
            monthly_limit=None,
            resets_at_midnight_utc=True,
        )
