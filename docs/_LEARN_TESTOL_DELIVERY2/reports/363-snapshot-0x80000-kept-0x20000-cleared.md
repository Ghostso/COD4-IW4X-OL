# 363 · **"这个写入器把它【完全反了】"** —— `0x80000` 是保留的而 `0x20000` 是要清的、IW3 的 eFlags **左移两位**、`0x280000` 而非 `0xA0000`

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 16800–17200 行。

## 二、**`0x80000` 与 `0x20000` 的完全反转**（本组最重要的一段）

### 2.1 那段

```php
// CODREF(player_die): a settled corpse's eFlags is EXACTLY
// 0x80000 - clear 0x20000 and every low player bit, and KEEP
// the re-initialise bit. This writer had it exactly inverted.
//
// MEASURED across ~18 corpse lives in the dm demo; the settle is
// always the same shape and 0x80000 is by far the most common
// corpse eFlags value seen (n=29):
//     ent25 0xA0002@78400  -> 0x80000@80600
//     ent27 0xA0002@88500  -> 0x80000@90500
//     ent28 0xA0202@102000 -> 0x80000@103400
//     ent29 0xA0206@106200 -> 0x80000@109100
//     ent35 0xA0002@132400 -> 0x80000@134600
// i.e. spawn 0x80000|0x20000|<player bits>, settle 0x80000,
// 1.4..2.9 s later - which is after the death animation.
//
// Clearing 0x80000 and LEAVING 0x20000 set is what made the body
// vanish the instant the animation ended: 0x20000 is the bit that
// makes sub_BB89E0 skip the entire per-client animation-state
// initialisation, so the client stops presenting the entity. The
// observed symptom was exactly "body vanishes at ~1.5-2 s", which
// is this deadline, deathAnimationDuration being 1616..1818 ms.
//
// Holding 0x80000 forever does NOT reset the corpse every frame:
// CG_ResetEntity runs on entity reset, not per frame, and a live
// probe measured exactly one reset per corpse.
state.eFlags = SvCorpseReinitialiseFlag;
```

### 2.2 十九层

```text
1. **一具已落定的尸体的 eFlags 恰好是 `0x80000`**
2. ⇒ **清 `0x20000` 与每一个低位玩家位，并【保留】重新初始化位**
3. ⇒ **这个写入器把它【完全反了】**
4. ⇒ **跨 dm demo 里【约 18 条尸体生命】测量**
5. ⇒ **落定总是同样的形状，而 `0x80000` 是迄今为止最常见的尸体 eFlags 值（n=29）**
6. ⇒ **五个实测样本**：
     · `ent25 0xA0002@78400 → 0x80000@80600`
     · `ent27 0xA0002@88500 → 0x80000@90500`
     · `ent28 0xA0202@102000 → 0x80000@103400`
     · `ent29 0xA0206@106200 → 0x80000@109100`
     · `ent35 0xA0002@132400 → 0x80000@134600`
7. ⇒ **即 spawn = `0x80000 | 0x20000 | <玩家位>`，settle = `0x80000`**
8. ⇒ **1.4..2.9 秒后 —— 那在死亡动画之后**
9. ⇒ **清 `0x80000` 而【保留 `0x20000` 置位】正是让身体在动画结束的瞬间消失的原因**
10. ⇒ **`0x20000` 是那个让 `sub_BB89E0` 【跳过整个逐客户端动画状态初始化】的位**
11. ⇒ **所以客户端停止呈现这个实体**
12. ⇒ **观察到的症状正是"身体在约 1.5-2 秒时消失"**
13. ⇒ **那正是这个截止时间**
14. ⇒ **因为 `deathAnimationDuration` 是 `1616..1818` ms**
15. ⇒ **永远持有 `0x80000` 【不】让尸体每帧重置**
16. ⇒ **`CG_ResetEntity` 在【实体重置】时运行，不是每帧**
17. ⇒ **而一个活探针测到每个尸体【恰好一次】重置**
```

### 2.3 ⭐⭐ **"这个写入器把它完全反了"**

**✅ 这是本文件里**最重要的一个"完全反转"**。**

