# Historic corpus audit — E-series / Demonware / crypto / lobby-chain

Scope: 47 report directories at workspace root, read at summary / verdict / blocker level.
Audit date: 2026-10-29. All quotes are verbatim from the cited file. Paths are relative to
`D:\BaiduNetdiskDownload\使命召唤OL\`.

**Global discipline note.** Several of these corpora are themselves *errata chains* — later
numbered reports routinely refute earlier ones. Where that happens the later report is recorded
as the status and the earlier claim is marked OBSOLETE/CONTRADICTORY, but both paths are listed
so nothing is silently dropped.

**Coverage note.** All 47 directories in scope were opened. For each, the executive summary,
verdict, or blocker/unknown file was read in full; supporting evidence files were read only where
a verdict's claim needed its exact wording. One directory is a duplicate rather than an unread
one: `CODOL-DEMONWARE-BUNDLE-001/00_CONSOLIDATED_QUESTION_REGISTER.md` and
`CODOL-DEMONWARE-EVIDENCE-BUNDLE-20261012/00_CONSOLIDATED_QUESTION_REGISTER.md` are byte-identical
(both `57b886e2…5921`); the former's other files are generation scripts (`_build_register.py`,
`_stage.py`, …) plus `_register_raw.json`. `CODOL-DEMONWARE-EVIDENCE-BUNDLE-20261012` is treated
as the canonical copy.

---

## 1. Master table

| # | Issue | Primary evidence file | Status | Superseded / updated by |
|---|---|---|---|---|
| 1 | Client in-match receive buffer → reader edge never closed (`recv buf` vs `0x7765A0 arg1`) | `CODOL-BATTLE-SERVER-RECEIVE-LINK-050/00_FINDINGS.md` | OPEN | — (latest in chain) |
| 2 | 3rd section (`.tp3 #3`) ~229.6 MB never present in any recovered image | `CODOL-BATTLE-SERVER-CONNECTIONLESS-HANDSHAKE-049/08_SECTION3_GAP_ANALYSIS.md` | BLOCKED (needs runtime image) | — |
| 3 | Main-DLL `.tvm0` (31.4 MB) and `.tls` (15.5 MB) undecoded | `CODOL-BATTLE-SERVER-DLL-NETBIND-040/STATIC_ANALYSIS_BLOCKERS.md` | BLOCKED | confirmed unchanged in 043/044/046 |
| 4 | TASK-009 battle RVA list does not apply to build 1649370 (1/48 hits) | `CODOL-BATTLE-SERVER-TRACE-034/UNKNOWN_AND_BLOCKERS.md` (BLK-034-01) | CONFIRMED / claim invalidated | self-superseding |
| 5 | 040–044 compared absolute VA as RVA → false "beyond EOF" | `CODOL-BATTLE-SERVER-CLIENT-IMPORT-IDENTITY-045/08_NEXT_ACTION_DECISION.md` (045-C1) | CONFIRMED-ERRATA (OBSOLETE claim) | 045 |
| 6 | 042/045 classed Tencent TDR/TQOS unpacker as CoD netfield/delta decoder | `CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046/09_NEXT_ACTION_DECISION.md` (046-C1) | CONTRADICTORY → corrected | 046 |
| 7 | 042 "唯一可复核调用者为 TQOS" — narrowed | 045 `08` (045-C3) | CONTRADICTORY → corrected | 045 |
| 8 | 044 "0x87BE00 更像 ReadFile/重叠读" | 045 `08` (045-C2) | CONTRADICTORY → corrected (`select`+`recv`) | 045 |
| 9 | In-match opcode table not located (A-03) | `CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046/07_A_BLOCKERS_STATUS.md` | OPEN | 045 → 046, unchanged |
| 10 | Gamestate client consumption semantics unknown (A-04) | same `07_A_BLOCKERS_STATUS.md` | OPEN | unchanged 043→046 |
| 11 | Configstring client consumption semantics unknown (A-05) | same | OPEN | unchanged |
| 12 | Snapshot / delta / EOF client decode unknown (A-06) | same | OPEN (narrowed) | 045's `0x87D5A0` reclassified TDR by 046 |
| 13 | Reliable command `0x01/0x02` client dispatch unproven (A-08) | same | OPEN | unchanged |
| 14 | Client `0x06` terminator read/align/terminate semantics | `E10_CONFIGSTRING_DISPATCH_001/07_E10_VERDICT.md`; `E11_GAMESTATE_SUBFRAME_001/07_E11_VERDICT.md` | BLOCKED | E16/E26 still report BLOCKED |
| 15 | Outer `0x04` subframe value-level dispatch not proven | `E10.../07_E10_VERDICT.md`; `E11.../07_E11_VERDICT.md` | BLOCKED (position CROSS-INFERRED) | E11 corrects E10's layer |
| 16 | `0xA2660` realtime attribution (3 callers all demo chain) | `E12_REALTIME_GAMESTATE_CONSUMER_001/07_E12_VERDICT.md` | BLOCKED | E13/E14 confirm |
| 17 | Realtime `0x03` gamestate consumer not located | `E12.../07_E12_VERDICT.md` (E12-C8) | BLOCKED | E13..E16 confirm |
| 18 | Demo-path consumer `0x34FD80(1)` field order conflicts with server `0xA21B8` | `E12.../07_E12_VERDICT.md` (E12-C7) | REFUTED (demo consumer) | — |
| 19 | `0x3524F0` is a send/serialize staging buffer, not a receive ring | `E13_RECV_RINGBUFFER_TRACE_001/07_E13_VERDICT.md` | REFUTED (recv→ring in 3-level closure) | — |
| 20 | `0xA2E50` (opcode 0x02 handler) still 0 callers after full-.text scan | `E06_TVM0_STATIC_DECODE_001/08_E06_VERDICT.md` | OPEN | repeated in E09, REVERSE-COVERAGE G-02 |
| 21 | `.tvm0` semantics — format solved (aPLib) but obfuscated control flow unresolved | `E06.../08_E06_VERDICT.md` | PARTIALLY_RESOLVED (format) / BLOCKED (semantics) | — |
| 22 | Demonware type-code 1 / 2 semantics | `E20_TYPE_BRANCH_CLOSURE_001/E20_BLOCKER_REGISTER.md` (B-E20-01) | BLOCKED | E19's "size 1 vs 9" REFUTED by E20 |
| 23 | E19 "type1→size1, type2→size9" | `E19_DEMONWARE_SESSION_OBJECT_DATAFLOW_001/E19_EXECUTIVE_SUMMARY.md` | REFUTED | E20 (merge at `0x6A9978`, both `ebx=9`) |
| 24 | HMAC direction (inbound verify vs outbound sign) | `E22_HMAC_DIRECTION_RETURN_PATH_001/E22_DIRECTION_HYPOTHESIS_MATRIX.md` | INFERRED (strong) — not PROVEN | — |
| 25 | E22 "five addresses in `.data` BSS virtual tail" | `E23_BSS_INITIALIZATION_AND_DISPATCH_RECOVERY_001/E23_EXECUTIVE_SUMMARY.md` | REFUTED (VA/RVA misuse) | 023 |
| 26 | `0xA87830` 24-byte output struct field semantics | `E23.../E23_EXECUTIVE_SUMMARY.md` §阻塞项 | OPEN | — |
| 27 | `0xACE1B0` cipher tables at `0xD48F48`/`0xD48F64` claimed BSS/unresolvable | `E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001/E24_EXECUTIVE_SUMMARY.md` | UNVERIFIED (same VA/RVA error class as E22) | not yet re-audited |
| 28 | `[+0x5CC]` phase numbering 0/1/2/3 business naming | `E24.../E24_EXECUTIVE_SUMMARY.md` | BLOCKED | — |
| 29 | 0x81 reply bytes vs on-wire payload byte-exactness | `E25_HANDSHAKE_RESPONSE_SEND_PATH_001/E25_EXECUTIVE_SUMMARY.md` | INFERRED (strong) — chain PROVEN, bytes not | — |
| 30 | Server has no Demonware consumer; opcode width 3-bit vs 8-bit conflict | `E26_SERVER_HANDSHAKE_PEER_CROSSWALK_001/E26_PROTOCOL_CONFLICTS_AND_BLOCKERS.md` (C-1) | CONFIRMED (conflict), sides incompatible | — |
| 31 | 2697 Demonware server endpoint absent from all 2697 server modules | `E27_DEMONWARE_SERVER_PEER_DISCOVERY_001/E27_EXECUTIVE_SUMMARY.md` | CONFIRMED (absent) / blocked for interop | E26's "does not exist" narrowed to "not in codol_dedrun.exe" |
| 32 | ol-mod / REF_LOBBY_KIT peer targets 1.1.1.13 / 3.3.3.3; its client addresses invalid in 2697 image | `E27.../E27_EXECUTIVE_SUMMARY.md` | REFUTED (for 2697 reuse) | — |
| 33 | Client codec layer vs reference peer | `CLIENT-DEMONWARE-PEER-REUSE-AUDIT-001/05_REUSE_VERDICT.md` | REUSE-PARTIAL → REFUTED as gap | `CLIENT-DEMONWARE-CODEC-KEYFLOW-001` |
| 34 | Codec store/load identity ⇒ `K_client,consumed = K_reference,derived` | `CLIENT-DEMONWARE-CODEC-KEYFLOW-001/05_FINAL_VERDICT.md` | KEYFLOW-EQUIVALENT (static only) / NOT-OBSERVED | — |
| 35 | G2 gate — no independent algorithm-structure spec | `CODOL-KEYFLOW-SPEC-PROVENANCE-001/CODOL_KEYFLOW_G2_REASSESSMENT_001.md` | CONDITIONAL PASS / `NO-INDEPENDENT-SPEC-FOUND` | 维持 from INDEPENDENT-VERIFY-001 |
| 36 | G3 gate — frame/MAC/seq validation | `CODOL-KEYFLOW-G3-FRAME-VALIDATION-001/CODOL_G3_DECISION_001.md` | PARTIAL PASS (CONDITIONAL) | counter-boundary + length dirs |
| 37 | G3 sequence model "expected unchanged on failure" | `CODOL-KEYFLOW-COUNTER-BOUNDARY-001/CODOL_G3_RESIDUAL_RISK_UPDATE_001.md` | CONFLICTING-EVIDENCE → corrected (post-increment-before-compare) | counter-boundary-001 |
| 38 | Length upper bound layering: local parser `0x100000` vs client ciphertext `<0xFFFFFF` | `CODOL-KEYFLOW-LENGTH-COMPATIBILITY-001/CODOL_LENGTH_COMPATIBILITY_AUDIT_001.md` (Q-LEN-01) | CONFIRMED-STATIC (differs) / UNRESOLVED (impact) | — |
| 39 | 32-bit wrap `0xFFFFFFFF→0` and post-failure connection lifecycle | `CODOL-KEYFLOW-COUNTER-BOUNDARY-001/CODOL_G3_TC27_REASSESSMENT_001.md` | PASS (STATIC BEHAVIOR RECORDED) / UNRESOLVED (runtime) | — |
| 40 | Large-frame allocation / parser compatibility | `CODOL-KEYFLOW-COUNTER-BOUNDARY-001/CODOL_G3_RESIDUAL_RISK_UPDATE_001.md` | UNRESOLVED | — |
| 41 | All 36 runtime validation test cases never executed | `CODOL-DEMONWARE-RUNTIME-VALIDATION-001/CODOL_DEMONWARE_RUNTIME_VALIDATION_PLAN_001.md` | NOT_EXECUTED | — |
| 42 | I4 register accounting discrepancy (Q-44 double-count) | `CODOL-DEMONWARE-EVIDENCE-BUNDLE-20261012/00_REGISTER_I4_RECONCILIATION_NOTE.md` | CONTRADICTORY (two ledgers) | — |
| 43 | `[matching+0x288]` booking latch never set to 1 | `CODOL-TARGET-PROTOCOL-TRACE-009/UNKNOWN_AND_BLOCKERS.md` (BLK-009-01) | INVALID_PRECONDITION (per 031) | `CODOL-TASK-031-ACCEPTED-LATCH-REGRESSION` |
| 44 | `accepted` transport channel / caller not located | 009 `BLK-009-02`; 031 §5 | OPEN | — |
| 45 | `accepted` byte-form conflict (u32 prefix present vs stripped) | 009 `BLK-009-03`; 031 §4 | UNRESOLVED | — |
| 46 | Battle endpoint (address+port) source not located; `BATTLE_28960 = NOT_OBSERVED` | 009 `BLK-009-04`, `BLK-009-07` | OPEN | — |
| 47 | Client stops at "100" popup, `rc=-1`, never enters lobby | `CODOL-TASK-031-ACCEPTED-LATCH-REGRESSION/UNKNOWN_AND_BLOCKERS.md` (BLK-031-01) | OPEN (highest priority) | — |
| 48 | Six launch-chain deviations from known-good chain (incl. missing 8444 portproxy) | 031 `UNKNOWN_AND_BLOCKERS.md` (BLK-031-02) | OPEN | — |
| 49 | `hosts` file 937B original irrecoverable (now 915B) | 031 `UNKNOWN_AND_BLOCKERS.md` §6 | OPEN (irreversible config change) | — |
| 50 | Target version: user's stated 3.9.9.7 vs actual 3.19.26.22 | `CODOL-TARGET-GAME-IDENTITY-008/BLOCKERS.md` (BLK-008-01) | CONTRADICTORY across corpus | TARGET_VERSION_VERDICT CONFIRMED 3.19.26.22 |
| 51 | No 3.9.9.7 client exists anywhere in workspace | `CODOL-BATTLE-SERVER-CLIENT-IDENTITY-007/BLOCKERS.md` (BLK-007-00/01) | CONFIRMED-absurd premise (006/007 series blocked on a nonexistent version) | 008's verdict |
| 52 | No runtime image of target EXE (only main DLL has one) | 008 `BLK-008-07` | OPEN | — |
| 53 | OOB states 3/4/5/6 business semantics; 5/6 have no immediate write points | `CODOL-BATTLE-OOB-STATE-035/UNKNOWN_AND_BLOCKERS.md` (U-03, BLK-035-02) | UNKNOWN / BLOCKED | 035 corrects 034 |
| 54 | `[ebx+0x100260]` gate-2 third condition semantics | 035 `BLK-035-03` | INFERRED (unproven) | — |
| 55 | State-4 userinfo 28-key → value wiring/quoting | 035 `BLK-035-04`, `CONFIRMED_VS_UNKNOWN.tsv` U-04 | UNKNOWN | — |
| 56 | OOB inbound envelope / length / delimiter rules | `CODOL-BATTLE-OOB-STATE-035/CONFIRMED_VS_UNKNOWN.tsv` (U-07, U-09) | UNKNOWN — cannot emit target-valid OOB | restated in 037/038/042 |
| 57 | `getchallenge` seed string generation untraced | 035 `U-10` | UNKNOWN | — |
| 58 | `cancelConnect` teardown side effects | 035 `U-08` | UNKNOWN | — |
| 59 | Throttle 3000/100/500 business semantics | 035 `U-01`, `U-02` | UNKNOWN | — |
| 60 | Client OOB reply-branch bodies after token match | 035 `U-06` | UNKNOWN | — |
| 61 | Server has never received a real client connection | `CODOL-BATTLE-SERVER-INTEGRATION-FREEZE-005/FREEZE-005_REPORT.md` §8 | NOT_EXECUTED (251/251 is server-only) | repeated in 002, 003, 037 |
| 62 | 2697 snapshot sending disabled by default | `CODOL-BATTLE-SERVER-PROTOCOL-GAP-037/CURRENT_SERVER_CAPABILITIES.md` §2 | NOT_IMPLEMENTED (deliberate) | — |
| 63 | ol-mod EngineBindings host gate: expects `SizeOfImage 0x0E5D6000`, actual `0x0E659000` | `CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001/05_SERVER_IMPLEMENTATION_GAP.md` (G-08) | BLOCKED (blocks 100% of ol-mod battle chain) | — |
| 64 | 2697 record layer never observed with C-2697; COOKIE_ECHO 189 vs 219; AES192/Tiger192 vs AES128/SHA1 | `CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001/05_SERVER_IMPLEMENTATION_GAP.md` (G-01) | CONFLICTED / unobserved | — |
| 65 | Lobby (REF_LOBBY_KIT) and ol-mod booking not wired together | `CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001/05_SERVER_IMPLEMENTATION_GAP.md` (G-06) | NOT_IMPLEMENTED | — |
| 66 | Match traffic goes to `101.67.36.18:10035`; `28960` seen 0 times | `CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001/05_SERVER_IMPLEMENTATION_GAP.md` (G-07) | OPEN / NOT_OBSERVED | — |
| 67 | Server config map mismatch; SessionDescriptor hardcodes `127.0.0.1:28960` | `CODOL-BATTLE-SERVER-RECEIVE-LINK-050/00_FINDINGS.md` | NOT_IMPLEMENTED (recorded, not fixed) | — |
| 68 | Fragment stride 1154 vs 1162 unresolved | `CODOL-BATTLE-SERVER-CLIENT-IMPORT-IDENTITY-045/07_SERVER_READINESS_ISSUE_LEDGER.tsv` (B-05) | UNKNOWN | — |
| 69 | Sample identity contradiction: recorded `E3823FD6` not present locally | 045 `07_SERVER_READINESS_ISSUE_LEDGER.tsv` (A-07) | OPEN (engineering ruling) | — |
| 70 | No target capture / E2E for build 1649370 | `CODOL-BATTLE-SERVER-TRACE-034/UNKNOWN_AND_BLOCKERS.md` (BLK-034-15) | NOT_EXECUTED (project-wide) | repeated everywhere |
| 71 | 035 module passes 84/84 offline tests but only a confirmed subset | `CODOL-BATTLE-OOB-STATE-035/UNKNOWN_AND_BLOCKERS.md` §1 | OFFLINE-ONLY (not client-validated) | — |
| 72 | Plugin boundary (31,953 lines) has zero tests | `CODOL-BATTLE-SERVER-REVERSE-COVERAGE-001/05_SERVER_IMPLEMENTATION_GAP.md` (G-20) | NOT_IMPLEMENTED | — |
| 73 | `0x788133` / `0x78772D` attribution chain (recv vs timestamp) | `E19.../E19_EXECUTIVE_SUMMARY.md` §4; `E16.../08_E16_VERDICT.md` | REFUTED / closed | E16 → E19 |
| 74 | E13 "`0x60E5B0` is a protocol state machine" | `E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001/10_E14_VERDICT.md` | REFUTED (it is `vsnprintf`) | E14 |
| 75 | E08 "A2 count = 10 bit" | `E14.../10_E14_VERDICT.md` | CONTRADICTORY → corrected to 11 bit | E14 |
| 76 | E08 "count1 8 vs 16 bit" conflict | `E08_CONFIGSTRING_BODY_001/07_E08_VERDICT.md` → `E09.../07_E09_VERDICT.md` | RESOLVED (16 bit PROVEN, 8 REFUTED) | E09 |
| 77 | E15 "TLS plaintext → application dispatch" | `E15_TLS_PLAINTEXT_TO_APPLICATION_001/07_E15_VERDICT.md` | REFUTED (1-byte readiness peek, libcurl) | E15 self-corrects E14 |

