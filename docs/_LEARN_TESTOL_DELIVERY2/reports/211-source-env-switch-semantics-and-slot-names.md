# 211 · 五个环境开关的四种语义、三个读串函数的差别、17 个附件槽名

## 一、范围

本报告学习 `EngineBindings.cpp` 3377–3556 行。

## 二、四个环境开关，**同一种严格语义**

```cpp
bool dobjGeomDiagnosticsEnabled()  → OLMOD_DOBJ_GEOM_DIAGNOSTICS
bool hitboxDiagnosticsEnabled()    → OLMOD_HITBOX_DIAGNOSTICS
bool nativeCapsuleTraceEnabled()   → OLMOD_NATIVE_CAPSULE_TRACE
bool nativeTraceComparisonEnabled()→ OLMOD_NATIVE_TRACE_COMPARISON
```

**四个函数的实现逐字节相同**：

```cpp
static const bool enabled = [] {
    std::array<char, 8> value{};
    const auto size = GetEnvironmentVariableA(NAME, value.data(), (DWORD)value.size());
    return size == 1 && value[0] == '1';
}();
```

### 2.1 严格语义：**必须恰好是 "1"**

```text
size == 1 && value[0] == '1'
```

**`"true"`、`"yes"`、`"01"`、`"1 "` 全都是关**。

### 2.2 与前面几处**宽松语义**形成对照

§162 里 `installClientRenderFrameHook`：

```cpp
enabled = size && value[0] != '0' && value[0] != 'n' &&
          value[0] != 'N' && value[0] != 'f' && value[0] != 'F';
```

**接受任何非 0/n/f 开头的值** —— 所以 `"1"`、`"true"`、`"yes"`、`"on"` 都开。

### 2.3 两种语义各有适用场景

| 语义 | 适用 | 后果 |
|---|---|---|
| **严格 `== "1"`** | 高风险诊断（改行为、打补丁） | 误配时**安全失败**（关） |
| **宽松 `!= "0nNfF"`** | 生产修复（打补丁但已验证） | 误配时**功能可用** |

**这四个是诊断开关**，所以用严格的 —— **误配时宁可不跑**。

而 §201 的 `characterModelResolutionEnabled` 是**另一种**：

```cpp
if (getenv_s(...) != 0 || size < 2) return true;
return value[0] != '0';
```

**缺省为开**，只有 `"0"` 关 —— 因为它已经是生产路径。

**所以本文件里有三种开关语义**：

```text
1. 严格 == "1"        → 缺省关，诊断
2. 宽松 != "0nNfF"    → 缺省关，生产修复
3. 缺省开，== "0" 关  → 生产路径 + kill switch
```

## 三、`nativeCapsuleTraceEnabled` 的一段重要说明

```cpp
// OLMOD(capsule-entity-collision): section 74 kill switch. out.exe's
// 0x0046E780 is the CLIENT general trace, and its entity half walks the
// client's own centity array -- the array a dedicated server never
// fills. Setting this to 1 restores that call for a bisect; anything
// else, including leaving it unset, uses the source per-entity path.
```

**关键事实**：

> **`0x0046E780` 是【客户端】通用 trace，而它的实体那一半走客户端自己的 `centity` 数组 —— 那个 dedicated 服务器【从不填充】的数组。**

**这是与 §209 里 `SV_Trace` 分析的对立面**：`0x0046E780` 是客户端路径，`0x0046EA60` 是服务器路径。

**而 §209 里说 `sub_46EA60` 是"纯透传"到 `SV_Trace`** —— 所以两者是不同入口。

**"包括不设置它"都走源码路径** —— 所以缺省是**不用原生**。

## 四、三个读串函数的**三处细节差异**

### 4.1 `readCString(text, maxLength)`

```cpp
const auto textBytes = readableBytes(text);
if (!textBytes) return nullopt;
const auto limit = std::min(*textBytes, maximumLength);
const auto end = std::find(text, text + limit, '\0');
if (end == text || end == text + limit) return nullopt;   // ← 【空串也拒绝】
return std::string(text, end);
```

**`end == text`（空串）也返回 nullopt**。

### 4.2 `readStringTableCell(cell, maxLength = 128)`

```cpp
if (!cell.value) return std::string{};                    // ← 【null 返回空串】
const auto textBytes = readableBytes(cell.value);
if (!textBytes) return nullopt;
const auto limit = std::min(*textBytes, maximumLength);
const auto end = std::find(cell.value, cell.value + limit, '\0');
if (end == cell.value + limit) return nullopt;            // ← 【空串【不】拒绝】
return std::string(cell.value, end);
```

**两处不同**：

1. **`!cell.value` 返回空串而不是 nullopt**；
2. **`end == cell.value` 不拒绝**。

### 4.3 `readStringObject(object)`

```cpp
const auto objectBytes = readableBytes(object);
if (!objectBytes || *objectBytes < sizeof(const char*)) return nullopt;
const auto* text = *(const char* const*)object;
const auto textBytes = readableBytes(text);
if (!textBytes) return nullopt;
constexpr std::size_t MaximumLength = 128;
const auto limit = std::min(*textBytes, MaximumLength);
const auto end = std::find(text, text + limit, '\0');
if (end == text || end == text + limit) return nullopt;   // ← 【空串也拒绝】
return std::string(text, end);
```

