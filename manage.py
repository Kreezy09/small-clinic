#!/usr/bin/env python
"""Django command-line entry point."""

import os
import sys

from django.core.management import execute_from_command_line


def main() -> None:
    """Run a Django management command from the command line."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.settings")
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
