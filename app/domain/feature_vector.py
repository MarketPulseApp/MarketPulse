import math
from dataclasses import dataclass, field
from datetime import UTC, datetime

CURRENT_SCHEMA_VERSION = "1.0"


@dataclass
class FeatureVector:
    values: list[float] = field(default_factory=list)
    schema_version: str = ""
    assembled_at: datetime = datetime.now(UTC)

    def __post_init__(self) -> None:
        for v in self.values:
            if not math.isfinite(v):
                raise ValueError(f"FeatureVector contains a non-finite value: {v}")

        if self.schema_version != CURRENT_SCHEMA_VERSION:
            raise ValueError(
                f"Schema version mismatch: expected {CURRENT_SCHEMA_VERSION}, "
                f"got {self.schema_version}"
            )
