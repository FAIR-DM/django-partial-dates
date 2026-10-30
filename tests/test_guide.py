import ast
import doctest
import re
import textwrap
from pathlib import Path

import django_filters
import pytest

from partial_dates import PartialDate
from partial_dates.filters import PartialDateFilter, PartialDateRangeFilter
from tests.factories import SampleFactory
from tests.models import Event, Note, Record, Sample

ROOT = Path(__file__).parent.parent
GUIDE = ROOT / "docs" / "developer" / "querying.md"
MOVING_GUIDE = ROOT / "docs" / "developer" / "moving-from-django-partial-date.md"
FORMS_GUIDE = GUIDE.parent / "forms.md"
FILTERING_GUIDE = GUIDE.parent / "filtering.md"
SHOWING_GUIDE = GUIDE.parent / "showing.md"
VALUES_GUIDE = GUIDE.parent / "values.md"
STORING_GUIDE = GUIDE.parent / "storing.md"
FENCED_PYTHON = re.compile(r"^```python\n(.*?)^```", re.DOTALL | re.MULTILINE)
LISTED_ROWS = re.compile(r"^for text in (\[.*?\]):$", re.DOTALL | re.MULTILINE)
GUIDE_BLOCK = re.compile(
    r"^(?P<indent> *)```python(?P<info>[^\n]*)\n(?P<code>.*?)^(?P=indent)```",
    re.DOTALL | re.MULTILINE,
)
FILE_NAME = re.compile(r'title="(?P<path>[^"]+)"')
BEFORE_STATE = "before-state"
NO_DATE = "no date"


class TestExamples:
    def test_every_example_in_the_guide_runs_and_prints_what_it_shows(
        self, guide_samples
    ):
        blocks = FENCED_PYTHON.findall(GUIDE.read_text())
        parser = doctest.DocTestParser()
        test = parser.get_doctest(
            "\n".join(blocks),
            {"Sample": Sample, "PartialDate": PartialDate},
            "querying",
            str(GUIDE),
            0,
        )
        runner = doctest.DocTestRunner(
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.IGNORE_EXCEPTION_DETAIL
        )
        report = []

        results = runner.run(test, out=report.append, clear_globs=False)

        assert results.attempted > 0
        assert results.failed == 0, "".join(report)

    def test_the_rows_the_guide_lists_are_the_rows_its_examples_run_against(
        self, guide_samples
    ):
        listed = ast.literal_eval(LISTED_ROWS.search(GUIDE.read_text()).group(1))

        assert listed == [sample.collected for sample in guide_samples]


class TestFormsExamples:
    def test_every_example_on_the_forms_page_runs_and_prints_what_it_shows(self):
        blocks = FENCED_PYTHON.findall(FORMS_GUIDE.read_text())
        parser = doctest.DocTestParser()
        test = parser.get_doctest(
            "\n".join(blocks), {"Record": Record}, "forms", str(FORMS_GUIDE), 0
        )
        runner = doctest.DocTestRunner(
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.IGNORE_EXCEPTION_DETAIL
        )
        report = []

        results = runner.run(test, out=report.append, clear_globs=False)

        assert results.attempted > 0
        assert results.failed == 0, "".join(report)


class TestShowingExamples:
    def test_every_example_on_the_showing_page_runs_and_prints_what_it_shows(self):
        blocks = FENCED_PYTHON.findall(SHOWING_GUIDE.read_text())
        parser = doctest.DocTestParser()
        test = parser.get_doctest(
            "\n".join(blocks), {}, "showing", str(SHOWING_GUIDE), 0
        )
        runner = doctest.DocTestRunner(
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.IGNORE_EXCEPTION_DETAIL
        )
        report = []

        results = runner.run(test, out=report.append, clear_globs=False)

        assert results.attempted > 0
        assert results.failed == 0, "".join(report)


