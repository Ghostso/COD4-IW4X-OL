# E2 — CODOL 2697 Snapshot 与 EOF `0x06` 静态追踪

> 分析日期：2026-10-12  
> 范围：仅静态反汇编、PE 读取、交叉引用与已有派生素材；未运行服务端/客户端，未注入，未编译，未修改样本。  
> 结论等级：`VERIFIED`（二进制指令直接支持）、`STATIC-INFERENCE`（有依据的语义解释）、`NOT-OBSERVED`（无运行时/互通观测）、`BLOCKED`（当前样本或工具不足）。

## 1. 样本身份与工具

| 项目 | 值 | 证据 |
|---|---|---|
| 服务端样本 | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe` | 本任务复核 |
| SHA-256 | `80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1` | `Get-FileHash` 复核，与任务给定值一致：`VERIFIED` |
| 文件大小 | `7,295,919` 字节 | 本任务复核：`VERIFIED` |
| ImageBase | `0x400000` | `_tools\e_common.py` + `syms_NEW.json` 读取：`VERIFIED` |
| 分析方式 | Capstone 32 位反汇编、E8/E9 rel32 扫描、绝对 VA 扫描、PE 区段/符号 JSON | 只读派生分析 |
| 本次派生输出 | `07_PROTOCOL_BIDIRECTIONAL_TRACE\_data\e2_snapshot_trace_20261012.txt` | 可复现实验数据 |

本报告中的函数 RVA 均相对服务端 ImageBase `0x400000`。旧遗留函数名如 `_CODOL_WriteSnapshotDeltaNumber` 是符号 JSON 中的既有命名，不据此直接断言旧版实际运行路径。

## 2. 函数边界与参数

### 2.1 `_CODOL2697_WriteSnapshot` RVA `0xA4FA0`

**函数边界：`0xA4FA0`–`0xA4FFD`（含 `ret`；后接两个 `nop`）。**

反汇编直接显示它是薄包装函数，不自行构造 writer、不检查资源注册门控，也不写 `0x06`：

```asm
004a4fa0  push ebp
004a4fa1  mov  ebp, esp
004a4fa3  sub  esp, 0x2c
004a4fa6  mov  dword ptr [esp+0x28],0
004a4fae  mov  dword ptr [esp+0x24],0
004a4fb6  mov  dword ptr [esp+0x20],0
004a4fbe  mov  dword ptr [esp+0x1c],0
004a4fc6  mov  dword ptr [esp+0x18],0
004a4fce  mov  eax,[ebp+0x1c]
004a4fd1  mov  [esp+0x14],eax
004a4fd5  mov  eax,[ebp+0x18]
004a4fd8  mov  [esp+0x10],eax
004a4fdc  mov  eax,[ebp+0x14]
004a4fdf  mov  [esp+0xc],eax
004a4fe3  mov  eax,[ebp+0x10]
004a4fe6  mov  [esp+8],eax
004a4fea  mov  eax,[ebp+0xc]
004a4fed  mov  [esp+4],eax
004a4ff1  mov  eax,[ebp+8]
004a4ff4  mov  [esp],eax
004a4ff7  call 0x4a4860              ; _CODOL2697_WriteSnapshotReached
004a4ffc  leave
004a4ffd  ret
```

调用者通过栈传入的 6 个可见参数被原样转发；包装器在 `0xA4FA6`–`0xA4FC6` 清零 5 个**额外的可选输出/状态指针槽**，因此 `_CODOL2697_WriteSnapshotReached` 实际接收：

- `arg0`（`[ebp+8]`）：writer 指针；
- `arg1`（`[ebp+0xc]`）：主 snapshot/history 输入结构；
- `arg2`（`[ebp+0x10]`）：第二输入或比较结构；
- `arg3`（`[ebp+0x14]`）：额外输入；
- `arg4`（`[ebp+0x18]`）：flags/参数；
- `arg5`（`[ebp+0x1c]`）：序号/序列参数；
- 包装器补入的 `arg6..arg10`：均为 0（对应 `[ebp+0x20]`、`+0x24`、`+0x28`、`+0x2c`、`+0x30` 的额外输出指针）。

**结论：`VERIFIED`。** 参数个数、转发关系和包装边界由上述指令直接支持。

### 2.2 `_CODOL2697_WriteSnapshotReached` RVA `0xA4860`

**函数边界：`0xA4860`–`0xA4F9D`/`0xA4F9E` 附近（尾部分支返回，随后 `0xA4FA0` 为新函数）。** 函数入口使用 `0x6690` 字节栈帧（`___chkstk_ms`，`0xA4869`–`0xA4873`），并分配多处内部缓冲区。

入口校验（`VERIFIED`）：

```asm
004a4875  mov ebx,[ebp+8]            ; writer
004a4878  test ebx,ebx
004a487a  je 0x4a48cb                ; 失败返回 0
004a487c  cmp dword ptr [ebx+0x14],0 ; writer error
004a4880  jne 0x4a48b7
004a4882  cmp dword ptr [ebp+0x1c],0 ; arg5 必须非空
004a4886  je 0x4a48b7
004a4888  cmp dword ptr [ebp+0xc],0  ; arg1 必须非空
004a488c  je 0x4a48b7
004a488e  mov eax,[ebp+0xc]
004a4891  mov esi,[eax+4]
004a4894  test esi,esi
004a4896  je 0x4a48bc
004a4898  mov ecx,[eax]
004a489a  lea eax,[ecx-1]
004a489d  cmp eax,0x1ffffffe
004a48a2  seta dl
004a48a5  cmp dword ptr [ebp+0x18],0xff
004a48ac  seta al
004a48af  or dl,al
004a48b1  mov [esp+0x2f],dl
004a48b5  je 0x4a48d8
```

后续继续校验 `arg1+0x10 <= 0x7ff`（`0xA48D8`）、`arg1+0x18 <= 0x20`（`0xA48E5`）、`arg1+0x20 <= 0x20`（`0xA48F0`），并在 `arg1+0x14` 与 `arg1+0xc` 存在性之间做条件检查。`arg1+0x18` 为零时需要 `arg1+0x14`；`arg1+0x10` 为零时需要 `arg1+0xc`。

`arg2`（`[ebp+0x10]`）存在时还要求：

- `arg2+4 != 0`；
- `arg2[0] < arg1[0]` 且 `arg2[0] != 0`；
- flags 的 `bit 3` 未置位（`0xA4930` `test byte [ebp+0x18],8`）；
- `arg1[0] - arg2[0] <= 0x1f`（`0xA4936`–`0xA493D`）。

上述检查失败时，`0xA48B7` 将 `esi` 置零并走 `0xA48BC` 的 `_free`，随后 `0xA48C4` 将 `writer+0x14` 置 1（错误标志），最终返回 0。入口 writer 为空时直接返回 0，不设置错误。**这些是函数内部快照对象参数校验，不是 E1 的 resources/registration 门控。**

## 3. 写入顺序、分段与 `0x06`

### 3.1 调用顺序（`VERIFIED`）

从 `0xA4860` 到 `0xA4E90` 的实际 `call` 顺序如下（只列带符号的主要调用）：

| 顺序 | 调用点 RVA | 被调函数 | 作用/证据 |
|---:|---|---|---|
| 0 | `0xA486E` | `___chkstk_ms` | 分配大栈帧 |
| 1 | `0xA48BF` | `_free` | 失败清理路径 |
| 2 | `0xA495D` | `_CODOL_WriteByte` | 参数 0：初始分段/长度字段路径 |
| 3 | `0xA496E` | `_CODOL_WriteLong` | `arg5` 派生序号 |
| 4 | `0xA497A` | `_CODOL_WriteByte` | 长度/字段 |
| 5 | `0xA4989` | `_CODOL_WriteByte` | flags/参数 |
| 6 | `0xA49A1` | `_CODOL_WriteBits` | 布尔/位域 |
| 7 | `0xA49DA` | `_CODOL_WriteByte` | 另一分支的初始 `0` |
| 8 | `0xA49EB` | `_CODOL_WriteLong` | 序号 |
| 9 | `0xA49FB` | `_CODOL_WriteByte` | 长度/字段 |
| 10 | `0xA4A0A` | `_CODOL_WriteByte` | flags/参数 |
| 11 | `0xA4A28` | `_CODOL_WriteBits` | 布尔/位域 |
| 12 | `0xA4A57` | `_CODOL2697_WritePlayerFields` | 玩家字段 |
| 13 | `0xA4A82` | `_malloc` | 分配 `count*0x1F8` 临时数组 |
| 14 | `0xA4AA3` | `_CODOL_WriteByte` | 临时数据头 |
| 15 | `0xA4AB4` | `_CODOL_WriteLong` | 序号 |
| 16 | `0xA4AC0` | `_CODOL_WriteByte` | 长度 |
| 17 | `0xA4ACF` | `_CODOL_WriteByte` | flags |
| 18 | `0xA4AED` | `_CODOL_WriteBits` | 位域 |
| 19 | `0xA4B25` | `_CODOL2697_WritePlayerFields` | 第二遍/基准备份玩家字段 |
| 20 | `0xA4B5C` | `_CODOL2697_WritePlayerArrays` | 玩家数组 |
| 21 | `0xA4B89` | `_CODOL2697_WriteAnimations` | 动画/命令 |
| 22 | `0xA4BD8` | `_CODOL2697_WriteActors` | Actors 第一遍 |
| 23 | `0xA4C1F` | `_CODOL2697_WriteEntities` | Entities 第一遍 |
| 24 | `0xA4C63` | `_CODOL2697_WriteClients` | Clients |
| 25 | `0xA4C97` | `_CODOL_WriteGlass` | Glass |
| 26 | **`0xA4CAF`** | **`_CODOL_WriteByte`，参数 `6`** | **`0x06` 写入** |
| 27 | `0xA4CEE` | `_CODOL2697_ReachHud` | HUD 到达/回写区域 |
| 28 | `0xA4D4B` | `_CODOL2697_WriteActors` | Actors 第二遍（另一分支） |
| 29 | `0xA4D99` | `_CODOL2697_WriteEntities` | Entities 第二遍（另一分支） |
| 30 | `0xA4DF4` | `_CODOL2697_ReachClient` | Clients 到达/回写区域 |
| 31 | `0xA4EBB` | `_memcpy` | 将 `0x728` 字节复制到可选输出 |
| 32 | `0xA4EDF` | `_memcpy` | 将 `0x2C38` 字节复制到可选输出 |
| 33 | `0xA4F3F` | `_memcpy` | 将 `count*0x1F8` 字节复制到可选输出 |
| 34 | `0xA4F61` | `_memcpy` | 将 `count*0x13C` 字节复制到可选输出 |
| 35 | `0xA4F7D` | `_memcpy` | 将 `count*0x5C` 字节复制到可选输出 |
| 36 | `0xA4F17` / `0xA4F8E` | `_free` | 临时数组清理 |

`0xA4CAF` 的精确上下文为（`VERIFIED`）：

```asm
004a4c97  call _CODOL_WriteGlass
004a4c9c  test eax,eax
004a4c9e  je   0x4a48bc             ; WriteGlass 失败则走错误清理
004a4ca4  mov  dword ptr [esp+4],6   ; 参数 = 6
004a4cac  mov  dword ptr [esp],ebx   ; writer
004a4caf  call _CODOL_WriteByte       ; 写一个 0x06
004a4cb4  cmp  dword ptr [ebx+0x14],0 ; 检查 writer error
004a4cb8  jne  0x4a48bc
```

`_CODOL_WriteByte` 的实现符号位于 `0x499551`，这里不把符号名当作未经验证的语义；调用点直接显示“第二参数为 6”，因此写入的字节值是 `0x06` 本身。写前没有为这次调用单独计算长度，长度/缓冲状态由 writer 在 `_CODOL_WriteByte` 内维护；写后立即读取 `writer+0x14` 错误标志。**`VERIFIED`：写入值为 6，紧邻 `_CODOL_WriteGlass` 成功之后。**

### 3.2 0x06 之后仍有同 writer 的写入

同一函数在 `0xA4CAF` 之后继续：

- `0xA4CEE`：`_CODOL2697_ReachHud`，第一参数是 `[esp+0x3330]` 栈缓冲区，不是刚才的 writer；
- `0xA4D4B`：`_CODOL2697_WriteActors(writer, ...)`；
- `0xA4D99`：`_CODOL2697_WriteEntities(writer, ...)`；
- `0xA4DF4`：`_CODOL2697_ReachClient`，参数含 `[esp+0xbb0]` 与累计偏移；
- `0xA4EBB` 等：把函数内多个区域复制到调用者提供的输出指针。

其中 `0xA4D4B` 与 `0xA4D99` 的第一参数明确仍是 `ebx`（writer），说明 `0xA4CAF` 之后 writer 仍被用于后续 Actors/Entities 写入；这不是“写入最后一个字节后函数只做清理”的结构。  
**`STATIC-INFERENCE`：`0xA4CAF` 是内部子段/阶段终止 token，而不是整条网络消息的最后一个字节。** 该推断由“之后仍用同一 writer 写入 Actors/Entities”直接支持；仅凭 0x06 常量本身不能证明客户端语义。

### 3.3 多子段/段的连接方式

从调用顺序和参数看，函数至少包含以下几类连续区域：

1. 初始字段/位域区（`0xA495D`–`0xA49A1`）；
2. 另一分支的初始字段区（`0xA49DA`–`0xA4A28`）；
3. `_CODOL2697_WritePlayerFields` 玩家字段；
4. `_CODOL2697_WritePlayerArrays`；
5. `_CODOL2697_WriteAnimations`；
6. `_CODOL2697_WriteActors`（第一遍）；
7. `_CODOL2697_WriteEntities`（第一遍）；
8. `_CODOL2697_WriteClients`；
9. `_CODOL_WriteGlass`；
10. `0x06`；
11. `_CODOL2697_ReachHud`、第二遍 Actors/Entities、`_CODOL2697_ReachClient`；
12. 多个 `_memcpy` 将 `0x728`、`0x2C38`、`count*0x1F8`、`count*0x13C`、`count*0x5C` 复制到输出。

这些区域可能是内部快照对象中的不同子缓冲/到达区域，不能仅凭调用顺序断言每个区域都在网络 wire 上独立成帧。关于“子段如何在客户端侧重新连接”的结论为 `BLOCKED`（需 E4 客户端游标/解码分析）。

## 4. Writer 状态与长度计算

在 `0xA4860` 中可稳定观察到 writer `ebx` 的字段：

| writer 偏移 | 在 E2 中的使用 | 证据 |
|---|---|---|
| `+0x14` | 错误标志；`cmp [ebx+0x14],0`，非零走失败清理 | `0xA487C`、`0xA4CB4`、`0xA48C4` |
| `+0x10` | 写前被清 0（如 `0xA494B`、`0xA49C8`、`0xA4A91`） | `VERIFIED` |
| `+0x0` / `+0x4` | 由 `WriteByte`/`WriteLong`/`WriteBits` 的实现自行维护 | `STATIC-INFERENCE`；E2 未展开通用 writer 实现 |

`_CODOL_WriteByte` 在 `0xA4CAF` 被调用时传入 `writer` 和常量 `6`。E2 没有在 A4860 中看到针对这次 `0x06` 的显式长度字段或显式长度回填指令；`0x06` 的长度效果是 `WriteByte` 的直接 1 字节写入。  
**`VERIFIED`：写入点、写入值、writer 错误检查位置。**  
**`BLOCKED`：`0x06` 是否在客户端协议中承载额外长度/版本语义，当前仅靠服务端 A4860 不能完成。**

### 4.1 与 E1 gamestate/configstring 中的 0x06 区分

旧阶段和 E1 已确认：

- `_CODOL2697_WriteGamestate`（RVA `0xA21B8`）尾部有 `0x06`；
- `_CODOL2697_WriteConfigstrings`（RVA `0xA0468`）尾部有 `0x06`；
- E2 的 A4860 在 `WriteClients/WriteGlass` 后写 `0x06`。

这三个位置不能自动合并成“同一层级的 EOF”。`A4860` 的 `0x06` 在写后仍继续调用 `WriteActors/WriteEntities` 与 `ReachClient`，更符合内部子段/阶段划分；gamestate 与 configstring 的对应语义仍沿用 E1 的独立证据。**结论：局部重复的 `0x06` 值不能单独证明协议层语义一致性。**

## 5. 调用者证据

### 5.1 `_CODOL2697_WriteSnapshotReached` 的直接调用点

当前 E8/E9 rel32 扫描结果（`VERIFIED`）：

| 被调 RVA | 直接调用点 | 调用者 | 说明 |
|---|---|---|---|
| `0xA4860` | `0xA26EB` | `_CODOL2697_PrepareHistory` | 构造 history/snapshot 对象后调用 |
| `0xA4860` | `0xA4FF7` | `_CODOL2697_WriteSnapshot` | 薄包装转发 |

`_CODOL2697_PrepareHistory` 的入口为 `0xA249D`，其调用前构造了约 `0x33A8` 字节对象：

- `_malloc` 分配 `count*0x1F8`、`count*0x13C`、`count*0x5C` 暂存区；
- 将 `arg1` 结构前 `0x34` 字节及 `+0x80` 等状态复制到对象；
- 在对象中初始化 `+4`、`+8`、`+0xc`、`+0x14`、`+0x1c`、`+0x24`、`+0x28`、`+0x2c`、`+0x80` 等偏移；
- `0xA26EB` 调 `WriteSnapshotReached` 后，如果返回非零，将对象 `+0x80` 设为新状态并把 `arg5` 输出区回填，最后返回 1。

**`VERIFIED`：PrepareHistory 确实调用 A4860，且 A4860 的输出/状态会被回写到 history 对象。**
**`STATIC-INFERENCE`：PrepareHistory 是 snapshot/history 的生产者或提交路径。**

### 5.2 `_CODOL2697_WriteSnapshot` 的直接引用搜索

当前扫描范围：

- `.text` 段内所有 `E8`（call rel32）；
- `.text` 段内所有 `E9`（jmp rel32）；
- 全文件绝对 VA 引用 `0x400000+0xA4FA0` 及 RVA 形式 `0xA4FA0`。

结果：**搜索范围未命中**。  
这只能写成“在本版 PE、当前扫描范围、当前符号/指令解码条件下没有找到直接调用或绝对引用”，**不能写成“该函数不存在”或“永远不会被调用”**。可能原因包括但不限于：

- 调用者位于 E8/E9 扫描未覆盖的结构（如通过寄存器/跳转表间接调用、经导出/回调表调用）；
- 调用点被优化成跳转或包装器；
- 当前符号 JSON 给出的函数边界不包含相关入口；
- 扫描未覆盖重定位、虚拟/填充区、间接 thunk 或运行时解密后的代码。

### 5.3 两条根链的证据状态

1. **根链 A：`_CODOL2697_PrepareHistory 0xA249D` → `WriteSnapshotReached 0xA4860`**
   - `A4860` 的直接调用关系：`VERIFIED`；
   - PrepareHistory 的完整上层调用者：当前 E8/E9 搜索未命中；
   - 因此其实际运行时可达性：`BLOCKED`，不能仅凭符号名断言它已用于在线 snapshot 发布。

2. **根链 B：`_CODOL2697_WriteSnapshot 0xA4FA0` → `WriteSnapshotReached 0xA4860`**
   - 包装转发关系：`VERIFIED`；
   - `0xA4FA0` 的直接调用/绝对引用：当前搜索范围未命中；
   - 因此其实际运行时可达性：`BLOCKED`，不能断言“新通道已实际调用”或“只是不存在”。

PrepareHistory 与 WriteSnapshot 两条根链在**当前证据层**是“可达性未闭合”的静态候选，而不是已被证实正在使用的生产路径。

## 6. 与 delta 写入函数的关系

### 6.1 2697 delta 函数

符号表中存在：

- `_CODOL2697_WriteDeltaValue` RVA `0xA0A9C`；
- `_CODOL2697_ReachDeltaValue` RVA `0xA0FD7`；
- `_CODOL_SetDeltaPositionBase` RVA `0xA8E8F`；
- `_CODOL_WriteDeltaValue` RVA `0xA8F29`；
- `_CODOL_ReachDeltaValue` RVA `0xA9BF1`。

E8/E9 扫描显示 `0xA0A9C`、`0xA0FD7`、`0xA8F29`、`0xA9BF1` 均有多个调用点，说明 delta 值/到达处理在二进制中确有代码使用，但它们是否由 `A4860` 主干直接调用，当前没有被 E2 调用序列捕获。  
**`STATIC-INFERENCE`：这些函数属于 snapshot 数据字段的 delta 编码/到达辅助层；不是 A4860 的独立网络消息头。** 该判断依据是函数名、参数中的 writer/位宽/值字段，以及调用点分布；未做完整运行时路径绑定。

### 6.2 旧 legacy 快照写入函数

旧遗留符号：

- `_CODOL_WriteSnapshotFailure` RVA `0xBE940`；
- `_CODOL_WriteSnapshotDeltaNumber` RVA `0xBE946`；
- `_CODOL_WriteSnapshot` RVA `0xBEE15`。

在 `_CODOL_WriteSnapshotDeltaNumber` 中直接观察到：

- 初始 writer 清零路径：`0xAEA00` 前的 `mov [esp+4],0`，随后调用 `_CODOL_WriteByte`（地址 `0xAEA0B`）；
- “reached/到达”路径：`0xAECBF` 将参数设为 `5`，随后调用 `_CODOL_WriteByte`（地址 `0xAECCD`）。

这支持旧版研究记录中的“`0x00`、`0x05`”写入分支，但**不是** A4860 的 `0x06`。`_CODOL_WriteSnapshot`（`0xBEE15`）也调用 `_CODOL_WriteSnapshotDeltaNumber`，而 `_CODOL_WriteSnapshotDeltaNumber` 的调用者当前扫描为 `0xBEE91`、`0xC1A53`。  
**`VERIFIED`：旧 legacy 函数中有 0x00/0x05 写入。**  
**`STATIC-INFERENCE`：旧版与 2697 版可能采用不同的快照终止/到达标记编码。** 当前没有足够证据证明旧版运行时也走同一分支，也没有证明两版客户端对它们的读取完全一致。

## 7. 内部消息到 `_SV_SendMessageToClient` / `_SV_Netchan_Transmit`

### 7.1 `_SV_EndClientSnapshot`（RVA `0x86F7D`）的 0x05/0x06 选择

`0x87104` 附近指令（`VERIFIED`）：

```asm
00487104  call 0x540133              ; _CODOL_Target2697ArchivesActive
00487109  cmp  eax,1
0048710c  mov  eax,5
00487111  sbb  eax,-1                ; 5-(-1)-CF：CF=1 得 5；CF=0 得 6
00487114  mov  [esp+4],eax
00487118  mov  [esp],edi
0048711b  call 0x42B40A              ; _MSG_WriteByte
00487120  jmp  0x487016
```

按 `cmp eax,1` 后 `sbb eax,-1` 的语义：

- `eax < 1`（未激活/非目标 2697）：`cmp eax,1` 置 CF=1，`sbb eax,-1` 得 `eax = 5 - (-1) - 1 = 5`；
- `eax >= 1`（2697 archives active）：`cmp eax,1` 置 CF=0，`sbb eax,-1` 得 `eax = 5 - (-1) = 6`。

结合上下文，该分支在 `_SV_EndClientSnapshot` 中向 `edi` 指向的 `Msg` 写一个字节：**2697 archives 激活时写 `0x06`，未激活/非目标时写 `0x05`**（以当前反汇编的算术结果为准）。这与 A4860 内部 `0x06` 不是同一写入点，说明服务端至少在两个层级存在 `0x06` 常量：内部 snapshot 子段/阶段标记与快照结束时的 Msg 终止/到达标记之一。

**`VERIFIED`：`0x87104` 处的条件算术和 `_MSG_WriteByte` 调用。**
**`STATIC-INFERENCE`：该字节是快照外层 Msg 的结束/到达标记。**
**`NOT-OBSERVED`：客户端是否按相同条件区分 0x05/0x06。**

### 7.2 发送调用链

当前 E8/E9 交叉引用结果（`VERIFIED`）：

```text
_SV_SendMessageToClient 0x86B06
  ├─ 被 _SV_SendClientGameState 0x7110C 调用
  └─ 被 _SV_EndClientSnapshot  0x87073 调用
       ├─ _SV_EndClientSnapshot 0x86F7D ← _SV_SendClientSnapshot 0x8743C
       └─ _SV_EndClientSnapshot 0x86F7D ← _SV_SendClientMessages 0x8AB4E
            └─ _SV_SendClientMessages 0x8A9F1 ← _SV_Frame 0x84158
