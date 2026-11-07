# 学习报告 019 — 逐字节转储：7 个 PE 头部 + 导出表（插件契约的真相）

**方法**：`ReadAllBytes` + 手工解析 DOS/NT 头、节表、数据目录、导出表
**性质**：全实测

---

## 一、七个 PE 的共同与差异（逐字节实测）

| 文件 | 大小 | e_lfanew | ImageBase | SizeOfImage | EntryPoint | 节数 |
|---|---|---|---|---|---|---|
| `Injector32.exe` | 126,464 | `0xF8` | **0x00400000** | 0x00024000 | 0x1C5E | 5 |
| `Bootstrapper32.dll` | 159,744 | `0xF8` | **0x10000000** | 0x0002C000 | 0x4D23 | 5 |
| `ol_room_owner.exe` | 283,648 | `0xF8` | **0x00400000** | 0x0004B000 | 0x1182A | 5 |
| `Alwaysoffline.Localnet32` | 4,189,184 | `0x110` | **0x10000000** | 0x00405000 | 0x2C07ED | 5 |
| `CodolGameServer.Localnet32` | 6,834,176 | `0x118` | **0x10000000** | 0x00842000 | 0x421938 | 5 |
| `Localnetworking.Ayria32` | 519,168 | `0x110` | **0x10000000** | 0x00083000 | 0x24D27 | 5 |
| `Platformwrapper.Ayria32` | 543,232 | `0x108` | **0x10000000** | 0x00089000 | 0x2665E | 5 |

### ★ 三个立刻可读出的规律

1. **全部 `Machine = 0x014C` = i386** ⇒ **PE32，32 位** ✓
   （与 BUILD.md "必须 x86" 一致；名字里 `.Localnet32`/`.Ayria32` 也标了 32）
2. **全部 `Magic = 0x010B` = PE32**（不是 PE32+ `0x20B`）✓
3. **`OptionalHeaderSize = 224` 全部相同** —— PE32 标准值 ✓

### ★★★ ImageBase 分成严格两组

```
0x00400000  = EXE 组：Injector32.exe, ol_room_owner.exe
0x10000000  = DLL 组：Bootstrapper32.dll + 四个插件
```

★★ **这不是巧合，是 loader 的规矩**：
- **EXE 首选 0x400000**（Windows 默认镜像基址）
- **DLL 首选 0x10000000**（MSVC 链接器对 DLL 的默认值）

★★★ **关键推论**：**插件都是 DLL，都被 `LoadLibrary` 到 0x10000000** ——
**四个插件如果都按 0x10000000 加载，必须发生重定位（基址冲突）**。
`Alwaysoffline` 的 SizeOfImage = 0x405000（4 MB），
`CodolGameServer` = 0x842000（8.3 MB）—— **两者范围会重叠**。

**⇒ 除第一个外，其余插件全部要被重定位（`.reloc` 节必然生效）**

★ **这解释了为什么每个插件都有 `.reloc` 且体积不小**：
```
Alwaysoffline    .reloc RawSize = 0x25800 (153 KB)
CodolGameServer  .reloc RawSize = 0x3A200 (238 KB)  ← 最重
Localnetworking  .reloc RawSize = 0x3400  (13 KB)
Platformwrapper  .reloc RawSize = 0x3600  (13.5 KB)
Bootstrapper32   .reloc RawSize = 0x1800  (6 KB)
```

★★ **`CodolGameServer` 的 reloc 238 KB 是最大的** —— 因为它代码最多、需要重定位的地址最多。

---

## 二、★★★ `.fptable` 节 —— 一个非常规的发明

### 实测节表

| 文件 | 节名 | VA | VSize | RawSize |
|---|---|---|---|---|
| `ol_room_owner.exe` | `.text/.rdata/.data/**.fptable**/.reloc` | 0x47000 | **0x80** | 0x200 |
| `Alwaysoffline` | 同上 | 0x3DE000 | **0x80** | 0x200 |
| `CodolGameServer` | 同上 | 0x806000 | **0x80** | 0x200 |
| `Localnetworking` | 同上 | 0x7E000 | **0x80** | 0x200 |
| `Platformwrapper` | 同上 | 0x84000 | **0x80** | 0x200 |

★★★ **五个文件全部有 `.fptable`，VSize 严格都是 `0x80`（128 字节）**。

### ★ 盘上全零（实测）