---

## 2. Per-item detail

### Group A — client netcode / receive path

**A1 (row 1) — recv buffer → `0x7765A0` reader edge.**
`CODOL-BATTLE-SERVER-RECEIVE-LINK-050/00_FINDINGS.md`:
> "因此，目前不能证明 0x7765A0 读取的字节就是 recv 的后续 payload。可以证明两端使用同一个会话对象、同一长度/类型控制链，不能把"对象构造"写成"payload 已复制"。"

Proven: `[esi+0xA8]` is the recv destination (050 §"已证实的数据流" item 1);
`0x7A44F6/0x7A4557/0x7A45F0/0x7A46AE` compare against `0x81/0x83/0x84/0x85`.
Claimed only: that the object built at `[esi+0xB0]` receives the payload.
Status OPEN. This is the single "minimum unclosed edge" the whole 048→050 chain converges on.

**A2 (row 2) — 3rd section missing.**
`CODOL-BATTLE-SERVER-CONNECTIONLESS-HANDSHAKE-049/08_SECTION3_GAP_ANALYSIS.md`:
> "裁定:第 3 节区缺口 = 缺文件数据(壳压缩 + 恢复过程未展开),不是工具无法解码。"

Quantified: declared VSize `0x0DBB1CC0`, only `0x4F000` present, ~229.6 MB missing; and
> "工作区内**没有**任何文件的长度超过 10,899,456。因此**没有任何映像补上第 3 节区**。"

