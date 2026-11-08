"""Argument parser for the robot-dog operator CLI."""

from __future__ import annotations

import argparse


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise argparse.ArgumentTypeError("expected true or false")


def _add_acknowledgement(
    parser: argparse.ArgumentParser,
    option: str,
    *,
    dest: str,
    help_text: str,
    required: bool = False,
) -> None:
    """Add an explicit, adapter-shaped acknowledgement flag.

    These are deliberately flags rather than a catch-all ``--yes`` switch.  A
    command's parsed namespace therefore maps directly to the named boolean
    gates in the Unitree adapters.
    """

    parser.add_argument(
        option,
        dest=dest,
        action="store_true",
        required=required,
        help=help_text,
    )


def _add_json(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit the normalized result as machine-readable JSON",
    )


def _add_runtime_options(
    parser: argparse.ArgumentParser,
    *,
    operator_acknowledged: bool,
) -> None:
    parser.add_argument(
        "--interface",
        "--network-interface",
        dest="interface",
        required=True,
        metavar="NAME",
        help="explicit robot-facing network interface",
    )
    parser.add_argument(
        "--domain-id",
        "--domain",
        required=True,
        type=int,
        metavar="N",
        help="explicit DDS domain id",
    )
    _add_acknowledgement(
        parser,
        "--hardware-enabled",
        dest="hardware_enabled",
        required=True,
        help_text="acknowledge that this command may access robot hardware",
    )
    if operator_acknowledged:
        _add_acknowledgement(
            parser,
            "--operator-acknowledged",
            dest="operator_acknowledged",
            required=True,
            help_text="acknowledge operator intent for a hardware mutation",
        )
    _add_json(parser)


def _add_high_level_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=None,
        metavar="SECONDS",
        help="SportClient RPC timeout",
    )
    parser.add_argument(
        "--enable-lease",
        action="store_true",
        help="pass the adapter's explicit SDK lease option through",
    )


def _add_target_confirmation(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--target-id",
        required=True,
        metavar="ID",
        help="named service/robot target",
    )
    parser.add_argument(
        "--confirm",
        required=True,
        metavar="ID",
        help="must exactly equal --target-id",
    )


