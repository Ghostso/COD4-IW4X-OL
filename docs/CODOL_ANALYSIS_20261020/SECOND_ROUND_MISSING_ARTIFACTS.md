# Second Round Missing Artifacts

Date: 2026-10-21 (Asia/Shanghai)

Every row states what is absent, why it matters, how to obtain it, which domain it unblocks, and whether round 3 can proceed without it.

| ID | Project | Missing artifact | Why it is missing | Acquisition | Unblocks | Blocks round 3? |
|---|---|---|---|---|---|---|
| M2-C4-01 | CoD4x | 32-bit GCC/G++/MinGW and NASM build environment | absent from PATH | Provide pinned 32-bit toolchain or a CI-built artifact with provenance | build proof | no, for comparison; yes for executable claims |
| M2-C4-02 | CoD4x | `cod4x18_dedrun` output and build log | no build performed | Build a clean checkout in an isolated directory; retain log, compiler versions and SHA | B/R build evidence | yes for executable claims |
| M2-C4-03 | CoD4x | complete legitimate Cod4 `main/*.iwd` and `zone/*` | not confirmed in workspace | Hash a lawful original Cod4 install; record manifest and licenses | map load/live run | yes for runtime claims |
| M2-C4-04 | CoD4x | deterministic Pmove/trace fixtures | core is in assembly, no fixture corpus | Record input `pmove_t`, `usercmd_t`, map coordinates and expected trace/state; compare build output | movement/collision semantics | no for static comparison; yes for parity |
| M2-C4-05 | CoD4x | per-symbol audit of 110 asm files | volume, no automated semantic oracle | Build symbol table by domain; disassemble/dispatch and map C callers to asm callees | game/world/vehicle/weapon | no for first cross-check; yes for complete audit |
| M2-C4-06 | CoD4x | real OOB/netchan/RCon/WebAdmin captures | no server/client run | Use isolated loopback environment; capture UDP, TCP RCON, HTTP and hash configs | D/E/F/N/O | no for source comparison; yes for protocol equivalence |
| M2-C4-07 | CoD4x | WebAdmin reachability decision | startup call commented while `sv_webadmin` exists | Run a build with each branch separately and record routes/auth | N/O | no |
| M2-C4-08 | CoD4x | trusted config/update provenance evidence | remote globalconfig and autoupdate path found; signature verification not established | Capture TLS chain, payload signature/checksum and failure behavior | O/Q | no for server architecture; yes for secure operation |
| M2-C4-09 | CoD4x | plugin ABI loading and lifecycle tests | no build; 14 plugins present but not exercised | Build one minimal plugin, load/unload, invoke each relevant callback and capture crash behavior | P | no for architecture; yes for plugin claims |
| M2-C4-10 | CoD4x | test execution evidence | `tests.c` delta bodies commented; CI no test step | Add isolated tests or provide external harness and logs | R | no for static comparison; yes for coverage claim |
| M2-IW-01 | IW4X | all 16 submodule commits checked out | repository has uninitialized gitlinks | `git submodule update --init --recursive` at the recorded superproject SHA in a fresh checkout | build/assets/protobuf/security | yes for build |
| M2-IW-02 | IW4X | generated `version.h/.hpp` | premake buildinfo not run | Run `generate.bat`/premake in isolated tree and retain output | A/R | yes for build |
| M2-IW-03 | IW4X | built x86 `iw4x.dll`, solution and build log | no Visual Studio/premake build performed | Use pinned VS/MSVC x86 toolchain, submodules and reproducible build script | B/R | yes for runtime |
| M2-IW-04 | IW4X | exact matching MW2/IW4 host binary with SHA | `iw4x.exe` and `iw4mp.exe` candidates exist but address match is unproven | Identify retail host by version/SHA and verify the expected fixed addresses; preserve a legal copy | A/H/I/J/K/L | yes for host claims |
| M2-IW-05 | IW4X | host disassembly/address map | host not identified; source only wraps addresses | Produce function/field map for every used address and compare with `Structs.hpp` asserts | H/I/J/K/L | no for extension architecture; yes for server reconstruction |
| M2-IW-06 | IW4X | `iw4-open-formats` source and asset parser tests | submodule absent | Initialize the recorded submodule; build parser; parse `clipMap`, `MapEnts`, FF and CFG | G | no for static comparison; yes for asset format |
| M2-IW-07 | IW4X | rawfiles manifest mapped to source/runtime purpose | 1.03 GB assets not individually classified | Extend inventory with semantic labels: FF, GSC, ENT, IWD, model, audio, binary, config, source fixture | G/Q | no for first cross-check; yes for asset audit |
| M2-IW-08 | IW4X | wire captures from one exact host build | no build/run and no host lock | Capture OOB auth, gamestate, snapshot and disconnect; record host SHA and DLL SHA | E/F/K | no for source comparison; yes for protocol equivalence |
| M2-IW-09 | IW4X | RCon and HTTP E2E evidence | no build/run; private hash auth route only source-inspected | Run loopback server, test auth failure/success, rate limits, file hash and path traversal cases | N/O | no for architecture; yes for service claims |
| M2-IW-10 | IW4X | Session/Node/Party behavior with actual macro configuration | `DISABLE_SESSION` is default; no build variant matrix | Build default and session-enabled variants in separate dirs; capture protocol and logs | M/Q | no |
| M2-IW-11 | IW4X | host-version/ownership proof for fixed-address hook safety | no ASLR/version/address verification | Record module base, image SHA, PE metadata and address bytes before/after hooking | A/H/I/J/K | no for design comparison; yes for host safety |
| M2-IW-12 | IW4X | crash/security regression corpus | Huffman, auth, RCon, download and deferred packet paths have no execution evidence | Build isolated harness and fuzz malformed lengths, duplicate keys, negative ACK, oversized/partial packets | O/R | no for first pass; yes for production readiness |
