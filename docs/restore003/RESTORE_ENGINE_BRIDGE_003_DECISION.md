# RESTORE-ENGINE-BRIDGE-003 — Engine → ResourceManager consumption

## 判定

```text
RESTORE_ENGINE_BRIDGE_003_STATUS = COMPLETE

LOCALRM_LOAD                 = PASS
GETRM                        = FAIL        (Engine never called it)
RM_OBJECT_CONSUMED           = NO / NOT_OBSERVED
RM_VTABLE_ACCESSED           = NO / NOT_OBSERVED
RM_VTABLE_CALLS              = 0
FIRST_RM_SLOT_CALLED         = UNKNOWN
FIRST_RM_CALL_CONFIDENCE     = NOT_OBSERVED
RELEASE_CALLED               = NO / NOT_OBSERVED
ENGINE_GATE                  = PASS
POST_GATE_ENGINE_ACTIVITY    = YES
FF_ACTIVITY                  = NO
ZONE_ACTIVITY                = NO
ASSET_ACTIVITY               = NO
GAME_INIT                    = NO
ROOT_BLOCKING_POINT          = Post-gate, the Engine resolves IIPS\iips.dll and
                               requires the provider's own IIPS initialisation
                               contract (WIN_IIPS_INIT_ERROR / "iipsinit" window).
                               In condition B that contract is absent, the Engine
                               terminates with 0xFFFFFFFF at ~30.5s, and
                               GetResourceManagerII is never invoked.
NEXT_TARGET                  = Reproduce the post-gate IIPS init contract
                               observably (see §8)
```

本轮核心结论是一句**负证据**，但它是**真实的、可重复的、机器码级的**证据：

> 在 9 次运行、两种 provider、60/90 秒观测窗口内，
> **Engine 从未调用 `GetResourceManagerII`，也从未消费任何 ResourceManager 对象。**

`RM_VTABLE_CALLS = 0` 只表示"在当前实验窗口和当前观测机制下未观察到"。
**不能**据此写"Engine 不调用 ResourceManager"。

---

## 0. 本轮的完整性边界（先说清楚）

```text
原始 iips.dll        byte-identical    E2367C48...F97770   347704 bytes
原始 EXE             byte-identical    36997674...72B537   7841344 bytes
原始 Base.dll        byte-identical    EF75220D...BC6A20   60327992 bytes
原始 BugTrace.dll    byte-identical    1FDB07E4...225646   1029624 bytes
原始 TenProxy.dll    byte-identical    A5EE7EDE...1348CB   167592 bytes
LocalRM_v3.dll       byte-identical    032FAC66...A3EF26   352256 bytes
```

条件 B **没有**就地替换 `IIPS\iips.dll`。做法是建立隔离沙箱：顶层条目对原始目录做
junction/hardlink，`IIPS\` 是真实目录且内容为副本，**只把 `iips.dll` 一个文件换成
`LocalRM_v3.dll`**。因此 A 与 B 的唯一字节级差异就是 provider 模块本身。
（`restore003/mk_sandbox.ps1`）

全程**未**使用 debugger / CDB / WinDbg、**未**使用硬件断点、**未**触碰反调试 /
TenProtect / ACE、**未**做 PRCL 静态扫描、**未**猜测 `.tvm0` ISA。
观测手段只有 `CreateProcess` + `ReadProcessMemory` + `VirtualAllocEx` +
`Toolhelp32` + `EnumWindows`。

---

## 1. Agent 01 — 两个 provider 的静态事实

### 原始 iips.dll（导出表，byte 级解析）

```text
dll name = iips.dll      Base=1  nfunc=4  nnames=4
  GetResourceManager          ord=1  RVA 0x1BC0
  ReleaseResourceManager      ord=2  RVA 0x1C60
  GetResourceManagerII        ord=3  RVA 0x1C80
  ReleaseResourceManagerII    ord=4  RVA 0x1C60