Status BLOCKED. Note this is *not* the same defect as A3 (`.tvm0`) — different section, different binary.

**A3 (row 3, plus E06's separate `.tvm0` finding at row 21) — `.tvm0` / `.tls` undecoded.**
`CODOL-BATTLE-SERVER-DLL-NETBIND-040/STATIC_ANALYSIS_BLOCKERS.md` (BLK-039-04/05):
> "`.tvm0` 31.4MB 未解码，3 个导出全在其中"
and `BLK-040-05` "`.tls` 熵 7.532, 非正常 x86".
Note the corpus contains **two different `.tvm0` claims**: E06 solved the *2.6.9.7 recovered image's*
`.tvm0` as an aPLib/AP32 compressed block ("`.tvm0` 的**格式之谜已解**（它是 aPLib 压缩块，不是虚拟机）"),
while the 1649370 main DLL's 31.4 MB `.tvm0` remains undecoded. These are not the same artifact and
must not be merged; E16 additionally REFUTED a `.tvm0` call site in `0x78772D`
("`.tvm0` 定性 REFUTED（实为 .data/BSS 与 .rimp 伪影）").

**A4 (row 4) — TASK-009 RVA list inapplicable.**
`CODOL-BATTLE-SERVER-TRACE-034/UNKNOWN_AND_BLOCKERS.md`:
> "在本镜像中把该列表当作 RVA 读取时，48 个常量里**只有 1 个**落在函数序言（且该命中项语义未证），与随机基线不可区分。"

Proven: the probe targets OLFinal `out.exe` (`SizeOfImage 0x0E5D6000`), the local image is `0x0E659000`.
Status: the *earlier* claim is OBSOLETE; replacement localization done in 034 itself.

**A5 (row 5) — VA/RVA confusion.** `045/08_NEXT_ACTION_DECISION.md` 045-C1:
> "**040/041/043/044 原文:**"读 API IAT 槽 `0x0CA84E8` 落在镜像未覆盖节区"… **045 实测:**`0x0CA84E8` 是**绝对 VA**；`RVA = 0x8A84E8 < 0xA65000` → **在文件内**。"

Status: the "beyond EOF" blocker A-01/BE-01 is CLOSED; the residual issue is that three separate
reports (040, 041, 043, 044) propagated the error — a process finding, not a technical one.

**A6 (rows 6, 7, 8) — TDR/TQOS misattribution.**
046-C1:
> "实测:两函数引用 `lib_src\tdr\tdr_net.c`(`RVA 0x99F060`)与整套 TDR net-buffer 诊断… → 腾讯 **TDR**,非 CoD netfield。"

046 §1 also states the net consequence plainly:
> "本轮**否证**了 045 把 `0x85D96E→0x87BA50→0x87D5A0` 当作游戏业务解析入口的推断… 同时**未**在现有恢复映像内定位到**任何一个**游戏网络消息解析器或业务消费者"

Status of the chain: CONTRADICTORY → corrected. Status of the underlying question (game parser):
OPEN in a *narrower* form — A-02 (`业务层调用 net-buffer 解码器的边未闭合`) remains OPEN per 046.

**A7 (rows 9–13) — the five A-class semantics.** `046/07_A_BLOCKERS_STATUS.md` §3:
> "对下列**五项关键客户端消费语义**，本轮解决率仍为 **0%**。"

Each of opcode (A-03), gamestate (A-04), configstring (A-05), snapshot (A-06), reliable (A-08) is
listed OPEN with only diagnostic-string xrefs located (e.g. `gamestateupdate %d` @ `0x54B7B`/`0x73214`;
`EXE_CONFIGSTRINGMISMATCH` @ `0x731E1`/`0xF2833`). Proven: the strings exist and are referenced.
Not proven: any read/dispatch/store path. Recorded as five distinct items because the report keeps
them in five distinct rows with distinct close conditions.

**A8 (rows 14, 15) — `0x06` terminator and outer `0x04`.** E10 verdict:
> "| 2 | `0x06` 读取路径 | **BLOCKED** | 客户端读取点未定位 |"
E11 adds: "| `0x04` 值级比较 | **BLOCKED** |".
E11 also corrected E10's layer model (M3: "`0x04` 是顶层 opcode" → "实为 **Gamestate 内部子帧头**").
Status: BLOCKED for client side; server write side PROVEN (`0xA0997` `WriteByte(6)`).
Note the E-series explicitly forbids merging the four `0x06` contexts
("四类 `0x06` 上下文…分别登记，**未跨层合并**").

**A9 (rows 16, 17, 18) — realtime vs demo attribution.**
E12:
> "`0xA2660` 作为 "Configstring body reader" 的字段级行为 **PROVEN**；但其"**实时**"归属未证——3 个调用点均无实时上游证据"
and E12-C7 (REFUTED): the demo consumer's field order conflicts with the server writer.
These are three separate statuses for the same function family and must not be conflated:
"field-level decode PROVEN" ≠ "realtime PROVEN" ≠ "client acts on it PROVEN".

**A10 (row 19) — `0x3524F0` direction.** E13:
> "`0x351D00` 的指令序列是**序列化本地状态 → 写入环形缓冲 → 提交发送**… 因此 `0x3524F0` 是**发送/序列化暂存**，方向为**出站**。"

Status REFUTED (within the 3-level closure). This kills one of the two remaining candidate paths.

**A11 (row 20) — `0xA2E50` unreachable.** E06:
> "`0xA2E50` 在**高完备搜索面**（`.text` 全节指令级、`.rdata` 30,895 个指针、`.data` 已初始化区 2,375 个指针）**均不可达**。… **仍不排除** 运行时生成代码/回调/`.tvm0` 内间接分派。"

Note explicitly: "仍不排除" — the report does *not* claim absence. Status OPEN.

**A12 (row 73) — `0x788133` / `0x78772D`.** E19 §4:
> "**裁定（REFUTED，限定范围）：`0x788133` 与 `0x6ABBC0` 状态机不属同一路径。**"
E16 had already established `0x78772D` as a timestamp conversion function. Status closed/REFUTED;
recorded because 040/041/042 had treated it as a candidate receive point.

---

### Group B — Demonware handshake / crypto

**B1 (rows 22, 23) — Demonware type codes.** `E20_BLOCKER_REGISTER.md`:
> "B-E20-01 type-code semantics BLOCKED; min action expand 0x6A9720."
E20 summary: "Type 1 and 2 merge at 0x6A9978 with ebx=9; E19 separate-size claim REFUTED."
Proven: one shared path, `ebx=9` for both. Not proven: what 1 and 2 mean, or what the payload is.
Status BLOCKED.

**B2 (row 24) — HMAC direction.** `E22_DIRECTION_HYPOTHESIS_MATRIX.md`:
> "裁定：H1 与 H3 均为 `INFERRED（强）`；H2 为 `WEAK_INFERENCE`；H4 为 `BLOCKED`。不得将任一方向单独标为 `PROVEN`。"

Key evidence against a stronger claim: "无直接调用 `recv`，因此"入站"来自帧码/计数器语义推断，不是调用边证明。"
Status INFERRED. If a server implementation signs outbound frames on this basis it is
acting on an inference, not on a proven direction.

**B3 (row 25) — E22's BSS claim refuted.** E23:
> "E-22 将其判为 `.data` BSS 虚拟尾部是**地址基准（VA/RVA）误用**"
and "按 VA 重算 rel32 得到的真实调用点… `0xA85AD0`：`0x6AC168`".
Status REFUTED. Same class of error as A5 — the corpus contains at least three independent
VA/RVA mix-ups (E06 M-01, E08 M-01, E22→E23, 040–044→045).

**B4 (row 27) — `0xACE1B0` cipher tables.** E24 states:
> "`0xACE1B0` 依赖的 `.data 0xD48F48`/`0xD48F64` 表位于 BSS 尾部，磁盘无字节，**静态不可解析**。"

This carries the **same signature** as the E22 claim that E23 refuted (a `.data`-tail/BSS claim
immediately after a VA/RVA correction). E23 explicitly warns about the mechanism. Status:
UNVERIFIED — flagged for the same VA/RVA double-check that overturned E22. Do not build on it
without re-audit.

**B5 (rows 26, 28, 29) — three residual E23/E24/E25 gaps.** Quoted:
- "`0xA87830` 的 `[ebp+0x18]` 24 字节输出结构字段语义"
- "`[+0x5CC]` 阶段编号（0/1/2/3）与协议语义命名…无独立证据"
- "`0x81` 应答字节与线上载荷的逐字节一致性未验证（只证同一缓冲链路）"

E25's five-layer table is the clearest example in the corpus of the
constructed→passed→queued→submitted→sent distinction: all five layers are PROVEN, and yet the
one layer that matters for interop (wire bytes) is INFERRED. Recorded as one item with
three sub-parts because they are three distinct objects (a struct, a state field, a byte buffer).

**B6 (rows 30, 31, 32) — the two-protocol-family split.**
E26:
> "它是**经典 iD-Tech（CoD）协议栈**，与客户端 E-21..E-25 追踪的 **Demonware 握手对象完全属于两条不同协议族**"
Conflict C-1: client `cmp al,0x81/0x83/0x84/0x85` (8-bit) vs server `_MSG_ReadBits(msg,3)` + `cmp edi,4`.
E27:
> "上述 Demonware 对端**面向 `1.1.1.13`（`C1.exe`）/ `3.3.3.3`**，其 IDA 库与 `dw_wire.py` 引用的客户端地址…**在我们的 2697 恢复镜像中不成立**"
Status: the *absence* from the 2697 server package is PROVEN (12511 files, 4 PE, 0 hits); the
*existence* of a peer elsewhere is PROVEN; the *interoperability* is UNVERIFIED and E27 explicitly
says the peer must be re-localized against the 2697 client before reuse.

**B7 (rows 33, 34) — codec / key equivalence.**
`CLIENT-DEMONWARE-CODEC-KEYFLOW-001/05_FINAL_VERDICT.md`:
> "**四个最终被密码学操作实际消费的密钥材料，与参考对端 `deriveSessionKeys` 的输出逐字节相同。**"
with the explicit limit: "**NOT-OBSERVED 不得改写**：本任务全程静态… `REUSE-SUPPORTED` 只表示"静态证据支持复用"，**不等于互操作成功**。"
Status: KEYFLOW-EQUIVALENT (static, bit-exact) — **not** an interoperability result. The earlier
REUSE-PARTIAL gap is REFUTED (codec is an identity transform).

**B8 (row 35) — G2 conditional.** `CODOL_KEYFLOW_G2_REASSESSMENT_001.md`:
> "结构描述 15 条中：7 `ARTIFACT-ONLY`、4 `SOURCE-SHARED`、2 `UNRESOLVED`、仅 2 条（原语层）`INDEPENDENTLY-CORROBORATED`"
and "**G2 维持 `CONDITIONAL PASS`，不予升级。**"
Proven: 11/11 KATs pass with independent primitives + artifact-derived parameters.
Not proven: the algorithm *structure* itself. Requires S-1 (`NO-INDEPENDENT-SPEC-FOUND`).

**B9 (rows 36, 37, 39, 40) — G3 chain.** Four distinct sub-items:
(a) G3 overall = PARTIAL PASS / CONDITIONAL (`CODOL_G3_DECISION_001.md`);
(b) the failure-state model was wrong and has been replaced:
> "原 G3 的本地序列号模型为… `if incoming != expected: reject and leave expected unchanged` … 新反汇编证据显示：… `expected = (old + 1) mod 2^32 ; happens before comparison`"
status CONFLICTING-EVIDENCE → corrected;
(c) wrap behavior now `PASS (STATIC BEHAVIOR RECORDED)` but "**不是**运行时通过" and
"同一连接下下一次 seq=0 是否会被处理：`UNRESOLVED`";
(d) large-frame path `UNRESOLVED` ("不做大规模分配；等待安全测试环境").

**B10 (row 38) — length bound layering.** `CODOL_LENGTH_COMPATIBILITY_AUDIT_001.md`:
> "客户端静态等价的最大外层长度：`0x100000E`" vs local parser `0x100000`
with "**不建议直接修改 parser 上限。**"
Status CONFIRMED-STATIC (the two limits are at different layers) / UNRESOLVED (whether any
target scenario needs frames >1 MiB).

**B11 (row 41) — runtime validation untouched.** `CODOL_DEMONWARE_RUNTIME_VALIDATION_PLAN_001.md`:
> "**未执行**：TC-01…TC-36 任何用例；未启动客户端/服务端/模拟器；未注入；未读取运行时内存；未连接网络。"

G2 was later partially filled by the INDEPENDENT-VERIFY dir, but G3/G4/G5 remain unexecuted.
This needs to be flagged whenever someone cites "the keyflow is verified".

**B12 (row 42) — I4 ledger discrepancy.** `00_REGISTER_I4_RECONCILIATION_NOTE.md`:
> "I4 权重 | 368 | **376** | **+8**" and "E-23 回退到"权威 XVAL-02 账本 206"作为基线… **Q-44 自此未被计入任何后续分母**"
Status CONTRADICTORY (two coexisting denominators 59.13% vs 57.87%). Does not affect the
technical verdict, but any completeness-percentage claim in this project has ±1.26pt ambiguity
in the I4 subset unless the caller states which denominator it used.

---

### Group C — lobby → battle latch

**C1 (row 43) — latch.** `CODOL-TARGET-PROTOCOL-TRACE-009/UNKNOWN_AND_BLOCKERS.md`:
> "`[matching+0x288]` 的唯一消费者 `0x00634402` 驱动 `mmstart`；但 019/023/024/025/029 全部运行中 `this288` **从未为 1**。"
**Superseded conditionally by 031**, which found the client never reached the lobby at all:
> "~~"客户端从未发出 `mmbook`"~~ —— 该表述**仅适用于本次错误启动会话**"
Status therefore INVALID_PRECONDITION, not "latch broken". This is the correct reading of 031 and
must not be collapsed back into a latch defect.

**C2 (rows 44, 45) — accepted channel and byte form.** 009:
> "已排除直接 `call 0x632680`、普通虚调用、Base.dll 处理；`response channel = UNKNOWN`"
and BLK-009-03 "ol-mod 存档断言为**带 u32 前缀**… 本项目 023 之后实现**去掉前缀**，疑为 REGRESSION" with
"两者均未在目标客户端单变量复现."
031 adds static confirmation of the gate string and comparison but leaves `arg5` INFERRED.
Status UNRESOLVED (both sub-items).

**C3 (row 46) — battle endpoint.** 009:
> "`Booking -> 28960 linkage = UNKNOWN`；`BATTLE_28960 = NOT_OBSERVED`"
and BLK-009-07 is described as "**强否定结论**：在这段采集里游戏网络层没有建立任何连接".
Note: that strong negative was later qualified by 046/045's discovery of P5 `recv` — the client
*does* have an in-match recv path in the EXE, it simply was not observed connecting. Status OPEN.

**C4 (rows 47, 48, 49) — the "100" popup.** 031:
> "**`CLIENT_DID_NOT_ENTER_LOBBY` —— 客户端未通过已固化的正式启动链成功进入游戏，停在 "100" 弹窗错误处（`rc=-1 / 0xFFFFFFFF`）。**"

Six concrete deviations are tabulated for #48 (script, sandbox, `dwauth.ini`, auth service, lobby
service, missing `443→8444` portproxy). #49 is a separate evidence-integrity item:
> "实验前的 937 B 版本**在本机未找到任何可验证副本**" … "这是一次**不可完全复原的系统配置修改**"

