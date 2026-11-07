# 学习报告 102（重开）— `qcommon` 剩余 4 文件（`msg_mp` / `com_math` / `net_types`）

**学习范围**：`msg_mp.hpp`（1,436 B / 40 行）+ `msg_mp.cpp`（781 B / 27 行）+ `com_math.hpp`（736 B / 22 行）+ `net_types.hpp`（316 B / 12 行）
**性质**：全实测（**四文件逐行读完**，`qcommon` 8 文件至此全部完成）
**★★★★★ 本报告收录两个关键发现**：①**`msg_t` 的精确 ABI（0x30 字节 + 4 个偏移断言）** ②**`com_math` 的定点常量与 `net_dtls_cod` 的 conditionalAngle 常量完全一致**

---

## 一、★★★★★ **`msg_t` 的精确 ABI（编译期断言锁死）**

### 1.1 ★★★ 完整结构（`msg_mp.hpp:10-23`）

```cpp
struct msg_t
{
    std::int32_t  overflowed{};
    std::int32_t  readOnly{};
    std::uint8_t *data{};
    std::uint8_t *splitData{};
    std::int32_t  maxsize{};
    std::int32_t  cursize{};
    std::int32_t  splitSize{};
    std::int32_t  readcount{};
    std::int32_t  bit{};
    std::int32_t  lastEntityRef{};
    std::int32_t  flush{};
    std::int32_t  targetLocalNetID{};
};
```

### ★★★★★ 四个编译期断言（第 25–29 行，逐字）

```cpp
static_assert(sizeof(void *) != 4 || sizeof(msg_t) == **0x30**);
static_assert(sizeof(void *) != 4 || offsetof(msg_t, data)      == **0x08**);
static_assert(sizeof(void *) != 4 || offsetof(msg_t, cursize)   == **0x14**);
static_assert(sizeof(void *) != 4 || offsetof(msg_t, readcount) == **0x1C**);
static_assert(sizeof(void *) != 4 || offsetof(msg_t, bit)       == **0x20**);
```

### ★★★★★ 推导出的完整 32 位布局

| 偏移 | 大小 | 字段 |
|---|---|---|
| **0x00** | 4 | `overflowed` |
| **0x04** | 4 | `readOnly` |
| ★ **0x08** | **4** | **`data`**（指针） |
| **0x0C** | 4 | `splitData`（指针） |
| **0x10** | 4 | `maxsize` |
| ★ **0x14** | **4** | **`cursize`** |
| **0x18** | 4 | `splitSize` |
| ★ **0x1C** | **4** | **`readcount`** |
| ★ **0x20** | **4** | **`bit`** |
| **0x24** | 4 | `lastEntityRef` |
| **0x28** | 4 | `flush` |
| **0x2C** | 4 | `targetLocalNetID` |
| ★ **0x30** | — | **总大小** ✓ |

★★★ **⇒ `0x30` = 48 字节,`12` 个字段全部 `4` 字节（含两个指针）⇒ 32 位布局,无填充。**

### ★★★★★ **`sizeof(void *) != 4 ||` 的意义**

```
这个断言只在 **32 位**（`sizeof(void*) == 4`）时生效
        ↓
★★★ 因为 `msg_t` 的布局**只对 32 位有意义**
   （64 位下两个指针是 8 字节 ⇒ 偏移全变）
        ↓
★★★ ⇒ **`msg_t` 是**原生 CODOL 的 32 位结构镜像**,必须逐字节一致**
   ⇒ 否则 `MSG_*` 函数与原生代码无法互操作
```

★★ **⇒ 这是**"用 `static_assert` 把 ABI 钉死"的第二个实例**（第一个是报告 095 的 `IServer::Address == 8`）。**

---

## 二、★★★★★ **`MsgWriter` 的接口（4 个纯虚 + 3 个非虚）**

### 2.1 ★★★ 完整定义（第 32–45 行）

```cpp
class MsgWriter
{
public:
    virtual ~MsgWriter() = default;                                     // ★ 有虚析构

    virtual void MSG_WriteData(std::span<const std::uint8_t> value) = 0;   // 纯虚
    virtual void MSG_WriteBits(std::int32_t value, std::uint32_t bits) = 0; // 纯虚
    virtual void MSG_WriteString(std::string_view value) = 0;              // 纯虚
    [[nodiscard]] virtual bool overflowed() const = 0;                    // 纯虚

    void MSG_WriteByte(std::uint8_t value);      // ★ 非虚（基类实现）
    void MSG_WriteShort(std::uint16_t value);    // ★
    void MSG_WriteLong(std::uint32_t value);     // ★
};
```

