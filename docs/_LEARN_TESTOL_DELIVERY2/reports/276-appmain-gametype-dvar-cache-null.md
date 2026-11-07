# 276 · **`0x0043204F` 的 `edx=0`**、`ui_mp` 区未加载的因果链、抢修与"引擎是否抢先"的判据

## 一、范围

本报告学习 `Appmain.cpp` 1263–1480 行。

## 二、**`0x0043204F` 的 `edx=0`**（本组最重要的一段）

### 2.1 那段完整因果

```php
// OLMOD(section-79-ui-dvar-cache): THE CLIENT'S GAMETYPE DVAR CACHE, AND WHY
// A LEVEL LOAD FAULTS WITHOUT IT.
//
// Every cycle that lost the client died at 0x0043204F with edx = 0, which is
// `mov edx,[0x032AA908]; mov ecx,[edx+0x0C]` -- the CACHED POINTER to the
// g_gametype dvar, then its string. The dvar itself is fine; only the cache
// is missing. That cache has exactly one writer, `sub_4E8990`, whose caller
// chain is gated on DB_IsZoneLoaded("ui_mp"), and a client we drive straight
// into a match never loads the legacy UI zone. CL_ParseGamestate -> the level
// load -> mp/gametypeWeaponCustomTable.csv then dereferences NULL on the
// FIRST weapon it resolves, so the fault is unconditional once we get there.
```

### 2.2 六层

```text
1. 每一个丢失客户端的周期都死在 `0x0043204F` 而 `edx = 0`
2. 那两条指令是 `mov edx,[0x032AA908]; mov ecx,[edx+0x0C]`
3. ⇒ `0x032AA908` 是 g_gametype dvar 的【缓存指针】，然后读它的字符串（`+0x0C`）
4. dvar 本身是好的；【只有缓存缺失】
5. 那个缓存【恰好一个】写入者 `sub_4E8990`，其调用链被 `DB_IsZoneLoaded("ui_mp")` 门控
6. 而我们直接驱入比赛的一个客户端【从不加载遗留的 UI 区】
7. ⇒ `CL_ParseGamestate` → 关卡加载 → `mp/gametypeWeaponCustomTable.csv` 然后对【它解析的第一把武器】解引用 NULL
```

### 2.3 而"一旦到那里故障就是无条件的"

**⇒ 因为 `mp/gametypeWeaponCustomTable.csv` 的每一行都会读那个 dvar。**

**⇒ 所以在**第一把武器**就崩。**

### 2.4 与 §245 的**同一个文件**对照

**§245**："`sub_432130` 载入 `mp/gametypeWeaponCustomTable.csv` 并逐武器问当前 gametype 是否在该行的 `|` 分隔列表里 —— 而 `sub_432000` 用 `mov ecx, [edx+0Ch]` 读 g_gametype dvar，**无保护**。专用服里那个 dvar 从未注册（唯一注册它的是 `CG_Init`），所以 `edx` 是 0 而读 `0xC` 就是整个 fault。"

**⇒ 完全相同的机制，两个不同的进程：**

```text
§245  专用服   dvar 从未【注册】  ⇒ edx = 0
§276  客户端   dvar 已注册而【缓存】未填充 ⇒ edx = 0
```

**⇒ 同一个 `mov ecx,[edx+0Ch]`，两个不同的上游原因。**

**⇒ §245 的修法是"调 `registerGameplayDvars()`"，§276 的修法是"调 `RegisterGameplayDvarsRva`"。**

**⚠ 而两个 RVA 可能不同**（一个 `registerGameplayDvars()` 是 `Appmain.cpp` 自己的函数，另一个是引擎的 `sub_4E8990` 链的入口）。

### 2.5 而 `0x032AA908` 是**缓存槽地址**

**⇒ 所以"缓存"是一个全局的 `dvar_t*` 指针，而它必须是 `g_gametype` 的地址。**

**⇒ 与记忆里"dvar 对象 +0xC 是值；`dw_autoStartGame`=1 不是闸门"同一读法** ✓

**⇒ `+0x0C` 是值的指针** ✓

## 三、`clientUiDvarRepairEnabled` 的**第七种解析**

```php
// Default ON: without it no cycle reaches a spawn at all.
return !(size == 1 && value[0] == '0');
```

### 3.1 三层

```text
未设置            ⇒ 开
设为单元 '0'      ⇒ 关
设为其它          ⇒ 开
```

**⇒ 这是**默认开**的第七种模式。**

**⇒ 而 §274 的 `CODOL_CLIENT_EXECUTION_STATE_PATCH` 也是默认开但用五字符否定。**

**⇒ 两个默认开的变量用两种规则。**

