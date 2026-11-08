"""Run one explicit, read-only Unitree SDK2 compatibility probe.

This example only initializes DDS, queries the RobotState API/server versions,
and reads the service list.  It does not subscribe to an unverified topic,
create a publisher, change network configuration, or issue a robot command.

Usage (supported Linux engineering host only)::

    python examples/hardware/unitree_readonly_probe.py --interface enp2s0

The interface is intentionally required.  Do not replace it with automatic
interface discovery or an environment-variable fallback.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TextIO

# Keep this example runnable directly from a source checkout without making
# the optional SDK part of the ordinary package import path.

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from robot_dog.adapters.unitree_sdk2 import (  # noqa: E402
    UnitreeSdk2Error,
    UnitreeSdk2ReadOnlyProbe,
)

ProbeFactory = Callable[..., UnitreeSdk2ReadOnlyProbe]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read-only Unitree SDK2 version and service-list probe."
    )
    parser.add_argument(
        "--interface",
        required=True,
        metavar="NAME",
        help="explicit robot-facing Linux network interface (for example enp2s0)",
    )
    parser.add_argument(
        "--domain-id",
        type=int,
        default=0,
        metavar="N",
        help="DDS domain id (default: 0)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the normalized probe result as JSON",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    stream: TextIO | None = None,
    error_stream: TextIO | None = None,
    probe_factory: ProbeFactory = UnitreeSdk2ReadOnlyProbe,
) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    output = sys.stdout if stream is None else stream
    errors = sys.stderr if error_stream is None else error_stream

    try:
        probe = probe_factory(
            network_interface=args.interface,
            domain_id=args.domain_id,
        )
        result = probe.probe()
    except UnitreeSdk2Error as exc:
        errors.write(f"unitree read-only probe unavailable: {exc}\n")
        return 2

    payload = result.to_dict()
    if args.json:
        json.dump(payload, output, indent=2, sort_keys=True)
        output.write("\n")
    else:
        output.write("Unitree SDK2 read-only probe\n")
        output.write(f"  interface:          {payload['network_interface']}\n")
        output.write(f"  DDS domain:         {payload['domain_id']}\n")
        output.write(f"  local API version:  {payload['api_version']}\n")
        output.write(f"  server API version: {payload['server_api_version']}\n")
        output.write(f"  services:           {len(payload['services'])}\n")
        for service in payload["services"]:
            output.write(
                "    {name}: status={status} protected={protected}\n".format(**service)
            )
        output.write("  read-only:          yes\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