**⇒ 两个位的角色：**

```text
0x80000  重新初始化位   ⇒ **要保留**（客户端据此建立一次）
0x20000  跳过动画初始化 ⇒ **要清**（否则客户端不呈现）
```

**⚠ 而 §362 六.1 的注释说" clears eFlags 0x80000"** ⇒ **那是错误版本**。**

**⇒ 所以 §362 的**我读的那段**与这里**矛盾**。**

**✅ 而这里给出了**完整的纠正**。**

**⇒ 而 §362 六.6 我发现的"位运算与注释矛盾"现在有解释：**

```text
§362 的注释是【旧版本】（错的）
§363 的注释是【新版本】（对的，且明确说"完全反了"）
```

**✅ **我的怀疑是对的** —— 那是**两次编辑的遗留**。**

**⇒ 与 §338 的"三条遗留注释"、§347 的"两处重复的进程锁存"**第三次"遗留注释"。**

### 2.4 而**`0x20000` 的功能**

**⇒ 三层**：

```text
1. `0x20000` 让 `sub_BB89E0` **跳过整个逐客户端动画状态初始化**
2. ⇒ **所以客户端停止呈现**
3. ⇒ **所以身体消失**
```

**✅ 一个**精确到函数地址的机制。**

### 2.5 而**五个样本的完整数据**

```text
ent25  0xA0002  @78400   →  0x80000  @80600   （+2200ms）
ent27  0xA0002  @88500   →  0x80000  @90500   （+2000ms）
ent28  0xA0202  @102000  →  0x80000  @103400  （+1400ms）
ent29  0xA0206  @106200  →  0x80000  @109100  （+2900ms）
ent35  0xA0002  @132400  →  0x80000  @134600  （+2200ms）
```

**⇒ 五个间隔：`2200 / 2000 / 1400 / 2900 / 2200`**

**⇒ 范围 `[1400, 2900]` ⇒ 正是注释说的"1.4..2.9 秒"** ✓

**✅ **完全闭合。**

### 2.6 而**三种 spawn 值**

```text
0xA0002  ×3
0xA0202  ×1
0xA0206  ×1
```

**⇒ 位分解：**

```text
0xA0002 = 0x80000 | 0x20000 | 0x00002
0xA0202 = 0x80000 | 0x20000 | 0x00200 | 0x2
0xA0206 = 0x80000 | 0x20000 | 0x00200 | 0x4 | 0x2
```

**⇒ 所以：**

```text
0x80000   重新初始化（所有 5 个都有）
0x20000   跳过动画初始化（所有 5 个都有）
0x2       位 1（3 个有）
0x200     位 9（2 个有）
0x4       位 2（1 个有）
```

**✅ 而 §362 四 的 `reuseToggle = eFlags & 0x2 ^ 0x2` ⇒ **就是那个 `0x2`**。**

**✅ **完整闭合。**

### 2.7 而**"活探针测到每个尸体恰好一次重置"**

**✅ 与 §362 六.1 的"每秒重置 20 次"**矛盾**。**

**⇒ 三层**：

```text
§362 的注释说：持有它 ⇒ 每秒重置 20 次 ⇒ 永不动画
§363 的注释说：**持有它【不】每帧重置** ⇒ **恰好一次**
```

**⚠ 所以**两个注释直接矛盾**。**

**✅ 而 §363 有**探针证据**（"一个活探针测到"）**

**⇒ 所以 §363 是对的。**

**⚠ 而 §362 的注释（"每秒 20 次"）是**推导的**（从"每一个快照"推理）。**

**✅ 而 §363 是**实测的**。**

**⇒ **第二次"推导 vs 实测"（§360 的 `demoq` 也是）。**

## 三、**IW3 的 eFlags 左移两位**（本组第二重要）

### 3.1 那段

