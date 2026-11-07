# 313 · **`14,610 / 93,042` 的自然语料测量**、`CharacterModelIndexBootstrap = 6`、`64 位命名空间`的两次确认

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 1–200 行（文件开头）。

## 二、23 个 `#include`

### 2.1 四组

```text
本目录的头             sv_snapshot_mp.hpp
server_mp 的依赖       sv_client_spawn_mp / sv_missile_mp / sv_map_triggers_mp /
                       sv_zm_ground_mp / sv_zm_window_motion_mp /
                       sv_zm_door_motion_mp / sv_zm_power_motion_mp /
                       sv_zm_perk_machines_mp / sv_use_object_mp
qcommon                com_math / net_chan_mp
同目录其它             sv_gamestate_mp / sv_const_baselines_mp / sv_killcam_archive_mp
shared                 RuntimeLog
标准库                 17 个
```

### 2.2 而十个 `sv_zm_*` / `sv_*_mp` 的依赖

**⇒ 所以快照写入器**直接依赖 zm 的九个运动/机器模块**。**

**⇒ 而 `sv_zm_ground_mp`/`sv_zm_window_motion_mp`/`sv_zm_door_motion_mp`/`sv_zm_power_motion_mp`/`sv_zm_perk_machines_mp` 五个** —— 与 §144 的 ZM/Factory 部分对应。

## 三、`AgentStateFieldCodecs` 的**24 个编码**（本组第二重要）

```cpp
constexpr std::array<std::int32_t, SvAgentState::FieldCount> AgentStateFieldCodecs{
    -58, -100, -100, -57, -97, 16, -57, -100,
    10, 12, -97, -57, 32, 10, 10, 6,
    10, 6, 10, 6, 11, 11, 11, 6,
};
```

### 3.1 24 个

**⇒ `SvAgentState::FieldCount == 24`。**

### 3.2 五种负值 + 八个正值

```text
负值（特殊语义）  -58   -100×2   -57×3   -97×2
正值（位宽）      16, 10, 12, 32, 10, 10, 6, 10, 6, 10, 6, 11, 11, 11, 6
```

**⇒ 让我数一遍：**

```text
-58   ×1
-100  ×2
-57   ×3
-97   ×2
16    ×1
10    ×4
12    ×1
32    ×1
6     ×4
11    ×3
```

**⇒ 1+2+3+2+1+4+1+1+4+3 = 22。**

**⚠ 我数到 22 而应该是 24。**

**⇒ 让我按位置精确列：**

```text
索引  0: -58
      1: -100
      2: -100
      3: -57
      4: -97
      5: 16
      6: -57
      7: -100
      8: 10
      9: 12
     10: -97
     11: -57
     12: 32
     13: 10
     14: 10
     15: 6
     16: 10
     17: 6
     18: 10
     19: 6
     20: 11
     21: 11
     22: 11
     23: 6
```

**⇒ 24 个 ✓（我上面数错了）**

### 3.3 而 `validAgentState` 的**四层检查**

```cpp
if (state.agentNum >= 24) return false;                       // ①
const SvAgentState nativeDefault{};
for (field = 0; field < state.fields.size(); ++field)
{
    const auto value = state.fields[field];
    const auto codec = AgentStateFieldCodecs[field];
    if (codec == -57 && value > 1) return false;               // ②
    if (codec == -100 && !isfinite(bit_cast<float>(value))) return false;  // ③
    if (codec > 0 && codec < 32 && value != SvAgentState{}.fields[field] && value >= (1u << codec))
        return false;                                          // ④
}
```

### 3.4 四项

```text
① agentNum < 24
② -57 ⇒ bool（≤ 1）
③ -100 ⇒ float 且有限
④ 正 codec（< 32）⇒ value < (1 << codec)【除非等于默认值】
```

### 3.5 而**四种负 codec 的语义**

```text
-58    ？            （无检查 ⇒ 可能是一个 enum 或 int）
-100   float         （isfinite 检查）
-57    bool          （≤ 1）
-97    ？            （无检查 ⇒ 可能是一个 uint16 或 int）
```

**⇒ 所以四种负值里只有两种有检查。**

### 3.6 而 `codec == 32` 的**无检查**

**⇒ 因为 `codec < 32` 的条件 ⇒ **32 被跳过**。**

**⇒ 一个 32 位的值不需要上界检查。**

**✓ 正确。**

### 3.7 而 `value != SvAgentState{}.fields[field]` 的**默认值豁免**

**⇒ 三层**：