GetResourceManagerII @0x1C80:
  6A FF 68 A9 25 03 10 64 A1 00 00 00 00 50 51 A1 20 20 04 10 33 C4 50 8D 44 24 08
  64 A3 00 00 00 00 F6 05 6C EB 04 10 01
  （SEH 序言 + /GS cookie + test byte [0x1004EB6C],1 —— 与 LOCALRM-006 的译码一致）

ReleaseResourceManagerII @0x1C60:
  8B 4C 24 04 85 C9 74 08 8B 01 8B 10 6A 01 FF D2 C3
  （__cdecl, NULL-safe, vtable[0](this,1) —— 与 LOCALRM-006 完全一致）
```

**注**：`IIPS\iips.dll` 的 PE 头是 `nsec=5`、无 `.localrm` 段，确认它是**未修改的原始文件**，
不是前几轮的改造产物。

### LocalRM_v3.dll

```text
nsec=6  entry RVA 0x55180   SizeOfImage 0x56000   preferred base 0x10000000
exports:
  GetResourceManagerII        ord=1  RVA 0x55000
  ReleaseResourceManagerII    ord=2  RVA 0x55040
vtable @.localrm+0x210: 48 slots，只有两个不同目标
  slot 0    = 0x10055080   (deleting destructor)
  slot 1..47= 0x100550C0   (同一个共享 stub: mov eax,1 ; ret)
```

代码与 LOCALRM-006 记录**逐字节一致**（已重新反汇编确认）：

```asm
GetResourceManagerII  (RVA 0x55000)
  B8 00 52 05 10   mov  eax,0x10055200     ; guard/flag slot
  83 38 00         cmp  dword [eax],0
  74 08            je   lazy
  B8 04 52 05 10   mov  eax,0x10055204     ; instance slot
  8B 00            mov  eax,[eax]
  C3               ret
  E8 C9 00 00 00   call lazy_init
  B8 04 52 05 10   mov  eax,0x10055204
  8B 00            mov  eax,[eax]
  C3               ret

ReleaseResourceManagerII (RVA 0x55040)
  8B 4C 24 04 85 C9 74 0B 8B 01 8B 10 68 01 00 00 00 FF D2 C3
  （__cdecl；test ecx,ecx；vtable[0](this,1)）

lazy_init (RVA 0x550E0)
  push 0x410                       ; 对象大小
  call dword ptr [0x1003328C]      ; operator new（IAT，来自 msvcr80）
  mov [edx+0x00],0x10055210        ; 4 个 vptr
  mov [edx+0x04],0x10055214
  mov [edx+0x20],0x10055230
  mov [edx+0x44],0x10055254
  mov [0x10055204],edx             ; instance = 新对象
  mov dword [0x10055200],1         ; guard = 1
```

### 一个真实的实现缺陷（记录，不修）

`LocalRM_v3.dll` 的 Data Directory 把 EXPORT 目录指向 `RVA 0x55360`，
但真正的 `IMAGE_EXPORT_DIRECTORY` 起点在**文件偏移 `0x5535C`（即 `.localrm+0x35C`）**，
**声明值比实际晚 4 字节**。Windows loader 容忍这一点（两个导出名都能解析），
但镜像结构是错位的。

```text
LOCALRM_V3_EXPORT_DIR_ALIGNMENT = DEFECT (declared 0x55360, actual 0x5535C, delta +4)
IMPACT                          = none observed (loader tolerant)
EVIDENCE                        = restore003/evidence/a01_artifact_recon.json
```

---

## 2. Agent 02 / 03 / 05 — Engine 究竟怎样拿到 provider

### 谁 import 了 iips？

```text
codoMP_client_shipRetail.exe
    导入表只有 1 个条目： codoMP_client_shipRetailBase.dll  ordinal 1
    不导入 iips.dll，也不导入 LoadLibrary / GetProcAddress
    但 .rdata 里有字符串 "IIPS\iips.dll"

