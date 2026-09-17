from __future__ import annotations

import aiosqlite

# SpatiaLite extends SQLite with geographic types and functions.
# Install: sudo apt install libsqlite3-mod-spatialite   (Ubuntu)
#          brew install spatialite-tools                 (macOS)

CREATE_SQL = """
SELECT InitSpatialMetaData(1);
"""
CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS company_locations (
    symbol  TEXT PRIMARY KEY,
    city    TEXT,
    country TEXT,
    sector  TEXT
)
"""
ADD_GEOM = """
SELECT AddGeometryColumn('company_locations', 'geom', 4326, 'POINT', 'XY')
"""
CREATE_IDX = """
SELECT CreateSpatialIndex('company_locations', 'geom')
"""


async def _open(db_path: str) -> aiosqlite.Connection:
    """Open connection and load the SpatiaLite extension."""
    conn = await aiosqlite.connect(db_path)
    await conn.enable_load_extension(True)
    await conn.load_extension("mod_spatialite")
    return conn


class CompanyGeoRepository:
    """Store company HQ coordinates using SpatiaLite.

    Coordinates are stored as WGS-84 POINT geometries (SRID 4326).
    SpatiaLite uses (longitude, latitude) order — the reverse of the
    common (lat, lon) convention used in most web APIs.
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    async def initialize(self) -> None:
        """Create tables, geometry column, and spatial index. Call once."""
        conn = await _open(self.db_path)
        try:
            # InitSpatialMetaData only works on a fresh database
            try:
                await conn.execute("SELECT InitSpatialMetaData(1)")
            except Exception:
                pass  # already initialised
            await conn.execute(CREATE_TABLE)
            try:
                await conn.execute(ADD_GEOM)
            except Exception:
                pass  # column already exists
            try:
                await conn.execute(CREATE_IDX)
            except Exception:
                pass  # index already exists
            await conn.commit()
        finally:
            await conn.close()

    async def insert(
        self,
        symbol: str,
        lat: float,
        lon: float,
        city: str = "",
        country: str = "",
        sector: str = "",
    ) -> None:
        """Insert or replace a company location.

        MakePoint(lon, lat, srid) — note lon before lat.
        """
        conn = await _open(self.db_path)
        try:
            await conn.execute(
                """
                INSERT OR REPLACE INTO company_locations (symbol, city, country, sector, geom)
                VALUES (?, ?, ?, ?, MakePoint(?, ?, 4326))
                """,
                (symbol, city, country, sector, lon, lat),
            )
            await conn.commit()
        finally:
            await conn.close()

    async def get(self, symbol: str) -> dict | None:
        """Fetch a single company by symbol, returning lat/lon as floats."""
        conn = await _open(self.db_path)
        try:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute(
                "SELECT symbol, city, country, sector, Y(geom) AS lat, X(geom) AS lon "
                "FROM company_locations WHERE symbol = ?",
                (symbol,),
            )
            row = await cur.fetchone()
            return dict(row) if row else None
        finally:
            await conn.close()

    async def get_by_sector(self, sector: str) -> list[dict]:
        """Return all companies in a sector with their coordinates."""
        conn = await _open(self.db_path)
        try:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute(
                "SELECT symbol, city, country, sector, Y(geom) AS lat, X(geom) AS lon "
                "FROM company_locations WHERE sector = ?",
                (sector,),
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]
        finally:
            await conn.close()

    async def get_within_km(self, lat: float, lon: float, km: float) -> list[dict]:
        """Return companies within *km* kilometres of a coordinate.

        Distance(a, b, 1) uses the spheroid model (metres). Divide by 1000
        to convert to kilometres.
        """
        conn = await _open(self.db_path)
        try:
            conn.row_factory = aiosqlite.Row
            cur = await conn.execute(
                """
                SELECT symbol, city, country, sector,
                       Y(geom) AS lat, X(geom) AS lon,
                       Distance(geom, MakePoint(?, ?, 4326), 1) / 1000.0 AS distance_km
                FROM company_locations
                WHERE Distance(geom, MakePoint(?, ?, 4326), 1) / 1000.0 <= ?
                ORDER BY distance_km ASC
                """,
                (lon, lat, lon, lat, km),
            )
            rows = await cur.fetchall()
            return [dict(r) for r in rows]
        finally:
            await conn.close()
