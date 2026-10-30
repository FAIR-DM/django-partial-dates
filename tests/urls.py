import django_filters
from django.contrib import admin
from django.urls import path
from django_filters.views import FilterView

from partial_dates.filters import PartialDateFilter, PartialDateRangeFilter
from tests.models import Sample


class SampleFilter(django_filters.FilterSet):
    collected = PartialDateFilter()
    when = PartialDateRangeFilter(field_name="collected")

    class Meta:
        model = Sample
        fields = []


class SampleFilterView(FilterView):
    queryset = Sample.objects.order_by("pk")
    filterset_class = SampleFilter
    template_name = "tests/sample_filter.html"
    strict = False


urlpatterns = [
    path("admin/", admin.site.urls),
    path("samples/", SampleFilterView.as_view(), name="sample-filter"),
]
