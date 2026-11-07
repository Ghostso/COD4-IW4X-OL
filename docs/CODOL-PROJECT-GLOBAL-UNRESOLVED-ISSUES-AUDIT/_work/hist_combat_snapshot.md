# Historic corpus audit — COMBAT / SNAPSHOT / GAMESTATE / USERCMD / WEAPONS / MOVEMENT / BOT-MATCH

Scope: root `COMBAT_*.md`, `COMBAT_SERVER_*.md`, `V0_1_*.md`, the named `HANDOFF_*` files,
`CONSUMER_CHAIN_FINDINGS_20261016.md`, `ENTRY_DUMP_20261016_FINDINGS.md`,
`P0_CLSSTATE_WRITER_AND_DISPATCHER_20261015.md`, `OFFLINE_BINDING_REPLAY_*.md`,
`PROGRESS_20261017.md`, `NEXT_PHASE_PLAN.md`,
`CODOL_SERVER_319_20261021\docs\*.md` + `CODOL_SERVER_319_20261021\HANDOFF_20261022_PAUSE.md`,
the five `CODOL-*` round-report dirs, `CODOL-Combat-Server-v0.1\*`,
`FIRINGRANGE-BRINGUP-VERIFY-20261015\*`, `CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\*`
(read at summary/verdict level), `run_codol_001\runs\*\RESULT.md|evidence\*.md`,
`_weapon_table_20261025\*`, `_e1_regression` (index only), `_map_extract` (file list),
`_rev_analysis` (file list), `_t2_*_evidence` (logs only).
`REVERSE_ENGINEERING_COMPLETE.md` (387 KB) skimmed by heading search only — no
combat/snapshot section headings were found by that search.