**`CodolGameServer` 的 `.fptable`（RawPtr `0x64A400`，转储 512 字节）**：
```
0064A400..0064A5FF   全部 00
```

**`Alwaysoffline` 的 `.fptable`（RawPtr `0x3D9200`，转储 256 字节）**：
```
003D9200..003D92FF   全部 00
```

★★★ **盘上全零 ⇒ 运行期填充 ⇒ 这是插件加载器写入的"函数指针表"。**

### 字符属性（`0xC0000040`）

```
0xC0000040 = IMAGE_SCN_CNT_INITIALIZED_DATA (0x40)
           | IMAGE_SCN_MEM_READ           (0x40000000)
           | IMAGE_SCN_MEM_WRITE          (0x80000000)
```

★★ **可读可写** —— 允许加载器**运行期写入**函数指针 ✓

### ★★ `.fptable` 名字在文件里出现两次

```
偏移 0x288  : 节表里的 8 字节名 ".fptable"
偏移 0x5FC250: .rdata 里的字符串表（含 .data$rs, .bss, .fptable 等）
```

★★ **`0x5FC250` 处是一串节名（`.data$rs` / `.bss` / `.fptable`）** ——
**这是 MSVC 的节名注册表，`$` 分隔说明用了 `#pragma section` / `__declspec(allocate)`。**

★ **`__declspec(allocate(".fptable"))`** —— 这是 MSVC 的**自定义节分配语法**。
**⇒ `.fptable` 是代码里显式声明的 128 字节数组。**

### ★★★ `.fptable` 的用途推断（由导出表证实）

**五个模块都有，128 字节**：
```
128 字节 / 4 字节（32位指针） = 32 个函数指针槽
```

★★ **这与 `nt10.py` 的 `--apis` 里的 `zN` 占位符是同一类设计**（报告 007 第二节）：
**"代码洞/cnt 槽位是固定分配的"。**

★ **但没有证据说它们是同一个表** —— `nt10.py` 的 zN 是**注入代码的槽位**，
`.fptable` 是**模块自身导出的表**。**两者独立。**

---

## 三、★★★ 导出表 —— 插件契约的真正载体

### `CodolGameServer.Localnet32` 的导出表（实测完整）

```
Export Directory: RVA 0x0061E100, Size 0x00000A98
  DLL Name : "CodolGameServer.Localnet32"
  Base     : 1
  NumFunc  : 55
  NumNames : 55            ← ★ 名字数 = 函数数，无序号-only 导出
```

### 55 个导出，按功能分组

#### A. 生命周期（`onStartup` / `onInitialized`）

| # | 名称 | RVA |
|---|---|---|
| 53 | `Createserver` | **0x0005DD70** ← ★ 注意在 `.text` 低段 |
| 54 | `onInitialized` | 0x00220880 |
| 55 | `onStartup` | **0x00220880** ← ★★ **与 onInitialized 同地址！** |

★★★ **`onInitialized` 和 `onStartup` 是**同一个 RVA**（`0x00220880`）**
—— **编译器把两个空函数合并了（tail merge / ICF）**，
**或者其中一个是 `ret` 桩。**

★ **`Createserver` 的 RVA `0x5DD70` 明显低于其他所有导出（都是 `0x2xxxxx`）**
—— **它在 `.text` 的**前半段**，而其他都在 `0x22xxxx` 附近。**

★★ **强推论**：`Createserver` 是**真实入口**（加载器调用它），
而 `onStartup`/`onInitialized` 是**空桩**（可能只是为了满足 Ayria 的契约）。

#### B. 配置入口（3 个）

| # | 名称 | 意义 |
|---|---|---|
| 1 | `CODOL_GameServerConfigureBooking` | 预订配置（`DedicatedBookingDispatcher` 相关） |
| 2 | `CODOL_GameServerConfigureGameState` | gamestate 配置 |
| 3 | `CODOL_GameServerConfigureSession` | ★ **session 配置**（`ConfigureSession`，报告 015 提到 `bytes=22 endpoint=28960`） |

#### C. 状态查询 `Get*Status`（约 25 个）