These are three distinct root causes and must not be merged: a runtime failure, a launch-chain
configured differently, and an unrecoverable host config mutation.

**C5 (rows 50, 51, 52) — the version question.** 008 `TARGET_VERSION_VERDICT.md`:
> "它是 CODOL `3.19.26.22`（构建号 `1649370`）… **它不是 3.9.9.7。** 目标目录中没有任何 3.9.9.7 证据。"
yet `CODOL-BATTLE-SERVER-CLIENT-IDENTITY-007/BLOCKERS.md` opens with
> "**BLK-007-00 — 本地没有可归属于 CODOL 3.9.9.7 的客户端映像。**"
and 006 `BLOCKERS.md` says "3.9.9.7 仅出现在四份任务报告的"目标版本"行."

Correction needed by any reader: **the entire 006/007 series is blocked on a version that does not
exist**, while 008, 009, 034, 035, 037, 038–050, and every E-series report work against 1649370 /
3.19.26.22. BLK-008-01 is marked "需用户裁定" but the verdict file issued a CONFIRMED determination
in the same task. Status: CONTRADICTORY resolution; the effective target is 3.19.26.22 / 1649370.

---

### Group D — OOB state machine (035)

**D1 (rows 53–60).** From `CONFIRMED_VS_UNKNOWN.tsv` — proven with exact instruction addresses:
`getchallenge 0 "%s"` @ `0x1C071E`, `connect %s "%s"` @ `0x1C0D6E`, 28 ordered userinfo keys,
`stats` @ `0x1C0E26`, `heartbeat` @ `0x1C0EBB`, throttles 3000/100/500 with state guards,
7 reply tokens with ASCII-fold comparison.

