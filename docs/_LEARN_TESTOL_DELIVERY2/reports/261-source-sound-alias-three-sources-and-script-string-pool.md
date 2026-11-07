# 261 · 骨骼名用脚本串池而不是附件表、声音别名的"服务器自己的注册优先"、`63` 次加载全失败

## 一、范围

本报告学习 `EngineBindings.cpp` 16650–17030 行。

## 二、`resolveWeaponConfigStringIndex` 的**注册表回退**

```cpp
if (weaponLookup_ && SV_ParseModularWeaponConfigString(weaponName))
{
    const std::string nativeName(weaponName);
    const auto index = weaponLookup_(nativeName.c_str());
    if (index && index < WeaponConfigStringCount)
        return static_cast<std::uint16_t>(index);
}
return std::nullopt;
```

### 2.1 两个门

```text
weaponLookup_ 已绑定
SV_ParseModularWeaponConfigString(weaponName) 成功   ← 【只有模块化串才走】
```

### 2.2 四项

```text
1. index 非零
2. index < 1700
```

**⇒ 只对模块化串回退** —— 因为"动态模块化定义住在原生 WeaponDef 注册表里"。

**注释说**：

```cpp
// Dynamic modular definitions live in the native WeaponDef registry.
// CL_GetConfigString does not consistently expose that tail after the
// retained server has replaced its own gamestate, so use the registry's
// lookup for the exact raw definition as the authoritative fallback.
```

### 2.3 三层

```text
1. 动态模块化定义在原生 WeaponDef 注册表
2. `CL_GetConfigString` 在服务器替换了自己的 gamestate 之后【不一致地】暴露那个尾部
3. ⇒ 用注册表的 lookup 作权威回退
```

**"不一致地"** —— 说明这是一个**时有时无**的问题。

## 三、`modelBoneIndex`：**骨骼名用脚本串池**（本组最重要的一段）

```cpp
// CODREF(actor_head_attachment): exact CODOL XModel boneNames at +44,
// numBones at +4; DObj assembly 0x52FBE0/0x781110 keeps the base skeleton
// first. BO1/Ghosts attachment comparisons are in the head-attachment review.
// OLMOD(death_fx_resolution): resident map-load lookup, no asset loading or
// fallback bone zero. Attachment-local indices are not actor bone indices.
```

### 3.1 四个地址

```text
XModel boneNames   +44
numBones           +4
DObj 组装           0x52FBE0 / 0x781110
```

**⇒ 与 §250 里 `auditRig` 的 `+4 = boneCount`、`+44 = boneNames` 完全一致** ✓

### 3.2 **那次"附件表返回武器名"的事故**（本组核心）

```cpp
// CODDIFF(actor_head_attachment): XModel boneNames are script-string
// IDs, not weapon attachment IDs. CODOL 0x485300 retains these IDs in
// the pool at VA 0x789C524; 0x4EAAD0 resolves text as pool+20*id+4.
// AK live server/client reads confirmed j_neck at base bone20 and
// j_spinelower at bone5. The attachment table returned weapon names
// for the same numeric IDs, disabling every death-FX model change.
```

### 3.3 五层

```text
1. XModel 的 boneNames 是【脚本串 id】而不是武器附件 id
2. `0x485300` 把它们保留在 `0x789C524` 的池里
3. `0x4EAAD0` 用 `pool + 20*id + 4` 解析文本
4. 实测：`j_neck` 在 bone20、`j_spinelower` 在 bone5
5. 【用附件表解析同样的数字 id 会返回武器名】⇒ 每一个死亡特效模型变更都失效
```

### 3.4 **两个命名空间的碰撞**

```text
InternedStringTable   （§251 的附件名）
ScriptStringPool      （0x789C524 的脚本串）
```

**⇒ 同一个数字 id 在两个池里指向**完全不同的字符串**。**

**⇒ 而错误地用一个池解析另一个池的 id ⇒ 得到合法但无关的名字 ⇒ **检查通过但语义全错**。**

