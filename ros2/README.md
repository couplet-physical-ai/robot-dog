# Optional ROS 2 track

This directory documents the optional ROS 2 integration; it does not currently
ship a package, node, or executable. Start with
[`docs/integrations/ros2.md`](../docs/integrations/ros2.md).

The supported starting point is Ubuntu 22.04 with ROS 2 Humble and
`rmw_cyclonedds_cpp`. Select the physical or simulation DDS domain and the
network interface explicitly. Source the ROS installation and the Unitree
workspace first, then source
[`scripts/robot-dog-ros2-env.sh`](../scripts/robot-dog-ros2-env.sh) to validate
that state and export configuration.

The official Unitree stack is treated as a messages/examples layer. It is not a
complete URDF, Nav2, or TF integration. Any community package or adapter that
adds those capabilities is experimental until separately validated.
