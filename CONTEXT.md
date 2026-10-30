# CONTEXT.md — Ubiquitous language

The words this project uses. Every core concept is named once here, so specifications, issues and
code use the same words. Where a term has a tempting synonym, the synonym is called out.

| Term | Definition | Notes / synonyms to avoid |
|---|---|---|
| **Partial date** | A single calendar date recorded to the year, to the month or to the day. `1990`, `1990-06` and `1990-06-14` are all partial dates. | A full date is a partial date at day precision. Not a "fuzzy", "approximate" or "incomplete" date. |
| **Precision** | How much of a partial date was recorded: **year**, **month** or **day**. | Not "resolution" or "granularity". |
| **Recorded part** | A year, month or day that someone actually gave. A partial date holds only its recorded parts. | The parts it does not hold are **unknown**, never "missing" or "defaulted". |
| **ISO form** | The text a partial date is written and stored as: `YYYY`, `YYYY-MM` or `YYYY-MM-DD`. These are the three forms of EDTF level 0 (ISO 8601-2). | The only stored form. Not "string representation" or "format". |
| **Period** | The days a partial date could be. `1990` covers 1 January to 31 December 1990. A day-precision date covers one day. | Derived, never stored. Not a "range" or an "interval", which imply known ends. |
| **Start** / **end** | The first and the last day of a partial date's period, as real dates. Used where something needs a real date, such as a chart axis. | Derived, never stored. |
| **Uncertain match** | A partial date whose period is partly inside and partly outside the range a filter asks for. `1990` against "June 1990 onwards" is an uncertain match. | The documentation says, filter by filter, whether uncertain matches are included. |
| **Display form** | The text a reader sees for a partial date: the year, the month and year, or the full date, written the way the active language writes it, at the precision recorded. Worked out each time it is shown. | Not the ISO form, which is stored and never changes with language. Not "formatted" or "pretty" date. |
| **EDTF** | The Extended Date/Time Format, published as ISO 8601-2. This package covers level 0 only. | Uncertain (`1990?`) and approximate (`1990~`) dates are EDTF level 1 and out of scope. |
| **Old column** | The column django-partial-date writes: a timestamp whose seconds carry the precision, 0 for year, 1 for month and 2 for day. An empty value is `NULL`. | Not the "legacy" or "source" column. |
| **Conversion** | The migration operation, `ConvertPartialDateField`, that turns an old column into a `PartialDateField` column in place. | Not a "migration tool" or an "import". |
| **Refused value** | A value in an old column that the conversion will not convert, because it is not exactly what django-partial-date writes for a partial date. | Not an "invalid" or "bad" value. The conversion refuses it and changes nothing. |
| **Stand-in field** | `OldPartialDateField`, the field existing migrations use in place of django-partial-date's. It describes the old column, and it exists for migration history, never for a model. | Not a "compatibility field" or "shim". |
