# 262 · `0x077D8188` 头表、16 个 CCS 类型的穷举、`0x90/0x94` 的碰撞图、`contactBrushModel`

## 一、范围

本报告学习 `EngineBindings.cpp` 17030–17250 行。

## 二、`0x077D8188` 的**逐指令对照**（本组最重要的一段）

```cpp
// OLMOD(section-84): the two VAs here were 3.3.3.3's and this code calls
// out.exe. CCSGetConstantStringRva 0x261C50 puts the function at VA
// 0x00661C50, whose body is instruction-for-instruction 3.3.3.3's
// 0x005851F0 with ONE operand changed: `mov eax, [eax*8 + 0x77D8188]`
// at 0x00661C53 against `[eax*8 + 0x2DF7CE8]` at 0x005851F3. So the
// shape and the stride carry over and THE HEAD TABLE IS AT 0x077D8188
// on this build.
```

### 2.1 三对数字

```text
本 build 函数 VA    0x00661C50   ← RVA 0x261C50 + 0x400000
3.3.3.3 函数 VA     0x005851F0
```

```text
本 build 指令        0x00661C53   mov eax, [eax*8 + 0x77D8188]
3.3.3.3 指令         0x005851F3   mov eax, [eax*8 + 0x2DF7CE8]
```

### 2.2 **"逐指令相同，只有一个操作数变了"**

**⇒ 所以形状与步长（8）沿用，而**头表地址**不同。**

### 2.3 那个 `stride 8`

```text
CCS_GetConstantString 索引一个 per-TYPE 的链表头表，步长 8
```

**⇒ 16 个类型 × 8 字节 = 128 字节的头表。**

**而 `+0x77D8188` 与 `+0x2DF7CE8` 相差 `0x49E04A0`。**

### 2.4 那句"本树没有任何东西解引用它"

```cpp
// Nothing in this tree dereferences it -- the walk goes
// through the bound function -- but the number was wrong to quote.
```

**⇒ 所以这个地址只对"引用时写对"有意义** —— 而实际调用走 `ccsGetConstantString_`。

**"但那个数字引用错了"** —— 一处自我更正。

### 2.5 而**类型 5 的 1507 项全是语音**

```cpp
// Type 5
// holds 1507 entries and every feedback-word match in it is
// voice-over - ab_1mc_hardpoint, uk_ac130_fco_directhit,
// za_m1_killstreak1 - so the announcer table is what this project has
// been searching for a hit marker. Enumerate every type instead.
```

### 2.6 三层的推理

```text
1. 类型 5 有 1507 项
2. 而每一个 feedback-word 匹配都是语音（三个例子）
3. ⇒ 播音员表正是这个项目一直在找"命中提示"的地方
4. ⇒ 【改为枚举每一个类型】
```

**"ab_1mc_hardpoint"、"uk_ac130_fco_directhit"、"za_m1_killstreak1"** —— 三个具体名字。

### 2.7 三个前缀与 §261 的四个

```text
§261  collectServerSoundAliasAuditions   ab_/uk_/za_/rb_
§262  这里的例子                        ab_/uk_/za_
```

**⇒ 三个例子覆盖了四个前缀中的三个。**

## 三、`Wanted` 的**十二个关键词**

```cpp
static constexpr std::string_view Wanted[]{
    "hit", "alert", "medal", "challenge", "reward", "level_up",
    "splash", "headshot", "killstreak", "point", "score", "ui_",
};
```

### 3.1 十二个

```text
hit           命中
alert         警报
medal         勋章
challenge     挑战
reward        奖励
level_up      升级
splash        溅射
headshot      爆头
killstreak    连杀
point         分数点
score         得分
ui_           UI
```

### 3.2 **`"hit"` 是最宽的一个**

**⇒ 会匹配 `hit`、`hardpoint`（含 `hit`? 不）、`directhit`（含 `hit`? 是）**

**⚠ `"uk_ac130_fco_directhit"` 含 `"hit"`** ⇒ 所以它会被匹配。

**⇒ 而 `"ab_1mc_hardpoint"` 含 `"point"`** ⇒ 也会被匹配。

**⇒ 所以关键词匹配是**子串**的（`name->find(want) != npos`）。**

### 3.3 而 `"ui_"` 是唯一带下划线的

**⇒ 说明 UI 别名有一个明确的命名约定。**

## 四、**16 个类型的穷举**

