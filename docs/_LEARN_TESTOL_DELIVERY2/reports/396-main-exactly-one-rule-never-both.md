# 396 · **"恰好一条规则生效，绝不同时用两条"** —— `xuid` 匹配不到就【失败】而不是退到地址、三个更多不持锁的 setter

## 一、范围

本报告学习 `sv_main_mp.cpp` 2400–2760 行。

## 二、**`setPlayerNoclipForSender` 的"恰好一条规则"**（本组最重要的一段）

### 2.1 那段

```php
// EXACTLY ONE RULE APPLIES, NEVER BOTH. A named xuid that matches
// nothing must FAIL rather than quietly fall through to the address
// -- falling through would fly whoever happens to share the address
// with the caller, which is the worst possible way to be wrong.
if (xuid) {
    if (slots[slot].xuid != xuid) continue;
    resolved = slot; matches = 1;
    break;
}
if (!senderIpv4 || slots[slot].peer.ipv4 != senderIpv4) continue;
++matches;
if (!resolved) resolved = slot;
```

### 2.2 十二层

```text
1. **恰好一条规则生效，绝不同时用两条**
2. ⇒ **一个指定了而【匹配不到任何东西】的 `xuid` 必须【失败】**
3. ⇒ **而不是悄悄退到地址**
4. ⇒ **因为退到地址会【飞起任何恰好与调用方共享那个地址的人】**
5. ⇒ **那是最糟的出错方式**
6. ⇒ **所以 `xuid` 分支【`break`】**（找到即停）
7. ⇒ **而地址分支【累加 `matches`】**
8. ⇒ **且只记第一个**（`if (!resolved) resolved = slot;`）
9. ⇒ **所以地址匹配可能【多个**】
10. ⇒ **而结果报 `ambiguous = matches > 1`**
```

### 2.3 ⭐⭐ **"飞起任何恰好与调用方共享那个地址的人"**

**✅ 这是本文件里**对"权限回退的危险"最清晰的陈述**。**

**⇒ 三层**：

```text
规则 A：`xuid`（精确身份）
规则 B：`senderIpv4`（网络地址）
⇒ **若 A 失败退到 B ⇒ 可能命中【别人】**
⇒ **⇒ 而"飞起"（noclip）是一个高权操作**
```

**✅ 与 §370 的"两个错位的位"**不同**（这是**权限回退**而不是**读错值**）。**

**⚠ 而"最糟的出错方式"⇒ **一个明确的安全判断**。**

**✅ 与 §353 的"缺选的变体不被静默转成内脏"**同族（**第二十次"不要猜/不要回退"）。**

**⇒ **一个反复出现的纪律**：**

```text
精确规则失败 ⇒ **失败**，不要退到一个更宽松的规则
```

**✅ **第六次确认。**

### 2.4 而**`ambiguous = matches > 1`**

**⇒ 三层**：

```text
1. **地址匹配可能命中【多个】客户端**
2. ⇒ **而仍取第一个**
3. ⇒ **但把 `ambiguous` 报给调用方**
```

**✅ ⭐ **"做但说出来"** —— 一个**折中**。**

**⚠ 而 `xuid` 分支 `matches = 1`【硬设】** ⇒ **所以 `ambiguous` 恒假。**

**✅ 一个**精确的区分**。

### 2.5 而 `debugGrantFactoryBattery` 的**同族逻辑**

```php
if(senderIpv4!=0x7F000001u || matchGameType_!="zm" || matchMapName_!="zm_factory_sh")return false;
if(targetClient) { ... }
for(i) {
    if(slots[i].state!=ClientState::Active)continue;
    if(target || slots[i].peer.ipv4!=senderIpv4)return false;   // ← 【两个匹配 ⇒ 失败】
    target=i;
}
```

**⇒ 六层**：

```text
1. **必须是 `127.0.0.1`**（`0x7F000001`）
2. ⇒ **必须是 `zm` + `zm_factory_sh`**
3. ⇒ **若指定了目标 ⇒ 必须 Active 且地址匹配**
4. ⇒ **否则扫全部 slots**
5. ⇒ **而【两个匹配 ⇒ 立即 `return false`】**
6. ⇒ **⇒ 更严格的"恰好一个"**
```

**✅ ⭐ **一个更严的版本**（**多个匹配直接失败**而不是"取第一个并标记 ambiguous"）。**

**⇒ 三层**：

```text
`setPlayerNoclipForSender`     ⇒ **多个 ⇒ 取第一个 + `ambiguous` 标志**
`debugGrantFactoryBattery`     ⇒ **多个 ⇒ 直接失败**
```

