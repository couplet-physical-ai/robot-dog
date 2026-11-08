#!/usr/bin/env bash
# Source this file; it is intentionally not an executable setup program.
#
# Usage:
#   source scripts/robot-dog-ros2-env.sh <physical|sim> <interface> <install-prefix>
#
# The helper validates the current shell and exports/prints configuration only.
# It does not source a ROS workspace, change networking, or invoke robot tools.

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  printf 'robot-dog ROS 2 environment: source this file; do not execute it\n' >&2
  exit 2
fi

robot_dog_ros2_env_error() {
  printf 'robot-dog ROS 2 environment: %s\n' "$1" >&2
  return 1
}

robot_dog_ros2_env_main() {
  local mode="${1:-${ROBOT_DOG_ROS2_MODE:-}}"
  local interface="${2:-${ROBOT_DOG_ROS2_INTERFACE:-}}"
  local workspace="${3:-${ROBOT_DOG_ROS2_WORKSPACE:-}}"
  local domain_id profile
  local workspace_without_slash prefix prefix_without_slash
  local workspace_sourced=false
  local old_ifs script_dir repo_root config_file
  local -a ament_prefixes=()

  case "$mode" in
    physical)
      domain_id=0
      profile=physical
      ;;
    sim|simulation)
      mode=sim
      domain_id=1
      profile=simulation
      ;;
    '')
      robot_dog_ros2_env_error "mode is required: use physical or sim"
      return 1
      ;;
    *)
      robot_dog_ros2_env_error "unsupported mode '$mode': use physical or sim"
      return 1
      ;;
  esac

  if [[ -z "$interface" ]]; then
    robot_dog_ros2_env_error "an explicit network interface is required"
    return 1
  fi

  # The allow-list also keeps the /sys/class/net lookup below inside that tree.
  if [[ ! "$interface" =~ ^[[:alnum:]_.:-]+$ ]]; then
    robot_dog_ros2_env_error "invalid network interface '$interface'"
    return 1
  fi

  # This is a read-only kernel view; no network command or configuration API is used.
  if [[ ! -d "/sys/class/net/$interface" ]]; then
    robot_dog_ros2_env_error "network interface '$interface' does not exist"
    return 1
  fi

  if [[ "${ROS_VERSION:-}" != "2" ]]; then
    robot_dog_ros2_env_error "the current shell does not have a ROS 2 environment sourced"
    return 1
  fi

  if [[ "${ROS_DISTRO:-}" != "humble" ]]; then
    robot_dog_ros2_env_error "ROS_DISTRO must be humble; refusing an unvalidated distro"
    return 1
  fi

  if [[ -z "${AMENT_PREFIX_PATH:-}" ]]; then
    robot_dog_ros2_env_error "AMENT_PREFIX_PATH is empty; source ROS 2 and the Unitree workspace first"
    return 1
  fi

  if [[ -z "$workspace" || "$workspace" != /* ]]; then
    robot_dog_ros2_env_error "an absolute, already-sourced ROS install prefix is required"
    return 1
  fi

  if [[ ! -d "$workspace" || ! -r "$workspace/setup.bash" ]]; then
    robot_dog_ros2_env_error "ROS workspace '$workspace' is missing or has no readable setup.bash"
    return 1
  fi

  # A workspace is considered sourced only when its install prefix is present in
  # the current shell's AMENT_PREFIX_PATH. Do not source it implicitly here.
  workspace_without_slash="${workspace%/}"
  old_ifs="$IFS"
  IFS=:
  read -r -a ament_prefixes <<< "${AMENT_PREFIX_PATH}"
  IFS="$old_ifs"
  for prefix in "${ament_prefixes[@]}"; do
    prefix_without_slash="${prefix%/}"
    if [[ "$prefix_without_slash" == "$workspace_without_slash" ]]; then
      workspace_sourced=true
      break
    fi
  done

  if [[ "$workspace_sourced" != true ]]; then
    robot_dog_ros2_env_error "ROS workspace '$workspace' is not present in AMENT_PREFIX_PATH"
    return 1
  fi

  script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" 2>/dev/null && pwd -P)" || {
    robot_dog_ros2_env_error "cannot resolve the helper directory"
    return 1
  }
  repo_root="$(cd -- "$script_dir/.." 2>/dev/null && pwd -P)" || {
    robot_dog_ros2_env_error "cannot resolve the repository root"
    return 1
  }
  config_file="$repo_root/config/cyclonedds/$profile.xml"
  if [[ ! -r "$config_file" ]]; then
    robot_dog_ros2_env_error "Cyclone DDS profile is not readable: $config_file"
    return 1
  fi

  export ROBOT_DOG_ROS2_MODE="$mode"
  export ROBOT_DOG_ROS2_INTERFACE="$interface"
  export ROBOT_DOG_ROS2_WORKSPACE="$workspace_without_slash"
  export ROBOT_DOG_ROS2_DOMAIN_ID="$domain_id"
  export ROBOT_DOG_ROS2_CYCLONEDDS_CONFIG="$config_file"
  export ROS_DOMAIN_ID="$domain_id"
  export RMW_IMPLEMENTATION="rmw_cyclonedds_cpp"
  export CYCLONEDDS_URI="file://$config_file"

  printf 'robot-dog ROS 2 environment configured (exports only):\n'
  printf '  mode:             %s\n' "$ROBOT_DOG_ROS2_MODE"
  printf '  ROS_DISTRO:       %s\n' "$ROS_DISTRO"
  printf '  RMW_IMPLEMENTATION: %s\n' "$RMW_IMPLEMENTATION"
  printf '  ROS_DOMAIN_ID:    %s\n' "$ROS_DOMAIN_ID"
  printf '  interface:        %s\n' "$ROBOT_DOG_ROS2_INTERFACE"
  printf '  workspace:        %s\n' "$ROBOT_DOG_ROS2_WORKSPACE"
  printf '  CYCLONEDDS_URI:   %s\n' "$CYCLONEDDS_URI"
  return 0
}

# Run through a function so sourcing this helper does not overwrite the
# caller's positional parameters. Remove the temporary functions afterward.
if robot_dog_ros2_env_main "$@"; then
  unset -f robot_dog_ros2_env_main robot_dog_ros2_env_error
  return 0
fi
unset -f robot_dog_ros2_env_main robot_dog_ros2_env_error
return 1
