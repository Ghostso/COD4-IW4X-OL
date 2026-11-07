# 277 · **"我瞄的正是那堵墙"**、`40` 比 `64` 是更弱的假设、十五个 loadout 失败名

## 一、范围

本报告学习 `Appmain.cpp` 1479–1700 行。

## 二、`runDObjLocationalProbe` 的**八个量**

```php
"DObj locational probe result attempt=" + N + " segment=" + N +
" fraction=" + fraction + " hitType=" + hitType + " hitId=" + hitId +
" modelIndex=" + modelIndex + " partName=" + partName + " partGroup=" + partGroup
```

### 2.1 六个 trace 字段

```text
fraction / hitType / hitId / modelIndex / partName / partGroup
```

### 2.2 而完成的判据是**三项**

```php
if (result->fraction < 1.0f && result->hitId == ProbeClientNum && result->partName != 0)
{
    DObjLocationalProbe.completed = true;
    logGameServer("DObj locational probe completed");
    return;
}
```

```text
fraction < 1.0          有命中
hitId == ProbeClientNum 【打中的是目标客户端】
partName != 0           【且是骨骼/部件而不是世界】
```

**⇒ 三项一起 ⇒ 才判定"DObj 定位路径工作"。**

**⇒ 而 `partName != 0` 是关键 —— 世界命中 `partName` 是 0。**

### 2.3 而失败时 `return`（不继续段）

```php
if (!result) { logGameServer("... unavailable ..."); return; }
```

**⇒ 所以一段失败就整体放弃。**

**⇒ 与 `MaximumAttempts = 3` 配合 ⇒ 下次重试全部三段。**

### 2.4 而**打不中就继续下一段**

**⇒ 三段都打完都不满足 ⇒ 只增加 `attemptCount` ⇒ 下次再试。**

**⇒ 三次后放弃。**

## 三、**`runCapsuleEntityProbe` 的"我瞄的正是那堵墙"**（本组最重要的一段）

### 3.1 那段自我批评

```php
// A player-sized capsule swept THROUGH the player, with no pass
// filter, so he is a legal candidate.
//
// THE FIRST VERSION OF THIS SWEPT 64 UNITS ALONG X AND STARTED INSIDE
// A WALL: fraction=0.047302 hitType=1 hitId=2046 startSolid=1, where
// 2046 is the world. The locational probe's own segment 0 had already
// measured that wall at 0.116 of 128 units -- about 15 units out --
// and I aimed at it anyway. A world hit NEARER than the player is not
// a failure of the entity half; it means the entity half never got a
// chance, exactly as segment 0 of the locational probe does not.
```

### 3.2 五个数

```text
fraction = 0.047302
hitType  = 1
hitId    = 2046      （= 世界）
startSolid = 1
```

**⇒ 而"0.116 of 128 units ≈ 15 units out"** —— 那堵墙在 15 单位外。

### 3.3 而"我还是瞄了它"

**"the locational probe's own segment 0 had already measured that wall at 0.116 of 128 units -- about 15 units out -- and I aimed at it anyway."**

**⇒ 一个**极强的自我批评** —— 而它揭示了一个可复用的教训：**

```text
探针 A 已经测量出一堵墙的位置
⇒ 而探针 B 却朝那个方向发射
⇒ ⇒ 探针 B 必然打到那堵墙而不是目标
```

**⇒ 所以"用同一组测量既确定墙也确定目标"是错的** —— 必须**分开**。

### 3.4 而算术闭合

```text
段 0（locational probe）：origin - 64 到 origin + 64（128 单位）
fraction = 0.116 ⇒ 命中在 origin - 64 + 0.116 × 128 = origin - 49.2
⇒ 墙在 x = origin.x - 49.2，而起点是 origin.x - 64
⇒ 距离起点 14.8 单位 ✓ "about 15 units out"
```

**⇒ 完全吻合。**

### 3.5 而胶囊探针的第一版：`origin.x - 64 到 origin.x + 64`

**⇒ 起点恰好在 `origin.x - 64` ⇒ **与段 0 的起点相同** ⇒ 墙在 14.8 单位外。**

