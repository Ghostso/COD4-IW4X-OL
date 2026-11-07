# 320 · **`1004` 个 scriptmover 里 `920` 从不断言模型索引**、"发明的界是错的"、`BG_EvaluateTrajectory` 只处理 0..12

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 1399–1600 行。

## 二、`sameActorPacketEntity` 的**十五项**（续 §319）

```cpp
return left.eType == right.eType &&
    left.origin == right.origin &&
    left.angles[1] == right.angles[1] &&
    left.actorField00B4 == right.actorField00B4 &&
    (!SvActorSendUnmeasuredSpawnWords || left.events == right.events) &&
    left.actorLoopSound == right.actorLoopSound &&
    (!SvActorSendUnmeasuredSpawnWords || left.actorField0058 == right.actorField0058) &&
    left.actorVelocity == right.actorVelocity &&
    left.actorField005C == right.actorField005C &&
    left.eFlags == right.eFlags &&
    left.groundEntityNum == right.groundEntityNum &&
    left.positionTrajectoryType == right.positionTrajectoryType &&
    left.angleTrajectoryType == right.angleTrajectoryType &&
    (!SvActorSendUnmeasuredSpawnWords || left.actorField00AC == right.actorField00AC) &&
    left.actorField009C == right.actorField009C &&
    left.actorField0054 == right.actorField0054 &&
    left.actorAttackerEntityNum == right.actorAttackerEntityNum &&
    left.actorPartBits0 == right.actorPartBits0;
```

### 2.1 十八项

**⇒ 而其中**三个**被 `SvActorSendUnmeasuredSpawnWords` 守护：**

```text
events
actorField0058
actorField00AC
```

**✅ 与 §319 的"三个未解释字段"**完全一致** ✓**

**⇒ 而"关掉时**不比较**它们" ⇒ 所以**即使它们变了也不会触发 delta**。**

**✓ 一个正确的配套。**

### 2.2 而 `left.actorField009C == right.actorField009C`

**⇒ `+0x09C` 是 `actorModelIndex`（§319 的 `ActorAppearanceField = 29`）。**

**⇒ 所以**外观变化触发 delta**。**

**✓ 与"外观必须存在"配合。**

## 三、`validScriptMoverEntity` 的**eFlags 白名单**（本组第三重要）

### 3.1 那段

```php
// eFlags was pinned to 0 until the podium needed the intermission
// flag retail sets on its figures. STILL A WHITELIST -- every value
// in it is one a real server was MEASURED sending, not a range that
// lets any flag through.
//
// The retail dm demo's ET_SCRIPTMOVER eFlags, counted with
// Tools/olfinal/audit-bounds-vs-demo.py and confirmed with
// Tools/demo-re/demoq.py:
//
//     eFlags  2   33 assertions across 13 lives, first t=56600
//     eFlags 16  239 assertions across 87 lives, first t=43100
//
// 0 never appears on the wire because it is the baseline and needs
// no assertion. THIS SERVER DOES NOT PRODUCE 2 TODAY, so admitting
// it fixes nothing now -- it pre-empts a frame-wide kill later,
// because an entity that fails this predicate does not get dropped,
// it rejects the WHOLE FRAME for EVERY client. What bit 1 MEANS is
// not known and is deliberately not guessed at here.
```

### 3.2 七层

```text
1. `eFlags` 过去被钉到 0 直到领奖台需要零售在其人偶上设的中场旗标
2. ⇒ **仍然是一个白名单** —— 每一个值都是**一个真实服务器被测量发送过的**
3. ⇒ **不是让任何旗标通过的区间**
4. ⇒ demo 的计数：
     · **`eFlags 2`：33 个断言跨 13 个生命，首次 `t=56600`**
     · **`eFlags 16`：239 个断言跨 87 个生命，首次 `t=43100`**
5. ⇒ **0 从不出现在线上** 因为它是**基线**而**不需要断言**
6. ⇒ **本服务器今天不产出 2** ⇒ 所以接纳它**现在修不好任何东西**
7. ⇒ 它**预先阻止一个未来的整帧杀死** —— 因为**失败于此谓词的实体不被丢弃，它拒绝整个帧对所有客户端**
8. ⇒ **bit 1 意味着什么不知道，而这里刻意不猜**
```