```php
// CODDIFF(eflags-shift): 3.3.3.3's eFlags are IW's SHIFTED LEFT BY TWO,
// measured twice in this build and not ported:
//   * BG_UpdatePlayerDObj 0x0040B700 gates the weapon on 0xC00 where
//     IW3 uses 0x300
//   * the corpse setup path tests 0x200000 where IW3 uses 0x80000 -
//     `f7 47 08 00 00 20 00  test [edi+8], 200000h` at ida 0x00BB86BD,
//     and edi+8 is entityState+0x08, the eFlags field itself
// So IW3's 0xA0000 (0x80000 re-init | 0x20000) is 0x280000 here.
// Sending 0xA0000 sets two unrelated bits, the client never runs
// CG_CopyCorpseInfo, corpseinfo[n].model stays empty, and
// BG_UpdatePlayerDObj frees the DObj - a corpse that exists on the wire
// and draws nothing, which is exactly what the 18:18 run showed.
state.eFlags = reuseToggle |
    (source.eFlags & ~(SvCorpseReinitialiseFlag | 0x2u)) |
    SvCorpseSpawnFlags;
```

### 3.2 十六层

```text
1. **3.3.3.3 的 eFlags 是 IW 的【左移两位】**
2. ⇒ **在这个 build 里被测量两次而没有移植**
3. ⇒ **`BG_UpdatePlayerDObj 0x0040B700` 用 `0xC00` 门控武器而 IW3 用 `0x300`**
4. ⇒ **`0xC00 / 0x300 = 4` 而 `shift 2` ⇒ `×4` ✓**
5. ⇒ **尸体设置路径测 `0x200000` 而 IW3 用 `0x80000`**
6. ⇒ **`0x200000 / 0x80000 = 4` ✓**
7. ⇒ **指令 `f7 47 08 00 00 20 00` = `test [edi+8], 200000h` 在 ida `0x00BB86BD`**
8. ⇒ **而 `edi+8` 是 `entityState+0x08`，即 eFlags 字段本身**
9. ⇒ **所以 IW3 的 `0xA0000`（`0x80000` 重新初始化 | `0x20000`）在这里是 `0x280000`**
10. ⇒ **发 `0xA0000` 会设两个【无关的位】**
11. ⇒ **客户端【从不】跑 `CG_CopyCorpseInfo`**
12. ⇒ **`corpseinfo[n].model` 保持空**
13. ⇒ **而 `BG_UpdatePlayerDObj` 释放 DObj**
14. ⇒ **一具【在线上存在而什么都不画】的尸体**
15. ⇒ **那正是 18:18 那次运行所显示的**
```

### 3.3 ⭐ **"左移两位"**

**✅ 一个**极其重要的 CODDIFF**。**

**⇒ 三层**：

```text
IW3 的位   ⇒ **左移 2 位** ⇒ 本项目
0x300      ⇒ 0xC00
0x80000    ⇒ 0x200000
0x20000    ⇒ 0x80000
0xA0000    ⇒ 0x280000
```

**⚠ 而 §362 六.5 的"spawn `0xA0002` → settle `0x80000`"**是**实测的**（不是 IW3 的）。**

**⇒ 所以：**

```text
IW3 的对应值（shift 2）：0x280008 → 0x200000
实测的 OLfinal 值：      0xA0002  → 0x80000
```

**⚠ 而**实测的是 `0x80000` 不是 `0x200000`**。**

**⇒ 所以**实测显示本 build **不**移位**？**

**⚠ 而注释说"measured twice in this build and not ported"。**

**⇒ 所以**两处代码测到移位，而实测数据是未移位的值**。**

**⚠ 一个**真实矛盾**。**

**✅ 而注释说"**not ported**" ⇒ 所以**当前代码仍用未移位的值**。**

**⇒ 所以**两处代码证据说移位，而实测数据说不移位**。**

**⚠ 而代码选择相信**实测数据**。**

**✅ 与 §360 的"崩溃说 `demoq` 是对的"**不同方向**（那里相信代码，这里相信数据）。**

**⇒ **一个精确的取舍记录。**

### 3.4 而 **`0x00BB86BD` 的指令字节**

```text
f7 47 08 00 00 20 00
```

**⇒ 拆解：**

```text
f7 /0     = test
47        = modrm: mod=01, reg=000, rm=111 ⇒ [edi+disp8]
08        = disp8 = 0x08      ⇒ [edi+0x08]
00 00 20 00  = imm32 = 0x00200000
```