def _add_authority_parser(
    parent: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
    *,
    aliases: list[str] | None = None,
) -> tuple[
    argparse.ArgumentParser,
    argparse._SubParsersAction[argparse.ArgumentParser],
]:
    parser = parent.add_parser(
        name,
        aliases=aliases or [],
        help="inspect and control Unitree services or motion authority",
    )
    children = parser.add_subparsers(dest="unitree_operation", metavar="OPERATION")
    parser.set_defaults(handler="unitree_help")
    return parser, children


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="robot-dog",
        description=(
            "Operator CLI for full Unitree Go2 programming access. Offline "
            "tools remain safe by default; explicit hardware commands require "
            "named interfaces, domains, and adapter acknowledgements."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version="robot-dog 0.1.0 (full-control operator CLI)",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    doctor = subparsers.add_parser(
        "doctor",
        help="inspect local OS, Python, optional SDKs, and a configured NIC",
    )
    doctor.add_argument(
        "--nic",
        metavar="NAME",
        help="check this configured local interface (the name is never printed)",
    )
    doctor.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable diagnostics",
    )
    doctor.set_defaults(handler="doctor")

    demo = subparsers.add_parser(
        "demo",
        help="show deterministic fake telemetry and read-only learning state",
    )
    demo.add_argument(
        "--frames",
        type=int,
        default=3,
        metavar="N",
        help="number of deterministic telemetry frames to show (default: 3)",
    )
    demo.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable demo data",
    )
    demo.set_defaults(handler="demo")

    capabilities = subparsers.add_parser(
        "capabilities",
        aliases=["caps"],
        help="show what the offline adapter can and cannot do",
    )
    capabilities.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable capabilities",
    )
    capabilities.set_defaults(handler="capabilities")

    status = subparsers.add_parser(
        "status",
        help="show the current offline fake adapter status",
    )
    status.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable status",
    )
    status.set_defaults(handler="status")

    unitree = subparsers.add_parser(
        "unitree",
        help="full, explicitly gated Unitree Go2 operator commands",
    )
    unitree_subparsers = unitree.add_subparsers(
        dest="unitree_command", metavar="UNITREE_COMMAND"
    )
    unitree.set_defaults(handler="unitree_help")

    catalog = unitree_subparsers.add_parser(
        "catalog",
        aliases=["commands"],
        help="list the complete source-verified SportClient catalog",
    )
    catalog.add_argument(
        "--json",
        action="store_true",
        help="emit catalog entries as JSON",
    )
    catalog.set_defaults(handler="unitree_catalog")

    sport = unitree_subparsers.add_parser(
        "sport-invoke",
        aliases=["invoke", "sport", "action"],
        help="invoke one cataloged SportClient action with JSON arguments",
    )
    sport.add_argument(
        "action",
        nargs="?",
        help="catalog action name (for example StandUp or front_flip)",
    )
    sport.add_argument(
        "--action",
        dest="action_option",
        help="catalog action name; equivalent to the positional action",
    )
    sport.add_argument(
        "--args",
        "--positional-args",
        dest="positional_args",
        default="[]",
        metavar="JSON",
        help="JSON array of positional arguments (default: [])",
    )
    sport.add_argument(
        "--kwargs",
        "--keyword-args",
        dest="keyword_args",
        default="{}",
        metavar="JSON",
        help="JSON object of keyword arguments (default: {})",
    )
    _add_runtime_options(sport, operator_acknowledged=True)
    _add_high_level_options(sport)
    _add_acknowledgement(
        sport,
        "--hazardous-motion-acknowledged",
        dest="hazardous_motion_acknowledged",
        help_text="pass the adapter's separate special-motion acknowledgement",
    )
    _add_acknowledgement(
        sport,
        "--intentional",
        dest="intentional",
        required=True,
        help_text="confirm this dynamic action invocation is intentional",
    )
    sport.set_defaults(handler="unitree_sport_invoke")

    move = unitree_subparsers.add_parser(
        "move",
        aliases=["bounded-move"],
        help="run the bounded, deadman-protected SportClient Move action",
    )
    move.add_argument("vx", type=float, metavar="VX")
    move.add_argument("vy", type=float, metavar="VY")
    move.add_argument("vyaw", type=float, metavar="VYAW")
    move.add_argument(
        "--duration-seconds",
        "--duration",
        dest="duration_seconds",
        required=True,
        type=float,
        metavar="SECONDS",
    )
    move.add_argument("--session-id", "--session", dest="session_id", required=True)
    move.add_argument("--deadman-timeout-seconds", type=float, default=None)
    move.add_argument("--refresh-period-seconds", type=float, default=None)
    _add_runtime_options(move, operator_acknowledged=True)
    _add_high_level_options(move)
    move.set_defaults(handler="unitree_bounded_move")

    service, service_operations = _add_authority_parser(
        unitree_subparsers, "service", aliases=["services"]
    )
    service_list_parser = service_operations.add_parser(
        "list", help="read RobotStateClient.ServiceList"
    )
    _add_runtime_options(service_list_parser, operator_acknowledged=False)
    service_list_parser.set_defaults(handler="unitree_service_list")
    service_switch = service_operations.add_parser(
        "switch", help="enable or disable one named service"
    )
    service_switch.add_argument("name", metavar="SERVICE")
    service_switch.add_argument("--enabled", required=True, type=_parse_bool)
    _add_runtime_options(service_switch, operator_acknowledged=True)
    _add_target_confirmation(service_switch)
    service_switch.set_defaults(handler="unitree_service_switch")
    report = service_operations.add_parser(
        "report-frequency",
        aliases=["report-freq"],
        help="set RobotState report frequency",
    )
    report.add_argument("interval", type=int, metavar="INTERVAL")
    report.add_argument("duration", type=int, metavar="DURATION")
    _add_runtime_options(report, operator_acknowledged=True)
    report.set_defaults(handler="unitree_report_frequency")

    motion, motion_operations = _add_authority_parser(
        unitree_subparsers, "motion", aliases=["motion-mode"]
    )
    check_mode = motion_operations.add_parser(
        "check", help="read the current motion mode"
    )
    _add_runtime_options(check_mode, operator_acknowledged=False)
    check_mode.set_defaults(handler="unitree_motion_check")
    select_mode = motion_operations.add_parser("select", help="select a motion mode")
    select_mode.add_argument("mode", metavar="MODE")
    _add_runtime_options(select_mode, operator_acknowledged=True)
    _add_target_confirmation(select_mode)
    select_mode.set_defaults(handler="unitree_motion_select")
    release_mode = motion_operations.add_parser(
        "release", help="release motion authority"
    )
    _add_runtime_options(release_mode, operator_acknowledged=True)
    _add_target_confirmation(release_mode)
    release_mode.set_defaults(handler="unitree_motion_release")

    video = unitree_subparsers.add_parser(
        "video",
        aliases=["video-capture"],
        help="capture one VideoClient image sample",
    )
    video.add_argument("--output", required=True, metavar="PATH")
    _add_runtime_options(video, operator_acknowledged=False)
    video.set_defaults(handler="unitree_video_capture")
    video_operations = video.add_subparsers(dest="video_operation", metavar="OPERATION")
    video_capture = video_operations.add_parser(
        "capture", help="capture one VideoClient image sample"
    )
    video_capture.add_argument("--output", required=True, metavar="PATH")
    _add_runtime_options(video_capture, operator_acknowledged=False)
    video_capture.set_defaults(handler="unitree_video_capture")

    vui = unitree_subparsers.add_parser(
        "vui", help="read or set VUI switch, volume, and brightness"
    )
    vui_operations = vui.add_subparsers(dest="vui_operation", metavar="OPERATION")
    vui_get = vui_operations.add_parser("get", help="read one VUI value")
    vui_get.add_argument("field", choices=["switch", "volume", "brightness"])
    _add_runtime_options(vui_get, operator_acknowledged=False)
    vui_get.set_defaults(handler="unitree_vui_get")
    vui_set = vui_operations.add_parser("set", help="set one VUI value")
    vui_set.add_argument("field", choices=["switch", "volume", "brightness"])
    vui_set.add_argument("value", metavar="VALUE")
    _add_runtime_options(vui_set, operator_acknowledged=True)
    vui_set.set_defaults(handler="unitree_vui_set")
    vui.set_defaults(handler="unitree_help")

    obstacles = unitree_subparsers.add_parser(
        "obstacles", aliases=["obstacle"], help="inspect and control obstacle avoidance"
    )
    obstacle_operations = obstacles.add_subparsers(
        dest="obstacle_operation", metavar="OPERATION"
    )
    obstacle_get = obstacle_operations.add_parser(
        "get-switch", help="read obstacle avoidance state"
    )
    _add_runtime_options(obstacle_get, operator_acknowledged=False)
    obstacle_get.set_defaults(handler="unitree_obstacles_get_switch")
    obstacle_switch = obstacle_operations.add_parser(
        "set-switch", help="set obstacle avoidance state"
    )
    obstacle_switch.add_argument("--enabled", required=True, type=_parse_bool)
    _add_runtime_options(obstacle_switch, operator_acknowledged=True)
    obstacle_switch.set_defaults(handler="unitree_obstacles_set_switch")
    for operation, handler, help_text in (
        ("move", "unitree_obstacles_move", "send obstacle-aware velocity"),
        (
            "move-absolute",
            "unitree_obstacles_move_absolute",
            "move to an absolute position",
        ),
        ("move-increment", "unitree_obstacles_move_increment", "move by an increment"),
    ):
        obstacle_move = obstacle_operations.add_parser(operation, help=help_text)
        obstacle_move.add_argument("vx", type=float, metavar="VX")
        obstacle_move.add_argument("vy", type=float, metavar="VY")
        obstacle_move.add_argument("vyaw", type=float, metavar="VYAW")
        _add_runtime_options(obstacle_move, operator_acknowledged=True)
        obstacle_move.set_defaults(handler=handler)
    obstacle_remote = obstacle_operations.add_parser(
        "remote-command",
        aliases=["use-remote-command"],
        help="select API remote commands",
    )
    obstacle_remote.add_argument("--enabled", required=True, type=_parse_bool)
    _add_runtime_options(obstacle_remote, operator_acknowledged=True)
    obstacle_remote.set_defaults(handler="unitree_obstacles_remote_command")
    obstacles.set_defaults(handler="unitree_help")

    low_level = unitree_subparsers.add_parser(
        "low-level",
        aliases=["lowlevel"],
        help="publish explicit 12-joint LowCmd records",
    )
    low_operations = low_level.add_subparsers(
        dest="low_level_operation", metavar="OPERATION"
    )

    def add_low_level_command(
        name: str,
        handler: str,
        help_text: str,
        *,
        aliases: list[str] | None = None,
    ) -> argparse.ArgumentParser:
        command = low_operations.add_parser(name, aliases=aliases or [], help=help_text)
        command.add_argument(
            "commands_file",
            nargs="?",
            metavar="COMMANDS_JSON",
            help="JSON file containing exactly 12 q/dq/kp/kd/tau/mode objects",
        )
        command.add_argument(
            "--file",
            "--commands-file",
            "--command-file",
            "--json-file",
            "--commands",
            dest="commands_file_option",
            metavar="PATH",
            help="JSON command file (alternative to the positional path)",
        )
        _add_runtime_options(command, operator_acknowledged=False)
        for option, dest, help_text in (
            (
                "--operator-confirmed",
                "operator_confirmed",
                "confirm the low-level operator action",
            ),
            (
                "--expert-low-level-confirmed",
                "expert_low_level_confirmed",
                "confirm expert low-level commissioning approval",
            ),
            (
                "--robot-restrained-confirmed",
                "robot_restrained_confirmed",
                "confirm the named robot is physically restrained",
            ),
            (
                "--motion-service-released",
                "motion_service_released",
                "pass the adapter's motion-service release gate",
            ),
            (
                "--motion-ownership-confirmed",
                "motion_ownership_confirmed",
                "pass the adapter's motion-ownership gate",
            ),
        ):
            _add_acknowledgement(
                command,
                option,
                dest=dest,
                required=True,
                help_text=help_text,
            )
        command.add_argument("--state-timeout", type=float, default=1.0)
        command.add_argument("--state-freshness", type=float, default=0.25)
        command.set_defaults(handler=handler)
        return command

    add_low_level_command(
        "once",
        "unitree_low_level_once",
        "publish one LowCmd",
        aliases=["one-shot", "publish-once"],
    )
    timed = add_low_level_command(
        "timed",
        "unitree_low_level_timed",
        "publish LowCmd repeatedly for a finite duration",
        aliases=["publish-timed"],
    )
    timed.add_argument("--period", required=True, type=float, metavar="SECONDS")
    timed.add_argument("--duration", required=True, type=float, metavar="SECONDS")
    low_level.set_defaults(handler="unitree_help")

    return parser


__all__ = ["build_parser"]