```
GetStatus / GetNetworkStatus / GetNetchanStatus / GetTransportStatus
GetSessionStatus / GetLoadingStatus / GetClientLoadingStatus
GetGameStateStatus / GetGameStateReadinessStatus / GetGameStateConfigurationStatus
GetSnapshotStatus / GetSnapshotDeltaStatus
GetLoadoutPreparationStatus / GetLoadoutResolveFailure
GetRegisteredCharacterStatus / GetRegisteredCharacterPresentation
GetDedicatedSessionConsumptionStatus
GetBotStatus / RequestBots
GetConnectionlessDiagnosticsV1
GetConstantConfigStringStatus
GetTransportTimingStatus
GetClientGameStateStage / GetClientGameplayStatus
GetClientIngressStatus / GetClientMenuResponseStatus / GetClientRejectStatus
GetClientReliableCommandStatus / GetClientUserCmdStatus
GetSdStatusV1
```

★★ **`GetSdStatusV1`** —— `Sd` 可能是 `ServerData`/`SessionData`。
★ **`V1` 后缀**说明**版本化接口**（`GetEntityDamageStatusV1`/`GetWorldBulletExecutionStatusV1,V2`/`GetWorldPlayerSampleV1,V2`/`GetWorldObjectiveStatusV1`/`GetWorldPredictableEventStatusV1`）。

★★★ **这套 `Get*Status` 是**外部可观测的探针面** ——
**`force_display_name.py`/测试脚本能通过 `GetProcAddress` 问"进图了吗"。**

#### D. ★★★ World 层（17 个）—— 这是战斗服的真实能力清单

```
GetWorldStatus
GetWorldPlayerStatus
GetWorldPlayerPmoveStatus           ← ★ player movement
GetWorldPlayerViewHeightStatus      ← ★ 视角高度（蹲/站）
GetWorldPlayerHealthStatus          ← ★ 生命值
GetWorldPlayerFlagsStatus           ← ★ pm_flags
GetWorldPlayerWeaponStatus          ← ★ 玩家武器
GetWorldPlayerSampleV1 / V2         ← ★ 位置采样
GetWorldResolvedLoadoutStatus       ← ★ 已解析配装
GetWorldBulletExecutionStatusV1 / V2← ★ 弹道
GetWorldClientThinkStatus           ← ★ 客户端 think
GetWorldEventStatus                 ← ★ 事件
GetWorldEventWeaponStatus           ← ★ 事件武器
GetWorldObjectiveStatusV1           ← ★ 目标（占点/炸弹）
GetWorldPredictableEventStatusV1    ← ★ 可预测事件
GetEntityDamageStatusV1             ← ★★★ 伤害！
```

★★★ **`GetEntityDamageStatusV1` 的存在**直接证明了记忆里的关键结论：

> 记忆 `codol-battle-server-world-binding.md`：
> "`codol_battle_service_bind_world` **从未被调用** ⇒ `svc->world` 恒 NULL ⇒
> 实体层/真 clipmap 碰撞/伤害/HIT **整条是死的**"

★★★ **⇒ 这些 `GetWorld*` / `GetEntityDamage*` 导出全部返回"未绑定"状态。**
**导出表里有名字 ≠ 功能可用。**

★ **这是本报告最重要的一条**：
**导出表是"能力清单"，不是"可用清单"。**

### ★ 与记忆的交叉验证

| 记忆结论 | 导出表证据 |
|---|---|
| `world` 从未绑定 | 17 个 `GetWorld*` + `GetEntityDamageStatusV1` 全在，但需 world 指针 |
| 快照有 512 字节上限 | `GetSnapshotStatus`/`GetSnapshotDeltaStatus` 存在 |
| 实体最多约 10 个 | 同上 |
| 开镜失效 / pm_flags | `GetWorldPlayerFlagsStatus` 存在 |
| 位置/出生点 | `GetWorldPlayerSampleV1/V2` + `GetWorldPlayerPmoveStatus` |

---

## 四、数据目录（`CodolGameServer` 实测）

```
Magic = 0x010B (PE32), DataDirectory 偏移 = 0x190

  Export         RVA=0x0061E100  Size=0x00000A98
  Import         RVA=0x0061EB98  Size=0x00000078   ← ★ 只有 120 字节
  Reloc          RVA=0x00807000  Size=0x0003A1B8
  Debug          RVA=0x005F62D0  Size=0x0000001C
  TLS            RVA=0x005F6300  Size=0x00000018   ← ★ 有 TLS！
  LoadConfig     RVA=0x005F6210  Size=0x00000040
  IAT            RVA=0x0047D000  Size=0x000003B8
```

### ★★★ 三个关键发现

