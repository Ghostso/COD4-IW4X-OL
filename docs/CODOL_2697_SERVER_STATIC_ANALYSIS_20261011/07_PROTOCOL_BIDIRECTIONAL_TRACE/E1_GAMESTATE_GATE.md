# E1 — Gamestate 发布链与注册门控（服务端侧）

> 阶段 E · 静态分析。二进制：`codol_dedrun.exe`
> SHA-256 `80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1`
> ImageBase `0x400000`。所有 RVA 均相对文件映像。
> 本阶段未启动游戏/服务端，未做运行时观测；互通结论一律为 NOT-OBSERVED。

## 0. 结论速览

| 项目 | 结论 | 等级 |
| --- | --- | --- |
| 注册门控由两个全局标志（资源安装 + 注册校验）共同决定，两个写入者均已定位 | 是 | VERIFIED |
| 未通过门控时行为 | 打印 withheld 后直接 **return 0**，不延迟、不切旧通道、不排队 | VERIFIED |
| gamestate 编码顺序 | `03 <long> <map\0> "mp"\0 <long> <configstrings:04…> <long> <long> 06` | VERIFIED |
| configstrings 子段终止符同样是 `0x06` | 是 | VERIFIED |
| 新通道实际调用者 | 有；`_CODOL_WriteServerGamestate` ← `_SV_WriteGameState` ← `_SV_SendClientGameState`/`_SV_RecordClient` | VERIFIED |
| `evidence\client-registration2697.txt` 的性质 | 磁盘上的**真实注册校验输入**（CRC32 校验通过后置门控标志），只在 CVar 指名时才被读取；启动脚本确实指名了它 | VERIFIED |
| 客户端能否接收该 gamestate | 未在客户端验证 | NOT-OBSERVED |

## 1. 样本与身份

| 项 | 值 |
| --- | --- |
| 服务端路径 | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe` |
| SHA-256 | `80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1` |
| ImageBase | `0x400000`（VERIFIED，pefile 直接读取） |
| 符号来源 | `CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\_data\syms_NEW.json`（上一阶段生成，本次仅作为名称参考，所有断言均以本样本反汇编为准） |

注册证据文件：

| 项 | 值 |
| --- | --- |
| 路径 | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\evidence\client-registration2697.txt` |
| 大小 | 2,976 B |
| SHA-256 | `4F1B4A38D8088FDCF650BE83BBAAE0A5D34D2A0550C592609BECFAD3AC289E2C` |
| 首行 | `codol2697-registration 2 6b6fb5d0 180 139 f78302fe` |
| 行数 | 100+ 行（首行 + 索引/配置名行） |

## 2. 注册门控：检查了什么

### 2.1 请求写 gamestate 的入口

`_CODOL2697_WriteNativeGamestate` RVA `0xA3DAB`（VERIFIED，反汇编 0xA3DAB..0xA3EA0）：

```
004a3db8  call  _CODOL_Server2697ResourceSource      ; 0x4C3020 -> 返回 &资源指针
004a3dbd  mov   ebx, eax
004a3dbf  mov   eax, [eax]                           ; eax = 资源对象
004a3dc1  cmp   dword [eax+0x78F4], 0                ; 门控条件①
004a3dc8  je    0x4A3DD8                             ; 为 0 -> withheld
004a3dca  call  _CODOL_Server2697Registration        ; 0x4C3026 -> 返回注册结构基址
004a3dcf  cmp   dword [eax+0x6408], 0                ; 门控条件②
004a3dd6  jne   0x4A3E00                             ; 非 0 -> 放行
004a3dd8  ... withheld 路径 ...
```

- **条件①**：资源对象（`_CODOL_Server2697ResourceSource` 解引用后）+`0x78F4` 非零。
- **条件②**：注册结构（`_CODOL_Server2697Registration` 返回的 `0x14973B00`）+`0x6408` 非零。
- 等级：**VERIFIED**（指令级）。

`_CODOL_Server2697ResourceSource` RVA `0xC3020`：`mov eax,0x78AEC8; ret`（返回的是**指针的地址**，故调用点需要再 `mov eax,[eax]`）。
`_CODOL_Server2697Registration` RVA `0xC3026`：`mov eax,0x14973B00; ret`。

### 2.2 注册结构 `0x14973B00`

- 在 `_CODOL_SetTarget2697ServerResources`（RVA `0xC311B`）中先 `memset(0x14973B00, 0, 0xC814)`。
  → 结构大小 **0xC814**（VERIFIED，`004c3217..004c322e`）。