```text
1. 如果 value 等于**默认值** ⇒ 不检查位宽
2. ⇒ 因为默认值可能**故意超界**（例如负数当哨兵）
3. ⇒ 所以这是一个"默认值豁免"
```

**✅ 与 §242 的"`addressable` 作哨兵"同族（第十次"哨兵豁免"）。**

## 四、`actorTorsoAnimation` 的**八个映射**

```cpp
switch (agent.fields[SvAgentState::AttachmentField])
{
case 264: return agent.fields[12] == 7 ? 1204 : 1202;
case 289: return 1206;
case 463: return 1192;
case 466: return 1195;
case 479: return 1208;
case 480: return 1209;
case 481: return 1210;
case 482: return 1211;
case 484: return 1213;
default: return 0;
}
```

### 4.1 **八个 case + 一个特殊**

```text
264 ⇒ fields[12] == 7 ? 1204 : 1202    ← 【一个条件】
289 ⇒ 1206
463 ⇒ 1192
466 ⇒ 1195
479 ⇒ 1208
480 ⇒ 1209
481 ⇒ 1210
482 ⇒ 1211
484 ⇒ 1213
```

**⇒ **九个** case（含 264 那个条件分支）。**

### 4.2 而 `AttachmentField` 是**索引**而八个值是**附件 id**

**⇒ 所以"某个特定的附件装备时用某个躯干动画"。**

**✅ 与 §297 的 `SvZmOutfit` 的 `body`/`head`/`torso`/`lower` 的模型 id 配合。**

**⚠ 而这里的 264/289/463/... 是**什么种类的 id**？**

**⇒ 从 `fields[SvAgentState::AttachmentField]` 看是**AgentState 的一个字段**。**

**⇒ 而 §313 后面可能解释。**

### 4.3 而 264 的**条件分支**

```text
264 且 fields[12] == 7  ⇒ 1204
264 且其它              ⇒ 1202
```

**⇒ 所以同一个附件有两种躯干动画，由 `fields[12]` 决定。**

**⚠ 而 `fields[12]` 是**索引 12** ⇒ 而 codec 是 **32**（唯一一个）。**

**⇒ 所以 `fields[12]` 是一个**32 位的值** —— 可能是模型的 scale 或一个变体 id。**

**✅ 与本文件开头的 `PlayerSizeScaleBootstrap = 1.0f` 相关？**

## 五、`gZmActorWalkAnim` 的**原子共享**

```cpp
// 12.154: the writer lives outside SvServerWorld, so the resolved walk
// animation is mirrored here by setZmActorWalkAnim. Atomic because the
// snapshot writer and the world update do not share a lock.
std::atomic<std::uint16_t> gZmActorWalkAnim{ 0 };
```

### 5.1 三层

```text
1. **写入者住在 `SvServerWorld` 之外**
2. ⇒ 所以解析出的行走动画由 `setZmActorWalkAnim` **镜像到这里**
3. ⇒ **原子**因为**快照写入器与世界更新不共享锁**
```

**✅ 与 §295 的 `gZmActorWalkAnim` 在 `Appmain.cpp` 里被 `setZmActorWalkAnim` 设置**完全对上** ✓**

**⇒ 所以这是一个**跨文件的无锁镜像**。**

**⚠ 而 §296 说 476 是 `ai_zombie_boardtear_l_1` ⇒ 所以 `gZmActorWalkAnim` 的默认 0 会显示 476（回退）。**

## 六、`PlayerKinematicsDiagnostics = true` 的**编译期开关**

### 6.1 那段

```php
// Bring-up diagnostics only. Both paths format large records from hot
// gameplay loops and write through RuntimeLog's shared lock. Factory now
// has the evidence those probes were added to collect; keep the code
// available for a deliberate diagnostic build without charging normal
// zombie play for it.
// OLMOD(aim-state-probe 2026-10-09): switched ON to answer the
// "sniper scope twitches / the reticle is pulled back" report. This
// is a COMPILE-TIME flag and the block below is log-only: it prints
// the server's own playerState.viewAngles next to the accepted
// usercmd's buttons and angles, once a second per client. Flip back
// to false to remove the cost entirely.
constexpr bool PlayerKinematicsDiagnostics = true;
```

### 6.2 五层