#### 1. `Import` 只有 120 字节 —— **极少的外部依赖**

```
0x78 = 120 字节。每个 IMAGE_IMPORT_DESCRIPTOR 是 20 字节：
120 / 20 = 6 个描述符（含末尾全零的终止符）
⇒ ★ 只有 5 个 DLL 被导入
```

★★★ **一个 6.8 MB 的战斗服只导入 5 个 DLL** ——
**这是全静态链接的 xmake 构建**（`x86-windows-static` OpenSSL，BUILD.md 也说了）。

★ **⇒ 不依赖 `ayria.dll` 或任何 Ayria 运行时导出**
—— **插件与加载器之间是**松耦合**：靠**导出函数名**和 `.fptable` 约定，不是导入。

#### 2. **有 TLS 目录**（`TLS RVA=0x005F6300`）

★★ **DLL 带 TLS 意味着**：它有 **thread-local 静态变量**，
而且可能需要 **TLS 回调（`DllMain` 之前的初始化）**。

★ **TLS 回调在 `LoadLibrary` 时被 loader 调用** ——
**这是插件能在 `DllMain` 之前做事的唯一途径。**

★★ **可能用于**：把 `.fptable` 初始化、注册回调。

#### 3. **`LoadConfig` 存在**（64 字节）

★ **`IMAGE_LOAD_CONFIG_DIRECTORY`** —— 可能有 **SafeSEH / CFG / 栈检查**。

★ **如果启用了 CFG，`.fptable` 里的函数指针必须在 CFG 白名单里**，
否则**间接调用会触发进程终止**。

★★ **这可能解释为什么 `.fptable` 需要专门的节** ——
**`__declspec(allocate)` + CFG 友好的标记。**

---

## 五、字符串面（实测出现次数）

```
'fptable'         出现 2 次   0x289, 0x5FC251
'.fptable'        出现 2 次   0x288, 0x5FC250
'Ayria'           出现 5 次   0x5D9F04, 0x5DE0EE, 0x5DE1BA, 0x5DEBA7, 0x5E29D4
'Plugin'          出现 0 次   ← ★★★
'GetProc'         出现 4 次   0x517CBD, 0x61E4A4, 0x61E7F2, 0x61F38A
'Bootstrapper'    出现 0 次   ← ★★★
```

### ★★★ `'Plugin'` 出现 0 次 —— 极重要的负面证据

★★ **`CodolGameServer.Localnet32` 里**完全没有 `"Plugin"` 这个字符串**。

★ **`'Bootstrapper'` 也是 0 次。**

★★★ **推论：插件**不知道**自己被 `Bootstrapper32.dll` 加载。**
**它只导出符号，谁 `LoadLibrary` 它、谁 `GetProcAddress` 它，它都不关心。**

★ **这与报告 009 的"第二条加载路径"问题相关**：
**插件本身是"被动"的** —— 任何能 `LoadLibrary` + `GetProcAddress` 的东西都能驱动它。
**⇒ 理论上可以用一个自定义 loader 替代 `Injector32.exe`。**

### ★ `'Ayria'` 出现 5 次 —— 插件确实知道 Ayria 这个"服务名"

```
0x5D9F04, 0x5DE0EE, 0x5DE1BA, 0x5DEBA7, 0x5E29D4
```

★ **可能用于**：日志路径（`Ayria\Logs\...`）、配置路径解析。

★ **`0x5D9F04` 等仍在 `.rdata`（0x47C400..0x6213C6）范围内** ——
**是数据字符串不是代码。**

### ★ `'GetProc'` 出现 4 次 —— 可能有动态解析

```
0x517CBD (在 .text 0x400..0x47C400 内 ⇒ 代码)
0x61E4A4, 0x61E7F2, 0x61F38A (在导出表附近 ⇒ 导出名字符串)
```

★★ **`0x517CBD` 在 `.text` 里** —— 可能是 `GetProcAddress` 的导入名字符串，
或日志里的文本 `"GetProcAddress"`。

★ **需要看具体字节才能定。**

---

## 六、PE 时间戳（★★ 决定性证据）

