"""The model field that stores a partial date."""

from collections.abc import Sequence
from typing import Any

from django.db import models
from django.db.backends.base.base import BaseDatabaseWrapper
from django.utils.translation import gettext_lazy as _

from partial_dates.partial_date import PartialDate


class PartialDateField(models.Field):
    """A model field holding a partial date in one ten-character text column.

    The column is `varchar(10)`, so the field fixes its length and refuses a
    `max_length` argument.

    Args:
        *args: Positional arguments of `django.db.models.Field`.
        **kwargs: Keyword arguments of `django.db.models.Field`.

    Attributes:
        description: What the field holds, as Django shows it.
        empty_strings_allowed: `False`, so an empty value is `None`, never `""`.

    Raises:
        TypeError: If `max_length` is passed.
    """

    description = _("A date known to the year, the month or the day")
    empty_strings_allowed = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if "max_length" in kwargs:
            raise TypeError("PartialDateField fixes max_length at 10")
        kwargs["max_length"] = 10
        super().__init__(*args, **kwargs)

    def deconstruct(self) -> tuple[str, str, Sequence[Any], dict[str, Any]]:
        """Describe the field for a migration.

        Returns:
            The field's name, import path, positional and keyword arguments, without
            the fixed `max_length`, and with a `PartialDate` default as its ISO form.
        """
        name, path, args, kwargs = super().deconstruct()
        del kwargs["max_length"]
        if isinstance(kwargs.get("default"), PartialDate):
            kwargs["default"] = kwargs["default"].isoformat()
        return name, path, args, kwargs

    def get_internal_type(self) -> str:
        """Return the column type family.

        Returns:
            The name of the Django field whose column type this field shares.
        """
        return "CharField"

    def db_parameters(self, connection: BaseDatabaseWrapper) -> dict[str, Any]:
        """Add the byte-order collation on PostgreSQL.

        Args:
            connection: The database the column is created on.

        Returns:
            The column's type, check and collation.
        """
        parameters = super().db_parameters(connection)
        if connection.vendor == "postgresql":
            parameters["collation"] = "C"
        return parameters