codoMP_client_shipRetailBase.dll
    导入 kernel32!LoadLibraryA, kernel32!GetProcAddress（+1 个 CEF 函数）
    完全没有 "iips" 相关字符串
```

### EXE `.rdata` 里的解析契约（原始字节）

```text
0x6B5294  "GetResourceManagerII"
0x6B52AC  "ReleaseResourceManagerII"
0x6B53A8  "WIN_IIPS_INIT_ERROR"
0x6B53BC  "WIN_IIPS_PREDOWNLOAD_ERROR"
0x6B53D8  "WIN_IIPS_INIT_FAILED"
0x6B53F0  "IIPS\iips.dll"
0x6B5408  "WIN_IIPS_DLL_ERROR"
0x6B5440  "Environment List Box"
```

结论：

```text
PROVIDER_RESOLUTION = LoadLibraryA("IIPS\iips.dll") + GetProcAddress(名字)
RESOLVED_BY_ORDINAL = REFUTED
```

**序数布局差异不影响本轮结论**（虽然确实存在）：

```text
原始 iips.dll     GetResourceManagerII = ordinal 3
LocalRM_v3.dll    GetResourceManagerII = ordinal 1
→ 若按序数绑定会拿到不同函数；但 Engine 按**名字**绑定，所以这条被排除。
```

### 模块架构

```text
Base.dll   60327992 bytes, 8 sections, 有 .tvm0 (vsize 0x01F5E000 ≈ 32.7 MB)
           导出 3 个无名序数；序数 1 = RVA 0x1D6582C
EXE        7841344 bytes, 7 sections, .tp3 段承载主体, .tvm0 仅 0x4000
           只调用 Base.dll!ordinal1
```

`Base.dll` 的引擎逻辑位于 **~32.7 MB 的 `.tvm0` 虚拟化容器**里，静态不可达。
这解释了为什么下一节的 IAT hook 观察不到解析调用。

---

## 3. Agent 04 / 13 — ABI 等价性（本轮最硬的正向结果）

在**真实 32-bit host** 中分别加载两个 provider 并驱动导出（原始 `iips.dll` 用临时副本，
不加载安装目录里的文件）：

| 观测项 | 原始 `iips.dll` | `LocalRM_v3.dll` |
|---|---|---|
| LoadLibrary | PASS | PASS |
| Load base | 0x10000000 | 0x10000000 |
| GetProcAddress | PASS `0x10001C80` | PASS `0x10055000` |
| 返回值 | 非空堆对象 | 非空堆对象 |
| `obj+0x00` vptr | `0x1003934C`（在镜像内） | `0x10055210`（在镜像内） |
| vtable 48 槽非空 | **48/48** | **48/48** |
| `obj+0x04` | `0x1003940C` | `0x10055214` |
| `obj+0x20` | `0x10039430` | `0x10055230` |
| `obj+0x44` | `0x10039438` | `0x10055254` |
| 调用结果 | NO_FAULT | NO_FAULT |

```text
STRUCTURAL_ABI_EQUIVALENCE = CONFIRMED
```

两点意义：

1. LOCALRM-006 关于"4 个 vptr 位于 +0x00/+0x04/+0x20/+0x44、48 槽非空 vtable"的机器码论断，
   本轮**首次用原始 provider 独立复现**，不再只是重构物的自证。
2. **原始 `iips.dll` 确实会构造一个真实的 0x410 ResourceManager 对象**——
   这一点此前并未被直接观察到过。

证据：`restore003/evidence/a13_abi_equivalence.json`

---

## 4. Agent 09 / 12 — 一个被本轮自己否证的假设（如实记录）

我一度建立过以下假设：

> H1：`.localrm` 的 8 个硬编码绝对地址（guard `0x55200`、instance `0x55204`、
> 4 个 vptr `0x55210/14/30/54`、operator new/delete IAT `0x3328C/0x33284`）
> **不在重定位表内**，所以只要模块不落在 `0x10000000`，这些地址就是错的，
> 导致条件 B 失败。

静态部分成立：

```text
.localrm 重定位数量 = 0        （.text 5166 / .rdata 1482 / .data 308）
8 个硬编码绝对地址 = 全部 NOT RELOCATED
vtable 48 槽自身地址 = 0/48 relocated
```

但运行数据把它**否证**了：

```text
全部 9 次运行中，provider 都**不是**加载在 0x10000000（Base.dll 先占了它）
  A1 0x17380000  A2 0x16550000  A3 0x16520000  A4 0x164D0000
  B1 0x16690000  B2 0x16540000  B3 0x16690000  B4 0x12E10000  B5 0x12D40000

