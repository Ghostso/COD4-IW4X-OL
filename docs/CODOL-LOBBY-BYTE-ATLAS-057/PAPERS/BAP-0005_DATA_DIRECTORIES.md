# BAP-0005 — 数据目录全表与四个异常 `[0x0001A0, 0x000220)`

| 项 | 值 |
|---|---|
| 范围 | 可选头内 16 × 8 = 128 字节，`0x0001A0` – `0x00021F` |
| 结构 | `IMAGE_DATA_DIRECTORY[16]` |
| 最高判据 | **E3**（每个非零目录都能在其 RVA 处解析出合法结构） |

---

## 1. 地址约定（本篇起严格执行）

```
RVA          = 目录里写的值
file_offset  = RVA                    ← 本镜像
VA           = RVA + 0x400000         ← 仅用于指令里的绝对地址
```

依据 BAP-0004 §0 与 BAP-0004D §6（E3，6/6 双向对照）。

---

## 2. 原始字节

```
01A0  b0 55 a1 00 c0 04 00 00 35 c6 5d 0e 00 00 00 00
01B0  00 90 5c 0e 00 00 00 00 00 00 00 00 00 00 00 00
01C0  48 70 77 00 f8 35 00 00 00 00 00 00 00 00 00 00
01D0  60 da 8a 00 1c 00 00 00 00 00 00 00 00 00 00 00
01E0  00 00 00 00 00 00 00 00 b8 8e 9e 00 18 00 00 00
01F0  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
0200  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
0210  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
```

---

## 3. 全表

| # | 名称 | RVA | Size | 状态 | 判据 |
|---|---|---|---|---|---|
| 0 | EXPORT | `0x00A155B0` | `0x000004C0` | ✅ 可解析 22 函数 | E3 |
| 1 | IMPORT | `0x0E5DC635` | **0** | ⚠ **Size=0 但内容完整** | E3 |
| 2 | RESOURCE | `0x0E5C9000` | **0** | ⚠ **Size=0 但内容完整** | E3 |
| 3 | EXCEPTION | 0 | 0 | 无 SEH 表 | E3 |
| 4 | SECURITY | `0x00777048` | `0x000035F8` | ❌ **指向代码，假指针** | E3 |
| 5 | BASERELOC | 0 | 0 | 无重定位 | E3 |
| 6 | DEBUG | `0x008ADA60` | `0x0000001C` | ✅ CodeView RSDS | E3 |
| 7 | ARCH | 0 | 0 | — | E3 |
| 8 | GLOBALPTR | 0 | 0 | — | E3 |
| 9 | TLS | `0x009E8EB8` | `0x18` | ⚠ **回调表为空** | E3 |
| 10 | LOADCFG | 0 | 0 | 无 CFG | E3 |
| 11 | BOUNDIMP | 0 | 0 | — | E3 |
| 12 | IAT | 0 | 0 | ⚠ IAT 目录为空 | E3 |
| 13 | DELAYIMP | 0 | 0 | — | E3 |
| 14 | COM | 0 | 0 | — | E3 |
| 15 | RESERVED | 0 | 0 | — | E3 |

---

## 4. 异常 1：`SECURITY` 目录是**假指针**

声明：`RVA = 0x00777048`，`Size = 0x35F8`。

该处字节（E3，直接读出）：

```
00777048  8b 4d 10 50 8b 45 08 51 52 50 e8 f9 12 00 00  .M.P.E.QRP......
00777058  83 c4 18 5d c2 10 00 cc cc 55 8b ec 32 c0 66  ...]......U..2.f
```

反汇编：

```
0x00777048  8B 4D 10        mov ecx, [ebp+0x10]
0x0077704B  50              push eax
0x0077704C  8B 45 08        mov eax, [ebp+0x08]
0x0077704F  51              push ecx
0x00777050  52              push edx
0x00777051  50              push eax
0x00777052  E8 F9 12 00 00  call +0x12F9
0x00777057  83 C4 18        add esp, 0x18
0x0077705A  5D              pop ebp
0x0077705B  C2 10 00        ret 0x10
0x0077705E  CC CC           int3 ×2
```

**这是标准 `__stdcall` 函数尾声**（`ret 0x10` = 4 个参数）。
`SECURITY` 目录应指向 `WIN_CERTIFICATE`，而不是代码。

若强行按 `WIN_CERTIFICATE` 解析：
`dwLength = 0x50104D8B`（1.3 GB）、`wRevision = 0x458B`、
`wCertificateType = 0x5108` —— 全部非法。

