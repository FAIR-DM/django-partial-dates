"""The admin mixin that shows a partial date as its display form."""

from collections.abc import Callable, Iterable
from functools import cached_property
from typing import Any, cast

from django.contrib import admin
from django.contrib.admin.options import BaseModelAdmin, InlineModelAdmin
from django.contrib.admin.utils import flatten_fieldsets
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
                value = field.to_python(getattr(obj, field.name))
                if value is None:
                    return str(self.get_empty_value_display())
                return value.display_form()

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

    def whole_object_read_only(self, request: HttpRequest, obj: Any = None) -> bool:
        """Say whether the user can only read this object.

        An inline is read-only for a user who may not add to it and may not change
        both the parent and the inline. The parent is asked through the admin site.

        Args:
            request: The current request.
            obj: The object being shown, or `None` on the add page.

        Returns:
            `True` when every partial date field on the page is read-only.
        """
        if obj is None:
            return False
        if not isinstance(self, InlineModelAdmin):
            return not self.has_change_permission(request, obj)
        if self.has_add_permission(request, obj):
            return False
        parent = self.admin_site.get_model_admin(self.parent_model)
        return not (
            parent.has_change_permission(request, obj)
            and self.has_change_permission(request, obj)
        )

    def read_only_names(self, request: HttpRequest, obj: Any = None) -> set[str]:
        """Name the partial date fields that are read-only for this request.

        Args:
            request: The current request.
            obj: The object being shown, or `None` on the add page.

        Returns:
            Every partial date field when the whole object is read-only, and
            otherwise the names in the admin's own `readonly_fields`.
        """
        if self.whole_object_read_only(request, obj):
            return set(self.partial_fields())
        return {
            name
            for name in super().get_readonly_fields(request, obj)
            if isinstance(name, str)
        }

    def get_readonly_fields(self, request: HttpRequest, obj: Any = None) -> list[Any]:
        """Show a read-only partial date field as its display form.

        Args:
            request: The current request.
            obj: The object being shown, or `None` on the add page.

        Returns:
            The read-only fields, with each partial date field replaced by its
            display callable. Nothing is added to what Django already lists.
        """
        return self.substitute(
            self.read_only_names(request, obj),
            super().get_readonly_fields(request, obj),
        )

    def get_fields(self, request: HttpRequest, obj: Any = None) -> list[Any]:
        """Put the display callable of a read-only field where the field was.

        Args:
            request: The current request.
            obj: The object being shown, or `None` on the add page.

        Returns:
            The fields of the form, with each read-only partial date field shown once.
        """
        names = self.read_only_names(request, obj)
        return list(
            dict.fromkeys(self.substitute(names, super().get_fields(request, obj)))
        )

    def get_fieldsets(self, request: HttpRequest, obj: Any = None) -> list[Any]:
        """Substitute the read-only partial date fields in each fieldset.

        Args:
            request: The current request.
            obj: The object being shown, or `None` on the add page.

        Returns:
            The fieldsets, with each read-only partial date field replaced by its
            display callable.
        """
        names = self.read_only_names(request, obj)
        return [
            (title, {**options, "fields": self.substitute(names, options["fields"])})
            for title, options in super().get_fieldsets(request, obj)
        ]

    def get_form(
        self,
        request: HttpRequest,
        obj: Any = None,
        change: bool = False,
        **kwargs: Any,
    ) -> Any:
        """Leave a read-only field the form declares out of the form.

        Django removes such a field by its name, which a display callable no longer
        matches, and the form would then ask for a value the page does not offer.

        Args:
            request: The current request.
            obj: The object being shown, or `None` on the add page.
            change: Whether this is the change page.
            **kwargs: Keyword arguments for the form factory.

        Returns:
            The form class.
        """
        declared = self.read_only_names(request, obj) & set(self.form.declared_fields)
        if declared:
            kwargs["form"] = type(
                self.form.__name__, (self.form,), dict.fromkeys(declared)
            )
        parent = cast(Any, super())
        return parent.get_form(request, obj, change, **kwargs)

    def get_formset(self, request: HttpRequest, obj: Any = None, **kwargs: Any) -> Any:
        """Build an inline's formset from the field names alone.

        Django leaves a callable out of a form on a change page, but an inline's
        formset does not, so only the names that are strings are passed on.

        Args:
            request: The current request.
            obj: The parent object being shown, or `None` on the add page.
            **kwargs: Keyword arguments for the formset factory.

        Returns:
            The formset class.
        """
        if "fields" not in kwargs:
            kwargs["fields"] = [
                name
                for name in flatten_fieldsets(self.get_fieldsets(request, obj))
                if isinstance(name, str)
            ]
        parent = cast(Any, super())
        return parent.get_formset(request, obj, **kwargs)
