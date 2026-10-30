"""The filters of the example app."""

import django_filters

from partial_dates.filters import PartialDateRangeFilter
from samples.models import Sample


class SampleFilter(django_filters.FilterSet):
    """Narrow the samples to those collected within a range of dates."""

    collected = PartialDateRangeFilter()

    class Meta:
        model = Sample
        fields: list[str] = []