**这与记忆里"指针 100% 吻合也骗人"（§144）是同一类** —— 数字吻合但命名空间错。

### 3.5 而 `pool + 20*id + 4` 与 §260 的 `animationNotifyName` **完全相同**

```cpp
// §260
constexpr std::size_t NotifyStringPoolRva = 0x0749C524;
const auto address = uint64{pool} + 20u * nameId + 4u;
// §261
constexpr std::size_t ScriptStringPoolRva = 0x749C524;
const char *text = scriptStrings + 20u * names[i] + 4u;
```

**⇒ `0x749C524` 与 `0x0749C524` 是同一个 RVA。**

**⇒ 而 §260 叫它 "NotifyStringPool"、§261 叫它 "ScriptStringPool"。**

**⇒ 所以 boneNames 与 notify 名共用**同一个池** —— 都是"脚本串"。**

**这是一处关键的交叉确认** —— 而两处的命名不同。

### 3.6 而 `+4` 是"跳过条目前 4 字节"

**⇒ 20 字节条目、名字在 `+4`。**

### 3.7 实现的三项

```cpp
if (!module_ || modelName.empty() || modelName.size() >= 128 || boneName.empty() ||
    modelName.find('\0') != npos || boneName.find('\0') != npos) return nullopt;
const auto *model = findXAsset(AssetTypeXModel, ...);
if (!readableSpan(model, 360)) return nullopt;
const auto count = model[4];
memcpy(&names, model + 44, sizeof(names));
if (!count || !readableSpan(names, count * sizeof(*names))) return nullopt;
```

**⇒ 四个检查**：

```text
model 可读 360 字节
count 非零
names 可读 count*2 字节
（名字无 NUL、无过长）
```

### 3.8 **`i < count && i < 255` 的双界**

```cpp
for (std::uint16_t i = 0; i < count && i < 255; ++i)
```

**⇒ `count` 是 `uint8` ⇒ 最多 255。**

**⇒ 而 `i < 255` 是**冗余的**（因为 `i < count <= 255`）。**

**⇒ 除非 `count` 是 `uint16`。但 `model[4]` 是单字节 ⇒ `uint8`。**

**⇒ 所以 `i < 255` 是一个防御性的冗余检查。**

### 3.9 而返回 `uint8`

**`static_cast<std::uint8_t>(i)`** —— 所以骨骼索引最多 255。

### 3.10 `names[i]` 为 0 时跳过

```cpp
if (names[i]) { ... }
```

**⇒ 空的骨骼名 id 被跳过。**

## 四、`attachmentBoneIndex`：**附件骨骼 = 身体骨骼数 + 附件局部索引**

```cpp
const auto local = modelBoneIndex(attachment, bone);
if (!local || modelBoneIndex(body, bone)) return nullopt;
const auto *model = findXAsset(AssetTypeXModel, body);
if (!readableSpan(model, 360)) return nullopt;
const auto count = model[4];
if (!count || (unsigned)count + *local >= 255) return nullopt;
return static_cast<std::uint8_t>(count + *local);
```

### 4.1 三项

```text
1. 附件模型里有这个骨骼
2. 【身体模型里没有】这个骨骼   ← 【关键】
3. count + local < 255
```

### 4.2 第 2 项的意义

**"如果身体模型也有这个名字，就拒绝"** —— 因为那样"附件骨骼"与"身体骨骼"无法区分。

**⇒ 所以这个函数只处理**身体里不存在**的骨骼名。**

### 4.3 那个"复合索引"

```text
DObj 里的骨骼索引 = 身体骨骼数 + 附件局部索引
```

**⇒ 因为 DObj 是"身体骨架 + 追加的附件骨架"。**

**与注释"0x781110 appends XModel bone arrays"一致** ✓

## 五、`resolveEffectEventParameter`：**效果名精确匹配**