**⚠ 一处**不一致**。**

**✅ 而 `debug` 更严是**合理的**（一个调试工具应该拒绝歧义）。**

### 2.6 而 `0x7F000001u`

**✅ 一个**字面量 IPv4**（`127.0.0.1`）。**

**⇒ 三层**：

```text
1. **`0x7F000001` = `127.0.0.1`**
2. ⇒ **所以只接受【本机】的调试请求**
3. ⇒ **一个网络层的安全检查**
```

**✅ 与 §393 的"`peerKey = (ipv4 << 16) | port`"**配合。

## 三、**三个更多不持锁的 setter**（本组第二重要）

### 3.1 三处

```cpp
void ServerCore::setWeaponDefinitionResolver(WeaponDefinitionResolver resolver) {
    world_.setWeaponDefinitionResolver(std::move(resolver));    // ← 无锁
}
void ServerCore::setUnarmedSpawnWeapon(const std::uint16_t weaponAssetIndex) {
    world_.setUnarmedSpawnWeapon(weaponAssetIndex);             // ← 无锁
}
void ServerCore::setSpawnAnimationRunner(SpawnAnimationRunner runner) {  // §395 已记
    world_.setSpawnAnimationRunner(std::move(runner));          // ← 无锁
}
```

**⇒ 三处不持锁。**

**⚠ 而 §395 已记 `setSpawnAnimationRunner`。**

**⇒ 所以**总共三处**。**

**✅ 与 §395 的"唯一不持锁"**矛盾** —— 那是我当时的判断，而**这里又发现两处**。**

**⇒ 一个**更正**：**

```text
§395 说 "唯一不持锁"  ⇒ **错**
§396 实测  ⇒ **三处**（`setSpawnAnimationRunner` / `setWeaponDefinitionResolver` / `setUnarmedSpawnWeapon`）
```

**✅ 一处**真实的更正**。**

**⚠ 而三处**都是"设置一个纯函数/常量"**。**

**⇒ 三层**：

```text
`WeaponDefinitionResolver` / `unarmedSpawnWeapon` / `SpawnAnimationRunner`
⇒ **都是【配置项】而不是【运行时状态】**
⇒ **所以可能在初始化时设置（单线程）**
```

**✅ **一个合理的解释**（虽然注释没说）。**

## 四、**`loadGameplayScript` 的两阶段失败处理**（本组第三重要）

### 4.1 那段

```php
// A failed generation must not retain map-mode activation performed by
// a partially executed source. Other gameplay mutations remain owned
// by their individual builtin contracts.
if (!world_.setMapGameObjects({}))
    return false;
if (scriptRuntime_.reload(sourceName, source))
    return true;
static_cast<void>(world_.setMapGameObjects({}));
return false;
```

### 4.2 九层

```text
1. **一个失败的代际绝不能保留【一个部分执行的源所做的地图模式激活】**
2. ⇒ **其它玩法变异仍由它们各自的 builtin 契约拥有**
3. ⇒ **所以在 reload【之前】先 `setMapGameObjects({})`** ⇒ **清空**
4. ⇒ **若清空失败 ⇒ 直接返回 false**
5. ⇒ **然后 `reload`**
6. ⇒ **成功 ⇒ `return true`**
7. ⇒ **失败 ⇒ 【再清一次】**（因为 reload 可能部分激活了）
8. ⇒ **然后 `return false`**
```

**✅ ⭐ **"两次清空"** —— 一个**精确的失败回滚**。**

**⇒ 三层**：

```text
前：清（保证起点干净）
后（失败时）：再清（撤销部分执行的效果）
⇒ **所以两侧都清**
```

**✅ 与 §349 的"staged-then-commit"**不同**（这是**"清-做-失败再清"**）。**

**⚠ 而"其它玩法变异仍由它们各自的 builtin 契约拥有"⇒ **所以 `setMapGameObjects` 是唯一被回滚的**。**

**✅ 一个**明确的责任边界**。**

### 4.3 而 `setMapGameObjects({})` 的**空 span**

**✅ 与 §367 的"`isAllowed("")` 返回 `true`"**配合。**

**⇒ 三层**：

```text
空 `allowedGameObjectNames`
⇒ `isAllowed` 对【任何】名字返回 `true`
⇒ **⇒ 所以清空时【全部】被禁用**
```

**✅ ⭐ **一个"空即全部"的语义**。**

