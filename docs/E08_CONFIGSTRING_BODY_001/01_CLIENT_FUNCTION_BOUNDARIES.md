# 01 — 客户端函数边界 / CLIENT FUNCTION BOUNDARIES

> 只读静态分析。未启动游戏/服务端，未注入，未读进程内存。独立工作目录 `E08_CONFIGSTRING_BODY_001`。
> 等级：`DIRECT`（直接证据）/ `CROSS`（交叉印证）/ `INFERRED`（推断）/ `BLOCKED`

---

## 1. 首个必须记录的发现：任务给出的 RVA 基准**不是客户端地址**

任务书要求"调查**客户端** RVA 0xA0807–0xA0997"。实测：

| 地址 | 服务端 `S-2697` | 客户端 `C-2697-Rec` | 客户端 `C-2697`（发行版） |
|---|---|---|---|
| RVA 0xA0468 | `.text`，**函数入口** `_CODOL2697_WriteConfigstrings` | `.text`，普通指令（`mov [0x1a8953c],1`） | `.tp3` 压缩流内 |
| RVA 0xA0807 | `.text`，`_CODOL2697_WriteConfigstrings` **函数体内部** | `.text`，**函数尾** `mov esp,ebp / pop ebp / ret / int3` | 同上 |
| RVA 0xA0997 | `.text`，同函数体内（写终止符处） | `.text`，`int3` 填充之后（无意义字节） | 同上 |

**裁定（DIRECT）：** RVA 0xA0807 与 0xA0997 是 **2697 服务端** `_CODOL2697_WriteConfigstrings`（RVA 0xA0468）**函数体内的指令偏移**，**不是**客户端函数或客户端 `_CODOL2697_WriteConfigstrings` 的地址。客户端 `0xA0468` 处的 8 条指令与服务端完全不同。

**含义：** 任务书第 1 步的"目标 RVA"应理解为 **服务端写入路径**；客户端侧必须按**行为**（位读取原语）重新定位。本报告按此执行，并保留此更正。

## 2. 地址换算（强制自检）

| 项 | 规则 |
|---|---|
| 区段表 | 存 **RVA** |
| Capstone 打印 | **VA**（`RVA = VA − ImageBase`） |
| 代码内立即数（如格式串/函数指针） | **VA** |
| 文件偏移 | `off = PointerToRawData + (RVA − VirtualAddress)` |

**自检对：** `RVA 0x1AC1D0 → off 0x1AB5D0`；`RVA 0xA2E50 → off 0xA2250`（与既有交接值一致）。
**本轮已两次因 VA/RVA 混用产生错误中间结果（见 `06`），全部已定位并改正。**

## 3. 服务端函数边界（DIRECT）

| 项 | 值 |
|---|---|
| 函数 | `_CODOL2697_WriteConfigstrings` |
| 入口 RVA | **0xA0468** |
| 返回 | RVA **0xA04E2**（`leave; ret`） |
| 栈帧 | `push ebp; mov ebp,esp; mov eax,0x1e28; call __chkstk; sub esp,eax` → 约 7.7 KB 局部缓冲 |
| 符号来源 | `_data\syms_NEW.json`（服务端符号表，符号名 `_CODOL2697_WriteConfigstrings` @ RVA 0xA0468） |
| 参数 | `[ebp+8]`=msg；`[ebp+0xC]`=A1 描述符；`[ebp+0x10]`=A1 count；`[ebp+0x14]`=count1；`[ebp+0x18]`=A2 描述符；`[ebp+0x1C]`=count2；`[ebp+0x20]`=A3 基址；`[ebp+0x24]`=count3 |
| 关键指令 | 0xA07F8 `WriteByte(4)`；0xA0807 `WriteShort(count1)`；0xA0997 `WriteByte(6)` |

**前置校验（DIRECT，RVA 0xA049B–0xA04D0）：** 若 `msg==0`、或 `msg+0x14 != 0`（已标记出错）、或 A1 指针为 0、或 `count1 > 0x1DD7`、或某记录数 `> 0x7FF`（`[ebp+0x1C]`）、或 `> 0x3FF`（`[ebp+0x24]`）→ 置 `msg+0x14 = 1` 并**返回 0**（失败）。

## 4. 服务端调用者 / 被调用者（DIRECT）

