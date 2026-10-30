"""The models of the example app."""

from django.db import models

from partial_dates import PartialDate, PartialDateField


class Sample(models.Model):
    """A sample, collected on a date known to the year, the month or the day."""

    collected = PartialDateField(help_text="Required. Give as much as you know.")
    published = PartialDateField(null=True, blank=True)
    catalogued = PartialDateField(default=PartialDate(1990))

    def __str__(self) -> str:
        """Name the sample by when it was collected.

        Returns:
            A short name for the sample.
        """
        return f"Sample collected {self.collected}"


class Note(models.Model):
    """A note on a sample, shown as an inline in the admin."""

    sample = models.ForeignKey(Sample, on_delete=models.CASCADE)
    written = PartialDateField(null=True, blank=True)

    def __str__(self) -> str:
        """Name the note by when it was written.

        Returns:
            A short name for the note.
        """
        return f"Note written {self.written or 'at an unknown date'}"
