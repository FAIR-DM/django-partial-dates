# django-partial-dates Constitution

The rules every change to this repository follows. The words in it are defined in
[`CONTEXT.md`](CONTEXT.md).

## Core articles

### Article I — Testing
Every change follows [`docs/contributing/standards/testing.md`](docs/contributing/standards/testing.md): what gets a test
and what does not, the test-first cycle, test structure and fixtures, and the coverage floors.

### Article II — Simplicity
Start with the simplest design that satisfies the spec. New dependencies, new abstractions,
and new infrastructure each require a stated justification in the plan or the pull request.
YAGNI over speculation.

### Article III — Anti-Abstraction
No wrapper layers, base classes, or "future-proofing" indirection without a present, concrete
second use. Prefer duplication over the wrong abstraction.

### Article IV — Integration-First
Contracts and integration points are designed and tested before internals are polished.
Acceptance scenarios exercise the system the way users touch it.

### Article V — Security & data-safety
Values interpolated into rendered output are escaped through the framework's template layer,
never hand-built string interpolation of model or user data. Secrets live in runtime config,
never in code, fixtures, or version control. Authentication, authorisation, cryptography and
permission changes never take a shortened review path.

### Article VI — Documentation
Public API changes ship their docs in the same PR: README + CHANGELOG updated. Docstrings,
component annotations and code comments follow
[`docs/contributing/standards/code-documentation.md`](docs/contributing/standards/code-documentation.md). The pages under
`docs/` and the README's quickstart follow
[`docs/contributing/standards/documentation.md`](docs/contributing/standards/documentation.md). If the repo ships
built docs, they must build clean. The README follows the package README standard, including its badge row and a *Scope &
philosophy* section.

### Article VII — Dependency discipline
A new runtime dependency requires a stated justification (Simplicity applied to the dependency
tree; prefer the shared `mvp-shared` toolchain bundle over ad-hoc dev deps). `deptry` must pass:
no unused, missing, or transitively-relied-upon dependencies.

### Article VIII — Internationalization
User-facing strings are translatable. In Python (models, forms, views, admin, template tags,
validators) they are wrapped with `gettext_lazy` (imported as `_`); templates load
`{% load i18n %}` and wrap strings with `{% trans %}` / `{% blocktrans %}`. Model `verbose_name`
/ `verbose_name_plural` and form `label` / `help_text` / `error_messages` use `gettext_lazy`; pure
acronyms are exempt. A package ships a base English (`en`) catalog and a `locale/` directory so
host projects can compile or extend translations. CI runs `makemessages` clean over the source as
the i18n gate; correct wrapper usage is otherwise enforced by review, and a hard-coded user-visible
string in a PR is a blocking comment. A package with no user-facing strings satisfies this
trivially.

### Article IX — Data-model conventions (Django)
Every model field is a deliberate indexing decision. Because consumers of a published package cannot
add their own indexes, any field with a plausible lookup / filter / ordering path is indexed at its
definition (`db_index`, `unique`, an FK's automatic index, or a composite `Meta.constraints` /
`Meta.indexes`); a field with no query path stays unindexed to avoid write cost. The choice —
indexed or not, and why — is recorded (plan `data-model.md` or `decisions.md`). `verbose_name` and
`help_text` are mandatory on every model field (Article VIII). **Migrations are consolidated per
PR:** the migrations a feature branch introduces are squashed into as few files as possible before
the PR is submitted (branch-local and unapplied, so safe at any release stage); data migrations
(`RunPython`/`RunSQL`) are exempt from auto-regeneration — keep them via `squashmigrations` or
standalone.

### Article X — Cohesion (Python)
Related behaviour is grouped in a class, not scattered across module-level functions.

**The test:** two or more module-level functions that share a *subject* belong on a class. They
share a subject when they operate on the same data, take the same first argument, are only
meaningful in sequence, or are named around the same noun (`build_x`, `validate_x`, `render_x`).

**Why this is a standard and not a taste.** In a published package, a class is the extension
point. A consumer who needs different behaviour subclasses it and overrides one method. A module
of functions can only be monkey-patched, which is not a supported interface and breaks on any
internal change. Grouping also gives the behaviour a name, a place for shared configuration, and
one import instead of six.

**Shape:** shared state or configuration → a regular class holding it. Grouping for namespacing
with no shared state → still a class, with `@classmethod`/`@staticmethod`, or a small frozen
dataclass carrying the config. Expose a module-level convenience function only as a thin wrapper
over the class, never as the implementation.

**Django first.** Where the framework already owns the grouping, use it rather than inventing a
class: a `QuerySet`/`Manager` method instead of a function taking a queryset, a model method or
property instead of a function taking an instance, a `Form`/`Serializer` method instead of a free
validation function, a `TemplateView` method instead of a helper called by a view.

**Django standards.** Where code lives in a Django codebase, and when a new abstraction is worth
adding, is set out in [`docs/contributing/standards/django.md`](docs/contributing/standards/django.md).

**Exceptions — narrow, and stated rather than assumed.** A genuinely standalone pure function with
no siblings. Framework-dictated module shapes: `conftest.py` fixtures, migrations, `urls.py`,
`apps.py`, decorator-registered template tags and filters, signal receivers, management-command
entry points. Factory functions that return the class. A module of independent utilities that
genuinely share no subject.

**This does not license abstraction.** Article III still holds: one class grouping today's
behaviour is the goal, not a base class, a registry, or a hierarchy built for a second
implementation that does not exist. Grouping related functions is organisation; adding a layer
between the caller and the work is not.

## Project articles

### Article XI — Storage
A partial date is stored as its ISO form (`YYYY`, `YYYY-MM` or `YYYY-MM-DD`) in one text column
with byte-order (`C`) collation, as [ADR 0001](docs/adr/0001-store-partial-dates-as-iso-8601-strings.md)
records. No change adds a companion column or asks a model to declare one, writes a part that was
not recorded, or stores a value through a `date` or `datetime` column. Derived values, such as a
partial date's start and end, are computed when they are read, never stored.

### Article XII — Every filter states its uncertain matches
Every lookup and filter this package provides documents which uncertain matches it includes. Its
tests cover a value at each precision on both sides of each boundary, so `1990`, `1990-06` and
`1990-06-14` are each tested against a bound of `1990-06`. A lookup is added only when it runs
in the database and works on every supported database.

### Article XIII — Compatibility and stack
- Python 3.12 and later. Django 5.2 LTS and the current stable release.
- PostgreSQL and SQLite are the supported databases.
- Managed with uv, built with hatchling, released through the Prepare Release workflow.
- The stored ISO form is a data contract independent of the package version. A release that
  changes how values are stored ships the migration that converts existing data.
- Before 1.0.0, a minor release may change the Python API. From 1.0.0 the Python API follows
  semantic versioning, with a deprecation lasting one minor release before removal.

## Quality bar

Read at plan and review. It applies to every change.
- Test coverage meets the floors in `docs/contributing/standards/testing.md`, set in `codecov.yml`.
- Every public API change updates README + CHANGELOG in the same PR.
- Lint, type-check (`mypy`), and `deptry` pass.

The package also builds and its metadata is valid. The README renders on the package index, so
its links are absolute URLs. The public API honours the deprecation policy.

## Non-negotiables

- Tests, build and lint pass before a change merges. Nobody overrides a red check.
- The default branch requires one approval, and the author of a change never approves it.

---

**Version**: 1.0.0 | **Ratified**: 2026-10-29 | **Last Amended**: 2026-10-29
