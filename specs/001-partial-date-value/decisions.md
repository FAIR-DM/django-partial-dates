# Decisions — FS-001: A partial date value for Python code

Decisions made while specifying, where the issue and the roadmap were silent. Each was resolved
from the goals, the constitution, the ADR and the prior-art notes, and is open to veto at review.

## The reading of the issue that the spec is written from

A developer gets one immutable value for a partial date: built from parts or read from the ISO
form, written back in the ISO form, sorted in ISO order, hashable, with the start and end of its
period as real dates and a separate answer of before, after or overlapping. It is the value alone:
the model field, lookups, forms, the migration from django-partial-date and display to a reader
are R2 to R6. It serves G2.

## Self-resolved decisions

1. **Three stories, not one or five.** Recording a value, sorting and collecting values, and asking
   when a value could have been are three things a developer sets out to do. Validation,
   immutability and the ISO form are scenarios under the first, hashing under the second, start
   and end under the third.
2. **Refused input raises Python's standard error for an invalid value, not Django's
   `ValidationError`.** The value is plain Python and the roadmap makes Django a dependency only at
   R2, with the first module that imports it. A `ValidationError` here would make Django a runtime
   dependency for a value that never touches it. The field (R2) and the form field (R4) turn the
   error into a `ValidationError` with a code, which is where the testing standard expects codes.
3. **Reading text is strict.** Only the three ISO forms, exactly. No trimming, no unpadded parts,
   no compact form, no times, no EDTF level 1. ADR 0001 accepts nothing else, and a lenient reader
   would accept values the database's check constraint (R2) refuses. Form input cleanup is R4.
4. **A partial date is never equal to a real date, a text or a number, and ordering against one is
   refused.** Equality across types would either break hashing (`a == b` with different hashes) or
   make a day-precision value interchangeable with a real date, which is the false certainty the
   package exists to avoid.
5. **The comparison has three answers: before, after and overlapping.** Two periods are always
   either nested or apart, so overlapping covers "one holds the other" and "the same". Equality is
   already `==`. "Before" is exactly FairDM's current coarser-precision `precedes()` rule, which
   SC-003 holds it to.
6. **Year is always required, and a day needs a month.** A value with no year is not a partial
   date, and `YYYY--DD` is not an ISO form.
7. **Years 0001 to 9999, proleptic Gregorian.** This is ADR 0001's range and Python's own date
   range, so start and end are always representable.
8. **Building from a real date is left out.** It is not in R1's deliverables, a real date's parts
   are one call away, and it is added when a consumer needs it.
9. **The precision is exposed.** R6's formatting and FairDM's own code branch on it, and the value
   cannot be read correctly without it.
10. **No planning notes.** The settled design direction (parts with `None`, immutable, hashable,
    ISO order, start and end, a separate comparison, ISO in and out, years 0001–9999) is all
    behaviour and is in the spec itself.
