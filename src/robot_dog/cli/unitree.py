"""Operator command implementation for the full Unitree Go2 surface.

This module is the CLI composition root for the optional SDK2 adapters.  It
contains no Unitree imports at module import time: catalog/help can therefore
run on an offline workstation, while each hardware operation loads only the
adapter it needs.  Tests inject :class:`AdapterFactories` and never construct
DDS clients.
"""

from __future__ import annotations

import argparse
import base64
import json
from collections.abc import Callable, Mapping
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, TextIO

Factory = Callable[..., Any]


class AdapterFactories:
    """Factories for the four optional adapter boundaries.

    Keeping these as callables is intentional.  A test can provide pure fakes,
    and production imports happen only inside the default factory functions
    when a command is actually executed.
    """

    def __init__(
        self,
        *,
        sport_client: Factory,
        authority: Factory,
        peripherals: Factory,
        low_level: Factory,
    ) -> None:
        self.sport_client = sport_client
        self.authority = authority
        self.peripherals = peripherals
        self.low_level = low_level


def sport_client_factory(**kwargs: Any) -> Any:
    from robot_dog.adapters.unitree_sdk2.high_level import Go2SportClient

    return Go2SportClient(**kwargs)


def authority_factory(**kwargs: Any) -> Any:
    from robot_dog.adapters.unitree_sdk2.authority import UnitreeSdk2Authority

    return UnitreeSdk2Authority(**kwargs)


def peripherals_factory(**kwargs: Any) -> Any:
    from robot_dog.adapters.unitree_sdk2.peripherals import UnitreeSdk2Peripherals

    return UnitreeSdk2Peripherals(**kwargs)


def low_level_factory(**kwargs: Any) -> Any:
    from robot_dog.adapters.unitree_sdk2.low_level import UnitreeGo2LowLevel

    return UnitreeGo2LowLevel(**kwargs)


DEFAULT_FACTORIES = AdapterFactories(
    sport_client=sport_client_factory,
    authority=authority_factory,
    peripherals=peripherals_factory,
    low_level=low_level_factory,
)


def _factories(value: AdapterFactories | None) -> AdapterFactories:
    return DEFAULT_FACTORIES if value is None else value


def _json_value(value: Any) -> Any:
    """Convert normalized adapter values into JSON-safe data."""

    if is_dataclass(value) and not isinstance(value, type):
        return _json_value(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, bytes):
        return {
            "encoding": "base64",
            "data": base64.b64encode(value).decode("ascii"),
        }
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


def _normalized_result(value: Any) -> Any:
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return _json_value(to_dict())
    return _json_value(value)


def _emit(
    value: Any,
    stream: TextIO,
    args: argparse.Namespace | None = None,
) -> int:
    payload = _normalized_result(value)
    if args is not None and getattr(args, "json", False):
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
    else:
        if isinstance(payload, (dict, list)):
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
        else:
            stream.write(f"{payload}\n")
    if isinstance(payload, Mapping) and payload.get("ok") is False:
        return 1
    return 0


def _emit_error(stream: TextIO, exc: Exception) -> int:
    message = str(exc) or type(exc).__name__
    if isinstance(exc, (ImportError, ModuleNotFoundError)):
        message += (
            "; install the pinned Linux Unitree SDK2 and CycloneDDS optional "
            "profile, then verify the robot-facing interface and DDS domain"
        )
    elif isinstance(exc, OSError):
        message += "; verify Linux DDS dependencies, interface name, and robot link"
    stream.write(f"robot-dog unitree: {message}\n")
    return 2


def _action_name(args: argparse.Namespace) -> str:
    positional = getattr(args, "action", None)
    option = getattr(args, "action_option", None)
    if positional and option and positional != option:
        raise ValueError("positional action and --action disagree")
    selected = option or positional
    if not isinstance(selected, str) or not selected.strip():
        raise ValueError("a SportClient action name is required")
    return selected


def _parse_json(text: str, *, label: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be valid JSON: {exc.msg}") from exc


def _sport_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "network_interface": args.interface,
        "domain_id": args.domain_id,
        "hardware_enabled": args.hardware_enabled,
        "operator_acknowledged": args.operator_acknowledged,
        "hazardous_motion_acknowledged": getattr(
            args, "hazardous_motion_acknowledged", False
        ),
        "enable_lease": getattr(args, "enable_lease", False),
    }
    timeout = getattr(args, "timeout_seconds", None)
    if timeout is not None:
        kwargs["timeout_seconds"] = timeout
    return kwargs


def _authority_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "network_interface": args.interface,
        "domain_id": args.domain_id,
        "hardware_enabled": args.hardware_enabled,
        "operator_acknowledged": getattr(args, "operator_acknowledged", False),
    }