Not proven (each is a separate row):
- U-03: "business names of states 3/4/5/6 … no Free/Connected/Loading/Active mapping"
- BLK-035-02: "5 与 6 必由寄存器/计算写入，未定位 ⇒ 进入条件 `UNKNOWN`"
- BLK-035-03: "`[ebx+0x100260]`… `INFERRED` 为"进行中/占用"，未证"
- U-04: "only key identity + order confirmed"
- U-07/U-09: "caller-side framing not established" / "no target evidence for length bytes"
- U-10: "seed is an input parameter … not traced"
- U-08: "closes only the owning session"
- U-06: "classifier returns the token only … no state change invented"

Status for all: UNKNOWN. Crucially, 035's own summary warns:
> "即使本模块 84/84 全绿，也**只能**说明"已确认子集被正确实现"。**不能**说明真实客户端会接受我们的报文。"
This is the clearest "offline/simulated ≠ client-verified" flag in the corpus and should be
carried into any claim about OOB compatibility.

---

### Group E — server implementation & integration

**E1 (row 61) — the E2E hole.** `FREEZE-005_REPORT.md`:
> "**没有执行真实 CODOL 客户端端到端验证**，因此不得宣称"已实现客户端互通"或"可进入游戏"。"
The 251/251 selftest and 3-second UDP bind are real but server-internal only. Every later server
report (002, 003, 034, 037, 050) restates `NOT_RUN` / `NOT-OBSERVED`.

