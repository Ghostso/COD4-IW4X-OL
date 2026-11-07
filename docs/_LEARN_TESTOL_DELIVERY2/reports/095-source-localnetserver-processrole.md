# 学习报告 095（重开）— `shared\LocalnetServer.hpp` + `ProcessRole.hpp`

**学习范围**：`LocalnetServer.hpp`（1,359 B / 50 行）+ `ProcessRole.hpp`（1,178 B / 45 行）
**性质**：全实测（**两个文件逐行读完**）
**★★★★★ 本报告收录一个**精确的 ABI 定义**（6 个虚函数 / 8 与 16 字节的结构体）与**三种进程角色**

---

## 一、★★★★★ **`IServer`：Localnetworking 插件的精确 ABI**

### 1.1 ★★★★★ 完整定义（第 5–31 行，逐字）

```cpp
// Exact Localnetworking plugin ABI used by the archived 2019 Ayria runtime.
// There is deliberately no virtual destructor: server instances remain owned
// by the Localnet32 plugin for the lifetime of the process.
struct IServer
{
    struct Address
    {
        std::uint32_t ipv4;
        std::uint16_t port;
    };

    struct Endpoints
    {
        Address client;
        Address server;
    };

    virtual void onConnect() {}
    virtual void onDisconnect() {}
    virtual bool onStreamread(void *data, std::uint32_t *size) = 0;
    virtual bool onStreamwrite(const void *data, std::uint32_t size) = 0;
    virtual bool onPacketread(void *data, std::uint32_t *size) = 0;
    virtual bool onPacketwrite(
        const void *data,
        std::uint32_t size,
        const Endpoints *endpoints) = 0;
};
```

### ★★★★★ 六个虚函数（完整 vtable）

| # | 签名 | 纯虚？ | 说明 |
|---|---|---|---|
| **1** | `void onConnect()` | 否（空实现） | 连接 |
| **2** | `void onDisconnect()` | 否（空实现） | 断开 |
| **3** | ★ `bool onStreamread(void *data, std::uint32_t *size)` | ★ **是** | **流读**（`size` 是**入出参数**） |
| **4** | `bool onStreamwrite(const void *data, std::uint32_t size)` | ★ **是** | **流写** |
| **5** | ★ `bool onPacketread(void *data, std::uint32_t *size)` | ★ **是** | **包读**（`size` 是**入出参数**） |
| **6** | ★★ `bool onPacketwrite(const void *data, std::uint32_t size, const Endpoints *endpoints)` | ★ **是** | **包写**（多一个 `Endpoints`） |

★★★ **⇒ 四个纯虚（3–6）+ 两个有默认实现（1–2）。**

### ★★★★★ 三个精确的设计要点

```
① ★★★ **"There is deliberately no virtual destructor"**
   ⇒ 理由（逐字）："server instances **remain owned by the Localnet32 plugin
     for the lifetime of the process**"
        ↓
★★★ ⇒ 这是**一个刻意的 ABI 约束**：实例由插件持有到进程结束,不需要析构
   ⇒ 与常规 C++ 接口设计**相反**（通常必须有虚析构）
        ↓
② ★★★ **`onStreamread` / `onPacketread` 的 `size` 是**指针**（`std::uint32_t *`）
   ⇒ **入出参数**（调用方给缓冲区大小,实现回填实际长度）
        ↓
③ ★★ **`onPacketwrite` 多一个 `const Endpoints *`**（客户端 + 服务端地址）
   ⇒ 而 `onStreamwrite` **没有**
```

### ★★★ "archived 2019 Ayria runtime" 的血统声明

```
"Exact Localnetworking plugin ABI used by the **archived 2019 Ayria runtime**."
        ↓
★★★ ⇒ 这个 ABI 是**2019 年那个 Ayria 运行时**的精确 ABI
   ⇒ 即：**ol-mod 必须与 2019 年的插件 ABI 二进制兼容**
        ↓
★ 与报告 082 的 `Localnetworking.Ayria32`（PE 时间戳被我覆盖）/
  报告 083 的 `kind: rebuilt` 呼应
```

### ★★★ 两个子结构与 `static_assert`（第 48–49 行）

```cpp
static_assert(sizeof(IServer::Address) == 8);
static_assert(sizeof(IServer::Endpoints) == 16);
```

★★★ **⇒ 编译期强制：**
```
`Address`   = u32 ipv4 + u16 port  ⇒ **8 字节**（含 2 字节对齐填充）
`Endpoints` = 2 × Address          ⇒ **16 字节**
        ↓
★★★ ⇒ **`Address` 的 8 字节意味着有 2 字节填充**（`u32` + `u16` = 6,对齐到 8）
   ⇒ 而 `static_assert` **锁死了这个填充**（否则与 2019 年的 ABI 不符）
```

★★ **⇒ 这是一个**ABI 兼容性的硬保证**（不是注释,是编译期断言）。**

### ★★★★★ `IStreamServer` 与 `IDatagramServer` 的**互补默认实现**

