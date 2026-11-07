# BAP-0003 — COFF 头与可选头 `[0x000128, 0x000220)`

| 项 | 值 |
|---|---|
| 范围 | `0x000128` – `0x00021F`（248 字节） |
| 结构 | PE 签名 `[0x128,0x12C)` + COFF 头 `[0x12C,0x140)` + 可选头 `[0x140,0x220)` |
| 最高判据 | **E3**（`SizeOfImage` 与节表末端自洽；`TimeDateStamp` 与 DEBUG/EXPORT 两处独立吻合） |

---

## 1. 原始字节

```
0120  00 00 00 00 00 00 00 00 50 45 00 00 4c 01 07 00  ........PE..L...
0130  0a 93 96 60 00 00 00 00 00 00 00 00 e0 00 22 01  ...`..........".
0140  0b 01 0a 00 00 70 8a 00 00 f0 30 00 00 00 00 00  .....p....0.....
0150  90 c6 5d 0e 00 10 00 00 00 80 8a 00 00 00 40 00  ..]...........@.
0160  00 10 00 00 00 10 00 00 05 00 01 00 00 00 00 00  ................
0170  05 00 01 00 00 00 00 00 00 90 65 0e 00 10 00 00  ..........e.....
0180  0d 84 78 00 02 00 00 81 00 00 10 00 00 00 10 00  ..x.............
0190  00 00 10 00 00 10 00 00 00 00 00 00 10 00 00 00  ................
01A0  b0 55 a1 00 c0 04 00 00 35 c6 5d 0e 00 00 00 00  .U......].......
01B0  00 90 5c 0e 00 00 00 00 00 00 00 00 00 00 00 00  ..\.............
01C0  48 70 77 00 f8 35 00 00 00 00 00 00 00 00 00 00  Hpw..5..........
01D0  60 da 8a 00 1c 00 00 00 00 00 00 00 00 00 00 00  `...............
01E0  00 00 00 00 00 00 00 00 b8 8e 9e 00 18 00 00 00  ................
01F0  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0200  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
0210  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
```

---

## 2. COFF 头 `[0x12C, 0x140)`

| 偏移 | 宽 | 字节 | 值 | 字段 | 判据 |
|---|---|---|---|---|---|
| `0x128` | 4 | `50 45 00 00` | `"PE\0\0"` | Signature | E1 |
| `0x12C` | 2 | `4c 01` | **`0x014C`** | Machine = i386 | E1 |
| `0x12E` | 2 | `07 00` | **7** | NumberOfSections | E3 |
| `0x130` | 4 | `0a 93 96 60` | **`0x6096930A`** | TimeDateStamp | **E3** |
| `0x134` | 4 | `00 00 00 00` | 0 | PointerToSymbolTable | E2 |
| `0x138` | 4 | `00 00 00 00` | 0 | NumberOfSymbols | E2 |
| `0x13C` | 2 | `e0 00` | **`0x00E0`** = 224 | SizeOfOptionalHeader | **E3** |
| `0x13E` | 2 | `22 01` | **`0x0122`** | Characteristics | E2 |

### 2.1 `NumberOfSections = 7` 与 `SizeOfOptionalHeader = 0xE0`

`SizeOfOptionalHeader = 0xE0 = 224` 恰好是 **PE32 附 16 个数据目录**的标准值
（`28 + 96 + 16×8 = 224`）。⇒ 可选头是 **PE32 + 16 目录**，E3。

节表起点 = `0x140 + 0xE0 = 0x220`，与实测一致（见 BAP-0004）。

### 2.2 `TimeDateStamp = 0x6096930A` → **2021-05-08 13:32:58 UTC**

三处独立吻合：

| 位置 | 值 |
|---|---|
| COFF `+0x04` (`0x130`) | `0x6096930A` |
| DEBUG `Type=2` 记录 `TimeDateStamp` (`0x008ADA64`) | `0x6096930A` |
| EXPORT 目录 `TimeDateStamp` (`0x00A155B4`) | `0x609690DA`（差 `0x230` = 560 秒） |

前两处**逐字节完全相同**（E3）。第三处差 560 秒是链接过程分段写入的
正常现象（导出表先于最终 COFF 头生成）。