**被调用（关键）：**

| 目标 VA | RVA | 解析结果 |
|---|---|---|
| `0x499551` | 0x99551 | 包装：`ecx=1` → 核心写入器 → **写 1 字节** |
| `0x499566` | 0x99566 | 包装：`ecx=2` → **写 2 字节** |
| `0x49957B` | 0x9957B | 包装：`ecx=4` → **写 4 字节** |
| `0x499590` | 0x99590 | `MSG_WriteBits(msg,value,bitcount)`（位级） |
| `0x49949B` | 0x9949B | `MSG_WriteData(msg,ptr,len)` |
| `0x4A0400` | 0xA0400 | **索引增量写入器** `WriteIndexDelta(msg, newIdx, &lastIdx)` |
| `0x7572E0` | 0x3572E0 | `snprintf` 包装（经 `0x357292` 转发） |
| `0x765740` | 0x365740 | **IAT thunk → `msvcrt!strlen`**（已解析导入） |

**调用者（DIRECT）：** 入口由 `_CODOL2697_WriteGamestate`（RVA 0xA21B8）在 **0xA22C1** 调用（既有 E1 证据，本轮复核一致）。

## 5. 客户端侧边界（本轮重新定位，DIRECT）

客户端恢复镜像**无符号表**（COFF 符号 0，仅 22 个导出），因此客户端函数**不能按名字定位**，只能按**行为签名**定位。

**位读取原语签名（DIRECT，客户端多处出现，54 处）：**

```asm
and  ecx, 7            ; bitpos & 7
mov  edx, 1
shl  edx, cl           ; mask = 1 << (bitpos & 7)
mov  ecx, edi
shr  ecx, 3            ; bitpos >> 3   (byte index)
mov  al,  byte [buf+ecx]
test al, dl
setne al               ; → 0/1
```

**已确认的客户端读取点（DIRECT）：**

| RVA | 说明 |
|---|---|
| **0x1A07E7–0x1A0807** | 完整、自足的"读 1 位"函数：`and r,7 / shl / shr r,3 / test / setne / pop regs / leave / ret`。**入口 0x1A07B0，出口 0x1A0807。** |
| 0x510233 / 0x5103A6 / 0x510547 | 同类位读取（位于 0x5101E0 起的函数内，读 `[esi]` 缓冲 + `[esi+4]`/`[esi+6]` 位长） |
| 0x234040 / 0x2342E6 / 0x2348C8 | 同类（另一族） |
| 0x259FF4 / 0x5F0175 / 0x7874BB | 同类（其他族） |

**重要更正（针对既有档案）：** 既有 E4/E5 曾指出"客户端 `0x1AC1D0` 为 Msg 字节复制核心"。本轮确认它是**按字节复制**（`movzx byte [ecx+eax]`），**不含位域逻辑** —— 与位读取是**两个不同原语**。位读取在**别处**（上表）。

## 6. 客户端函数边界限制（BLOCKED 项）

| 限制 | 影响 |
|---|---|
| 客户端无符号表/无 PDB | 无法给出函数名，只能给地址与行为签名 |
| `.text` 内含 `int3` 与不可解码字节 | 线性扫描必须**重同步**（本轮已采用，2,892,767 条指令） |
| `.tvm0` 入口对齐率 0%（见 E-06） | `.tvm0` 内的读取器**不能**线性确认 |
| 无运行时 | 无法确认哪个候选函数**实际**在 configstring 路径上被调用 |

## 7. 结论

| 结论 | 等级 |
|---|---|
| RVA 0xA0807/0xA0997 属**服务端**函数体，非客户端函数 | **DIRECT** |
| 服务端 `_CODOL2697_WriteConfigstrings` 边界 = 0xA0468..0xA04E2 | **DIRECT** |
| 服务端写入原语族（1/2/4 字节 / WriteBits / WriteData / 索引增量）已定位 | **DIRECT** |
| 客户端存在**同构的 LSB-first 位读取原语**（54 处，含一个自足函数 0x1A07B0） | **DIRECT** |
| 客户端 `0x1AC1D0` 是**字节**读取，**非**位读取 | **DIRECT** |
| 客户端哪个函数消费 configstring body | **BLOCKED**（无运行时、无符号） |