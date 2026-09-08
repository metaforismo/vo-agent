"""Command-line tools for Limes Quaestio bundles."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from quaestio.bundles import load_bundle
from quaestio.exceptions import BundleValidationError
from quaestio.report import render_markdown_report


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "research":
        from quaestio.research_cli import run
        return run(args)

    try:
        bundle = load_bundle(args.bundle)
    except (OSError, BundleValidationError) as exc:
        print(f"invalid: {exc}", file=sys.stderr)
        return 1

    if args.command == "validate":
        print(f"valid: {bundle['name']}")
        return 0
    if args.command == "inspect":
        print(render_markdown_report(bundle), end="")
        return 0

    parser.error(f"unknown command: {args.command}")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="quaestio",
        description="Durable research graphs and evidence-gated workflow bundles.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate a workflow bundle")
    validate.add_argument("bundle", help="path to a workflow bundle JSON file")

    inspect = subparsers.add_parser("inspect", help="print a markdown bundle report")
    inspect.add_argument("bundle", help="path to a workflow bundle JSON file")

    from quaestio.research_cli import configure
    configure(subparsers.add_parser("research", help="work with a durable research graph"))

    return parser


if __name__ == "__main__":
    raise SystemExit(main())
