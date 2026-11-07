# 274 · `EV_MELEE_HIT` 零售一局 36 次而我们一次没发、`SvResolvedWeapon` 的尺寸敏感、`CODOL_CLIENT_EXECUTION_STATE_PATCH` 的五字符否定

## 一、范围

本报告学习 `Appmain.cpp` 816–1040 行。

## 二、`resolveServerMeleeDamage`：**按资产侧存**（本组第二重要）

```php
// SIDE STORAGE BY ASSET, because SvResolvedWeapon is held inside the
// address-sensitive WorldClientState node. Growing that node broke
// corpse animation in section 184h. WeaponDefs are immutable after
// registration, so one native read per newly seen asset is enough.
static std::mutex cacheMutex;
static std::unordered_map<uint16, uint16> cache;
const std::lock_guard guard(cacheMutex);
if (auto found = cache.find(weaponAssetIndex); found != cache.end()) return found->second;

ClientWeaponSelection selection{};
if (!Bindings.readWeaponSelection(weaponAssetIndex, selection) ||
    !selection.meleeDamage ||
    selection.meleeDamage > UINT16_MAX) return nullopt;
const auto damage = (uint16)selection.meleeDamage;
cache.emplace(weaponAssetIndex, damage);
return damage;
```

### 2.1 四层

```text
1. `SvResolvedWeapon` 住在【地址敏感的】`WorldClientState` 节点里
2. ⇒ 增大那个节点【破坏了尸体动画】（§184h）
3. ⇒ 所以用【按资产的侧存】
4. 而 WeaponDef 注册后不可变 ⇒ 每个新资产一次原生读就够
```

### 2.2 这是一个**非常重要的约束**

**⇒ "增大 `WorldClientState` 会破坏尸体动画"。**

**⇒ 因为某个偏移是硬编码的，而节点变大会移动后续字段。**

**⇒ 与记忆里"复制以地址为键的缓冲区会让指针失效"（§180 的 `0x00198A90`/`0x00DAF2AC`/`0x0041144C` 野跳）同族。**

### 2.3 而"§184h 的教训"

**§184h** —— 从编号看是 `EngineBindings.hpp` 的学习段（§181–190）。

**⇒ 所以这个约束在 `EngineBindings.hpp` 里首次记录，而 `Appmain.cpp` 引用它。**

### 2.4 三个拒绝

```text
readWeaponSelection 失败
meleeDamage == 0
meleeDamage > 0xFFFF
```

**⇒ 与 §240 的 `weaponId` 三重判据同族。**

**⇒ 而 `!selection.meleeDamage` 意味着"0 = 没有近战伤害"。**

**⇒ 与 §240 里"`meleeDamage <= 0 ||` 无武器类门 ⇒ 拒绝每个 `+2072` 未填充的定义"是**相反**的处理**：

```text
§240  非近战武器 meleeDamage == 0 ⇒ 【合法】（只是没有近战伤害）
§274  近战攻击路径 meleeDamage == 0 ⇒ 【拒绝】（这把武器不能近战）
```

**✓ 两个不同的上下文，两个不同的语义。**

### 2.5 ⚠ **缓存不存"失败"**

**⇒ 失败时 `return nullopt` 而**不写缓存**。**

**⇒ 所以一个失败的资产每次都会重试。**

**⇒ 与 §247 的 `attempted = true`（失败也缓存）**相反**。**

**⇒ 这可能是有意的（"注册后不可变"），但如果读取因瞬态原因失败，会反复重试。**

## 三、`SV_ExecuteMeleeAttack` 的**六项配置 + 六个回调**

```php
{
    .basis, .weaponAssetIndex, .meleeDamage, .firingEntityNum, .levelTime, .glassPieceCount,
}
```

**⇒ 六项。**

**而 `glassPieceCount = glassMetadata.initialPieces.size()`** —— 玻璃片数。

### 3.1 而"近战不穿透"的桩不同

```php
[](const SvBulletTraceInput &, const TraceResult &, std::uint32_t) -> optional<bool> {
    // Melee does not penetrate; the first thing the swing reaches
    // is the thing it hits.
    return false;
}
```

**⇒ 与 §272 的子弹桩**同样返回 `false`**，但**理由不同**：**

```text
§272  子弹   "三项未恢复"（TODO）
§274  近战   "近战不穿透"（设计）
```

**⇒ 同一个返回值、两种理由。**