### 3.3 而**五个 eFlags 值**

```cpp
(entity.eFlags == 0 ||
 // Factory board358: gravity launch31550 flags1; settled32150 flags17.
 // Both are absolute demo words, not inferred meanings.
 entity.eFlags == 1 || entity.eFlags == 17 ||
 entity.eFlags == SvEFlagsScriptMoverMeasuredBit1 ||     // = 2
 entity.eFlags == SvEFlagsIntermission)                  // = 16
```

**⇒ 五个：`0`、`1`、`17`、`2`、`16`。**

### 3.4 而 `1` 与 `17` 的**具体来源**

```text
Factory board358: gravity launch31550 flags1; settled32150 flags17
```

**⇒ 四层**：

```text
1. Factory 的 **board358**
2. ⇒ **重力发射在 `t=31550` 时 `flags=1`**
3. ⇒ **稳定在 `t=32150` 时 `flags=17`**
4. ⇒ **两个都是绝对的 demo 词，不是推断的含义**
```

**✅ 一个**具体的实测记录**。**

**⇒ 而 `17 = 16 | 1`。**

**✅ 所以 `17` 可能是 `Intermission | bit1`。**

**⚠ 但注释说"不推断含义"。**

## 四、**"`modelIndex > 0` 是一个发明的界而它对真实流量是错的"**（本组最重要的一段）

### 4.1 那段七层

```php
// `modelIndex > 0` WAS AN INVENTED BOUND AND IT IS WRONG AGAINST
// REAL TRAFFIC. Measured on the retail dm demo with
// `Tools/demo-re/demoq.py`: of 1004 ET_SCRIPTMOVER lives,
// **920 never assert xModelIndex at all** and none asserts it
// as zero -- a modelless scriptmover carrying only a position
// and a trajectory is the COMMON case, not an error.
//
// This is not a cosmetic relaxation. An entity that fails this
// validator does not get dropped: it rejects the WHOLE FRAME
// for EVERY client (see the allow-list comment in
// SV_ValidateSnapshotFrame), so one modelless scriptmover would
// stop every snapshot and the match would die on the spot.
// A figure with an unresolved model is refused where that
// decision belongs -- spawnPodiumFigures logs and skips it --
// not in the frame validator.
entity.modelIndex < ModelConfigStringCount &&
```

### 4.2 七层

```text
1. **`modelIndex > 0` 是一个【发明的界】而它对真实流量是【错的】**
2. ⇒ 在零售 dm demo 上用 `demoq.py` 测量：**1,004 个 `ET_SCRIPTMOVER` 生命里**
3. ⇒ **920 个【完全不断言】`xModelIndex`** 而**没有一个断言它是零**
4. ⇒ **一个无模型的 scriptmover 只携带一个位置与一个轨迹是【常见情况】，不是错误**
5. ⇒ **这不是一个装饰性的放宽**
6. ⇒ 因为**失败于此验证器的实体不被丢弃：它拒绝整个帧对所有客户端**
7. ⇒ 所以**一个无模型的 scriptmover 会停止每一个快照而比赛当场就死**
8. ⇒ **一个模型未解析的人偶在它该被拒的地方被拒 —— `spawnPodiumFigures` 记日志并跳过它 —— 而不是在帧验证器里**
```

### 4.3 **`920 / 1004` = 91.6%**

**⇒ 所以**绝大多数** scriptmover 没有模型。**

**⇒ 而"没有一个断言它是零"⇒ 所以模型字段**根本不发**而不是发 0。**