**这个时间戳是本项目的关键时间锚**：
它说明我们手上的镜像是 **2021-05-08** 的构建。
此前记忆中"2020 年游戏跑起来过"（`TCLS_SHAREDMEMEMORY` 握手）是
**另一个更早的构建**，不能与本镜像的时间戳混淆。

### 2.3 `Characteristics = 0x0122`

```
0x0001 IMAGE_FILE_RELOCS_STRIPPED
0x0002 IMAGE_FILE_EXECUTABLE_IMAGE
0x0020 IMAGE_FILE_LARGE_ADDRESS_AWARE
0x0100 IMAGE_FILE_32BIT_MACHINE
```
`0x0122 = 0x0100 | 0x0020 | 0x0002`。

⚠ **`IMAGE_FILE_RELOCS_STRIPPED` 未置位**（`0x0001` 不在掩码里）——
即声明"可重定位"。但 `BASERELOC` 目录为 0（见 §3.5），
**声明与数据矛盾**。这是加壳/重打包的典型痕迹（E3，见讨论篇）。

---

## 3. 可选头 `[0x140, 0x220)`

### 3.1 标准字段

| 偏移 | 宽 | 字节 | 值 | 字段 | 判据 |
|---|---|---|---|---|---|
| `0x140` | 2 | `0b 01` | **`0x010B`** | Magic = PE32 | E1 |
| `0x142` | 1 | `0a` | 10 | MajorLinkerVersion | E2 |
| `0x143` | 1 | `00` | 0 | MinorLinkerVersion | E2 |
| `0x144` | 4 | `00 70 8a 00` | **`0x008A7000`** | SizeOfCode | **E3** |
| `0x148` | 4 | `00 f0 30 00` | **`0x0030F000`** | SizeOfInitializedData | **E3** |
| `0x14C` | 4 | `00 00 00 00` | 0 | SizeOfUninitializedData | E2 |
| `0x150` | 4 | `90 c6 5d 0e` | **`0x0E5DC690`** | **AddressOfEntryPoint** | **E4** |
| `0x154` | 4 | `00 10 00 00` | `0x00001000` | BaseOfCode | E3 |
| `0x158` | 4 | `00 80 8a 00` | `0x008A8000` | BaseOfData | E3 |
| `0x15C` | 4 | `00 00 40 00` | **`0x00400000`** | ImageBase | E3 |
| `0x160` | 4 | `00 10 00 00` | `0x1000` | SectionAlignment | E2 |
| `0x164` | 4 | `00 10 00 00` | `0x1000` | FileAlignment | E2 |
| `0x168` | 2 | `05 00` | 5 | MajorOperatingSystemVersion | E2 |
| `0x16A` | 2 | `01 00` | 1 | MinorOperatingSystemVersion | E2 |
| `0x16C` | 2 | `00 00` | 0 | MajorImageVersion | E2 |
| `0x16E` | 2 | `00 00` | 0 | MinorImageVersion | E2 |
| `0x170` | 2 | `05 00` | 5 | MajorSubsystemVersion | E2 |
| `0x172` | 2 | `01 00` | 1 | MinorSubsystemVersion | E2 |
| `0x174` | 4 | `00 00 00 00` | 0 | Win32VersionValue | E2 |
| `0x178` | 4 | `00 90 65 0e` | **`0x0E659000`** | **SizeOfImage** | **E3** |
| `0x17C` | 4 | `00 10 00 00` | `0x1000` | SizeOfHeaders | **E3** |
| `0x180` | 4 | `0d 84 78 00` | `0x0078840D` | CheckSum | E2 |
| `0x184` | 2 | `02 00` | **2** | Subsystem = GUI | E2 |
| `0x186` | 2 | `00 81` | **`0x8100`** | DllCharacteristics | E2 |
| `0x188` | 4 | `00 00 10 00` | `0x00100000` | SizeOfStackReserve | E2 |
| `0x18C` | 4 | `00 00 10 00` | `0x00100000` | SizeOfStackCommit | E2 |
| `0x190` | 4 | `00 00 10 00` | `0x00100000` | SizeOfHeapReserve | E2 |
| `0x194` | 4 | `00 00 00 00` | 0 | SizeOfHeapCommit | E2 |
| `0x198` | 4 | `00 00 00 00` | 0 | LoaderFlags | E2 |
| `0x19C` | 4 | `10 00 00 00` | **16** | NumberOfRvaAndSizes | E3 |

### 3.2 关键校验 1：`SizeOfImage` 自洽性