**E2 (row 62) — 2697 snapshot deliberately off.** `CURRENT_SERVER_CAPABILITIES.md`:
> "`PumpSnapshot` 在 2697 模式且未开启实验时直接返回，日志写"不下发：2697 snapshot 帧边界/delta 基准仍是 BLOCKED"。"

**E3 (row 63) — ol-mod host gate.** G-08:
> "本机唯一客户端映像 `SizeOfImage=0x0E659000`（加壳零售件）≠ 期望；三次真实启动均 `engine binding failed`，**无 stage 日志**… **一条阻断 100% 战斗链**。"
This is a hard architectural fact: the only client that exists locally is the wrong image size for
the only server that implements booking. Related to #4 (same OLFinal-vs-local image confusion).

**E4 (row 64) — record layer conflicts.** G-01:
> "**对 C-2697 从未观测**；`COOKIE_ECHO` 189 vs 219 冲突（CONFLICT-01/BQ-10）；记录层加密原语在旧源与 C# 间存在 AES192/Tiger192 vs AES128/SHA1 描述冲突（BQ-11）。"

**E5 (rows 65, 66) — the two worlds.** G-06: "**两个世界未接线**——冻洁大厅基线（REF_LOBBY_KIT）不加载 ol-mod 插件".
G-07: "实测客户端把对局流量送 **外部腾讯 `101.67.36.18:10035`**（`gcloudvoice.dll`），`28960` 出现 **0 次**".
Note G-07 is an *observation* (`NOT_OBSERVED` for 28960), while G-06 is a *structural* fact
(a code dependency that does not exist). Different statuses, recorded as separate items.

