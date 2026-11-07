# BATTLE_RX_CALLCHAIN — 战斗接收链（目标 3.19.26.22 / 1649370）

**分析对象：** `image_best.bin`，`17cef6e0…`（10,899,456 B）
**地址约定：** `file_offset = RVA = VA - 0x400000`（证明见 `00_INDEX.md` §1）
**方法：** Capstone 线性反汇编 + `int3` 填充序言恢复 + `E8 rel32` 直接调用解析 + `push/mov imm32` 字符串交叉引用。**无插桩。**

---

## 1. TASK-009 RVA 列表：逐项复核结果（**关键否定结论**）

**来源登记：** 这些 RVA 的唯一来源是 `_e1_regression\ol-mod-olfinal\references\client_probe\CodolNetchanTrace.py`
（第 140–166 行），其声明形式为 `const X = module.base.add(0x……)`，文件头注释为
*"All RVAs below belong to the main executable"*，指向的是 **OLFinal 模块**（`out.exe`，`044c396c…`，`SizeOfImage 0x0E5D6000`），
而**不是**本机目标镜像（`SizeOfImage 0x0E659000`）。TASK-009 将该列表整体标为 "CONFIRMED"。

**本轮复核（把每个数值当作本镜像的 RVA 读取）：**

| 名称（TASK-009 标注） | RVA | 字节@RVA | 所在函数入口 | 判定 |
|---|---|---|---|---|
| packetEvent | `0x67520` | `00 6a 00 83` | `0x67260` | **非入口（中途）** |
| netchanProcess | `0x1A5960` | `c3 cc cc cc` | `0x1A5680` | **非入口（落在 ret/padding）** |
| decodeMessage | `0x6BF80` | `0c d9 5c 24` | `0x6BC60` | **非入口** |
| parseServerMessage | `0x6E6A0` | `ff ff dd d8` | `0x6E480` | **非入口** |
| parseGameState | `0x6DEA0` | `d9 e0 d9 5d` | `0x6DCF0` | **非入口** |
| parseConfigStrings | `0x6DB20` | `84 b0 01 00` | `0x6DAE0` | **非入口** |
| parseSnapshot | `0x6D170` | `83 ec 0c d9` | `0x6D060` | **非入口** |
| parsePacketEntities | `0x6C2F0` | `00 00 0f 82` | `0x6C170` | **非入口** |
| parsePacketClients | `0x6CC60` | `81 f3 7a c9` | `0x6CC40` | **非入口** |
| parsePacketAux | `0x6C840` | `df e0 dd d9` | `0x6C7F0` | **非入口** |
| **parseMatchState** | `0x6D060` | `55 8b ec 51` | `0x6D060` | **唯一命中入口**（但语义未证） |
| parsePlayerState | `0x1A4230` | `e8 52 81 69` | `0x1A41E0` | **非入口** |
| readDeltaField | `0x1A27F0` | `00 2b 05 18` | `0x1A26C0` | **非入口** |
| readDeltaEntity | `0x1A3670` | `5d c3 cc cc` | `0x1A35C0` | **非入口（落在 ret/padding）** |
| readFieldIndex | `0x1A3250` | `1b 00 eb 57` | `0x1A31A0` | **非入口** |
| readBits | `0x1A13A0` | `00 00 8b d6` | `0x1A1280` | **非入口** |
| readBit | `0x3C0C370` | — | — | **超出文件范围** |
| configChecksumCompare | `0x6E06B` | `d9 ee d9 5d` | `0x6E030` | **非入口** |
| playerStateFields | `0x855F70` | `0b d0 66 0f` | — | **非表结构**（非指针数组） |

**量化（`evidence\verify_probe_rva_for_target.py`）：**
- 探针 48 个 RVA 常量中，作为本镜像偏移**只有 1 个**落在函数序言（`parseMatchState 0x6D060`）。
- 随机基线（同区间同数量）命中 0–1 个 ⇒ **命中率与随机不可区分**。
- 常数平移假设测试：最佳平移仅 7/18 命中 ⇒ **不是简单的整体位移**。

**结论：** TASK-009 战斗链 RVA 列表**不适用于本目标**，其 "CONFIRMED" 标记**不得**在本报告沿用。
本报告后续全部结论改用**独立定位**的目标地址。

---

## 2. 独立定位方法（不依赖上述列表）

三种互相独立的定位手段，仅用本镜像自身：

1. **字符串存在性**：在本镜像中检索协议命令字面量（这些是硬事实，不受 RVA 约定影响）。
2. **绝对交叉引用**：`push imm32` / `mov reg,imm32` 中 `imm32 == 字符串 VA` ⇒ 得到引用点。
3. **序言边界恢复**：自引用点向前扫描，找到"前驱字节为 `0xCC`（int3 填充）且以 `55 8b ec` / `6a ff` / `8b ff` 开头"的位置 = 函数入口。

