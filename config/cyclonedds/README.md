# Cyclone DDS profiles

These profiles are intentionally small and explicit:

| Profile | ROS/DDS domain | Intended use |
| --- | ---: | --- |
| `physical.xml` | `0` | Physical robot network |
| `simulation.xml` | `1` | Simulation or isolated test network |

Both profiles take the interface from the `ROBOT_DOG_ROS2_INTERFACE`
environment variable. The variable must be set by
`scripts/robot-dog-ros2-env.sh` after that helper has validated the interface.
Do not edit the XML to guess a host-specific interface and do not reuse domain
0 for simulation.

The helper also sets `CYCLONEDDS_URI` to the selected profile and selects
`rmw_cyclonedds_cpp`. It does not rewrite these files, change networking, source
a workspace, or invoke a robot command.