```text
1. **只在扶持期诊断**：两条路径从**热游戏循环**格式化大记录并通过 `RuntimeLog` 的**共享锁**写
2. Factory 现在有了那些探针要收集的证据
3. ⇒ **保留代码以便一次刻意的诊断构建，而不为正常僵尸游戏收费**
4. **`OLMOD(aim-state-probe 2026-10-09)`：打开了**以回答**"狙击镜抖动 / 分划被拉回"的报告**
5. ⇒ 这是一个**编译期标志**而下面那块**只有日志**
6. ⇒ 它每秒每客户端一次打印**服务器自己的 `playerState.viewAngles`** 与**被接受的 usercmd 的 buttons 与 angles**
7. ⇒ **翻回 `false` 完全移除成本**
```

### 6.3 而**"狙击镜抖动 / 分划被拉回"**是一个玩家报告

**✅ 与 §311 的"`0x100000` 是右键"、§273 的"进图之后很卡一会儿"同族**（第十一次"玩家原话"）。

**⇒ 而这里比较的是 `playerState.viewAngles` 与 `usercmd.angles`。**

**⇒ 所以核心问题是"服务器记的视角与服务端收到的 usercmd 角度是否一致"。**

**✅ 与记忆里"`aiming` 失效未归因：候选之一是字段20 `pm_flags`"**相关**。**

### 6.4 而"**编译期而非运行期**"

**⇒ 与 §270 的 `BulletTraceDiagnostics = false` 同族。**

**⇒ 而这里是 `true`（打开）⇒ 所以**当前有成本**。**

## 七、`zombieRouteDiagnosticsEnabled` 的**三项**

```cpp
static const bool enabled = [] {
    const auto *value = std::getenv("OLMOD_ZM_ROUTE_DIAGNOSTICS");
    return value != nullptr && value[0] != '\0' &&
        !(value[0] == '0' && value[1] == '\0');
}();
```

### 7.1 三层

```text
value 非空指针
value[0] != '\0'        （非空串）
非精确 "0"
```

**⇒ 所以默认**关**（未设置 ⇒ `value == nullptr` ⇒ false）。**

**⇒ 而 "0" 也关，其它任何非空值都开。**

**✅ 第十七种解析。**

## 八、**`CharacterSelectionBitWidths` 的 11 个**（本组第三重要）

```cpp
constexpr std::array<std::uint8_t, 11> CharacterSelectionBitWidths{
    7, 4, 8, 8, 6, 7, 8, 5, 0, 8, 0,
};
constexpr std::size_t CharacterSelectionMaximumPayloadBitCount = [] {
    std::size_t result = CharacterSelectionBitWidths.size();      // ← 【11】
    for (const auto width : CharacterSelectionBitWidths) result += width;
    return result;
}();
static_assert(CharacterSelectionMaximumPayloadBitCount == 72);
```

### 8.1 11 个位宽

```text
7, 4, 8, 8, 6, 7, 8, 5, 0, 8, 0
```

**⇒ 和 = 7+4+8+8+6+7+8+5+0+8+0 = 61**

**⇒ 而 `61 + 11 = 72`** ✓

### 8.2 **加 11 是因为"每一项有一个存在位"**

**⇒ 三层**：

```text
1. 11 项，每项有一个**存在位**（1 位）
2. ⇒ 所以总位数 = 11 + 61 = 72
3. ⇒ **`static_assert(== 72)`**
```

**✅ 与本文件后面的 `CharacterSelectionStorageBitCount == 76` 对照 —— 两个不同的位数。**

### 8.3 而**两个 0 位宽**

```text
索引 8: 0
索引 10: 0
```

**⇒ 所以第 9 与第 11 项**没有载荷位**（只有存在位）。**

**⚠ 而 §309 说"**`selectionIds[0]` 有 7 位宽（1..128 合法）"** ⇒ 索引 0 是 7 位 ✓**

**✅ 与 §309 完全一致。**

### 8.4 而 §309 说"`viewmodelIndex` 是十位（0x3FF）"

**⚠ 那不在这个 11 项的数组里。**

**⇒ 所以 `viewmodelIndex` 是**另一个字段**。**

**✅ 与 §309 的"三个字段三种位宽"一致。**

## 九、`ClientInfoCustomizationStorageFields` 的**八个**

```cpp
constexpr std::array ClientInfoCustomizationStorageFields{
    { 20, 10 }, { 21, 10 }, { 22, 10 }, { 27, 10 },
    { 31, 10 }, { 32, 10 }, { 33, 10 }, { 34, 6 },
};
constexpr std::size_t CharacterSelectionStorageBitCount = [] {
    std::size_t result{};
    for (const auto &field : ClientInfoCustomizationStorageFields) result += field.bitCount;
    return result;
}();
static_assert(CharacterSelectionStorageBitCount == 76);
```