---

## 3. 本目标存在的战斗命令字面量（硬事实）

| 字面量 | 字符串 VA | 文件偏移 | 引用点 RVA |
|---|---|---|---|
| `getchallenge 0 "%s"` | `0x00DBFD04` | `0x009BFD04` | `0x1C071E`（`push`） |
| `challengeResponse` | `0x00DBFEE8` | `0x009BFEE8` | `0x1C1684`（`mov edx,imm32`） |
| `connectResponse` | `0x00DBFF0C` | `0x009BFF0C` | `0x1C17B4`（`mov edx,imm32`） |
| `gamestateupdate %d` | `0x00DB4700` | `0x009B4700` | `0x054B7A` / `0x073213`（`push`） |
| `heartbeat` | `0x00DBFE40` | `0x009BFE40` | `0x1C0EBB`（`push`） |
| `cancelConnect` | `0x00DBFC8C` | `0x009BFC8C` | `0x1BF25C` |
| `connect` | `0x00DC5694` | `0x009C5694` | （见 §5） |
| `userinfo "%s"` | `0x00DBFFB4` | `0x009BFFB4` | — |

证据：`evidence\xref_strings.out.txt`、`evidence\locate_local_battle_entries.out.txt`

---

## 4. OOB（连接无关包）**发送器** — 函数入口 RVA `0x1C05F0`

```
RVA 001C05F0  55                 push ebp
RVA 001C05F1  8bec               mov ebp, esp
RVA 001C05F3  b8bc110000         mov eax, 0x11bc          ; 栈帧 0x11BC — 大局部缓冲
RVA 001C05F8  e8832c6800         call 0x843280            ; __chkstk
RVA 001C0607  a1b046640700       mov eax, [0x76446b0]     ; ★ 连接状态全局
RVA 001C0611  8b0dc8c03103       mov ecx, [0x331c0c8]
RVA 001C0619  81f31f5062d3       xor ebx, 0xd362501f      ; 解密客户端对象指针
```

**状态门（进入构造前）：**
```
001C0635  83f803        cmp eax, 3
001C0638  7413          je  0x1c064d      \ 仅当状态 ∈ {3,4,5,6}
001C063A  83f804        cmp eax, 4        | 才继续；
001C0644  83f805        cmp eax, 5        | 否则 jne -> 0x1c0f1b（返回）
001C0647  0f85ce080000  jne 0x1c0f1b     /
```

**二级门（对象侧）：**
```
001C064D  85c9                 test ecx, ecx
001C0651  85db                 test ebx, ebx
001C0655  83bb6002100001       cmp dword [ebx+0x100260], 1
001C065C  0f84b9080000         je 0x1c0f1b       ; 已在某个"进行中"态 -> 直接返回
```

**节流门（对 4 个命令分支共用的计时判定）：**
```
001C0699  8b35b0466407   mov esi, [0x76446b0]
001C06A1  2b4b08         sub ecx, [ebx+8]      ; ecx = now - lastChallengeTime
001C06A6  2b4330         sub eax, [ebx+0x30]   ; eax = now - lastStateTime
001C06B3  3db80b0000     cmp eax, 0xbb8        ; 3000 ms 门（状态 3/4）
001C06B8  0f8c5d080000   jl  0x1c0f1b
001C06C9  83f964         cmp ecx, 0x64         ; 100 次/单位 门（状态 5）
001C06D3  81f9f4010000   cmp ecx, 0x1f4        ; 500 门（状态 6）
001C06D9  0f8c3c080000   jl  0x1c0f1b
```

**命令分派（`jmp [eax*4 + 0x5C0F3C]`，`eax = state - 3`）：**

| 状态 | 分支入口 | 行为（已证部分） |
|---|---|---|
| 3 | `0x1C070E` | **构造 `getchallenge 0 "%s"`**（`push 0xDBFD04` @ `0x1C071E`），`sprintf`-型 @ `0x1C0729`，随后打包对象字段 `[ebx+0x14..0x28]` 并调用发送 |
| 4 | `0x1C0776` | 走 `0x26C9B0` / `0x83C740`（字符串拷贝上限 `0x3FF`），拼 `%08x%08x` 令牌，构造另一条 OOB |
| 5 | `0x1C0E07` | `0x26E720` 取 0x800 字节，引用 `0xDBFE38`（`stats` 族），构造 |
| 6 | `0x1C0EBB` | **构造 `heartbeat`**（`push 0xDBFE40`），打包 `[ebx+0x14..0x28]` 六字段，发送 |

**另一张跳表（`jmp [eax*4 + 0x5C0F2C]`，索引为 `0x3F4F10` 的返回值）：**
`[0]→0x1C067A`（`0x1BE700` 判定失败则记 `EXE_HOSTUNREACH`）、`[1]→0x1C0F1B`（返回）、`[2]→0x1C0693`（节流主线）、`[3]→0x1C067A`。