**⇒ 而 `fraction = 0.047302 × 128 = 6.05` 单位。**

**⚠ 而段 0 说墙在 14.8 单位外而这里说 6.05 单位。**

**⇒ 两个不同的值** —— 因为**胶囊有半径**（约 15），所以胶囊的**表面**在 6 单位处碰到墙。

**⇒ `6.05 + 15 ≈ 21` 而墙在 14.8？不完全闭合。**

**⇒ 或者胶囊的半径与碰撞盒不同。**

**⇒ 无论如何，**起点在墙附近**是清楚的。**

### 3.6 而"一个比玩家更近的世界命中不是实体半边失败"

**"A world hit NEARER than the player is not a failure of the entity half; it means the entity half never got a chance."**

**⇒ 这是一个**关键的判读规则** —— 区分"实体路径坏了"与"实体路径没机会"。**

**⇒ 与 §273 的"胶囊不存在 vs 存在但未相交"同族** —— 第四次"两缺陷一症状"。

### 3.7 而解法：**五段 + 更短的线**

```php
// So it sweeps several lines and stops at the first ENTITY hit. The
// short ones matter most: a player capsule has a radius near 15, so
// 40 units of separation clears the two capsules at the start and
// still crosses the player, and 40 units of open space is a much
// weaker assumption about a map than 64.
```

### 3.8 三层

```text
1. 扫多条线，停在第一个【实体】命中
2. 【短的那些最重要】
3. 玩家胶囊半径约 15 ⇒ 40 单位的间隔让两个胶囊在起点【分开】且仍能穿过玩家
4. 而"40 单位的空旷"对地图是一个比"64"【弱得多】的假设
```

### 3.9 **"更弱的假设"这个说法**

**⇒ 这是一个**实验设计原则**：**

```text
假设"起点外 64 单位空旷"   ⇒ 强假设，容易失败
假设"起点外 40 单位空旷"   ⇒ 弱假设，容易成立
```

**⇒ 而"40 > 2 × 15 = 30"保证两个胶囊不重叠。**

**✓ 数学上刚好够。**

### 3.10 五段的端点

```text
段 0   y ± 40                                （水平，主）
段 1   x ± 40                                （水平，副）
段 2   y ± 64                                （长）
段 3   y ± 40 而 z + 16                      （抬高 16）
段 4   (x-40, y-40) → (x+40, y+40)           （【对角】）
```

**⇒ 五种不同的几何，覆盖不同的空旷方向。**

**⇒ 而段 4 是对角** —— 扩展到 2D 覆盖。

### 3.11 而 `traceWorldCapsule` 用**玩家自己的 bounds**

```php
const auto entity = Server.worldPlayerEntity(ProbeClientNum);
if (!entity) return;
...
const auto result = Server.traceWorldCapsule(
    segments[segmentIndex].first, segments[segmentIndex].second,
    entity->collisionBounds,                       // ← 【他自己的身体尺寸】
    CodolGameServer::PlayerCollisionContentMask,
    CodolGameServer::SvTraceEntityFilter{});        // ← 【空过滤器 = 不过滤自己】
```

**⇒ 用一个**默认构造**的 `SvTraceEntityFilter{}`** ⇒ 没有 pass 过滤。**

**⇒ 所以玩家自己是合法候选** ✓

**⇒ 而"用他自己的 bounds"保证"如果路径穿过他，一定命中"。**

### 3.12 而完成判据是**两项**（比 DObj 探针少一项）

```php
if (result->hitType != 0 && result->hitId == ProbeClientNum)
{
    CapsuleEntityProbe.completed = true;
    ...
}
```

```text
hitType != 0            有命中（世界是 1？所以非 0 包括世界！）
hitId == ProbeClientNum 打中的是目标
```

**⚠ `hitType != 0` 而 `hitId == ProbeClientNum`。**

**⇒ 如果 `hitId` 是客户端号而世界是 `2046`，那 `hitId == 0` 只可能是玩家 0。**

