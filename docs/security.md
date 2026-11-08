# Robot-dog security baseline

**Baseline date:** 2026-08-21
**Security posture:** assume DDS is an exposed, unauthenticated local control network unless a separately reviewed implementation proves otherwise

The baseline protects a physical robot and its control/telemetry plane. It does not assume that a vendor package, a product name, or successful DDS discovery provides identity, authorization, confidentiality, or integrity.

## Non-negotiable controls

1. **Isolate DDS at the link.** Use a point-to-point NIC or a dedicated VLAN/switch segment containing only the approved robot and engineering-host peers.
2. **No corporate bridge.** Do not bridge the DDS interface to a corporate LAN, Wi-Fi uplink, VPN, hotspot, office switch, or another robot network.
3. **No default route or Internet.** The robot/host DDS path must have no default gateway and no Internet route. Package downloads happen on a separate approved path, not through the live DDS link.
4. **No security claim from reachability.** The Python prebuilt Cyclone package lacks DDS Security. Assume traffic can be observed, spoofed, replayed, or injected by anyone who can reach that segment. [R14]
5. **No secrets in project docs.** Never commit serials, MACs, IPs, passwords, tokens, private keys, DDS governance/permissions files, or credential-bearing logs. Store references to approved secret/evidence systems instead.
6. **No unapproved shell or credential guessing.** Shell access is not a baseline capability. Use only an authorized vendor/site path; do not bypass access controls or rely on default credentials.
7. **No vendor binaries by default.** Prefer a reviewed source build or approved internal artifact. If a prebuilt is necessary, pin it, checksum it, scan it, inventory its licenses, and record the review before use.
8. **Read-only first.** Start with discovery and telemetry. Motion, actuator, setpoint, configuration, and firmware operations require a separate operator-approved procedure.

## Trust boundaries and threat model

| Boundary | Threat | Baseline treatment |
| --- | --- | --- |
| Physical unit | Unauthorized handling, damaged battery, unexpected motion, tampered accessories | Physical intake, safe area, operator approval, and hold on unresolved defects. |
| DDS segment | Eavesdropping, discovery spoofing, command injection, replay, denial of service | Point-to-point/dedicated VLAN, no route/bridge/Internet, host firewall, expected-peer checks, read-only bring-up. Isolation is containment, not cryptographic authentication. |
| Engineering host | Compromised process, stale dependency, overly broad route, accidental package download on DDS NIC | Separate package path, pinned artifacts, least privilege, interface binding, route verification, logs and checksums. |
| Artifacts | Malicious or altered source/binary, license omission, floating dependency | Immutable revisions, checksums, source/license ledger, no default binary vendoring, review before redistribution. |
| Evidence | Secret or personal/physical data leakage through logs/photos | Sanitization, private evidence store, references/hashes only in repository. |
| Vendor/firmware boundary | Firmware/API mismatch or undocumented behavior | Record exact firmware and test result per unit; do not extrapolate from another unit. |

## Approved network shape

The preferred shape is:

```text
[Go2 EDU unit] ===== dedicated point-to-point NIC or isolated VLAN ===== [authorized host]
       no corporate bridge       no default gateway       no VPN/hotspot bridge       no Internet route
```

The host may have a second interface for ordinary engineering work, but the DDS interface must not forward, bridge, NAT, or share that route. Before bringing up DDS, inspect routes, bridge membership, firewall rules, interface binding, and the actual peer list. Record only sanitized results in the repository.

A dedicated switch/VLAN is acceptable only when its isolation is verified. A VLAN label by itself is not evidence that inter-VLAN routing, management access, Wi-Fi bridging, or a default route is absent.

## Secure bring-up checklist

- [ ] Physical intake and safety hold checks pass.
- [ ] Unit-specific manifest exists in the private inventory with no repository-visible secrets.
- [ ] The robot and host interfaces are identified and bound to the isolated link.
- [ ] Bridge membership, forwarding/NAT, VPN/hotspot sharing, default route, and Internet route are absent or explicitly disabled.
- [ ] Firewall policy permits only the tested robot/host traffic on the dedicated link; broad corporate-LAN rules are not used as a shortcut.
- [ ] DDS domain/configuration and expected peers are recorded privately and are not copied from an unrelated unit.
- [ ] DDS Security is marked **not provided by the Python prebuilt baseline**; no encryption/authentication claim is made.
- [ ] Logs are sanitized before storage, with secrets and private network identifiers removed.
- [ ] The first application action is read-only discovery/telemetry.
- [ ] Any command path has a separate operator, physical-clearance check, and approved procedure.

## Application and host controls

- Bind processes to the intended DDS interface; do not rely on the kernel to choose a safe interface.
- Run development processes with the least privilege that supports the test.
- Keep the DDS process and dependency tree on the approved immutable baseline. Do not install a newer wheel or copy a library into place to make an import succeed without recording and retesting the deviation.
- Treat all robot telemetry, video, logs, and maps as potentially sensitive. Define retention and access in the approved evidence store.
- Avoid capturing credentials or raw network configuration in shell transcripts. If a raw log is necessary for incident response, keep it private and reference it by an evidence ID.
- If a test needs Internet access, disconnect or disable the DDS path first, or use a separately approved host/path. Never temporarily bridge the live control network for convenience.

## Incident response

If an unexpected peer, command, route, broadcast, process, or robot behavior is observed:

1. Stop issuing application commands and follow the approved physical safe-state procedure.
2. Isolate the DDS link without creating a new route or bridge.
3. Preserve sanitized timestamps, process/configuration versions, route/firewall state, and private raw evidence under the incident process.
4. Record the unit, host, exact dependency revisions, and last known safe state.
5. Do not restore connectivity, rotate firmware, delete logs, or repeat motion until the responsible operator/security owner approves the next step.

This document does not replace a site emergency procedure. It specifically prohibits treating an unprotected DDS segment as a trusted corporate network.

## References

- [compatibility.md](compatibility.md)
- [hardware/intake.md](hardware/intake.md)
- [third-party.md](third-party.md)
- [references.md](references.md)
