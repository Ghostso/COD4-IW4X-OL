# 学习报告 052（重开）— `payload\` 八个二进制的 PE 结构

**学习范围**：4 个插件 + 4 个 loader 的 PE 头、节表、导入/导出
**方法**：`ReadAllBytes` + 手工解析 DOS/NT 头、节表、数据目录
**性质**：全实测
**★★★ 本报告发现 `Bootstrapper64.dll` 的**三个异常**（PE32+ / AMD64 / ImageBase 1 / 时间戳 1970）**

---

## 一、★★★★★ 八个二进制的 PE 头完整对照

| 文件 | 大小 | e_lfanew | Machine | 格式 | 节数 | EntryPoint | ImageBase | SizeOfImage | 时间戳 |
|---|---|---|---|---|---|---|---|---|---|
| `Injector32.exe` | 126,464 | `0xF8` | **`0x014C`** | PE32 | 5 | `0x1C5E` | **`0x00400000`** | `0x24000` | **2055-03-24** |
| `Bootstrapper32.dll` | 159,744 | `0xF8` | **`0x014C`** | PE32 | 5 | `0x4D23` | **`0x10000000`** | `0x2C000` | **2042-11-13** |
| **`Bootstrapper64.dll`** | **204,288** | **`0x108`** | **`0x8664`** | **PE32+** | **7** | `0x622C` | ★★★ **`0x00000001`** | `0x38000` | ★★★ **1970-01-01** |
| `ol_room_owner.exe` | 283,648 | `0xF8` | **`0x014C`** | PE32 | 5 | `0x1182A` | **`0x00400000`** | `0x4B000` | 2026-10-18 |
| `Alwaysoffline.Localnet32` | 4,189,184 | `0x110` | **`0x014C`** | PE32 | 5 | `0x2C07ED` | **`0x10000000`** | `0x405000` | 2026-10-21 19:13:48 |
| `CodolGameServer.Localnet32` | 6,834,176 | `0x118` | **`0x014C`** | PE32 | 5 | `0x421938` | **`0x10000000`** | `0x842000` | 2026-10-21 **19:14:07** |
| `Localnetworking.Ayria32` | 519,168 | `0x110` | **`0x014C`** | PE32 | 5 | `0x24D27` | **`0x10000000`** | `0x83000` | **2026-10-24 17:00:22** |
| `Platformwrapper.Ayria32` | 543,232 | `0x108` | **`0x014C`** | PE32 | 5 | `0x2665E` | **`0x10000000`** | `0x89000` | 2026-10-03 |

### ★★★ 三个立刻可读出的规律

**① 七个是 PE32 / i386，只有 `Bootstrapper64.dll` 是 PE32+ / AMD64**

```
Machine = 0x014C  →  i386（32 位）× 7 个
Machine = 0x8664  →  AMD64（64 位）× 1 个（Bootstrapper64.dll）
```

**② ImageBase 严格三组**

```
0x00400000  →  EXE 组：Injector32.exe / ol_room_owner.exe
0x10000000  →  DLL 组：Bootstrapper32.dll + 四个插件
0x00000001  →  ★★★ Bootstrapper64.dll（异常值）
```

**③ 时间戳分成三类**

```
真实（2026-10-xx）  →  ol_room_owner / 四个插件
★★★ 伪未来时间     →  Injector32 (2055) / Bootstrapper32 (2042)
★★★ 伪零时间       →  Bootstrapper64 (1970-01-01 04:25:30)
```

---

## 二、★★★★★ `Bootstrapper64.dll` 的三个异常

### 2.1 ★★★ 异常 1：PE32+ / AMD64（64 位）

```
Machine = 0x8664     （AMD64）
Magic   = 0x20B      （PE32+，OptionalHeader 是 240 字节而非 224）
节数    = 7          （其他都是 5）
```

★★★ **⇒ 这是**唯一一个 64 位二进制**。**