### 3.2 "没有它没有任何周期能到达一个 spawn"

**⇒ 所以这是一个**必需**的修复** —— 而不是可选的。

## 四、**"必须能看到引擎赢"**（本组第二重要）

```php
// OLMOD(section-79d): AND IT MUST BE ABLE TO SEE THE ENGINE WIN.
// The first version repaired on the first frame the cache was NULL, which
// makes the question "does the engine ever fill it on its own?" permanently
// unanswerable -- the repair always gets there first. Hold off for a while,
// report the NULL->populated transition if it happens, and only then repair.
// The match flow needs ninety seconds from client start to gamestate, so a
// thirty-second wait is comfortably ahead of the reader.
```

### 4.1 五层

```text
1. 第一版在缓存为 NULL 的【第一帧】就修复
2. ⇒ 这让"引擎会自己填它吗"这个问题【永久不可答】
3. 因为修复总是抢先
4. ⇒ 所以【等一会儿】，报告 NULL→populated 的转变（如果发生），然后才修复
5. 而比赛流程从客户端启动到 gamestate 需要【90 秒】，所以 30 秒的等待【稳妥地早于读取者】
```

### 4.2 **这是一个教科书级的诊断设计**

**⇒ "抢修会抹掉它要测量的事实。"**

**⇒ 与 §243 里"零与错地址读起来一样"、§255 里"EMPTY 被当成 UNREADABLE"是同一族，但这次是**主动避免**。**

### 4.3 三个数

```text
90 秒      客户端启动到 gamestate
30 秒      等待
（所以余量 60 秒）
```

### 4.4 而"其他什么都不打印"的那个条件

```php
// This runs in the CLIENT process only. It is SILENT while the cache is
// populated -- if this ever stops printing, the engine got there first and
// the repair is dead code that should be deleted rather than kept.
```

**⇒ **"如果这永远停止打印，引擎先到了，而修复是应该删除而不是保留的死代码。"**

**⇒ 这是一个**自删除条件** —— 明确写出了"什么时候它是多余的"。

### 4.5 而那个 `by=%s` 的判据

```php
snprintf(line, ...,
    "client gametype dvar cache POPULATED by=%s cache=0x%08X afterMs=%lu",
    repaired ? "repair" : "THE ENGINE", cache,
    nowMilliseconds - firstNullTick);
```

**⇒ `by=repair` 或 `by=THE ENGINE`** —— 两种来源。**

**⇒ 而 `afterMs` 给出时间差。**

**✓ 一行日志回答"谁填的、多久之后"。**

## 五、四个状态量

```php
static bool reported = false;
static bool repaired = false;
static bool settled = false;
static std::uint32_t firstNullTick{};
```

### 5.1 四个

```text
reported     已报告过 NULL
repaired     已修复过
settled      已结算（无论谁填的）
firstNullTick  第一次看到 NULL 的时刻
```

### 5.2 而 `settled` 是"已记录 POPULATED"

**⇒ 所以 `reported && !settled` 是"报告过 NULL 但还没结算"。**

**⇒ 而如果引擎填了，`settled = true` 并打 `by=THE ENGINE`。**

### 5.3 而"修复后不会重复"

```php
if (!clientUiDvarRepairEnabled() || repaired) return;
```

**⇒ `repaired` 保证只修一次。**

## 六、`maintainClientGametypeDvarCache` 的**三段**

### 6.1 第一段：缓存非零 ⇒ 可能结算

```php
const auto cache = *(const uint32*)(base + GametypeDvarCacheRva);
if (cache != 0)
{
    if (reported && !settled) { settled = true; ... "POPULATED by=..." ... }
    return;
}
```

### 6.2 第二段：首次看到 NULL ⇒ 报告

```php
if (!reported)
{
    reported = true;
    firstNullTick = nowMilliseconds;
    snprintf(line, ..., "client gametype dvar cache NULL zone=%s loaded=%d stateFlags=0x%02X repair=%d",
        uiZoneName, isZoneLoaded(uiZoneName) ? 1 : 0, flags, clientUiDvarRepairEnabled() ? 1 : 0);
    logGameServer(line.data());
}
```

**⇒ 四个量**：

```text
zone 名
该 zone 是否 loaded
stateFlags（uint8）
repair 是否启用
```

**⇒ 所以"为什么缓存是 NULL"由 `loaded` 与 `stateFlags` 回答。**

### 6.3 三个 RVA

```php
IsZoneLoadedRva              DB_IsZoneLoaded 的地址
UiZoneNameRva                "ui_mp" 字符串的地址
UiZoneStateFlagsRva          区状态标志（uint8）
```

**⇒ 而 `isZoneLoaded(uiZoneName)` 是**调用引擎函数**。**

