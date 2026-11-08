"""The offline-first ``robot-dog`` command line interface."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import TextIO

from .commands import dispatch
from .parser import build_parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stream: TextIO | None = None,
) -> int:
    """Run the CLI and return a process exit code.

    ``stream`` is injectable for contract tests and does not affect the
    diagnostics performed by ``doctor``.
    """

    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    output = sys.stdout if stream is None else stream
    if getattr(args, "command", None) is None:
        parser.print_help(file=output)
        return 0
    return dispatch(args, stream=output)


__all__ = ["build_parser", "main"]