### 9.1 八个 + 76 位

```text
20: 10    21: 10    22: 10    27: 10
31: 10    32: 10    33: 10    34: 6
⇒ 10×7 + 6 = 76
```

**✅ 算术闭合。**

### 9.2 而 `fieldIndex` 是 **ClientInfo 的字段号**

**⇒ 与 §310 的"`CG_SetupClientCharacterInfo` 把 netfields 21..32 交给 `sub_80E600`"对比**：

```text
§310  netfields 21..32（12 个）
§313  fields 20,21,22,27,31,32,33,34（8 个）
```

**⚠ 两组不同的字段号。**

**⇒ 而 §310 的是**服装位掩码**而这里是**选择 id 存储**。**

**⇒ 两个不同的通道。**

**✅ 与 §309 的"`optionMask[12]` = netfields 21..32 = 12"与这里的"8 个字段 76 位"是**两条不同的路**。**

## 十、**`14,610 / 93,042` 的自然语料测量**（本组最重要的一段）

### 10.1 那段完整的测量

```php
// THE AUTHORITATIVE NATURAL CAPTURE THAT TODO ASKED FOR, 2026-08-26. Mining
// the retail corpus for this exact field -- clientState index 17, +0x150,
// four bits, 14,610 clientState entries across 93,042 snapshots -- gives:
//
//     6 x377    7 x117    0 x83    8 x27
//
// A real server sends 6, 7, 8 or 0. It NEVER sends 1, which is what this
// placeholder had been sending on every player since it was written. Zero is
// the documented "clear all ten character model slots", so the non-zero set
// is {6, 7, 8} and 6 is the dominant one by three to one.
//
// Kept as one replaceable owner because the SELECTOR is still unported: 6/7/8
// is a three-value namespace this side cannot yet compute per character, and
// the faction/gender split is the obvious candidate for what picks between
// them. What has changed is that the constant is now a value a real server
// actually sends rather than one it never does.
constexpr std::uint8_t CharacterModelIndexBootstrap = 6;
```

### 10.2 八层

```text
1. **权威的自然语料捕获，2026-08-26**
2. 挖**正是这个字段**：`clientState index 17`、`+0x150`、**四位**
3. ⇒ 语料：**93,042 个快照里 14,610 个 clientState 条目**
4. **分布：`6 ×377`、`7 ×117`、`0 ×83`、`8 ×27`**
5. ⇒ **一个真实的服务器发 6、7、8 或 0** ⇒ **它【从不】发 1**
6. ⇒ 而 1 **就是这个占位符自写出来起对每个玩家发的**
7. ⇒ **零是文档化的"清空全部十个角色模型槽"** ⇒ 所以非零集是 **`{6, 7, 8}`** 而 **6 以三比一占主导**
8. ⇒ **保留为单一可替换所有者**因为**选择器仍未移植**：`6/7/8` 是一个**本侧还不能按角色计算的三值命名空间**
```

### 10.3 而**四个数的比例**

```text
6  × 377    63.0%
7  × 117    19.5%
0  ×  83    13.9%
8  ×  27     4.5%
总   × 604
```

**⚠ 而 377+117+83+27 = 604。**

**⇒ 而 604 ≠ 14,610。**

**⇒ 所以 604 是**有值的样本数**而 14,610 是**总 clientState 条目数**。**

**⇒ 所以**大多数是别的值**（未在语料中出现的？）**

**⚠ 或者 604 是"从 14,610 里挖出来的这四类"。**

**⇒ 注释说 "gives: 6 x377 7 x117 0 x83 8 x27" —— 所以是**四类的计数**。**

**⇒ 而 93,042 / 14,610 ≈ 6.37 ⇒ 所以每 6.4 个快照一个 clientState 条目？**

**⚠ 或者 14,610 是**某个子集**。**

**⇒ 无论如何"1 从不出现"是最强的结论。**

### 10.4 **"从不发 1"** 与 §309 的"占位符 1"

**§309**："`viewmodelIndex = 1` 是最小合法占位符"

**⚠ 而这里是 `modelIndex` 的占位符也曾是 1。**

**⇒ 所以**两个不同的字段**都曾用 1 作占位符：**

```text
modelIndex（+0x150，4 位）     曾发 1 而真实服务器从不发 1
viewmodelIndex（10 位）        发 1 ⇒ 是 defaultvehicle ⇒ 致命
```

**✅ 两个字段两个占位符两个后果。**

