from django.db import models
from django.utils.translation import gettext_lazy as _

from partial_dates.fields import PartialDateField
from partial_dates.partial_date import PartialDate


def default_reviewed():
    return PartialDate(2000, 3)


class Record(models.Model):
    date = PartialDateField(
        null=True,
        blank=True,
        verbose_name=_("date"),
        help_text=_("When the record happened."),
    )
    other = PartialDateField(
        null=True,
        blank=True,
        verbose_name=_("other date"),
        help_text=_("A second date on the same record."),
    )
    defaulted = PartialDateField(
        default="1990",
        verbose_name=_("defaulted date"),
        help_text=_("A date that starts as 1990."),
    )


class Event(models.Model):
    occurred = PartialDateField(
        unique=True,
        verbose_name=_("occurred"),
        help_text=_("When the event occurred. Required and unique."),
    )
    indexed = PartialDateField(
        db_index=True,
        null=True,
        blank=True,
        verbose_name=_("indexed date"),
        help_text=_("A date with a database index."),
    )


class Sample(models.Model):
    collected = PartialDateField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_("collected"),
        help_text=_("When the sample was collected."),
    )


class Note(models.Model):
    record = models.ForeignKey(Record, on_delete=models.CASCADE)
    written = models.DateField(
        null=True,
        blank=True,
        verbose_name=_("written"),
        help_text=_("The day the note was written."),
    )
    drafted = PartialDateField(
        default=PartialDate(1990, 6),
        verbose_name=_("drafted"),
        help_text=_("A date that starts as June 1990."),
    )
    reviewed = PartialDateField(
        default=default_reviewed,
        verbose_name=_("reviewed"),
        help_text=_("A date that starts as a callable gives it."),
    )