**✅ 一个**完整的指令解码**。**

**⚠ 而 `00 00 20 00` 是 **`0x00200000`**（小端）✓**

**✅ 与注释的"`0x200000`"**完全一致 ✓**

### 3.5 而 **"一具在线上存在而什么都不画的尸体"**

**✅ 与 §350 的"接收了、存储了、而从未被画"**同族（**第四次"存在但不画"**）。

**⇒ 三层**：

```text
1. 尸体在线上
2. ⇒ **客户端不跑 `CG_CopyCorpseInfo`**
3. ⇒ **`corpseinfo[n].model` 空 ⇒ DObj 被释放**
4. ⇒ **所以什么都不画**
```

**✅ 与 §361 的"空资源 ⇒ 无骨骼数组 ⇒ `25 j_spine4`"**同族（**第二次"空导致不画"**）。

## 四、**尸体的"五个不同的字段"**（本组第三重要）

### 4.1 那段

```php
// CODREF(copy_to_body_que): every line below is what IW3's corpse
// producer sets, NOT a copy of the dying player's entity. The five that
// differ are eFlags, both trajectory fields, trDelta and groundEntity -
// copying those verbatim was wrong in the first pass.
```

### 4.2 五层

```text
1. **IW3 的尸体生产者的每一行**
2. ⇒ **不是死亡玩家实体的一个副本**
3. ⇒ **五个不同的**：`eFlags` / 两个轨迹字段 / `trDelta` / `groundEntity`
4. ⇒ **逐字复制那些在第一遍是【错的】**
```

**✅ 与 §360 的"pitch 与 roll 强制为零不是复制"**同族（**第二次"不要复制"**）。

### 4.3 而**五个具体的不同**

```text
eFlags            见 §363 二/三
positionTrajectoryType   1（spawn）而玩家是别的
positionTrajectoryTime   0（基线）而 IW3 是 level.time
positionTrajectoryDelta  {0,0,0} 而 IW3 是玩家速度
groundEntityNum   2046（世界）而 IW3 是 NONE
```

**✅ 而注释对 `trDelta` 的解释：**

```php
// With trType 1 the client interpolates between server origins anyway, which
// makes a trDelta inert - consistent with retail not bothering to send one.
```

**⇒ 五层**：

```text
1. **用 trType 1 时客户端反正会在服务器原点之间插值**
2. ⇒ **那让一个 `trDelta` 【惰性】**
3. ⇒ **与零售不去发一个一致**
```

**✅ 一个**优雅的自洽论证**。**

### 4.4 而**"every corpse the retail server spawns carries groundEnt 2046"**

```php
// MEASURED, dm demo: every corpse the retail server spawns carries
// groundEnt 2046 - the WORLD entity - not ENTITYNUM_NONE. IW3's
// CopyToBodyQue sets NONE; this build's traffic does not agree, and the
// traffic wins.
```

**⇒ 六层**：

```text
1. **零售服务器生成的每一具尸体携带 `groundEnt 2046`**
2. ⇒ **`2046` = 世界实体**
3. ⇒ **不是 `ENTITYNUM_NONE`（2047）**
4. ⇒ **IW3 的 `CopyToBodyQue` 设 NONE**
5. ⇒ **这个 build 的流量不同意**
6. ⇒ **而【流量获胜】**
```

**✅ 与 §360 的"崩溃说 `demoq` 是对的"**同族的**方法论**：**

**⇒ **"the traffic wins"（流量获胜）** 是一个**极好的原则陈述。**

**✅ 与 AGENTS.md 的"本地逆向 > IW4X > CoD4X"**完全一致 ✓**

**⇒ **第七次"实测优先"。**

## 五、**`idx29 = 1` 的完整澄清**（本组第四重要）

### 5.1 那段