def _peripheral_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return _authority_kwargs(args)


def _close(adapter: Any) -> None:
    close = getattr(adapter, "close", None)
    if callable(close):
        close()


def run_catalog(args: argparse.Namespace, stream: TextIO) -> int:
    # The adapter module itself is import-safe; this is still a local import so
    # the CLI composition root never imports an optional profile for help.
    from robot_dog.adapters.unitree_sdk2.high_level import command_catalog

    entries = [
        {
            "name": spec.name,
            "parameters": list(spec.parameters),
            "hazardous": spec.hazardous,
            "requires_hazardous_acknowledgement": (
                spec.requires_hazardous_acknowledgement
            ),
        }
        for spec in command_catalog()
    ]
    if args.json:
        json.dump(entries, stream, indent=2, sort_keys=True)
        stream.write("\n")
    else:
        stream.write("Unitree Go2 SportClient command catalog\n")
        for entry in entries:
            suffix = " [hazardous acknowledgement]" if entry["hazardous"] else ""
            parameters = ", ".join(entry["parameters"])
            stream.write(f"  {entry['name']}({parameters}){suffix}\n")
    return 0


def run_sport_invoke(
    args: argparse.Namespace, stream: TextIO, factories: AdapterFactories
) -> int:
    action = _action_name(args)
    positional = _parse_json(args.positional_args, label="--args")
    keyword = _parse_json(args.keyword_args, label="--kwargs")
    if not isinstance(positional, list):
        raise ValueError("--args must be a JSON array")
    if not isinstance(keyword, dict):
        raise ValueError("--kwargs must be a JSON object")
    adapter = factories.sport_client(**_sport_kwargs(args))
    try:
        result = adapter.invoke(
            action,
            *positional,
            intentional=args.intentional,
            hazardous_motion_acknowledged=args.hazardous_motion_acknowledged,
            **keyword,
        )
        return _emit(result, stream, args)
    finally:
        _close(adapter)


def run_bounded_move(
    args: argparse.Namespace, stream: TextIO, factories: AdapterFactories
) -> int:
    adapter = factories.sport_client(**_sport_kwargs(args))
    try:
        result = adapter.run_bounded_move(
            args.vx,
            args.vy,
            args.vyaw,
            duration_seconds=args.duration_seconds,
            session_id=args.session_id,
            deadman_timeout_seconds=args.deadman_timeout_seconds,
            refresh_period_seconds=args.refresh_period_seconds,
        )
        return _emit(result, stream, args)
    finally:
        _close(adapter)


def run_service_list(
    args: argparse.Namespace, stream: TextIO, factories: AdapterFactories
) -> int:
    adapter = factories.authority(**_authority_kwargs(args))
    try:
        return _emit(adapter.read_service_list(hardware_enabled=True), stream, args)
    finally:
        _close(adapter)


def run_service_switch(
    args: argparse.Namespace, stream: TextIO, factories: AdapterFactories
) -> int:
    adapter = factories.authority(**_authority_kwargs(args))
    try:
        result = adapter.switch_service(
            args.name,
            args.enabled,
            hardware_enabled=True,
            operator_acknowledged=True,
            target_id=args.target_id,
            confirm=args.confirm,
        )
        return _emit(result, stream, args)
    finally:
        _close(adapter)


def run_report_frequency(
    args: argparse.Namespace, stream: TextIO, factories: AdapterFactories
) -> int:
    adapter = factories.authority(**_authority_kwargs(args))
    try:
        return _emit(
            adapter.set_report_frequency(
                args.interval,
                args.duration,
                hardware_enabled=True,
                operator_acknowledged=True,
            ),
            stream,
            args,
        )
    finally:
        _close(adapter)


def run_motion_check(
    args: argparse.Namespace, stream: TextIO, factories: AdapterFactories
) -> int:
    adapter = factories.authority(**_authority_kwargs(args))
    try:
        return _emit(adapter.check_mode(hardware_enabled=True), stream, args)
    finally:
        _close(adapter)


def run_motion_select(
    args: argparse.Namespace, stream: TextIO, factories: AdapterFactories
) -> int:
    adapter = factories.authority(**_authority_kwargs(args))
    try:
        return _emit(
            adapter.select_mode(
                args.mode,
                hardware_enabled=True,
                operator_acknowledged=True,
                target_id=args.target_id,
                confirm=args.confirm,
            ),
            stream,
            args,
        )
    finally:
        _close(adapter)