**✅ 与 §318 的"`movementDir` 零次断言 ⇒ 不发"同族**（第六次"零断言即不发"）。

### 4.4 而"**在它该被拒的地方被拒**"

**⇒ 三层**：

```text
1. 帧验证器**不做**业务决策
2. ⇒ 业务决策在 `spawnPodiumFigures`（它记日志并跳过）
3. ⇒ **分层正确**
```

**✅ 与 §244 的"八个出口一个返回类型"**相反 —— 这里**分层清晰**。**

### 4.5 而 `modelIndex < ModelConfigStringCount` **仍保留**

**⇒ 所以**上界**保留而**下界**去掉了。**

**✓ 一个精确的修正。**

## 五、**`+0x09C != 0` 与 `+0x0AC == 0xFFFFFF` 恰好同 238 个条目**

```php
// A BRUSH MODEL IS THE ONE ET_SCRIPTMOVER THAT CARRIES SOLID,
// AND IT CARRIES BOTH HALVES OR NEITHER. Retail's own table
// makes that a fact rather than a policy: across factory's 397
// const baselines, +0x09C != 0 and +0x0AC == 0x00FFFFFF hold on
// exactly the same 238 entries and on no others
// (re/demo-re/16-const-baselines.md). Admitting one half without
// the other puts an entity on the wire that the client's
// brush-model branch reads `world->bmodels + 60 * index` out of
// with an index it was never given.
((entity.scriptMoverBrushModelIndex == 0 && entity.solid == 0) ||
    (entity.scriptMoverBrushModelIndex > 0 &&
        entity.scriptMoverBrushModelIndex <= 0x3FF &&
        entity.solid == BrushModelSolid)) &&
```

### 5.1 六层

```text
1. **一个 brush model 是唯一携带 `solid` 的 `ET_SCRIPTMOVER`**
2. ⇒ **而它携带【两半或都不】** 
3. ⇒ 零售自己的表让那成为**事实而不是政策**：
     · **在 factory 的 397 个 const baselines 里**
     · **`+0x09C != 0` 与 `+0x0AC == 0x00FFFFFF` 恰好持有在同样的 238 个条目上**
     · **而不在其它任何条目上**
4. ⇒ **只接纳一半而不接纳另一半会把一个实体放上线**
5. ⇒ 而**客户端的 brush-model 分支从 `world->bmodels + 60 * index` 读它**
6. ⇒ **用一个它从未被给的索引**
```

### 5.2 而 `397` 与 `238` 的**第三次**

```text
§294  288/397 平台期
§302  34/238 零售发布
§318  397 个 const baselines、238 个 brush model
§320  397 与 238 恰好同
```

**✅ 四次确认，全部一致。**

### 5.3 而 `world->bmodels + 60 * index`

**⇒ 三层**：

```text
1. 客户端读 `world->bmodels[60 * index]`
2. ⇒ **60 字节步长**
3. ⇒ 而**索引是那个 `+0x09C`**
```

**⚠ 而 §262 的 `resolveBrushModelCollision` 用 `sizeof(NativeBrushModel)`。**

**⇒ 若 `NativeBrushModel` 是 60 字节则一致。**

### 5.4 而 `BrushModelSolid` 与 `0xFFFFFF`

**⇒ 三层**：

```text
`+0x0AC == 0x00FFFFFF` ⇒ `BrushModelSolid` 应该是 `0xFFFFFF`
```

**✅ 与 §318 的"`0xFFFFFF` 是 24 位"**完全一致** ✓**

## 六、**`weaponAssetIndex` 的三个分支**（本组第四重要）

