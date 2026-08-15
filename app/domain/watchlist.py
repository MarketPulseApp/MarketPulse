from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class WatchListEntry:
    symbol: str
    added_at: datetime | None


@dataclass
class WatchList:
    user_id: str
    name: str
    entries: list[WatchListEntry] = field(default_factory=list)
    id: str | None = None
    description: str | None = None
    created_at: datetime | None = None

    def add_ticker(self, symbol: str, added_at: datetime | None = None) -> None:
        entry = WatchListEntry(symbol=symbol, added_at=added_at)
        self.entries.append(entry)

    def remove_ticker(self, symbol: str) -> None:
        entry = next((wle for wle in self.entries if wle.symbol == symbol), None)
        if entry is not None:
            self.entries.remove(entry)

    def contains(self, symbol: str) -> bool:
        entry = next((wle for wle in self.entries if wle.symbol == symbol), None)
        if entry is not None:
            return True
        else:
            return False
