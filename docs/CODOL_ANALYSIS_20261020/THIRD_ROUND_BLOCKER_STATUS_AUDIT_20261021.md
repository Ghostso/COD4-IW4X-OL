# THIRD_ROUND_BLOCKER_STATUS_20261021.json 审计摘要

日期：2026-10-21（Asia/Shanghai）

对象：`CODOL_ANALYSIS_20261020/THIRD_ROUND_BLOCKER_STATUS_20261021.json`

状态：**MACHINE STATUS ACCEPTED / P0 REMAINS 0/11 / WIRE AND PLAYABILITY BLOCKED**

本摘要只核对机器可读门禁字段与封口证据、现有第三轮文档的一致性。没有启动客户端、dumpcap、战斗服、Auth、Lobby、IIPS 或任何端口探测。

## 1. 文件身份

| 项 | 值 |
|---|---|
| Schema | `third-round-blocker-status/v1` |
| 更新时间 | `2026-10-21T14:22:00+08:00` |
| 字节 | 4,793 |
| SHA-256 | `4465FBA9EA769786EE16341C00D84C4A6F5F17C4F0B8E8B4AB771B30C9E2843C` |
| 解析 | 通过 |
| 顶层字段 | `schema`、`overall`、`evidence`、`protected`、`p0`、`next_run`、`disallowed_claims`、`protected_baseline` |

## 2. 总体状态复核

| 字段 | 声明 | 审计结论 |
|---|---|---|
| `p0_total` | 11 | 与 A01..A11 对齐 |
| `p0_closed` | 0 | 正确；没有任何 P0 被登记为闭合 |
| `capture_state` | `ACCEPTED_AS_PARTIAL` | 与封口包入库审计一致 |
| `wire_protocol` | `BLOCKED` | 正确 |
| `playability` | `BLOCKED` | 正确 |
| `blocking_audit` | `ALLOWED` | 正确 |
| `next_capture_preparation` | `ALLOWED` | 正确 |

## 3. 证据数值复核

| 字段 | JSON | 独立复验 | 结果 |
|---|---:|---:|---|
| `hash_entries` | 103 | 103 | 一致 |
| `hash_mismatches` | 0 | 0 | 一致 |
| `filtered_pcap_bytes` | 776 | 776 | 一致 |
| `filtered_pcap_packets` | 3 | 3 | 一致 |
| `filtered_pcap_sha256` | `F644...651E6` | 同值 | 一致 |
| `udp_28960_packets` | 0 | 0 | 一致 |
| `image_pages_total` | 58,969 | 58,969 | 一致 |
| `image_pages_read` | 0 | 0 | 一致 |
| `image_error` | 299 | 299 | 一致 |
| `gamestate_frames` | 0 | 0 | 一致 |
| `snapshot_frames` | 0 | 0 | 一致 |
| `consumer_trace` | `NOT_PRESENT` | 空占位 | 一致 |
| `ff_state` | `BLOCK0_ONLY_LAYOUT_MISMATCH` | `IWffs100` block-0 only | 一致 |

附加核对：

- `image_state=BLOCKED_AFTER_ACE` 与封口 manifest 一致；
- `tcp_3074_payload=00000000` 与原始帧一致；
- `closure`、`manifest`、`intake_audit`、`run_dir` 路径均存在；
- `hashes.sha256` 中当前 manifest 行的 SHA 与实文件一致；但 manifest 的 `hashes_file_sha256` 记录的是较早修订，形成已知的自引用时序差异；
- 门禁 JSON 只描述状态，不声称抓到 gamestate/snapshot；
- 3 帧 pcap 是 TCP，不得把其中的 TCP ACK 当成游戏层 ACK。

## 4. 受保护清单复核

| 字段 | 值 |
|---|---|
| `checked` | 9 |
| `matched` | 8 |
| `preexisting_conflict` | `REF_LOBBY_KIT/marketplace_store.py` |
| `actual_size` | 50,022 B |
| `expected_size` | 46,226 B |
| `changed_by_this_run` | false |

结论：该 JSON 正确保留了 8/9 的预先冲突，没有把它改写成 9/9。它不是本 run 新引入的破坏；但在后续基线处理前，仍需视为冻结链的已知差异。门禁不授权修改 golden、不授权重写冲突文件。

## 5. P0 字段完整性

JSON 的 `p0` 恰好包含 11 项：

```text
R3_A01 ... R3_A11
```

每项都处于非闭合状态：

- A01：`BLOCKED_AFTER_ACE`
- A02：`NOT_BOUND`
- A03/A04/A05：`NOT_CAPTURED`
- A06：`NOT_PRESENT`
- A07：`PARTIAL_BLOCK0_ONLY`
- A08/A09/A11：`NOT_CAPTURED`
- A10：`BLOCKED_ORIGINAL_PACKAGE_ABSENT`

没有发现把 `PARTIAL`、空占位或指纹命中的 block-0 提升为闭合值的条目。

## 6. next_run 规则是否符合要求