```php
// The dm demo's "idx29 = 1" on every corpse spawn is OLfinal index 29,
// which is offset 0x54 - the scale - and NOT movementDir. See the field
// constants above. OLfinal's movementDir is index 35 and the demo never
// asserts it, so a corpse sends no movementDir: leave it at the baseline
// so this writer does not emit it.
//
// CODREF(player_die): entityState_s +0x54 -> DObj_s::scale +0xC8. The
// demo's measured value is a full-float 1.0. Inherit the dead player's
// scale, which is that same 1.0 in every observed case, and never let a
// non-positive value through - that is the zero that makes the model
// invisible. The source is the PLAYER entity, which carries +0x54 in
// playerSizeScale; the corpse writer serialises it from modelScale.
// Same struct byte, two members, so translate explicitly.
state.modelScale = source.playerSizeScale > 0.0f ? source.playerSizeScale : 1.0f;
```

### 5.2 十四层

```text
1. **dm demo 在每一次尸体生成时的 "idx29 = 1"**
2. ⇒ **是 OLfinal 的索引 29**
3. ⇒ **它的偏移是 `0x54` —— 【缩放】**
4. ⇒ **【不是】 `movementDir`**
5. ⇒ **OLfinal 的 `movementDir` 是索引 35**
6. ⇒ **而 demo 【从不】断言它**
7. ⇒ **所以一具尸体【不发】** `movementDir`
8. ⇒ **让它留在基线上，这样这个写入器不发出它**
9. ⇒ **`entityState_s +0x54 → DObj_s::scale +0xC8`**
10. ⇒ **demo 的测量值是一个【全浮点 1.0】**
11. ⇒ **继承死亡玩家的缩放**（在每一个观测案例里都是那个 1.0）
12. ⇒ **而绝不让一个非正值通过** —— **那是让模型不可见的零**
13. ⇒ **源是【玩家】实体，它在 `playerSizeScale` 里携带 `+0x54`**
14. ⇒ **而尸体写入器从 `modelScale` 序列化它**
15. ⇒ **同一个结构字节，两个成员，所以【显式翻译】**
```

### 5.3 ⭐ **"同一个结构字节，两个成员"**

**✅ 与 §343 的"`groundEntityNum` 在布告上是字段 13"**同族（**第八次"一偏移多语义"**）。

**⇒ 而这里是**在同一个 eType 内的两个成员共享一个字节**（`+0x54`）。**

**⚠ 因为**两个不同的结构重叠**（`entityState_s` 与 `DObj_s`）。**

**✅ 一个**极微妙的类型双关**。**

### 5.4 而**"绝不让一个非正值通过"**

**✅ 与 §344 的"`validScriptModel` 的 `scale > 0`"**同族（**第三次"零缩放不可见"**）。

**⇒ 三层**：

```text
1. `scale <= 0` ⇒ 模型不可见
2. ⇒ **所以强制 `> 0`，默认 1.0**
3. ⇒ **绝不发零**
```

**✅ 与 §343 的"`validActorEntity` 拒绝非正缩放"配合。**

**⚠ 所以本文件里**四处**处理"零缩放"。**

## 六、**`spawnPlayerCorpse` 的"环形槽"**（本组第五重要）

### 6.1 那段

```php
// OLMOD(player-corpse-ring): corpses do NOT come from the entity pool.
// The client indexes corpseinfo by the raw entity number with no bounds
// check, so the number IS the slot and a dynamic allocation corrupts
// the client. Walk the fixed ring instead, exactly as IW3's
// G_SpawnPlayerClone does, reusing the slot in place.
const auto entityNum = FirstPlayerCorpseEntityNum + (nextPlayerCorpseSlot_ % PlayerCorpseRingSize);
nextPlayerCorpseSlot_ = (nextPlayerCorpseSlot_ + 1) % PlayerCorpseRingSize;
```

### 6.2 八层

```text
1. **尸体不来自实体池**
2. ⇒ **客户端用【原始实体号】索引 `corpseinfo` 而【没有边界检查】**
3. ⇒ **所以号【就是】槽**
4. ⇒ **而一个动态分配会【损坏客户端】**
5. ⇒ **所以走固定环**
6. ⇒ **完全像 IW3 的 `G_SpawnPlayerClone`**
7. ⇒ **就地复用一个槽**
8. ⇒ `entityNum = FirstPlayerCorpseEntityNum + (next % RingSize)`
```

