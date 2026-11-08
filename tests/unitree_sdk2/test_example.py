"""Tests for the explicit hardware example using an injected fake probe."""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path

from robot_dog.adapters.unitree_sdk2 import UnitreeSdk2ProbeResult, UnitreeService

_EXAMPLE_PATH = (
    Path(__file__).resolve().parents[2]
    / "examples"
    / "hardware"
    / "unitree_readonly_probe.py"
)
_EXAMPLE_SPEC = importlib.util.spec_from_file_location(
    "unitree_readonly_probe_example", _EXAMPLE_PATH
)
assert _EXAMPLE_SPEC is not None and _EXAMPLE_SPEC.loader is not None
_EXAMPLE_MODULE = importlib.util.module_from_spec(_EXAMPLE_SPEC)
_EXAMPLE_SPEC.loader.exec_module(_EXAMPLE_MODULE)
main = _EXAMPLE_MODULE.main


def fake_probe_factory(*, network_interface: str, domain_id: int):
    assert network_interface == "enp2s0"
    assert domain_id == 0

    class FakeProbe:
        def probe(self) -> UnitreeSdk2ProbeResult:
            return UnitreeSdk2ProbeResult(
                network_interface=network_interface,
                domain_id=domain_id,
                api_version="1.0.0.1",
                server_api_version="1.0.0.1",
                services=(UnitreeService("sport", 1, True),),
            )

    return FakeProbe()


def test_example_requires_named_interface() -> None:
    output = io.StringIO()
    errors = io.StringIO()
    try:
        main([], stream=output, error_stream=errors, probe_factory=fake_probe_factory)
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover - argparse owns this path
        raise AssertionError("argparse should require --interface")


def test_example_is_read_only_and_json_serializable() -> None:
    output = io.StringIO()
    errors = io.StringIO()

    code = main(
        ["--interface", "enp2s0", "--json"],
        stream=output,
        error_stream=errors,
        probe_factory=fake_probe_factory,
    )

    assert code == 0
    assert errors.getvalue() == ""
    payload = json.loads(output.getvalue())
    assert payload["read_only"] is True
    assert payload["domain_id"] == 0
    assert payload["network_interface"] == "enp2s0"
    assert payload["services"] == [{"name": "sport", "protected": True, "status": 1}]