- 门控标志位于结构偏移 `+0x6408`。
- **写入者已定位（VERIFIED）**：`_CODOL2697_ReadRegistration` 把校验结果写入**本地栈 blob** 的同布局区域。栈布局证据：

  | 指令 RVA | 内容 |
  | --- | --- |
  | `0xA3EB5` | `lea eax,[ebp-0xC820]` — 本地 blob 基址 |
  | `0xA43BC` | `mov dword [ebp-0x6418], 1` — 校验全部成功后写“成功”标志 |

  偏移换算：`0xC820 − 0x6418 = 0x6408`。即 `[ebp-0x6418]` 正好是本地 blob base `[ebp-0xC820]` 的 `+0x6408`。
- 随后 `0xA43DE` 的 `memcpy(out, [ebp-0xC820], 0xC814)` 把该 blob 整体拷到调用方提供的 `0x14973B00`。
  → 因此 `_CODOL2697_ReadRegistration` 返回 1 时，`[0x14973B00+0x6408] == 1`；任何一步失败（CRC 校验失败 / 字符集非法 / 行格式不合法）则保持 memset 后的 0。
- 等级：**VERIFIED（指令级 + 偏移算术）**。这解释了为什么不存在 `mov [0x14973B00+0x6408], …` 形式的直接写指令——写入发生在**栈副本**上。

### 2.3 注册文件的读取时机与语义

`_CODOL_SetTarget2697ServerResources` RVA `0xC311B` 关键分支（VERIFIED）：

```
004c3209  call  _Cvar_FindVar                     ; "codol_target2697Registration"
004c3233  test  edi, edi
004c3235  je    0x4C3247                          ; CVar 不存在 -> 用零注册构建
004c3237  mov   eax, [edi+0xC]                    ; .string
004c323a  test  eax, eax
004c323c  je    0x4C3247
004c323e  cmp   byte [eax], 0
004c3241  jne   0x4C3324                          ; 非空 -> 读注册文件
004c3324  mov   [esp+4], 0x14973B00
004c332c  mov   [esp], eax
004c332f  call  _CODOL2697_ReadRegistration       ; 0xA3EA0
004c3334  mov   edi, eax
004c3336  test  eax, eax
004c3338  jne   0x4C3247                          ; 成功 -> 继续构建
004c333e  ... "CoDOL 2697 invalid client registration export\n"
```

`_CODOL2697_ReadRegistration` RVA `0xA3EA0`（VERIFIED，0xA3EA0..0xA4400）：

1. `memset` 本地 `0xC814` blob；
2. 参数要求路径非空、输出指针非空；
3. `fopen(path,"rb")`；
4. `fgets(line,0x80,f)`；
5. 先按 **3 字段**格式 `sscanf(line,"codol2697-registration %u %x %u", &kind,&hash,&idx)`；
   若不等于 3，则按 **5 字段**格式 `sscanf(line,"codol2697-registration %u %x %u %u %x %c", …)`；
6. 校验 `kind ∈ [1,2]`、`index ∈ [1,0xC7]`；
7. 逐行读表项，字符集校验 `[0-9A-Z_]`，对正文算 **CRC32（多项式 0xEDB88320）**，要求 `~crc32 == 存储值`；
8. 全部通过后 `memcpy(0xC814)` 到输出指针并 **return 1**（`004a43e3`）。

实际文件首行解析结果（与 5 字段格式匹配）：

| 字段 | 值 |
| --- | --- |
| kind | `2` |
| hash | `0x6B6FB5D0` |
| idx | `180` |
| idx2 | `139` |
| crc | `0xF78302FE` |

**关于“该文件是运行时输入还是审计记录”的判定**：

- 文件内容被 `fopen/sscanf/CRC32` 真正消费；它不是纯记事文本 → 具备运行时输入格式。**VERIFIED**
- 只有当 CVar `codol_target2697Registration` 的 `.string` 非空时才会读；CVar 缺失/为空时走“零注册直接构建”路径。**VERIFIED**
- 该 CVar 字符串在整个 `server2697` 目录内的**全部文件**中只出现在：
  - `codol_dedrun.exe`（字符串本身）
  - `room_host2697.py`（第 82 行把它设成 `evidence/client-registration2697.txt`）
  - `run_native_connection.py`（第 258/270 行同样指名该文件）
  **VERIFIED**（全目录字节级搜索）。
