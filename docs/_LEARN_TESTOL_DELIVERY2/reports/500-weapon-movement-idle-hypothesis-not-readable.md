# 500 · **"那个『狙击镜抽搐』的假设【无法【从【任何现有的日志里【读出来**"** —— `sv_weapon_movement_mp.*` 的九个阶段、`lastIdleFactor`/`weaponIdleTime` 的两个输入、以及一个**只用于诊断**的探针

## 一、范围

本报告学习 `sv_weapon_movement_mp.cpp`（**`166` 行**）+ `.hpp`（**`9,150` 字节**，已读 90 行）：`viewState_t` 与 `weaponState_t` 两个 ABI、三个 `valid*` 校验、`SV_SaveWeaponMovementState` 的指针所有权、以及那个 `SvWeaponMovementIdleDiagnostics` 的九阶段采样。

## 二、**"那个『狙击镜抽搐』的假设无法从任何现有的日志里读出来"**（本组最重要的一段）

### 2.1 那段

```cpp
// OLMOD(scope-idle-quantifier 2026-10-09): WHAT THE NATIVE IDLE/BOB STAGES
// RETURNED, CARRIED OUT OF THE TRANSACTION SO A DIAGNOSTIC LINE CAN READ IT.
//
// `lastIdleFactor` and `weaponIdleTime` are the two inputs of the native idle
// stage (sub_4355D0 0x0355D0 -- see the ABI note above: `a1[7] lastIdleFactor,
// read AND written`, `**((int **)a1 + 8) -- weaponIdleTime dereferenced as a
// pointer`). Neither reaches the snapshot, so the "sniper scope twitches"
// hypothesis "the idle phase is rebuilt from a non-advancing weaponIdleTime
// every frame" cannot be read from any existing log.
//
// These are DIAGNOSTIC ONLY: nothing consumes them, and they are not part of
// any native ABI. Remove with the probe.
```

### 2.2 二十四层

```text
1. **`lastIdleFactor` 与 `weaponIdleTime` 【是【那个原生 idle 阶段的**两个输入**】
2. ⇒ **⇒ （`sub_4355D0` 的 `a1[7]` 被**读并写**，而 `**((int **)a1 + 8)` ⇒ `weaponIdleTime` 被**当作指针解引用**）**
3. ⇒ **⇒ ⚠ 而【两者【都【不【到达【那个**快照**
4. ⇒ **⇒ 所以【那个"狙击镜抽搐"的假设**】（**"那个 idle 相位【每帧【从【一个【不推进**的 `weaponIdleTime` 【重建"**）**
5. ⇒ **⇒ 【不能【从【任何现有的日志**读出来**
```

### 2.3 ⭐⭐⭐ **"两者都不到达那个快照，所以那个假设无法从任何现有的日志里读出来"**

**✅ 这是本报告里**最重要的一条"**一个**不可观测的**状态**"**。**

**✅ 与 §464 的"`SvSwayPhase` 的生产者：我方零生产者 ⇒ 客户端每快照被种 0 ⇒ 摆动按快照率锯齿化 = 拉回/抽搐"**——**完全同族** ✓

**⇒ 三层**：
```text
§464  **`SvSwayPhase` 零生产者 ⇒ 摆动【锯齿化**
§500  **`lastIdleFactor`/`weaponIdleTime` 【不到达快照** ⇒ **⇒ 那个**狙击镜抽搐【的假设【不可测**
⇒ **⇒ 两次【同一个**不可观测【的状态**
```

**✅ ⭐⭐⭐ **"同一个不可观测的状态"两例** —— 而**§464 的那个是**已定的**，§500 的这个【还【是【一个**假设**】**。**

**⚠ 而那个**九阶段的采样表**】**。**

**⇒ 十六层**：
```cpp
// OLMOD(scope-idle-quantifier): *weaponIdleTime sampled AFTER each bound
// stage, in call order --
//   0 damageKick 1 idle 2 viewBob 3 adsBob
//   4 base 5 sway 6 recoil 7 weaponBob 8 setAngles
// The idle stage only READS the counter, so the pair that differs names
// the stage that advances it.
std::array<std::int32_t, 9> stageWmTime{};
```
```text
1. **九个阶段，按**调用顺序**】
2. ⇒ **⇒ 而【每一个之后【采样 `*weaponIdleTime`**】
3. ⇒ **⇒ 而【那个 idle 阶段【只**读**那个计数器**】
4. ⇒ **⇒ 所以【那个**不同的对【命名了【那个**推进**它的阶段**
5. ⇒ **⇒ 而那【是【一个**极精巧的**差分探测**
```

**✅ ⭐⭐⭐ **"那个不同的对命名了那个推进它的阶段"** —— 一个**极精巧的差分探测**。

**✅ 与 §494 的"`stageWmTime`"**——**不同**，但与 §481 的"那个报告器被声明在第一个拒绝之前"**同族**（**第七次"一个**诊断的位置**"**）。

**⚠ 而"`frameTimeMs`"**】**。**

**⇒ 三层**：
```text
`frameTimeMs` ⇒ **一个**单独**的字段**
⇒ **⇒ 而【那【让【一个读者【能【把 `stageWmTime` 的差【除以【那个**帧时间**
```

**✅ ⭐⭐⭐ **"那让一个读者能把 stageWmTime 的差除以那个帧时间"**。

**✅ 而"它们**只用于诊断**，没有东西消费它们，而它们不是任何原生 ABI 的一部分"**⇒ **一个**极强的**范围声明**。**

**⇒ 三层**：
```text
"These are DIAGNOSTIC ONLY: nothing consumes them, and they are not part of
any native ABI. Remove with the probe."
⇒ **⇒ 所以【一个**未来的**读者【可以【安全地【删除**它们**
```

**✅ ⭐⭐⭐ **"一个未来的读者可以安全地删除它们"** —— 与 §462 的"`altForceTest` 保留但不要用"**相反**（**那里【保留**，这里【可以【删除**）**。**

## 三、**`viewState_t` 的九个字段与那个 ABI 的偏移**（本组第二重要）

### 3.1 那段

```cpp
// CODREF(g_build_weapon_state): exact x86 CODOL viewState_t layout recovered
// from CG_OffsetFirstPersonView 0x0051D3B0 and shared stage consumers. This
// remains caller-owned and may enter native code only through the guard.
//
// CONFIRMED ON out.exe. The addresses above are 3.3.3.3's -- this file was
// byte-identical to that tree and its comments were never re-derived -- but
// every offset in it is right on this build, read off the two bound stages:
//     sub_4353E0  ViewMovementDamageKickRva 0x0353E0
//         a2[0] playerState   a2[1] damageTime   a2[2] time
//         a2[3] damagePitch   a2[4] damageRoll
//     sub_4355D0  ViewMovementIdleAnglesRva 0x0355D0
//         a1[6] frameTime   a1[7] lastIdleFactor, read AND written
//         **((int **)a1 + 8) -- weaponIdleTime dereferenced as a pointer
```

### 3.2 二十四层

```text
1. **那个布局【从 `CG_OffsetFirstPersonView 0x0051D3B0` 【恢复**】
2. ⇒ **⇒ 而【那个**地址是 3.3.3.3 的**】⇒ **⇒ 因为【这个文件【曾是【逐字节相同**的**
3. ⇒ **⇒ 而【它的注释【从未【被【重新**推导**
4. ⇒ **⇒ 但【每一个偏移【在这个 build 上【都**对**】⇒ **⇒ 从【那两个**绑定的**阶段**读出来**
5. ⇒ **⇒ `sub_4353E0` ⇒ `a2[0]` playerState / `a2[1]` damageTime / `a2[2]` time / `a2[3]` damagePitch / `a2[4]` damageRoll**
6. ⇒ **⇒ `sub_4355D0` ⇒ `a1[6]` frameTime / `a1[7]` lastIdleFactor（读且写）/ `**((int **)a1 + 8)` weaponIdleTime（指针）**
```

### 3.3 ⭐⭐⭐ **"那些地址是 3.3.3.3 的 —— 这个文件曾与那棵树逐字节相同，而它的注释从未被重新推导 —— 但每一个偏移在这个 build 上都对"**

**✅ 与 §497 的"同一个常数住在两个地方"**——**一个精确的对照** ✓

**⇒ 三层**：
```text
§497  **一个**过时的**注释【与【一个**修正的**常量**
§500  **一个**过时的**地址【而【那个**布局【仍然**对**
⇒ **⇒ 两次"一个**未更新的注释**"】（**而【§500 的【那个【结果【是**无害的**）
```

**✅ ⭐⭐⭐ **"一个未更新的注释，而 §500 的那个结果是无害的"** —— 一个**重要的区分**。

**⚠ 而"这个文件曾与那棵树逐字节相同"**】**。**

**⇒ 十层**：
```text
"byte-identical to that tree"
⇒ **⇒ 所以【它【是【一个**没有被** CODOL 专属的**重写【碰过**的文件**
⇒ **⇒ 而【那【意味着【那个布局【是【**引擎共享**的
```

**✅ ⭐⭐⭐ **"那个布局是引擎共享的"** —— 与 §498 的 `allocateMapMetadataLua` 的重复**不同**（**那里【是【一个**复制**，这里【是【一个**共享的**布局**）**。**

**⚠ 而 `a1[7]` 的**读且写**】**。**

**⇒ 十层**：
```text
`a1[7] lastIdleFactor, read AND written`
⇒ **⇒ 所以【那个阶段【既【读【那个值【又【写**它**
⇒ **⇒ 而【那【意味着【它【是【一个**累加器**（**`lastIdleFactor` 【推进【每帧**）**
```

**✅ ⭐⭐⭐ **"lastIdleFactor 是一个累加器"** —— 而**那【正是【那个"狙击镜抽搐"假设【的核心**（**如果它不推进，那个 idle 相位就每帧重建**）**。**

## 四、`SV_SaveWeaponMovementState` 的指针所有权检查

### 4.1 那段

```cpp
if (!validCalculatedState(input) ||
    input.weaponIdleTime != &clientState.weaponIdleTime)
{
    return false;
}
```

### 4.2 二十四层

```text
1. **`input.weaponIdleTime` 【必须【恰好【是 `&clientState.weaponIdleTime`**】
2. ⇒ **⇒ 而【那【排除了【一个【指向【**别处**的指针**
3. ⇒ **⇒ 所以【那个原子候选【被【保护**免受【一个**外来的**写者**
```

### 4.3 ⭐⭐⭐ **"那个指针必须恰好是那个持久状态的地址"**

**✅ 与 §472 的"`connectionAnnounced_` 必须比那个槽活得更久"**——**不同**，但与 §481 的"地址绑定的 entityState"**同族**（**第四次"一个**地址【的**身份**"**）。

**⇒ 三层**：
```text
§481  **`encoded ^ fieldAddress ^ ~key`**（**⇒ 那个地址【是【一个**密钥**）
§500  **`input.weaponIdleTime != &clientState.weaponIdleTime`**（**⇒ 那个地址【是【一个**身份**）
⇒ **⇒ 两次【一个**地址【的**语义**"**
```

**✅ ⭐⭐⭐ **"一个地址的语义"两例**。

**⚠ 而那个 `auto next = clientState;` 的**拷贝 + 校验 + 提交**】**。**

**⇒ 十层**：
```cpp
auto next = clientState;
next.lastIdleFactor = input.lastIdleFactor;
...
if (!validClientState(next)) return false;
clientState = next;
return true;
```
```text
1. **先**拷贝**】⇒ **⇒ 改【那个**副本**
2. ⇒ **⇒ 然后【校验【那个**副本**
3. ⇒ **⇒ 然后【提交**】
4. ⇒ **⇒ 所以【一个**原子的**保存回**
```

**✅ ⭐⭐⭐ **"一个原子的保存回"** —— 与 §495 的"那个溢出循环"、§477 的"玩家半程"**同族**（**第五次"一个**两阶段**"**）。

**⚠ 而 `validCalculatedState` 比 `validClientState` **多了 `bobAngles` 与 `shellShock*`**】**。**

**⇒ 十层**：
```text
`validClientState` ⇒ 11 个检查（**那个**持久**的状态**）
`validCalculatedState` ⇒ 那些 + `bobAngles` + `shellShockDuration` + `shellShockFadeTime`（**⇒ 一个**计算后**的状态**）
⇒ **⇒ 所以【那个**超集【是【那个**语义**的（**一个计算出的状态【有更多**字段**）**
```

**✅ ⭐⭐⭐ **"那个超集是那个语义的"**。

## 五、`SV_MeleeAttackResult` 的对照：`SvWeaponMovementState` 的两个 `valid*` 的**重复**

### 5.1 那两段

```cpp
// validClientState：11 个检查
return std::isfinite(state.damagePitch) && std::isfinite(state.damageRoll) &&
    std::isfinite(state.lastIdleFactor) && finiteVector(state.baseAngles) &&
    finiteVector(state.baseOrigin) && finiteVector(state.recoilAngles) &&
    finiteVector(state.recoilSpeed) && finiteVector(state.swayAngles) &&
    finiteVector(state.swayOrigin) && finiteVector(state.swayViewAngles);