```cpp
if (!findXAsset(AssetTypeFx, effectName.c_str(), false).data) return nullopt;
for (eventParameter = 1; eventParameter < EffectConfigStringCount; ++eventParameter)
{
    const auto configStringIndex = SV_EffectEventParameterToConfigString(eventParameter);
    if (!configStringIndex) return nullopt;         // ← 【注意：不是 continue】
    const auto candidate = readCString(nativeConfigString(*configStringIndex), 128);
    if (candidate && *candidate == effectName) return eventParameter;
}
return nullopt;
```

### 5.1 **`!configStringIndex ⇒ return nullopt`**

**⇒ 而 §259 的 `effectConfigStringBand` 用的是 `continue`。**

**⇒ 两个函数对"转换失败"的处理**不同**：**

```text
resolveEffectEventParameter   转换失败 ⇒ 【整个失败】
effectConfigStringBand        转换失败 ⇒ 【跳过这一项】
```

**⚠ 这可能是一个 bug** —— 因为如果 `SV_EffectEventParameterToConfigString` 对某些 eventParameter 无值（合法的空槽），`resolveEffectEventParameter` 会在第一个空槽处**整个失败**。

**⇒ 而 `effectConfigStringBand` 会正确地跳过。**

**⇒ 所以 `resolveEffectEventParameter` 可能因此**从未成功过**（如果空槽在前面）。**

**这是一处高度可疑的不一致** —— 值得记录。

### 5.2 而 `AssetTypeFx` 的号

**§259 的注释说 "fx 30"** ⇒ `AssetTypeFx = 30` ✓

## 六、`resolveSoundAliasEventParameter` 的单一包装

```cpp
const std::array names{ std::string(aliasName) };
auto result = resolveSoundAliasEventParameters(names);
return result.empty() ? std::nullopt : result.front();
```

### 6.1 ⚠ **`result.front()` 是 `optional<uint16>`**

**而 `result` 是 `vector<optional<uint16>>`（大小 = 1）。**

**⇒ `result.empty()` 只可能是 `aliasNames.empty()` 的情况** —— 而这里 `names` 大小恒为 1 ⇒ **`result` 恒非空。**

**⇒ 所以返回的是 `result.front()`，可能是 `nullopt`。**

**⇒ 而函数返回类型是 `optional<uint16>` ⇒ 正确** ✓

### 6.2 但 `result.empty() ? nullopt : result.front()` 中的 `result.front()` 是 `optional<uint16>`

**⇒ 三元的两支类型不同（`nullopt_t` vs `optional<uint16>`）⇒ 会隐式转换。**

**⇒ 正确但绕。**

## 七、声音别名的**三个来源**（本组第二重要）

### 7.1 第一个：**服务器自己的注册表**

```cpp
// 28800: THE SERVER'S OWN REGISTRATION WINS. `announceSoundAliases`
// writes `name -> cs 3624+idx`; the CCS scan below walks a SPARSE
// client chain that (measured 16:23) is not populated yet, so every
// announcer name reported UNRESOLVED although the alias was live.
if (const auto registered = LookupRegisteredSoundAlias(name))
{
    result[index] = registered;
    continue;
}
```

### 7.2 三层

```text
1. `announceSoundAliases` 写 `name -> cs 3624+idx`
2. CCS 扫描走一条【稀疏的客户端链】，在 16:23 实测时【尚未填充】
3. ⇒ 每个播音员名都报 UNRESOLVED，尽管别名是活的
```

**⇒ 所以服务器的注册表是**第一手**来源。**

### 7.3 注册表的实现