**✅ 与 §345 的"实体号被复用"**第五次。**

**⇒ 而这里是**一个极端的例子**：号是**客户端的数组索引**。**

**⚠ 所以**尸体号必须在一个固定范围内**。**

### 6.3 而**"belt and braces"的拒绝**

```php
// Belt and braces: this is the exact condition that crashed the client,
// so refuse rather than emit an out-of-ring corpse under any bug.
if (entityNum < FirstPlayerCorpseEntityNum ||
    entityNum >= FirstPlayerCorpseEntityNum + PlayerCorpseRingSize ||
    entityNum >= FirstDynamicServerEntityNum)
{
    return false;
}
```

**⇒ 四层**：

```text
1. **这是【正是】让客户端崩溃的那个条件**
2. ⇒ **所以拒绝而不是在任何 bug 下发出一个环外的尸体**
3. ⇒ **三重检查**（下界 / 环上界 / 动态实体界）
4. ⇒ **所以一个环外的尸体永不发出**
```

**✅ 与 §346 的"拒绝必须说哪一个"**同族（**一个防御性的三重检查**）。

## 七、**槽复用开关（`0x2` 的异或）与三个 build 的交叉验证**（本组第六重要）

### 7.1 那段

```php
// CODREF(g_spawn_player_clone): the slot-reuse toggle, restored after
// the cross-check AGENTS.md requires for entity lifecycle. All three
// required references agree on bit 0x2, and agree despite disagreeing
// on everything else about the ring:
//   IW3    flags = e->s.lerp.eFlags & 2 ^ 2       (base 64, count 8)
//   BO1    flags = e->s.lerp.eFlags & 2 ^ 2       (base 32, count 4)
//   Ghosts v2    = ~(unsigned __int8)eFlags & 2   (base 42, count 8)
// Three builds independently toggling the same bit is the evidence the
// demo could not give: OLfinal carries IW's unshifted layout, so it
// could not settle a bit position for a build whose eFlags are shifted.
// A client delta-compressing a new corpse against the old one in the
// same slot needs a differing bit or the body appears to teleport.
const auto reuseToggle = (corpseEntity.networkState.eFlags & 0x2u) ^ 0x2u;
```

### 7.2 十五层

```text
1. **槽复用开关，在 AGENTS.md 要求的实体生命周期交叉检查后恢复**
2. ⇒ **全部三个必需参照在 bit `0x2` 上同意**
3. ⇒ **而它们在关于这个环的【所有其它事】上都不同意**
4. ⇒ **IW3：`flags = eFlags & 2 ^ 2`（base 64，count 8）**
5. ⇒ **BO1：`flags = eFlags & 2 ^ 2`（base 32，count 4）**
6. ⇒ **Ghosts v2：`~(uint8)eFlags & 2`（base 42，count 8）**
7. ⇒ **三个 build 独立地翻转同一个位，那是 demo 【无法给出】的证据**
8. ⇒ **OLfinal 携带 IW 的【未移位】布局**
9. ⇒ **所以它不能为一个 eFlags 被移位的 build 确定一个位位置**
10. ⇒ **一个把同一槽里的新尸体对旧尸体 delta 压缩的客户端【需要一个不同的位】**
11. ⇒ **否则身体看起来会【传送】**
```

### 7.3 ⭐ **"三个 build 独立同意一个位而不同意其它一切"**

**✅ 这是本文件里**最强的交叉验证论证**。**

**⇒ 三层**：

```text
三个独立实现（IW3 / BO1 / Ghosts）
⇒ 关于 ring 的 **一切** 都不同（base 64/32/42、count 8/4/8）
⇒ **而关于 bit 0x2 完全一致**
⇒ 所以 bit 0x2 是【结构必需】而非实现细节
```

**✅ 与 §351 的"237 个间隔方程在二十个未知数上"**同族（**第二次"过定的交叉验证"**）。

### 7.4 而**"OLfinal 携带 IW 的未移位布局 ⇒ 它不能确定一个位位置"**

**✅ 一个**精确的证据边界**。**

**⇒ 三层**：