原始 iips.dll 的 singleton 操作数 [0x1004EB6C] / [0x1004EB68] 同样 NOT RELOCATED
→ 原始 DLL 也一样"依赖基址"，但它在每次 A 运行里都能走到自己的 IIPS 初始化路径
```

```text
H1_MISSING_RELOCATION_AS_ROOT_CAUSE = REFUTED
```

**重定位状态无法区分 A 与 B**，因此不能作为条件 B 失败的根因。
这条否证保留在案，以免后续轮次重复踩同一个假设。

证据：`a08_localrm_relocs.json`、`a11_original_base_dep.json`、
`a12_refute_reloc_hypothesis.json`

---

## 5. 第一/二阶段 — baseline 与 A/B 对照结果

每次运行：`codoMP_client_shipRetail.exe -q`，观测 60s（B5 为 90s）。

| run | 条件 | gate 时刻 | provider | `#32770 致命错误` | iipsinit 文本 | RM vtable 调用 | GetRM 调用 | 终止 |
|---|---|---|---|---|---|---|---|---|
| A1 | 原始 | 7.32s | (分类器早期版本) | **YES** | "Environment List Box" | 0 | 不可观测 | 挂起至 60s |
| A2 | 原始 | 6.53s | `orig_iips` | **YES** | "Environment List Box" | 0 | 不可观测 | 挂起至 60s |
| A3 | 原始 | 6.59s | `orig_iips` | **YES** | "Environment List Box" | 0 | 不可观测 | 挂起至 60s |
| A4 | 原始 | 7.04s | `orig_iips` | **YES** | "Environment List Box" | 0 | 不可观测 | 挂起至 60s |
| B1 | LocalRM_v3 | 7.13s | `LocalRM_v3` | **NO** | *(空)* | 0 | **0** | 挂起至 60s |
| B2 | LocalRM_v3 | 6.49s | `LocalRM_v3` | **NO** | *(空)* | 0 | **0** | **0xFFFFFFFF @30.6s** |
| B3 | LocalRM_v3 | 6.64s | `LocalRM_v3` | **NO** | *(空)* | 0 | **0** | **0xFFFFFFFF @30.6s** |
| B4 | LocalRM_v3 | 6.47s | `LocalRM_v3` | **NO** | *(空)* | 0 | **0** | **0xFFFFFFFF @33.6s** |

```text
ENGINE_GATE            = PASS   两种条件都通过（约 6.5–7.3s，96 项派发表填满）
ENGINE_GATE_IS_NOT_GAME_INIT
                       派发表填满 ≠ Engine 初始化成功。两种条件下 gate 之后的
                       行为完全不同，而 GAME_INIT 在两种条件下都**没有**到达。
PROCESS_ALIVE_IS_NOT_ENGINE_OK
                       条件 A 进程"活着 60s"只是因为模态对话框阻塞，不是成功。
```

### 条件 A 的 post-gate 行为

```text
gate 后 ~0.5s : 弹出 "iipsinit" 窗口，文本 "Environment List Box"
gate 后 ~0.5s : 弹出 #32770 对话框，标题「致命错误」
                内容 "初始化IIPS错误：8189fec。"
随后         : 模态阻塞，直到被观测器 terminate
FF / Zone / Asset 活动 = 未观察到
```

