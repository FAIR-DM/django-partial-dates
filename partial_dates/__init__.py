"""A Django model field for dates known to the year, the month or the day."""

from importlib.metadata import version

from partial_dates.partial_date import PartialDate, Precision, Relation

__version__ = version("django-partial-dates")

__all__ = ["PartialDate", "Precision", "Relation", "__version__"]