**⚠ 而 §367 的 `setMapGameObjects` 的 `active` 来自 `mapModeEligible && isAllowed(...)`。**

**⇒ 所以**空 ⇒ `isAllowed` 恒真 ⇒ 但 §367 的 `active = eligible && isAllowed` 会**为真**！**

**⚠ 与"清空"**矛盾**！**

**⇒ 让我核对 §367 的代码：**

```cpp
const auto active = entity.mapModeEligible && isAllowed(entity.scriptGameObjectName);
```

**⚠ 而 `isAllowed("")` 返回 `true`。**

**⇒ 所以**空输入 ⇒ `active = eligible` ⇒ **不为 false**！**

**⚠ 一处**语义矛盾**。**

**⇒ 可能 `setMapGameObjects({})` 调用方期望"清空"而实际是"全部激活 eligible 的"。**

**⚠ 一个**需要核对的差异**。**

## 五、**`worldPlayerSample` 的十个字段**（本组第四重要）

### 5.1 那段

```cpp
weaponSample = SvWorldWeaponSample{
    .currentWeaponAssetIndex = playerState->currentWeaponAssetIndex,
    .weaponTime = playerState->weaponTime[0],
    .weaponDelay = playerState->weaponDelay[0],
    .weaponState = playerState->weaponState[0],
    .weaponAnim = playerState->weaponAnim[0],
    .clipAmmo = clip->count[0],
    .weaponType = weapon->weaponType,
    .fireType = weapon->fireType,
    .definitionFireDelay = weapon->fireDelayMilliseconds,
    .definitionFireTime = weapon->fireTimeMilliseconds,
};
```

### 5.2 八层

```text
1. **六个来自 `playerState`**（槽 0）
2. ⇒ **而四个来自武器定义**
3. ⇒ **所以是"运行时 + 静态定义"的混合样本**
4. ⇒ **而 `weaponType` / `fireType` / `fireDelay` / `fireTime` 是【定义】的**
5. ⇒ **所以一个诊断能在【同一个快照】里对比运行时与定义**
```

**✅ 与 §374 的"`player-kinematics` 的二十二组"**同族（**第二次"完整诊断样本"）。**

**⚠ 而"`clipAmmo = clip->count[0]`"⇒ 所以**只取第一条**。**

**✅ 与 §366 的"`count[1]` 是第二只手"**配合。

### 5.3 而**"`lastReceivedUserCmd` 来自客户端槽"**

```cpp
const auto lastReceivedUserCmd = clientNum < clientSlots.size()
    ? clientSlots[clientNum].lastReceivedUserCmd : std::nullopt;
```

**⇒ 三层**：

```text
1. **从【客户端系统】读**
2. ⇒ **而 `playerState` 从【世界】读**
3. ⇒ **所以两个子系统在一个样本里**
```

**✅ 与 §392 的"`cmdAge`"**配合（**第二次确认那个字段**）。

## 六、**九个 `take*` 方法**（本组第五重要）

```text
takeFrameTimingStatus      ⇒ 六个 `take()` + 一个命令数
takeTimeoutDrops           ⇒ 转发
takeGameplayScriptLogs     ⇒ 转发
```

**⇒ 三个 `take`（而 `frameTiming` 有六个子 take）。**

### 6.1 而 `takeFrameTimingStatus` 的**七项**

```cpp
SvServerFrameTimingStatus status{
    .total = frameTotalTiming_.take(),
    .prepare = framePrepareTiming_.take(),
    .beginWorld = frameBeginWorldTiming_.take(),
    .clientThink = frameClientThinkTiming_.take(),
    .mode = frameModeTiming_.take(),
    .endAndPublish = frameEndAndPublishTiming_.take(),
    .clientThinkCommands = frameClientThinkCommands_,
};
frameClientThinkCommands_ = 0;
```

**⇒ 三层**：

```text
1. **六个 `take()`**（累计 + 重置）
2. ⇒ **加一个命令数**
3. ⇒ **然后显式清 `frameClientThinkCommands_`**
```

**✅ ⭐ **六个阶段的完整帧分解**（`total` / `prepare` / `beginWorld` / `clientThink` / `mode` / `endAndPublish`）。**

**⚠ 与 §374 的"`CLIENTTHINK PHASE` 的四段"**不同**（那是 **`clientThink` 内部**的四段）。**

**⇒ **两层分解**：**

```text
ServerCore 的六段帧
  └ clientThink 的四段（§374）
```

**✅ ⭐ **一个嵌套的性能分解**。**