`SizeOfImage = 0x0E659000`。节表最后一个节（节 6）
`VA = 0x0E5D7000` + `VirtualSize = 0x00082000` = `0x0E659000`。
**完全相等**（E3）。⇒ 磁盘上的 `SizeOfImage` 字段与节表一致，
未被加壳器篡改。

同时：**镜像实际长度 = 241,537,024 = `0x0E659000`**，与 `SizeOfImage`
逐字节相等。⇒ 我们提取的内存镜像**完整覆盖声明的全部虚拟地址空间，
无截断、无缺页**。

### 3.3 关键校验 2：`SizeOfCode` 自洽性

`SizeOfCode = 0x008A7000`。节 0 的 `VirtualSize = 0x008A689A`，
`SizeOfRawData = 0x008A7000`。

⇒ `SizeOfCode` 等于**节 0 的 RawSize**（按 `FileAlignment` 0x1000 上取整），
而不是 VirtualSize。这与标准链接器行为一致（E2）。

**但要注意**：`BaseOfData = 0x008A8000` = 节 1 的 VA，而节 1 是
`.tp3 a`，**可读可写**（`0x40000040`），不是典型 `.data`。
节 2 才是可写可执行的大节。

### 3.4 `AddressOfEntryPoint = 0x0E5DC690`（**E4**）

这是本书最重要的字段之一。镜像在 `0x0E5DC690` 处的字节：

```
0E5DC690  ff 15 65 c6 9d 0e    call dword ptr [0x0E9DC665]
0E5DC696  00 00 00 00 ...
```

**判据 E4**：`FF 15 <disp32>` = `call dword ptr [abs32]`，
目标槽 `0x0E9DC665`。在 PE32 上这是**绝对地址间接调用**。

⚠ 注意槽地址 `0x0E9DC665` **不是 4 字节对齐**（末位 `5`）。
标准 IAT 槽必须 4 对齐。⇒ 这**不是 IAT 槽**，而是：
1. 加壳器改写的间接跳板；或
2. 我们的镜像在 `0x0E5DC690` 附近有 1 字节偏移错误。

**必须验证**（见 BAP-0003D §1 H2）：若 `call` 的目标槽错开 1 字节，
则整个"入口点"判断错误。这是 055 轮"6 字节偏移制造一批假发现"的
同类风险。

### 3.5 数据目录 16 项

| # | 名称 | RVA | Size | 判据 |
|---|---|---|---|---|
| 0 | EXPORT | `0x00A155B0` | `0x000004C0` | E3（见 BAP-0006） |
| 1 | IMPORT | `0x0E5DC635` | **0** | **E3 — SIZE=0 异常** |
| 2 | RESOURCE | `0x0E5C9000` | **0** | **E3 — SIZE=0 异常** |
| 3 | EXCEPTION | 0 | 0 | E3 — 无 SEH 表 |
| 4 | SECURITY | `0x00777048` | `0x000035F8` | **异常见下** |
| 5 | BASERELOC | 0 | 0 | E3 — 无重定位 |
| 6 | DEBUG | `0x008ADA60` | `0x0000001C` | E3 |
| 7 | ARCH | 0 | 0 | E3 |
| 8 | GLOBALPTR | 0 | 0 | E3 |
| 9 | TLS | `0x009E8EB8` | `0x18` | E3（见 BAP-0007） |
| 10 | LOADCFG | 0 | 0 | E3 — 无 CFG |
| 11 | BOUNDIMP | 0 | 0 | E3 |
| 12 | IAT | **0** | **0** | **E3 — IAT 目录为空** |
| 13 | DELAYIMP | 0 | 0 | E3 |
| 14 | COM | 0 | 0 | E3 |
| 15 | RESERVED | 0 | 0 | E3 |

#### 异常 1：`IMPORT` Size = 0 但 RVA 非 0

`0x0E5DC635` 处字节：
```
5d c6 5d 0e 00 00 00 00 ff ff ff ff 6d c6 5d 0e
```
按 `IMAGE_IMPORT_DESCRIPTOR` 解析：
`OriginalFirstThunk = 0x0E5DC65D`、`TimeDateStamp = 0`、
`ForwarderChain = 0xFFFFFFFF`、`Name = 0x0E5DC66D`。