- 结论：**该文件是启动脚本显式指名的真实注册校验输入**，而非仅供审计的说明文件；但“默认不读”仍成立——是脚本让它被读的。等级 **VERIFIED（脚本）** + **STATIC-INFERENCE（该脚本即实际启动路径）**。

### 2.4 未通过门控的具体行为

`0x4A3DD8` 落点（VERIFIED）：

```
004a3dd8  mov [esp+4], 0x7C424C        ; "CoDOL 2697 gamestate withheld: ... required\n"
004a3de0  mov [esp], 0xF               ; 打印级别
004a3de7  call _Com_Printf
004a3dec  mov esi, 0
004a3df1  mov eax, esi
004a3df9  leave
004a3dfa  ret
```

- **直接返回 0**：不延迟、不切旧通道、不入队、不重试。上层的 `_collect`/`calloc` 只有在门控**通过后**才会执行。**VERIFIED**
- 两个门控条件的来源（VERIFIED）：

  | 条件 | 位置 | 写入者 | 写入指令 |
  | --- | --- | --- | --- |
  | ① `[resource+0x78F4] != 0` | 资源对象 | `_CODOL2697_InstallResources`（`0xA44A0`） | `0xA4505`：`mov dword [eax+0x78F4], 1` |
  | ② `[registration+0x6408] != 0` | `0x14973B00+0x6408` | `_CODOL2697_ReadRegistration`（`0xA3EA0`） | `0xA43BC`：`mov dword [ebp-0x6418], 1`（栈副本，随 memcpy 进入全局） |

  两者的共同上游都是 `_CODOL_SetTarget2697ServerResources`（`0xC311B`）：先调 `_CODOL2697_InstallResources`（`0xC34B3`），再按 CVar 决定是否调 `_CODOL2697_ReadRegistration`（`0xC332F`）。
- 注意：这里“返回 0”是**新通道的自放弃**，不是“回退到旧 0x02/0x05 通道”。旧通道是否在主流程另有分支需在 `_SV_WriteGameState` 层确认（见 §4）。

## 3. 通过门控后的编码路径

### 3.1 调用链（VERIFIED）

```
_SV_SendClientGameState  (0x70E47)
  ├─ _SV_WriteGameState   (0x822D7)          ; 该函数内同时有 legacy 与 2697 两条路
  │     └─ _CODOL_WriteServerGamestate (0xC396D)
  │           └─ _CODOL2697_WriteNativeGamestate (0xA3DAB)
  │                 ├─ gate 检查（见 §2）
  │                 ├─ _collect (0xA31F8)
  │                 └─ _CODOL2697_WriteGamestate (0xA21B8)
  │                       └─ _CODOL2697_WriteConfigstrings (0xA0468)
_SV_RecordClient (0x7910F 区) ──> _SV_WriteGameState (0x822D7)   ; 第二条 legacy 调用者
```

`_CODOL_WriteServerGamestate` RVA `0xC396D` 内部先调用 `_CODOL_Target2697ArchivesActive`：
- **未激活** → 走 legacy 路径（写旧 opcode，见 §3.5）；
- **激活** → `_CODOL_MsgWriteInit` 初始化 writer，再调 `_CODOL2697_WriteNativeGamestate`（`0xC3A81`）。

等级：**VERIFIED**（call 站点静态交叉引用）。真实“谁在何时触发”的运行时顺序为 **NOT-OBSERVED**。

`_CODOL2697_WriteNativeGamestate` 中的调用者（`e1_disasm.txt`）：

```
004a3e1d  mov  edx, 1
004a3e22  call _collect                          ; 0xA31F8
004a3e27  mov  esi, eax
004a3e29  test eax, eax
004a3e2b  jne  0x4A3E3A                          ; 收集失败 -> free 后 return 0
...
004a3e83  call _CODOL2697_WriteGamestate          ; 0xA21B8
004a3e88  test eax, eax
004a3e8a  setne al
```

`_collect` RVA `0xA31F8`：遍历 configstring（`_CODOL_GetConfigstring`，最多 `0x1977` 项），用 `_CODOL2697_MapConfigIndex` 映射索引，写入集合缓冲；再收集资源/武器配方。**只有当没有“unmapped”条目时返回 1**（VERIFIED）。`_collect` 也输出 `"CoDOL 2697 publication rows=%u aliases=%u recipes=%u unmapped=%u registration=%u\n"` 与 `"CoDOL 2697 unmapped config index %u\n"`。

### 3.2 `_CODOL2697_WriteGamestate` 的编码顺序（VERIFIED）

`_CODOL2697_WriteGamestate` RVA `0xA21B8`（0xA21B8..0xA2340）：