**⇒ 所以这里有一次原生调用（在游戏线程上？）。**

### 6.4 第三段：延迟后修复

```php
if (!clientUiDvarRepairEnabled() || repaired) return;
if (nowMilliseconds - firstNullTick < clientUiDvarRepairDelayMs()) return;
repaired = true;

// Logged BEFORE the call on purpose: if the client dies inside the
// registration this line is the only thing that says so.
logGameServer("client gametype dvar cache repair CALLING sub_4E8990");
reinterpret_cast<RegisterGameplayDvars>(base + RegisterGameplayDvarsRva)();

const auto after = *(const uint32*)(base + GametypeDvarCacheRva);
snprintf(done, ..., "client gametype dvar cache repair RETURNED cache=0x%08X", after);
```

### 6.5 那句话

**"故意在调用**之前**记录：如果客户端在注册内部死掉，这一行是唯一说明它的东西。"**

**⇒ 所以"调用前日志 + 调用后日志"是一对**围栏**。**

**⇒ 与 §249 里"`logged before the call`"（§248 的 `tryLinkXAssetEntry`）同族。**

### 6.6 而 `repaired = true` 在**调用之前**

**⇒ 如果调用死掉，`repaired` 已经是 true ⇒ 不会重试。**

**⚠ 这与"调用前日志"是同一意图（记录意图），但如果调用**没死却失败**，也不会重试。**

**⇒ 可能是有意的（避免反复调用）。**

## 七、`clientUiDvarRepairDelayMs` 的**第七种解析**

```php
const auto size = GetEnvironmentVariableA("OLMOD_CLIENT_UI_DVAR_REPAIR_DELAY_MS", value.data(), 16);
if (size == 0 || size >= value.size()) return 30000u;
const auto parsed = std::strtoul(value.data(), nullptr, 10);
return (uint32)parsed;
```

### 7.1 两项

```text
size == 0         ⇒ 默认 30000
size >= 16        ⇒ 默认 30000
```

### 7.2 ⚠ **`strtoul` 不检查全消费与错误**

**⇒ `"abc"` 会得到 0 ⇒ **延迟 0** ⇒ **立即修复**（破坏 §4 的设计）。**

**⇒ `"-5"` 会得到一个巨大的 `uint32`（回绕）⇒ 永不修复。**

**⚠ 两个方向的错误都很严重** —— 而 `glassDamageThresholds`（§276 后面）用的是**正确的** `from_chars` + 全消费检查。

**⇒ 所以同一个文件里既有正确做法也有错误做法。**

## 八、`glassDamageThresholds` 的**正确解析**（对照组）

```php
const auto read = [](const char *name, uint16 &output) {
    std::array<char, 16> value{};
    const auto size = GetEnvironmentVariableA(name, value.data(), 16);
    if (!size) return true;                          // 未设置 ⇒ 保持默认
    if (size >= value.size()) return false;           // 截断 ⇒ 失败
    uint32 parsed{};
    const auto [end, error] = std::from_chars(value.data(), value.data() + size, parsed);
    if (error != std::errc{} || end != value.data() + size || !parsed ||
        parsed > UINT16_MAX)
        return false;
    output = (uint16)parsed;
    return true;
};
if (!read("OLMOD_GLASS_DAMAGE_TO_WEAKEN", thresholds.weaken) ||
    !read("OLMOD_GLASS_DAMAGE_TO_DESTROY", thresholds.destroy) ||
    thresholds.weaken > thresholds.destroy)
    return nullopt;
```

### 8.1 五项检查

```text
未设置      ⇒ true（保持默认）
截断        ⇒ false
from_chars 失败 ⇒ false
未全消费    ⇒ false
parsed == 0 ⇒ false      ← 【0 不合法】
> 0xFFFF    ⇒ false
```

**⇒ 六项（我多算了一项）。**

### 8.2 而两个默认值

```php
CodolGameServer::SvGlassDamageThresholds thresholds{
    .weaken = 25,
    .destroy = 100,
};
```

**⇒ `weaken = 25`、`destroy = 100`。**

**⇒ 而注释说"Ghosts 派生的恢复默认值，等 CODOL 服务端 `glass_map`（type 17）提供原生阈值"。**

**⇒ 所以这两个数是**借来的**。**

**⇒ 与 §258 的玻璃 `definitionCount`/`pieceLimit` 相关但不同（那是容量，这是伤害阈值）。**

### 8.3 `weaken > destroy` ⇒ 整体失败

**⇒ 一个跨字段的一致性检查** ✓

## 九、`capsuleEntityProbeEnabled` 又一个 `size == 1 && '1'`

**⇒ 第七次/第八次出现。**