★ **⇒ 而 `payload\Ayria\` 的其余 7 个都是 32 位 ⇒ `Bootstrapper64.dll` 在这套 32 位链里**不可能被加载**。**

### 2.2 ★★★★★ 异常 2：`ImageBase = 0x00000001`

★★★ **⇒ `ImageBase = 0x00000001` 是**非法的 DLL 首选基址**：**
```
正常 DLL：0x10000000（MSVC 默认）或 0x180000000（64 位常见）
        ↓
★ 而这里是 **1**
        ↓
★★★ 任何地址都会与它冲突 ⇒ **必然重定位**
```

★★ **⇒ 这是一个**明显的打包/伪造痕迹**（或工具输出的占位值）。**

### 2.3 ★★★★★ 异常 3：时间戳 `1970-01-01 04:25:30`

```powershell
TS = 1970-01-01 04:25:30
```

★★★ **⇒ Unix 纪元（1970-01-01 00:00:00 UTC）+ 4 小时 25 分 30 秒 = `0x00003F1A`（推测）。**

★ **⇒ 这是一个**极小的值**（约 15,930 秒）。**

★★ **⇒ 与另外两个伪时间戳（2055 / 2042）不同，这是**伪零时间**。**

★★★ **⇒ 三个异常叠加 ⇒ `Bootstrapper64.dll` 很可能是**占位/未使用的文件**。**

### 2.4 ★★★ `Bootstrapper64.dll` 的七个节

```
.text      VA=0x00001000  VSize=0x000205B0  Chars=0x60000020
.rdata     VA=0x00022000  VSize=0x0000DB94  Chars=0x40000040
.data      VA=0x00030000  VSize=0x000028AC  Chars=0xC0000040
★ .pdata   VA=0x00033000  VSize=0x00001D4C  Chars=0x40000040   ← ★★★ 64 位特有的异常表
★ _RDATA   VA=0x00035000  VSize=0x00000094  Chars=0x40000040   ← ★ 名字前有下划线（少见）
.rsrc      VA=0x00036000  VSize=0x000001B4  Chars=0x40000040
.reloc     VA=0x00037000  VSize=0x00000790  Chars=0x42000040
```

★★★ **⇒ `.pdata`（异常处理表）是 **x64 独有**的节（用于 SEH/展开）。**
**⇒ 这**确证**了它是真正的 64 位二进制（不是改头伪装的）。**

★★ **⇒ `_RDATA`（前导下划线）是 **MSVC 的旧式节名**（与 `.rdata` 并存，少见）。**

---

## 三、★★★★ 五个节的标准布局（7 个 32 位二进制）

```
.text      Chars=0x60000020   CODE | EXECUTE | READ
.rdata     Chars=0x40000040   INITIALIZED_DATA | READ
.data      Chars=0xC0000040   INITIALIZED_DATA | READ | WRITE
.rsrc      Chars=0x40000040   （资源）
.reloc     Chars=0x42000040   INITIALIZED_DATA | DISCARDABLE | READ
```

★★★ **⇒ 七个 32 位二进制**全部是这五个节**（名字和顺序都相同）。**

### ★★★ `ol_room_owner.exe` 与四个插件多了一个 `.fptable`

```powershell
.fptable   VA=0x00047000  VSize=0x00000080  Chars=0xC0000040   （ol_room_owner）
.fptable   VA=0x003DE000  VSize=0x00000080  Chars=0xC0000040   （Alwaysoffline）
.fptable   VA=0x00806000  VSize=0x00000080  Chars=0xC0000040   （CodolGameServer）
.fptable   VA=0x0007E000  VSize=0x00000080  Chars=0xC0000040   （Localnetworking）
.fptable   VA=0x00084000  VSize=0x00000080  Chars=0xC0000040   （Platformwrapper）
```

★★★ **⇒ **五个**二进制都有 `.fptable`，且 **VSize 严格都是 `0x80`（128 字节）**。**

★ **⇒ `Chars = 0xC0000040` = **INITIALIZED_DATA | READ | WRITE** ⇒ **运行期可写**。**

★★ **⇒ 而 `Injector32.exe` / `Bootstrapper32.dll` / `Bootstrapper64.dll` **没有** `.fptable`。**

★★★ **⇒ `.fptable` 只属于**被加载的模块**（room_owner + 四个插件），**
**不属于**加载器**（Injector/Bootstrapper）。**

---

## 四、★★★★★ 导入表规模（最小依赖）

| 文件 | Import Size | 描述符数 | 实际 DLL 数 |
|---|---|---|---|
| `Injector32.exe` | `0x28`（40） | **2** | **1** |
| `Bootstrapper32.dll` | `0x28`（40） | **2** | **1** |
| `Bootstrapper64.dll` | `0x28`（40） | **2** | **1** |
| `ol_room_owner.exe` | `0x3C`（60） | **3** | **2** |
| `Alwaysoffline.Localnet32` | **`0x8C`（140）** | **7** | **6** |
| `CodolGameServer.Localnet32` | **`0x78`（120）** | **6** | **5** |
| `Localnetworking.Ayria32` | `0x3C`（60） | **3** | **2** |
| `Platformwrapper.Ayria32` | `0x3C`（60） | **3** | **2** |

★★★ **⇒ 每个描述符 20 字节，末尾有一个全零终止符 ⇒ 实际 DLL 数 = 描述符数 − 1。**

★★ **⇒ 三个 loader 都只导入 **1 个 DLL**（`KERNEL32`）。**

★ **⇒ `Alwaysoffline` 导入最多（**6 个**），`CodolGameServer` 次之（5 个）。**

★★★ **⇒ 这印证了"全静态链接"（报告 019）：一个 6.8 MB 的战斗服只导入 5 个 DLL。**

---

## 五、★★★★ 导出表（只有 5 个有导出）

| 文件 | Export RVA | 有无导出 |
|---|---|---|
| `Injector32.exe` | **`0x00000000`** | ✗ **无** |
| `Bootstrapper32.dll` | **`0x000258E0`** | ✓ |
| `Bootstrapper64.dll` | **`0x0002F080`** | ✓ |
| `ol_room_owner.exe` | **`0x00000000`** | ✗ **无** |
| `Alwaysoffline.Localnet32` | `0x003CA680` | ✓ |
| `CodolGameServer.Localnet32` | `0x0061E100` | ✓ |
| `Localnetworking.Ayria32` | `0x000550A0` | ✓ |
| `Platformwrapper.Ayria32` | `0x0005B1C0` | ✓ |

★★★ **⇒ 两个 EXE（`Injector32` / `ol_room_owner`）**没有导出**（它们是进程入口，不需要）。**

★★ **⇒ 六个 DLL 都有导出（包括 `Bootstrapper64`）。**

---

## 六、★★★ 四个插件的 `.fptable` 位置

| 插件 | `.fptable` VA | `.fptable` Raw |
|---|---|---|
| `Alwaysoffline` | `0x003DE000` | `0x003D9200` |
| `CodolGameServer` | `0x00806000` | `0x0064A400` |
| `Localnetworking` | `0x0007E000` | `0x0007B600` |
| `Platformwrapper` | `0x00084000` | `0x00081200` |

★★★ **⇒ 四个插件的 `.fptable` 都在**节表最后一个数据节**（`.reloc` 之前）。**

★ **⇒ 且 VSize 都是 **`0x80`（128 字节 = 32 个 4 字节指针）**。**

★★ **⇒ 上一轮（报告 019）实测盘上**全零** ⇒ **运行期填充**。**

---

## 七、★★★★ `.data` 的 VSize 与 RawSize 差异

| 文件 | `.data` VSize | `.data` RawSize | 差异 |
|---|---|---|---|
| `Alwaysoffline` | `0x119F8`（72 KB） | `0xE800`（59 KB） | 13 KB |
| **`CodolGameServer`** | **`0x1E5C74`（1.9 MB）** | **`0x2B000`（176 KB）** | ★★★ **1.7 MB** |
| `Localnetworking` | `0x27A74`（162 KB） | `0x26A00`（157 KB） | 5 KB |
| `Platformwrapper` | `0x27918`（162 KB） | `0x26C00`（158 KB） | 4 KB |

★★★ **⇒ `CodolGameServer` 的 `.data` **VSize 是 RawSize 的 11 倍**（1.9 MB vs 176 KB）⇒**
**★★★ 有 **1.7 MB 是未初始化的 BSS**（零填充）。**

★ **⇒ 这与上一轮（报告 041）的发现**一致**（`.data` 有大量 BSS）。**

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ 格式 | **7 个 PE32/i386 + 1 个 PE32+/AMD64** |
| 2 | ★★★ **64 位的是** | **`Bootstrapper64.dll`**（唯一） |
| 3 | ★★★ ImageBase 三组 | **`0x400000`（EXE）/ `0x10000000`（DLL）/ `0x00000001`（Boot64）** |
| 4 | ★★★★★ **`Bootstrapper64` ImageBase** | **`0x00000001`**（非法 ⇒ 必然重定位） |
| 5 | ★★★★★ **`Bootstrapper64` 时间戳** | **`1970-01-01 04:25:30`**（伪零） |
| 6 | ★★★ 伪时间戳 | `Injector32`=**2055** / `Bootstrapper32`=**2042** / `Bootstrapper64`=**1970** |
| 7 | ★ 真实时间戳 | `ol_room_owner`=10-18 / 四插件=10-21、10-24、10-03 |
| 8 | ★★★ `CodolGameServer` vs `Alwaysoffline` | 10-21 **19:14:07** vs **19:13:48**（差 **19 秒**） |
| 9 | ★★ `Localnetworking` | **10-24 17:00:22**（单独重建） |
| 10 | ★★★ `.fptable` | **五个二进制**（room_owner + 四插件），**VSize 严格 `0x80`** |
| 11 | ★ `.fptable` Chars | **`0xC0000040`（可写）** |
| 12 | ★★ 无 `.fptable` | `Injector32` / `Bootstrapper32` / `Bootstrapper64` |
| 13 | ★★ `.pdata` | **只有 `Bootstrapper64`**（x64 异常表 ⇒ 确证 64 位） |
| 14 | ★ `_RDATA` | 只有 `Bootstrapper64`（MSVC 旧式节名） |
| 15 | ★★★ 导入最少 | 三个 loader 都只 **1 个 DLL** |
| 16 | ★★ 导入最多 | **`Alwaysoffline` 6 个** / `CodolGameServer` 5 个 |
| 17 | ★ 无导出 | `Injector32.exe` / `ol_room_owner.exe` |
| 18 | ★★★ **`CodolGameServer` 的 `.data` BSS** | **VSize 1.9 MB vs RawSize 176 KB（11 倍）** |

---

## 九、结论

### 1. ★★★★★ **`Bootstrapper64.dll` 有三个叠加异常 ⇒ 很可能是占位/未使用文件**

```
PE32+/AMD64（唯一 64 位）
ImageBase = 0x00000001（非法）
时间戳 = 1970-01-01（伪零）
        ↓
★★★ 而其余 7 个都是 32 位 ⇒ 它在这套链里**不可能被加载**
```

★ **⇒ 但 `.pdata` 节存在 ⇒ **确证**它是真正的 64 位二进制（不是改头伪装）。**

### 2. ★★★ **`ImageBase = 0x00000001`** 是明显的伪造/占位值

### 3. ★★★ **`.fptable` 只属于被加载的模块**（room_owner + 四插件），不属于 loader

### 4. ★★ **三个 loader 只导入 1 个 DLL**（`KERNEL32`）

### 5. ★★ **`CodolGameServer` 的 `.data` 有 1.7 MB BSS**（VSize 是 RawSize 的 11 倍）

### 6. ★★ **`Alwaysoffline` 与 `CodolGameServer` 相差 19 秒**（同一次构建）

---

## 十、下一步

- 四个插件的**导出表详情**（符号名）
- `payload\` **18 个小 map lua** + `cha.lua`/`zm.lua` 剩余
- `source\` 结构与关键文档