```php
entity.weaponAssetIndex <= MaxCurrentWeaponAssetIndex &&
((entity.weaponAssetIndex == 0 && entity.scriptMoverParentNumPlusOne == 0 &&
    entity.scriptMoverTagIndex == 0) ||
 // CODREF(sv_write_snapshot_to_client): out.exe 520263 reads
 // centity+15C (ES+68); parent=0 skips optional tag selection at
 // 520273 but still builds the weapon DObj at 5202B4. Renderer
 // 5222B5 accepts null parent and reaches ordinary draw5231EE.
 // OLMOD(factory_weapon_display_admission): admit only the
 // non-solid, model-less standalone shape our producer owns.
 // Retain the attached-weapon guard and reject partial links.
 (entity.weaponAssetIndex != 0 && entity.scriptMoverParentNumPlusOne == 0 &&
    entity.scriptMoverTagIndex == 0 && entity.modelIndex == 0 &&
    entity.podiumClientNumPlusOne == 0 && entity.scriptMoverBrushModelIndex == 0) ||
 (entity.weaponAssetIndex != 0 && entity.scriptMoverParentNumPlusOne != 0 &&
    entity.scriptMoverParentNumPlusOne <= EntityNumWorld &&
    entity.scriptMoverParentNumPlusOne != entity.number + 1 &&
    entity.scriptMoverTagIndex != 0 && entity.modelIndex == 0 &&
    entity.podiumClientNumPlusOne == 0 && entity.scriptMoverBrushModelIndex == 0)) &&
```

### 6.1 三个分支

```text
① 无武器：weapon == 0，parent == 0，tag == 0
② 无父武器：weapon != 0，parent == 0，tag == 0，model == 0，podium == 0，brush == 0
③ 有父武器：weapon != 0，parent != 0 且 <= EntityNumWorld 且 != number+1，tag != 0，其余全 0
```

### 6.2 而 ③ 的**两个精确约束**

```text
scriptMoverParentNumPlusOne <= EntityNumWorld      （父必须是一个世界实体或编号内）
scriptMoverParentNumPlusOne != entity.number + 1   （【父不能是自己】）
```

**✅ 三层**：

```text
1. 父在编号范围内
2. ⇒ **父不能是自己**（否则挂到自己）
3. ⇒ 而 `+1` 是因为 `ParentNumPlusOne` 的编码
```

### 6.3 而 `520263` / `520273` / `5202B4` / `5222B5` / `5231EE`

**⇒ 五个地址：**

```text
0x520263   读 centity+15C (ES+68)
0x520273   parent=0 跳过可选 tag 选择
0x5202B4   仍构建 weapon DObj
0x5222B5   渲染器接受 null parent
0x5231EE   普通绘制
```

**⇒ 所以"parent=0 但仍然绘制"。**

**✅ 一个**具体的 5 点链条**。**

## 七、`validPlayerCorpseEntity` 的**两个轨迹类型上界**（本组第五重要）

### 7.1 那段

```php
// BG_EvaluateTrajectory (sub_AB29C0) Com_Errors on any trType
// it does not handle, and it handles only 0..12. A corpse that
// carries one out of range takes the client down with a dialog,
// which is what sending the demo's 13 did.
entity.positionTrajectoryType <= 12 &&
entity.angleTrajectoryType <= 12 &&
```

### 7.2 四层

```text
1. **`BG_EvaluateTrajectory`（`sub_AB29C0`）对任何它不处理的 `trType` 都 `Com_Error`**
2. ⇒ **而它只处理 0..12**
3. ⇒ 一个携带越界值的尸体**用弹窗把客户端打下来**
4. ⇒ **那就是发 demo 的 13 所做的事**
```

### 7.3 **"发 demo 的 13 把客户端打下来"**

**✅ 与 §319 的"`positionTrajectoryType == 1 || == 13`"**矛盾**？**

**⚠ §319 的 `validActorEntity` 允许 `1` 与 `13`。**

**⇒ 而 §320 的 `validPlayerCorpseEntity` 只允许 `0..12`。**

**⚠ 两个不同的 eType 不同的上界！**

**⇒ 所以 actor 可以有 `13` 而尸体不行。**

**⇒ 因为 `BG_EvaluateTrajectory` 只被**尸体的路径**调用？**

