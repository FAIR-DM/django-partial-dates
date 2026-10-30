"""The model field that stores a partial date."""

from collections.abc import Sequence
from typing import Any

from django.core.exceptions import ValidationError
from django.db import models
from django.db.backends.base.base import BaseDatabaseWrapper
from django.utils.translation import gettext_lazy as _

from partial_dates.lookups import Day, Month, Start, Year
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
        default_error_messages: The `invalid` message, shown for text that is not a
            partial date.

    Raises:
        TypeError: If `max_length` is passed.
    """

    description = _("A date known to the year, the month or the day")
    empty_strings_allowed = False
    default_error_messages = {
        "invalid": _(
            "\u201c%(value)s\u201d is not a date as YYYY, YYYY-MM or YYYY-MM-DD."
        ),
    }

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

    def db_check(self, connection: BaseDatabaseWrapper) -> str:
        """Build the column check that refuses text that is not a partial date.

        Args:
            connection: The database the column is created on.

        Returns:
            SQL, true for `NULL` and for `YYYY`, `YYYY-MM` and `YYYY-MM-DD` naming a
            real date, and false for any other text. On SQLite it also refuses text
            holding a NUL character.
        """
        column = connection.ops.quote_name(self.db_column or self.attname)

        def digits(*positions: int) -> str:
            return " AND ".join(
                f"SUBSTR({column}, {position}, 1) BETWEEN '0' AND '9'"
                for position in positions
            )

        year = f"CAST(SUBSTR({column}, 1, 4) AS INTEGER)"
        month = f"CAST(SUBSTR({column}, 6, 2) AS INTEGER)"
        day = f"CAST(SUBSTR({column}, 9, 2) AS INTEGER)"
        leap = (
            f"(({year} - ({year} / 4) * 4 = 0 AND {year} - ({year} / 100) * 100 <> 0)"
            f" OR {year} - ({year} / 400) * 400 = 0)"
        )
        days = (
            f"CASE WHEN {month} = 2 THEN CASE WHEN {leap} THEN 29 ELSE 28 END "
            f"WHEN {month} IN (4, 6, 9, 11) THEN 30 ELSE 31 END"
        )
        year_set = f"SUBSTR({column}, 1, 4) <> '0000'"
        sql = (
            f"{column} IS NULL OR CASE "
            f"WHEN LENGTH({column}) = 4 AND {digits(1, 2, 3, 4)} THEN {year_set} "
            f"WHEN LENGTH({column}) = 7 AND {digits(1, 2, 3, 4, 6, 7)} "
            f"AND SUBSTR({column}, 5, 1) = '-' "
            f"THEN {year_set} AND {month} BETWEEN 1 AND 12 "
            f"WHEN LENGTH({column}) = 10 AND {digits(1, 2, 3, 4, 6, 7, 9, 10)} "
            f"AND SUBSTR({column}, 5, 1) = '-' AND SUBSTR({column}, 8, 1) = '-' "
            f"THEN {year_set} AND {month} BETWEEN 1 AND 12 "
            f"AND {day} BETWEEN 1 AND ({days}) "
            f"ELSE FALSE END"
        )
        if connection.vendor == "sqlite":
            sql = f"({sql}) AND LENGTH(CAST({column} AS BLOB)) = LENGTH({column})"
        # Django's SQLite introspection splits the table's SQL on ", " and fails on a
        # check that contains one.
        return sql.replace(", ", ",")

    def from_db_value(
        self, value: str | None, expression: Any, connection: BaseDatabaseWrapper
    ) -> PartialDate | None:
        """Read the stored text as a partial date.

        Args:
            value: The stored text, or `None`.
            expression: The expression the value was selected by.
            connection: The database the value came from.

        Returns:
            `None`, or the partial date the text records.
        """
        return None if value is None else PartialDate.fromisoformat(value)

    def to_python(self, value: Any) -> PartialDate | None:
        """Turn a value into a partial date.

        Args:
            value: A `PartialDate`, its ISO text, `""` or `None`.

        Returns:
            `None` for `None` and `""`, otherwise the partial date the value names.

        Raises:
            ValidationError: With code `invalid`, if the value is not a partial date.
        """
        if value is None or value == "":
            return None
        if isinstance(value, PartialDate):
            return value
        try:
            return PartialDate.fromisoformat(value)
        except ValueError:
            raise ValidationError(
                self.error_messages["invalid"],
                code="invalid",
                params={"value": value},
            ) from None

    def get_prep_value(self, value: Any) -> str | None:
        """Turn a value into the text stored in the column.

        A value that is not a partial date makes `PartialDate.fromisoformat` raise
        `ValueError`, before any query runs.

        Args:
            value: A `PartialDate`, its ISO text, `""` or `None`.

        Returns:
            `None` for `None` and `""`, otherwise the ISO form of the value.
        """
        value = super().get_prep_value(value)
        if value is None or value == "":
            return None
        if isinstance(value, PartialDate):
            return value.isoformat()
        return PartialDate.fromisoformat(value).isoformat()

    # Django types the result as str, but its serialisers write None as null.
    def value_to_string(self, obj: models.Model) -> str | None:  # type: ignore[override]
        """Write the field's value for a serialiser.

        Args:
            obj: The instance whose value is written.

        Returns:
            `None` for an empty value, otherwise the ISO form of the value, also when
            the instance still holds unvalidated text.
        """
        return self.get_prep_value(self.value_from_object(obj))


PartialDateField.register_lookup(Year)
PartialDateField.register_lookup(Month)
PartialDateField.register_lookup(Day)
PartialDateField.register_lookup(Start)
