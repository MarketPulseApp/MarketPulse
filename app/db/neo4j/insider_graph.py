from __future__ import annotations

from datetime import datetime

from neo4j import AsyncDriver


class InsiderGraphRepository:
    """Model insider trading relationships in Neo4j.

    Node labels:   Person, Ticker
    Relationships: TRADED   (Person)-[:TRADED {type, amount, date}]->(Ticker)
                   WORKS_AT (Person)-[:WORKS_AT {role}]->(Ticker)

    Each TRADED relationship is a distinct event, so we use CREATE (not MERGE)
    for those — each transaction should appear as a separate edge.

    WORKS_AT is an affiliation (one per person per company), so we MERGE it.
    """

    def __init__(self, driver: AsyncDriver, database: str = "neo4j") -> None:
        self.driver = driver
        self.database = database

    async def add_person(
        self,
        person_id: str,
        name: str,
        title: str | None = None,
    ) -> None:
        """Create or update a Person node."""
        async with self.driver.session(database=self.database) as session:
            await session.run(
                """
                MERGE (p:Person {person_id: $person_id})
                SET p.name  = $name,
                    p.title = $title
                """,
                person_id=person_id,
                name=name,
                title=title,
            )

    async def add_affiliation(
        self,
        person_id: str,
        symbol: str,
        role: str,
    ) -> None:
        """Link a Person to a Ticker company with an employment role."""
        async with self.driver.session(database=self.database) as session:
            await session.run(
                """
                MERGE (p:Person {person_id: $person_id})
                MERGE (t:Ticker {symbol: $symbol})
                MERGE (p)-[w:WORKS_AT]->(t)
                SET w.role = $role
                """,
                person_id=person_id,
                symbol=symbol,
                role=role,
            )

    async def add_transaction(
        self,
        person_id: str,
        symbol: str,
        transaction_type: str,
        shares: float,
        price_per_share: float,
        filed_at: datetime | None = None,
    ) -> None:
        """Record an insider trade as a new TRADED relationship.

        We use CREATE (not MERGE) here because each filing is a distinct
        transaction — you want every trade to appear as a separate edge.
        """
        async with self.driver.session(database=self.database) as session:
            await session.run(
                """
                MERGE (p:Person {person_id: $person_id})
                MERGE (t:Ticker {symbol: $symbol})
                CREATE (p)-[:TRADED {
                    type:             $transaction_type,
                    shares:           $shares,
                    price_per_share:  $price_per_share,
                    filed_at:         $filed_at,
                    date:             date()
                }]->(t)
                """,
                person_id=person_id,
                symbol=symbol,
                transaction_type=transaction_type,
                shares=shares,
                price_per_share=price_per_share,
                filed_at=filed_at or datetime.utcnow(),
            )

    async def get_insider_activity(
        self,
        symbol: str,
        transaction_type: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        """Return recent insider trades for a ticker."""
        type_filter = "AND rel.type = $transaction_type" if transaction_type else ""
        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                f"""
                MATCH (p:Person)-[rel:TRADED]->(t:Ticker {{symbol: $symbol}})
                WHERE 1=1 {type_filter}
                RETURN p.name          AS name,
                       p.title         AS title,
                       rel.type        AS type,
                       rel.shares      AS shares,
                       rel.price_per_share AS price_per_share,
                       rel.filed_at    AS filed_at
                ORDER BY rel.filed_at DESC
                LIMIT $limit
                """,
                symbol=symbol,
                transaction_type=transaction_type,
                limit=limit,
            )
            return await result.data()

    async def get_connected_insiders(self, symbol_a: str, symbol_b: str) -> list[dict]:
        """Find people who have traded at BOTH companies — a shared-insider signal."""
        async with self.driver.session(database=self.database) as session:
            result = await session.run(
                """
                MATCH (p:Person)-[:TRADED]->(a:Ticker {symbol: $sym_a}),
                      (p)-[:TRADED]->(b:Ticker {symbol: $sym_b})
                RETURN p.person_id AS person_id, p.name AS name, p.title AS title
                """,
                sym_a=symbol_a,
                sym_b=symbol_b,
            )
            return await result.data()
