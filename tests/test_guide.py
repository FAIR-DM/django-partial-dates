import ast
import doctest
import re
from pathlib import Path

import pytest

from partial_dates import PartialDate
from tests.models import Sample

GUIDE = Path(__file__).parent.parent / "docs" / "developer" / "querying.md"
FENCED_PYTHON = re.compile(r"^```python\n(.*?)^```", re.DOTALL | re.MULTILINE)
LISTED_ROWS = re.compile(r"^for text in (\[.*?\]):$", re.DOTALL | re.MULTILINE)
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
