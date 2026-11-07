# -*- coding: utf-8 -*-
from pathlib import Path
OUT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E23_BSS_INITIALIZATION_AND_DISPATCH_RECOVERY_001")
files={}

files["E23_EXECUTIVE_SUMMARY.md"]=r'''# E23 执行摘要

## 一句话结论

`0xA85AD0`、`0xA85BE0`、`0xA85640`、`0xA87830`、`0xA878A0` 是五个**以 VA（ImageBase=0x400000）记法**的普通 `.text` 函数（RVA 分别为 `0x685AD0`、`0x685BE0`、`0x685640`、`0x687830`、`0x6878A0`）；E-22 将其判为 `.data` BSS 虚拟尾部是**地址基准（VA/RVA）误用**，三个是缓冲区 Range/Advance 辅助、两个是帧缓冲读取辅助，`[edi+0x5F4]` 成功路径调用可归约为"协商对象（vtable `0xC5A31C`）的 slot+3 字节流提交"。

## 关键事实

1. 五个地址按 **VA** 口径全部落在 `.text`（`VA 0x00001000..0x007AD90B`），有真实磁盘字节、可线性反汇编；只有在按 **RVA** 口径解释时才会落入 `.data`（`VA 0x8F1000`，RawSize `0x49600`）的 BSS 虚拟尾部。
2. E-22 的机器可读中间产物与 E-21 自述均把这些值写作 **VA**（例如 `call 0xA85AD0`、`call 0xa878a0`），其"BSS 无字节"结论来自把 VA 当成 RVA 查询节区映射。
3. 按 VA 重算 rel32 得到的真实调用点：
   - `0xA85AD0`：`0x6AC168`（位于 `0x6AC0C0` 内，解析消息码）
   - `0xA85640`：`0x6AC22C`、`0x6A5CCA`（共 36 处）
   - `0xA85BE0`：`0x6AC2BC`、`0x6AC37B` 等（共 96 处）
   - `0xA87830`：125 处
   - `0xA878A0`：96 处（含 `0x6AAEF4`、`0x6AAF22`）
4. 函数语义（`.text`，非 BSS）：
   - `0xA878A0`（`0x6878A0`）：计算 span = `[ebp+0x10]+[ebp+0x1c]` 写回 `[ebp+0x14]`，越界则日志 `0x43A7C0`，否则 `memcpy`（`0xB49B40`）。
   - `0xA87830`（`0x687830`）：同类 Range 辅助，输出 24 字节结构。
   - `0xA85640`（`0x685640`）：thiscall 字段分派，`ret 8`，跳转 `.tvm0` 入口 `0xDF6F97C`。
   - `0xA85BE0`（`0x685BE0`）：thiscall 字段分派，`ret 4`，跳转 `.tvm0` 入口 `0xDF6F97C`。
   - `0xA85AD0`（`0x685AD0`）：`0xA878A0` 的簿记封装，`ret`（cdecl）。
5. 初始化来源：**TLS 回调为空**（数据目录 `AddressOfCallBacks` 指向的 `.rdata` 数组首元素为 0）、**`.rimp` 无任何目标地址引用**、无静态构造器写入——因为它们是普通 `.text` 代码，根本不需要"加载期写入 BSS"。
6. `[edi+0x5F4]`：字段由 `0x6AB9B3`/`0x6AB9E7` 写入（值 `0` 或构造对象指针），对象由 `0x6AB9D8`/`0x6AB9DA`（`call 0xA87BA0`）构造，vtable `0xC5A31C`；成功路径 `0x6AB14E` 取 slot+3 = `0xA87D50` 并用 4 个栈参数调用。

## 逐项裁定

| 地址 | VA → RVA | 所属节区 | 裁定 |
|---|---|---|---|
| 0xA85AD0 | 0x685AD0 | .text | CONFIRMED-CODE-FUNCTION（`0xA878A0` 封装） |
| 0xA85BE0 | 0x685BE0 | .text | CONFIRMED-CODE-FUNCTION（字段分派，`ret 4`） |
| 0xA85640 | 0x685640 | .text | CONFIRMED-CODE-FUNCTION（字段分派，`ret 8`） |
| 0xA87830 | 0x687830 | .text | CONFIRMED-CODE-FUNCTION（Range/memcpy，24B 输出） |
| 0xA878A0 | 0x6878A0 | .text | CONFIRMED-CODE-FUNCTION（Range 写回/memcpy） |

## `[edi+0x5F4]` 是否得到解释

是。`[edi+0x5F4]` 持有"协商/参数对象"指针，其 vtable 为 `0xC5A31C`；成功路径调用该对象 slot+3（`0xA87D50`），参数形如 `(this, buf, buf, len)`。该对象是 `.text` 对象，与五个目标**同属一族**（`0xA87xxx`/`0xAA8xxx`），**不再**是 E-22 所述"无磁盘字节的 BSS 虚表"。

## 被证伪/更正的关联假设

- **E-22「五地址位于 `.data` BSS 虚拟尾部」→ REFUTED（基准错误）**；正确为 `.text`。
- E-21「`0xA85AD0` 属 `.tvm0`」→ 仍为 REFUTED（正确为 `.text`）。
- E-22「I4 加权完备率 33.33%（I4 权重 96）」→ 与权威 XVAL-02 账本（I4=104）冲突，判为账目口径错误；正确为 32/104 = 30.77%。
- 新增 REFUTED：五个辅助函数**不是**"加载期被写入 BSS 的隐藏分派表"，而是被大量静态调用点（共 1+36+96+125+96 = 354 处）直接调用的普通函数。

## 阻塞项

- `0xA87830` 的 `[ebp+0x18]` 24 字节输出结构字段语义（部分见 `0x6B95C0` 写入 `0xffffffff`）。
- `0xA87D50` slot+3 的 4 个缓冲区参数语义与握手状态机的对应关系。
- 消息码 `0x81/0x83/0x84/0x85` 与出/入站方向的最终绑定。

## 下一步唯一建议

解析调用点 `0x6AB9D8` 的交叉引用，确定 `[edi+0x5F4]` 协商对象的创建时机与调用者，从而闭合握手状态机——这是唯一能在静态范围内进一步收敛的边界。
'''

