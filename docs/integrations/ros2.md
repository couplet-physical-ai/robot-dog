# Optional ROS 2 setup track

This track is an optional ROS 2 integration for the Unitree Go2. It is designed
for safe, observable bring-up and configuration validation; this repository
does not yet ship a ROS 2 package or executable.

## Recommended baseline and pin

Use **Ubuntu 22.04 with ROS 2 Humble** as the recommended host. Select
`rmw_cyclonedds_cpp` explicitly and keep the physical and simulation DDS domains
separate:

| Use | `ROS_DOMAIN_ID` | Profile |
| --- | ---: | --- |
| Physical robot network | `0` (DDS domain 0) | `config/cyclonedds/physical.xml` |
| Simulation or isolated test network | `1` (DDS domain 1) | `config/cyclonedds/simulation.xml` |

The official Unitree ROS 2 source must be verified at this revision:

```text
Repository: https://github.com/unitreerobotics/unitree_ros2
Commit:     668d1ec5a05d1c38d3306bdca7d59f2ba3581a88
```

Obtain the source in an external workspace and keep the resolved commit in the
setup record. Do not place a second copy under `ros2/`.

## Source order and the Foxy trap

The pinned upstream setup scripts hardcode Foxy paths. They are not the setup
contract for this repository and must not be sourced blindly on Humble. Use this
order instead:

1. Install and source the ROS 2 Humble environment supplied by the host.
2. Build or install the official Unitree workspace at the pinned revision in an
external workspace.
3. Source that workspace's `install/setup.bash` in the current shell.
4. Select an explicit host interface and source the repository helper:

   ```bash
   source /path/to/robot-dog/scripts/robot-dog-ros2-env.sh \
     physical eno1 "$HOME/unitree_ros2_ws/install"
   ```

   Replace `eno1` with the interface that is actually connected to the intended
   network. The helper rejects a missing interface, a non-Humble/non-ROS 2
   shell, or a workspace that is not present in `AMENT_PREFIX_PATH`.

The helper only exports and prints configuration. It does not source either ROS
workspace for you, alter a route or interface, or invoke a robot command. This
keeps environment selection visible and reversible in the current shell.

## Cyclone DDS and interface selection

The helper sets:

- `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`;
- `ROS_DOMAIN_ID=0` for `physical` or `1` for `sim`/`simulation`;
- `ROBOT_DOG_ROS2_INTERFACE` to the validated interface;
- `CYCLONEDDS_URI` to the matching profile under
  `config/cyclonedds/`; and
- `ROBOT_DOG_ROS2_WORKSPACE` to the already-sourced install prefix.

An explicit interface is required for both profiles. Do not rely on DDS
interface auto-selection when a host has Wi-Fi, VPN, container, loopback, or
multiple Ethernet interfaces. Keep simulation on domain 1 so it cannot
accidentally join the physical domain.

## What the official stack does and does not provide

Treat the official pinned stack as a **messages/examples layer**. It is not a
complete URDF, Nav2, or TF stack. A later integration may add those pieces, but
that work needs its own compatibility and safety validation.

Community bridges, adapters, simulator integrations, and packages that add
URDF/Nav2/TF behavior are **experimental** here. Label them as such in any
follow-on documentation and keep them isolated from the official pinned
workspace until they have a reproducible validation result.

## Bring-up checklist

- [ ] Host is Ubuntu 22.04 and ROS 2 Humble is sourced.
- [ ] The official Unitree workspace resolves to commit
      `668d1ec5a05d1c38d3306bdca7d59f2ba3581a88`.
- [ ] The Unitree workspace install prefix is present in `AMENT_PREFIX_PATH`.
- [ ] The intended NIC is named explicitly and exists on the host.
- [ ] The helper prints `rmw_cyclonedds_cpp`, the intended domain, the intended
      interface, and the matching Cyclone profile.
- [ ] Physical and simulation checks use different domains.
- [ ] Initial observations remain read-only; no write-capable path is added by
      this setup track.