## 十、`runDObjLocationalProbe` 的三段射线（本组第三重要）

```php
constexpr uint32 ProbeClientNum = 0;
constexpr uint32 MaximumAttempts = 3;
if (!dobjLocationalProbeEnabled() || DObjLocationalProbe.completed ||
    DObjLocationalProbe.attemptCount >= MaximumAttempts ||
    !Server.worldNativeEntityMirrorSynchronized())
    return;

const auto sample = Server.worldPlayerSample(ProbeClientNum);
if (!sample || sample->playerState.pmType != 0) return;

const auto origin = sample->playerState.origin;
const std::array<std::pair<array<float,3>, array<float,3>>, 3> segments{
    // 段 1：x 方向
    { origin[0]-64, origin[1],      origin[2]+42 },
    { origin[0]+64, origin[1],      origin[2]+42 },
    // 段 2：y 方向
    { origin[0],    origin[1]-64,   origin[2]+42 },
    { origin[0],    origin[1]+64,   origin[2]+42 },
    // 段 3：垂直
    { origin[0],    origin[1],      origin[2]+96 },
    { origin[0],    origin[1],      origin[2]+8  },
};
```

### 10.1 六个端点

```text
段 1   沿 x：origin ± (64, 0, 42)
段 2   沿 y：origin ± (0, 64, 42)      ← 【§272 的自伤探针用的正是这一段】
段 3   垂直：origin + (0, 0, 96) → origin + (0, 0, 8)
```

### 10.2 而 `+42` 是**胸/腹高度**

**⇒ 站立时 `maxsZ = 70`（§273）⇒ `+42` 在躯干中部。**

**⇒ 而 `+96 → +8` 是**从头顶到地面**的垂直扫描。**

### 10.3 而 §272 的实测 `fraction=0.437363 partGroup=5` 正是**段 2**

**⇒ 所以段 2 打中 `partGroup=5`（大概是腹部或腿）。**

**⇒ 而 `0.437363` 意味着从 `origin-64` 出发，打到 `origin - 64 + 0.437363 × 128 = origin - 8.0`。**

**⇒ 所以命中点在 `origin.y - 8`** —— 距轴 8 单位。

**⇒ 而胶囊半径通常 15-20 ⇒ 所以**在内部**。**

**✓ 数学闭合。**

### 10.4 而三个前置

```text
开关
未完成
attemptCount < 3
原生实体镜像已同步
```

**⇒ `worldNativeEntityMirrorSynchronized()`** —— 与 §265/§268 的镜像检查同族。

### 10.5 而 `pmType != 0` 时返回

**⇒ `pmType` 是 pmove 类型** —— 0 大概是 `PM_NORMAL`。

**⇒ 所以只在正常移动状态下探测。**

## 十一、关键结论

1. **`0x0043204F` 的 `edx=0` 是 `g_gametype` dvar 的**缓存**指针缺失，而非 dvar 本身**。
2. **唯一写入者 `sub_4E8990` 的链被 `DB_IsZoneLoaded("ui_mp")` 门控**，而我们直接驱入比赛不加载 legacy UI 区。
3. **与 §245 的专用服问题是**同一指令、不同上游**（未注册 vs 未缓存）。
4. **"抢修会抹掉它要测量的事实"** —— 30 秒延迟让"引擎是否自己会填"可答。
5. **"如果这永远停止打印，修复是应该删除的死代码"** —— 明确的自删除条件。
6. **`by=THE ENGINE` / `by=repair`** —— 一行日志回答"谁填的"。
7. **"故意在调用前记录"** —— 与 §249 同族；而 `repaired = true` 也在调用前。
8. **`OLMOD_CLIENT_UI_DVAR_REPAIR_DELAY_MS` 的 `strtoul` 不检查** —— `"abc"` ⇒ 0 ⇒ 立即修复（破坏设计）。
9. **同一个文件里 `glassDamageThresholds` 用正确的 `from_chars` + 全消费** —— 对照组。
10. **玻璃默认 `25/100` 是从 Ghosts 借来的**，等 `glass_map`（type 17）。
11. **`runDObjLocationalProbe` 的三段射线**，而 §272 的 `fraction=0.437363 partGroup=5` 是段 2 且数学闭合（命中在轴内 8 单位）。
12. **`pmType != 0` 时跳过**（只在正常移动状态探测）。
13. **`MaximumAttempts = 3`**。

## 十二、未闭合点

- `GametypeDvarCacheRva`（`0x032AA908`）与 §245 的 `GametypeDvarRva` 是否不同。
- `RegisterGameplayDvarsRva` 与 `sub_4E8990` 的关系。
- `partGroup = 5` 对应的身体部位。
- `Appmain.cpp` 1480 行之后未读取。