files["E23_IMAGE_LAYOUT_AND_ADDRESS_MAPPING.md"]=r'''# E23 映像布局与地址映射复核

## 冻结样本

| 样本 | 路径 | SHA-256 | 核对 |
|---|---|---|---|
| 恢复镜像（客户端） | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin` | `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4` | 与冻结值一致 |

- ImageBase = `0x400000`，SizeOfImage = `0x0DC14000`，OptionalHeader.Magic = `0x010B`（PE32）。
- 本轮地址口径：报告地址若为 **VA**，则 RVA = VA − ImageBase。

## 节区表（实测）

| 节区 | VirtualAddress | VirtualSize | PointerToRawData | SizeOfRawData | VA 范围 | 可否磁盘反汇编 | 可执行 |
|---|---|---|---|---|---|---|---|
| .text | 0x00001000 | 0x007AC90B | 0x00000400 | 0x007ACA00 | 0x001000..0x7AD90B | 是 | 是 |
| .rdata | 0x007AE000 | 0x00142880 | 0x007ACE00 | 0x00142A00 | 0x7AE000..0x8F0880 | 是 | 否 |
| .data | 0x008F1000 | 0x0D05C420 | 0x008EF800 | 0x00049600 | 0x8F1000..0xD94D420 | 仅前 0x49600 字节 | 否（BSS 尾） |
| .tls | 0x0D94E000 | 0x00000019 | 0x00938E00 | 0x00000200 | 0x0D94E000..0x0D94E019 | 是 | 否 |
| .rsrc | 0x0D94F000 | 0x00008DF8 | 0x00939000 | 0x00008E00 | 0x0D94F000..0x0D957DF8 | 是 | 否 |
| .tvm0 | 0x0D958000 | 0x002B9000 | 0x00941E00 | 0x002B8C00 | 0x0D958000..0x0DC11000 | 是 | 是 |
| .rimp | 0x0DC11000 | 0x00002964 | 0x00BFAA00 | 0x00002A00 | 0x0DC11000..0x0DC13964 | 是 | 否 |

`.data` 的 VirtualSize（`0x0D05C420`）远大于 SizeOfRawData（`0x00049600`）：`RVA 0x8F1000+0x49600 = 0x93A600` 之后为 loader 零填的 BSS 虚拟尾部（约 208 MB）。

## 数据目录（实测）

| 目录 | RVA | Size |
|---|---|---|
| EXPORT | 0x008F03C0 | 0x000004C0 |
| IMPORT | 0x0DC11000 | 0x00000168 |
| RESOURCE | 0x0D94F000 | 0x00008DF8 |
| DEBUG | 0x007B3400 | 0x0000001C |
| TLS | 0x008D7E00 | 0x00000018 |
| IAT | 0x007AE000 | 0x000006E0 |

注意：IMPORT 目录 RVA 落在 `.rimp`（`0x0DC11000`），即恢复镜像把导入目录重建在 `.rimp` 区。

## 五个目标地址的两种解释（决定性对照）

| 报告地址 | 若按 VA 解释 → RVA | 节区（VA 口径） | 有磁盘字节 | 若按 RVA 解释 → 节区 |
|---|---|---|---|---|
| 0x00A85AD0 | 0x00685AD0 | .text | 是（raw_off 0x684ED0） | .data（BSS，无字节） |
| 0x00A85BE0 | 0x00685BE0 | .text | 是（raw_off 0x684FE0） | .data（BSS，无字节） |
| 0x00A85640 | 0x00685640 | .text | 是（raw_off 0x684A40） | .data（BSS，无字节） |
| 0x00A87830 | 0x00687830 | .text | 是（raw_off 0x686C30） | .data（BSS，无字节） |
| 0x00A878A0 | 0x006878A0 | .text | 是（raw_off 0x686CA0） | .data（BSS，无字节） |

**裁定**：五个地址是 **VA**，映射进 `.text`。E-22 的 `.data` BSS 结论来自把 VA 值当作 RVA 去查节区表。

## 地址基准误用的证据链

1. **调用点存在性**：对 `.text` 中所有 `E8`(call rel32) 重新按 `target = insn_VA + 5 + rel` 计算，得到在 `.text` 内、且指令边界对齐（由前导 `0xCC` 填充反推起点后线性反汇编验证）的调用点共 354 处：
   - `0xA85AD0`：1；`0xA85640`：36；`0xA85BE0`：96；`0xA87830`：125；`0xA878A0`：96。
2. **指针形式扫描**：全文件对五个地址的 VA 形式（如 `D0 5A A8 00`）与 RVA 形式（如 `D0 5A 68 00`）做 4 字节精确扫描，几乎全部为 0 次命中——说明它们**不以数据指针形式存在于 `.rdata/.data/.rimp`**，仅以 `call rel32` 立即数（运行时计算）形式出现，这与"普通被调用函数"一致，与"分派表项/BSS 指针目标"不一致。
3. **反汇编一致性**：五个 RVA 处均以 `55 8B EC`（`push ebp; mov ebp,esp`）标准序言开始，并以 `ret`/`ret N` 结束，无 `int3` 破口。

## 与历史交付物的差异

- E-21：称 `0xA85AD0`、`0xAAB260`、`0xAAB310` 属 `.tvm0`（VM 混淆区）。
- E-22：把 `0xA85AD0`、`0xA85BE0`、`0xA85640`、`0xA87830`、`0xA878A0` 改判为 `.data` BSS 虚拟尾部。
- E-23（本轮）：两者均不成立；五个地址为 `.text` 函数。E-21/E-22 的定性均保留原文，本轮新增更正记录。
'''

