"""Sphinx settings for the package's documentation.

The site is built on fairdm-docs, which reads the site's title, version, authors and
repository from pyproject.toml and supplies the theme, its navbar, the extensions and
MyST options.
"""

from fairdm_docs.conf import *  # noqa: F403

# docs/agents/ configures tooling for automated contributors and is not part of the site.
exclude_patterns.append("agents")  # noqa: F405