```cpp
struct IStreamServer : IServer
{
    bool onPacketread(void *, std::uint32_t *) override { return false; }
    bool onPacketwrite(const void *, std::uint32_t, const Endpoints *) override
    {
        return false;
    }
};

struct IDatagramServer : IServer
{
    bool onStreamread(void *, std::uint32_t *) override { return false; }
    bool onStreamwrite(const void *, std::uint32_t) override { return false; }
};
```

★★★★★ **⇒ 一个精确的"二选一"设计：**
```
`IStreamServer`（流式）  ⇒ **流读/流写**由子类实现,**包读/包写**返回 `false`
`IDatagramServer`（数据报）⇒ **包读/包写**由子类实现,**流读/流写**返回 `false`
        ↓
★★★ ⇒ **两者互补**:一个实现流,一个实现包;另一半**显式返回 false**（不实现）
```

★ **⇒ 与报告 090 的 RTTI 实测**完全吻合**：**
```
报告 090：`Alwaysoffline` 里有 `IServer` / `IStreamServer` / `IDatagramServer` 三个类
          且 `Auth3Server`/`LobbyServer`/`PendingStreamServer` 是流式,`StunServer` 是数据报
        ↓
★★★ 本报告：ABI 定义在此 ⇒ **代码级证实了报告 090 的推断** ✓
```

---

## 二、★★★★★ **`ProcessRole`：三种进程角色**

### 2.1 ★★★ 完整定义（第 10–51 行）

```cpp
enum class ProcessRole
{
    Combined,      // ★ 默认
    Client,
    Dedicated,
};

inline ProcessRole processRole()
{
    char *configured{};
    std::size_t configuredSize{};
    if (_dupenv_s(&configured, &configuredSize, "OLMOD_PROCESS_ROLE") != 0 ||
        !configured)
    {
        return ProcessRole::Combined;      // ★ 未设 ⇒ Combined
    }

    std::string role(configured);
    std::free(configured);
    std::ranges::transform(role, role.begin(), [](const unsigned char character) {
        return static_cast<char>(std::tolower(character));
    });
    if (role == "client")    return ProcessRole::Client;
    if (role == "dedicated") return ProcessRole::Dedicated;
    return ProcessRole::Combined;          // ★ 无法识别 ⇒ Combined
}

inline bool runsBackend(const ProcessRole role)
{
    return role != ProcessRole::Dedicated;
}

inline bool runsGameServer(const ProcessRole role)
{
    return role != ProcessRole::Client;
}
```

### ★★★★★ 完整的角色矩阵

| `OLMOD_PROCESS_ROLE` | `ProcessRole` | **`runsBackend`** | **`runsGameServer`** |
|---|---|---|---|
| **未设置** | **`Combined`** | ★ **true** | ★ **true** |
| **`"client"`**（不区分大小写） | **`Client`** | ★ **true** | ★★ **false** |
| **`"dedicated"`**（不区分大小写） | **`Dedicated`** | ★★ **false** | ★ **true** |
| 其他任何值 | **`Combined`** | true | true |

★★★ **⇒ 三条精确规律：**
```
① **未设置 / 无法识别 ⇒ `Combined`**（同时跑 backend + game server）
② ★ **`Client` ⇒ 只跑 backend**（`runsGameServer` 为 false）
③ ★ **`Dedicated` ⇒ 只跑 game server**（`runsBackend` 为 false）
        ↓
★★★ ⇒ **`Combined` = 两者都跑**（★ 与 `launch_chain.py` 的 `--combined` 对应）
```

★★ **⇒ 这与报告 017–019 的 `launch_chain.py` 三模式**完全吻合**：**
```
`launch_chain.py`：`--combined`（战斗服在进程内）/ `--no-dedicated`（**无战斗服**）
        ↓
本报告：`Combined` = backend + game server 都跑 ✓
        `Client`   = 只 backend（对应 `--no-dedicated`）
        `Dedicated`= 只 game server（对应双客户端专服路线）
```

### ★★★ 三个实现细节

```
① ★ **`_dupenv_s` 而非 `getenv`** ⇒ MSVC 的安全版本,会**分配内存**（所以有 `std::free`）
② ★★ **`std::tolower` 逐字符** ⇒ 环境变量**不区分大小写**（`"CLIENT"` / `"Client"` 都行）
③ ★★★ **无法识别的值 ⇒ `Combined`（不是报错）**
   ⇒ 与 `OLMOD_HOST_ADDRESS` 的"未设即回环"**同一哲学**（宽容默认）
```

### ★★★ `OLMOD_*` 环境变量累计

| 变量 | 来源 | 默认 |
|---|---|---|
| **`OLMOD_PROCESS_ROLE`** | 本文件 | ★ **`Combined`** |
| **`OLMOD_HOST_ADDRESS`** | 094 | ★ **`127.0.0.1`** |
| **`OLMOD_DEDICATED_CONTROL_PORT`** | 094 | 28961 |
| **`OLMOD_ALLOW_RAW_COMMAND`** | 094 | ★ **拒** |
| `OLMOD_CONSOLE_LOG` | 017–019 | — |
| `OLMOD_UNLOCK_ALL` | 020–043 | — |
| `OLMOD_SYNTHETIC_DNS` | memory | — |
| `OLMOD_ZM_COOP_SPAWN_ZONES` | 067 | — |
| `OLMOD_DUMP_MODEL_BAND` | 073 | — |
| `NT10_INJECT` | 020–043 | ★ **false** |