```cpp
for (std::uint32_t type = 0; type < 16; ++type)
{
    std::size_t total{}, matched{};
    std::string firstNames;
    for (std::uint32_t relativeIndex = 0; relativeIndex < 16384; ++relativeIndex)
    {
        const char *candidate{};
        if (!invokeCCSGetConstantString(ccsGetConstantString_, type, relativeIndex, candidate))
            break;                                    // ← 【break】
        const auto name = readCString(candidate, 128);
        if (!name || name->empty()) continue;
        ++total;
        if (total <= 3) firstNames += " " + *name;    // ← 【前 3 个名字】
        if (matched >= limit) continue;
        if (!any_of(Wanted, [&](want) { return name->find(want) != npos; })) continue;
        ++matched;
        write("ccs type=N index=M = name");
    }
    if (!total) continue;
    write("ccs type=N total=X matched=Y first: ...");
}
```

### 4.1 **三层**

```text
外层   16 个类型
中层   每个类型最多 16384 项
内层   每个名字（前 3 个记名字，有上限的匹配计数）
```

### 4.2 `type < 16` 的上界

**⇒ 头表是 16 个槽** —— 与 `stride 8` 的推断一致（16 × 8 = 128）。

### 4.3 **`break` 在 `invokeCCSGetConstantString` 失败时**

**⇒ 与 §261 的 `resolveSoundAliasEventParameters` 的 `continue` **相反**。**

**⚠ 这里又是 `break`。**

**⇒ 但这个函数是**诊断** —— 它要"枚举全部"，而 `break` 会截断。**

**⇒ 如果某条链是稀疏的，这个诊断会低估 `total`。**

**⇒ 而 §261 的注释明确说 "sparse CCS chain -- a miss is not the end"。**

**⇒ 同一文件里对同一 API 的三种处理（`continue` / `break` × 2）仍然存在。**

### 4.4 `limit` 的**双重用途**

```cpp
if (matched >= limit) continue;        // ← 【不是 break】
```

**⇒ 达到上限后仍然继续遍历（为了统计 `total`），只是不打印。**

**⇒ 这是一个有意的设计** —— 上限只限"打印的行数"，不限制"统计"。

**✓ 正确。**

### 4.5 `firstNames` 只记前 3 个

**⇒ 因为"这个类型里有什么"用 3 个样例就能看出来。**

### 4.6 而 `if (!total) continue` 跳过空类型

**⇒ 所以只有非空类型会打印。**

## 五、`resolveServerMaterialConfigStringIndex`：**64 字节上限**

```cpp
if (!configStringGet_ || !CCS_Initialized() || materialName.empty() ||
    materialName.size() >= 64 ||                          // ← 【64，不是 128】
    materialName.find('\0') != npos)
    return nullopt;
for (index = 1; index < ServerMaterialConfigStringCount; ++index)
{
    const auto candidate = readCString(nativeConfigString(ServerMaterialConfigStringBase + index), 64);
    if (candidate && *candidate == materialName) return index;
}
```

### 5.1 **`64` 与其它函数的 `128`**

```text
resolveModelConfigStringIndex        128
resolveAnimConfigStringIndex         128
resolveWeaponConfigStringIndex       128
resolveEffectEventParameter          128
resolveServerMaterialConfigStringIndex  64     ← 【不同】
```

**⇒ 材质名短于 128。**

**⇒ 这是一个**逐函数的**上限。**

### 5.2 精确比较

**`*candidate == materialName`** —— 大小写敏感。

**⇒ 与模型名的 `_stricmp` 不同。**

### 5.3 与 §261 的 `material=125 killMaterial=144` 对照

**§261**："而旁边的材质查找正常（material=125 killMaterial=144）"

**⇒ 那两个数字是**索引值**（125 与 144）。**

**⇒ 所以材质解析确实成功了。**

## 六、`firstDynamicServerMaterialIndex`：**类型 >= 23**

```cpp
// CODREF(actor_grounded_adapter): CODOL514880 reads class>=23 from
// 77D8250 through the parsed gamestate string table. Original Factory
// registers clock names at5170/5171; never assume those session indices.
if (!module_ || !CCS_Initialized()) return nullopt;
const auto *types = module_ + ConfigStringTypesRva + ServerMaterialConfigStringBase;
if (!readableSpan(types, ServerMaterialConfigStringCount)) return nullopt;
for (std::uint16_t i = 1; i < ServerMaterialConfigStringCount; ++i)
    if (types[i] >= 23) return i;
return nullopt;
```

### 6.1 **`types[i] >= 23`**

**⇒ 与 §236 的"两个哨兵 `{21, 23}`"里的 `23` 一致。**

**而 §236 的 `firstDynamicWeaponAssetIndex` 用 `type == 21 || type >= 23`。**