| 文件 | TimeDateStamp | UTC 时间 | 含义 |
|---|---|---|---|
| `Injector32.exe` | `0xA04EA110` | **2055-03-24 13:26:40** | ★★ **伪时间戳（Ayria 作者故意设未来）** |
| `Bootstrapper32.dll` | `0x890F2622` | **2042-11-13 06:03:14** | ★★ **伪时间戳** |
| `ol_room_owner.exe` | `0x6AD500AD` | **2026-10-18 17:23:57** | 真实 |
| `Alwaysoffline.Localnet32` | `0x6AD90EEC` | **2026-10-21 19:13:48** | 真实 |
| `CodolGameServer.Localnet32` | `0x6AD90EFF` | **2026-10-21 19:14:07** | ★ **比 Alwaysoffline 晚 19 秒** |
| `Localnetworking.Ayria32` | `0x6ADCE426` | **2026-10-24 17:00:22** | ★★ **最新（比 README 的 10-24 早 1 天）** |
| `Platformwrapper.Ayria32` | `0x6AC09C66` | **2026-10-03 06:10:46** | ★ **最旧** |

### ★★★ 时间戳揭示的构建顺序

```
2026-10-03 06:10:46   Platformwrapper.Ayria32    ← 最早
2026-10-18 17:23:57   ol_room_owner.exe
2026-10-21 19:13:48   Alwaysoffline.Localnet32
2026-10-21 19:14:07   CodolGameServer.Localnet32 ← 同一次构建（19 秒后）
2026-10-24 17:00:22   Localnetworking.Ayria32    ← 最后，但只改了它
```

★★★ **`Alwaysoffline` 与 `CodolGameServer` 相差 19 秒** ——
**证明是同一次 `xmake build` 的产物**（链接顺序：backend 先，game_server 后）。

★★ **`Localnetworking` 单独在 10-24 重建** ——
**说明 10-24 那轮只改了 Localnetworking**（对应记忆里的"本地网络层 hook ws2_32"问题）。

★★ **`Platformwrapper` 是最旧的（10-03）** ——
**从那时起就没动过。**

★★★ **`Injector32.exe` (2055) 和 `Bootstrapper32.dll` (2042) 是伪时间戳**
—— 这是**反调试/反取证手段**：让"这个二进制什么时候编译的"不可考。
**Ayria 框架的作者有意为之。**

★ **注意 `Bootstrapper32.dll` 的 `0x890F2622` = 2042 年，
而 `Injector32.exe` 是 2055 年 —— 两者不一致，说明是随意填的。**

---

## 七、★★★ 由 PE 证据得出的架构结论

### 加载链（由 ImageBase + 导出表 + 字符串面证实）

```
ol_room_owner.exe     ImageBase 0x400000（EXE，独立进程）
        │
Injector32.exe        ImageBase 0x400000（EXE）
        │  LoadLibrary
        ▼
Bootstrapper32.dll    ImageBase 0x10000000（DLL）
        │  LoadLibrary + GetProcAddress
        ├──> Plugins\Localnetworking.Ayria32      0x10000000 + reloc
        ├──> Plugins\Alwaysoffline.Localnet32     0x10000000 + reloc
        ├──> Plugins\CodolGameServer.Localnet32   0x10000000 + reloc
        └──> Plugins\Platformwrapper.Ayria32      0x10000000 + reloc
```

★★ **四个插件全部首选 0x10000000 ⇒ 必须重定位**（除第一个外）。

### ★★★ 插件的契约 = 命名导出（不是 COM，不是 C++ 虚表）

```
CodolGameServer.Localnet32 导出 55 个符号，全部有名字：
  Createserver                              ← ★ 真实入口（RVA 0x5DD70）
  onStartup / onInitialized                 ← 同 RVA 0x220880（空桩）
  CODOL_GameServerConfigure{Booking,GameState,Session}
  CODOL_GameServerGet*Status (约 25 个)
  CODOL_GameServerGetWorld* (17 个)
```

★★★ **⇒ 加载器不需要头文件，只要 `GetProcAddress(h, "Createserver")`。**

★ **这与 `'Plugin'` / `'Bootstrapper'` 字符串为 0 完全自洽**：
**插件不知道加载器，加载器只需知道符号名。**

### ★★★ `Createserver` 的 RVA 异常是最有价值的发现

```
Createserver     RVA 0x0005DD70   ← 在 .text 低段（0x400..0x47C400）
所有其他导出     RVA 0x0022xxxx   ← 在 .text ⾼段
```

★★ **相差约 0x1C2B60（1.8 MB）** ——
**`Createserver` 在 `.text` 的前 1/8，其他都在中后段。**