**E6 (row 67) — server internal inconsistencies.** `050/00_FINDINGS.md`:
> "其默认配置同时写着 map=mp_firingrange、gametype=coop 与 session_map=mp_crash_tropical；这会让导出的会话地图与服务器实际地图不一致。"
and "`SessionDescriptor.BuildMissionSessionObject` 的地址块将 127.0.0.1:28960 写死，`SessionExporter.Build` 调用它时未传递配置的 `session_endpoint`".
These are two separate defects (map mismatch; endpoint not threaded) and are recorded, not fixed,
"由于该描述符也包含历史黄金向量和大厅契约，本轮只记录这些不一致".

**E7 (rows 68, 69) — stride and sample identity.** B-05 "客户端分片步长 1154 vs 1162 未裁决"
contrasts with `CODOL-BATTLE-SERVER-PROTOCOL-002/00_INDEX.md` which asserts "1162 B 分片" as
supported by local evidence. These two are in direct tension within the same corpus and should be
read as UNRESOLVED. A-07: "目标 E3823FD6..F37B 本机不存在" — needs an engineering ruling.

**E8 (row 72) — plugin tests.** G-20: "9 个插件专属文件 **31,953 行**… 不在任何测试目标… 当前最大工程风险".

---

### Group F — E-series errata worth tracking