## 四、**`payloadsBefore` 的"前后差"**

```php
// Where the staged payloads end BEFORE the swing, so the one this swing
// adds can be identified without the melee path having to report it.
const auto payloadsBefore = entity.pendingPlayerDamagePayloads.size();
const auto result = SV_ExecuteMeleeAttack(...);
```

### 4.1 三层

```text
1. 记录挥击【之前】的 payload 数量
2. 挥击后如果多了，最后那一个就是这次挥击加的
3. ⇒ 所以近战路径【不需要报告】它加了什么
```

**⇒ 这是一个"用前置快照代替输出参数"的设计** ✓

**⇒ 与 §267 的 `entryFraction`、§273 的 `reports++` 同族。**

### 4.2 而"保持单一输出与签名"

```php
// Read from there rather than threaded back out of SV_ExecuteMeleeAttack,
// so the melee transaction keeps its single output and its signature.
```

**⇒ 所以事务的签名不变。**

**✓ 一个干净的接口保持策略。**

## 五、**`EV_MELEE_HIT` 零售一局 36 次而我们一次没发**（本组最重要的一段）

```php
// AND THE KNIFE'S OWN IMPACT EVENT. A swing that connects has always
// staged damage and shown the victim NOTHING -- retail sends
// EV_MELEE_HIT 36 times a match and this server never sent it once.
// Everything it needs is already in the payload the swing just staged:
// the hit point, the attacker and the weapon.
```

### 5.1 三层

```text
1. 一次命中的挥击【一直】暂存伤害而【对受害者什么也不显示】
2. 零售一局发 EV_MELEE_HIT 【36 次】，而本服务器【一次都没发过】
3. 而所需的一切都已经在 payload 里：命中点、攻击者、武器
```

### 5.2 而 §276（报告 146）里学过 **`EV_MELEE_HIT/MISS` 在 1514 个事件里零出现**

**⇒ 那是在**事件表**里的零出现。**

**⇒ 而这里是**发出的线事件**里的零出现。**

**⇒ 两个不同层面的零。**

**⇒ 而"零售 36 次一局"给出了**期望值**。**

**⇒ 所以现在的修法是用 payload 构造一个 `SvBulletImpactEvent` 并 `melee = true`。**

### 5.3 四项构造

```cpp
const SvBulletImpactEvent meleeImpact{
    .position = *staged.point,
    .weaponAssetIndex = weapon.weaponAssetIndex,
    .sourceEntityNum = (uint16)entity.networkState.number,
    .melee = true,
};
if (SV_IsBulletImpactEventValid(meleeImpact))
    entity.pendingEntitySpawns.push_back(meleeImpact);
```

**⇒ 复用 `SvBulletImpactEvent` 加一个 `melee` 布尔** —— 而不是新结构。

**⇒ 所以 `melee` 字段会在序列化时改变事件类型（从子弹撞击到近战撞击）。**

### 5.4 而 `staged.point` 是 `optional`

```php
if (staged.point) { ... }
```

**⇒ 所以"命中但没有点"⇒ 不发事件。**

**⇒ 与 §244 的"两个方向代价不对称"同族。**

## 六、`melee` 日志的**六个量**

```php
"melee attacker=%u weapon=%u damage=%u result=%s "
"damageablePlayers=%zu damageableEntities=%zu"
```

### 6.1 五个 `%` 转换 + 一个字符串

**⇒ 六个量。**

### 6.2 而 `result` 的四态

```php
result == Applied ? "APPLIED"
: result == Glass   ? "GLASS"
: result == Missed  ? "missed"
: "FAILED"
```

**⇒ 四种** —— 而"APPLIED"与"missed"大小写不一致（一个全大写一个全小写）。

**⚠ 一处格式不一致。**

### 6.3 而那两句理由

```php
// SAY IT, ONCE PER SWING. A knife that does not kill is the reported
// bug, and the two ways it can fail -- the trace finding nobody, and
// the trace finding somebody who is not a damageable player -- are
// indistinguishable without this line. Melee is rare enough per match
// that one line per swing is not the section 104 flood.
```

### 6.4 两种失败

```text
trace 找不到任何人
trace 找到某人但【不是可伤害的玩家】
```

**⇒ 两个不同的缺陷，而"刀不杀人"对两者都一样。**

**⇒ 与 §273 的"胶囊不存在 vs 存在但未相交"同族** —— 第三次"两缺陷一症状"。