**⚠ 而 `frameClientThinkCommands_` 在 `setEnabled` 里也被清（§392）。**

**⇒ 所以**两个清点**。**

## 七、`setScriptAnimationResolver` / `setScriptEffectResolver` 的**双写**

```cpp
void setScriptAnimationResolver(ScriptAnimationResolver resolver) {
    const std::lock_guard lock(mutex_);
    scriptBuiltins_.setAnimationResolver(resolver);   // ← 传【拷贝】
    scriptAnimationResolver_ = std::move(resolver);    // ← 然后【移动】
}
```

### 7.1 六层

```text
1. **先传 `resolver`（拷贝）给 `scriptBuiltins_`**
2. ⇒ **然后 `std::move` 到成员**
3. ⇒ **所以顺序是【必须的】**（移动后就不能再用）
4. ⇒ **一个"拷贝后移动"的模式**
```

**✅ 与 §394 的"二十一个 `gameState.*` 本地拷贝"**同族（**第三次"移动前拷贝"）。**

**⚠ 而"`scriptBuiltins_` 与 `scriptAnimationResolver_` 两个副本"⇒ **一个双写**。**

**⇒ 三层**：

```text
`scriptBuiltins_`         ⇒ **给 builtin 用的**
`scriptAnimationResolver_` ⇒ **给 ServerCore 自己用的**
⇒ **所以两个都需要**
```

**✅ 一个**必要的双写**。

## 八、关键结论

1. **⭐⭐ "恰好一条规则生效，绝不同时用两条"`** —— 一个指定了而**匹配不到任何东西的 `xuid` 必须失败而不是退到地址**，因为 **"退到地址会飞起任何恰好与调用方共享那个地址的人，那是最糟的出错方式"`**。
2. **⭐ `xuid` 分支 `break` 而地址分支累加 `matches` 并只记第一个**，而**结果报 `ambiguous = matches > 1`** —— **"做但说出来"**。
3. **⭐ `debugGrantFactoryBattery` 的同族逻辑更严**：**两个匹配 ⇒ 立即 `return false`**（而不是取第一个并标记）。
4. **⚠ 一处不一致**：`setPlayerNoclipForSender` 取第一个 + `ambiguous` 标志 / `debugGrantFactoryBattery` 直接失败。
5. **`0x7F000001u` = `127.0.0.1`** —— 只接受本机的调试请求。
6. **⚠ 更正 §395 的"唯一不持锁的 setter"** —— 实际是**三处**（`setSpawnAnimationRunner` / `setWeaponDefinitionResolver` / `setUnarmedSpawnWeapon`），而三者都是**纯配置项**（可能在初始化时单线程设置）。
7. **⭐ `loadGameplayScript` 的"两次清空"**（前：保证起点干净；失败：撤销部分执行的效果）—— **"一个失败的代际绝不能保留一个部分执行的源所做 的地图模式激活"`**。
8. **⚠ 而 `setMapGameObjects({})` 的语义可疑**：§367 的 `active = mapModeEligible && isAllowed(...)` 而 `isAllowed("")` 返回 **true** ⇒ **空输入会让所有 `eligible` 的实体【激活】**，与"清空"的意图**矛盾**。
9. **⭐ `worldPlayerSample` 的十个字段**——**六个来自 `playerState` + 四个来自武器定义** ⇒ **一个"运行时 vs 定义"的混合样本**。
10. **`lastReceivedUserCmd` 从客户端系统读而 `playerState` 从世界读** —— 两个子系统在一个样本里（第二次确认 `cmdAge`）。
11. **⭐⭐ `takeFrameTimingStatus` 的六阶段帧分解**（`total` / `prepare` / `beginWorld` / `clientThink` / `mode` / `endAndPublish`），而与 §374 的"`clientThink` 内部四段"形成**两层嵌套分解**。
12. **`setScriptAnimationResolver` 的"先拷贝后移动"** —— 第三次"移动前拷贝"，而**两个副本（`scriptBuiltins_` 与 `scriptAnimationResolver_`）是必要的双写**。

## 九、未闭合点

- `setMapGameObjects({})` 的实际语义（空 = 全部激活 还是 全部禁用）。
- `WeaponDefinitionResolver` 等三个纯配置项的设置时机。
- `ClientIngressStatus` / `TimeoutDrop` 的完整字段。
- `framePrepareTiming_` 等的采样点。
- `dangerouslyDisableSandbox` 与 `xuid` 校验的关系。
- `sv_main_mp.cpp` 2760 行之后未读取。