证据：`evidence\dis_oob_full.out.txt`

---

## 5. OOB **接收/解析器** — 函数入口 RVA `0x1C13A0`

- 该函数在 `0x1C1684` / `0x1C17B4` 以 `mov edx, imm32` 引用
  `challengeResponse`（`0xDBFEE8`）与 `connectResponse`（`0xDBFF0C`）。
- 序言恢复：引用点向前最近的 `int3` 填充 + `55 8b ec` 位于 RVA `0x1C13A0`（偏移 delta = 0x2E4 / 0x414 之前）。
- **身份等级：`CONFIRMED`（字符串 + 容器函数边界）。**
- **未闭合：** 这两个响应字面量是用于**比较入站命令**还是用于**记录/日志**，本轮未判定（`UNKNOWN`）；因此"接收解析分支"本身仍为 `INFERRED`。

**`cancelConnect` 处理** — RVA `0x1BF1C0`（引用点 `0x1BF25C`），序言经 `int3` 填充恢复。
**`gamestateupdate` 引用点** — RVA `0x73180`（引用 `0xDB4700`；另一处 `0x054B7A` 所在函数未定位入口）。

---

## 6. 增量字段类型分派器 — 函数入口 RVA `0x5F830`

这是本目标内**最强**的"字段解码"证据，且**独立于** TASK-009 列表。

```
RVA 0005F830  55                 push ebp
RVA 0005F831  8bec               mov ebp, esp
RVA 0005F833  83ec18             sub esp, 0x18
RVA 0005F836  8b15583b2c08       mov edx, [0x82c3b58]        ; 本地客户端索引
RVA 0005F83F  8b149588d1c101     mov edx, [edx*4 + 0x1c1d188]; 客户端表
RVA 0005F858  81f27ac9b2fb       xor edx, 0xfbb2c97a         ; 解密
RVA 0005F85E  8955fc             mov [ebp-4], edx            ; 客户端对象
```

**内部两张分派跳表：**

| 表 | 索引表 RVA | 索引范围 | 目标表 RVA | 处理分支数 |
|---|---|---|---|---|
| A | `0x460550` | `0 .. 0x139`（314） | `0x46040C` | 81（0x00–0x50） |
| B | `0x4606E4` | `0..0x87`（136） | `0x46068C` | 22（0x00–0x15） |

- 表 A 的索引映射中，**默认项 = `0x50`（223 项）**；其余为密集低编号（0..0x4F）。
- 表 B 的索引映射中，**默认项 = `0x15`（115 项）**；有效项集中在 `0..0x0D` 与 `0x0E..0x14`。
- 代码形态：`movzx edx, byte ptr [edx + <indexTable>]` + `jmp dword ptr [edx*4 + <targetTable>]`
  （`0x5F89B` / `0x601A4`）。
- 表 A 的索引门为 `cmp edx, 0x139; ja`，表 B 为 `cmp edx, 0x87; ja`。

**调用链（`E8` 解析）：**

```
0x5F830  <--0x208432--  0x208380
0x208380 <--0x1FFB88--  0x1FF820
0x1FF820 <--0x20059B--  (0x20059B 所在函数入口本轮未定位)
0x5F830  <--0x208432--  （同上）
0x5F730  <-- 0x6010A / 0x207D63 / 0x207EFC
```

证据：`evidence\dump_typetables.out.txt`、`evidence\locate_delta_dispatcher.out.txt`、`evidence\delta_chain_context.out.txt`

---

## 7. 十字符量 `0x288` 交叉核对（与 TASK-031 对齐）

TASK-031 已证 `+0x288` 在匹配对象语境下写入 1 的唯一立即数点在 `0x63280B`。
本轮在战斗语境下扫描 `+0x288` 位移引用，未发现与战斗接收链重合的写入点；
但**本报告不把该结论外推**为"战斗链不涉及 +0x288"，因为对象基址不同（`0x288` 在多结构体中出现 86 次）。

---

## 8. 未闭合项（**不得推测**）

| 项 | 状态 |
|---|---|
| 服务端消息（0..5）opcode 分派表位置 | `UNKNOWN`（269 个 6 项跳表已扫描，无一可与 packet/netchan 语境绑定） |
| `netchanProcess` 真实入口 | `UNKNOWN`（4 个 1154 常量位点均为无关代码） |
| `decodeMessage` / `parseServerMessage` 真实入口 | `UNKNOWN` |
| OOB 接收字面量是"比较"还是"记录" | `UNKNOWN` |
| `0x20059B` 所在函数入口 | `UNKNOWN` |
| snapshot 帧边界 / delta 基线 / 实体增删 | `UNKNOWN` |

> **纪律：** 本报告不对上述任何一项给出实现建议；`SERVER_IMPLEMENTATION_GAP.tsv` 中对应行为"暂缓实现"。
