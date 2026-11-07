# SD 目标快照诊断

## 结论

2026-08-14 检查确认，SD 的 A/B 包点和炸弹目标并非只存在于 dedicated 的模式状态中：

- `ServerCore::projectSdObjectives` 按观察者队伍和炸弹阶段生成每个玩家独立的 32 槽目标数组；
- `SvServerWorld::setPlayerObjectives` 在 `endFrame` 前写入该玩家的 authoritative `SvPlayerState`；
- `writeObjectives` 将目标数组作为 CODOL playerstate auxiliary section 4 编码进 full/delta snapshot；
- `sv_native_playerstate_mp.cpp` 同时把相同字段投影到 CODOL 原生 playerstate 布局；
- 炸弹拾取物是 gameplay-active script mover，随实体 snapshot 发送；
- SD 语音通过原生可靠命令 `p <eventParameter>` 排队发送。

因此，后续“客户端看不到包点/炸弹”的定位重点应放在客户端字段消费、材质 configstring 映射和事件解析，而不是继续重复添加 server-only 状态。

## 诊断出口

新增只读导出 `CODOL_GameServerGetWorldObjectiveStatusV1(clientNum, ...)`，返回当前 authoritative playerstate 的活动目标数量以及前三个目标的 `state/icon`。`tools/runtime/CodolGameServerControl.py` 会把它们输出到 `objectives` 数组，供真实运行时对照 dedicated 状态和客户端画面。

该出口不改变 snapshot 编码、Pmove 或客户端行为；它只是把“目标是否进入玩家快照源状态”从推断变为可读证据。`icon` 仍须和 CODOL 客户端材质表逐项核对，不能仅凭非零值宣称 HUD 已恢复。

## 排除的错误方向

CODOL snapshot 在 playerstate 后的一位不是 BO1/BO2 的 `MatchState` presence。`CL_ParseSnapshot 0x0046D170` 在这里调用 `CL_ParsePacketSoundCommands 0x0046D060`，后者解码 44-byte 声音命令记录；最终消费者 `CG_ProcessSnapshotSoundCommands 0x0051A780 -> CG_ExecuteSnapshotSoundCommand 0x005075D0` 进入声音系统的 start/update/stop/fade 路径。BO1/BO2 的 128-byte `MatchState` 位于 playerstate 前，Ghosts 的后续 scoreboard/omnvars 也不是该记录。因此服务端继续在此写空 sound-command section，不把 round/HUD 数据塞入该位置；下一步改查模式/回合 configstring、round-start 可靠命令、objective material consumer、炸弹实体视觉与 pickup/use consumer。

## 3D 目标标记的正式链路

IW4 `_gameobjects.gsc` 将 `set2DIcon` 与 `_objpoints` 创建的 `set3DIcon` 明确分开；前者进入 objective/compass，后者进入 playerstate HudElem。CODOL reader 进一步确认 objectives 后的 auxiliary section 9 同时携带 `current[31]` 和 `archival[31]`，每项 `0xA8/42 fields`。CODOL 3D consumer 要求 waypoint type `13/14`、flags `0x4000`、有效 server-material index 与非零 alpha。dedicated 因此保留已验证的 2D objective，同时把同一组按 team 过滤后的 SD A/B、炸弹和 planted marker 投影为 archival HudElem；这不是完整 GSC HudElem VM，也没有客户端 UI 特判。
