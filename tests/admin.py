from django.contrib import admin

from tests.models import Event, Note, Record


class NoteInline(admin.TabularInline):
    model = Note
    extra = 1


@admin.register(Record)
class RecordAdmin(admin.ModelAdmin):
    inlines = [NoteInline]


admin.site.register(Event)
