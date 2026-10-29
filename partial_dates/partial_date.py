"""The partial date value and its precision."""

import datetime
import enum
import re
from dataclasses import dataclass
from typing import Self

ISO_FORM = re.compile(r"([0-9]{4})(?:-([0-9]{2})(?:-([0-9]{2}))?)?")


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

    @classmethod
    def fromisoformat(cls, text: str) -> Self:
        """Read a partial date from its ISO form.

        Only ``YYYY``, ``YYYY-MM`` and ``YYYY-MM-DD`` are accepted, in ASCII digits
        and with no surrounding whitespace.

        Args:
            text: The ISO form to read.

        Returns:
            The partial date the text records.

        Raises:
            ValueError: The text is not a string, is not one of the three forms, or
                names a date that does not exist.
        """
        match = ISO_FORM.fullmatch(text) if isinstance(text, str) else None
        if match is None:
            raise ValueError(f"Not a partial date in ISO form: {text!r}")
        year, month, day = match.groups()
        return cls(
            int(year),
            None if month is None else int(month),
            None if day is None else int(day),
        )

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

    def isoformat(self) -> str:
        """Return the ISO form of the date, at the precision it was recorded.

        Returns:
            ``YYYY``, ``YYYY-MM`` or ``YYYY-MM-DD``, zero-padded.
        """
        text = f"{self.year:04d}"
        if self.month is not None:
            text += f"-{self.month:02d}"
        if self.day is not None:
            text += f"-{self.day:02d}"
        return text

    def __str__(self) -> str:
        """Return the ISO form of the date."""
        return self.isoformat()

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
