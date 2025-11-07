"""CLI helpers for database maintenance."""

from __future__ import annotations

import argparse

from .session import ensure_engine


def main() -> None:
    parser = argparse.ArgumentParser(description="Database utilities")
    parser.add_argument("--init", action="store_true", help="Initialize database tables")
    args = parser.parse_args()

    if args.init:
        ensure_engine(echo=True)
        print("Database initialized")


if __name__ == "__main__":
    main()