class TestValuesExamples:
    def test_every_example_on_the_values_page_runs_and_prints_what_it_shows(self):
        blocks = FENCED_PYTHON.findall(VALUES_GUIDE.read_text())
        parser = doctest.DocTestParser()
        test = parser.get_doctest("\n".join(blocks), {}, "values", str(VALUES_GUIDE), 0)
        runner = doctest.DocTestRunner(
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.IGNORE_EXCEPTION_DETAIL
        )
        report = []

        results = runner.run(test, out=report.append, clear_globs=False)

        assert results.attempted > 0
        assert results.failed == 0, "".join(report)


@pytest.mark.django_db
class TestStoringExamples:
    def test_every_example_on_the_storing_page_runs_and_prints_what_it_shows(self):
        blocks = FENCED_PYTHON.findall(STORING_GUIDE.read_text())
        parser = doctest.DocTestParser()
        test = parser.get_doctest(
            "\n".join(blocks), {"Sample": Sample}, "storing", str(STORING_GUIDE), 0
        )
        runner = doctest.DocTestRunner(
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.IGNORE_EXCEPTION_DETAIL
        )
        report = []

        results = runner.run(test, out=report.append, clear_globs=False)

        assert results.attempted > 0
        assert results.failed == 0, "".join(report)


def parse_tables(text):
    tables, current = [], []
    for line in text.splitlines():
        if line.startswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not set("".join(cells)) <= set("-: "):
                current.append(cells)
        elif current:
            tables.append(current)
            current = []
    if current:
        tables.append(current)
    return tables


def unquote(cell):
    return cell.strip("`")


def stated_results():
    cases = []
    for table in parse_tables(GUIDE.read_text()):
        header = [unquote(cell) for cell in table[0]]
        if "Row" not in header:
            continue
        for cells in table[1:]:
            row = dict(zip(header, [unquote(cell) for cell in cells], strict=True))
            for column in header:
                if row[column] not in ("yes", "no"):
                    continue
                if "=" in column:
                    key, value = column.split("=")
                    lookup = {f"collected__{key}": ast.literal_eval(value)}
                else:
                    lookup = {f"collected__{column}": row["Bound"]}
                cases.append(
                    pytest.param(
                        row["Row"],
                        lookup,
                        row[column] == "yes",
                        id=f"{row.get('Bound', '')}-{row['Row']}-{column}",
                    )
                )
    return cases


class TestStatedResults:
    def test_the_guide_states_results(self):
        assert stated_results()

    @pytest.mark.django_db
    @pytest.mark.parametrize(("row", "lookup", "stated"), stated_results())
    def test_each_stated_result_is_what_the_filter_returns(
        self, guide_samples, row, lookup, stated
    ):
        text = None if row == NO_DATE else row

        found = [
            sample.collected and str(sample.collected)
            for sample in Sample.objects.filter(**lookup)
        ]

        assert (text in found) is stated


def listed_filtering_rows():
    return ast.literal_eval(LISTED_ROWS.search(FILTERING_GUIDE.read_text()).group(1))


def optional(cell):
    return None if cell == "-" else cell


def filtering_cases():
    cases = []
    for table in parse_tables(FILTERING_GUIDE.read_text()):
        header = [unquote(cell) for cell in table[0]]
        if "Row" not in header:
            continue
        for cells in table[1:]:
            row = dict(zip(header, [unquote(cell) for cell in cells], strict=True))
            if "After" in row:
                data = {
                    f"collected_{side.lower()}": optional(row[side])
                    for side in ("After", "Before")
                    if optional(row[side])
                }
                cases.append(
                    pytest.param(
                        PartialDateRangeFilter,
                        {},
                        data,
                        row["Row"],
                        row["Found"] == "yes",
                        id=f"{row['After']}-{row['Before']}-{row['Row']}",
                    )
                )
            elif "Lookup" in row:
                cases.append(
                    pytest.param(
                        PartialDateFilter,
                        {"lookup_expr": row["Lookup"]},
                        {"collected": row["Entry"]},
                        row["Row"],
                        row["Found"] == "yes",
                        id=f"{row['Lookup']}-{row['Entry']}-{row['Row']}",
                    )
                )
            else:
                for column in header:
                    if row[column] in ("yes", "no"):
                        cases.append(
                            pytest.param(
                                PartialDateFilter,
                                {"lookup_expr": column},
                                {"collected": row["Bound"]},
                                row["Row"],
                                row[column] == "yes",
                                id=f"{row['Bound']}-{row['Row']}-{column}",
                            )
                        )
    return cases