### 10.5 而"**待推导：一旦选择器找到就按角色推导 6/7/8**"

**✅ 与 §309 的 `TODO` **完全相同的措辞** ✓**

**⇒ 所以两个文件记录同一个未解决问题。**

### 10.6 而"**faction/gender 分裂是挑选它们之间的显而易见候选**"

**⇒ 三层**：

```text
1. `6/7/8` 是一个三值命名空间
2. ⇒ 本侧**还不能按角色计算**
3. ⇒ **faction/gender 分裂**是"什么在它们之间挑选"的**显而易见候选**
```

**✅ 一个**具体的待验证假设**。**

## 十一、`PlayerSizeScaleBootstrap = 1.0f` 的**三项**

```php
// OLMOD(player-size-bootstrap): CODOL's retained consumer chain proves
// playerState +0x98 -> entityState +0x54 -> DObj +0xC8. BO1/Ghosts do
// not have this field, and the deleted CODOL initializer is not
// recoverable from the client. This single owner prevents a zero-scale
// DObj while keeping the exit condition explicit and searchable.
// TODO(CODOL): replace it only after a CODOL ClientSpawn/GSC writer or
// authoritative natural capture establishes the producer and value.
constexpr float PlayerSizeScaleBootstrap = 1.0f;
```

### 11.1 三层

```text
1. CODOL 保留的消费者链证明 `playerState +0x98` → `entityState +0x54` → `DObj +0xC8`
2. **BO1/Ghosts 没有这个字段**，而删除的 CODOL 初始化器**不能从客户端恢复**
3. ⇒ 这个单一所有者**防止一个零 scale 的 DObj** 同时把退出条件保持**显式且可搜索**
```

### 11.2 而**三个偏移的链条**

```text
playerState +0x98   ⇒ entityState +0x54   ⇒ DObj +0xC8
```

**⇒ 与记忆里"DObj stride **`0xD8`**"**不同的 `0xC8`。**

**⚠ `0xD8` 是**stride** 而 `0xC8` 是**字段偏移**。**

**✓ 不冲突。**

### 11.3 而"**防止一个零 scale 的 DObj**"

**⇒ 三层**：

```text
1. 零 scale ⇒ DObj 不可见
2. ⇒ 所以 1.0f 是最小安全值
3. ⇒ 而"退出条件显式且可搜索"（`TODO` + 常量名）
```

**✅ 与 §309 的"bootstrap 6 是合法值"同族**（第十二次"bootstrap 不是待改进的占位符"）。

## 十二、**`currentAngles` 是仅有 YAW 的**（本组第四重要）

### 12.1 那段完整的跨 build 对照

```php
// CODREF(client_think_real): the orientation of a live player's hit
// skeleton is gentity_s::r.currentAngles, and it is YAW ONLY.
//   BO1    ClientThink_real 0x005F9980: 0x005FAAAE/0x005FAAC0/
//          0x005FAAD3 write all three components zero, then
//          0x005FAAE7 writes currentAngles[1] = ps.viewangles[1].
//   Ghosts ClientThink_real 0x140114E10: 0x140115783 pitch = 0,
//          0x14011578A roll = 0, 0x1401157B8 yaw = <view yaw>.
//   CODOL  SV_PointTraceToEntity 0x005FB510 reads gentity_s +0x154,
//          builds the entity axis from it (sub_C9B6E0, which is VA
//          0x005FB6E0 -- ONE 3.3.3.3 address written in the i64's
//          +0x6A0000 coordinates, not a second build's, section 81a;
//          it sits just past SV_PointTraceToEntity itself, which is
//          what an inlined AnglesToAxis helper should look like)
//          and transposes the trace start/end into that frame
//          before DObjTraceline. BO1's symbolised twin
//          SV_TracePointToEntity 0x00720940 spells the same two calls
//          AnglesToAxis(touch->r.currentAngles, entAxis) /
//          MatrixTransposeTransformVector43.
// Leaving this at zero does not merely lose a cosmetic angle: every
```

### 12.2 三个 build 的对照

```text
BO1     0x005F9980 ClientThink_real
        0x005FAAAE/0x005FAAC0/0x005FAAD3  【三个分量写零】
        0x005FAAE7                        currentAngles[1] = ps.viewangles[1]
Ghosts  0x140114E10 ClientThink_real
        0x140115783 pitch = 0
        0x14011578A roll = 0
        0x1401157B8 yaw = <view yaw>
CODOL   0x005FB510 SV_PointTraceToEntity 读 gentity_s +0x154
        sub_C9B6E0 = VA 0x005FB6E0        ← 【一个 3.3.3.3 地址】
```