**⇒ 这里只用 `>= 23`（没有 `== 21`）。**

**⚠ 两处的判据不同** —— 是一处不一致。

### 6.2 **`ConfigStringTypesRva + ServerMaterialConfigStringBase`**

**⇒ 与 §236 的 `ConfigStringTypesRva + WeaponConfigStringBase + index` 同一手法。**

**⇒ 类型数组是按配置串索引全局索引的。**

### 6.3 `0x77D8250` 与 §262 开头的 `0x077D8188`

```text
0x077D8188   CCS 头表（16 × 8）
0x77D8250    【另一个全局】
```

**⚠ 注意 `0x77D8250` 与 `0x077D8188` 相差 `0xC8`。**

**⇒ 而 `ConfigStringTypesRva` 在 §236 里是 `0x73D8250`。**

**⇒ `0x77D8250` 与 `0x73D8250` 相差 `0x400000`** ⇒ **同一个地址的 VA 与 RVA 写法。**

**⇒ 所以 `ConfigStringTypesRva = 0x73D8250`，其 VA 是 `0x77D8250`。**

**⇒ 而 `0x077D8188` 是一个**不同**的全局。**

**⇒ 两个地址相差 `0x5C38`（`0x77D8250 - 0x77D8188 = 0xC8`… 等等）**

**算一下**：`0x77D8250 - 0x77D8188 = 0xC8` = 200。

**⇒ 所以 CCS 头表在类型数组之前 200 字节处。**

### 6.4 "original Factory 在 5170/5171 注册 clock 名；绝不假定那些会话索引"

**⇒ 与 §236 的"不要重新推导，它们是测量过并被佐证的"相反方向：**

```text
§236  保留测量值但暂时不用（因为目标不同）
§262  绝不假定会话索引（因为每次会话不同）
```

**⇒ 前者是"测量过但目标不符"，后者是"会话相关不可假定"。**

## 七、`resolveBrushModelCollision`：**`0x90/0x94` 的碰撞图**（本组第二重要）

```cpp
const auto *const collisionMap = module_ + CollisionMapRva;
constexpr std::size_t BrushModelCountOffset = 0x90;
constexpr std::size_t BrushModelsOffset = 0x94;
if (!readableSpan(collisionMap + 0x90, sizeof(uint32) + sizeof(NativeBrushModel*)))
    return nullopt;

std::uint32_t modelCount{};
const NativeBrushModel *models{};
memcpy(&modelCount, collisionMap + 0x90, 4);
memcpy(&models, collisionMap + 0x94, sizeof(models));
if (!modelCount || clipHandle >= modelCount || !models ||
    modelCount > SIZE_MAX / sizeof(NativeBrushModel) ||
    !readableSpan(models, modelCount * sizeof(NativeBrushModel)))
    return nullopt;

const auto &model = models[clipHandle];
const auto contents = model.leafBrushContents | model.leafTerrainContents;
const SvBrushModelCollision result{ .clipHandle = clipHandle, .bounds = model.bounds, .contents = contents };
return SV_EncodeBrushModelSolid(result) ? optional{result} : nullopt;
```

### 7.1 五个界

```text
① collisionMap + 0x90 可读 8 字节（count + pointer）
② modelCount 非零
③ clipHandle < modelCount
④ modelCount <= SIZE_MAX / sizeof(NativeBrushModel)   ← 【溢出防御】
⑤ models 可读 modelCount * sizeof(NativeBrushModel)
```

### 7.2 **第四项的溢出防御**

```cpp
modelCount > std::numeric_limits<std::size_t>::max() / sizeof(NativeBrushModel)
```

**⇒ 在 32 位进程里 `SIZE_MAX = 0xFFFFFFFF`，而 `sizeof(NativeBrushModel)` 可能是几十字节。**

**⇒ 所以 `modelCount` 上限是 `0xFFFFFFFF / 40 ≈ 107M`** —— 而 `modelCount` 是 `uint32`，最高 4G。

**⇒ 所以这项**确实**能拦住大宗值。**

**这是一个正确的乘法溢出防御** ✓

**与 §262 后面 `SV_LinkBrushModelCollisionEntity` 之前的检查同族。**

### 7.3 **`contents` 是两个字段的**按位或**

```cpp
const auto contents = model.leafBrushContents | model.leafTerrainContents;
```

**⇒ 所以"brush 内容"与"terrain 内容"被合并成一个掩码。**

**⇒ 这在 COD 的 `CM_*Contents` 语义里是标准的**（所有内容位合并）。

### 7.4 `SV_EncodeBrushModelSolid` 的**最终门**

