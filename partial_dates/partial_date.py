"""The partial date value and its precision."""

import enum
from dataclasses import dataclass


class Precision(enum.StrEnum):
    """How much of a date was recorded: the year, the month or the day.

    The members compare as their text, so they sort alphabetically. That order carries
    no meaning: it is not a ranking from coarse to fine.
    """

    YEAR = "year"
    MONTH = "month"
    DAY = "day"


@dataclass(frozen=True, slots=True)
class PartialDate:
    """A date known to the year, to the month or to the day.

    A part that was not recorded is held as ``None``, never as an invented value.

    Args:
        year: The year.
        month: The month, or ``None`` when it was not recorded.
        day: The day, or ``None`` when it was not recorded.

    Attributes:
        year: The year.
        month: The month, or ``None`` when it was not recorded.
        day: The day, or ``None`` when it was not recorded.
    """

    year: int
    month: int | None = None
    day: int | None = None

    @property
    def precision(self) -> Precision:
        """Return how much of the date was recorded.

        Returns:
            ``Precision.DAY`` when the day is known, ``Precision.MONTH`` when only the
            month is, and ``Precision.YEAR`` otherwise.
        """
        if self.day is not None:
            return Precision.DAY
        if self.month is not None:
            return Precision.MONTH
        return Precision.YEAR
