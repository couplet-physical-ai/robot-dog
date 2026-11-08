# Third-party software, licensing, and redistribution ledger

**Baseline date:** 2026-08-21
**Purpose:** identify the license scope and redistribution work required for the robot-dog software boundary

This is an engineering intake and source ledger, not legal advice. The top-level Unitree SDK license does not collapse the licenses of bundled or transitive dependencies. A build is not cleared for redistribution until its exact source/artifact closure, notices, modifications, and distribution mode are recorded.

## Governing rules

- Use immutable source revisions, not `main`, floating tags, or an unrecorded package-manager result.
- Keep a software bill of materials (SBOM) for every releaseable host image, wheel, native library, or binary bundle.
- Preserve the copyright, license, NOTICE, attribution, and source-offer material required by each component's license.
- Do not vendor upstream binary libraries by default. The pinned C++ SDK source tree itself contains architecture-specific `libddsc.so`/`libddscxx.so` files under `thirdparty/lib`; that is evidence of upstream packaging, not permission for this project to copy or redistribute them. [R3]
- Build from reviewed source where practical. If a prebuilt is necessary, record its publisher, exact digest, provenance, target ABI, license package, vulnerability review, and redistribution decision.
- This project license does not grant redistribution rights to Unitree, Eclipse, ROS 2, Python, OS, or other third-party code. It also does not waive source, notice, patent, trademark, or modification obligations.
- Never put credentials, private keys, DDS permissions/governance files, or identifying unit records in a license or source archive.

## Current baseline ledger

| Component / closure | Immutable reference | License evidence | Scope and action |
| --- | --- | --- | --- |
| Unitree `unitree_sdk2` | `9754cd153af3da471b0fe5f3aa535e426fb11db3` [R1] | Top-level BSD-3-Clause [R2] | BSD-3-Clause obligations apply to Unitree SDK files. Inspect the bundled `licenses/` tree and native artifacts before any redistribution. |
| Unitree `unitree_sdk2_python` | `65691c8a8bc53b98d3976dba4dbf9d5d20b2e7f5` [R4] | Unitree project is BSD-3-Clause per the pinned baseline record [R5] | Top-level license is not a complete transitive inventory. Capture Python package metadata, wheel contents, and native-library provenance for the actual build. |
| Unitree `unitree_ros2` | `668d1ec5a05d1c38d3306bdca7d59f2ba3581a88` [R6] | Repository LICENSE and ROS package metadata declare BSD-3-Clause [R8] | Applies to Unitree repository/package content. ROS 2, RMW, message generators, and OS packages remain a separate closure. |
| Eclipse CycloneDDS | `0.10.2`, commit `9995905bce6c4cf9f740d6438bbf7fcfd1c83dfd` [R9] | EPL-2.0 **or** EDL-1.0 in LICENSE/package metadata [R10] | Preserve applicable license text and notices; review modifications and distribution form. Do not summarize this component as BSD merely because a Unitree wrapper is BSD. |
| CycloneDDS notices/embedded content | same CycloneDDS revision [R11] | NOTICE identifies `libmd5-rfc` as Zlib and `getopt` as public domain, in addition to the project license | Include the notice inventory when the component is distributed. Verify the exact build feature set and closure. |
| CycloneDDS C/C++ content bundled by `unitree_sdk2` | `unitree_sdk2` revision above [R1, R3] | Bundled Cyclone licenses include EPL/EDL; C++ wrapper content includes Apache-2.0 license text [R3, R13] | Treat each bundled directory/library as its own inventory item. Prefer reviewed source build rather than copying upstream binary payloads. |
| Iceoryx / RapidJSON material in the C++ SDK tree | same `unitree_sdk2` revision [R1] | Iceoryx license text is Apache-2.0; RapidJSON license identifies MIT source terms plus third-party exceptions [R13] | Retain component notices and third-party exceptions if those files or derived artifacts are distributed. |
| ROS 2, RMW, Python, OS and build-tool closure | exact environment required per build | May include BSD variants, Apache-2.0, MIT, MPL-2.0, EPL/EDL, Zlib/public-domain, and other terms | **Not cleared by this baseline.** Generate and review the actual closure. Never assume the top-level Unitree BSD license covers it. |

The closure must be prepared to account for the license families encountered in this stack, including EPL/EDL, Apache, MIT, MPL, BSD variants, Zlib/public-domain, and any additional notices discovered. The exact component, version, file scope, and license expression—not a family-level guess—controls the release decision.

## Distribution modes

Classify each use before release:

1. **Local source-only development** — source is available to the development team; still retain notices and respect upstream terms.
2. **Organisation-internal binary artifact** — a wheel, native library, image, or host bundle is shared within an organisation; attach SBOM, notices, checksums, and review decision.
3. **External/customer distribution** — requires a release-specific legal review, complete applicable notices/source obligations, and a decision on any proprietary Unitree or vendor material.
4. **No redistribution** — use only for a local test when rights, provenance, or notices are incomplete. This is the default for unreviewed vendor binaries.

Do not call an artifact "open source" or "redistributable" based solely on a repository being public.

## Intake record for every dependency/artifact

For each source file, package, library, wheel, firmware-adjacent tool, or binary that enters a build, record:

- component name and exact version/commit;
- immutable source URL and access date;
- package/artifact URL and SHA-256, if prebuilt;
- direct and transitive dependency relationship;
- SPDX expression if available and the authoritative license file/NOTICE path;
- copyright holders and attribution requirements;
- source modifications and patch identifiers;
- build flags/features that affect included code;
- target architecture/ABI and where the artifact is stored;
- vulnerability/security review status;
- whether it is source-only, internal binary, or externally redistributed; and
- owner and approval for the distribution decision.

The unit manifest points to this inventory; it does not replace it.

## Review gates

A dependency is **approved for local development** when its source, license, provenance, and security record are complete. It is **approved for redistribution** only when all applicable notices/source obligations are packaged and the release owner has signed off.

A missing license file, floating revision, unknown binary provenance, unexplained native library, unresolved MPL/EPL/EDL/Apache obligation, or incomplete transitive inventory is a **blocker**, not an invitation to infer a permissive license.

## References

- [references.md](references.md) — immutable source URLs, access dates, and source roles
- [compatibility.md](compatibility.md) — artifact pinning and ABI evidence
- [security.md](security.md) — supply-chain and binary handling controls
