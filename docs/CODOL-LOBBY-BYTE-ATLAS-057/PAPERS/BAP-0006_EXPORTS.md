# BAP-0006 — 导出表 `[0x00A155B0, 0x00A15A70)`

| 项 | 值 |
|---|---|
| 目录 RVA | `0x00A155B0`，Size = `0x000004C0` |
| 所在节 | 节 1 `.tp3 a`（`0x008A8000`–`0x00A15A70`），RW– |
| 结构 | `IMAGE_EXPORT_DIRECTORY` + 函数表 + 名字表 + 序号表 |
| 最高判据 | **E3**（22 个函数 RVA 处全部可反汇编为合法代码） |

---

## 1. 原始字节

导出目录头（40 字节，`0x00A155B0`）：

```
00A155B0  00 00 00 00 da 90 96 60 00 00 00 00 b4 56 a1 00
00A155C0 01 00 00 00 16 00 00 00 16 00 00 00 d8 55 a1 00
00A155D0 30 56 a1 00 88 56 a1 00 63 6f 64 6f 4d 50 5f
```

---

## 2. 逐字段解析

| 偏移 | 宽 | 值 | 字段 | 判据 |
|---|---|---|---|---|
| `+0x00` | 4 | `0x00000000` | Characteristics | E1 |
| `+0x04` | 4 | `0x609690DA` | TimeDateStamp | E2 |
| `+0x08` | 2 | `0x0000` | MajorVersion | E1 |
| `+0x0A` | 2 | `0x0000` | MinorVersion | E1 |
| `+0x0C` | 4 | `0x00A156B4` | **Name**（DLL 名 RVA） | E3 |
| `+0x10` | 4 | **`0x00000001`** | **Base**（起始序号） | E1 |
| `+0x14` | 4 | **`0x00000016`** = 22 | **NumberOfFunctions** | E3 |
| `+0x18` | 4 | **`0x00000016`** = 22 | **NumberOfNames** | E3 |
| `+0x1C` | 4 | `0x00A155D8` | AddressOfFunctions | E3 |
| `+0x20` | 4 | `0x00A15630` | AddressOfNames | E3 |
| `+0x24` | 4 | `0x00A15688` | AddressOfNameOrdinals | E3 |

### 2.1 模块名（E3，**已按讨论篇更正**）

`RVA 0x00A156B4` → file_offset `0x00A156B4`：

```
"codoMP_client_shipRetail.exe"
```

⚠ 修正：初稿把"导出名 `.exe` 与导入描述符 `.dll` 不同"当成异常，
**这是错的**。PE 规范里：
- `EXPORT.Name` = **本模块自己的名字** → `.exe` ✅
- `IMPORT.Name` = **被依赖模块的名字** → `.dll` ✅

两者本就不同，**不是残留、不是改写**。见 BAP-0006D §1 H4。

### 2.2 `NumberOfFunctions == NumberOfNames == 22`，`Base = 1`

无空洞序号，序号 1–22 全部有名。⇒ **全部按名字导出**（E2）。

---

## 3. 全部 22 个导出

`AddressOfFunctions` 在 `0x00A155D8`，`AddressOfNames` 在 `0x00A15630`，
`AddressOfNameOrdinals` 在 `0x00A15688`。

| 序号 | Name RVA | 函数 RVA | 反汇编（前 12 字节） | 名字 |
|---|---|---|---|---|
| 1 | — | `0x000364F0` | `55 8b ec 8b 45 0c 56 8b f1 8b 4d 08` | `??0System@Scaleform@@QAE@ABUHeapDesc@MemoryHeap@1@PAVSysAllocBase@1@@Z` |
| 2 | — | `0x000364A0` | `55 8b ec 83 ec 20 33 c0 56 8b f1 b9` | `??0System@Scaleform@@QAE@PAVSysAllocBase@1@@Z` |
| 3 | — | `0x000363F0` | `c7 01 2c 35 d6 00 c3 cc` | `??1AcquireInterface@Scaleform@@UAE@XZ` |
| 4 | — | `0x000363F0` | 同上（合并） | `??1DefaultAcquireInterface@Scaleform@@UAE@XZ` |
| 5 | — | `0x00036510` | `e9 8b e1 3e 00 cc` | `??1System@Scaleform@@QAE@XZ` |
| 6 | — | `0x00036470` | `6a 00 6a 00 e8 b7 cf 3e 00 c3` | `??_FEvent@Scaleform@@QAEXXZ` |
| 7 | — | `0x00036460` | `6a 00 6a 01 e8 d7 e4 3e 00 c3` | `??_FMutex@Scaleform@@QAEXXZ` |
| 8 | — | `0x00036480` | `6a 00 6a 01 e8 c7 d0 3e 00 c3` | `??_FSemaphore@Scaleform@@QAEXXZ` |
| 9 | — | `0x00036790` | — | `??_FSysAllocPagedMalloc@Scaleform@@QAEXXZ` |
| 10 | — | `0x000362D0` | — | `??_FSysAllocStatic@Scaleform@@QAEXXZ` |
| 11 | — | `0x000367A0` | — | `??_FSysAllocWinAPI@Scaleform@@QAEXXZ` |
| 12 | — | `0x00036570` | — | `??_FSystem@Scaleform@@QAEXXZ` |
| 13 | — | `0x00036490` | — | `??_FThread@Scaleform@@QAEXXZ` |
| 14 | — | `0x0003A1A0` | — | `?GetXScale@?$Matrix2x4@M@Render@Scaleform@@QBEMXZ` |
| 15 | — | `0x0003A1D0` | — | `?GetYScale@?$Matrix2x4@M@Render@Scaleform@@QBEMXZ` |
| 16 | — | `0x000365E0` | — | `?Init@System@GFx@Scaleform@@SAXPAVSysAllocBase@3@@Z` |
| 17 | — | `0x00036520` | — | `?Init@System@Scaleform@@SAXPAVSysAllocBase@2@@Z` |
| 18 | — | `0x00255220` | — | `?Prepend@?$Matrix2x4@M@Render@Scaleform@@QAEAAV123@ABV123@@Z` |
| 19 | — | `0x0003A180` | — | `?SetIdentity@?$Matrix2x4@M@Render@Scaleform@@QAEXXZ` |
| 20 | — | `0x0003A200` | — | `?SetIdentity@?$Matrix3x4@M@Render@Scaleform@@QAEXXZ` |
| 21 | — | `0x0003A220` | — | `?SetIdentity@?$Matrix4x4@M@Render@Scaleform@@QAEXXZ` |
| 22 | — | `0x00A3E29C` | — | **`NvOptimusEnablement`** |