```cpp
std::mutex SoundAliasRegistryMutex;
std::unordered_map<std::string, uint16> SoundAliasRegistry;

void NoteRegisteredSoundAlias(std::string_view aliasName, uint16 aliasIndex)
{
    if (aliasName.empty() || aliasName.size() >= 128 || !aliasIndex) return;
    const lock_guard lock(SoundAliasRegistryMutex);
    SoundAliasRegistry[std::string(aliasName)] = aliasIndex;
}

optional<uint16> LookupRegisteredSoundAlias(std::string_view aliasName)
{
    if (aliasName.empty()) return nullopt;
    const lock_guard lock(SoundAliasRegistryMutex);
    const auto exact = SoundAliasRegistry.find(std::string(aliasName));
    if (exact != SoundAliasRegistry.end()) return exact->second;
    // One retry without the CCS `%` prefix, matching the scan below.
    std::string_view trimmed = aliasName;
    if (!trimmed.empty() && trimmed.front() == '%') trimmed.remove_prefix(1);
    const auto trimmedHit = SoundAliasRegistry.find(std::string(trimmed));
    return trimmedHit == SoundAliasRegistry.end() ? nullopt : optional<uint16>{trimmedHit->second};
}
```

### 7.4 两个函数**都是全局自由函数**

**⇒ 不是 `EngineBindings` 的成员** —— 所以**所有实例共享同一个注册表**。

**⚠ 这意味着专用服与客户端（如果是同一进程内的两个 `EngineBindings`）会共享。**

**⇒ 在正常情况下两个进程是分开的，所以没有问题。**

### 7.5 查找的**两次尝试**

```text
1. 精确名
2. 去掉 '%' 前缀后
```

**⇒ 与后面的扫描的规范化一致。**

### 7.6 第二个：**配置串带扫描**

```cpp
for (aliasIndex = 1; aliasIndex < SoundAliasConfigStringCount && !unresolved.empty(); ++aliasIndex)
{
    const auto candidate = readCString(nativeConfigString(SoundAliasConfigStringBase + aliasIndex), 128);
    if (!candidate) continue;
    const auto match = findAlias(*candidate);
    if (match != unresolved.end())
    {
        for (const auto index : match->second) result[index] = aliasIndex;
        unresolved.erase(match);
    }
}
```

### 7.7 **循环条件里的 `!unresolved.empty()`**

**⇒ 一旦全部解决就提前退出** ✓

### 7.8 第三个：**CCS 常量串链**

```cpp
for (relativeIndex = 0; !unresolved.empty() &&
     relativeIndex < SoundAliasEventParameterLimit - SoundAliasConstantStringBase;
     ++relativeIndex)
{
    const char *candidate{};
    if (!invokeCCSGetConstantString(ccsGetConstantString_, ConstantStringTypeSoundAlias, relativeIndex, candidate))
    {
        continue;  // 28800: sparse CCS chain -- a miss is not the end
    }
    const auto name = readCString(candidate, 128);
    if (name) { ... result[index] = SoundAliasConstantStringBase + relativeIndex; ... }
}
```

### 7.9 **`continue` 而不是 `break`**

```cpp
// 28800: sparse CCS chain -- a miss is not the end
```

**⇒ 与 §261 后面 `collectServerSoundAliasAuditions` 的 `break` **相反**！**

**⚠ 这是一个明确的内部分歧**：

```text
resolveSoundAliasEventParameters   缺失 ⇒ 【continue】（稀疏链）
collectServerSoundAliasAuditions   缺失 ⇒ 【break】（假定连续）
```

**⇒ 两个函数对同一个 CCS 链的**稀疏性假设相反**。**

**⇒ 而注释明确说"稀疏链"⇒ 所以 `collectServerSoundAliasAuditions` 的 `break` 是**错的**（它会在第一个空槽处停止，而那条链是稀疏的）。**

**⇒ 这可能就是为什么 `auditions` 返回空或很少。**

**这是一个重要发现。**

### 7.10 而 `resolveScriptAnimation` 也用 `break`

```cpp
for (std::uint32_t key = 1; key <= 0xFFF; ++key)
{
    if (!invokeCCSGetConstantString(ccsGetConstantString_, 18, key, candidate)) break;
    ...
}
```

**⇒ 第三种做法（`break`）。**

**⚠ 所以同一个文件里三种做法**：

```text
resolveSoundAliasEventParameters    continue（正确，因为链是稀疏的）
resolveScriptAnimation              break
collectServerSoundAliasAuditions    break
```