### 6.5 "近战每局足够罕见 ⇒ 每次挥击一行不是 §104 的洪水"

**⇒ 所以这里**不做**上限。**

**⇒ 与 §273 的"最多 96/48/128/12"形成对照** —— 频率决定是否采样。

## 七、**十七个 `Last...` 状态槽**

```php
uint32 LastRuntimeStatusLogMilliseconds{};
ServerStatus LastLoggedServerStatus{};
SvNetworkStatus LastLoggedNetworkStatus{};
optional<AlphaWeaponPortStatus> LastLoggedAlphaWeaponPortStatus{};
array<optional<SvClientThinkStatus>, 18> LastLoggedClientThinkStatus{};
array<string, 18> LastLoggedClientIngressState{};
array<uint32, 18> LastLoggedUnsupportedDiscardCounts{};
array<string, 18> LastLoggedClientRejectState{};
```

### 7.1 三个标量 + 四个 18 长数组

```text
标量 3 个     时间戳 + 服务端状态 + 网络状态 + alpha 状态（4 个）
18 长 4 个    think 状态 / ingress 状态 / 丢弃计数 / 拒绝状态
```

**⇒ 四个 18 长数组 ⇒ `MaximumGameClients = 18`。**

**⇒ 与记忆里"`0xAF350 + 18*0x450`"一致** ✓

### 7.2 而另一处用 18 字面量

```cpp
std::array<std::optional<SvClientThinkStatus>, 18> LastLoggedClientThinkStatus{};
```

**⇒ 用的是**字面量 18**而不是 `MaximumGameClients`。**

**⚠ 一处不一致** —— 如果客户端数变了，这些数组不会跟着变。

**⇒ 而 §266 的 `SnapshotBuildTiming` 用的是 `MaximumGameClients`。**

## 八、**两个探针状态**

```php
struct DObjLocationalProbeState { uint32 attemptCount{}; bool completed{}; };
DObjLocationalProbeState DObjLocationalProbe;

// OLMOD(capsule-entity-collision): section 74. The counterpart of the
// locational probe, for the CAPSULE path. Section 73h said this question
// needed a second player and a person at the screen; it does not, because
// the one player already in the map IS a linked entity and a capsule
// sweep through him with no pass filter has exactly one candidate.
struct CapsuleEntityProbeState { uint32 attemptCount{}; bool completed{}; };
CapsuleEntityProbeState CapsuleEntityProbe;
```

### 8.1 两个探针，同一个形状

```text
DObjLocationalProbe    DObj 骨骼路径
CapsuleEntityProbe     胶囊路径
```

### 8.2 而 §73h 的"需要第二个玩家"再次被撤回

**⇒ 与 §272 的"§73h 被撤回"**第二次出现**。**

**⇒ 理由**："地图里已有的那一个玩家**就是**一个已链接实体，而无 pass 过滤的胶囊扫描穿过他只有一个候选。"

**⇒ 这是一个"排除法"：如果只有一个候选而仍然打不到，那就是路径本身的问题。**

**✓ 一个正确的实验设计。**

## 九、`alphaWeaponPortStatusName` 的**九项**

```cpp
case Disabled:                  return "disabled";
case WaitingForCommonAssets:    return "waiting-common-assets";
case WaitingForWeaponRegistry:  return "waiting-weapon-registry";
case WrongThread:               return "wrong-thread";
case SourceAssetMissing:        return "source-asset-missing";
case InvalidDefinition:         return "invalid-definition";
case LinkFailed:                return "link-failed";
case RegistrationFailed:        return "registration-failed";
case Ready:                     return "ready";
```

### 9.1 **九个状态**

**⇒ 与 §246 里"九个（比七态多）"一致** ✓

```text
Disabled
WaitingForCommonAssets
WaitingForWeaponRegistry
WrongThread
SourceAssetMissing
InvalidDefinition
LinkFailed
RegistrationFailed
Ready
```

**⇒ 完全吻合。**

### 9.2 而 `switch` 没有 `default`，最后 `return "unknown"`

**⇒ 所以新增状态会得到 "unknown" 而不是编译错误。**

**⚠ 与 `-Wswitch` 的期望不符** —— 但这个项目可能不开那个警告。

## 十、`installClientInputPatches` 的**五字符否定**（本组第三重要）