```

在 `_SV_SendMessageToClient` 内，`0x86BCC` 调用 `_SV_Netchan_Transmit`：

```asm
00486bc2  mov eax,[edi+8]
00486bc5  mov [esp+4],eax
00486bc9  mov [esp],ebx              ; client
00486bcc  call 0x4856B6              ; _SV_Netchan_Transmit
```

`_SV_SendMessageToClient` 还对 `client+0x380` 非零情况调用 `_SV_DropClient`，并在发送前后保存/恢复 netchan 状态字段。**`VERIFIED`：内部 Msg 参数通过 `_SV_SendMessageToClient` 到 `_SV_Netchan_Transmit` 发送。**

### 7.3 缓冲区边界

- E2 的 `A4860` 写入目标是 `arg0` 传入的 writer；`A4FA0` 只是转发并补零可选输出。
- `_SV_EndClientSnapshot` 的 `0x87104` 写入目标是其参数 `edi` 的 `Msg`，随后 `0x87073` 调 `_SV_SendMessageToClient(edi, client)`。
- `_SV_SendMessageToClient` 最终把该 Msg 和 client 参数交给 `_SV_Netchan_Transmit`。

因此静态边界为：**A4860 内部 writer 产生的字节最终必须由上层组装/复制到 `_SV_EndClientSnapshot` 的 Msg；`_SV_SendMessageToClient`/`_SV_Netchan_Transmit` 处理的是 netchan 外层的发送对象，而不是 A4860 的原始栈缓冲区本身。**  
**`VERIFIED`：调用链和参数传递方向。**  
**`BLOCKED`：A4860 内部区域到 `_SV_EndClientSnapshot` Msg 的逐字节复制点；当前 E2 未找到一条闭合的 `A4860 → PrepareHistory/WriteSnapshot → _SV_EndClientSnapshot` 运行时调用链。**

## 8. 与旧版 `0x05/0x00` 记录的区分

| 项目 | 旧版记录/当前证据 | 2697 E2 证据 | 当前结论 |
|---|---|---|---|
| delta/snapshot 初始标记 `0x00` | legacy `_CODOL_WriteSnapshotDeltaNumber 0xBE946` 有写 0 的路径 | A4860 初始字段路径也调用 `WriteByte(0)`，但 A4860 另有 `0x06` | 相同值不能自动等同相同 wire 位置；`STATIC-INFERENCE` |
| legacy 到达标记 `0x05` | `0xBE946` 的 `0xAECBF` 附近写 5 | `_SV_EndClientSnapshot 0x87104` 在 archives inactive 时按算术可得到 5 | 两处一个是 legacy 快照函数，一个是 Msg 结束分支；不可直接合并：`VERIFIED` 写入，`STATIC-INFERENCE` 语义 |
| 2697 新 `0x06` | 旧记录未把它作为旧版 A4860 证据 | A4860 `0xA4CAF` 写 6，且写后仍有 writer 调用 | 新路径内部标记：`VERIFIED` 写入 + `STATIC-INFERENCE` 子段语义 |
| 外层 archives-active 选择 | 旧记录为 `0x05` | `0x87104` 的 2697 archives 条件分支 | 服务端选择关系：`VERIFIED`；客户端一致性：`NOT-OBSERVED` |

**明确保留：** 不能把 A4860 的 `0x06` 直接套用到旧版 `_CODOL_WriteSnapshotDeltaNumber` 的 `0x00/0x05` 记录上。旧版记录仍然只是历史静态记录，除非找到对应的旧版调用链和客户端读取证据。

## 9. 客户端对照（E2 仅做必要复核）

任务要求 E2 不越权下结论客户端支持 `0x06`。当前 E2 侧仅记录：

- E2 没有在当前服务端证据之外直接证明 2.6.9.7 客户端读取 A4860 的 0x06；
- `_SV_EndClientSnapshot` 的 0x05/0x06 写入点位于服务端；
- 客户端读取、游标推进、长度检查和终止循环属于 E4（客户端分派）主线，本报告不把“服务端写入”写成“客户端已读取”。

**客户端 0x06 支持：`NOT-OBSERVED`。**  
**客户端 0x05/0x06 语义差异：`BLOCKED`，需 E4 的客户端反汇编证据。**

## 10. 结论汇总

### 10.1 已直接验证

1. 服务端样本 SHA-256 与 ImageBase 复核通过。  
2. `_CODOL2697_WriteSnapshot 0xA4FA0` 是 `_CODOL2697_WriteSnapshotReached 0xA4860` 的薄包装，边界清楚，补零 5 个输出槽。  
3. `A4860` 的入口/参数校验、主要调用顺序、writer `+0x14` 错误检查路径已反汇编确认。  
4. `0xA4CAF` 在 `_CODOL_WriteGlass` 成功后写入字节 `6`，写入后同一 writer 继续用于 Actors/Entities 等路径。  
5. `A4860` 的直接调用点为 `0xA26EB`（PrepareHistory）和 `0xA4FF7`（WriteSnapshot 包装器）。  
6. `_SV_EndClientSnapshot 0x87104` 根据 `_CODOL_Target2697ArchivesActive` 的返回值选择写 `0x05` 或 `0x06`：未激活/非目标时写 `0x05`，2697 archives 激活时写 `0x06`；随后 `_SV_SendMessageToClient` 在 `0x86BCC` 调 `_SV_Netchan_Transmit`。  
7. legacy `0xBE946` 函数中存在写 `0/5` 的分支，可与旧版历史记录对照，但不能混同 A4860 的 0x06。

### 10.2 静态推断

1. A4860 的 `0x06` 是内部子段/阶段终止 token，而不是整条网络消息的最终 EOF。  
2. PrepareHistory 与 WriteSnapshot 是 snapshot/history 生产者/提交候选路径；其运行时使用状态尚未闭合。  
3. `_SV_EndClientSnapshot` 的 0x05/0x06 是快照外层结束/到达标记。  
4. delta 函数属于 snapshot 字段编码/到达辅助层，而不是独立网络头。

### 10.3 未观测/阻塞

1. **`NOT-OBSERVED`**：A4860 的 `0x06` 在 2.6.9.7 客户端中的读取、游标推进和终止语义。
2. **`NOT-OBSERVED`**：客户端是否把 `_SV_EndClientSnapshot` 的 0x05/0x06 当作相同终止/到达标记处理。
3. **`BLOCKED`**：`A4860 → PrepareHistory/WriteSnapshot → _SV_EndClientSnapshot → Msg` 的逐字节装填点和运行时调用链未闭合。
4. **`BLOCKED`**：`0xA4FA0` 的直接调用在当前 E8/E9 与绝对 VA 扫描中未命中；不能断言该新路径已经被使用，也不能断言不存在调用者。
5. **`BLOCKED`**：`A4860` 内部各输出区域（`0x728`、`0x2C38`、`count*0x1F8`、`count*0x13C`、`count*0x5C`）到 netchan 外层消息的完整拼接顺序未由当前静态证据闭合。

## 11. 可复现实验摘要

```text
样本：
D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe
SHA-256=80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1
ImageBase=0x400000

关键 RVA：
0xA4FA0  _CODOL2697_WriteSnapshot
0xA4FF7  call _CODOL2697_WriteSnapshotReached
0xA4860  _CODOL2697_WriteSnapshotReached
0xA26EB  call _CODOL2697_WriteSnapshotReached (PrepareHistory)
0xA4CA4  mov [esp+4],6
0xA4CAC  mov [esp],ebx
0xA4CAF  call _CODOL_WriteByte
0x87104  call _CODOL_Target2697ArchivesActive
0x87109  cmp eax,1
0x8710C  mov eax,5
0x87111  sbb eax,-1
0x8711B  call _MSG_WriteByte
0x86BCC  call _SV_Netchan_Transmit

扫描结果：
E8/E9 call refs of 0xA4FA0  = 搜索范围未命中
absolute VA refs of 0xA4FA0 = 搜索范围未命中
E8/E9 call refs of 0xA4860  = 0xA26EB, 0xA4FF7
```

报告完。