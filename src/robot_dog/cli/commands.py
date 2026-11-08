"""Command handlers for the offline-first CLI."""

from __future__ import annotations

import argparse
import sys
from typing import TextIO

from robot_dog.adapters import FakeRobotAdapter
from robot_dog.envcheck import collect_environment, doctor_exit_code, format_environment

from .output import format_capabilities, format_demo, format_status, write_json


def run_doctor(args: argparse.Namespace, *, stream: TextIO = sys.stdout) -> int:
    report = collect_environment(nic_name=args.nic)
    if args.json:
        write_json(report.to_dict(), stream)
    else:
        stream.write(format_environment(report) + "\n")
    return doctor_exit_code(report)


def run_demo(args: argparse.Namespace, *, stream: TextIO = sys.stdout) -> int:
    if args.frames < 0:
        stream.write("robot-dog demo: --frames must be non-negative\n")
        return 2

    adapter = FakeRobotAdapter()
    frames = adapter.telemetry_samples(args.frames)
    capabilities = adapter.capabilities()
    status = adapter.read_status().to_dict()
    if args.json:
        write_json(
            {
                "mode": "offline-fake",
                "read_only": True,
                "capabilities": capabilities,
                "status": status,
                "telemetry": [frame.to_dict() for frame in frames],
            },
            stream,
        )
    else:
        stream.write(format_demo(capabilities, status, frames) + "\n")
    return 0


def run_capabilities(args: argparse.Namespace, *, stream: TextIO = sys.stdout) -> int:
    capabilities = FakeRobotAdapter().capabilities()
    if args.json:
        write_json(capabilities, stream)
    else:
        stream.write(format_capabilities(capabilities) + "\n")
    return 0


def run_status(args: argparse.Namespace, *, stream: TextIO = sys.stdout) -> int:
    adapter = FakeRobotAdapter()
    status = adapter.read_status().to_dict()
    if args.json:
        write_json(status, stream)
    else:
        stream.write(format_status(status) + "\n")
    return 0


def dispatch(args: argparse.Namespace, *, stream: TextIO = sys.stdout) -> int:
    handler = getattr(args, "handler", None)
    if handler == "doctor":
        return run_doctor(args, stream=stream)
    if handler == "demo":
        return run_demo(args, stream=stream)
    if handler == "capabilities":
        return run_capabilities(args, stream=stream)
    if handler == "status":
        return run_status(args, stream=stream)
    if handler == "unitree_catalog" or (
        isinstance(handler, str) and handler.startswith("unitree_")
    ):
        # Keep the optional SDK2 profile out of the ordinary CLI import path.
        from .unitree import run_unitree

        return run_unitree(args, stream=stream)
    # The parser owns the user-facing help text.  Keeping this fallback
    # explicit makes programmatic callers safe when they pass an empty argv.
    return 0


__all__ = [
    "dispatch",
    "run_capabilities",
    "run_demo",
    "run_doctor",
    "run_status",
]