**两级间接**：`object` 是一个含指针的对象，先读指针再读串。

**多一道检查**：`*objectBytes < sizeof(const char*)` —— 对象本身至少要能装下一个指针。

### 4.4 三者的语义差异汇总

| | null 对象 | 空串 | 无 NUL |
|---|---|---|---|
| `readCString` | nullopt | **nullopt** | nullopt |
| `readStringTableCell` | **空串** | **空串** | nullopt |
| `readStringObject` | nullopt | **nullopt** | nullopt |

**`readStringTableCell` 是唯一的"空即合法"** —— 因为 StringTable 的单元格可以合法为空。

## 五、`validBookingName`：白名单字符集

```cpp
return !value.empty() && value.size() <= 64 &&
    all_of(value, [](char c) {
        return c == '_' || c == '-' ||
               (c >= '0' && c <= '9') ||
               (c >= 'A' && c <= 'Z') ||
               (c >= 'a' && c <= 'z');
    });
```

**五个字符类**：下划线、连字符、数字、大写、小写。

**长度 1..64**。

**这是把地图名/模式名限制在安全字符集** —— 因为后面要拼进命令字符串或路径。

## 六、`asciiCaseInsensitiveEqual`

```cpp
if (left.size() != right.size()) return false;
return ranges::equal(left, right, [](char a, char b) {
    const auto lower = [](char v) { return v >= 'A' && v <= 'Z' ? (char)(v - 'A' + 'a') : v; };
    return lower(a) == lower(b);
});
```

**只对 A-Z 做小写化** —— 不是 `tolower`（那受 locale 影响）。

**与 §162 里 `Com_HashKey` 的小写化、§143 里 `SV_ForgeXAssetNamesEqual` 的小写化完全同一规则**。

**"只降 A-Z"** 是这三处共有的约定 —— 因为它们都要与引擎自己的比较规则一致。

## 七、`SlotNames`：17 个槽，最后一个 `dec` 是补上的

```cpp
constexpr std::array<std::string_view, WeaponAttachmentSlotCount> SlotNames{
    "wea", "sco", "muz", "bas", "hbs", "sto", "rai", "gri",
    "bip", "sra", "iro", "mag", "cam", "cqc", "rof", "ret",
    "dec",
};
```

### 7.1 顺序与索引

```text
索引  0 wea
      1 sco
      2 muz
      3 bas
      4 hbs
      5 sto
      6 rai
      7 gri
      8 bip
      9 sra
     10 iro
     11 mag
     12 cam
     13 cqc
     14 rof
     15 ret
     16 dec
```

**与 §200 的 `AttachmentSlotTables` 逐项对应**：

```text
bas → 3     cqc → 13    hbs → 4     iro → 10
muz → 2     rai → 6     ret → 15    sco → 1
sto → 5     gri → 7     bip → 8     sra → 9
mag → 11    cam → 12    dec → 16
```

**15 个有表**，而 `wea`（0）与 `rof`（14）**没有表**：

- `wea` = 武器本身，不是附件；
- `rof` = 射速，**"这个 build 上没有任何东西装备它"**（§200）。

### 7.2 `dec` 的补上过程

```text
DECORATION (`dec_*`)。这些物品像任何其它附件一样从客户端 profile 到达，
但这里没有名字时，每一个都会让 readAttachmentModelSlot 返回 `slot=none`
并在武器串构建【之前】被丢掉 —— 活体日志说
    attachment slot unresolved name=dec_littlesis
    tables=.............. slot=none
    attachment skipped item=16807 weapon=msrmodern_mp has no model slot
```

**`tables=..............`** —— **十四个点**，对应当时的 14 个表。

**"每一个都因此被丢掉"** —— 一次遗漏让一整类附件失效。

### 7.3 命名规则是**从资产读出来的**

> **表是 `mp/coweapitemsdec.csv`，而命名规则与产生 cam/iro/mag/sto 的是同一条，所以拼写是从资产读出来的而不是猜的。**

**"从资产读出而不是猜"** —— 与本项目反复出现的原则一致。

## 八、关键结论

1. **本文件有三种环境开关语义**：严格 `=="1"`、宽松 `!=0nNfF`、缺省开只认 `"0"`。
2. **诊断开关用严格语义**，所以误配时安全失败（关）。
3. **`0x0046E780` 是客户端 trace，实体那半走 `centity` 数组，dedicated 从不填充**。
4. **三个读串函数对"null / 空串 / 无 NUL"的处理各不相同**，`readStringTableCell` 是唯一"空即合法"。
5. **"只降 A-Z"在四处共用** —— 因为要与引擎自己的比较规则一致。
6. **`dec` 的遗漏让一整类装饰附件全部被丢弃**，而 `tables=..............`（14 个点）在日志里就是线索。

## 九、未闭合点

- `parseWeaponAttachmentSlot` 的返回（3556 行之后）未读取。
- `EngineBindings.cpp` 3556 行之后未读取。