### 条件 B 的 post-gate 行为

```text
gate 后 ~0.3s : 弹出 "iipsinit" 窗口，**文本为空**（"Environment List Box" 消失）
gate 后 ~0.3s : **没有** #32770 致命错误对话框
随后         : 进程自行退出，退出码 0xFFFFFFFF（4/4 次携带该信号的运行都如此）
```

`RM_GUARD_CHANGED guard=0` —— `LocalRM_v3` 的 guard 槽**始终为 0**，
即 `lazy_init` 从未运行，对象从未被构造。

---

## 6. 第二/三阶段 — 逐条回答 Q1–Q4

### Q1 Engine 是否读取 ResourceManager 对象的 vtable？

```text
Q1 = NOT_OBSERVED
  条件 A：无法观测（禁止对原始 provider 写入，因此无法挂接 vtable）
  条件 B：对象从未被构造，故不存在可读的 vtable
```

我**没有**把"48 槽计数全为 0"写成"Engine 不读 vtable"。

### Q2 Engine 是否调用任意 RM vtable slot？

```text
Q2 = NOT_OBSERVED
RM_VTABLE_CALLS = 0
FIRST_RM_SLOT_CALLED = UNKNOWN
CONFIDENCE = NOT_OBSERVED

条件 B 已启用真实 vtable 记录机制（把对象的 vptr 改指向 48 个记录 trampoline，
记录 slot/this/args/caller 后转发到真实实现），但因为对象从未构造，
该机制一次都没有被触发。
```

**若某个 slot 被调用，它会成为硬事实。48 个 slot 一个都没被调用，同样是硬事实。**

### Q3 Engine 是否访问 RM object 内存？

```text
Q3 = NOT_OBSERVED

条件 A：用"形状发现"扫描了 2085 个私有可读写区域，candidates = 0
        （扫描条件已收紧为只接受 LOCALRM-006 记录的 4 个 vtable RVA，
          早期宽松版本产生的 8 个匹配已被判定为 false positive 并弃用）
条件 B：对象不存在
```

**字段读取从进程外原理上不可观测**，本轮不对任何 offset 赋予语义。

### Q4 Engine 是否调用 GetResourceManagerII / ReleaseResourceManagerII？

```text
GETRM = FAIL   （Engine 从未调用）
RELEASE_CALLED = NO / NOT_OBSERVED

条件 B 的直接测量：
  * 在导出入口 0x166E5000 等地址装记录 trampoline → 调用计数 = 0
  * 全进程 IAT 扫描（任何槽的值落在 provider 映像内）→ hits = 0
  * provider 自己的 instance 槽 (base+0x55204) → 始终 0
  * provider 自己的 guard 槽   (base+0x55200) → 始终 0
  四条独立通道一致：Engine 从未取得也未调用这两个导出。

条件 A：不写入原始 provider，因此没有直接的调用计数；
        外部对象扫描也未发现符合形状的 RM 对象（candidates=0）。
```

`Release → Get` 的悬空指针行为：本轮**未能观测**，因为 `Release` 本身从未被调用。

---

## 7. 第三/四阶段 — Gate 对照表与"未观察到"的含义

```text
                     A = 原始 iips.dll      B = LocalRM_v3.dll
IIPS_LOAD            PASS                   PASS
GETRM                NOT_OBSERVED(不可写)     FAIL (计数 0，四通道一致)
RM_NON_NULL          NOT_OBSERVED           NO (guard=0, instance=0)
RM_VTABLE_ACCESS     NOT_OBSERVED           NOT_OBSERVED (对象不存在)
RM_VTABLE_CALL       NOT_OBSERVED           NOT_OBSERVED (0)
ENGINE_GATE          PASS                   PASS
ENGINE_POST_GATE_EXECUTION  YES (到 IIPS 错误对话框)  YES (到空 iipsinit 窗口后自行退出)
FF_ACTIVITY          NO                     NO
ZONE_ACTIVITY        NO                     NO
ASSET_ACTIVITY       NO                     NO
GAME_INIT            NO                     NO
TERMINATION          观测器终止 (模态阻塞)    自行退出 0xFFFFFFFF @~30.5s
```