**⚠ 或者 actor 的轨迹由**另一条路**处理。**

**✅ 一个**需要核对的差异**。**

**⇒ 而与记忆里"ragdoll type **9**（demo's 13 doesn't exist）"**相关**——**

**⇒ 记忆说"ragdoll type 9 (demo's 13 doesn't exist)"！**

**⇒ 所以 **13 在 ragdoll 上不存在**。**

**✅ 而这里说"发 demo 的 13 把客户端打下来"**完全一致** ✓**

**⇒ 所以 §319 允许 actor 的 `13` 而 §320 拒绝尸体的 `13` —— **一致**（不同的 eType 不同的约束）。**

## 八、`validGeneralBrushModelEntity` 的四项

```php
// CODDIFF(sv_write_snapshot_to_client): ET_GENERAL covers more native
// entity kinds. Until their producers and fields are recovered,
// accept only the exact script_brushmodel projection proven by
// CODOL SV_LinkEntity: brush index in +0x98 and solid 0xFFFFFF.
return entity.eType == EntityTypeGeneral &&
    entity.number >= FirstDynamicServerEntityNum &&
    entity.clientNum == 0 && entity.eFlags == 0 &&
    entity.modelIndex > 0 && entity.modelIndex < 0x400 &&
    entity.solid == 0xFFFFFF && ...
```

### 8.1 而 `modelIndex > 0` 在这里**保留**

**⚠ 而 §4 刚说 `modelIndex > 0` 是"发明的界"。**

**⇒ 但那是 `ET_SCRIPTMOVER` 的（§4）而这里是 `ET_GENERAL` 的（brush model）。**

**⇒ 所以**不同的 eType 不同的约束**。**

**✅ 一个**有意的区别**（brush model 必须有模型）。**

### 8.2 而 `modelIndex < 0x400` 与 §318 的"`*N` 的 10 位"

**⇒ `0x400 = 1024` ⇒ 与 10 位一致** ✓

## 九、`validPlayerCorpseEntity` 的**六项额外**

```php
entity.solid == 0 && entity.eventParm == 0 &&
entity.otherEntityNum == 0 && entity.impactSurfaceType == 0 &&
entity.impactFlags == 0 && entity.eventSequence == 0 &&
entity.movementDir >= 0 && entity.movementDir <= 0xFF &&
entity.weaponAssetIndex == 0 &&
entity.presentationWeaponAssetIndex == 0 &&
entity.offhandWeaponAssetIndex == 0 &&
entity.coKnifeStatsIndex == 0 && entity.unk00E0 == 0 &&
entity.unk00A0 == 0 &&
all_of(entity.events, == SvEntityEvent{});
```

### 9.1 而**"尸体是 `ET_PLAYER` 的 fail-closed 子集"**

```php
// A corpse is a fail-closed subset of ET_PLAYER: the fields the eType 2
// writer emits are range-checked, and every field it does NOT emit is
// required to be zero so a stale value cannot ride along unencoded.
```

**⇒ 三层**：

```text
1. **尸体是 `ET_PLAYER` 的一个 fail-closed 子集**
2. ⇒ 它**发出的**字段被范围检查
3. ⇒ 而它**不发出的每一个字段被要求为零** ⇒ 所以**一个陈旧的值不能搭便车不被编码**
```

**✅ 一个**极严格**的模式。**

**⇒ 与 §315 的"最小合法占位符"**相反 —— 这里**严格拒绝**。**

### 9.2 而 `entity.number` 的**腐尸环检查**

```php
// NOT the dynamic range: a corpse's number is its slot in the
// client's corpseinfo array, so it must be inside the fixed
// ring. This is the exact check that would have prevented the
// entity-396 crash, and it is deliberately fail-closed.
entity.number >= FirstPlayerCorpseEntityNum &&
entity.number < FirstPlayerCorpseEntityNum + PlayerCorpseRingSize &&
```

### 9.3 四层