**⇒ 后两个可能都因为在第一个空槽就退出而失效。**

**这与 §261 的"63 次加载每次 `sound=unavailable`"可能相关** —— 但那个 `sound=unavailable` 是 `findXAsset` 失败，不是 CCS。

## 八、`findAlias` 的**三级规范化**（本组第三重要）

```php
const auto normalise = [](std::string_view value) {
    std::string out;
    for (const char ch : value)
        out.push_back((char)std::tolower((unsigned char)ch));
    return out;
};

const auto findAlias = [&unresolved, &normalise](const std::string &candidate) {
    const auto exact = unresolved.find(candidate);
    if (exact != unresolved.end()) return exact;            // ① 精确
    std::string_view trimmed = candidate;
    if (!trimmed.empty() && trimmed.front() == '%') trimmed.remove_prefix(1);
    const auto wanted = normalise(trimmed);                  // ② 去 '%' + 小写
    for (auto it = unresolved.begin(); it != unresolved.end(); ++it)
    {
        std::string_view raw = it->first;
        if (!raw.empty() && raw.front() == '%') raw.remove_prefix(1);
        if (normalise(raw) == wanted) return it;             // ③ 逐个比较
    }
    return unresolved.end();
};
```

### 8.1 三项

```text
① 精确（最快，多数情况）
② 去 '%' 前缀 + 小写
③ 与剩下的每一个做规范化比较（O(n²) 最坏）
```

### 8.2 那段理由

```cpp
// 28800: EXACT COMPARISON WAS TOO STRICT FOR THREE SOURCES AT ONCE.
// The name can arrive with a `%` prefix (resolveScriptAnimation already
// strips one for animations), in a different case (`AB_1mc_...` and
// `ab_1mc_...` both ship), or with map-registered spelling. Compare on a
// normalised copy and return the real key so the caller can erase it.
```

### 8.3 三个来源的三种差异

```text
'%' 前缀         （resolveScriptAnimation 已经处理）
大小写不同        （`AB_1mc_...` 与 `ab_1mc_...` 都出货）
地图注册的拼写
```

### 8.4 **"返回真实的键以便调用者 erase"**

```cpp
for (const auto index : match->second) result[index] = ...;
unresolved.erase(match);
```

**⇒ `findAlias` 返回一个迭代器（真实的键），所以 `erase` 是安全的。**

**这是一个"返回键而不是值"的设计** ✓

### 8.5 ⚠ **`unresolved` 是 `unordered_map<string_view, vector<size_t>>`**

```cpp
std::unordered_map<std::string_view, std::vector<std::size_t>> unresolved;
...
unresolved[name].push_back(index);
```

**⇒ 键是 `string_view` 指向 `aliasNames` 里的 `std::string`** —— **所以 `aliasNames` 必须在我们用完 `unresolved` 之前存活。**

**`aliasNames` 是 `std::span<const std::string>`** ⇒ 生命周期由调用者保证 ✓

**⚠ 但 `findAlias` 在 `normalise(raw)` 里比较，而 `raw` 是 `string_view`** —— 安全。

**⇒ 然而 `unresolved.erase(match)` 在遍历后** —— 也安全（不在遍历中）。

### 8.6 ⚠ **第三个循环的 `O(n²)`**

```cpp
for (it = unresolved.begin(); it != unresolved.end(); ++it) { normalise(raw); }
```

**⇒ 对每个候选都重新规范化每一个未解决的名字。**

**⇒ 如果 CCS 链有几千项而 `unresolved` 有几十个 ⇒ 几十万次规范化 + 分配。**

**这是一个性能问题** —— 而注释没说。

## 九、**那 63 次加载的实测**