**⇒ 所以 `hitType != 0` 是**冗余的**（只要 `hitId == 0` 就是玩家）。**

**⇒ 但两者都检查更安全。**

**⇒ 而这里**没有** `partName != 0` 的检查** —— 因为胶囊路径不返回骨骼。**

**✓ 两个探针的判据差异是正确的。**

## 四、**两个探针的 `MaximumAttempts = 3`**

```text
DObjLocationalProbe   3
CapsuleEntityProbe    3
```

**⇒ 两个都是 3。**

### 4.1 而 DObj 探针还要求 `worldNativeEntityMirrorSynchronized()`

**⇒ 胶囊探针**没有**这一项。**

**⚠ 一处不一致** —— 但胶囊探针用 `worldPlayerEntity` + `worldPlayerSample`，可能隐含了同步。

## 五、`loadoutResolveFailureName` 的**十六个**

```cpp
case None:                      return "none";
case StagedSlot:                return "staged_slot";
case NativeResolverUnavailable: return "native_resolver_unavailable";
case ItemName:                  return "item_name";
case BaseWeaponLookup:          return "base_weapon_lookup";
case BaseWeaponResolver:        return "base_weapon_resolver";
case DefaultAttachments:        return "default_attachments";
case EquippedAttachmentName:    return "equipped_attachment_name";
case EquippedAttachmentSlot:    return "equipped_attachment_slot";
case AttachmentMerge:           return "attachment_merge";
case AttachmentLookup:          return "attachment_lookup";
case AttachmentCapacity:        return "attachment_capacity";
case ModularWeaponResolver:     return "modular_weapon_resolver";
case WeaponDefinition:          return "weapon_definition";
case ModularWeaponDependency:   return "modular_weapon_dependency";
case AttachmentModelResolution: return "attachment_model_resolution";
```

**⇒ 十六个（含 `None`）⇒ 十五个失败态。**

### 5.1 与 §252/§253 的对照

**§252 的 `resolveWeaponItem` 里的六个跳过**（附件）在**这里**对应：

```text
ItemName                     无内部名
EquippedAttachmentSlot       has no model slot      ← §252 的 "has no model slot"
EquippedAttachmentName       （另一个名字相关的）
```

**⇒ 而 `att is not in the attachment registry` 与 `is not supported by this weapon` 与 `has no model for this weapon` 的跳过**在**这里**没有对应的枚举值**。**

**⇒ 所以那三个跳过**不设置** `loadoutResolveFailure_`**（它们只是 `skip()`）。**

**⇒ 与 §252 的"六级全部 continue"一致** ✓

### 5.2 而 §253 的四个致命点对应

```text
AttachmentLookup          attachmentIndex 无效        （§253 第一个 return false）
AttachmentModelResolution 模型解析失败               （§253 第二个）
AttachmentCapacity        超出数组容量               （§253 第三个）
ModularWeaponDependency   注册表异常                 （§253 第四个）
```

**⇒ 四个一一对应** ✓

### 5.3 而 §245 的 `stage` 号与这里的名字

**⇒ 不重叠** —— `stage` 是 `ensureWeaponRegistryInitialized` 的，而这是 loadout 的。

## 六、`executableDirectory` 的**32768**

```php
std::array<wchar_t, 32768> path{};
const auto size = GetModuleFileNameW(nullptr, path.data(), 32768);
if (!size || size >= path.size()) return std::filesystem::current_path();
return std::filesystem::path(path.data()).parent_path();
```

### 6.1 32768 是**宽字符的 MAX_PATH 长版本**

**⇒ 与 §243 的 `diagnosticPath` 用 `MAX_PATH`（260）**不同**。**

**⇒ 所以两处用了不同的上限。**

### 6.2 而失败时回退到 `current_path()`

**⇒ 与 §243 的 `return {}`（空路径）**不同**。**

**⇒ 所以这个函数**总是**返回一个可用的路径。**

## 七、`gameplayScriptRoot`

```php
return executableDirectory() / L"Ayria" / L"Assets" / L"OlMod" / L"GameScripts";
```