★★★★★ **⇒ 与报告 095 的 `IServer` **形成鲜明对比**：**
```
`IServer`    ⇒ **刻意无虚析构**（实例由插件持有到进程结束）
`MsgWriter`  ⇒ **有虚析构**（`virtual ~MsgWriter() = default;`）
        ↓
★★★ ⇒ 两个接口的**生命周期模型不同**：
   `IServer` 由外部持有 ⇒ 不需要析构
   `MsgWriter` 可能由 `unique_ptr<MsgWriter>` 持有 ⇒ 需要虚析构
```

★★ **⇒ 且三个 `MSG_Write*` 是**非虚的便捷包装**,建立在 `MSG_WriteData` 之上。**

### ★★★ 三个便捷函数的实现（`msg_mp.cpp`）

```cpp
void MsgWriter::MSG_WriteByte(const std::uint8_t value)
{
    MSG_WriteData(std::span(&value, 1));                       // ★ 1 字节
}

void MsgWriter::MSG_WriteShort(const std::uint16_t value)
{
    const std::array bytes{
        static_cast<std::uint8_t>(value),                      // ★ 低字节先
        static_cast<std::uint8_t>(value >> 8),
    };
    MSG_WriteData(bytes);
}

void MsgWriter::MSG_WriteLong(const std::uint32_t value)
{
    const std::array bytes{
        static_cast<std::uint8_t>(value),                      // ★ 小端
        static_cast<std::uint8_t>(value >> 8),
        static_cast<std::uint8_t>(value >> 16),
        static_cast<std::uint8_t>(value >> 24),
    };
    MSG_WriteData(bytes);
}
```

★★★ **⇒ 全部**小端**（与报告 099/101 的 `appendU16`/`appendU32` **完全一致**）。**

★★ **⇒ 三个函数**只依赖 `MSG_WriteData`** ⇒ 子类只需实现 4 个纯虚即可。**

---

## 三、★★★★★ **`com_math` 的定点常量与 `net_dtls_cod` 完全一致**

### 3.1 ★★★ 完整定义（`com_math.hpp`）

```cpp
constexpr float ShortAngleScale = **360.0f / 65536.0f**;   // = 0.0054931640625f
constexpr float AngleShortScale = **65536.0f / 360.0f**;   // = 182.0444488525391f

[[nodiscard]] inline float BG_ShortToAngle(const std::uint16_t value)
{
    return static_cast<float>(value) * ShortAngleScale;
}

[[nodiscard]] inline std::uint16_t BG_AngleToShort(const float value)
{
    return static_cast<std::uint16_t>(static_cast<std::int32_t>(value * AngleShortScale));
}

[[nodiscard]] inline float BG_NormalizeAngle360(const float value)
{
    const auto wrapped = std::fmod(value, 360.0f);
    return wrapped < 0.0f ? wrapped + 360.0f : wrapped;
}
```

### ★★★★★ 与报告 099 的**精确对应**

```
报告 099（`net_chan_mp.cpp` 的 conditionalAngle）：
    baselineAngle = (int16)(baseline.conditionalAngle * **182.0444488525391f**);
    command.conditionalAngle = (float)(int16)(value) * **0.0054931640625f**;
        ↓
本报告（`com_math.hpp`）：
    **`AngleShortScale = 65536.0f / 360.0f`** = **182.0444488525391f** ✓
    **`ShortAngleScale = 360.0f / 65536.0f`** = **0.0054931640625f** ✓
        ↓
★★★★★ ⇒ **同一对常量在两处独立定义,数值完全一致**
   ⇒ 且本报告给出了它们的**解析形式**（`65536/360` 与 `360/65536`）
```

★★★ **⇒ 确立了**角度定点编码的标准**：**
```
**16 位定点角度**：全圆 360° = **65536** 单位
  `angle → short`  ⇒ `angle * (65536/360)`
  `short → angle`  ⇒ `short * (360/65536)`
        ↓
★★★ ⇒ 即**每单位 = 360/65536 ≈ 0.00549°**（精度约 **0.0055°**）
```

★★ **⇒ 三个函数名用 `BG_` 前缀（`BG` = **B**ase**G**ame?）⇒ 与 IW 的 `bg_*.c` 血统一致。**

### ★★★ `BG_AngleToShort` 的**有符号中转**