```php
void installClientInputPatches(const OlMod::ProcessRole role)
{
    if (role == OlMod::ProcessRole::Dedicated) return;
    if (!ClientProcessPatchAttempted)
    {
        ClientProcessPatchAttempted = true;
        std::array<char, 8> value{};
        const auto size = GetEnvironmentVariableA("CODOL_CLIENT_EXECUTION_STATE_PATCH",
            value.data(), value.size());
        const auto enabled = !size ||
            (value[0] != '0' && value[0] != 'n' && value[0] != 'N' &&
                value[0] != 'f' && value[0] != 'F');
        if (!enabled) logGameServer("client execution state patch disabled");
        else { ClientProcessPatch = installClientProcessPatches(); ... }
    }
}
```

### 10.1 三件事

```text
① 专用服直接返回（补丁只在客户端）
② `ClientProcessPatchAttempted` 一次性
③ 默认【开】：`!size` ⇒ 未设置 ⇒ 开
```

### 10.2 **五个字符的否定**

```text
'0'  零
'n' / 'N'   no
'f' / 'F'   false
```

**⇒ 所以 `"0"`、`"n"`、`"N"`、`"f"`、`"F"` 都关闭，**其它任何非空值都开**。**

**⇒ 包括 `"off"`?? 不，`'o'` 不在列表 ⇒ `"off"` 会**开**。**

**⚠ 这是一个真实的陷阱** —— 用户设 `=off` 会意外启用。**

**⇒ 而 `"false"` 会关（因为 `'f'`），`"no"` 会关（`'n'`），`"0"` 会关。**

**⇒ 所以"off"是唯一常用的英文否定词**不在**列表里。**

### 10.3 而这个模式在本文件里**第五次**出现

```text
§271  OLMOD_SNAPSHOT_HEX        strtol（非正数 ⇒ 默认 16）
§271  OLMOD_SNAPSHOT_HEX_OBITUARY  value[0] != '0'
§274  CODOL_CLIENT_EXECUTION_STATE_PATCH  五字符否定
§272  OLMOD_BULLET_SELF_DAMAGE_PROBE       size == 1 && '1'
§272  OLMOD_LOG_BULLET_PENETRATION          size == 1 && '1'
```

**⇒ 五种不同的布尔环境变量解析规则。**

**⇒ 这是一处明确的**一致性缺陷** —— 用户无法预测。**

### 10.4 而 `ClientProcessPatchAttempted = true` 在**读取之前**

**⇒ 所以失败后不重试。**

**⇒ 与 §247 的 `attempted` 一致，与 §274 的 `resolveServerMeleeDamage` **相反**。**

## 十一、关键结论

1. **`SvResolvedWeapon` 住在地址敏感的 `WorldClientState` 里，增大它会破坏尸体动画（§184h）** ⇒ 侧存。
2. **近战缓存不存失败**（与 §247 的 `attempted` 相反）。
3. **`meleeDamage == 0` 在近战路径是拒绝而在武器定义是合法** —— 两个上下文两个语义。
4. **`payloadsBefore` 的"前后差"代替输出参数** —— 保持事务签名。
5. **`EV_MELEE_HIT` 零售一局 36 次而我们一次没发** —— 复用 `SvBulletImpactEvent` + `melee` 布尔。
6. **近战日志三态**（`APPLIED`/`glass`/`missed`/`FAILED`）大小写不一致。
7. **"trace 找不到人 vs 找到非可伤害玩家"** —— 第三次"两缺陷一症状"。
8. **近战罕见 ⇒ 不采样**；而子弹/穿透都采样。
9. **四个 18 长数组用字面量 18** 而 `SnapshotBuildTiming` 用 `MaximumGameClients`。
10. **两个探针同一形状**，而 §73h 的"需要第二个玩家"第二次被撤回。
11. **`alphaWeaponPortStatusName` 九个状态** 与 §246 完全吻合。
12. **五个字符的否定（`0`/`n`/`N`/`f`/`F`）而 `"off"` 会意外启用**。
13. **五种不同的布尔环境变量解析规则** —— 一致性缺陷。

## 十二、未闭合点

- `WorldClientState` 里哪个偏移对尺寸敏感（§184h 的具体字段）。
- `"off"` 会启用补丁是否是已知问题。
- 18 字面量与 `MaximumGameClients` 的关系。
- `Appmain.cpp` 1040 行之后未读取。