```cpp
return SV_EncodeBrushModelSolid(result) ? optional{result} : nullopt;
```

**⇒ 与 §254 的 `SV_IsEquipmentValid`、§242 的 `SV_PlaceCharacterItemsByRecordEntry` 同一分层**（逻辑在头文件里）。

**⇒ 所以"这个 brush model 是否是固体"由 `SV_EncodeBrushModelSolid` 判断。**

## 八、`contactBrushModel`：**一个"接触"查询**

```cpp
const auto entity = SV_LinkBrushModelCollisionEntity(
    MaximumServerCollisionEntityNum,      // ← 【一个固定的实体号】
    std::nullopt,                          // ← 没有 owner
    brushOrigin, brushAngles, brushModel);
if (!entity) return nullopt;

TraceResult initialTrace{ .fraction = 1.0f };
const auto trace = traceTransformedBrushModel(
    initialTrace, origin, origin,          // ← 【start == end】
    bounds, *entity, SvGlassState{});
return trace ? optional{ trace->startSolid } : std::nullopt;
```

### 8.1 **`start == end`**

**⇒ 一个"零长度"的 trace** —— 所以它只回答"起点是否在实心内"。

**⇒ 这正是"接触"的定义** ✓

### 8.2 而返回 `startSolid`

**⇒ 所以 `contactBrushModel` 返回的是 `optional<bool>`，即"是否在内部"。**

**⇒ `nullopt` = trace 失败；`true` = 接触；`false` = 不接触。**

### 8.3 **`MaximumServerCollisionEntityNum` 是一个"临时实体号"**

**⇒ 用于链接一个"不是真实体"的 brush model。**

**⇒ 这是一个"借用实体槽"的手法。**

### 8.4 `SvGlassState{}` 是**空状态**

**⇒ 所以玻璃不参与这个 trace。**

**⇒ 因为这是"brush model 接触"查询，玻璃是另一层。**

## 九、`traceCapsule` 的开头

```cpp
if (!trace_ || !validTraceInput(start, end, bounds, contentMask))
    return nullopt;

NativeTraceResult native{};
trace_(&native, start.data(), end.data(), &bounds, passEntityNum, contentMask);
```

### 9.1 **五项输入**

```text
start       3 float
end         3 float
bounds      TraceBounds
passEntityNum  int32
contentMask    uint32
```

### 9.2 而 `trace_` 是**原生函数指针**

**`trace_(&native, start.data(), end.data(), &bounds, passEntityNum, contentMask)`**

**⇒ 五个参数 + 输出 ⇒ 六个。**

**⇒ 这与 §204 里 `SV_Trace` 的"四个错误参数"形成对照** —— 那里参数错，这里看起来是对的。

**⇒ 待读余下部分确认返回值处理。**

## 十、关键结论

1. **`0x00661C50` 与 3.3.3.3 的 `0x005851F0` 逐指令相同，只差一个操作数** —— 形状与步长 8 沿用，头表地址不同。
2. **头表在 `0x077D8188`**（不是 3.3.3.3 的 `0x2DF7CE8`）。
3. **"本树没有任何东西解引用它"** —— 但引用时要写对。
4. **类型 5 的 1507 项全是播音员语音** ⇒ 所以改为枚举全部 16 个类型。
5. **十二个 `Wanted` 关键词，都是子串匹配** ⇒ `"hit"` 会命中 `directhit`。
6. **16 个类型 × 16384 项 × 12 个关键词** —— 但 `limit` 只限打印不限统计。
7. **诊断函数用 `break`（与 §261 的 `continue` 相反）** ⇒ 稀疏链会低估 `total`。
8. **材质名上限是 64 而其它是 128**。
9. **`types[i] >= 23` 而 §236 是 `== 21 || >= 23`** —— 一处不一致。
10. **`ConfigStringTypesRva = 0x73D8250`，VA `0x77D8250`，而 CCS 头表 `0x077D8188` 在其前 200 字节**。
11. **碰撞图 `+0x90` count、`+0x94` models 指针**，五项界含乘法溢出防御。
12. **`contents = leafBrushContents | leafTerrainContents`** —— 内容位合并。
13. **`contactBrushModel` 用 `start == end` 的 trace，返回 `startSolid`**。
14. **`MaximumServerCollisionEntityNum` 是一个借用的临时实体槽**。

## 十五、未闭合点

- 16 个 CCS 类型的实际总数（诊断的 `break` 可能低估）。
- `types[i] >= 23` 缺 `== 21` 是否有意。
- `NativeBrushModel` 的尺寸。
- `EngineBindings.cpp` 17250 行之后未读取。
