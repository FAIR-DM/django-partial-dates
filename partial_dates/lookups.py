"""The lookups on a partial date column: the recorded year, month and day."""

from typing import Any

from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.models import IntegerField, Transform
from django.db.models.lookups import Exact
from django.db.models.sql.compiler import SQLCompiler


class Year(Transform):
    """The recorded year of a partial date, as a whole number.

    Every partial date holds a year, so the result is empty only for a row holding
    no date.

    Attributes:
        lookup_name: `year`.
        output_field: The whole number the transform gives.
        template: SQL reading the first four characters of the stored text.
    """

    lookup_name = "year"
    output_field = IntegerField()
    template = "CAST(SUBSTR(%(expressions)s, 1, 4) AS INTEGER)"


class Month(Transform):
    """The recorded month of a partial date, as a whole number.

    The result is empty where the month was not recorded and for a row holding no
    date.

    Attributes:
        lookup_name: `month`.
        output_field: The whole number the transform gives.
        template: SQL reading characters six and seven of the stored text.
    """

    lookup_name = "month"
    output_field = IntegerField()
    template = "CAST(NULLIF(SUBSTR(%(expressions)s, 6, 2), '') AS INTEGER)"


class Day(Transform):
    """The recorded day of a partial date, as a whole number.

    The result is empty where the day was not recorded and for a row holding no date.

    Attributes:
        lookup_name: `day`.
        output_field: The whole number the transform gives.
        template: SQL reading characters nine and ten of the stored text.
    """

    lookup_name = "day"
    output_field = IntegerField()
    template = "CAST(NULLIF(SUBSTR(%(expressions)s, 9, 2), '') AS INTEGER)"


@Year.register_lookup
class YearExact(Exact):
    """Match one year by comparing the stored text, so an index on the column serves.

    A year is every stored text from `YYYY` up to `YYYY-99`. Comparing the column
    against those two bounds reads the index, which an equality on the year taken out
    of the text cannot.
    """

    def as_sql(
        self, compiler: SQLCompiler, connection: BaseDatabaseWrapper
    ) -> tuple[str, Any]:
        """Compare the column with the year's first and last possible text.

        Args:
            compiler: The compiler building the query.
            connection: The database the query runs on.

        Returns:
            SQL and its parameters. A year compared with another column or an
            expression takes Django's own comparison.
        """
        if not self.rhs_is_direct_value():
            return super().as_sql(compiler, connection)
        column, params = self.process_lhs(compiler, connection, self.lhs.lhs)
        return f"{column} BETWEEN %s AND %s", (
            *params,
            f"{self.rhs:04d}",
            f"{self.rhs:04d}-99",
        )
