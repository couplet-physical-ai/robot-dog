# Optional C++ SDK2 setup track

This is an optional developer track for the Unitree Go2 SDK2. It is separate
from the repository's current learning path and does not add a C++ executable.
The first target is **read-only state/telemetry**; this track must not be used as
a shortcut to a control path.

## Official source and pin

Use the official Unitree SDK2 repository and verify the resolved revision before
building anything:

```text
Repository: https://github.com/unitreerobotics/unitree_sdk2
Commit:     9754cd153af3da471b0fe5f3aa535e426fb11db3
```

Keep that checkout outside this repository. A local checkout is an input to the
build, not a new source tree under `cpp/`. Record the exact resolved commit in a
bring-up note; do not silently substitute the default branch.

## Baseline matrix

The documented baseline for the pinned SDK is Ubuntu 20.04 on
`x86_64/aarch64`, with GCC 9.4, C++17, and CMake>=3.10. The detailed matrix
is:

| Item | Baseline |
| --- | --- |
| Operating system | Ubuntu 20.04 |
| CPU | x86_64 or aarch64 |
| Compiler | GCC 9.4 |
| Language | C++17 |
| CMake | 3.10 or newer |
| SDK/transport libraries | Use the SDK's prebuilt SDK artifacts and bundled Cyclone libraries first |

The bundled libraries are part of the SDK provenance for this track. Do not
replace them with an unrelated system Cyclone installation during the first
bring-up; doing so can hide ABI or discovery differences.

## Setup gates

1. Choose a clean external SDK workspace and obtain the official repository at
the pin above. Verify the commit before configuring a build.
2. Confirm the compiler, CMake, architecture, and operating-system values
against the baseline matrix. Capture the versions rather than relying on a
shell prompt or distribution label.
3. Configure and build the pinned SDK using its documented CMake entry point,
keeping build output outside this repository. The initial check is a library
and compile/link compatibility check; it is not a new application target in
this repository.
4. Confirm that the SDK resolves its prebuilt artifacts and bundled Cyclone
libraries from the pinned distribution. If the build falls back to system
libraries, stop and record that as a compatibility result.
5. Once the toolchain gate is green, define the smallest read-only state sample
for a later change. Keep that sample out of this track until the transport,
identity, and safety review are complete.

## Ubuntu 22.04 compatibility gate

Ubuntu 22.04 is **not assumed compatible from the Ubuntu 20.04 baseline**. It
must be validated explicitly before being listed as a supported development
host. On both x86_64 and aarch64 where applicable, use the same pinned SDK and
record:

- Ubuntu release and kernel;
- architecture;
- `g++ --version` and the selected C++ standard;
- `cmake --version`;
- the exact SDK commit;
- every resolved SDK and Cyclone library path; and
- configure, compile, and link results for the read-only integration boundary.

A successful configuration alone is not sufficient. Treat an ABI mismatch,
missing bundled library, discovery failure, or compiler warning promoted to an
error as a failed Ubuntu 22.04 validation. Keep the result as a compatibility
note before changing the baseline.

## Current boundary

This repository does not yet ship a C++ node, executable, or source-level
control example. Do not infer that installing the SDK grants a supported
application interface. The safe sequence is:

1. validate the pinned SDK and its bundled transport dependencies;
2. prove read-only state/telemetry on the validated platform; and
3. review any future write-capable design separately.

For ROS 2 setup, use the separate [ROS 2 integration track](ros2.md) and its
safe environment helper; do not mix the two dependency baselines without a
recorded compatibility result.
