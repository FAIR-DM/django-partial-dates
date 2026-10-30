"""The admin mixin that shows a partial date as its display form."""

from collections.abc import Callable, Iterable
from functools import cached_property
from typing import Any, cast

from django.contrib import admin
from django.contrib.admin.options import BaseModelAdmin
from django.http import HttpRequest

from partial_dates.fields import PartialDateField


class PartialDateDisplayMixin(BaseModelAdmin):
    """Show the partial date fields of an admin class as their display form.

    Put it before `ModelAdmin` in the bases of the admin class. It reads the model
    and needs no other declaration. A column in `list_display` that names a partial
    date field shows the display form, and keeps its heading, its ordering and its
    link to the row. A field named in `list_editable` keeps its selects.
    """

    @cached_property
    def display_columns(self) -> dict[str, Callable[[Any], str]]:
        """The display callables built so far, one per field."""
        return {}

    def partial_fields(self) -> dict[str, PartialDateField]:
        """Find the partial date fields of the model.

        Returns:
            The fields by name. A name reached through a relation is never among them.
        """
        return {
            field.name: field
            for field in self.opts.concrete_fields
            if isinstance(field, PartialDateField)
        }

    def display_column(self, field: PartialDateField) -> Callable[[Any], str]:
        """Build the callable that shows one field.

        Args:
            field: The partial date field to show.

        Returns:
            A callable named after the field, with the field's verbose name as its
            heading and the field as its ordering. It gives the display form, or
            the admin's empty value display for an empty value.
        """
        if field.name not in self.display_columns:

            @admin.display(description=field.verbose_name, ordering=field.name)
            def shown(obj: Any) -> str:
                value = getattr(obj, field.name)
                if value is None:
                    return str(self.get_empty_value_display())
                return str(value.display_form())

            shown.__name__ = field.name
            self.display_columns[field.name] = shown
        return self.display_columns[field.name]

    def substitute(self, names: set[str], sequence: Iterable[Any]) -> list[Any]:
        """Replace the named partial date fields with their display callables.

        Args:
            names: The names to replace.
            sequence: Field names as an admin lists them, which may hold tuples.

        Returns:
            The sequence with each named partial date field replaced, nested tuples
            included, and everything else as it was.
        """
        fields = self.partial_fields()
        result: list[Any] = []
        for item in sequence:
            if isinstance(item, list | tuple):
                result.append(tuple(self.substitute(names, item)))
            elif isinstance(item, str) and item in names and item in fields:
                result.append(self.display_column(fields[item]))
            else:
                result.append(item)
        return result

    def listed_names(self) -> set[str]:
        """Name the partial date fields a change list shows as text.

        Returns:
            Every partial date field except those in `list_editable`.
        """
        return set(self.partial_fields()) - set(getattr(self, "list_editable", ()))

    def get_list_display(self, request: HttpRequest) -> list[Any]:
        """Show the partial date fields of the list as their display form.

        Args:
            request: The current request.

        Returns:
            The columns of the change list.
        """
        parent = cast(Any, super())
        return self.substitute(self.listed_names(), parent.get_list_display(request))

    def get_list_display_links(
        self, request: HttpRequest, list_display: Iterable[Any]
    ) -> list[Any] | None:
        """Link the display callables that stand for the fields named as links.

        Args:
            request: The current request.
            list_display: The columns of the change list.

        Returns:
            The columns that link to the row, or `None` for none.
        """
        parent = cast(Any, super())
        links = parent.get_list_display_links(request, list_display)
        if links is None:
            return None
        return self.substitute(self.listed_names(), links)
