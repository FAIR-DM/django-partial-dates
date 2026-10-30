#!/usr/bin/env python
"""Run the example project's management commands."""

import os
import sys


def main() -> None:
    """Run the command named on the command line."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
