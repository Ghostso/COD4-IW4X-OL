# CODOL 破坏物与玻璃链路

本文记录当前可复用的事实、责任边界和后续恢复顺序。状态以
[`../modules/game_server.md`](../modules/game_server.md) 为准；本文不把尚未自然验证的能力写成已完成效果。

## 两套独立状态所有者

玻璃和车辆等 `destructible` 都能被子弹命中，但不是同一种实体：

- 玻璃由地图 glass piece pool 持有，使用 `SvGlassState` 的四态
  `0..3`。碰撞、伤害累计、impact 量化和 snapshot glass section 共用
  同一个 authoritative owner，不通过普通 `entityState_s` 模型替换。
- 车辆、变压器、灯具等来自 MapEnts `script_model`，先作为
  `ET_SCRIPTMOVER` 建立 XModel、DObj、link、locational trace，再由显式注册的
  generation-safe damage owner 持有 health、stage、damage gate 和 model index。
- 普通场景模型不能因为名字像车辆就自动获得 health。只有具有可信
  `destructible_type` 定义并成功解析全部必需模型的实体才能启用受伤。

共同的子弹前缀为：

```text
native PM_Weapon / predictable fire event
  -> Bullet_Endpos
  -> CODOL locational Bullet_Trace
  -> hit classification
  -> command-local damage candidate
  -> complete usercmd commit
  -> snapshot / glass section / Lua event
```

候选阶段不能直接播放 FX、写外部脚本状态或修改 world。命中产生的 health、
stage、model、glass state、presentation event 必须随整条 command 原子提交或一起回滚。

## 玻璃完成边界

已经闭合：

- CODOL 1024-piece、5-byte record、四态和 `state < 2` solid 规则。
- full/delta glass snapshot、11-bit sparse index、1024 terminator 和 destroyed
  impact 的 raw-byte/6-bit wire。
- glass damage 累计、`0xFFFE` 饱和、`0xFFFF` deleted sentinel、
  `stateChangeTime`、命中位置/方向量化。
- 非穿透子弹命中玻璃后，damage、impact、collision 与 snapshot 使用同一状态。

尚未闭合：

- CODOL-local damage threshold；当前 `25/100` 仍来自 Ghosts，带明确 TODO。
- 玩家触碰/穿过碎玻璃产生的 touch producer、声音及伤害规则。
- 穿透弹穿过玻璃后的后续 trace、厚度和能量衰减。

## Destructible 完成边界

已经闭合：

- `mp_crash_tropical` 清点出 82 个 destructible、12 种类型；其中 7 种拥有
  完全同名的 IW4-derived 主 part 阶段定义并在 production 精确注册，共 25 个 owner。
- `SvDestructibleState` 显式持有 `stageIndex/health/destroyed`，跨阶段伤害会结转，
  不从 health 或模型反推阶段。
- CODOL XModel/CCS resolver、`setmodel` transaction、server DObj replacement、
  relink 和 rollback 已接通。
- native locational trace 可直接命中真实车辆 entity；自然射击已观察到车辆
  health 和 stage mutation。
- entity damage/presentation 只在完整 command commit 后发布；
  `SV_LinkEntity` 已在每次正向 link 和 rollback relink 前安装 server animation
  condition context，消除了车辆命中后 `0x005FADA0` 异常锁死快照的问题。

当前不能宣称完成：

- 轿车中间阶段定义只有 health，`replacementModel` 为空。原版更可能使用
  part/tag、动画或局部模型状态，不能凭文件名猜模型。
- 最终 destroyed model 已解析并具备 transaction 能力，但仍需定向自然测试打到
  终态，核对客户端模型、server DObj、link 和 snapshot。
- stage sound/FX 的发布数据结构与 resolver 已有，准确 alias、FX 名和触发规则未闭合。
- 爆炸范围伤害、伤害归属、MOD、友伤、连锁破坏与一次性终态未恢复。
- destroyed 后究竟 unlink、替换 bounds/contents，还是继续使用 destroyed DObj
  碰撞尚无 CODOL 证据；不得用 `contents=0` 临时特判。
- part detach、tag/link、阶段动画和穿透延续仍缺。

## 参考证据与恢复顺序

恢复时同时核对 CODOL 本体、BO1 和 Ghosts，必要时再看 BO2：

- IW4 `_destructible.gsc` 提供与 crash 类型完全同名的阶段表和跨阶段伤害职责。
- BO1/Ghosts/BO2 `G_Damage` 约束 client、vehicle、scriptable/generic 的分派边界，
  证明不能把所有 MapEnts 统一当可受伤实体。
- CODOL i64/运行态负责最终确认 XModel、DObj、trace、snapshot、asset 名和 ABI；
  参考游戏不能替代 CODOL-local 证据。

推荐顺序：

1. 自然打到最终 destroyed state，验证现有 model/DObj/link transaction。
2. 从 CODOL 资产或脚本恢复准确的 stage sound/FX，再接现有 presentation transaction。
3. 恢复爆炸 typed damage producer、范围查询和连锁规则。
4. 从 destroyed DObj、contents、bounds 和 link 的运行差异确认终态碰撞。
5. 最后处理部件/tag/动画与穿透延续。

每一步都应记录 `health/stage/modelIndex`、server DObj、native link、snapshot
attempted/committed/failure 和客户端视觉；任何失败不得永久卡住 usercmd 队首或泄漏部分状态。