### 全文件搜索真实证书（E3 负面结论）

扫描整个镜像，找 `wRevision == 0x0200` 且 `dwLength` 合法的候选：
**共 11 处，全部落在 `0x0093Axxx`–`0x0099Axxx` 范围，
内容是 `00 02 00 00 00 02 02 00 …` 这类字节模式，
不是 Authenticode 结构**（真实 PE 签名以 `0x0002` 长度前缀 +
PKCS#7 `30 82 …` 开头）。

⇒ **结论（E3 负面）：本镜像不含任何 Authenticode 签名。**
`SECURITY` 目录是加壳器留下的悬空指针。

**对项目的直接含义**：任何依赖数字签名验证的启动检查
（TCLS/IIPS/ACE）若校验本 EXE 的签名，必然失败。
这与"启动必须经由 WeGame/TCLS 链"的既有认识一致。

---

## 5. 异常 2：`TLS` 回调表**为空**（0 个回调）

TLS 目录（`0x009E8EB8`，24 字节）：

```
0000009E8EB8: 00 80 9C 0E | 30 80 9C 0E | 0C 93 96 01 | 3C DA CA 00
               0x0E9C8000   0x0E9C8030   0x0196930C   0x00CADA3C
               StartRaw     EndRaw       AddrIndex    AddrCallbacks
```

四个字段都是**绝对 VA**（标准 TLS 目录语义，E3）。

转 file_offset（`− 0x400000`）：

| 字段 | VA | file_offset | 内容 |
|---|---|---|---|
| `StartOfRawData` | `0x0E9C8000` | `0x0E5C8000` | 48 字节全零（TLS 模板，正常） |
| `EndOfRawData` | `0x0E9C8030` | `0x0E5C8030` | 边界 |
| `AddressOfIndex` | `0x0196930C` | `0x0156930C` | `0x00000000`（运行时写入） |
| `AddressOfCallBacks` | `0x00CADA3C` | `0x008ADA3C` | **首项 = 0** |

`AddressOfCallBacks` 处实际字节：

```
008ADA3C  00 00 00 00 00 00 00 00 f6 85 c5 00 21 c7 c5 00  ............!...
008ADA4C  3c d0 c3 00 00 00 00 00 ...
```

逐项读指针：

```
cb[0] = 0x00000000   ← 立即终止
```

⇒ **TLS 回调数组的第一项就是 NULL ⇒ 运行时不会调用任何 TLS 回调。**

### 这意味着什么

- `0x008ADA3C + 8` 之后的 `0x00C585F6` / `0x00C5C721` / `0x00C3D03C`
  是**恰好相邻的数据**（另一张表），不是 TLS 回调。
- **没有 TLS 回调 = 没有 `DllMain` 之外的线程本地初始化链**。
  MSVC 的 `[T]` 段构造器（全局 C++ 对象）走的是
  `__scrt_common_main` 里的 `_initterm`，不依赖 TLS 回调。
  这与"入口点是跳板、真实初始化另有去处"吻合（BAP-0004 §2.6）。

⚠ 但这可能是**转储时机**造成的：若我们的快照在 TLS 回调表
被填充之前就抓了（或该表位于被加壳器清零的页），看到的就是 0。
**这是本论文最需要讨论的点**，见 BAP-0005D §2。

---

## 6. 异常 3：`IMPORT` 目录 Size = 0，但描述符表完整

`RVA = 0x0E5DC635` 处：

```
0E5DC635  5d c6 5d 0e 00 00 00 00 ff ff ff ff 6d c6 5d 0e
0E5DC645  65 c6 5d 0e 00 00 00 00 00 00 00 00 00 00 00 00 00
```

按 `IMAGE_IMPORT_DESCRIPTOR`（20 字节）解析：

| 项 | 值 |
|---|---|
| `OriginalFirstThunk` | `0x0E5DC65D` |
| `TimeDateStamp` | 0 |
| `ForwarderChain` | `0xFFFFFFFF` |
| `Name` | `0x0E5DC66D` → **`"codoMP_client_shipRetailBase.dll"`** |
| `FirstThunk` | `0x0E5DC665` |
| 终止项 | `0x0E5DC649` 起 20 字节全零 |

### 6.1 结论（E3）：静态导入表中**只声明了一个 DLL 名**

⚠ 这是"静态声明"，**不等于运行时依赖集**（见 §6.3 与 BAP-0005D §1 H3/H4）。

