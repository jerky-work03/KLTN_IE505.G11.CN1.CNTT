"""Entrypoint hien tai chi cung cap tro giup va phien ban cua bo khung."""

from __future__ import annotations

import argparse

from . import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kltn",
        description="Research scaffold for static npm/PyPI malicious package detection.",
        epilog="The scan, train and evaluate commands are not implemented yet.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.parse_args(argv)
    parser.print_help()
    return 0