★★★ **⇒ 已确认 **10 个** `OLMOD_*` / `NT10_*` 环境变量。**
**⇒ 且其中 **4 个**遵循"**未设即安全默认**"的同一模式**（`PROCESS_ROLE` / `HOST_ADDRESS` / `ALLOW_RAW_COMMAND` / `NT10_INJECT`）。****

---

## 三、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ **`IServer` 血统** | **"Exact Localnetworking plugin ABI used by the archived 2019 Ayria runtime"** |
| 2 | ★★★★★ **6 个虚函数** | `onConnect` / `onDisconnect`（**有默认实现**）+ **4 个纯虚**：`onStreamread` / `onStreamwrite` / `onPacketread` / `onPacketwrite` |
| 3 | ★★★★ **无虚析构的理由** | **"server instances remain owned by the Localnet32 plugin for the lifetime of the process"** ⇒ 刻意的 ABI 约束 |
| 4 | ★★★ **`size` 是指针** | `onStreamread` / `onPacketread` 的 `std::uint32_t *size` = **入出参数** |
| 5 | ★★ `onPacketwrite` 多参数 | 多一个 **`const Endpoints *`**（`onStreamwrite` 没有） |
| 6 | ★★★ **`Address` = 8 字节** | `u32 ipv4 + u16 port` ⇒ **含 2 字节填充**,由 `static_assert` **锁死** |
| 7 | ★★ **`Endpoints` = 16 字节** | 2 × `Address` |
| 8 | ★★★★★ **两个子接口互补** | `IStreamServer` ⇒ 流读/写由子类实现,**包读/写返回 false**；`IDatagramServer` 反之 |
| 9 | ★★★ **与报告 090 吻合** | RTTI 里 `IServer`/`IStreamServer`/`IDatagramServer` 三类 ⇒ **代码级证实** |
| 10 | ★★★★★ **`ProcessRole` 三值** | **`Combined`（默认）/ `Client` / `Dedicated`** |
| 11 | ★★★ **角色矩阵** | 未设/无法识别 ⇒ **Combined**（backend + game server 都跑）；**Client ⇒ 只 backend**；**Dedicated ⇒ 只 game server** |
| 12 | ★★★ **与 `launch_chain.py` 吻合** | `Combined` ⇔ `--combined`；`Client` ⇔ `--no-dedicated` |
| 13 | ★★ `_dupenv_s` | MSVC 安全版（会分配内存 ⇒ 需 `std::free`） |
| 14 | ★★ **不区分大小写** | `std::tolower` 逐字符 ⇒ `"CLIENT"` / `"Client"` 都行 |
| 15 | ★★★ **宽容默认** | 无法识别 ⇒ `Combined`（不报错）⇒ 与 `OLMOD_HOST_ADDRESS` 同一哲学 |
| 16 | ★★ `OLMOD_*` 累计 | **10 个**（本文件 1 + 094 的 3 + 其他 6） |
| 17 | ★★ 四个"未设即安全默认" | `OLMOD_PROCESS_ROLE` / `OLMOD_HOST_ADDRESS` / `OLMOD_ALLOW_RAW_COMMAND` / `NT10_INJECT` |

---

## 四、结论

### 1. ★★★★★ **`IServer` 是一个**二进制兼容 2019 年 Ayria 运行时**的精确 ABI**

```
6 个虚函数（2 有默认 + 4 纯虚）
`Address` **8 字节**（含 2 字节填充,`static_assert` 锁死）
`Endpoints` **16 字节**
★★★ **刻意无虚析构**（实例由插件持有到进程结束）
        ↓
★★★ ⇒ 这是**为与既存二进制兼容而做的非常规设计**
```

### 2. ★★★★★ **`IStreamServer` / `IDatagramServer` 的互补默认实现被代码级证实**

★ **⇒ 与报告 090 从 RTTI 推断的"Auth3/Lobby/PendingStream 是流式,Stun 是数据报"**完全吻合**。**

### 3. ★★★★★ **`ProcessRole` 的三值矩阵解释了 `launch_chain.py` 的三种模式**

```
**未设 ⇒ `Combined`**（backend + game server 都跑）⇔ `--combined`
**`client` ⇒ 只 backend**                       ⇔ `--no-dedicated`
**`dedicated` ⇒ 只 game server**                ⇔ 双客户端专服路线
```

### 4. ★★★ **`OLMOD_*` 环境变量已达 10 个,其中 4 个遵循"未设即安全默认"**

### 5. ★★ **两处"宽容默认"**（无法识别的值不报错,退到安全默认）

---

## 五、下一步

- `shared\DedicatedControl.cpp`（36,106 B / 844 行）
- `shared\RuntimeLog.cpp`（398 行）
- 然后 `game_server\qcommon\`（8 文件 / 103 KB）