**⇒ `Ayria/Assets/OlMod/GameScripts`** —— 一个**深四层**的路径。

**⇒ 与 §243/§247 的 `Ayria/Logs` 同级但在 `Assets` 下。**

## 八、`parseFiniteFloat` 的**四项**

```php
while (value.front() == ' ') value.remove_prefix(1);
while (value.back() == ' ') value.remove_suffix(1);
float result{};
const auto parsed = std::from_chars(value.data(), value.data() + value.size(), result);
return parsed.ec == std::errc{} && parsed.ptr == value.data() + value.size() &&
    std::isfinite(result) ? optional{result} : nullopt;
```

### 8.1 四项

```text
去前导空格
去尾随空格
from_chars 成功 + 全消费
isfinite
```

### 8.2 **只去空格，不去制表/换行**

**⚠ 如果输入有 `\t` 或 `\r`，`from_chars` 会失败。**

**⇒ 这是一个很窄的清理。**

### 8.3 而这是本文件里**第三次**正确的 `from_chars` + 全消费

```text
§254  resolveSessionPerks 的 number lambda
§276  glassDamageThresholds 的 read lambda
§277  parseFiniteFloat
```

**⇒ 三个正确的对照五个错误的（`strtol`/`stoul`/五字符否定/`size==1&&'1'`/`!value[0]||parsed>0`）。**

## 九、`drainGameplayScriptLogs` 的**四种 kind**

```php
case Print:        return "print";
case CompileError: return "compile_error";
case RuntimeError: return "runtime_error";
case HostError:    return "host_error";
```

### 9.1 四种

```text
print            正常输出
compile_error    编译错误
runtime_error    运行时错误
host_error       宿主错误
```

### 9.2 而消息的**六个字段**

```php
"gameplay script generation=" + N + " kind=" + kind + " source=" + sourceName +
" message=" + message + (traceback.empty() ? "" : " traceback=" + traceback)
```

```text
generation    脚本代际
kind          四种之一
source        源文件名
message       消息
traceback     可选
```

**⇒ 五个（`traceback` 可选）。**

### 9.3 而 `generation` 与 §260 的"配置串代际"同族

**⇒ 所以脚本也有代际概念（重载后递增）。**

## 十、关键结论

1. **DObj 探针的完成判据三项**（`fraction < 1`、`hitId == 目标`、`partName != 0`）。
2. **胶囊探针的完成判据两项**（`hitType != 0`、`hitId == 目标`）—— 因为胶囊不返回骨骼。
3. **"我瞄的正是那堵墙"** —— 探针 A 已测出墙的位置而探针 B 仍朝那个方向发射。
4. **算术闭合**：段 0 的 `0.116 × 128 = 14.8` 单位 ✓ "about 15 units out"。
5. **"比玩家更近的世界命中不是实体半边失败，而是它没机会"** —— 一个关键的判读规则。
6. **`40` 比 `64` 是"对地图弱得多的假设"** —— 而 `40 > 2 × 15` 恰好够分开两个胶囊。
7. **五段覆盖五种方向**（y/x/长 y/抬高/对角）。
8. **`SvTraceEntityFilter{}` 默认构造 = 无 pass 过滤** ⇒ 玩家自己是合法候选。
9. **用玩家自己的 `collisionBounds`** ⇒ 路径穿过他必命中。
10. **`loadoutResolveFailureName` 十六个名字**，其中 §252 的三个跳过**不**设失败值。
11. **`executableDirectory` 用 32768** 而 §243 的 `diagnosticPath` 用 `MAX_PATH`。
12. **`parseFiniteFloat` 只去空格不去制表/换行** —— 很窄。
13. **三个正确的 `from_chars` 对照五个错误的解析器**。
14. **脚本日志四种 kind + 代际**。

## 十一、未闭合点

- 胶囊探针为何不要求 `worldNativeEntityMirrorSynchronized()`。
- `parseFiniteFloat` 的应用场景（哪个文件格式）。
- `Appmain.cpp` 1700 行之后未读取。
