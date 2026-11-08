# Optional C++ SDK2 track

This directory is reserved for the optional Unitree SDK2 integration. The track is
currently documentation-only: no executable or control node is part of this
repository yet.

Start with [`docs/integrations/cpp-sdk2.md`](../docs/integrations/cpp-sdk2.md).
That guide is the source of truth for the pinned SDK, toolchain baseline,
prebuilt-library provenance, and the Ubuntu 22.04 compatibility gate.

The first integration target is deliberately read-only state/telemetry. Keep the
initial bring-up limited to proving that the selected SDK and transport can
observe the expected state. Do not add a command path until the read-only gate,
platform validation, and an explicit review of the safety boundary are complete.