- 描述符表**只有 1 项** + 终止项。
- 该 DLL 名为 `codoMP_client_shipRetailBase.dll`
  —— 与我们已知的根层 `Base.dll` 名称一致，但是**完整版名字**。

⚠ 但 `TimeDateStamp = 0` 且 `OriginalFirstThunk` / `FirstThunk`
是**相邻的两个地址**（差 8 字节），且 `FirstThunk` 指向
`0x0E5DC665`——那是**导入名字符串中间的一个字节**
（`"codoMP_client_shipRetailBase.dll"` 从 `0x0E5DC66D` 开始，
`0x0E5DC665` 在它**之前** 8 字节）。

⇒ 这个描述符表**结构上不自洽**：
- `Name` 指向 DLL 名字符串 ✅
- `FirstThunk` 指向一个不是 thunk 数组的位置 ❌

**说明：描述符表是加壳器重建的"最小骨架"**，只为让某些检查
（读 DllName）通过，真正的 IAT 由加壳器在运行时填充。

这与记忆中"隐藏 IAT / `.idata2` / 序列号导入"系列结论方向一致，
但**具体机制本论文不下结论**，交 BAP-0009（导入表专篇）。

### 6.2 `FirstThunk` 处实际内容

```
0E5DC665: 2c 58 90 5e 00 00 00 00 | 63 6f 64 6f 4d 50 ... 
```

`0x5E90582C` 不是 VA（超出镜像），是垃圾。

⇒ 再次确认：这是**骨架描述符**，`FirstThunk` 值无意义。

---

## 7. 异常 4：`IAT` 目录（#12）为 0

标准 PE 会把 IAT 起始 RVA 写进 `dir[12]`，用于 loader 的写保护处理。
本镜像 `dir[12] = 0`。

⇒ 与 §6 一致：**加壳器不向 loader 暴露真实 IAT**。

⚠ 这条**不是**在推翻记忆中"隐藏 IAT 在 `.idata2`"的结论。
记忆本身已区分两种形态："EXE 是另一套形态（无 `.idata2`、`dir[12]` ABSENT）"。
本镜像属于后者。**两者说的是不同文件，不冲突**（见 BAP-0005D §1 H2）。

---

## 8. 其余目录的正面确认

| 目录 | 确认内容 | 判据 |
|---|---|---|
| `EXPORT` | 22 个 `Scaleform::`/`NvOptimusEnablement` 导出，见 BAP-0006 | E3 |
| `RESOURCE` | 5 类资源可完整展开，见 BAP-0008 | E3 |
| `DEBUG` | `RSDS` + GUID `f6225cf9…` + `D:\projects\AutoBuilder.rel2\iw4\game\pc\codoMP_client_shipRetail.pdb`，Age 1521 | E3 |
| `EXCEPTION` = 0 | 无 `.pdata`，函数边界只能线性扫描 | E3 |
| `BASERELOC` = 0 | **固定加载基址 0x400000，无 ASLR** | E3 |
| `LOADCFG` = 0 | 无 CFG（`/guard:cf` 未启用） | E3 |

### PDB 路径是本项目最强的构建身份证据

```
D:\projects\AutoBuilder.rel2\iw4\game\pc\codoMP_client_shipRetail.pdb
```

- `AutoBuilder.rel2` — 自动构建流水线、Release 分支 2
- `iw4` — **IW4 引擎代号**（Modern Warfare 2 引擎）
- `game\pc` — PC 平台
- 与 `VERSION` 资源里 `FileVersion = 1649370` 互相印证

⇒ **本镜像 = IW4 引擎 · AutoBuilder.rel2 流水线 · build 1649370 · 2021-05-08。**

---

## 9. 置信度

| 结论 | 级 |
|---|---|
| 16 目录值逐一读出 | **E1** |
| `file_offset = RVA` | **E3** |
| 无 Authenticode 签名 | **E3（11 候选全误报）** |
| `SECURITY` 指向代码 = 悬空指针 | **E3** |
| TLS 回调数组首项 = 0 | **E1**（静态；"运行时也无回调"未验） |
| 静态导入表只声明一个 DLL 名 | **E3** |
| 导入描述符是骨架，`FirstThunk` 无意义 | **E3** |
| `dir[12]` IAT = 0 | **E1** |
| PDB 身份 | **E3** |

---

## 10. 待办

- BAP-0005D：TLS 回调为空是"真无"还是"转储时机"？
- BAP-0005D：`dir[12]=0` 与记忆中 `.idata2` 结论的冲突处理。
- BAP-0009：导入表专篇（骨架结构 vs 运行时真实 IAT）。