`VTABLE_CALLS = 0` 的**唯一**合法解释是：

> 在当前实验窗口和当前观测机制下未观察到。

---

## 8. 根因（受限表述）

可确证的因果链：

```text
1. 两种条件下 Engine 都越过 Local RM gate（96 项派发表填满）。        CONFIRMED
2. Engine 通过 LoadLibrary("IIPS\iips.dll") + GetProcAddress(名字) 解析 provider。
   LocalRM_v3 提供两个所需导出名，绑定层面无障碍。                     CONFIRMED
3. 但 Engine 在调用 GetResourceManagerII **之前**还需要 provider 完成
   自身的 IIPS 初始化契约：
     - 创建 "iipsinit" 窗口并写入文本 "Environment List Box"
     - 失败时给出 WIN_IIPS_INIT_ERROR (8189fec) 与「致命错误」对话框
   LocalRM_v3 **完全没有实现**这套 IIPS 记账。                         CONFIRMED
4. 条件 B 中该契约缺失：iipsinit 窗口文本为空、无致命错误对话框、
   进程在 ~30.5s 自行退出 0xFFFFFFFF。                                 CONFIRMED
5. 在整个窗口内，四条独立通道一致表明 GetResourceManagerII 从未被调用。  CONFIRMED
```

因此：

```text
ROOT_BLOCKING_POINT = provider 层的 IIPS 初始化契约缺失，
                      而非 RM ABI 不匹配、也非导出不可用、也非序数错位。
                      在 Engine 的次序里，RM 供给发生在 IIPS 初始化之后，
                      而条件 B 从未走到那一步。
```

**受限于**：`Base.dll` 的引擎逻辑在 ~32.7 MB 的 `.tvm0` 虚拟化段内，
且对 `LoadLibraryA`/`GetProcAddress` 的 IAT hook 记录到 0 次调用
（说明解析路径不经过该 IAT）。因此"Engine 在哪一条指令上决定不再继续"
**无法在不恢复 VM ISA 的前提下定位**。这一点记为 `INSTRUMENTATION_BLOCKED`，
不猜测。

---

## 9. 证据分级汇总

```text
CONFIRMED
  Engine gate 在两种条件下都通过（9/9 运行，96 项派发表）
  两种 provider 的结构性 ABI 等价（48/48 槽非空，4 个 vptr 位置一致）
  原始 iips.dll 会构造真实 0x410 ResourceManager 对象
  provider 解析方式 = LoadLibrary(路径) + GetProcAddress(名字)
  条件 B 中 GetResourceManagerII 从未被调用（四通道一致）
  条件 B 中 guard/instance 槽始终为 0（对象未构造）
  条件 A 出现「致命错误 / 初始化IIPS错误：8189fec」对话框（4/4）
  条件 B 无该对话框、且 4/4 携带该信号的运行以 0xFFFFFFFF 自行退出
  .localrm 段重定位数量为 0
  LocalRM_v3 导出目录声明值偏移 +4 字节（结构错位）

REFUTED
  "缺重定位是条件 B 失败的根因"
  "按序数绑定能解释差异"
  "provider 导出名缺失/不可解析"

NOT_OBSERVED
  Engine 读取 RM vtable
  Engine 调用任意 RM vtable slot
  Engine 访问 RM object 内存字段
  Engine 调用 ReleaseResourceManagerII
  FF_ACTIVITY / ZONE_ACTIVITY / ASSET_ACTIVITY / GAME_INIT

UNKNOWN
  RM_SLOT_SEMANTICS（48 个 slot 的语义，本轮不赋予任何含义）
  NESTED_OBJECT_INPLACE_AT_0x70 / RM_OFFSET_3BC（沿用旧结论，本轮无新证据）

INSTRUMENTATION_BLOCKED
  Engine 在 .tvm0 内部分支的精确指令位置
  Engine→RM 的最终调用点（因为从未到达）
```

