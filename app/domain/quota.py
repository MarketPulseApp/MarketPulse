from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class QuotaStatus(Enum):
    OK = 1
    LOW = 2
    EXCEEDED = 3


@dataclass
class APIQuota:
    source_name: str
    daily_used: int = 0
    monthly_used: int = 0
    is_unlimited: bool = False
    low_threshold: int | None = 10
    daily_limit: int | None = None
    monthly_limit: int | None = None
    last_reset_daily: datetime | None = None
    last_reset_monthly: datetime | None = None
    updated_at: datetime | None = None

    def is_exceeded(self) -> bool:
        if self.is_unlimited:
            return False
        if self.daily_limit is not None:
            if self.daily_used >= self.daily_limit:
                return True

        if self.monthly_limit is not None:
            if self.monthly_used >= self.monthly_limit:
                return True

        if self.monthly_used is None and self.daily_used is None:
            raise ValueError(
                "You must set either daily_limit and daily_used or monthly_limit "
                "and monthly_used if is_unlimited is set to False - is_exceeded()"
            )

        if self.monthly_limit is None and self.daily_limit is None:
            raise ValueError(
                "You must set either daily_limit or monthly_limit "
                "if is_unlimited is set to False - is_exceeded()"
            )

        return False

    def is_low(self) -> bool:
        if self.is_unlimited:
            return False

        if self.low_threshold is None:
            raise ValueError("low_threshold cannot be None if is_unlimited is False")

        total_used: int = 0

        if self.daily_limit is not None:
            total_used = self._remaining(self.daily_used, self.daily_limit)
            if total_used <= self.low_threshold:
                return True

        if self.monthly_limit is not None:
            total_used = self._remaining(self.monthly_used, self.monthly_limit)
            if total_used <= self.low_threshold:
                return True
        if self.monthly_used is None and self.daily_used is None:
            raise ValueError(
                "You must set either daily_used or monthly_used "
                "if is_unlimited is set to False - is_low()"
            )

        if self.monthly_limit is None and self.daily_limit is None:
            raise ValueError(
                "You must set either daily_limit or monthly_limit "
                "if is_unlimited is set to False - is_low()"
            )

        return False

    def percent_used(self) -> float:
        if self.is_unlimited:
            return 0.0

        if self.daily_limit is not None:
            return (self.daily_used / self.daily_limit) * 100

        if self.monthly_limit is not None:
            return (self.monthly_used / self.monthly_limit) * 100

        if self.monthly_used is None and self.daily_used is None:
            raise ValueError(
                "You must set either and daily_used or monthly_used "
                "if is_unlimited is set to False - percent_used()"
            )

        if self.monthly_limit is None and self.daily_limit is None:
            raise ValueError(
                "You must set either daily_limit or monthly_limit "
                "if is_unlimited is set to False - percent_used()"
            )

        return 0.0

    def remaining(self) -> int | None:
        if self.is_unlimited:
            return None

        if self.monthly_used is None and self.daily_used is None:
            raise ValueError(
                "You must set either daily_limit and daily_used or monthly_limit "
                "and monthly_used if is_unlimited is set to False - remaining()"
            )

        if self.monthly_limit is None and self.daily_limit is None:
            raise ValueError(
                "You must set either daily_limit or monthly_limit "
                "if is_unlimited is set to False - remaining()"
            )

        if self.daily_limit is not None:
            return self._remaining(self.daily_used, self.daily_limit)

        if self.monthly_limit is not None:
            return self._remaining(self.monthly_used, self.monthly_limit)

        return None

    def _remaining(self, used: int, limit: int) -> int:
        return limit - used
