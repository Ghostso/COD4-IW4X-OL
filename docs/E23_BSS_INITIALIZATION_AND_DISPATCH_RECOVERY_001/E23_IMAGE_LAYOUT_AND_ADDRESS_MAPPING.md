# E23 映像布局与地址映射复核

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
