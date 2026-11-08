# Offline fake example

This example needs only Python. It does not import Unitree SDK, ROS, open a
socket, discover a robot, or issue a hardware command.

From the repository root:

```console
python examples/fake/demo.py
```

The same deterministic read-only experience is available through the CLI:

```console
robot-dog demo
robot-dog capabilities
robot-dog status
```
