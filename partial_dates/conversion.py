"""Moving a column from django-partial-date to a `PartialDateField`."""

from django.db import models
from django.db.backends.base.base import BaseDatabaseWrapper


class OldPartialDateField(models.Field):
    """A field describing the column django-partial-date created.

    Historical migrations point at this field instead of the old package's, so a
    project can uninstall that package while every database keeps the schema its
    migrations describe. It writes values through unchanged. Pass it any option of
    `django.db.models.Field`; it takes no `max_length`.
    """

    def get_internal_type(self) -> str:
        """Return the type family Django compares when it alters the column.

        Returns:
            `"CharField"`, which is deliberately not the type of the column.
        """
        # Django picks an alteration's USING clause by comparing these families. Naming
        # the text family stops an AlterField to PartialDateField casting the old
        # timestamps to varchar(10), which would truncate them silently (FS-005).
        return "CharField"

    def db_type(self, connection: BaseDatabaseWrapper) -> str | None:
        """Return the type of the old column.

        Args:
            connection: The database the column is created on.

        Returns:
            The timestamp type of the database.
        """
        return connection.data_types["DateTimeField"]

    def db_check(self, connection: BaseDatabaseWrapper) -> None:
        """Return no check, because the old column had none.

        Args:
            connection: The database the column is created on.

        Returns:
            `None`.
        """
        return None