```text
1. OLfinal 的 eFlags 是【未移位】的
2. ⇒ **所以无法用 OLfinal 确定"移位后"的位位置**
3. ⇒ **所以必须用三个 build 的交叉验证**
```

**✅ 与 §347 的"这是线半而对另一半盲"**第五次"声明证据边界"。

### 7.5 而**"否则身体看起来会传送"**

**✅ 三层**：

```text
1. 同一槽 ⇒ 客户端 delta 压缩
2. ⇒ **若所有位都相同 ⇒ delta 是"未变"**
3. ⇒ **所以客户端不更新位置**
4. ⇒ **所以身体停在旧位置**（看起来"传送"）
```

**⚠ 而"传送"的说法与我推导的"停在旧位置"**略有不同**。**

**⇒ 可能"传送"指**下一次**更新时的跳变。**

**✅ 合理。**

## 八、`freeEntity` 的**事务性回滚**（本组第七重要）

### 8.1 那段

```php
// OLMOD(entity-free-native-transaction): CODOL G_FreeEntity
// 0x004E8E70 owns unlink, subsystem cleanup, slot invalidation and
// FIFO publication as one lifecycle operation. The source pool and
// fixed native mirror are separate ol-mod owners, so retain both
// images until the mirror accepts removal of this generation.
const auto previousLifetime = *entityPool_->resolve(handle);
auto previousEntity = entity->second;
// ... 保存三个 handler/state
if (!entityPool_->free(handle, snapshot_.serverTime)) return false;
// ... erase 三项 + entities_
rebuildCollisionView();
if (nativeEntityMirrorSynchronizer_ && !nativeEntityMirrorSynchronized_) {
    if (!entityPool_->rollbackFree(handle, previousLifetime)) {
        throw std::logic_error("entity free rollback lost FIFO ownership");
    }
    entities_.emplace(handle.entityNum, std::move(previousEntity));
    // ... 恢复三个 handler/state
    rebuildCollisionView();
    return false;
}
```

### 8.2 十二层

```text
1. **CODOL `G_FreeEntity 0x004E8E70` 拥有 unlink、子系统清理、槽失效与 FIFO 发布作为一个生命周期操作**
2. ⇒ **源池与固定原生镜像【是分开的 ol-mod 所有者】**
3. ⇒ **所以保留两个镜像【直到镜像接受这一代的移除】**
4. ⇒ **所以先保存**：`previousLifetime` / `previousEntity` / 三个 handler
5. ⇒ **然后 `entityPool_->free`**
6. ⇒ **erase 三项 + `entities_`**
7. ⇒ **`rebuildCollisionView()`**
8. ⇒ **若镜像同步器存在而【未同步】⇒ 回滚**
9. ⇒ **`rollbackFree` 失败 ⇒ 【抛异常】**（`std::logic_error`）
10. ⇒ **否则恢复 `entities_` 与三个 handler**
11. ⇒ **`rebuildCollisionView()` 再跑一次**
12. ⇒ **返回 false**
```

**✅ 与本文件其它事务**不同的地方：**

```text
其它   staged-then-commit（先做后提交）
这里   **do-then-rollback**（先做后回滚）
```

**⚠ 所以**两种事务策略**。**

**✅ 而这里的理由：`G_FreeEntity` 是一个**不可分割的原生操作**（无法"预演"）。**

**⇒ 所以只能**做了再撤销**。**

**✅ **第七次事务性，而第一次"回滚式"。**

### 8.3 而**"抛异常而不是静默"**

**✅ 与 §349 的"故意大声"**同族（**第二次）。**

**⇒ 三层**：

```text
1. `rollbackFree` 失败 ⇒ FIFO 所有权丢失
2. ⇒ **对象池已损坏**
3. ⇒ **所以抛异常而不是继续**
```

**✅ 一个**正确的"不可恢复则崩溃"判断。**

## 九、关键结论