输入校验（任一不满足即置 `[writer+0x14]=1` 并返回 0）：
- `writer != NULL` 且 `[writer+0x14] == 0`；
- `state != NULL`，`[state+0x10]`（地图名）非空；
- 地图名字符集限制为 `[A-Za-z0-9_]`，长度上限 `0x3F`（由 `edi = 地图名+0x3F` 的边界比较实现）。

编码顺序：

| # | 指令 RVA | 写入 | 含义 |
| --- | --- | --- | --- |
| 1 | `0xA224C` | `_CODOL_WriteByte(writer, 3)` | **gamestate opcode = 0x03** |
| 2 | `0xA225A` | `_CODOL_WriteLong(writer, [state])` | 版本/序号字段 |
| 3 | `0xA2269` | `_CODOL_WriteString(writer, [state+0x10])` | 地图名（含 `\0`） |
| 4 | `0xA2279` | `_CODOL_WriteString(writer, "mp")` | 固定串 `"mp"`（RVA `0x3C0B90`） |
| 5 | `0xA2288` | `_CODOL_WriteLong(writer, [state+4])` | 字段 |
| 6 | `0xA22C1` | `_CODOL2697_WriteConfigstrings(writer, 7 参数)` | configstrings 子段 |
| 7 | `0xA22D9` | `_CODOL_WriteLong(writer, [state+0xC])` | 字段 |
| 8 | `0xA22E8` | `_CODOL_WriteLong(writer, [state+8])` | 字段 |
| 9 | `0xA22F8` | `_CODOL_WriteByte(writer, 6)` | **gamestate 终止符 = 0x06** |

返回值：`sete al`（`[writer+0x14]==0` 时为 1），即“无错误 = 成功”。

### 3.3 `_CODOL2697_WriteConfigstrings` 的编码顺序（VERIFIED）

RVA `0xA0468`，栈帧 `0x1E28`。参数校验：

- `writer != NULL`、`[writer+0x14]==0`；
- 参数1（数组）非空；参数 `[ebp+0x14] <= 0x1DD7`；`[ebp+0x1c] <= 0x7FF`；`[ebp+0x24] <= 0x3FF`。

编码顺序：

| # | 指令 RVA | 写入 | 含义 |
| --- | --- | --- | --- |
| 1 | `0xA07F8` | `_CODOL_WriteByte(writer, 4)` | **configstrings 子 opcode = 0x04** |
| 2 | `0xA0807` | `_CODOL_WriteShort(writer, [ebp+0x14])` | 主条目计数 |
| 3 | 循环 | `_CODOL_WriteString(writer, [array+ebx*8+4])` | 逐条字符串（索引经 `_index_bits`/`WriteBits` 编码） |
| 4 | `0xA085F` | `_CODOL_WriteBits(writer, [ebp+0x1C], 11)` | bits |
| 5 | 循环 | `_CODOL_WriteBits(writer, [array2+ebx*8+4], 10)` | bits |
| 6 | `0xA08BF` | `_CODOL_WriteBits(writer, [ebp+0x24], 10)` | bits |
| 7 | 循环 | `WriteBits([esi+4],10)` / `WriteBits([esi+8],7)` / `WriteBits([esi+0xC],4)`（stride 0x4C 配方记录，计数≠0 时再 12-bit 子循环） | 武器配方 |
| 8 | `0xA0997` | `_CODOL_WriteByte(writer, 6)` | **configstrings 子段终止符 = 0x06** |

返回 `sete [writer+0x14]`。

> 说明：译码辅助串 `"* %u"`(RVA `0x3C0A00`)、`"** %u %u"`(`0x3C0A05`)、`" %u"`(`0x3C0A0E`) 在构建阶段被用于 `_CODOL2697_TranslateCommand` 风格处理。

### 3.4 writer 结构布局（VERIFIED）

| 偏移 | 字段 |
| --- | --- |
| `+0x00` | 输出缓冲区指针 |
| `+0x04` | 当前写入偏移（字节+位混合游标） |
| `+0x08` | 容量 |
| `+0x10` | 位位置 |
| `+0x14` | 错误标志（非 0 = 失败） |

辅助函数：`_CODOL_WriteByte` `0x99551`、`_CODOL_WriteShort` `0x99566`、`_CODOL_WriteLong` `0x9957B`、`_CODOL_WriteBits` `0x99590`（上限 0x20 bit）、`_CODOL_WriteString` `0x99651`（`strlen+1` 后 `_CODOL_WriteData`）、`_CODOL_WriteData` `0x9949B`、`_CODOL_MsgWriteInit` `0x99292`。