```cpp
return static_cast<std::uint16_t>(static_cast<std::int32_t>(value * AngleShortScale));
```

★★ **⇒ 先转 `int32` 再转 `uint16` ⇒ 负角度会**环绕**（如 −90° → 49152）。**
**⇒ 而 `BG_NormalizeAngle360` 提供显式的 `[0, 360)` 归一化。**

### ★★★ `BG_NormalizeAngle360` 的负数处理

```cpp
const auto wrapped = std::fmod(value, 360.0f);
return wrapped < 0.0f ? wrapped + 360.0f : wrapped;
```

★★ **⇒ `fmod` 对负数返回负值 ⇒ 加 360 修正到 `[0, 360)`。**

---

## 四、★★★★★ **`net_types.hpp`：`PeerAddress` 与一个重要的否定声明**

### 4.1 ★★★ 完整定义

```cpp
// Transport identity used by the plugin. This is **not CODOL's in-memory netadr_t layout**.
struct PeerAddress
{
    std::uint32_t ipv4{};
    std::uint16_t port{};

    bool operator==(const PeerAddress &) const = default;
};
```

★★★★★ **⇒ 一行关键否定声明：**
```
"Transport identity used by the plugin.
 This is **not CODOL's in-memory `netadr_t` layout**."
        ↓
★★★ ⇒ `PeerAddress`（8 字节,`u32 + u16`）是**插件自己的传输身份**
   ⇒ **不是**原生 CODOL 的 `netadr_t`
        ↓
★ 与报告 095 的 `IServer::Address`（也是 8 字节,`u32 + u16`）**同尺寸但语义不同**
```

★★ **⇒ 两个 8 字节结构的对照：**

| 结构 | 定义处 | 语义 |
|---|---|---|
| **`IServer::Address`** | `LocalnetServer.hpp`（095） | ★ **2019 Ayria 插件 ABI** 的地址 |
| **`PeerAddress`** | `net_types.hpp`（102） | ★★ **本插件自己的**传输身份 |

★★★ **⇒ 两者都是 `u32 ipv4 + u16 port` = 8 字节（含 2 字节填充）,但一个是外部 ABI,一个是内部类型。**

---

## 五、★★★★★ **`qcommon` 8 文件全部完成 —— 收官账**

| # | 文件 | 字节 | 行 | 报告 |
|---|---|---|---|---|
| 1 | **`net_chan_mp.hpp`** | 7,412 | 182 | **098** |
| 2 | **`net_chan_mp.cpp`** | 50,686 | **1,106** | **099** |
| 3 | **`net_dtls_cod.hpp`** | 7,620 | 212 | **100** |
| 4 | **`net_dtls_cod.cpp`** | 34,426 | **831** | **101** |
| 5 | **`msg_mp.hpp`** | 1,436 | 40 | ★ **102** |
| 6 | **`msg_mp.cpp`** | 781 | 27 | ★ **102** |
| 7 | **`com_math.hpp`** | 736 | 22 | ★ **102** |
| 8 | **`net_types.hpp`** | 316 | 12 | ★ **102** |
| **合计** | — | **103,413** ✓ | **2,432** | **5 份报告（098–102）** |

★★★ **⇒ `qcommon` 8 文件 / 103,413 B / 2,432 行 = **100% 逐行读完**。**

### ★★★★★ 累计进度