```cpp
// CODREF(sound_alias_event): do NOT gate on the sound ASSET being
// loaded. The server's only job is to put an alias INDEX on the
// wire; the client owns playback and looks the asset up itself. A
// dedicated server loads no sound assets, so
// findXAsset(AssetTypeSound, ...) fails for every name and
// this filter emptied `unresolved` before either scan below could
// run - which is why this resolver has NEVER answered on this build.
// MEASURED: 63 level loads, every one logging `sound=unavailable`,
// including the damage-feedback hit alert, while the material
// lookups beside it resolve fine (material=125 killMaterial=144).
// The dm demo confirms the wire needs only a small index - its 98
// sound events are eType 26 (SoundAliasAsMaster) carrying 14/27.
```

### 9.1 五层

```text
1. 不要用"声音资产已加载"作为门
2. 服务器唯一的工作是把一个别名【索引】放上线路
3. 客户端拥有播放并自己查资产
4. ⇒ 专用服不加载任何声音资产 ⇒ findXAsset(AssetTypeSound) 对所有名字失败
5. ⇒ 那个过滤在两次扫描之前就清空了 unresolved
```

### 9.2 **"这个解析器在这个 build 上从未回答过"**

**⇒ 一个"过滤器把输入清空"的完整失败模式。**

**与 §244 里"八个出口一个返回类型"、§255 里"EMPTY 被当成 UNREADABLE"同族。**

### 9.3 **63 次实测**

```text
63 次关卡加载，每一次都记 `sound=unavailable`
包括伤害反馈的命中提示
而旁边的材质查找正常（material=125 killMaterial=144）
```

**⇒ 一个对照实验** —— 同样的环境下材质能解、声音不能 ⇒ **问题定位到声音这条路。**

**这是本文件里又一次"用相邻的成功作对照"。**

### 9.4 而 demo 的**线格式证据**

```text
dm demo 的 98 个声音事件是 eType 26（SoundAliasAsMaster），携带 14/27
```

**⇒ "携带 14/27" 是两个小索引** —— 所以线上只需要索引。

**⇒ 这与"服务器只放索引"一致** ✓

## 十、`collectServerSoundAliasAuditions` 的**四个前缀**

```cpp
const auto prefix = name->substr(0, 3);
if (prefix == "ab_" || prefix == "uk_" || prefix == "za_" || prefix == "rb_") continue;
```

### 10.1 四个前缀

```text
ab_    §155 学过 `sc ↔ ab_`
uk_    §155 学过 `tf ↔ uk_`
za_
rb_
```

**⇒ 四个**语言前缀** —— 播音员语音。**

### 10.2 而 1432/1507 带这些前缀

```text
// 1432 of its 1507 entries carry ab_/uk_/za_/rb_ language prefixes
```

**⇒ 所以剩下 75 项是"服务器可以真正引用的别名"。**

### 10.3 而 `SoundAliasConstantStringBase` 与 `SoundAliasEventParameterLimit`

```cpp
const auto parameter = (uint32)SoundAliasConstantStringBase + relativeIndex;
if (!parameter || parameter >= SoundAliasEventParameterLimit) continue;
auditions.emplace_back((uint16)parameter, *name);
```

**⇒ `SoundAliasConstantStringBase + relativeIndex < SoundAliasEventParameterLimit`。**

**与 §259 的 `effectConfigStringBand` 用 `SV_EffectEventParameterToConfigString` 不同** —— 这里是**直接相加**。

**⇒ 两个不同的转换**：

```text
effect   SV_EffectEventParameterToConfigString(eventParameter)
sound    SoundAliasConstantStringBase + relativeIndex
```

### 10.4 那个 TODO

```cpp
// TODO(CODOL): audition support. ... Remove with the audition mode.
```

**⇒ 一个明确标注"随试听模式一起删除"的死代码。**

### 10.5 而 `16384` 的上界

```cpp
for (relativeIndex = 0; relativeIndex < 16384; ++relativeIndex)
```

**⇒ 而实际只到 1507。**

**⇒ 所以循环会在 1507 处 `break`（因为有 `break`）。**

**⚠ 而如果链是稀疏的，`break` 会让它停在第一个空槽 —— 可能远早于 1507。**

