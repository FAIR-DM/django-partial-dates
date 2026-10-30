from django.db import models

from partial_dates import PartialDateField
from tests.moving.fields import ProjectDateField


class Sighting(models.Model):
    observed = PartialDateField(
        null=True,
        blank=True,
        db_index=True,
        db_column="seen_on",
        verbose_name="observed",
        help_text="When the animal was observed.",
    )
    note = models.CharField(max_length=20, blank=True, db_default="")


class Dated(models.Model):
    taken = ProjectDateField(
        verbose_name="taken", help_text="When the survey was taken."
    )

    class Meta:
        abstract = True


class Survey(Dated):
    note = models.CharField(max_length=20, blank=True, db_default="")