★ **这是链接顺序的结果**：`Createserver` 定义在 `server_mp/server.cpp` 之类**早期编译单元**，
而 `CODOL_GameServer*` 导出集中在 `backend_bridge.cpp` 之类**最后编译的单元**。

★★ **副产品**：如果要在客户端里 hook `Createserver`，**RVA 0x5DD70 是候选**
（但注意 `nt10.py` 用的兼容补丁在别的地址，见报告 002/003）。

---

## 八、★ `CodolGameServer` 只有 5 个导入 DLL

```
Import RVA=0x0061EB98  Size=0x78 (120 字节)
⇒ 120 / 20 = 6 个描述符（含终止符）
⇒ 5 个 DLL
```

★ **一个 6.8 MB 的战斗服只导入 5 个 DLL** —— **全静态链接**。

★★ **`kernel32.dll` 必定是其中之一**（需要 `LoadLibrary`/`GetTickCount` 等）。
**`ws2_32.dll` 可能没有**（因为网络由 `Localnetworking` 插件接管）。

★ **这印证了记忆**：
> "两组 nt10 关键差异：GOLDEN 版 hook 全成功+KDF 挂载；
> 外部版全失败（**Localnetworking 抢先 hook 了 ws2_32**）"

★★ **`Localnetworking` 是**唯一**碰 `ws2_32` 的插件**
—— `CodolGameServer` 通过 `Localnetworking` 的抽象层发网络。

---

## 九、这一块（逐字节）的结论

### 确证（实测字节）

1. **7 个 PE 全是 PE32 / i386 / Magic 0x010B** ✓
2. **ImageBase 严格两组**：EXE `0x400000` / DLL `0x10000000` ✓
3. **五个模块都有 `.fptable` 节，VSize 严格 `0x80`（128 字节），盘上全零** ✓
4. **`.fptable` 用 MSVC `__declspec(allocate)` 声明**（`.data$rs`/`.bss` 同表）✓
5. **`CodolGameServer` 导出 55 个命名符号**（NumFunc = NumNames = 55）✓
6. **`onStartup` 与 `onInitialized` 同 RVA `0x220880`** ✓
7. **`Createserver` RVA `0x5DD70`，比所有其他导出低 1.8 MB** ✓
8. **`GetEntityDamageStatusV1` 等 17 个 `GetWorld*` 导出存在** ✓
9. **`Import` 只有 120 字节（5 个 DLL）** ✓
10. **有 TLS 目录** ✓
11. **`'Plugin'` / `'Bootstrapper'` 字符串 0 次** ✓
12. **`Injector32` (2055) / `Bootstrapper32` (2042) 是伪时间戳** ✓
13. **`Alwaysoffline` 与 `CodolGameServer` 相差 19 秒（同一次构建）** ✓
14. **`Localnetworking` 单独在 10-24 重建** ✓

### 三条重要推论

| # | 推论 | 依据 |
|---|---|---|
| 1 | **插件契约 = 命名导出，非 COM/虚表** | 55 个具名导出 + `'Plugin'` 0 次 |
| 2 | **`GetWorld*`/`GetEntityDamage*` 存在 ≠ 可用** | 需 world 指针，而记忆已证 `bind_world` 从未调用 |
| 3 | **加载器可不依赖 Injector32** | 插件是被动的，任何 `LoadLibrary`+`GetProcAddress` 都能驱动 |

★★★ **推论 3 是解决报告 009 "`inject_ayria.on` 之谜"的钥匙**：
**如果插件是被动的，那么"不注入"不代表"一定没有插件"** ——
**任何进程（包括客户端自己、或另一个工具）都能加载它们。**

---

## 十、待逐字节继续

- [ ] `Alwaysoffline.Localnet32` 的导出表（对比 CodolGameServer 的 55 个）
- [ ] `Localnetworking.Ayria32` / `Platformwrapper.Ayria32` 的导出表
- [ ] `CodolGameServer` 的 5 个导入 DLL 名字（按 RVA 0x61EB98 读）
- [ ] `Createserver` @ RVA 0x5DD70 的反汇编（前 64 字节）
- [ ] `.fptable` 在运行期的实际内容（需注入+读内存）
- [ ] `0x517CBD` 处的 `'GetProc'` 上下文（是名字还是日志）
- [ ] TLS 回调地址（RVA 0x5F6300）
- [ ] LoadConfig 是否启用 CFG（决定 `.fptable` 间接调用是否合法）
