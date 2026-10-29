# Prior art

The packages that already store partial dates in Django, why none of them is used, and what this
package must not repeat. The storage decision itself is
[ADR 0001](../adr/0001-store-partial-dates-as-iso-8601-strings.md).

## Existing packages

| Package | Last release | Storage | Why not use it |
|---|---|---|---|
| [django-partial-date](https://github.com/ktowen/django_partial_date) | January 2022 | A `DateTimeField` column, with the precision held in the seconds | Unmaintained: four open issues have had no reply for years. Carries the defects listed below. |
| [r-django-partial-date](https://github.com/RamsesMartinez/r-django-partial-date) | February 2020 | The same as django-partial-date, of which it is a fork | Unmaintained. |
| [python-edtf](https://github.com/ixc/python-edtf) | September 2026 | The EDTF string, plus four float columns the model must declare for filtering and sorting | Healthy and complete, but its Django field needs four extra columns on every model, and its documentation warns that the float conversions can be inaccurate. It is the reference if uncertain or approximate dates are ever in scope. |

### What overlaps with python-edtf, and why this package exists anyway

python-edtf covers every form this package stores, and far more. The overlap is real. This
package exists because its users need three forms, not the whole of EDTF, and because they need
them in a single database column with no companion fields to declare. A field that adds hidden
columns, or asks every model to declare four more, is more machinery than the problem needs.

## Defects in django-partial-date

Every one of these is a defect this package must not repeat.

- **Comparisons across precisions are wrong.** `__ge__` is
  `self.date >= other.date and self.precision >= other.precision`, so `1990-06` is not "greater
  than or equal to" `1991`. There is no `__lt__` or `__le__`.
- **Values are unhashable.** The class defines `__eq__` without `__hash__`, so a value cannot go in
  a set or be a dictionary key.
- **The precision setter does nothing.** It calls `date.replace(day=1)` and discards the result, so
  a value built from 17 May 1990 at year precision still holds 17 May.
- **Serialisation breaks on empty values.** The field has no `value_to_string`, so `dumpdata` and
  django-reversion cannot handle a blank one.
- **It depends on `six`**, a Python 2 compatibility library.
- **It invents a day.** `.date` on a year-precision value returns 1 January, which callers cannot
  tell from a recorded 1 January.
- **Its database lookups depend on the time zone.** The column is a timestamp. With `USE_TZ`, the
  `__year`, `__month` and `__date` lookups convert to the current time zone first, so on a site
  west of UTC a value stored as 1990 matches `__year=1989`.

## Storage options considered

| Option | Outcome |
|---|---|
| A timestamp with the precision in its seconds, as django-partial-date does | Rejected. It stores a day and a month nobody recorded, and brings the time zone into date lookups. |
| A date column and a precision column | Rejected. Django has no field spanning two columns, so it needs a hidden companion field. |
| A start date and an end date, or a PostgreSQL `daterange` | Rejected. It presents an uncertain date as a certain interval, and a `daterange` works only on PostgreSQL. |
| The ISO 8601 string in one text column | Chosen. ADR 0001 records why. |