## 十一、`logServerSoundAliasTables` 的**五个量**

```cpp
snprintf(header, ...,
    "sound alias tables: configStringGet=%u ccsGetConstantString=%u "
    "ccsInitialized=%u base=%u count=%u",
    configStringGet_ ? 1 : 0, ccsGetConstantString_ ? 1 : 0, CCS_Initialized() ? 1 : 0,
    SoundAliasConfigStringBase, SoundAliasConfigStringCount);
```

**⇒ 五个量**：

```text
三个绑定的存在性
基址
计数
```

**⇒ 所以一次日志就能看出"是绑定缺失还是表空"。**

### 11.1 而 BO1 的对照

```cpp
// BO1 G_PlaySoundAlias 0x00694460 shows
// the server's job is to supply an alias INDEX - it stuffs it into
// entityState.loopSoundId on a TempEntity of event 4, which is exactly
// the eType 26 the dm demo carries 98 of.
```

**⇒ BO1 的 `G_PlaySoundAlias` 把索引塞进 `entityState.loopSoundId`，而 event 4 的 TempEntity 正是 demo 里的 eType 26。**

**⇒ 一个跨 build 的**行为**对照（不是数值）** ✓

## 十二、关键结论

1. **模块化串才走注册表回退** —— 因为 `CL_GetConfigString` 不一致地暴露尾部。
2. **XModel `+4` = boneCount、`+44` = boneNames** 与 §250 一致。
3. **骨骼名用脚本串池（`0x789C524`）而不是附件表** —— 用附件表会返回武器名，让每个死亡特效失效。
4. **同一个数字 id 在两个池里指向不同字符串** —— 数字吻合但命名空间错。
5. **`0x749C524` 与 `0x0749C524` 是同一个 RVA，而 §260 叫 "NotifyStringPool"、§261 叫 "ScriptStringPool"** —— 同一个池两个名字。
6. **`attachmentBoneIndex` 要求"身体里没有这个骨骼名"** —— 否则无法区分。
7. **复合索引 = 身体骨骼数 + 附件局部索引**。
8. **`resolveEffectEventParameter` 对 `!configStringIndex` 返回失败，而 `effectConfigStringBand` 是 `continue`** —— 高度可疑的不一致。
9. **声音别名三个来源：服务器注册表 → 配置串带 → CCS 常量串链**。
10. **服务器自己的注册优先**，因为 CCS 链是稀疏的且实测未填充。
11. **`resolveSoundAliasEventParameters` 用 `continue`（正确），而 `resolveScriptAnimation`/`collectServerSoundAliasAuditions` 用 `break`（对稀疏链是错的）**。
12. **`findAlias` 三级规范化**（精确 → 去 `%` + 小写 → 逐个）
13. **`unresolved` 用 `string_view` 作键** —— 生命周期依赖调用者。
14. **`O(n²)` 的规范化比较**（每个候选都重新规范化每个未解决项）。
15. **"这个解析器在本 build 上从未回答过"** —— 因为一个过滤器（`findXAsset(AssetTypeSound)` 在专用服恒失败）在两次扫描前清空了输入。
16. **63 次加载每次 `sound=unavailable`，而相邻的材质查找正常**（125/144）—— 一个干净的对照。
17. **1432/1507 的别名带四个语言前缀** —— 播音员语音，剩下 75 项可用。

## 十三、未闭合点

- `resolveScriptAnimation` 与 `collectServerSoundAliasAuditions` 的 `break` 是否真的让它们失效（需实测）。
- `resolveEffectEventParameter` 的 `return nullopt` 是否让它从未成功。
- `unresolved` 的 `O(n²)` 在实际规模下是否显著。
- `SoundAliasConstantStringBase` / `SoundAliasEventParameterLimit` / `SoundAliasConfigStringBase` / `SoundAliasConfigStringCount` 的具体值。
- `EngineBindings.cpp` 17030 行之后未读取。
