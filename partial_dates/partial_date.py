"""The partial date value and its precision."""

import datetime
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

    def __post_init__(self) -> None:
        """Refuse a combination of parts that is not a date.

        Raises:
            ValueError: A part is not a whole number, a day is given without a
                month, or the parts name a date that does not exist in years 1 to
                9999.
        """
        for part in (self.year, self.month, self.day):
            if part is not None and (type(part) is not int):
                raise ValueError(f"A date part must be an int, not {part!r}")
        if self.year is None:
            raise ValueError("A partial date needs a year")
        if self.month is None and self.day is not None:
            raise ValueError("A day needs a month")
        month = 1 if self.month is None else self.month
        day = 1 if self.day is None else self.day
        try:
            datetime.date(self.year, month, day)
        except (ValueError, OverflowError) as error:
            raise ValueError(str(error)) from error

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