### 3.5 与旧版 opcode 的对照

同一二进制内的 legacy 写函数（VERIFIED）：

| 旧函数 | RVA | 写出的 opcode |
| --- | --- | --- |
| `_CODOL_WriteGamestate`（legacy） | `0xA865A` | 起始 `0x02`（`0xA86EC`），结束 `0x05`（`0xA8769`） |
| `_CODOL_WriteConfigstrings`（legacy） | `0xA857F` | `0x03`（`0xA85B7`），终止 `0x05`（`0xA8639`） |

即：旧通道用 `0x02/0x03/0x05`；2697 新通道用 `0x03/0x04/0x06`。**两套编码同时存在于同一 EXE 中**，由 `_CODOL_Target2697ArchivesActive` 与门控决定走哪条。等级：**VERIFIED（并存）**；运行时取舍顺序为 **NOT-OBSERVED**。

## 4. 新通道是否有实际调用者（是否死代码）

| 函数 | RVA | 直接 caller 数 | caller |
| --- | --- | --- | --- |
| `_CODOL2697_WriteGamestate` | `0xA21B8` | 2 | `_CODOL2697_WriteNativeGamestate`(`0xA3E83`)；`_CODOL2697_PublicationAudit_f`(`0xA3B0B`) |
| `_CODOL2697_WriteNativeGamestate` | `0xA3DAB` | 1 | `_CODOL_WriteServerGamestate`(`0xC3A81`) |
| `_CODOL2697_WriteConfigstrings` | `0xA0468` | 1 | `_CODOL2697_WriteGamestate`(`0xA22C1`) |
| `_CODOL2697_ReadRegistration` | `0xA3EA0` | 1 | `_CODOL_SetTarget2697ServerResources`(`0xC332F`) |
| `_CODOL_WriteServerGamestate` | `0xC396D` | 1 | `_SV_WriteGameState`(`0x82396`) |

结论：新 gamestate 通道**有实际调用者，非死代码**（VERIFIED）。且其一条 caller 链最终抵达 `_SV_SendClientGameState`，是真实发送路径的一部分；`_CODOL2697_PublicationAudit_f` 是额外的一条 dry-encode 审计调用者（`+codol_checktargetpublication`）。

> 佐证：`run_native_connection.py` 的命令行以 `+codol_checktargetpublication` 结尾，说明审计入口确实被设计为可触发。

## 5. `evidence\client-registration2697.txt` 的完整判定

| 问题 | 结论 | 等级 |
| --- | --- | --- |
| 是否运行时输入 | 是，被 `fopen/sscanf/CRC32` 消费 | VERIFIED |
| 是否只供审计 | 否；它是门控放行所需的校验输入 | VERIFIED |
| 默认是否自动读取 | 否；需 CVar 指名 | VERIFIED |
| 本项目启动脚本是否指名 | 是（两个脚本都指向它） | VERIFIED |
| 内容是否与门控 `+0x6408` 直接对应 | 未直接观测到写 `+0x6408` 的指令 | 未决（见 §7） |

## 6. 证据文件清单（本阶段生成）

| 文件 | 内容 |
| --- | --- |
| `_data\e1_disasm.txt` | E1 关键函数反汇编（上一会话 + 本次） |
| `_data\e1_readreg.txt` | `_CODOL2697_ReadRegistration` 反汇编 |
| `_tools\e_common.py` | 反汇编公共库（pefile + capstone） |
| `_tools\xref.py` | 静态交叉引用扫描器（E8/E9 rel32 + 绝对 VA） |

## 7. 未决问题（BLOCKED / 待验证）

1. ~~`[registration+0x6408]` 的写入者未定位。~~ **已解决（VERIFIED）**：由 `_CODOL2697_ReadRegistration` 在栈 blob `[ebp-0x6418]`（= blob base+0x6408）写成功标志 1，再随 `memcpy` 进入全局。见 §2.2。
2. **`_collect` 返回 0 的真实概率未知。** 只要出现一个 unmapped config index，gamestate 即被 `free` 并返回 0，表现为“无输出”。运行时影响为 NOT-OBSERVED。
3. **客户端是否能读 `0x03/0x04/0x06`** 属 E4，本文件不下结论。
4. 新旧通道切换的实际时机（`_CODOL_Target2697ArchivesActive` 判定条件）仅在 E1 中确认存在分支，未逐指令展开。
