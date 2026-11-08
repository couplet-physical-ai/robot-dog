"""Stable human and JSON output for the CLI."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any, TextIO

from robot_dog.adapters import FakeTelemetry


def write_json(value: Mapping[str, Any], stream: TextIO) -> None:
    json.dump(value, stream, indent=2, sort_keys=True)
    stream.write("\n")


def format_capabilities(capabilities: Mapping[str, Any]) -> str:
    lines = [
        "robot-dog capabilities (fake adapter)",
        "  adapter:             " + str(capabilities.get("adapter", "unknown")),
        "  robot id:            " + str(capabilities.get("robot_id", "unknown")),
        "  offline:             " + _yes_no(capabilities.get("offline")),
        "  read-only:           " + _yes_no(capabilities.get("read_only")),
        "  telemetry:           " + _yes_no(capabilities.get("telemetry")),
        "  status:              " + _yes_no(capabilities.get("status")),
        "  hardware commands:   " + _yes_no(capabilities.get("hardware_commands")),
        "  low-level commands:  " + _yes_no(capabilities.get("low_level_commands")),
        "  network access:      " + _yes_no(capabilities.get("network_access")),
        "  network mutation:    "
        + _yes_no(capabilities.get("network_configuration_mutation")),
        "  SDK required:        " + _yes_no(capabilities.get("sdk_required")),
        "  safety:              no hardware commands are available",
    ]
    return "\n".join(lines)


def format_status(status: Mapping[str, Any]) -> str:
    lines = [
        "robot-dog status (fake adapter)",
        f"  robot id:   {status.get('robot_id', 'unknown')}",
        f"  state:      {status.get('state', 'unknown')}",
        f"  connected:  {_yes_no(status.get('connected'))}",
        f"  transport:  {status.get('transport', 'unknown')}",
        f"  read-only:  {_yes_no(status.get('read_only'))}",
    ]
    return "\n".join(lines)


def format_demo(
    capabilities: Mapping[str, Any],
    status: Mapping[str, Any],
    telemetry: Iterable[FakeTelemetry],
) -> str:
    lines = [
        "robot-dog demo (deterministic fake, offline, read-only)",
        "No robot, SDK, ROS, network, or hardware command is required.",
        "",
        "Capabilities",
        f"  telemetry: {_yes_no(capabilities.get('telemetry'))}",
        f"  status: {_yes_no(capabilities.get('status'))}",
        f"  hardware commands: {_yes_no(capabilities.get('hardware_commands'))}",
        "",
        "Status",
        f"  robot id: {status.get('robot_id', 'unknown')}",
        f"  state: {status.get('state', 'unknown')}",
        f"  transport: {status.get('transport', 'unknown')}",
        "",
        "Telemetry",
    ]
    for frame in telemetry:
        lines.append(
            f"  sample {frame.sample}: battery={frame.battery_percent:.1f}% "
            f"voltage={frame.battery_voltage:.2f}V "
            f"temperature={frame.temperature_c:.1f}C "
            f"position=({frame.position_m[0]:.2f}, {frame.position_m[1]:.2f}, "
            f"{frame.position_m[2]:.2f})"
        )
    lines.extend(
        [
            "",
            "Learning note: telemetry is observed only; the fake adapter cannot "
            "command a robot.",
        ]
    )
    return "\n".join(lines)


def _yes_no(value: object) -> str:
    return "yes" if value is True else "no" if value is False else "unknown"


__all__ = [
    "format_capabilities",
    "format_demo",
    "format_status",
    "write_json",
]