```text
1. **不是动态范围** —— 一个尸体的编号是它在客户端 `corpseinfo` 数组里的**槽**
2. ⇒ 所以它必须在**那个固定环内**
3. ⇒ **这正是本可以阻止 `entity-396` 崩溃的检查**
4. ⇒ 而它**刻意是 fail-closed 的**
```

### 9.4 而 `entity-396`

**⇒ 与记忆里"`PlayerCorpseRingSize = 18`、`FirstPlayerCorpseEntityNum = 19`、`FirstDynamicServerEntityNum = 37`"**

**⇒ 所以环是 `19..36`（18 个）而 **396** 远超。**

**✅ 所以 396 是一个**越界编号**。**

## 十、`unk00A0` 与 §319 的 `impactSurfaceType`

**⚠ §319 说 `EventEntityImpactSurfaceField = 15` 骑在 `unk00A0` 里。**

**⇒ 而 §320 的 `validPlayerCorpseEntity` 要求 `unk00A0 == 0`。**

**✅ 所以尸体不能用 `unk00A0` 装 impactSurface —— 因为它本来不发那字段。**

**✓ 一致。**

## 十一、关键结论

1. **`sameActorPacketEntity` 十八项**，其中三个由 `SvActorSendUnmeasuredSpawnWords` 守护。
2. **eFlags 白名单五个值**（`0`/`1`/`2`/`16`/`17`），而"`eFlags 2` 33 次跨 13 生命 / `eFlags 16` 239 次跨 87 生命"。
3. **"0 从不出现在线上因为它就是基线"**。
4. **"本服务器今天不产出 2 ⇒ 接纳它现在修不好任何东西 ⇒ 它预先阻止一个未来的整帧杀死"** —— 一个前瞻性的放宽。
5. **"bit 1 意味着什么不知道而刻意不猜"**。
6. **Factory board358：`t=31550` flags 1，`t=32150` flags 17**。
7. **⭐ `1004` 个 scriptmover 里 `920` 从不断言模型索引，没有一个断言它为 0** ⇒ **91.6% 无模型**。
8. **"一个发明的界而对真实流量是错的"** —— `modelIndex > 0` 被移除而**上界保留**。
9. **"一个无模型的 scriptmover 会停止每一个快照而比赛当场就死"**。
10. **"在它该被拒的地方被拒"（`spawnPodiumFigures`）而不是帧验证器** —— 分层正确。
11. **`+0x09C != 0` 与 `+0x0AC == 0xFFFFFF` 恰好同 238 个条目（397 个里的）** —— 第四次确认。
12. **"两半或都不"** —— 只接纳一半会让客户端读 `world->bmodels + 60 * index` 用一个未给的索引。
13. **`weaponAssetIndex` 的三个分支**，其中 ③ 要求"父不能是自己"。
14. **五个地址（`0x520263`/`0x520273`/`0x5202B4`/`0x5222B5`/`0x5231EE`）证明"parent=0 但仍然绘制"。**
15. **`BG_EvaluateTrajectory` 只处理 `0..12`** ⇒ 尸体的 `13` 会把客户端打下来。
16. **⚠ §319 允许 actor 的 `0..12` 与 `13` 而 §320 拒绝尸体的 `13`** —— 不同的 eType 不同的约束。
17. **`ET_GENERAL` 的 `modelIndex > 0` 保留**（brush model 必须有模型）。
18. **"尸体是 `ET_PLAYER` 的 fail-closed 子集"** —— 不发的字段必须为零。
19. **`entity-396` 崩溃的检查** —— 尸体编号必须在 `19..36` 的固定环内。

## 十二、未闭合点

- `NativeBrushModel` 是否 60 字节（与 `world->bmodels + 60 * index` 对齐）。
- actor 的 `13` 轨迹是由哪条路处理的。
- `eFlags 2` 的 bit 1 语义。
- `sv_snapshot_mp.cpp` 1600 行之后未读取。
