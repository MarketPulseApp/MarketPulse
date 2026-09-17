from __future__ import annotations

from neo4j import AsyncDriver


class TickerGraphRepository:
    """Model tickers, sectors, and correlations as a Neo4j graph.

    Node labels:   Ticker, Sector
    Relationships: BELONGS_TO, CORRELATED_WITH

    Key Cypher concepts:
      - MERGE  creates a node/relationship only if it does not already exist.
        Use it for upserts (tickers, sectors, sector memberships).
      - CREATE  always creates a new instance. Use it for one-off events
        (insider trades) where you want every event as a separate edge.
      - SET     updates properties on an existing node or relationship.
    """

    def __init__(self, driver: AsyncDriver, database: str = "neo4j") -> None:
        self.driver = driver
        self.database = database

    async def create_ticker(
        self,
        symbol: str,
        name: str,
        asset_type: str = "stock",
        is_active: bool = True,
    ) -> None:
        """Create or update a Ticker node."""
        async with self.driver.session(database=self.database) as session:
            await session.run(
                """
                MERGE (t:Ticker {symbol: $symbol})
                SET t.name = $name,
                    t.asset_type = $asset_type,
                    t.is_active = $is_active
                """,
                symbol=symbol,
                name=name,
                asset_type=asset_type,
                is_active=is_active,
            )

    async def add_sector_membership(self, symbol: str, sector: str) -> None:
        """Connect a Ticker to its Sector.  Creates both nodes if absent."""
        async with self.driver.session(database=self.database) as session:
            await session.run(
                """
                MERGE (t:Ticker  {symbol: $symbol})
                MERGE (s:Sector  {name:   $sector})
                MERGE (t)-[:BELONGS_TO]->(s)
                """,
                symbol=symbol,
                sector=sector,
            )

    async def add_correlation(
        self,
        sym_a: str,
        sym_b: str,
        r: float,
        window_days: int = 90,
    ) -> None:
        """Upsert an undirected CORRELATED_WITH edge with a Pearson r value.

        The relationship is undirected (-(rel)-) because correlation is
        symmetric: corr(A,B) == corr(B,A).
        """
        async with self.driver.session(database=self.database) as session:
            await session.run(
                """
                MERGE (a:Ticker {symbol: $sym_a})
                MERGE (b:Ticker {symbol: $sym_b})
                MERGE (a)-[rel:CORRELATED_WITH]-(b)
                SET rel.r           = $r,
                    rel.window_days = $window_days,
                    rel.updated_at  = datetime()
                """,
                sym_a=sym_a,
                sym_b=sym_b,
                r=r,
                window_days=window_days,
            )

    async def get_peers(self, symbol: str) -> list[str]:
        """Return active tickers in the same sector via graph traversal.

        Pattern: (ticker) -[:BELONGS_TO]-> (sector) <-[:BELONGS_TO]- (peer)
        """
        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                """
                MATCH (t:Ticker {symbol: $symbol})-[:BELONGS_TO]->(s:Sector)
                      <-[:BELONGS_TO]-(peer:Ticker)
                WHERE peer.symbol <> $symbol
                  AND peer.is_active = true
                RETURN peer.symbol AS symbol
                """,
                symbol=symbol,
            )
            rows = await result.data()
            return [row["symbol"] for row in rows]

    async def get_correlated(
        self,
        symbol: str,
        min_r: float = 0.7,
        limit: int = 10,
    ) -> list[dict]:
        """Return tickers most correlated with *symbol* above *min_r*."""
        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                """
                MATCH (a:Ticker {symbol: $symbol})-[rel:CORRELATED_WITH]-(b:Ticker)
                WHERE rel.r >= $min_r
                RETURN b.symbol AS symbol, rel.r AS r, rel.window_days AS window_days
                ORDER BY rel.r DESC
                LIMIT $limit
                """,
                symbol=symbol,
                min_r=min_r,
                limit=limit,
            )
            return await result.data()

    async def deactivate(self, symbol: str) -> None:
        async with self.driver.session(database=self.database) as session:
            await session.run(
                "MATCH (t:Ticker {symbol: $symbol}) SET t.is_active = false",
                symbol=symbol,
            )