| 模块 | 文件 | 字节 | 行 | 状态 |
|---|---|---|---|---|
| **`shared\`** | **10** | **112,091** | **2,776** | ★ **✓ 100%** |
| **`qcommon\`** | **8** | **103,413** | **2,432** | ★ **✓ 100%** |
| `backend\Demonware` | 52 | 549,733 | — | 待读 |
| `backend`（根） | 13 | 127,397 | — | 待读 |
| `game_server`（根） | 32 | 2,175,797 | — | 待读 |
| `server_mp` | **154** | **12,604,630** | — | 待读 |
| `localnetworking` | 6 | 76,563 | — | 待读 |
| `platformwrapper` | 7 | 21,720 | — | 待读 |
| `client_bridge` | 2 | 7,130 | — | 待读 |
| `win32` | 2 | 6,852 | — | 待读 |
| **合计** | **286** | **15,785,326** | **163,455** | **18 / 286 = 6.3% 文件** |

★★ **⇒ 按行数算：**5,208 / 163,455 = **3.2%**。**
**⇒ 但 `shared\` + `qcommon\` 是**协议与线格式的全部**（价值密度最高）。**

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **`msg_t` = `0x30`（48 字节）** | 12 个字段全 4 字节（含 2 个指针）⇒ **32 位布局,无填充** |
| 2 | ★★★★ **4 个偏移断言** | `data` **`0x08`** / `cursize` **`0x14`** / `readcount` **`0x1C`** / `bit` **`0x20`** |
| 3 | ★★★ `sizeof(void*) != 4 \|\|` 前缀 | 断言**只在 32 位生效** ⇒ `msg_t` 是**原生 CODOL 的 32 位结构镜像** |
| 4 | ★★★ `msg_t` 的 12 字段 | `overflowed` / `readOnly` / `data` / `splitData` / `maxsize` / `cursize` / `splitSize` / `readcount` / `bit` / `lastEntityRef` / `flush` / `targetLocalNetID` |
| 5 | ★★★★★ **`MsgWriter` 有虚析构** | 与报告 095 的 `IServer`（**刻意无虚析构**）**形成对比** ⇒ 生命周期模型不同 |
| 6 | ★★ 4 个纯虚 | `MSG_WriteData` / `MSG_WriteBits` / `MSG_WriteString` / `overflowed` |
| 7 | ★★ 3 个非虚便捷 | `MSG_WriteByte` / `MSG_WriteShort` / `MSG_WriteLong`（**全部小端**） |
| 8 | ★★★★★ **`com_math` 常量与 099 完全一致** | `ShortAngleScale = **360/65536**` = **0.0054931640625f**；`AngleShortScale = **65536/360**` = **182.0444488525391f** |
| 9 | ★★★★ **角度定点标准** | **全圆 360° = 65536 单位**,精度 **0.0055°** |
| 10 | ★★ `BG_AngleToShort` | 先转 `int32` 再转 `uint16` ⇒ 负角度**环绕** |
| 11 | ★★ `BG_NormalizeAngle360` | `fmod` 后若为负则 **+360** ⇒ `[0, 360)` |
| 12 | ★★★ `BG_` 前缀 | 与 IW 的 `bg_*.c` 血统一致 |
| 13 | ★★★★★ **`PeerAddress` 的否定声明** | "This is **not CODOL's in-memory `netadr_t` layout**" |
| 14 | ★★ 两个 8 字节结构 | `IServer::Address`（**外部 ABI**,095）vs `PeerAddress`（**内部类型**,102）⇒ **同尺寸,语义不同** |
| 15 | ★★★★★ **`qcommon` 收官** | **8 文件 / 103,413 B / 2,432 行 = 100%** |
| 16 | ★★ 累计 | `shared\` + `qcommon\` = **18 文件 / 5,208 行**（**163,455 行的 3.2%**,但覆盖**协议与线格式的全部**） |

---

## 七、结论

### 1. ★★★★★ **`msg_t` 的 ABI 被 4 个 `static_assert` 钉死**（`0x30` + 偏移 `0x08`/`0x14`/`0x1C`/`0x20`）

★ **⇒ 且断言只在 **32 位**生效 ⇒ `msg_t` 是**原生 CODOL 的 32 位结构镜像**。**

### 2. ★★★★★ **`com_math` 的角度定点常量与 `net_chan_mp.cpp` 完全一致**

```
`AngleShortScale = 65536/360` = **182.0444488525391f**
`ShortAngleScale = 360/65536` = **0.0054931640625f**
        ↓
★★★ ⇒ **全圆 360° = 65536 单位,精度 0.0055°**
   ⇒ 且给出了**解析形式**（之前只有小数）
```

### 3. ★★★★ **两个接口的生命周期模型相反**（`IServer` 无虚析构 / `MsgWriter` 有）

### 4. ★★★★★ **`PeerAddress` 明确声明"不是 `netadr_t`"**

★ **⇒ 与 `IServer::Address` **同尺寸（8 字节）但语义不同**（外部 ABI vs 内部类型）。**

### 5. ★★★★★ **`qcommon` 8 文件 100% 完成**（103,413 B / 2,432 行）

★ **⇒ 加上 `shared\` 的 10 文件,**两个模块合计 18 文件 / 5,208 行** ——
覆盖了**线格式与协议的全部**（netchan / DTLS / 会话 / 控制）。**

---

## 八、下一步

- ★★★ **`backend\Demonware\`（52 文件 / 549,733 B）** —— 15 个服务的实现
- 然后 `backend`（根，13 文件）/ `game_server`（根，32 文件）/ `server_mp`（154 文件）