files["E23_INITIALIZATION_SOURCE_CLOSURE.md"]=r'''# E23 初始化来源闭包

本文件对每个目标给出：已闭合的写入者集合、已闭合的引用者集合、间接调用、未解析项、结论状态与支持地址。

术语等级（严格递增，沿用任务书 §三）：
1. **引用**：地址被作为操作数出现。
2. **写入**：存在向该地址存值的指令。
3. **写值可确定**：写入值可静态求值。
4. **写值被用作代码指针**：写值确实被间接调用。
5. **调用约定/参数独立支持**。

## 目标总览

| 目标（VA） | RVA | 节区 | 引用者（rel32 call） | 间接调用 | 静态写入者 | 结论 |
|---|---|---|---|---|---|---|
| 0xA85AD0 | 0x685AD0 | .text | 1（`0x6AC168`） | 否 | 无（代码，非数据） | CODE-CONFIRMED |
| 0xA85BE0 | 0x685BE0 | .text | 96 | 否 | 无 | CODE-CONFIRMED |
| 0xA85640 | 0x685640 | .text | 36 | 否 | 无 | CODE-CONFIRMED |
| 0xA87830 | 0x687830 | .text | 125 | 否 | 无 | CODE-CONFIRMED（输出结构语义 BLOCKED） |
| 0xA878A0 | 0x6878A0 | .text | 96 | 否 | 无 | CODE-CONFIRMED |

**关键点**：这五个是**代码**，因此"写入者集合为空"是**正常**（不是缺陷），"无加载期初始化"也不是缺陷。E-22 之所以需要"BSS 写入者"，前提是它们为数据目标；前提已被推翻。

## 0xA85AD0（RVA 0x685AD0）

- 序言/尾声：`55 8B EC` … `5D C3`（cdecl）。
- 引用者（唯一）：`0x6AC168`（`0x6AC0C0` 内的"解析消息码"步）。
- 调用序列（`0x6AC150..0x6AC16D`）：压入 `ebx`（帧缓冲）、`edi`（有效长）、`0`、`&[ebp-0x14]`、`&[ebp-0x0E]`，`add esp,0x14` 平衡 5 个参数。
- 函数体：以相同 5 参调用 `0xA878A0`，将 `[ebp-1]` 经 `[ebp+0x18]` 回写，并返回 `AL`。
- 未解析：`[ebp-0x0E]`/`[ebp-0x14]` 在调用者中的最终用途（消息码/偏移）。
- 状态：**CODE-CONFIRMED**；调用约定 cdecl（5 参数，调用方清栈）。

## 0xA85BE0（RVA 0x685BE0）

- 序言/尾声：`55 8B EC` … `ret 4`（thiscall，this=ECX，1 个栈参数）。
- 语义：`cmp [ebp+8],-1` → 走 `0xA855A0` 取默认值；否则 `push 8`（字段标签）→ `0xA85490`（对象字段分派）→ `push 4` + `&[ebp+8]` + `this` → `call 0xDF6F97C`（`.tvm0` VM 入口）。
- 引用者：96 处（含 `0x6AC2BC`、`0x6AC37B`），`add esp,4` 表明 1 个栈参数、thiscall。
- 状态：**CODE-CONFIRMED**；参数为"字段标签(8)" + "32 位值"。

## 0xA85640（RVA 0x685640）

- 序言/尾声：`55 8B EC` … `ret 8`（thiscall，this=ECX，2 个栈参数）。
- 语义：`and edi,ebx` 判断掩码对；`cmp eax,-1` → `0xA855A0`；否则 `push 0xA`（字段标签 10）→ `0xA85490` → `push 8` + `&[ebp+8]` + `this` → `call 0xDF6F97C`（`.tvm0`）。
- 引用者：36 处（含 `0x6AC22C`、`0x6A5CCA`），`add esp,8` 表明 2 个栈参数、thiscall。
- 状态：**CODE-CONFIRMED**；参数为"字段标签(10)" + "64 位掩码对（低/高）"。

## 0xA87830（RVA 0x687830）

- 序言/尾声：`55 8B EC` … `5D C3`（自由函数，6 个栈参数，`ret`）。
- 语义：`span = [ebp+0x10] + [ebp+0x1c]` 写入 `[ebp+0x14]`；若两端非空且 span 越过 `[ebp+0xc]` → 日志 `0x43A7C0`；否则 `call 0xB49B40`（= `memcpy`），源 `[[ebp+8]+[ebp+0x10]]`，长 `[ebp+0x1c]`。
- 引用者：125 处（含 VM/渲染路径）。
- 未解析：`[ebp+0x18]` 指向的 24 字节输出结构字段语义（部分线索见 `0x6B95C0` 写入 `0xffffffff`）。
- 状态：**CODE-CONFIRMED**；输出结构语义 **BLOCKED**。

## 0xA878A0（RVA 0x6878A0）

- 序言/尾声：`55 8B EC` … `5D C3`（自由函数，6 个栈参数，`ret`）。
- 语义：与 `0xA87830` 同族，`[ebp+0x14]` 接收 span 尾指针；越界日志，否则 `memcpy`。
- 引用者：96 处（含 `0x6AAEF4`、`0x6AAF22`）。
- 状态：**CODE-CONFIRMED**；函数签名（6 参、内联 memcpy）已独立验证。

## 证据边界

- 引用者集合仅覆盖 `.text` 内 `E8` rel32 调用（对五个地址共 354 处，全部通过边界对齐校验）。未覆盖 `E9`/`FF /2` 等间接形式，但对"地址作为立即数"的函数入口而言，`E8` 已是主集合。
- 未发现任何向五个地址**写入**的指令，因为它们是代码；对数据指针表的形式扫描（VA/RVA 4 字节）也近乎 0 命中。
- 无间接调用证据：没有位置把这五个地址作为"从内存加载再 `call`"的目标。
'''

for name,content in files.items():
    (OUT/name).write_text(content,encoding="utf-8")
    print("wrote",name,len(content))