def run_motion_release(
    args: argparse.Namespace, stream: TextIO, factories: AdapterFactories
) -> int:
    adapter = factories.authority(**_authority_kwargs(args))
    try:
        return _emit(
            adapter.release_mode(
                hardware_enabled=True,
                operator_acknowledged=True,
                target_id=args.target_id,
                confirm=args.confirm,
            ),
            stream,
            args,
        )
    finally:
        _close(adapter)


def run_video_capture(
    args: argparse.Namespace, stream: TextIO, factories: AdapterFactories
) -> int:
    adapter = factories.peripherals(**_peripheral_kwargs(args))
    try:
        result = adapter.video.get_image_sample(hardware_enabled=True)
        payload = _normalized_result(result)
        value = getattr(result, "value", None)
        if not isinstance(value, (bytes, bytearray, memoryview)):
            raise ValueError("VideoClient returned no binary image sample")
        output = Path(args.output)
        output.write_bytes(bytes(value))
        metadata = {
            "code": payload.get("code") if isinstance(payload, Mapping) else None,
            "ok": payload.get("ok") if isinstance(payload, Mapping) else True,
            "operation": "video_capture",
            "output": str(output),
            "bytes": len(value),
        }
        return _emit(metadata, stream, args)
    finally:
        _close(adapter)


def _vui_value(field: str, text: str) -> Any:
    if field == "switch":
        if text.lower() not in {"true", "false"}:
            raise ValueError("VUI switch value must be true or false")
        return text.lower() == "true"
    try:
        return int(text)
    except ValueError as exc:
        raise ValueError(f"VUI {field} value must be an integer") from exc


def run_vui_get(
    args: argparse.Namespace, stream: TextIO, factories: AdapterFactories
) -> int:
    adapter = factories.peripherals(**_peripheral_kwargs(args))
    try:
        method_name = {
            "switch": "get_switch",
            "volume": "get_volume",
            "brightness": "get_brightness",
        }[args.field]
        method = getattr(adapter.vui, method_name)
        return _emit(method(hardware_enabled=True), stream, args)
    finally:
        _close(adapter)


def run_vui_set(
    args: argparse.Namespace, stream: TextIO, factories: AdapterFactories
) -> int:
    adapter = factories.peripherals(**_peripheral_kwargs(args))
    try:
        value = _vui_value(args.field, args.value)
        method_name = {
            "switch": "set_switch",
            "volume": "set_volume",
            "brightness": "set_brightness",
        }[args.field]
        method = getattr(adapter.vui, method_name)
        return _emit(
            method(
                value,
                hardware_enabled=True,
                operator_acknowledged=True,
            ),
            stream,
            args,
        )
    finally:
        _close(adapter)


def run_obstacles_get_switch(
    args: argparse.Namespace, stream: TextIO, factories: AdapterFactories
) -> int:
    adapter = factories.peripherals(**_peripheral_kwargs(args))
    try:
        return _emit(adapter.obstacles.get_switch(hardware_enabled=True), stream, args)
    finally:
        _close(adapter)


def run_obstacles_set_switch(
    args: argparse.Namespace, stream: TextIO, factories: AdapterFactories
) -> int:
    adapter = factories.peripherals(**_peripheral_kwargs(args))
    try:
        return _emit(
            adapter.obstacles.set_switch(
                args.enabled,
                hardware_enabled=True,
                operator_acknowledged=True,
            ),
            stream,
            args,
        )
    finally:
        _close(adapter)


def _obstacle_move(
    args: argparse.Namespace,
    stream: TextIO,
    factories: AdapterFactories,
    method_name: str,
) -> int:
    adapter = factories.peripherals(**_peripheral_kwargs(args))
    try:
        return _emit(
            getattr(adapter.obstacles, method_name)(
                args.vx,
                args.vy,
                args.vyaw,
                hardware_enabled=True,
                operator_acknowledged=True,
            ),
            stream,
            args,
        )
    finally:
        _close(adapter)


def run_obstacles_move(
    args: argparse.Namespace, stream: TextIO, factories: AdapterFactories
) -> int:
    return _obstacle_move(args, stream, factories, "move")


def run_obstacles_move_absolute(
    args: argparse.Namespace, stream: TextIO, factories: AdapterFactories
) -> int:
    return _obstacle_move(args, stream, factories, "move_to_absolute_position")


def run_obstacles_move_increment(
    args: argparse.Namespace, stream: TextIO, factories: AdapterFactories
) -> int:
    return _obstacle_move(args, stream, factories, "move_to_increment_position")


def run_obstacles_remote_command(
    args: argparse.Namespace, stream: TextIO, factories: AdapterFactories
) -> int:
    adapter = factories.peripherals(**_peripheral_kwargs(args))
    try:
        return _emit(
            adapter.obstacles.use_remote_command_from_api(
                args.enabled,
                hardware_enabled=True,
                operator_acknowledged=True,
            ),
            stream,
            args,
        )
    finally:
        _close(adapter)