// validCalculatedState：那些 + 3
return state.playerState && state.weaponIdleTime && ... &&
    finiteVector(state.bobAngles) &&
    state.shellShockDuration >= 0 && state.shellShockFadeTime >= 0;
```

### 5.2 二十四层

```text
1. **`validClientState` 【检查【那个**持久**状态的 11 个字段**
2. ⇒ **⇒ 而 `validCalculatedState` 【检查【那些 + 3**
3. ⇒ **⇒ ⚠ 而【那 11 个【被【**逐字**重复了一遍**
```

### 5.3 ⭐⭐⭐ **"那 11 个检查被逐字重复了一遍"**

**✅ 与 §498 的 `allocateMapMetadataLua` 的重复**——**完全同族** ✓

**⇒ 三层**：
```text
§498  **`allocateMapMetadataLua` 【逐字重复** `allocate`】
§500  **`validCalculatedState` 【逐字重复** 那 11 个检查**】
⇒ **⇒ 两次【一个**逐字的重复**】
```

**✅ ⭐⭐⭐ **"一个逐字的重复"两例** —— 而 **§500 的【可以【被【提取**成【一个**共享的谓词**）**。**

**✅ 与 §497 的"同一个常数住在两个地方"**——**同族**（**第三次"一个**重复的**病灶**）**。**

**⇒ 归纳**：
```text
① §497 一个**常数**（两个文件）
② §498 一个**函数**（两个文件）
③ §500 一个**谓词**（同一个文件的两处）
⇒ **⇒ 三种**重复**【三种**粒度】
```

**✅ ⭐⭐⭐ **"三种重复三种粒度"**。

## 六、"那个原生适配器【加上【更严格的**当前守卫**"

### 6.1 那段

```cpp
// OLMOD(server-weapon-movement-frame): generic builder validation.
// The native adapter adds stricter current guards such as nonzero
// frame time and unsupported shellshock rejection.
```

### 6.2 二十四层

```text
1. **这个通用构造器【接受 `frameTime >= 0`**】（**⇒ 包含**零**）
2. ⇒ **⇒ 而【那个原生适配器【加上【更严格的**当前守卫**】
3. ⇒ **⇒ 例如【非零**帧时间**】⇒ **⇒ 与【不支持的 **shellshock 拒绝**
```

### 6.3 ⭐⭐⭐ **"通用构造器接受 frameTime >= 0，而原生适配器加上非零"**

**✅ 与 §499 的"`Missed` 是一个独立的返回值"**——**同族**（**第二次"一个**分层的**校验**"**）。

**⇒ 三层**：
```text
通用 ⇒ **`frameTime >= 0`**（**⇒ 一个**宽松**的契约**）
原生 ⇒ **`frameTime != 0`**（**⇒ 一个**严格**的契约**）
⇒ **⇒ 所以【那个**分层【是【由【那个**消费者**决定**的**
```

**✅ ⭐⭐⭐ **"那个分层是由那个消费者决定的"** —— 与 §496 的"从什么出现了来决定"**同族**。

**⚠ 而 `shellShockFadeTime{ 3000 }` 的**默认值**】**。**

**⇒ 十层**：
```cpp
struct SvWeaponMovementFrameInput
{
    const SvNativePlayerState *playerState{};
    float xyspeed{};
    float frameTime{};
    std::int32_t time{};
    std::int32_t shellShockStart{};
    std::int32_t shellShockDuration{};
    std::int32_t shellShockFadeTime{ 3000 };
};
```
```text
`shellShockFadeTime = 3000` ⇒ **一个**默认的 3 秒**
⇒ **⇒ 而那【是【那个**only** 一个【有默认值的**字段**
⇒ **⇒ 所以【那【是【一个**有意的**默认**
```

**✅ ⭐⭐⭐ **"那是唯一一个有一个默认值的字段，所以那是一个有意的默认"**。

## 七、`SV_IsWeaponMovementOutputValid` 的五项

### 7.1 五项

```text
① viewAngles 有限
② weaponAngles 有限
③ gunPitch 有限
④ gunYaw 有限
```

### 7.2 二十四层

```text
1. **四个**检查**】（**两个向量 + 两个标量**）
2. ⇒ **⇒ 而【注释说**："**让枪的角度【能【喂【枪口计算【与【快照侧的状态**之前的【最终事务守卫**"
3. ⇒ **⇒ 所以【那【是【那个**最后**一道**
```

### 7.3 ⭐⭐⭐ **"让枪的角度能喂枪口计算与快照侧的状态之前的最终事务守卫"**

**✅ 与 §471 的"`input-invalid` 是一个线程局部的诊断"**——**同族**（**第三次"一个**最终守卫**"**）。

**⇒ 三层**：
```text
§471  **`SV_BulletFireFailed("input-invalid")`**（**那个**子弹【的**最后**守卫**）
§500  **`SV_IsWeaponMovementOutputValid`**（**那个**枪角【的**最后**守卫**）
⇒ **⇒ 两次【一个**最后守卫**】
```

**✅ ⭐⭐⭐ **"一个最后守卫"两例**。

**⚠ 而"`gunPitch` 与 `gunYaw`"**⇒ **一个**枪的**两个角度**。**

**⇒ 三层**：
```text
`viewAngles` ⇒ **那个**视图**的（`3` 个）**
`weaponAngles` ⇒ **那个**武器**的（`3` 个）**
`gunPitch`/`gunYaw` ⇒ **那个**枪**的（`2` 个）
⇒ **⇒ 所以【三个**层级**】（**视图 / 武器 / 枪**）
```

**✅ ⭐⭐⭐ **"三个层级：视图 / 武器 / 枪"**。

## 八、关键结论

1. **⭐⭐⭐ "`lastIdleFactor` 与 `weaponIdleTime` 是那个原生 idle 阶段的两个输入（`sub_4355D0` 的 `a1[7]` 被读并写，而 `**((int **)a1 + 8)` ⇒ `weaponIdleTime` 被当作指针解引用）。**两者都不到达那个快照**，所以那个『狙击镜抽搐』的假设『那个 idle 相位每帧从一个不推进的 `weaponIdleTime` 重建』**不能从任何现有的日志读出来**"`** ⇒ **"同一个不可观测的状态"**（与 §464 的 `SvSwayPhase` **完全同族**，而 §464 的那个是**已定的**，这个还**是一个假设**）。
2. **⭐⭐⭐ 那九阶段的差分探测**：**"`*weaponIdleTime` 在每一个绑定的阶段之后被采样，按调用顺序 —— `0 damageKick 1 idle 2 viewBob 3 adsBob 4 base 5 sway 6 recoil 7 weaponBob 8 setAngles`；那个 idle 阶段只**读**那个计数器，所以**那个不同的对命名了那个推进它的阶段**"`** ⇒ **"那个不同的对命名了那个推进它的阶段"**（**一个极精巧的差分探测**）；而 `frameTimeMs` **让一个读者能把那个差除以那个帧时间**。
3. **⭐⭐⭐ "这些只用于诊断：没有东西消费它们，而它们不是任何原生 ABI 的一部分。**随那个探针一起删除**"`** ⇒ **"一个未来的读者可以安全地删除它们"**（与 §462 的"`altForceTest` 保留但不要用"**相反**）。
4. **⭐⭐⭐ `viewState_t` 的布局"从 `CG_OffsetFirstPersonView 0x0051D3B0` 恢复；那些地址是 3.3.3.3 的 —— 这个文件曾与那棵树**逐字节相同**而它的注释从未被重新推导 —— 但**每一个偏移在这个 build 上都对**，从那两个绑定的阶段读出来"`** ⇒ **"一个未更新的注释，而 §500 的那个结果是无害的"**（与 §497 的"一个过时的注释与一个修正的常量"**一个重要的区分**）；而 **"那个布局是引擎共享的"**（与 §498 的 `allocateMapMetadataLua` 的重复**不同**）。
5. **⭐⭐⭐ `a1[7] lastIdleFactor, read AND written`** ⇒ **"lastIdleFactor 是一个累加器"** —— 而 **那正是那个"狙击镜抽搐"假设的核心**（如果它不推进，那个 idle 相位就每帧重建）。
6. **⭐⭐⭐ `SV_SaveWeaponMovementState` 的指针所有权检查**（`input.weaponIdleTime != &clientState.weaponIdleTime ⇒ false`）⇒ **"那个指针必须恰好是那个持久状态的地址"** ⇒ **"一个地址的语义"**（与 §481 的"地址是一个密钥"同族：**那里地址是一个密钥，这里地址是一个身份**）。
7. **⭐⭐⭐ 那个原子的保存回**（`auto next = clientState` → 改 → `validClientState(next)` → `clientState = next`）⇒ **"一个原子的保存回"**（与 §495/§477 同族）。
8. **⭐⭐⭐ `validCalculatedState` 把 `validClientState` 的 11 个检查**逐字重复了一遍**（再加 `bobAngles`/`shellShock*`）⇒ 与 §498 的 `allocateMapMetadataLua` 同族 ⇒ **"一个逐字的重复"** —— 而与 §497 构成 **"三种重复三种粒度"**（**一个常数 / 一个函数 / 一个谓词**）。
9. **⭐⭐ "这个通用构造器接受 `frameTime >= 0`（包含零），而那个原生适配器加上更严格的当前守卫（非零帧时间、不支持的 `shellshock` 拒绝）"** ⇒ **"那个分层是由那个消费者决定的"**（与 §496 同族）；而 **`shellShockFadeTime{3000}` 是唯一一个有默认值的字段** ⇒ **"一个有意值的默认"**。
10. **⭐⭐ `SV_IsWeaponMovementOutputValid` 的四项**（`viewAngles` / `weaponAngles` / `gunPitch` / `gunYaw`）⇒ **"让枪的角度能喂枪口计算与快照侧的状态之前的最终事务守卫"** ⇒ **"一个最后守卫"**（与 §471 同族）；而 **三个层级**（视图 / 武器 / 枪）。

## 九、`sv_weapon_movement_mp` 全文件总览

**`.cpp`：`166` 行。`.hpp`：`9,150` 字节。**

**`4` 个结构**：`SvWeaponMovementClientState`（12 字段）/ `SvWeaponMovementIdleDiagnostics`（5 字段，含 `stageWmTime[9]`）/ `SvWeaponMovementFrameInput`（7 字段）/ `SvViewMovementState` / `SvWeaponMovementState`。

**`5` 个函数**：`finiteVector` / `validClientState` / `validFrameInput` / `validCalculatedState` / `SV_IsWeaponMovementOutputValid` / `SV_BuildViewMovementState` / `SV_BuildWeaponMovementState` / `SV_SaveWeaponMovementState`。

**`3` 个反汇编锚点**：`CG_OffsetFirstPersonView 0x0051D3B0` / `ViewMovementDamageKickRva 0x0353E0`（`sub_4353E0`）/ `ViewMovementIdleAnglesRva 0x0355D0`（`sub_4355D0`）。

**`9` 个阶段**：`damageKick` / `idle` / `viewBob` / `adsBob` / `base` / `sway` / `recoil` / `weaponBob` / `setAngles`。

## 十、未闭合点

- `SvViewMovementState` / `SvWeaponMovementState` 的完整字段表（`.hpp` 后 90 行未读）。
- `sub_4353E0` / `sub_4355D0` 之外的那些阶段（`viewBob`/`adsBob`/`base`/`sway`/`recoil`/`weaponBob`/`setAngles`）的 RVA。
- 那个"狙击镜抽搐"问题的当前状态（§464 说 sway 相位零生产者）。
- 下一个文件：`sv_weapon_loadout_mp.cpp`（`6,092`）或 `sv_native_pmove_mp.cpp/.hpp`。