These are recorded because the corpus is linear and readers will hit the old claims first.

- **E13 → E14**: "`0x60E5B0` 是协议状态机候选" REFUTED; it is `vsnprintf`. (E14 finding #1)
- **E14 → E15**: "TLS 解密后的明文" → "REFUTED：无明文外传"; the OpenSSL path is a 1-byte
  readiness peek inside libcurl's update module. (E15 §2)
- **E13 → E16**: `0x1B0430` "通用 socket 事件管理" → ICMP ping/`IcmpSendReply2`; `0x78772D`
  "含 .tvm0 调用" → timestamp conversion. (E16 §2)
- **E12 → E13**: "收包函数 → 环形缓冲的调用边 BLOCKED" → "REFUTED（限定范围）": 0 edges in a
  179-function closure and 0 references to the ring-buffer globals.
- **E08 → E09**: count1 = 16 bit PROVEN, 8 bit REFUTED. E09 also corrected the bit-reader identity:
  "实为 RVA 0x1AC670（126 调用点）；0x1A07B0 是 `.def` 脚本字段读取器".
- **E08 → E14**: A2 count 10 bit → 11 bit (E14 finding #7).
- **E19 → E20**: "type 1 → size 1、type 2 → size 9" REFUTED.
- **E21 → E22 → E23**: `.tvm0` → `.data` BSS → `.text` (two successive corrections of the same
  five addresses; the final answer is `.text`).
- **E26 → E27**: "Demonware 服务端对端不存在" narrowed to "不存在于 `codol_dedrun.exe`";
  a peer exists in the workspace but targets a different build.

---

## 3. Status roll-up

Counts below are mechanically generated from the master table above (77 rows total), mapping
each label to its primary class. An item whose label is compound (e.g. `PASS (STATIC BEHAVIOR
RECORDED) / UNRESOLVED (runtime)`) is counted once, at its primary class.

| Status class | Count | Item numbers |
|---|---:|---|
| OPEN | 16 | 1, 9, 10, 11, 12, 13, 20, 26, 44, 46, 47, 48, 49, 52, 66, 69 |
| BLOCKED | 9 | 2, 3, 14, 15, 16, 17, 22, 28, 63 |
| CONTRADICTORY / CONFLICTED | 8 | 6, 7, 8, 37, 42, 50, 64, 75 |
| INFERRED / OFFLINE-ONLY (not client-validated) | 8 | 24, 29, 33, 34, 35, 39, 54, 71 |
| REFUTED / OBSOLETE (earlier claim corrected) | 8 | 18, 19, 23, 25, 32, 73, 74, 77 |
| UNKNOWN | 8 | 53, 55, 56, 57, 58, 59, 60, 68 |
| CONFIRMED-structural (facts that constrain implementation) | 6 | 4, 5, 30, 31, 38, 51 |
| NOT_IMPLEMENTED | 4 | 62, 65, 67, 72 |
| NOT_EXECUTED | 3 | 41, 61, 70 |
| PARTIALLY_RESOLVED | 2 | 21, 36 |
| UNRESOLVED | 2 | 40, 45 |
| INVALID_PRECONDITION | 1 | 43 |
| RESOLVED | 1 | 76 |
| UNVERIFIED | 1 | 27 |

Reading the roll-up: **25 of 77** items are genuinely still open or blocked (OPEN 16 + BLOCKED 9),
**9** are UNKNOWN or UNVERIFIED (8 + 1, no evidence either way), and **8** are contradictory (two
reports disagree). The 8 REFUTED items are not live defects but must still be matched against
anyone citing the superseded report.

## 4. Cross-cutting observations

1. **VA/RVA misuse is the single most productive bug class in this corpus.** It caused at least
   four documented false conclusions (040–044 §A5, E06 M-01, E08 M-01, E22/E23 §B3) and is
   currently suspected in one more (E24 `0xD48F48` §B4). E08 recommends elevating
   "地址基准自检" to a mandatory step; 045-C4 and 046 both re-state the rule.
2. **"Offline test green" is repeatedly written next to a warning that it does not mean client
   compatibility.** The strongest statements are 035 ("只能说明已确认子集被正确实现"), FREEZE-005
   ("没有执行真实 CODOL 客户端端到端验证"), and CODEC-KEYFLOW ("NOT-OBSERVED 不得改写").
   No report in this set claims client interop.
3. **Three distinct "there is no client receive path" conclusions were all overturned**, and the
   current state is a *single missing edge* (A1) rather than an absence. 046 explicitly reframes
   it: "其余 A 类问题…都**依赖**这条链… 使该问题**首次成为可执行的静态任务**".
4. **The 3.9.9.7 target (006/007) is a phantom.** Any downstream work that cites those two
   directories is citing a version that does not exist on disk.
