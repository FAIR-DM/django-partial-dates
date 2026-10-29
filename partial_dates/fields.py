"""The model field that stores a partial date."""

from typing import Any

from django.db import models


class PartialDateField(models.Field):
    """A model field holding a partial date in one ten-character text column.

    Args:
        *args: Positional arguments of `django.db.models.Field`.
        **kwargs: Keyword arguments of `django.db.models.Field`.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["max_length"] = 10
        super().__init__(*args, **kwargs)

    def get_internal_type(self) -> str:
        """Return the column type family.

        Returns:
            The name of the Django field whose column type this field shares.
        """
        return "CharField"