| 规则 | JSON 字段 | 审计 |
|---|---|---|
| 新 run 目录 | `fresh_directory_required=true` | 符合 |
| 先抓包再启动 | `capture_before_client=true`；timeline 首项 `dumpcap_live` | 符合 |
| 单次启动 | `single_client_launch=true` | 符合 |
| 同 PID | success gate 明确写 `same PID across the full session` | 符合 |
| 实际进入战斗 | success gate 明确写 battle 双向应用交换 | 符合 |
| gamestate/configstrings | success gate 明确包含 | 符合 |
| 至少两帧 snapshot | success gate 明确包含两帧连续 snapshot | 符合 |
| 游戏 ACK 历史 | success gate 将 ACK 与 snapshot 绑定 | 符合 |
| consumer trace | success gate 明确映射 bytes → parser/state delta | 符合 |
| 镜像覆盖 | success gate 包含 read path 与 late code | 符合 |
| layer-2 世界资产 | success gate 要求导出并 hash | 符合 |
| 保护文件前后 hash | `protected_hash_before_and_after=true` | 符合 |
| 原始包隔离 | run-local quarantine；发布只保留过滤/脱敏 | 符合 |
| required outputs | 12 个；无重复 | 符合 |

唯一需要继续保持的文字约束是“时间线顺序”与“成功门禁”不是同一件事：timeline 记录应当发生，success gate 才能决定是否进入第三轮。当前 JSON 没有把 timeline 中的字段当成已实现证据。

## 7. 不允许的结论

JSON 的 `disallowed_claims` 恰好包含 6 条：

1. P0 complete；
2. wire protocol compatible；
3. client compatibility proven；
4. playability proven；
5. 3-frame TCP/3074 sample is a battle session；
6. block-0 fastfile is layer-2 asset extraction。

这与当前审计状态一致。本摘要不新增、也不弱化这些禁止项。

## 8. 与现有文档的一致性

| 文档 | 一致性 |
|---|---|
| `COLLECT_319_20261021_132905_INTAKE_AUDIT.md` | 状态、证据数值和 P0 结论一致 |
| `THIRD_ROUND_PREREQUISITES.md` | A01..A11 状态一致；N 节规则与 JSON 对应 |
| `AUDIT_INDEX.md` | 状态串一致：P0 0/11、PARTIAL、wire/playability BLOCKED |
| 封口 manifest | 数值、错误码、pcap 摘要和 FF 状态一致 |

## 9. 结论

机器可读门禁 **可用**，但只表示“下一轮采集的准入契约已经定义”。它不阻止第三轮开放证据审查启动；它阻止的是把不完整证据升级为协议兼容、可玩性或 P0 闭合结论。它不关闭 P0，也不改变本 run 的 `LATE_CAPTURE`、`ACE_BLOCKED` 或 `PARTIAL` 判定。

当前正确动作：

- 允许：阻塞性审计、负证据整理、静态入口复核、下一轮采集设计；
- 不允许：把 3 帧 TCP/3074、block-0 或零页镜像当作正式协议证据；
- 禁止：未经新 run 与五类输入直接启动线协议或可玩性对照。

## 10. 入口

- [THIRD_ROUND_BLOCKER_STATUS_20261021.json](./THIRD_ROUND_BLOCKER_STATUS_20261021.json)
- [COLLECT_319_20261021_132905_INTAKE_AUDIT.md](./COLLECT_319_20261021_132905_INTAKE_AUDIT.md)
- [THIRD_ROUND_PREREQUISITES.md](./THIRD_ROUND_PREREQUISITES.md)
- [AUDIT_INDEX.md](./AUDIT_INDEX.md)
- [CAPTURE_CLOSURE.md](D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/runs/COLLECT_319_20261021_132905/CAPTURE_CLOSURE.md)

## 11. Baseline update (2026-10-21 14:30+08:00)

The machine status was extended after the baseline-source check. The new authoritative state is:

- `launch_authorized=false`;
- `baseline_migration=BLOCKED_PENDING_USER_DECISION`;
- current protected set remains `8/9` because of `REF_LOBBY_KIT/marketplace_store.py` (50,022 B vs golden 46,226 B);
- a byte-for-byte 9/9 source exists at `GOLDEN-LOBBY-001/REF_LOBBY_KIT`; a recursive copy reproduced 9/9;
- that source has 13 identified runtime residues (logs, certificates, session files and two off flags) and cannot be used as a clean run without an approved cleanup/migration rule;
- the original `run_all.py` uses a shared `GAME_ROOT` and defaults to six retries, so the single-shot and run-isolation gates are not yet satisfied.

Decision detail: `NEXT_RUN_BASELINE_DECISION_20261021.md`.

This update does not close P0, does not authorize a client launch, and does not change the `0/11` wire/playability status.


## 12. Revision verification

The JSON was extended after the first audit. Current revision verification is:

- bytes: 4,793;
- SHA-256: 4465FBA9EA769786EE16341C00D84C4A6F5F17C4F0B8E8B4AB771B30C9E2843C;
- new overall fields: baseline_migration=BLOCKED_PENDING_USER_DECISION, launch_authorized=false;
- protected_baseline records current 8/9 and clean source 9/9 separately;
- the clean source still has 13 runtime residues and is not an automatically clean launch tree;
- decision detail: NEXT_RUN_BASELINE_DECISION_20261021.md;
- this revision does not close P0 and does not authorize launch.