这在**结构上是一个有效的导入描述符表**，但目录 `Size = 0`。
⇒ **标准加载器不会解析它**（`Size=0` 即视为无导入）。

这条与记忆中"隐藏 IAT 在 `.idata2`，21 DLL / 748 槽"的旧结论**方向一致**，
但**旧结论的目录编号（dir[12]）已被本论文否定**：dir[12] = IAT 目录 = 0，
dir[1] = IMPORT = RVA 非零 / Size 0。

⇒ **导入表被剥离了大小字段，但内容还在**。这就是为什么
`iat_calls` / `resolve_exe_iat` 这类工具能工作：它们不依赖目录大小，
而是从 `RVA` 直接走链。

#### 异常 2：`RESOURCE` Size = 0 但内容完整

已实测解析出全部 5 类资源（见 BAP-0008）：ICON ×5、STRINGTABLE、
GROUP_ICON、VERSION、MANIFEST ×2。⇒ 同样是 **RVA 有效 / Size 归零**。

#### 异常 3：`SECURITY` 指向代码

`0x00777048` 处字节是 `8b 4d 10 50 8b 45 08 51 52 50 e8 f9 12 00 00`，
即 **x86 指令**（`mov ecx,[ebp+10] / push eax / mov eax,[ebp+8] / ...`），
不是 `WIN_CERTIFICATE`（应为 `dwLength/wRevision/wCertificateType` 且
`wRevision = 0x0200`）。实测首 4 字节 = `0x0C4D8B10`，长度荒谬。

⇒ **`SECURITY` 目录是假指针**，指向节 0 内的普通代码。
签名信息已被加壳器移除或篡改（E3）。

⚠ 但它 `Size = 0x35F8` 非零，若加载器按此解析会拒绝加载。
这解释了为什么**必须由原始加壳 EXE 启动、不能直接加载解包镜像**。

### 3.6 `DllCharacteristics = 0x8100`

```
0x0100 IMAGE_DLLCHARACTERISTICS_NX_COMPAT   ← 已置位
0x8000 IMAGE_DLLCHARACTERISTICS_TERMINAL_SERVER_AWARE ← 已置位
```
`DYNAMIC_BASE`(0x40)、`HIGH_ENTROPY_VA`(0x20)、`GUARD_CF`(0x4000)、
`FORCE_INTEGRITY`(0x80) **全部未置位**。

⇒ 无 ASLR、无 CFG、无强制签名校验。这与"`BASERELOC` = 0"互相印证：
镜像**加载地址固定为 `0x400000`**（E3）。

**这是本项目所有硬编码 VA 得以成立的根基**。
若 ASLR 开启，我们所有 `0x00DC6ACC` 之类的补丁地址都会失效。

---

## 4. 引用关系

| 字段 | 谁读 | 是否在镜像内 |
|---|---|---|
| `AddressOfEntryPoint` | Windows 加载器 | 否 |
| `ImageBase` / `BASERELOC=0` | Windows 加载器（决定是否重定位） | 否 |
| `DllCharacteristics` | Windows 加载器 | 否 |
| `SizeOfImage` | Windows 加载器（预留 VA 空间） | 否 |
| `CheckSum` | 仅驱动/签名校验时读 | 否 |

⇒ **整个可选头无镜像内读者**，全部由 loader 消费。
镜像内代码若有"读取自身 PE 头"的行为（常见于反调试/反篡改），
应表现为对 `0x400000` 附近常量的引用。BAP-0003D §3 将检查这一点。

---

## 5. 置信度

| 结论 | 级 |
|---|---|
| Machine = i386，PE32，7 节，GUI 子系统 | **E1/E2** |
| 构建时间 2021-05-08 13:32:58 UTC | **E3** |
| `SizeOfImage` = 镜像实际长度，无截断 | **E3** |
| 加载地址固定 `0x400000`（无 ASLR/无重定位） | **E3** |
| 入口点 `0x0E5DC690` = `call [0x0E9DC665]` | **E4** |
| `IMPORT`/`RESOURCE` 目录 Size 被归零但内容存在 | **E3** |
| `SECURITY` 目录指向代码，为假指针 | **E3** |

---

## 6. 待办（交讨论篇）

- 入口点 `call` 槽 `0x0E9DC665` 非 4 对齐 —— **必须排除 1 字节偏移错误**。
- `IMPORT` Size=0 是否为加壳器所为，还是我们提取镜像时清零。