### 12.3 **三个 build 都"只有 yaw"**

**⇒ 三层**：

```text
1. 一个活玩家的命中骨架的方向是 `gentity_s::r.currentAngles`
2. ⇒ 而它**只有 YAW**
3. ⇒ 三个 build 各自用不同方式证明（BO1 写零+写 [1]、Ghosts 三行、CODOL 读 +0x154）
```

### 12.4 而 `sub_C9B6E0` 的**地址混淆**

```text
sub_C9B6E0，它是 VA 0x005FB6E0
—— 一个 3.3.3.3 地址写在 i64 的 +0x6A0000 坐标里，不是第二个 build 的
```

**⇒ 四层**：

```text
1. `sub_C9B6E0` **就是** VA `0x005FB6E0`
2. ⇒ 因为**一个 3.3.3.3 地址写在 i64 的 `+0x6A0000` 坐标里**
3. ⇒ **不是第二个 build 的**
4. ⇒ §81a
```

**⚠ 一个**地址坐标系的混淆** —— 与 §245 的 `dword_1C1D188 ^ 0xFBB2C97A` 同族。**

### 12.5 而"**它正好坐在 `SV_PointTraceToEntity` 自己后面**"

```text
it sits just past SV_PointTraceToEntity itself, which is
what an inlined AnglesToAxis helper should look like
```

**⇒ 三层**：

```text
1. 它**正好坐在 `SV_PointTraceToEntity` 自己后面**
2. ⇒ 那正是一个**内联的 `AnglesToAxis` 助手应该看起来的样子**
3. ⇒ 所以这是同一个函数的一部分而不是一个独立的
```

**✅ 与 §164 的"`AnglesToQuaternion` vs `AngleVectors`"**相关**。**

### 12.6 而"**把它留零不只是丢一个装饰性的角度**"

**⇒ 所以**骨架方向为零 ⇒ 命中全错**。**

**✅ 与 §266 的"`toLocal` 用三个零向量 ⇒ 所有 trace 在原点"**完全同族** ✓**

## 十三、关键结论

1. **`AgentStateFieldCodecs` 24 个**，含四种负值（`-58`/`-100`/`-57`/`-97`）与八个正值。
2. **四种负值只有两种有检查**（`-100` float、`-57` bool）。
3. **`codec == 32` 跳过上界检查**（正确）。
4. **"默认值豁免"** —— 默认值可以故意超界。
5. **`actorTorsoAnimation` 九 case**，其中 264 有 `fields[12] == 7` 的条件分支。
6. **`gZmActorWalkAnim` 是无锁跨文件镜像**（原子，因为不共享锁）。
7. **`PlayerKinematicsDiagnostics = true`**（编译期，当前有成本）—— 为"狙击镜抖动"报告。
8. **`CharacterSelectionBitWidths` 11 项和 61 + 11 存在位 = 72**。
9. **`ClientInfoCustomizationStorageFields` 8 个 = 76 位**（10×7 + 6）。
10. **⭐ `14,610 / 93,042` 的自然语料测量**：`6 ×377`、`7 ×117`、`0 ×83`、`8 ×27`。
11. **"一个真实的服务器从不发 1"** —— 而占位符一直发 1。
12. **零是"清空全部十个角色模型槽"** ⇒ 非零集 `{6,7,8}`，6 以三比一占主导。
13. **"`6/7/8` 是三个值而本侧还不能按角色计算"** —— faction/gender 分裂是候选。
14. **`PlayerSizeScaleBootstrap = 1.0f`** 防零 scale DObj，而链条是 `playerState +0x98 → entityState +0x54 → DObj +0xC8`。
15. **`currentAngles` 只有 YAW** —— 三个 build 各自证明。
16. **`sub_C9B6E0` = VA `0x005FB6E0`**（3.3.3.3 地址写在 i64 的 `+0x6A0000` 坐标里）。
17. **"它正好坐在 `SV_PointTraceToEntity` 后面"** ⇒ 所以是内联的 `AnglesToAxis`。
18. **"把它留零不只是丢一个装饰性的角度"** ⇒ 命中全错。

## 十四、未闭合点

- `-58` 与 `-97` 两个负 codec 的语义。
- `fields[12]` 的 32 位值是什么。
- `14,610` 与 `604` 的关系。
- 6/7/8 的 faction/gender 假设是否已验证。
- `sv_snapshot_mp.cpp` 200 行之后未读取（1.47 MB）。