1. **⭐⭐ "这个写入器把它【完全反了】"`** —— `0x80000` 是**保留的重新初始化位**而 `0x20000` 是**要清的跳过动画初始化位**。
2. **五个实测样本的完整时间线**（`+2200/+2000/+1400/+2900/+2200` ms，范围 `[1400,2900]`）。
3. **三种 spawn 值的位分解**（`0xA0002` / `0xA0202` / `0xA0206`）⇒ `0x80000|0x20000|<player bits>`。
4. **`0x20000` 让 `sub_BB89E0` 跳过整个逐客户端动画状态初始化 ⇒ 客户端停止呈现**。
5. **⚠ `§362` 的"每秒 20 次"与 `§363` 的"恰好一次"矛盾** —— 而 §363 有**活探针证据**，所以它是对的。
6. **"`CG_ResetEntity` 在实体重置时运行，不是每帧"`**。
7. **⭐⭐ IW3 的 eFlags 在本 build 【左移两位】**：`0x300→0xC00`、`0x80000→0x200000`、`0x20000→0x80000`、`0xA0000→0x280000`。
8. **指令级证据**：`f7 47 08 00 00 20 00` = `test [edi+8], 200000h` @ `0x00BB86BD`，而 `edi+8` 是 `entityState+0x08`。
9. **⚠ "两处代码测到移位，而实测数据是未移位的值"** —— 而注释说"**not ported**"⇒ 代码选择相信数据。
10. **"一具在线上存在而什么都不画的尸体"`** —— `CG_CopyCorpseInfo` 从不跑、`corpseinfo[n].model` 空、DObj 被释放。
11. **⭐ 尸体的五个字段**（`eFlags` / 两个轨迹字段 / `trDelta` / `groundEntity`）**不是从玩家复制**。
12. **"用 trType 1 时客户端反正会在服务器原点之间插值 ⇒ 让 `trDelta` 惰性"`** —— 一个优雅的自洽论证。
13. **⭐ "the traffic wins"（流量获胜）`** —— `groundEnt 2046` 而非 IW3 的 NONE（**第七次"实测优先"**）。
14. **⭐ `idx29 = 1` 是 `+0x54` 的【缩放】而不是 `movementDir`** —— 而 `movementDir` 是索引 35 而 demo **从不**断言它。
15. **"同一个结构字节，两个成员"`**（`entityState_s +0x54` 与 `DObj_s::scale +0xC8` 重叠）—— **第八次"一偏移多语义"**。
16. **"绝不让一个非正值通过 —— 那是让模型不可见的零"`**（**第三/四次"零缩放"**）。
17. **⭐ 尸体【不】来自实体池** —— **客户端用原始实体号索引 `corpseinfo` 而【没有边界检查】** ⇒ 号就是槽。
18. **三重 belt-and-braces 检查**（"这是正是让客户端崩溃的那个条件"）。
19. **⭐ 槽复用开关 `eFlags & 2 ^ 2`** —— **三个 build（IW3/BO1/Ghosts）独立同意 bit `0x2` 而关于 ring 的一切都不同**。
20. **"OLfinal 携带 IW 的未移位布局 ⇒ 它【不能】确定一个位位置"`** —— 一个精确的证据边界（**第二次过定的交叉验证**）。
21. **"一个 delta 压缩同一槽里的新尸体需要一个不同的位，否则身体看起来会传送"`**。
22. **`freeEntity` 的【回滚式】事务**（不同于全文件的 staged-then-commit）—— 因为 `G_FreeEntity` 是不可分割的原生操作。
23. **"`rollbackFree` 失败 ⇒ 抛 `std::logic_error`"`** —— 第二次"故意大声"。

## 十、未闭合点

- 为什么实测数据（`0x80000`）与代码证据（`0x200000`）矛盾。
- `SvCorpseSpawnFlags` / `SvCorpseRagdollTrajectoryType` / `SvCorpseRagdollAngleTrajectoryType` 的值。
- `SvCorpseSettleRespawnSeparationMs` 的值。
- `PlayerCorpseRingSize` / `FirstPlayerCorpseEntityNum` 的值。
- `firstDynamicServerEntityNum` 与 `FirstPlayerCorpseEntityNum + RingSize` 的关系。
- `sv_snapshot_mp.cpp` 17200 行之后未读取（27,016 行，进度 64%）。