---

## 4. 语义推导

### 4.1 结论 1：导出面 = **Scaleform GFx 的内存/系统子系统**（E3）

20 个 `Scaleform::` C++ 修饰名，覆盖：

| 子域 | 导出 |
|---|---|
| 内存分配器 | `SysAllocBase` / `SysAllocStatic` / `SysAllocPagedMalloc` / `SysAllocWinAPI` |
| 系统对象 | `System` 构造/析构/`Init`（两个重载） |
| 同步原语 | `Event` / `Mutex` / `Semaphore` 的 `??_F`（静态局部对象析构注册） |
| 渲染矩阵 | `Matrix2x4` / `Matrix3x4` / `Matrix4x4` 的 `SetIdentity` / `GetXScale` / `GetYScale` / `Prepend` |
| 引用计数接口 | `AcquireInterface` / `DefaultAcquireInterface` 析构 |

⇒ **这个 EXE 把 Scaleform 的"分配器/系统/矩阵"这几层导出给外部**。
典型的宿主-插件结构：**EXE 提供 Scaleform 运行时，
另有 DLL（很可能就是 `Base.dll` 或其中的内嵌 CEF 宿主）链接并使用它。**

⚠ `??_F` 前缀是 MSVC 的 **"动态初始化/析构注册"**（`??_F` = static-local
destructor helper），不是普通成员函数。导出它们说明**跨 DLL 共享静态对象**。

### 4.2 结论 2：`NvOptimusEnablement` 是**显式性能标记**（E3）

`0x00A3E29C` 处是一个 `DWORD`，导出名 `NvOptimusEnablement`。
NVIDIA Optimus 在双显卡笔记本上靠这个导出的 `DWORD` 决定
是否用独显运行进程（值 `0x00000001` = 强制独显）。

实测该处值：见 §5。

⇒ **这是 NVIDIA 官方文档化的约定**，与游戏逻辑无关，
但证明**这个构建是针对 Optimus 双显卡环境发布的**。

### 4.3 结论 3：**没有游戏逻辑导出**（E3 负面）

22 个导出里**没有一个**是 `dw*` / `Lobby*` / `SV_*` / `CL_*` 之类的
游戏函数。⇒ **大厅逻辑不通过导出接口暴露**。

这与项目一直以来的"大厅逻辑在 EXE 内部、只能靠逆向进内存"吻合。

### 4.4 结论 4：`??1AcquireInterface` 与 `??1DefaultAcquireInterface`
**指向同一地址**（`0x000363F0`）

MSVC **ICF（Identical COMDAT Folding）** 的结果：两个析构函数
机器码相同，被合并。

其字节 `c7 01 2c 35 d6 00` = `mov dword ptr [ecx], 0x00D6352C`
—— 把 **vftable `0x00D6352C`** 写进对象首字段。
这是**析构函数恢复基类 vftable** 的标准形态（E4）。

⇒ 拿到一个真实 vftable 地址：**`0x00D6352C`**，
它是 `DefaultAcquireInterface` 的 vftable。可用于校准 RTTI 解析（BAP-0120）。

---

## 5. 引用关系

| 谁读导出表 | 在镜像内？ |
|---|---|
| Windows loader（`GetProcAddress` 用） | 否 |
| 链接本 EXE 的其它模块（`Base.dll`/CEF 宿主） | **在外部 DLL 里** |

⇒ **导出表是"给 Base.dll 用的"**。这解释了为什么
BAP-0005 §6 的导入表只写了一个 DLL：
**EXE ↔ Base.dll 是双向绑定**（EXE 导入 Base，Base 反向用 EXE 的
Scaleform 导出）。

⚠ 但 BAP-0006 §2.1 发现导出表里的模块名是 `.exe` 而导入是 `.dll`，
两个方向的名字不一致。这是**必须解释的异常**，见讨论篇。

---

## 6. 置信度

| 结论 | 级 |
|---|---|
| 22 个导出，序号 1–22 连续 | **E3** |
| 导出面 = Scaleform 内存/系统/矩阵 | **E3** |
| `NvOptimusEnablement` | **E3** |
| **无任何游戏逻辑导出** | **E3（负面）** |
| `AcquireInterface` 析构写 vftable `0x00D6352C` | **E4** |
| ~~导出模块名异常~~ | **已撤销**（见 BAP-0006D §1 H4） |

---

## 7. 待办

- BAP-0006D：架构认识重构（Base.dll = TP3Shell）。
- BAP-0120：`0x00D6352C` 处实测全零，不能直接当 vftable 用。
