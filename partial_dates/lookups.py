"""The lookups on a partial date column: the recorded year, month and day."""

from django.db.models import IntegerField, Transform


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