class TestFilteringExamples:
    @pytest.fixture
    def rows(self, db):
        return [SampleFactory(collected=text) for text in listed_filtering_rows()]

    def test_every_example_on_the_page_runs_and_prints_what_it_shows(self, rows):
        blocks = FENCED_PYTHON.findall(FILTERING_GUIDE.read_text())
        parser = doctest.DocTestParser()
        names = {"Sample": Sample, "Record": Record, "Note": Note}
        test = parser.get_doctest(
            "\n".join(blocks), names, "filtering", str(FILTERING_GUIDE), 0
        )
        runner = doctest.DocTestRunner(
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.IGNORE_EXCEPTION_DETAIL
        )
        report = []

        results = runner.run(test, out=report.append, clear_globs=False)

        assert results.attempted > 0
        assert results.failed == 0, "".join(report)

    def test_the_page_lists_a_row_holding_no_date(self):
        assert None in listed_filtering_rows()

    def test_the_page_states_results(self):
        assert filtering_cases()

    @pytest.mark.parametrize(
        ("filter_class", "options", "data", "row", "stated"), filtering_cases()
    )
    def test_each_stated_result_is_what_the_filter_finds(
        self, rows, filter_class, options, data, row, stated
    ):
        meta = type("Meta", (), {"model": Sample, "fields": []})
        filters = {"collected": filter_class(field_name="collected", **options)}
        built = type(
            "GuideFilter", (django_filters.FilterSet,), {"Meta": meta, **filters}
        )

        applied = built(data, queryset=Sample.objects.all())

        assert applied.is_valid()
        found = [sample.collected and str(sample.collected) for sample in applied.qs]
        text = None if row == NO_DATE else row
        assert (text in found) is stated


def moving_blocks():
    return [
        (match["info"].strip(), textwrap.dedent(match["code"]))
        for match in GUIDE_BLOCK.finditer(MOVING_GUIDE.read_text())
    ]


class TestMovingGuide:
    def test_every_end_state_block_equals_the_file_it_names(self):
        named = [
            (FILE_NAME.search(info)["path"], code)
            for info, code in moving_blocks()
            if FILE_NAME.search(info)
        ]

        assert "tests/moving/migrations/0004_convert_dates.py" in [
            path for path, _ in named
        ]
        for path, code in named:
            assert code == (ROOT / path).read_text(), path

    def test_every_other_block_runs_unless_it_shows_the_state_before_the_move(self):
        runnable = [
            code
            for info, code in moving_blocks()
            if not FILE_NAME.search(info) and info != BEFORE_STATE
        ]

        assert runnable
        for code in runnable:
            exec(compile(code, str(MOVING_GUIDE), "exec"), {})  # noqa: S102


REST_FRAMEWORK_GUIDE = GUIDE.parent / "rest-framework.md"


class TestRestFrameworkExamples:
    @pytest.mark.django_db
    def test_every_example_on_the_page_runs_and_prints_what_it_shows(self):
        blocks = FENCED_PYTHON.findall(REST_FRAMEWORK_GUIDE.read_text())
        parser = doctest.DocTestParser()
        names = {"Sample": Sample, "Event": Event}
        test = parser.get_doctest(
            "\n".join(blocks), names, "rest-framework", str(REST_FRAMEWORK_GUIDE), 0
        )
        runner = doctest.DocTestRunner(
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.IGNORE_EXCEPTION_DETAIL
        )
        report = []

        results = runner.run(test, out=report.append, clear_globs=False)

        assert results.attempted > 0
        assert results.failed == 0, "".join(report)