关于 slot 语义：本轮观测到的唯一"槽行为"事实是

```text
VTABLE_SLOT_0 = deleting destructor（沿用 LOCALRM-006，本轮静态复核通过）
VTABLE_SLOT_1..47 = 同一个共享 stub，mov eax,1 ; ret
STUB_SLOT_CALLED = NO   （条件 B 中一次都未被调用）
```

不写 `slot N = Something()`。

---

## 10. 复现

```powershell
# 0) 静态事实
python restore003/a01_artifact_recon.py        # 工件身份 + 两个 provider 的导出/vtable
python restore003/a02_import_binding.py        # 谁 import 了 iips
python restore003/a02b_ordinal_chain.py        # 序数布局对照
python restore003/a03_dynamic_resolution.py    # EXE 里的解析字符串
python restore003/a03b_string_cluster.py       # 解析契约字符串簇
python restore003/a05_base_host.py             # EXE/Base 的解析职责划分
python restore003/a05b_exe_ordinal1.py         # Base.dll 序数 1
python restore003/a06_tvm0_and_loader.py       # .tvm0 与 loader 面
python restore003/a08_localrm_relocs.py        # .localrm 重定位覆盖
python restore003/a10_root_cause.py            # 基址/因果链
python restore003/a11_original_base_dep.py     # 原始 DLL 是否也依赖基址
python restore003/a12_refute_reloc_hypothesis.py # H1 的否证

# 1) 观测器自检（写入目标进程之前先证明字节编码正确）
.\restore003\observer\out\EBO3.exe --selftest

# 2) ABI 等价性（真实 32-bit host；原始 DLL 用临时副本）
python restore003/a13_abi_equivalence.py

# 3) 沙箱（原始安装目录不被写入）
.\restore003\mk_sandbox.ps1 -Sandbox .\restore003\sandbox_B

# 4) A/B 运行
.\restore003\observer\out\EBO3.exe --mode A --tag A5 --duration 60
.\restore003\observer\out\EBO3.exe --mode B --tag B6 --duration 60 `
    --sandbox ".\restore003\sandbox_B"

# 5) 汇总
python restore003/a07_aggregate.py
```

---

## 11. 本轮未做的事（边界）

未修改原始 EXE / `iips.dll` / Base.dll / BugTrace.dll / TenProxy.dll；
未使用 debugger / CDB / WinDbg / 硬件断点；未绕过反调试 / TenProtect / ACE；
未做 PRCL 静态扫描；未猜测 `.tvm0` ISA；未猜 ResourceManager slot 语义；
未访问在线服务；未构造假的 FF / Zone / Asset 数据；未恢复 IIPS QoS / WeGame / TCLS。
原始 installed 文件在本轮结束后 SHA256 全部不变（§0）。

---

## 12. 下一步（单一目标）

```text
NEXT_TARGET = 在 LocalRM_v3 上补上可观测的 IIPS 初始化契约，
              使 Engine 走到 GetResourceManagerII 调用点；
              首个成功的 slot 调用即为下一轮的硬事实。
```

最小实验（不做额外扩张）：

1. 在沙箱 provider 中实现足以通过 post-gate IIPS 初始化的最小行为
   （创建并填充 `iipsinit` 窗口文本；不复现网络/QoS/TenProtect）。
2. 保留本轮的 vtable 记录机制与四条 GetRM 观测通道，条件 B 不变。
3. 判据：`GRM_CALL > 0` 或 `RM_VTABLE_CALLS > 0`。
   若仍然为 0，则说明 Engine 在 IIPS 初始化之前还有别的门槛，
   届时按同样标准记录新的负证据，**不要**修改结果去迎合旧模型。