def _command_file(args: argparse.Namespace) -> Path:
    positional = getattr(args, "commands_file", None)
    option = getattr(args, "commands_file_option", None)
    if positional and option and positional != option:
        raise ValueError("positional command file and --file disagree")
    selected = option or positional
    if not isinstance(selected, str) or not selected:
        raise ValueError("a low-level JSON command file is required")
    return Path(selected)


def _load_motor_commands(args: argparse.Namespace) -> list[dict[str, Any]]:
    path = _command_file(args)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read low-level command file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"low-level command file must be valid JSON: {exc.msg}"
        ) from exc
    if not isinstance(value, list) or len(value) != 12:
        raise ValueError(
            "low-level command file must contain exactly 12 motor command objects"
        )
    required = {"q", "dq", "kp", "kd", "tau", "mode"}
    commands: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict) or set(item) != required:
            raise ValueError(
                f"motor command {index} must contain exactly q, dq, kp, kd, tau, mode"
            )
        commands.append(item)
    return commands


def _low_level_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "interface": args.interface,
        "domain_id": args.domain_id,
        "hardware_enabled": args.hardware_enabled,
        "operator_confirmed": args.operator_confirmed,
        "expert_low_level_confirmed": args.expert_low_level_confirmed,
        "robot_restrained_confirmed": args.robot_restrained_confirmed,
        "motion_service_released": args.motion_service_released,
        "motion_ownership_confirmed": args.motion_ownership_confirmed,
        "state_timeout": args.state_timeout,
        "state_freshness": args.state_freshness,
    }


def run_low_level_once(
    args: argparse.Namespace, stream: TextIO, factories: AdapterFactories
) -> int:
    commands = _load_motor_commands(args)
    adapter = factories.low_level(**_low_level_kwargs(args))
    try:
        adapter.publish_once(commands, state_timeout=args.state_timeout)
        return _emit(
            {"ok": True, "operation": "low_level_publish_once", "motor_count": 12},
            stream,
            args,
        )
    finally:
        _close(adapter)


def run_low_level_timed(
    args: argparse.Namespace, stream: TextIO, factories: AdapterFactories
) -> int:
    commands = _load_motor_commands(args)
    adapter = factories.low_level(**_low_level_kwargs(args))
    try:
        return _emit(
            adapter.publish_timed(
                commands,
                period=args.period,
                duration=args.duration,
                state_timeout=args.state_timeout,
            ),
            stream,
            args,
        )
    finally:
        _close(adapter)


_HANDLERS: dict[str, Callable[[argparse.Namespace, TextIO, AdapterFactories], int]] = {
    "unitree_sport_invoke": run_sport_invoke,
    "unitree_bounded_move": run_bounded_move,
    "unitree_service_list": run_service_list,
    "unitree_service_switch": run_service_switch,
    "unitree_report_frequency": run_report_frequency,
    "unitree_motion_check": run_motion_check,
    "unitree_motion_select": run_motion_select,
    "unitree_motion_release": run_motion_release,
    "unitree_video_capture": run_video_capture,
    "unitree_vui_get": run_vui_get,
    "unitree_vui_set": run_vui_set,
    "unitree_obstacles_get_switch": run_obstacles_get_switch,
    "unitree_obstacles_set_switch": run_obstacles_set_switch,
    "unitree_obstacles_move": run_obstacles_move,
    "unitree_obstacles_move_absolute": run_obstacles_move_absolute,
    "unitree_obstacles_move_increment": run_obstacles_move_increment,
    "unitree_obstacles_remote_command": run_obstacles_remote_command,
    "unitree_low_level_once": run_low_level_once,
    "unitree_low_level_timed": run_low_level_timed,
}


def run_unitree(
    args: argparse.Namespace,
    stream: TextIO,
    factories: AdapterFactories | None = None,
) -> int:
    """Dispatch one parsed Unitree command with lazy runtime failures."""

    if args.handler == "unitree_catalog":
        return run_catalog(args, stream)
    if args.handler == "unitree_help":
        stream.write(
            "robot-dog unitree: choose a subcommand; run "
            "robot-dog unitree --help for the full command surface.\n"
        )
        return 0
    handler = _HANDLERS.get(args.handler)
    if handler is None:
        return 0
    try:
        return handler(args, stream, _factories(factories))
    except Exception as exc:
        return _emit_error(stream, exc)


__all__ = [
    "AdapterFactories",
    "DEFAULT_FACTORIES",
    "authority_factory",
    "low_level_factory",
    "peripherals_factory",
    "run_catalog",
    "run_unitree",
    "sport_client_factory",
]