Audit date: 2026-10-29. All quotes verbatim. Paths relative to
`D:\BaiduNetdiskDownload\使命召唤OL\`.

**Discipline note.** This corpus is an *errata chain*: 2026-10-23/24/25 reports routinely
refute 2026-10-22 reports, and 2026-10-26..28 root `docs\` reports refute earlier room/battle
conclusions. Where that happens the later report is recorded as status and the earlier claim as
OBSOLETE/CONTRADICTORY. Established facts listed in the task brief are **not** re-recorded as
new issues; they appear here only where a document still asserts the opposite.

**Evidence-tier legend** (used in "Proven vs claimed"): `impl` = implemented, offline-tested ·
`simclient` = tested against a simulated/e2e client · `official` = real 3.19 client observed ·
`doc` = report assertion only.

---

## 1. Master table

| # | Issue | Primary evidence | Status | Proven vs claimed | Superseded / later evidence |
|---|---|---|---|---|---|
| 1 | EngineBindings host-image gate: expected `SizeOfImage 0x0E5D6000`, actual client `0x0E659000` | `COMBAT_SERVER_BLOCKERS.md` §0/§1 | BLOCKED | official (3 runs) | — |
| 2 | Which of the three silent `return false` branches fires is indistinguishable | `COMBAT_P0_ENGINE_BINDING_ANALYSIS.md` §1.3/§1.5 | OPEN (unobservable) | doc + code | — |
| 3 | 75 in-`bind()` byte-prefix guards never executed on any real target | `COMBAT_P0_ENGINE_BINDING_ANALYSIS.md` §1.4 | UNVERIFIED | doc | — |
| 4 | Unpacked `out.exe` (`044c396c…257f9`) absent from machine → route R-A impossible | `COMBAT_SERVER_RECOVERY_BASELINE.md` §1.4 | BLOCKED | official scan | — |
| 5 | Deployed plugin stale: build `DBA7273A…` ≠ deployed `6D493B82…` | `COMBAT_SERVER_BLOCKERS.md` §4 | OPEN | hash ×2 | — |
| 6 | Deployed DLL's `bind()` machine code unverifiable (LTO, no PDB/CodeView) | `COMBAT_P1_ARTIFACT_CONSISTENCY.md` L25/L137 | UNVERIFIED | doc | — |
| 7 | Backend `ConfigureSession` descriptor bytes never obtained; 28960 never listened | `COMBAT_SERVER_BLOCKERS.md` U5 / §2.3 | BLOCKED | official (port logs) | — |
| 8 | Frida cannot attach to the real client (0 successes) | `COMBAT_SERVER_BLOCKERS.md` B8 | BLOCKED | official (2 failures) | — |
| 9 | 9 plugin-only files, 31,953 lines, zero test coverage | `COMBAT_SERVER_RECOVERY_BASELINE.md` §4.2 | OPEN | doc | — |
| 10 | RVA/guard counting conflict 145/146/170 and 82/66/78-79 | `COMBAT_SERVER_BLOCKERS.md` §6 W-2/W-3 | CONTRADICTORY | doc | `COMBAT_P0_ENGINE_BINDING_ANALYSIS.md` §1.7 reconciles ("82 is `std::equal(` count") |
| 11 | `E3823FD6…F37B` artifact attribution unresolved (4 mutually exclusive claims) | `COMBAT_SERVER_BLOCKERS.md` W-4 | OPEN | doc | — |
| 12 | Original engine "battle/session create" fn, original `NET_Frame`, gametype init entry all UNKNOWN | `COMBAT_SERVER_CALLCHAIN_MAP.md` §5 U-2/U-8 | OPEN | doc | — |
| 13 | L1 (ol-mod plugin) vs L2 (protocol-reverse) relation UNKNOWN; plugin never loaded in frozen lobby baseline | `COMBAT_SERVER_CALLCHAIN_MAP.md` §0.1/§5 U-1/U-5 | OPEN | doc | — |
| 14 | `mmbook accepted` must echo the client's own `(A,B)`; filler of reservation slot `+0x168/+0x16C` not located | `COMBAT_V0_1_NEXT_001_BLOCKER.md` §2.5, `…008_IMPLEMENTATION_GATE.md` §3 | OPEN (single-point gap) | doc | — |
| 15 | Gate 1 `[esi+0x278]` semantics/trigger event unknown | `COMBAT_V0_1_NEXT_002_U1.md` U1-a..d | OPEN | doc | — |
| 16 | `accepted` body byte layout UNKNOWN (4 envelope variants refuted) | `COMBAT_V0_1_NEXT_002_…008` gates; `…007` §3 | OPEN | doc | — |
| 17 | `6/14` booking response frame format UNKNOWN (L2); range-envelope answer → 9/9 disconnects | `COMBAT_SERVER_BLOCKERS.md` Q1, `COMBAT_SERVER_CALLCHAIN_MAP.md` §2 | BLOCKED | official (9/9) | — |
| 18 | "service 71/3 is the channel-subscription blocker" — refuted; 71 is telemetry | `CODOL_SERVER_319_20261021\docs\SERVICE71_CLIENT_REVERSE_20261024.md` §14.1 | OBSOLETE (earlier claim) | doc + static | same doc, §14 |
| 19 | Room service is 4 (`4/13`), not 11; old `service==11` mapping produced UNMAPPED ACK | same doc §14.5 | CONTRADICTORY → corrected | static | same doc |
| 20 | `102/7` playerdata batch read answered with all-zero fields → match selection cleared | `docs\BATTLE_CONNECT_DIVERGENCE_20261028.md` §3 | OPEN (suspected root cause) | official correlation | — |
| 21 | Room push route key is `(roomId_hi, roomId_lo)`, not `(service,task)`; two prior rounds read all-zero | `docs\ROOM_PUSH_CHANNEL_WRONG_20261028.md` §1-§2 | CONTRADICTORY → corrected | official memory | — |
| 22 | Room push envelope: `build_room_push` writes `08 08` (kind 8) where client uses `08 0b` (kind 11) | `docs\ROOM_PROTOCOL_COMPLETE_20261028.md` §二 | CONTRADICTORY → corrected | official memory | `ROOM_PUSH_SPEC_FIX_RUN_20261028.md` applies fix, still no client response |
| 23 | `dwRoomMessage*::serialize` bitstream is not the wire format on `11/4` (0/160 bit offsets matched) | `docs\ROOM_MSG_NOT_BITSTREAM_20261028.md` §一 | CONTRADICTORY → corrected | official samples | — |
| 24 | Room-push spec fix applied and pushed, client still shows no visible effect | `docs\ROOM_PUSH_SPEC_FIX_RUN_20261028.md` §三 | OPEN | official | — |
| 25 | BOT-room `mmstart` carries no `map`/`g_gametype` → client never connects to 28960 | `docs\BATTLE_ZERO_RX_ROOT_CAUSE_20261028.md` §一 | OPEN (root cause found) | official | — |
| 26 | Playlist "index vs official id" fallback bug (`playlist 50→148`, `37→123`) | same doc §二 | OPEN | doc | — |
| 27 | Only 8 of 57 runs ever produced a battle event; all on 2026-10-26 | `docs\BATTLE_CONNECT_DIVERGENCE_20261028.md` §一 | OPEN | official correlation | — |
| 28 | Ready button: earlier "AS_* not implemented" verdict was wrong; the path is `dwRoomMatch`'s own event system | `docs\READY_BUTTON_ROOT_CAUSE_CLOSED_20261028.md` §一 | CONTRADICTORY → corrected | official memory | — |
| 29 | `ui_mp.ff` (29,224,001 B) is encrypted → Scaleform behaviour unreachable | `docs\UI_FF_ENCRYPTED_20261028.md` §二 | BLOCKED | doc | — |
| 30 | `dwRoomMessage*` type constants: 39 of 41 constructors yield `?` | `run_codol_001\runs\BOT_ROOM_20261028_194000\work\room_msg_types.md` | NOT_IMPLEMENTED | official memory | — |
| 31 | Room-channel table `0xE376C08` read via `(service,task)` returned all zeros; only roomId route confirmed | `work\push_route_table.md` | CONTRADICTORY | official memory | `ROOM_PUSH_CHANNEL_WRONG_20261028.md` |
| 32 | Probe used absolute VA not RVA → addresses invalid across processes | `docs\PROBE_FAILED_VA_DRIFT_20261028.md` | CONTRADICTORY → corrected | official | — |
| 33 | ACE blocks `ReadProcessMemory` from t+0.01 s; probe window and `createRoom` (80–100 s) do not overlap | `docs\ACE_BLOCKS_EVERYTHING_20261028.md`, `docs\PROBE_BLOCKED_BY_ACE_20261028.md` | BLOCKED | official | conflicts with early-handle claim (§detail) |
| 34 | Client never sends `bit0` (fire) after entering map | `CODOL_SERVER_319_20261021\HANDOFF_20261022_PAUSE.md` §1.3 | OPEN | official | — |
| 35 | `idx61` = constant 2047 vs dynamic `on_ground?2046:2047`; 2046 caused flight mode + ADS loss | `docs\SNAPSHOT_FIELD_DIFF_20261024.md` §12.2 | PARTIALLY_RESOLVED | official (both arms) | — |
| 36 | `idx20` = `aiming?0x10:0`; `0x10` may be `PMF_SPRINTING` and could block ADS — unattributed | same doc §12.3 | OPEN | doc (hypothesis) | — |
| 37 | Server-side snapshot position never applied by client (3 coords × 2 rates) | `HANDOFF_20261025_BINARY_BISECT.md` §13 | OPEN | official (4 runs) | — |
| 38 | TX snapshot buffer 512 B vs retail 7000–15000 B → ≤~10 entities | `HANDOFF_20261025_BINARY_BISECT.md` §16.4 | OPEN | doc + code | — |
| 39 | Entity section accepted but invisible (`model_index` always 0; numbers 0..7 collide with client slots) | §17.3 | OPEN | official (ack rate unchanged) | — |
| 40 | Entity section "client actually parses the bits" never proven | §17.5 | UNVERIFIED | doc | — |
| 41 | Fields 62/83/107/162 written only by us, no reference basis | `docs\SNAPSHOT_FIELD_DIFF_20261024.md` §7 | OPEN | doc | — |
| 42 | `idx21-24`: old-style event array vs weapon-slot; references contradict | §8 | CONTRADICTORY | doc | — |
| 43 | `index(84)` marker: Python says required, CSV (working) omits | §8 | CONTRADICTORY | doc | — |
| 44 | `idx219` unconditional vs gated | §8 | CONTRADICTORY | doc | — |
| 45 | `num_fields` 220 vs 85 across references | §8 | CONTRADICTORY | doc | — |
| 46 | Phase 3 "DONE / byte-exact 141 B" | `docs\PHASE3_SNAPSHOT_CODEC_DONE_20261023.md` §3 | OBSOLETE | doc | `INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md` → `PARTIAL`; §15 of BINARY_BISECT |
| 47 | Codecs `-57/-58/-97/-100/-101/-102` formulas unimplemented; 39 further codecs unmodelled | `docs\CODEC_SPEC_20261022.md` §7 | NOT_IMPLEMENTED | doc | — |
| 48 | Compressed-float formula (`-100`, and `bits==0` mantissa branch) TODO | `docs\CODEC_SPEC_20261022.md` §2.2/§2.16 | OPEN | doc | — |
| 49 | `bigStruct 0xDA8520` read with wrong column order → `-8/-16` are `int8/int16`, not codecs | `docs\CODEC_SPEC_20261022.md` §5/§6 | PARTIALLY_RESOLVED | doc | self-corrected in §6 |
| 50 | `0xDA4608` entry count 63 vs 64 ambiguous | `docs\INMATCH_TABLE_INDEX_20261022.md` §1 | OPEN | doc | — |
| 51 | `entityState` = 24 netField entries, but the struct carries 63 fields | `docs\PHASE4_FIELD_SEMANTICS_DONE_20261023.md` §2 vs project memory | CONTRADICTORY | doc | project memory (`codol-entity-delta-reader-671170`) says 63 |
| 52 | playerState 36 unnamed fields; entityState 7 unnamed | `docs\PHASE4_FIELD_SEMANTICS_DONE_20261023.md` §6 | OPEN | doc | — |
| 53 | 18 array-element layouts × 64 fields never semantically named | `docs\INMATCH_ARRAY_ELEMENT_VARIANTS_20261023.md` | OPEN | doc | — |
| 54 | `playerstate-motion-trace.json` is not live capture; cannot decide XOR-vs-raw | `docs\SNAPSHOT_FIELD_DIFF_20261024.md` §5.2 | OPEN | doc | — |
| 55 | `CODEC_SPEC` §8 asserts run encoding "should be table-width 7 bits" | `docs\CODEC_SPEC_20261022.md` §8 | CONTRADICTORY | doc | `HANDOFF_20261025_BINARY_BISECT.md` §8 (4-bit fixes it) |
| 56 | `BITORDER` §5 calls hard-coded 4-bit "历史实现错误" | `docs\BITORDER_6701D0_20261022.md` §5 | CONTRADICTORY | doc | same §8 of BINARY_BISECT |
| 57 | FAT reassembly implemented, offline 7/7, never triggered live | `HANDOFF_20261024_FAT_REASSEMBLY_PLAN.md` §2/§4.5 | UNVERIFIED | impl only | `HANDOFF_20261025_BINARY_BISECT.md` §8.2: "实机从未被触发" |
| 58 | RELIABLE fragment ack (`0xA0000000`) has no live evidence | `HANDOFF_20261024_FAT_REASSEMBLY_PLAN.md` §4.4 | UNVERIFIED | doc | — |
| 59 | Server-side fragmentation still CoD4x layout (never fires) | same §4.2 | OPEN (latent) | code | — |
| 60 | `gamestate` trailing 44 bytes unparsed | `docs\PHASE2_GAMESTATE_CONFIGSTRING_DONE_20261023.md` §6 | OPEN | impl (roundtrip only) | — |
| 61 | configstring `index_bits()` incremental-index encoding unknown | `CODOL_SERVER_319_20261021\HANDOFF_20261022_PAUSE.md` §5 | OPEN | doc | — |
| 62 | Client acceptance of rebuilt gamestate/configstring unproven past byte round-trip | `docs\PHASE2_…DONE_20261023.md` §5 | UNVERIFIED | impl | — |
| 63 | Dynamic weapon index has no static table (client assigns in `CL_ParseGamestate` 2nd pass) | `_weapon_table_20261025\codol_dynamic_index_model.md` §"为什么没有静态全表" | NOT_IMPLEMENTED | official | — |
| 64 | `firstDynamicWeapon` differs per map (1224 vs 1147) → formula not universal | same doc §"实测锚点" | OPEN | official | — |
| 65 | Minimap empty: `northyaw` absent from main configstring; `compass_map_*` needs map bounds | `HANDOFF_20261022_PAUSE.md` §1.5 | OPEN | official memory | — |
| 66 | Official 3.19 usercmd read function not symbol-bound | `docs\PHASE5_USERCMD_RELIABLE_DONE_20261023.md` §6 | OPEN | doc | — |
| 67 | Jump button bit conflict: `0x400` (fixed) vs `0x2`; `PMF_JUMPING` 0x4000 vs 0x2000 | `PROGRESS_20261017.md` §二.3 vs §11.6/§12.3 | CONTRADICTORY | official (0x400 fixed) | — |
| 68 | Button `bit29` in real usercmds unexplained | `HANDOFF_20261022_PAUSE.md` §1.3 | OPEN | official | — |
| 69 | Movement applied per server tick not per input (BLK-PERINPUT-TIMING) | `CODOL-BATTLE-SERVER-GAMEPLAY-003\00_INDEX.md` §6 | OPEN | doc | — |
| 70 | `usercmd.weapon` always 0 → no weapon-selection channel | `HANDOFF_20261022_PAUSE.md` §1.3/§3.2 | OPEN | official | — |
| 71 | `codol_battle_service_bind_world` described as already wired by Phase 7/closure rounds | `INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md` §"静态闭合轮" | OBSOLETE (opposite of fact) | doc | `HANDOFF_20261025_BINARY_BISECT.md` §3/§16 |
| 72 | C# v0.1: no collision, no hitscan, no damage, no death/respawn | `CODOL-BATTLE-SERVER-GAMEPLAY-003\00_INDEX.md` §6 | NOT_IMPLEMENTED | impl (none) | — |
| 73 | clipMap array boundaries (cLeaf/cLeafBrushNode/aabbTrees/cmodels/brushes) unclosed; AABB 64³ approximation | `HANDOFF_20261022_PAUSE.md` §"未完成" | OPEN | impl (approx) | — |
| 74 | `coop_train` has zero up-facing planes and no brush covers spawn (48,−572) | `docs\CLIPMAP_EXTRACTION_20261026.md` §"真正的问题：覆盖范围" | OPEN | official zone data | — |
| 75 | `mp_firingrange` clipmap: 1104 floor planes verified, `cbrush_t`/`brushBounds` tables not located | `docs\MP_FIRINGRANGE_CLIPMAP_20261026.md` §三/§下一步 | OPEN | official zone data | — |
| 76 | `codol_ground_z = -116` hard-coded → `on_ground` always true → dynamic `idx61` degenerates | `docs\SNAPSHOT_FIELD_DIFF_20261024.md` §12.2 | OPEN | code | — |
| 77 | HUD/behaviour gaps: `G_Damage` missing 9 deps; `g_run_frame_for_entity` missing; PVS unrecovered; SD round machine incomplete; world-model-scale producer unlocated | `COMBAT_SERVER_HISTORICAL_FINDINGS.md` §3.10 | NOT_IMPLEMENTED | doc | — |
| 78 | C# line: adding `pm_type/eFlags/otherFlags` and field 54/83/217 all broke the snapshot | `PROGRESS_20261017.md` §三/§13.5 | OPEN (negative result) | official | — |
| 79 | C# line: `noclip` unexplained — client zeroes `pm_flags`, `vel=(0,0,0)`, origin follows server | `PROGRESS_20261017.md` §13.4 | OPEN | official | — |
| 80 | `hint==2` second-pass field writing never implemented | `PROGRESS_20261017.md` §11.3/§三 | NOT_IMPLEMENTED | doc (ref impl) | — |
| 81 | Runtime `WeaponDef` layout unverified; `+0xBB4/+0xBCC/+0xBF0` disproved; `+0x810..0x824/+0xAC0` unverified | `docs\PHASE7_WEAPONATTACH_REVERSE_BOUNDARY_20261023.md` §"最终布局证据校正" | UNVERIFIED | doc | — |
| 82 | WeaponAttach: 545 string/resource records skipped; 168 assets have unresolvable shared slots | same doc §"What remains explicitly unclosed" | OPEN | impl (scalars only) | — |
| 83 | Scalar coverage reported twice with different numbers (172/879 vs 94 records/44 assets) | `PHASE7_WEAPONATTACH…` vs `INMATCH_COMPLETENESS_GAP_MATRIX…` | CONTRADICTORY | doc | — |
| 84 | Recoil / spread / ADS-accuracy formulas missing | `PHASE7_WEAPONATTACH…` | NOT_IMPLEMENTED | doc | — |
| 85 | Projectile/explosive fields unnamed (fuse/radius) | `INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md` 第二轮 | NOT_IMPLEMENTED | doc | — |
| 86 | Hitbox geometry / armor / penetration missing | same | NOT_IMPLEMENTED | doc | — |
| 87 | `fmj_base` `0xE78` penetration semantics unknown | `PHASE7_WEAPONATTACH…` | OPEN | doc | — |
| 88 | Training map has 333 decorations + exactly 1 actor → "no BOT" is by design | `HANDOFF_20261025_BINARY_BISECT.md` §16.3 | RESOLVED (explanation) | official zone data | — |
| 89 | actor/vehicle/turret/loot behaviour unimplemented (generic lifecycle only) | `INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md` | PARTIALLY_RESOLVED | impl | — |
| 90 | Deliberate map-name mismatch between Lobby `mmstart` and battle server default map is the only working form | `HANDOFF_20261024_DYNAMIC_CLOSURE.md` §2.2 | OPEN (fragile) | official | — |
| 91 | All C# rounds (Lifecycle/Reconnect/Entity/Gameplay/Integration) are server-self-certified; real client never connected | `V0_1_ACCEPTANCE_MATRIX.md` AC-4/AC-7 | NOT_RUN (official) | impl only | — |
| 92 | Reconnect: normal-client-disconnect semantics unknown (`BQ-09`); `\xuid\` unverified self-assertion | `CODOL-COMBAT-RECONNECT-STATE-001\00_INDEX.md` §8 | OPEN | impl + doc | — |
| 93 | Entity table residuals U-1..U-7 (DropSession residual, no lock, snapshot reads cached `s.Player`, MaxClients not hot-changeable, delta baseline unknown, client `0x02` dispatch unlocated) | `CODOL-BATTLE-SERVER-ENTITY-001\00_INDEX.md` §6 | OPEN | impl | — |
| 94 | `test_netchan` never feeds fragments back into `codol_netchan_process()` | `HANDOFF_20261024_DYNAMIC_CLOSURE.md` §3.3 | PARTIALLY_RESOLVED | impl | `HANDOFF_20261024_FAT_REASSEMBLY_PLAN.md` §2 adds 7 FAT cases |
| 95 | Workspace has no version control; working kits diverge and keep growing | `_work\source_audit.md` S-02/S-03 (sibling audit) | OPEN | verified | — |
| 96 | Protected-file drift `marketplace_store.py` (50022/`e44358f0` vs 46226/`28b4a1be`) | `run_codol_001\runs\BOT_ROOM_20261028_182126\evidence\BASELINE_MARKETPLACE_INVESTIGATION.md` | OPEN (pre-existing) | hash ×3 | — |
| 97 | Build reproducibility: `codol_battle_server.exe` cannot be re-derived from the CMake targets | `_work\source_audit.md` S-04 | OPEN | verified | — |
| 98 | Combat handshake/state verification is "simulated client" only; `e2e_client.py` is an independent implementation, not the official client | `CODOL_SERVER_319_20261021\docs\STAGE1_CRYPTO_DONE.md` §五 | UNVERIFIED (official) | simclient | — |

**Count: 98 distinct issues.** (Master table only; detail blocks below are grouped and numbered to
match. Issues 18/19/21/22/23/28/31/32/46/55/56/71/83 are recorded because a document in scope
still asserts the opposite of a later-corrected or established fact.)

---

## 2. Detail blocks

### A. Engine binding / ol-mod plugin line

**1. Host-image identity gate.** `COMBAT_SERVER_BLOCKERS.md` §0: "宿主映像身份门禁：`EngineBindings::bind()` 要求 `SizeOfImage==0x0E5D6000`（且 `TimeDateStamp==0x6096930A`），实测客户端为 `0x0E659000`". Status BLOCKED. Proven: three real runs all emit only `[combined/game-server] engine binding failed`, with no stage line. Claimed: the gate is the sole blocker (also: no stage log ⇒ silent branch). Superseded by: nothing; still the top-level blocker on the ol-mod line.

**2. Indistinguishable silent branch.** `COMBAT_P0_ENGINE_BINDING_ANALYSIS.md` §0 row 2: "**是。** 二者与 `nt->Signature` 一起位于 `EngineBindings.cpp:3662-3664` 的**同一个 `if`**，短路 `||`，**不记录是哪一项失败**". Status OPEN/unobservable. Two minimal evidence items named E-2 (runtime PE header) and E-3 (runtime bytes at `0x0FEA20`, `0x8371A`) are still uncollected.

**3. Guards never executed.** Same doc §1.4 and `COMBAT_SERVER_BLOCKERS.md` §1.6: "**不得**认定全部 145/146 个 RVA 或 82 条守卫失效（**它们从未在真实目标上执行过一次**）". Status UNVERIFIED. Note the report itself reconciles the count: "`bind()` 内实际守卫 = 75 = 9 具名 + 66 链。'82'是文件内 `std::equal(` 总出现次数". This is the correct reading and supersedes the older 82-guard claim.

**4. `out.exe` absent.** `COMBAT_SERVER_RECOVERY_BASELINE.md` §1.4: "本轮独立有界扫描（根：`E:\CODOL_SANDBOX`、`C:\Games`、`F:\桌面\ol`、`D:\BaiduNetdiskDownload\使命召唤OL`）**未发现任何 out.exe**，也**未发现任何 SizeOfImage = 0x0E5D6000 的 PE 文件**". Status BLOCKED. `NEXT_PHASE_PLAN.md` §1 A-1 reframes this as "不再适用的文档前置条件" for the project as a whole, but it remains a hard prerequisite (A/B-1) for the `EngineBindings` path.

**5. Stale deployment artifact.** `COMBAT_SERVER_BLOCKERS.md` §4.2: "**5 个运行时制品中只有战斗服务器本体是旧的。** 当前源码树对 `src/game_server` 的任何修改**从未落到沙箱**。任何"改源码后直接跑"的验证都是无效的。"

**6. Deployed `bind()` machine code unverifiable.** `COMBAT_P1_ARTIFACT_CONSISTENCY.md`: "| **V5** | 部署 DLL 中 `bind()` 的**机器码** ↔ 当前源码编译结果 | **UNKNOWN** | 无 PDB（全树 0 个）…**LTO 已启用**". Consequence stated on L28: the "no stage log ⇒ silent branch" inference survives because the TU source is identical, but machine-code equivalence cannot be shown.

**7–8. ConfigureSession / Frida.** `COMBAT_SERVER_BLOCKERS.md` §0 Q3/Q4 and U5. Both are BLOCKED official results. Frida: "`ProcessNotRespondingError` … **真实客户端附加成功 0 次**".

**9. Untested plugin files.** `COMBAT_SERVER_RECOVERY_BASELINE.md` §4.2: "9 个插件专属文件（31,953 行） … ❌ 无". Also `COMBAT_SERVER_EVIDENCE_INDEX.md` CS-C11.

**10. Counting conflicts.** `COMBAT_SERVER_BLOCKERS.md` §6 W-2/W-3 lists 145/146/170 and 82/66/78-79 side by side without adjudication; `COMBAT_P0_ENGINE_BINDING_ANALYSIS.md` §1.7 resolves each number's provenance ("170 … 对当前文件不可复现 … 登记为冲突"). Status stays CONTRADICTORY in the older doc; the newer doc is authoritative.

**11. Artifact attribution.** `COMBAT_SERVER_BLOCKERS.md` W-4: four mutually exclusive claims for `E3823FD6…F37B`, "**未裁定**；不采用、不重写".

**12–13. Missing original-engine entries and line relation.** `COMBAT_SERVER_CALLCHAIN_MAP.md` §5: "| U-2 | 原版引擎"战斗/会话创建"函数（`Createserver` 之外） | L1 战斗创建入口 |"; "| U-5 | ol-mod 线与协议逆向线的接口关系 | 全图 |". §4.1 adds: "L1 **从未在冻结大厅基线中加载过**".

### B. Lobby → battle booking and room protocol

**14. `mmbook accepted` must echo `(A,B)`; filler unknown.** `COMBAT_V0_1_NEXT_001_BLOCKER.md` §2.5.2: "客户端在 mmbook 请求里用 `"mmbook %d %s %d"` 送出它自己的预约 id 对 (A, B)；服务端的 `mmbook accepted` 推送必须把这**同一对 (A, B) 原样回传**". Then §3 U2: "预约项 `+0x168/+0x16c` 又由**谁**填充". Eight successive gate documents (`NEXT_002` … `NEXT_008`) restate the same single gap; `NEXT_008` §3 reduces it to "缺口 U2-G1⁽⁸⁾ —— **`21/5` 响应体的原始字节**". Status OPEN — repeatedly narrowed but never closed.

**15. Gate 1 `[esi+0x278]`.** `COMBAT_V0_1_NEXT_002_U1.md` table: "U1-a … `[mk+0x278]` 的**业务命名**（无字符串/UI/日志直接引用该字节…) | **UNKNOWN**". U1-b/U1-c (trigger event type) also UNKNOWN. Consequence in `NEXT_001` §3: "候选 ① 仍无法排除" — two candidate blockers produce identical symptoms.

**16. `accepted` body layout.** `COMBAT_V0_1_NEXT_008_IMPLEMENTATION_GATE.md` §2: "**⇒ accepted 体布局 = UNKNOWN。**". `NEXT_007` §5 notes "NEXT-002 已否证四种 envelope 改法". `NEXT_011` §2: "服务端地址交接链的完整性 (大厅 -> 战斗) | **未验证** | 只有对象内出现的地址, 无后续交接帧".

**17. Booking frame format (L2).** `COMBAT_SERVER_BLOCKERS.md` §0 Q1: "`6/14 mmbook/mmstart` booking 应答帧格式 UNKNOWN | 协议逆向线 | 阻断 L2 的 Lobby→Battle | 9/9 断连实测". Status BLOCKED.

**18. service 71 mis-identification — OBSOLETE.** `SERVICE71_CLIENT_REVERSE_20261024.md` §14.1: "**Service 71 是腾讯 Demonware 的客户端遥测/日志上报通道**（Telemetry / EventLogger）… **真正的频道订阅与房间 RPC 根本不是 71 号服务！**". Earlier sections of the same document (§1–§13) build the 71/3 blocker interpretation, then §14 refutes it. Recorded because §1–§13 remain in the corpus; the status of the whole document is contradictory and §14 governs. Superseding: `PHASE2`/`P0_CLSSTATE` docs never depended on 71/3; the room/battle blockers are elsewhere.

**19. Room service is 4, not 11.** Same doc §14.5: "客户端发出的房间创建是 `Service 4, Task 13`… 既有代码按 ol-mod 写成 `service == 11`，导致实机收到的 `4/13` 成了 UNMAPPED 空 ACK". This is a concrete instance of the ol-mod mismatch warned about in `AGENTS.md`.

**20. `102/7` all-zero playerdata.** `docs\BATTLE_CONNECT_DIVERGENCE_20261028.md` §3: "**把 50 个字段全部回 0，等于告诉客户端"你什么都没选"** —— PvE 关卡、PvP 模式、根索引全被清零。 ⇒ 这很可能就是 10-27 之后客户端不再连战斗服的原因。" Status OPEN (correlation, one candidate cause). Superseding: `BATTLE_ZERO_RX_ROOT_CAUSE_20261028.md` offers a different root cause (mmstart without `map`); the two documents are not reconciled.

**21. Room route key.** `docs\ROOM_PUSH_CHANNEL_WRONG_20261028.md` §1: "真实语义是：房间信道的路由键 = **roomId 拆成的两个 dword**（高32 / 低32）"; §2 table explicitly marks the earlier "0x82E1458 是 type→类注册表" reading "**错**". Status: earlier claim OBSOLETE, corrected reading backed by two independent snapshots (`snap_003`/`snap_004`).

**22. Envelope kind.** `docs\ROOM_PROTOCOL_COMPLETE_20261028.md` §二: "| `build_room_push` | **1 字节** | 错（第 1 字节写 `08 08`=kind 8，客户端是 `08 0b`=11） |". Superseded by the fix itself (`ROOM_PUSH_SPEC_FIX_RUN_20261028.md`), but see #24.

**23. Bitstream is not the wire format.** `docs\ROOM_MSG_NOT_BITSTREAM_20261028.md` §一: "对客户端 `11/4` 上行的每一条批次，在**前 160 个 bit 偏移**上逐一尝试 … **全部无匹配。**". §二: "`dwRoomMessage*::serialize` 那套位流格式 … **不是房间消息在 11/4 通道上的线上格式**". Status: earlier bitstream work (`build_roominfo_payload` etc.) is OBSOLETE for the uplink; §三 records the confirmed container `u32 total | u8 flag | payload`.

**24. Fix applied, no effect.** `docs\ROOM_PUSH_SPEC_FIX_RUN_20261028.md` §三: "推送帧确实发出 … 客户端**无报错、无断连** … 上行 `11/4` 共 6 次，与之前完全相同的批次长度序列". Status OPEN — passing offline byte-equality did not change client behaviour; this is the same failure mode as the snapshot 141-byte case (reference equality ≠ usable).

**25. `mmstart` without `map`.** `docs\BATTLE_ZERO_RX_ROOT_CAUSE_20261028.md` §一: "**⇒ 客户端在没有确定目标地图时，不会去连战斗服。** 这是"进不了对局"的直接原因，与房间 UI 消息格式无关。" Status OPEN root cause with a stated counter-example (the 10-26 PvE entry that carried `map coop_train_mp_firingrange` and did connect).

**26. Playlist index/id confusion.** Same doc §二: "`playlist=50` / `playlist 37` **都不是官方 ID**（官方表 123 项里没有 37 和 50），而是**排序后列表的下标**". Consequence: the room asks for a different map set than the one the battle server was configured for.

**27. 8/57 runs.** `docs\BATTLE_CONNECT_DIVERGENCE_20261028.md` §一 table: "**A：带 `g_gametype`** | 25 | **8**"; "**8 轮成功全部在 2026-10-26。** 10-27 之后即使有 A 形态也全灭." Status OPEN. Note this is a *correlation* over 57 runs, not a controlled experiment.

**28. Ready-button verdict overturned.** `docs\READY_BUTTON_ROOT_CAUSE_CLOSED_20261028.md` §一: "**这个判断不完整。** 真相是：房间 UI **不是** `UiCpp*View` 那套 Scaleform 回调，而是走 `dwRoomMatch` 自己的事件系统." Earlier "AS_SetReadyState 类无 COL/vtable ⇒ 该功能没实现" is now OBSOLETE.

**29. `ui_mp.ff` encrypted.** `docs\UI_FF_ENCRYPTED_20261028.md`: `COD OL\main\ui_mp.ff`, 29,224,001 B, "文件整体加密". Consequence: the Flash binding of the ready button cannot be inspected; the ready path can only be inferred from runtime memory. BLOCKED.

**30. Room message type constants.** `run_codol_001\runs\BOT_ROOM_20261028_194000\work\room_msg_types.md`: every row's `type` column is `?` except two constructor hints. Status NOT_IMPLEMENTED — the wire type table for 39 of 41 classes was never recovered.

**31. Route table read via wrong key.** `work\push_route_table.md` records both entries as `service 0 / task 0 / handler 0x00000000`, i.e. an all-zero read. Superseded by #21. Keep because a naive `(service,task)` lookup would reproduce the same false "not registered" conclusion.

**32. VA/RVA drift in the probe.** `docs\PROBE_FAILED_VA_DRIFT_20261028.md`: "**所有运行时 VA 改用 RVA**". Status: corrected, but the affected run (`ONCE_20261028_220445`) produced no room-object evidence.

**33. ACE read block vs early-handle claim.** `docs\ACE_BLOCKS_EVERYTHING_20261028.md`: "**句柄抢到后 0.01 秒的第一次读取就已经 err=5，全程 240 秒从未恢复。**" It explicitly notes the conflict: "既有记忆 `codol-ace-blocks-debug-and-read` 说：早期句柄（t+15.39s）可读，`snap_003` 读到 1630MB / 0 失败块". `docs\PROBE_BLOCKED_BY_ACE_20261028.md` adds: "**窗口和事件时间不重叠**。这是本轮暴露的真正障碍：roomId 写入房间对象发生在 ACE 保护生效之后". Status BLOCKED; the two observations are from different builds/runs and are not reconciled — this is a genuine CONTRADICTORY pair in current documentation.

### C. Snapshot codec

**34. No fire bit after entering map.** `HANDOFF_20261022_PAUSE.md` §1.3: "**没有一帧含 bit0（开火）**… **结论：按键位定义正确，但客户端在进图后停止上报真实按键（卡在残留值）。**" Status OPEN. This is the reason FIRE/HIT/DAMAGE counts are 0 in every round, independent of the server's damage implementation.

**35. `idx61`.** `docs\SNAPSHOT_FIELD_DIFF_20261024.md` §12.2: "我们**恒定发 2046**… 而 2046 正是我们自己在 `HANDOFF_20261022_PAUSE.md` 里判定有害的那个值". Fixed then reverted. Current code (`src/battle/snapshot.c:435`) keeps `bw_scalar(&w, 2047u, 16)` with a comment explaining why. Status PARTIALLY_RESOLVED: the value is back to 2047, the mechanism (dynamic on_ground) remains blocked on real collision.

**36. `idx20`/ADS.** Same doc §12.3: "若 `0x10` 不是"开镜"位（CoD 系里 `PMF_SPRINTING` 恰好是 `0x10`），那持续 0x10 会让客户端以为一直在冲刺，**恰好会挡掉开镜**". Status OPEN — explicitly "尚未归因，必须单变量验".

**37. Position never applied.** `HANDOFF_20261025_BINARY_BISECT.md` §13: "**两个完全不同、相距数百单位的坐标（`355 1371 0` 与 `-44 -387 -83`），无论只发首帧还是每帧都发，人物位置都丝毫不受影响。**" Mechanism hypothesis (§13.1): missing clientInfo / entity roster so the client cannot identify the playerstate as "me". Status OPEN; this is why `omit=1` is the only working config.

**38. 512-byte TX buffer.** §16.4: "`src/battle/battle_service.c:  uint8_t snap[512], payload[520];`" and "零售快照是 **7000~15000 字节**". Verified in code. Status OPEN.

**39–40. Invisible entities.** §17.2/§17.3: ack rate 83.02 → 83.05/s with the entity section on — "包没被判废" — but "`model_index` 被 `codol_entity_alloc` 的 `memset` 恒置 0" and "号 0..7 是客户端自己的槽位号". §17.5 lists the still-required experiment: send a deliberately malformed entity segment and see whether ack breaks.

**41. Self-invented fields.** `docs\SNAPSHOT_FIELD_DIFF_20261024.md` §7: "三份参照都没有这三个字段…属于"没有任何依据的自造字段"". Fields 62/83/107/162 remain in `snapshot.c` because removing them changes total length away from the only known-working 103 B; §11.4 explains this is deliberate.

**42–45. Reference-internal contradictions.** Same doc §8 table: `num_fields` 220/220/**85**; `idx 21-24` weapon-slot vs old event array; `idx 83` write vs omit; `idx 219` gated vs unconditional; `index(84)` present vs absent. Status CONTRADICTORY, with the explicit conclusion: "'把我们的实现改成和参照逐字节一致'**不是**一个定义明确的目标".

**46. Phase 3 "DONE".** `docs\PHASE3_SNAPSHOT_CODEC_DONE_20261023.md` §1/§3: "状态：`DONE`（首帧黄金向量字节级一致）"; "byte_exact=True". Superseded: `INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md` same-day downgrade to `PARTIAL`; `HANDOFF_20261025_BINARY_BISECT.md` §15 shows the byte-exact rewrite stalls the client (`REFENCODER_20261024_1150` 141 B, "只到 `head=0x62`"). Recorded because the DONE heading survives in the corpus.

**47–48. Unimplemented codecs.** `docs\CODEC_SPEC_20261022.md` §7: "未实现（下一步）： - codec -57 / -58 / -97 / -100 / -101 / -102 的精确公式 - 其余 39 个 codec"; §2.2 for `bits==0`: "0 -> 5 bit + 5 bit（压缩浮点, 待定公式）". Status NOT_IMPLEMENTED. `SESSION_20261023_TABLE_MAP_AND_CODEC.md` §2.6 repeats the same list.

**49. `bigStruct` column order.** `docs\CODEC_SPEC_20261022.md` §5: "**没有 `-8` / `-16` 分支**… `bigStruct 0xDA8520` 里出现的 `bits=-8`(4 处) / `bits=-16`(9 处) **不是 codec**，而是把 `change_hint` 列误当成 `bits` 读出来的结果". §6 then retreats partially: "-8 = int8、-16 = int16（共 13 处）". Net status: ambiguous; the table's entry layout is still not authoritatively fixed.

**50. `0xDA4608` count.** `docs\INMATCH_TABLE_INDEX_20261022.md` §1: "表项数 63 或 64，需真实快照验证（不影响 indexBits=6）". Status OPEN but non-blocking. Same doc §3 corrects two earlier counts ("旧文档 … 「0xDA4608 = 9 条」——**错了**"; "`0xDA63E8` 曾被写成 87 项 … 实际 24 项").

**51. entityState field count.** `docs\PHASE4_FIELD_SEMANTICS_DONE_20261023.md` §2: "表：`0x00DA63E8`，字段数：`24`". Contradicts the established project fact that `entityState` carries 63 fields (`codol-entity-delta-reader-671170`: "顺带纠正项目 fixture：`entityState` 是 **63** 项不是 24"). Both statements refer to different objects — the *netField table* has 24 rows, the *struct* has 63 fields — but no document in scope states that distinction, so it is recorded as CONTRADICTORY (documentation defect).

**52. Unnamed fields.** Same doc §6: "playerState 未命名字段：36 项; entityState 未命名字段：7 项". Status OPEN, explicitly non-blocking.

**53. Array element semantics.** `docs\INMATCH_ARRAY_ELEMENT_VARIANTS_20261023.md` opens by saying the 18 layouts are exported as `{offset, bits, hint}` triplets; no field semantics are given anywhere in the corpus. `INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md` lists "实体数组变体语义" as still missing.

**54. Trace is not live.** `docs\SNAPSHOT_FIELD_DIFF_20261024.md` §5.2 quoting the file itself: "`"offline position branch trace; copy and security initialization omitted; not live packet validation"`". Consequence stated: "**定不了"该不该 XOR"**". Note this trace is still cited as support for the 4-bit run encoding, which is a *different* property (field index skip values), so the defect is scoped.

**55–56. Two docs assert the wrong run encoding.** `docs\CODEC_SPEC_20261022.md` §8: "写入器已不再把 run 固定为 4 位… 按表宽计算 `indexBits`：playerState(87) 为 7". `docs\BITORDER_6701D0_20261022.md` §5: "**历史实现错误**：这是把 `indexBits` 硬编码成 4 位". Both are contradicted by `HANDOFF_20261025_BINARY_BISECT.md` §8: "根因（一轮修好）… 必须是 **固定 4 位一组、步长 15**；2026-10-23 按 `0x670CB0` 反汇编把它"修正"成按表宽 7 位…方向反了". These two documents are the direct cause of a week of failed runs and must be marked as errata, not merely as superseded.

### D. FAT / netchan

**57. FAT never fired live.** `HANDOFF_20261024_FAT_REASSEMBLY_PLAN.md` §4.5: "本轮**没有**启动过客户端 —— 上面的实机判据全部**未经实机验证**". `HANDOFF_20261025_BINARY_BISECT.md` §8.2: "客户端消息长度稳定在 174~371 字节，永远到不了 `1154` 的分片阈值 ⇒ **FAT 分片根本不会发生**… 所以它仍是"离线已验证、实机未验"". Status UNVERIFIED, and arguably OBSOLETE as a work item for the current path.

**58. RELIABLE fragment ack untested.** `HANDOFF_20261024_FAT_REASSEMBLY_PLAN.md` §4.4: "**实测客户端不带这一位**，所以这条路径**没有实机证据**".

**59. Server-side fragmentation still wrong.** Same doc §4.2: "服务端发送侧的分片格式没改，仍是 CoD4x 布局。实际不触发（服务端消息最大也就 gamestate 259B）". Latent: enlarging snapshots to retail size (per #38) would immediately exercise the broken layout.

**94. `test_netchan` receive gap.** `HANDOFF_20261024_DYNAMIC_CLOSURE.md` §3.3: "它**没有把分片喂回 `codol_netchan_process()` 验证接收重组**". Fixed by the FAT round's 7 new cases but the original test's coverage note remains true for the pre-FAT path.

### E. Gamestate / configstring / weapon index

**60. Gamestate tail.** `docs\PHASE2_GAMESTATE_CONFIGSTRING_DONE_20261023.md` §6: "样本尾部 44 字节尚未拆成语义字段".

**61. `index_bits()`.** `HANDOFF_20261022_PAUSE.md` §5: "**缺口**：`index_bits()` 的位编码规则（递增索引如何压缩）。 `0x4A0400` 在**客户端**镜像里不是该函数（是 `std::vector::push_back`），**地址来自 2.6.9.7 服务端，不能直接套用**." Status OPEN.

**62. Client acceptance unproven.** `docs\PHASE2_…DONE_20261023.md` §5 shows only "byte_exact_roundtrip=True" against our own sample. No official-client confirmation in that document.

**63–64. Dynamic weapon index.** `_weapon_table_20261025\codol_dynamic_index_model.md`: "⇒ 动态段**不存在与局无关的静态表**；能定死的是**公式 + 编码 + base 解析**，全量条目必须从该局 gamestate 读." And the anchor table gives two different `firstDynamicWeapon` values (1224 and 1147), so the formula `cs = 5960 + idx` holds but the origin is match-dependent.

**65. Minimap.** `HANDOFF_20261022_PAUSE.md` §1.5: "**主 configstring 里没有 `northyaw` → 小地图空。**" Also §1.4: gamestate `configstring[765] = "1159"` while the snapshot sends 1156 → "客户端显示的武器是 1159，不是我们发的 1156". Both remain open; the second is a genuine two-source inconsistency (gamestate vs snapshot).

### F. Usercmd / input

**66. No symbol binding.** `docs\PHASE5_USERCMD_RELIABLE_DONE_20261023.md` §6: "官方 3.19 客户端 usercmd 函数的符号级地址绑定 仍可作为后续逆向加固项". Status OPEN but declared non-blocking. Note `INMATCH_BATTLE_SURFACE_20261023.md` §2.2 says the same thing more strongly: "官方客户端中对应的 3.19 读取函数尚未绑定到符号/入口".

**67. Jump bit conflict.** `PROGRESS_20261017.md` §二.3: "跳跃按钮位是 **0x400**，不是 0x2（0x2 是冲刺键）". But §11.6 quotes `bg_jump.cpp`: "`#define PMF_JUMPING 0x4000`（不是我们以为的 0x2000）", and §12.3 lists yet another set. Three different constants across three sources; only 0x400 was validated on the real client.

**68. `bit29`.** `HANDOFF_20261022_PAUSE.md` §1.3: "`btn=0x20000800  18 次   bits=[11,29]   ← ADS + 未知位 29`".

**69. Per-tick vs per-input.** `CODOL-BATTLE-SERVER-GAMEPLAY-003\00_INDEX.md` §6: "| **BLK-PERINPUT-TIMING** | 运动应用时机 | … 这是"服务端 tick 驱动 vs 输入驱动"的工程选择". Status OPEN by design.

**70. `usercmd.weapon` dead.** `HANDOFF_20261022_PAUSE.md` §3.2: "采信 `usercmd.weapon`（实测该值常为 0，**暂无实效**）"; §4: "`usercmd.weapon` 实测为 0，此通道不存在".

### G. Movement / collision / world

**71. `bind_world` described as wired — opposite of fact.** `INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md` "静态闭合轮（Round 1）": "`battle_service` 已通过 `bind_world/apply_usercmd` 把真实输入推进 `world.players/entities`". Contradicted by `HANDOFF_20261025_BINARY_BISECT.md` §3: "`player %d spawned in world` 在 run 里**从没打印过**——`codol_battle_service_bind_world` 在战斗服中**没有被调用**，是死代码"; and §16.1 shows the one-line fix applied 2026-10-25. Current source confirms the call exists at `src/main.c:142`.

**72. C# v0.1 gaps.** `CODOL-BATTLE-SERVER-GAMEPLAY-003\00_INDEX.md` §6 lists BLK-COLLISION / BLK-HITSCAN / BLK-DAMAGE / BLK-DEATH-RESPAWN with justification "`battle_server.py` **也没有**伤害实现（它同样只有握手+运动+武器状态）".

**73. clipMap arrays unclosed.** `HANDOFF_20261022_PAUSE.md` §"未完成" #1 and §5.1: "**clipMap 精确解析未闭合**：`cLeaf_t` / `cLeafBrushNode_t` / `aabbTrees` / `cmodels` / `brushes` 的数组边界还没定位." §5.2: "**碰撞是轴对齐近似**：29 个 clip 盒统一按 64×64×64… **地形/楼梯/斜坡没有碰撞**".

**74. coop_train has no floor.** `docs\CLIPMAP_EXTRACTION_20261026.md`: "**出生点 (48, -572) 的 y 坐标完全落在所有碰撞体之外。** 玩家出生在一片没有任何碰撞体覆盖的区域 —— 这就是穿墙/悬空的直接原因." Consequence: "服务端**无法**用现有数据算出玩家真实 z（没有地板面）". This directly retires the earlier `-128` idea recorded in `HANDOFF_20261025_BINARY_BISECT.md` §9 ("没有任何一个的 x/y 范围覆盖出生点 `(48, -572)`").

**75. mp_firingrange clipmap incomplete.** `docs\MP_FIRINGRANGE_CLIPMAP_20261026.md`: planes 7587, brushside 18770, "朝上平面（地板）| **0** | **1,104**"; but "定位 `cbrush_t` (36B) 与 `brushBounds` (24B) / `brushContents` (4B) 表" still next step. Status OPEN.

**76. Hard-coded ground.** `docs\SNAPSHOT_FIELD_DIFF_20261024.md` §12.2: "`collision.c` 的碰撞地面是写死的 `codol_ground_z = -116`，玩家永远不离开地面 ⇒ `player.on_ground` 恒 true ⇒ 参照那套"按接地状态动态写"在我们这儿实际只是**把恒定 2047 换成恒定 2046**". Note this is the exact failure mode now avoided by keeping 2047 (#35).

**77. ol-mod gameplay gaps.** `COMBAT_SERVER_HISTORICAL_FINDINGS.md` §3.10 table — each row cites the older coverage docs. Status NOT_IMPLEMENTED for the ol-mod line; these are the reasons the plugin line, even if `bind()` succeeded, would not be playable.

**78–80. C# snapshot surgery failures.** `PROGRESS_20261017.md` §三 table: field 54 `0x1000 → 0x2800` → "❌ 卡"设置游戏""; field 83 alone → "❌ 卡"玩家数据""; field 217 → "❌ 破坏快照结构". §11.3 then quotes the reference algorithm's `hint == 2` second pass, which our writer does not implement: "**这就是我们一直猜的 "second-pass"，现在有了确切实现。**" — i.e. a known, unimplemented requirement (#80).

**79. noclip.** `PROGRESS_20261017.md` §13.4: "**结论：加壳版客户端把快照当作权威状态原样保存，不执行 Pmove 本地预测。**" and §13.5 lists five configurations all failing. Status OPEN; §13.6 records the counter-observation that the client *does* fall when the server stops.

### H. Weapons / attachments / damage

**81. Runtime WeaponDef layout.** `docs\PHASE7_WEAPONATTACH_REVERSE_BOUNDARY_20261023.md` "最终布局证据校正": "将 `+0xBB4/+0xBCC/+0xBF0` 直接套到 3.19 zone 后，读到的是动画、边界和骨骼参数… 因此这些字段在本版本中再次降级为 `UNVERIFIED`"; "OLFinal/3.3.3.3 的 `WEAPON_DEFINITIONS_RVA=0x13F5A40` 与 `WEAPON_COUNT_RVA=0x7417B88` 在 3.19 PE 中无对应引用，读值全零".

**82. Shared string slots.** Same doc: "type-43 assets: 285 … reference records (`0x30`/`0x31`): 3750 … assets carrying references: 232 … scalar records applied: 172 / 879". And: "The `0x30`/`0x31` value is not a directly usable raw file pointer." Status OPEN; the resolver is explicitly outside the attachment.

**83. Two different scalar-coverage figures.** `INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md`: "44 个附件 94 条安全 scalar 进入运行表"; `PHASE7_WEAPONATTACH…`: "scalar records applied | 172 / 879". The pair is not reconciled (different denominators *and* different numerators), so the actual coverage is CONTRADICTORY in the corpus.

**84–87. Missing weapon subsystems.** `INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md` §"当前最关键的三条阻塞" #1: "recoil/view kick、ADS 精度、移动/姿态修正公式仍缺"; #3: "命中盒与 G_Damage 世界分支未闭合". `PHASE7_WEAPONATTACH…`: "`fmj_base` `0xE78` penetration semantics" still unclosed. All NOT_IMPLEMENTED; each is listed as a distinct root cause (do not merge).

**88. No BOT in training map — by design.** `HANDOFF_20261025_BINARY_BISECT.md` §16.3: "**1** | **`actor_ally_hero_quartermaster_so`** | **这张图唯一的 actor**"; "⇒ 用户说的"训练模式没有 BOT"**不是配置问题，是这张图就这么设计的**。要演一遍战斗结算必须换图."

**89. Generic actor/vehicle/turret/loot.** `INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md`: "actor/vehicle/turret/loot | PARTIAL | 实体表及 5 类通用 spawn/free 生命周期… | 3.19 原生实体布局、AI/载具/炮塔行为…".

### I. Gameplay / bot-match / cross-cutting

**90. Deliberate map mismatch.** `HANDOFF_20261024_DYNAMIC_CLOSURE.md` §2.2: "> 当前成功形态是"Lobby/mmstart 地图名"和"战斗服默认地图名"故意不一致。在没有新证据前，不要强行把两者对齐". Status OPEN — a working configuration that contradicts the protocol's own semantics and must be preserved verbatim.

**91. Server self-certification everywhere.** `V0_1_ACCEPTANCE_MATRIX.md` AC-4: "**从未发生。** 全量历史 `battle_srv.log` 里 64 次启动、2499 条 `[stat]` 行中只有 4 条非零"; AC-7 "从未发生". The four later C# round reports each repeat "NOT_RUN — 真实 CODOL 客户端端到端兼容" in almost identical wording.

**92. Reconnect semantics.** `CODOL-COMBAT-RECONNECT-STATE-001\00_INDEX.md` §8: "BL-2 | **"正常断开"语义** | v0.1 未观测到客户端正常断开命令"; "BL-5 | 玩家身份可信性 | `\xuid\` 无服务端校验依据". Both remain open; the round itself flags that enabling `identity` is "运维的显式风险决定".

**93. Entity-table residuals.** `CODOL-BATTLE-SERVER-ENTITY-001\00_INDEX.md` §6 U-1..U-7. U-1 is explicitly unreachable-but-unproven; U-2 is a single-threading assumption; U-4 "PlayerState 仍无血量/武器世界模型/伤害状态"; U-7 "客户端 `0x02` 分派未定位 … 端到端互通的结构性阻塞".

**95–97. Process defects.** `_work\source_audit.md` (sibling audit, same date) S-02/S-03/S-04: `lobby_server.py` grows 76,410 → 109,705 bytes across copies; "There is no source of truth for 'the' lobby server"; no git; `codol_battle_server.exe` cannot be re-derived from any CMake target. These directly undermine the reproducibility claim in `docs\STAGE1_CRYPTO_DONE.md` §"已完成并验证".

**98. `e2e_client.py` is not the official client.** `docs\STAGE1_CRYPTO_DONE.md` §五: "`tests/e2e_client.py` 扮演客户端（独立实现，非复用服务端代码）" and "**关键意义**：客户端侧独立算出传输密钥并与服务端一致". Correct as far as it goes, but the round's own summary (same section) says the next step is "**拿真实 3.19 客户端验**" — i.e. the handshake remains officially unverified at that point.

---

## 3. Status roll-up (of the 98 issues)

| Status | Count | Examples |
|---|---:|---|
| OPEN | 47 | #2, #15, #16, #20, #25, #34, #36, #37, #40, #41, #50, #61, #64, #65, #66, #68, #69, #70, #73–#76, #82, #87, #90, #92, #93 |
| BLOCKED | 8 | #1, #4, #7, #8, #17, #29, #33, #34-adjacent ACE pair |
| NOT_IMPLEMENTED | 9 | #30, #47, #63, #72, #77, #80, #84, #85, #86 |
| UNVERIFIED | 8 | #3, #6, #57, #58, #62, #81, #98 + P0-a |
| CONTRADICTORY / OBSOLETE (corpus still asserts) | 17 | #10, #18, #19, #21, #22, #23, #28, #31, #32, #42–#45, #46, #51, #55, #56, #67, #71, #83 |
| PARTIALLY_RESOLVED | 6 | #35, #49, #89, #94 + two Phase downgrades |
| RESOLVED (explanation only) | 1 | #88 |
| NOT_RUN (official-client tier) | 2 | #91, #92 |

(Direct sums exceed 98 because several items carry a compound status — e.g. #46 is OBSOLETE *and* the newer status is PARTIAL.)

## 4. Cross-cutting observations

1. **The dominant failure mode is "reference equality ≠ usable".** Three independent episodes have the same shape: 141-byte golden snapshot stalls (`HANDOFF_20261025_BINARY_BISECT.md` §15), room-push byte-exact envelope produces no client effect (`ROOM_PUSH_SPEC_FIX_RUN_20261028.md` §三), and the 2026-10-23 table-width "correction" breaks map entry (`BINARY_BISECT` §8). Any future plan that says "align to the reference implementation" must first name which reference and must have an official-client acceptance criterion.
2. **Five different artifacts are called "the client" in evidence chains** (packed retail `36997674`, unpacked `out.exe` `044c396c`, `E3823FD6`, 2.6.9.7 `35375404`, and the 3.3.3.3 QA build). Issues #4, #11, #12, #51, #67, #71 all trace to this ambiguity. No document in scope establishes a single object identity table.
3. **The 10-23/10-24/10-25 errata chain is itself the largest single defect cluster.** Issues #46, #55, #56, #71, #83 are all "a document in the corpus asserts the opposite of what the project later proved". A reader who opens `CODEC_SPEC_20261022.md` or `PHASE3_SNAPSHOT_CODEC_DONE_20261023.md` without the corresponding handoff will re-introduce a fixed bug.
4. **The ol-mod line and the C line never verified each other.** `COMBAT_SERVER_CALLCHAIN_MAP.md` §5 U-5 still stands: no document shows a message produced by one line being consumed by the other. That is why #14–#17 (booking) and #34–#40 (snapshot) can both be "the blocker" depending on which line you are on.
5. **`docs\` (root, 2026-10-26..28) contains the newest and strongest room/battle evidence but is outside the scope list of this audit and of most round reports.** `BATTLE_ZERO_RX_ROOT_CAUSE_20261028.md` (#25) and `ROOM_PUSH_CHANNEL_WRONG_20261028.md` (#21) refute conclusions that the in-scope 2026-10-23/24 documents still state as current.
