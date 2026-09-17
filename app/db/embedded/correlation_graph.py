from __future__ import annotations

import sqlite3

import networkx as nx

DB_PATH = "data/correlation_graph.db"


class CorrelationGraphRepository:
    """
    Ticker-pair correlation graph backed by NetworkX (in-memory) + SQLite (persistent).
    The graph is loaded from SQLite at startup and written back on every update.
    """

    def __init__(self, db_path: str = DB_PATH) -> None:
        self._db_path = db_path
        self._graph: nx.Graph = nx.Graph()
        self._init_db()
        self._load()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS correlation_edges (
                    sym_a       TEXT NOT NULL,
                    sym_b       TEXT NOT NULL,
                    correlation REAL NOT NULL,
                    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
                    PRIMARY KEY (sym_a, sym_b)
                )
                """
            )

    def _load(self) -> None:
        with self._conn() as conn:
            for row in conn.execute("SELECT sym_a, sym_b, correlation FROM correlation_edges"):
                self._graph.add_edge(row[0], row[1], correlation=row[2])

    def update_edge(self, sym_a: str, sym_b: str, correlation: float) -> None:
        """Upsert the correlation between two tickers (both in-memory and SQLite)."""
        a, b = sorted([sym_a, sym_b])  # canonical order avoids (A,B) / (B,A) duplicates
        self._graph.add_edge(a, b, correlation=correlation)
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO correlation_edges (sym_a, sym_b, correlation, updated_at)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT (sym_a, sym_b) DO UPDATE
                    SET correlation = excluded.correlation,
                        updated_at  = excluded.updated_at
                """,
                (a, b, correlation),
            )

    def get_neighbors(self, symbol: str, min_correlation: float = 0.7) -> list[str]:
        """Return symbols with an absolute correlation >= *min_correlation*."""
        if symbol not in self._graph:
            return []
        return [
            nbr
            for nbr, data in self._graph[symbol].items()
            if abs(data.get("correlation", 0.0)) >= min_correlation
        ]

    def get_graph(self) -> nx.Graph:
        """Return a copy of the full correlation graph."""
        return self._graph.copy()

    def remove_ticker(self, symbol: str) -> None:
        """Remove all edges for a ticker (e.g. when it is deactivated)."""
        if symbol not in self._graph:
            return
        self._graph.remove_node(symbol)
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM correlation_edges WHERE sym_a = ? OR sym_b = ?",
                (symbol, symbol),
            )
