# Preserve agent removals across empty zombie snapshots / 保留空快照中的 agent 删除记录

Status: candidate based on b55174aec4bb6651c82c48a95ec818af76eaae0c. Factory accepted through round 3; same-build two-client FFA passed. Accepted for integration.

## Problem and correction

An empty zombie snapshot selected the legacy player-list writer, omitting removals for agents from the baseline. The shipping client retains unmatched rows, so a later actor can be decoded against stale state with incorrect owner/model/attachment values. Keep the agent-aware writer when either frame uses the agent-only namespace or the baseline contains agents. Ordinary multiplayer with player-list semantics and no agent history retains its existing wire path. Animation commands, movement, spawning and model selection are unchanged.

空僵尸快照此前使用 player-only writer，未发送旧 agent 的删除记录。原生客户端保留未匹配的记录，下一波 actor 可能基于错误旧状态解码。当前帧或基线属于 agent-only 命名空间、或基线仍包含 agent 时，继续使用 agent-aware writer；无 agent 历史的普通多人模式保持原路径。

## Exact-build native evidence

IDA Professional 9.3 analysis of CODOL out.exe SHA256 044c396c90a7cfa63eac32bea194bf4dfa4d1eab547d9082ae8a575eb49257f9: sub_471980 merges 0x58-byte agent rows. At 0x471ACE and 0x471CFF it retains unmatched prior rows; only the explicit removal marker from sub_447190 removes them. Calls at 0x471BC8/0x471C84 use sub_670FF0 and the 24-field table at 0xDA63E8. Native default row 0xDA9920 supplies owner345, team2, body1266, attachments1267/1317.

The existing BO1/Ghosts snapshot-writer reference ownership remains in matrix sv_write_snapshot_to_client. This correction follows the exact CODOL consumer rather than substituting either reference game's wire format. It does not claim recovery of the original server implementation or whole-function audit coverage.

## Validation and limits

Tested gameplay DLL: 609562CE6BD7B1F1F120AA3C74FCD80AB43B1F87E0262FF91A7432F5A0B143B6.

- Release build, seven repository suites and 50-ms server suite passed.
- Production writer bodies were re-extracted for this candidate and exercised against shipping x86 readers in a private emulator. Old actor1174 -> two empty frames -> actor1171 incorrectly decoded owner348/team2/body242/head243 with the old writer. Corrected empty frames removed all rows; the next actor decoded owner1171/team1/body310/head330. These are authored protocol fixtures, not a live gameplay capture.
- Baseline Factory playtest reported a j_spine error after a recorded round1-to-2 transition. Fixed Factory playtest passed through round3; logs independently show two completed 11-second intermissions and continued snapshot acknowledgements. The live empty-agent packet sequence and exact causal chain of the baseline dialog were not captured; round3 alone cannot prove all bone errors are eliminated.
- Same-build two-real-client Nuketown dm/mp_nuked manual playtest passed. Both clients reached Playing; reciprocal combat actions were not separately instrumented assertions. No older build's acceptance applies.
- Raw logs, native binaries, IDBs and launcher tools remain local and are excluded.

Factory 实测通过至第3轮，日志独立确认两次完整间歇。原版 reader 的受控重放证明旧记录残留及修正效果；该证据与实机观察分开记录。同一构建双客户端 FFA 实测通过。
