"""The admin of the example app, which shows its partial dates as their display form."""

from django.contrib import admin

from partial_dates.admin import PartialDateDisplayMixin
from samples.models import Note, Sample


class NoteInline(PartialDateDisplayMixin, admin.TabularInline):
    """Notes on a sample, edited on the sample's own page."""

    model = Note
    extra = 1


@admin.register(Sample)
class SampleAdmin(PartialDateDisplayMixin, admin.ModelAdmin):
    """A sample with its notes, listed by when it was collected and published."""

    list_display = ["collected", "published", "catalogued"]
    readonly_fields = ["catalogued"]
    inlines = [NoteInline]
