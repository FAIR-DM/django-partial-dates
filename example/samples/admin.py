"""The admin of the example app, with no form or widget override."""

from django.contrib import admin

from samples.models import Note, Sample


class NoteInline(admin.TabularInline):
    """Notes on a sample, edited on the sample's own page."""

    model = Note
    extra = 1


@admin.register(Sample)
class SampleAdmin(admin.ModelAdmin):
    """A sample with its notes."""

    inlines = [NoteInline]
