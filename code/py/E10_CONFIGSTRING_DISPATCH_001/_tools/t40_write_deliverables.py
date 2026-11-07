import os, hashlib, json
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E10_CONFIGSTRING_DISPATCH_001"
# ---------- 01 CALLER INVENTORY ----------
files={}
files["01_A2660_CALLER_INVENTORY.md"]=r"""# 01 — 0xA2660 调用者清单 / CALLER INVENTORY

> 只读静态分析。未启动游戏、未注入、未读取进程内存、未修改原始样本。
> 样本身份：客户端 `codoMP_client_shipRetail.exe` SHA256 `353754047DBBFE3AFBF6C7D97DE3FACA785B3D5D5E34A9053C820EE78814D6E1`
> 恢复镜像：`codol2697-static-candidate.bin`，ImageBase `0x400000`，`.text` RVA `0x1000`。
> 等级：`DIRECT`（指令级）/ `CROSS`（两侧印证）/ `INFERRED` / `BLOCKED`

---

## 1. 复核方法（不沿用 E-09 结论，重新枚举）

| 步骤 | 方法 | 产物 |
|---|---|---|
| S1 | 对客户端 `.text` 全节做带重同步的线性扫描 | `_tools/t01_xref_scan.py`、`_work/client_callgraph.pkl` |
| S2 | 指令级枚举 `call/jmp` 即时目标 == VA `0x4A2660` | `_data/out_t01_xref.txt` |
| S3 | 独立字节模式扫描 `E8/E9 rel32`（覆盖反汇编对齐漏点） | 同上 `byte_rel32_hits` |
| S4 | 全镜像扫描等于 VA `0x4A2660` 的数据指针 | 同上 `data_pointer_hits` |

**扫描规模：** 指令 2,892,767 条；`call/jmp` 即时边 181,983 条；函数入口候选 23,187 个。

## 2. 完整调用点枚举（全量，无省略）

| # | 调用点 RVA | 指令 | 原始字节 | 目标 | 所属函数（入口） | 类别 |
|---|---|---|---|---|---|---|
| C1 | `0x3514F0` | `call 0xA2660` | `E8 6B 11 D5 FF` | `0xA2660` | `0x3512A0` | 直接 `call` |
| C2 | `0x352FA7` | `jmp 0xA2660` | `E9 B4 F6 D4 FF` | `0xA2660` | `0x352F80` | 尾跳转（**不是 0x352E80**） |
| C3 | `0x352FB4` | `jmp 0xA2660` | `E9 A7 F6 D4 FF` | `0xA2660` | `0x352F80` | 尾跳转（同上函数另一分支） |

- 指令级命中：**3**
- `E8/E9 rel32` 字节级命中：**3**（与指令级完全一致，无额外漏点）
- 数据指针命中：**0**

**结论（DIRECT）：** `0xA2660` 的直接调用点总数为 **3**，分布在 **2 个函数**中：`0x3512A0` 1 处、`0x352F80` 2 处。

## 3. 对既有报告地址的更正（追加，不覆盖）

| 既有表述 | 本轮复核 | 依据 |
|---|---|---|
| E-09：调用者为 `0x3512A0` 与 `0x352E80` | **函数边界误判**：C2/C3 位于 `0x352F80`，不是 `0x352E80` | `0x352F80` 为独立入口，`0x352E80` 在 `0x352F2A` 已 `ret`，二者之间有 `int3` 填充 |
| E-09：调用点 3 个 | 数量正确，但归属应为 `0x3512A0` ×1 + `0x352F80` ×2 | 同上 |

## 4. 每个调用点的调用目标核对

| 调用点 | 调用目标 | 核对结果 |
|---|---|---|
| `0x3514F0` | `0x4A2660`（VA） | 目标坐标正确（RVA `0xA2660`） |
| `0x352FA7` | `0x4A2660`（VA） | 目标坐标正确 |
| `0x352FB4` | `0x4A2660`（VA） | 目标坐标正确 |

**三条边的目标全部一致且唯一（DIRECT）。** 无第四个调用点，也无数据指针引用。

## 5. 原始证据

- 指令级/字节级/数据指针三路结果：`_data/out_t01_xref.txt`、`_data/out_t01_xref.json`
- 指令总数：`_data/out_t01_insn_count.txt`
- 生成脚本：`_tools/t01_xref_scan.py`

## 6. 结论

| 问题 | 裁定 |
|---|---|
| `0xA2660` 直接调用点数量 | **3**（PROVEN） |
| 是否有 `0x352E80` 直接调用 `0xA2660` | **否**（REFUTED，E-09 归属错误） |
| 是否有间接/数据指针调用 | 数据指针命中 **0**（DIRECT 范围内无） |
"""

# ---------- 02 OUTER DISPATCH CALLGRAPH ----------
files["02_OUTER_DISPATCH_CALLGRAPH.md"]=r"""# 02 — 外层分派调用图 / OUTER DISPATCH CALLGRAPH

> 从 3 个调用点向上反向追踪。等级：`DIRECT` / `INFERRED` / `BLOCKED`

---

## 1. 调用链总图（DIRECT 边）

```
[消息/数据流源]
      |
      +-- (P1) 0x3512A0 ──call──> 0xA2660 @0x3514F0
      |        ^  callers: 0x34E7C0 @0x34E945
      |        |           0x3519F0 @0x351A02 (jmp)
      |        |           0x351A10 @0x351A22 (jmp)
      |
      +-- (P2) 0x352F80 ──jmp──> 0xA2660 @0x352FA7 / @0x352FB4
               ^  caller: 0x354100 @0x3546F3
                        ^  caller: 0x3547D0 @0x354809
                                 ^  caller: 0x350170 @0x350238
```

## 2. 调用者 A：`0x3512A0`

| 项 | 值 | 等级 |
|---|---|---|
| 函数入口 | RVA `0x3512A0` | DIRECT |
| 进入 0xA2660 的边 | `call 0x4A2660` @ `0x3514F0` | DIRECT |
| 调用前状态 | `lea ecx,[esp+0x28]`（构造局部 msg 结构），`call 0x352570` 读入 4 字节 | DIRECT |
| 0xA2660 参数 | ECX = `[esp+0x28]` 局部结构 | DIRECT |
| 返回后动作 | `call 0x352FC0` → `call 0x3530E0` → `call 0x3532F0` → `call 0x3537D0` | DIRECT |
| 上级调用者 | `0x34E7C0@0x34E945`、`0x3519F0@0x351A02`、`0x351A10@0x351A22` | DIRECT |
| 本函数内对 `0x04`/`0x06` 的显式比较 | **无** | DIRECT（否定） |

**判读：** 该路径是“**先读一段数据 → 送 0xA2660 解析 Configstring body → 再跑收尾流程**”的消费路径。`0x352570` 以长度参数读取字节（`push 4` @0x351433），说明入参不是 1 字节 opcode 直接比较。

## 3. 调用者 B：`0x352F80`（E-09 误标为 `0x352E80`）

| 项 | 值 | 等级 |
|---|---|---|
| 函数入口 | RVA `0x352F80` | DIRECT |
| 进入 0xA2660 的边 1 | `jmp 0x4A2660` @ `0x352FA7`（先 `inc [esi+0x1c]`） | DIRECT |
| 进入 0xA2660 的边 2 | `jmp 0x4A2660` @ `0x352FB4`（越界分支） | DIRECT |
| 唯一上级 | `0x354100@0x3546F3` | DIRECT |
| 关键前导 | `0x3546BF call 0x1AC190`（MSG_InitReadOnly）→ 读 4 字节长度 → 读载荷 → 调 0x352F80 | DIRECT |
| 跳过 1 字节 | `0x352FA1 inc eax / 0x352FA2 mov [esi+0x1c],eax`，即**读指针前进 1 字节后才进入 0xA2660** | DIRECT |

**判读：** 该路径在进入 `0xA2660` 前**恰好跳过 1 个字节**。按服务端布局，这个被跳过的字节就是 Configstring 外层 `0x04`。但该 shim 本身**没有对该字节做值比较**。

## 4. 上层大分派器：`0x354100`（9 项跳转表）

| 项 | 值 | 等级 |
|---|---|---|
| 入口 | RVA `0x354100` | DIRECT |
| 分派键 | `movzx eax, byte [ebp+0xc]` → `cmp eax,8` → `jmp [eax*4+0x7547AC]` | DIRECT |
| 跳转表位置 | RVA `0x3547AC`（VA `0x7547AC`） | DIRECT |
| 表项数 | 9（case 0..8） | DIRECT |
| case 0 | `0x35416A` 读 1 字节 → 格式化输出 | DIRECT |
| case 1 | `0x3541C4` 读 4 字节 → 存 float | DIRECT |
| case 2 | `0x354200` 读 1 字节 | DIRECT |
| case 3 | `0x354264` 读 1 字节（含 `cmp byte [..],0` 布尔判断） | DIRECT |
| case 4 | `0x354366` 读 1 字节 | DIRECT |
| case 5 | `0x354468` 读 4 字节 → 再读 4 字节 | DIRECT |
| **case 6** | **`0x354697` → 初始化 msg → 读 4 字节长度 → 读载荷 → `0x352F80` → `0xA2660`** | **DIRECT** |
| case 7 | `0x354740` 写 1 字节 | DIRECT |
| case 8 | `0x354766` 读 4 字节 | DIRECT |
| 键来源 | `0x3547D0` 读 1 字节并排除 `0x09`/`0x0A` 后传入 | DIRECT |

**关键（DIRECT）：** **Configstring body 路径对应 case 6，而不是 case 4。** case 4 只读 1 字节，随后按 `[ebp+0x10]` 分支做 3-float 拷贝，与 Configstring 字段无关。

## 5. 选择器 / 外层循环：`0x3547D0`

| 项 | 值 | 等级 |
|---|---|---|
| 入口 | RVA `0x3547D0` | DIRECT |
| 读取 | `push 1 / call [esi+0x89244]` 读 1 字节到 `[ebp-4]` | DIRECT |
| 终止值 | 读到 `0x09` 或 `0x0A` 时跳出（`cmp al,9` / `cmp al,0xA`） | DIRECT |
| 分派 | 其它值以 `push 1; push eax; push edi; call 0x354100` 传入 | DIRECT |
| 循环 | `0x354801` 起循环，直到终止值 | DIRECT |
| 上级 | `0x350170@0x350238`、`0x3512A0@0x351569` | DIRECT |

**重要限定（DIRECT）：** 该读 1 字节的键**没有与服务端写入的 `0x04` 做值比较**；它只排除 `0x09`/`0x0A`。因此**不能**把 `0x354100` 的 case 编号直接等同于服务端外层 `0x04`。

## 6. 0x04 的层归属分析

| 候选 | 证据 | 裁定 |
|---|---|---|
| 服务端 `0x04` 是 Configstring 外层标识 | 服务端 `0x99551(4)` @ `0xA07F8`（WriteByte，1 字节） | **DIRECT** |
| 客户端 `0x354100` case 4 = 外层 `0x04` | **无任何值比较证据**；case 4 读 1 字节且语义为 3-float | **REFUTED** |
| 客户端 `0x352F80` 跳过 1 字节 = 跳过外层 `0x04` | `inc [esi+0x1c]` @0x352FA1–0x352FA2，紧接进入 `0xA2660` | **INFERRED（强）** |
| 客户端存在显式 `cmp ... 4` 校验外层 `0x04` | 在路径1/路径2/分派器/body reader 四个区域内**未命中** | **BLOCKED** |

**结论：** 外层 `0x04` 的**分派位置**未能以值比较形式直接证明；能证明的是“进入 body reader 前恰好前进 1 字节”。因此外层 `0x04` 分派裁定为 **BLOCKED**（但最小证据缺口已缩小到 `0x354100` case 6 与 `0x3547D0` 的键语义）。

## 7. .tvm0

`.tvm0` 未出现在本调用链的任何直接 `call/jmp` 边上（C1–C3 全部落在 `.text` 原生区）。按任务 A 第 5 条，**不对 `.tvm0` 做深入分析**。
"""

# ---------- 03 OPCODE 04 VERDICT ----------
files["03_OPCODE_04_DISPATCH_VERDICT.md"]=r"""# 03 — 外层 0x04 分派裁定 / OPCODE 0x04 DISPATCH VERDICT

---

## 1. 裁定

| 问题 | 裁定 |
|---|---|
| 外层 `0x04` 分派是否 PROVEN | **BLOCKED** |
| 是否找到直接证明外层 `0x04` 分派的指令或数据流 | **否** |
| 是否找到等价（强 INFERRED）证据 | **是**（进入 body reader 前固定前进 1 字节） |

**按任务 A 第 4 条保留 BLOCKED。**

## 2. 服务端侧（DIRECT）

```asm
0A07E6  mov dword [edi+0x10], 0      ; bitpos = 0
0A07ED  mov dword [esp+4], 4
0A07F5  mov [esp], edi
0A07F8  call 0x499551                ; WriteByte(msg, 4)  —— 1 字节
0A07FD  mov eax, [ebp+0x14]
0A0807  call 0x499566                ; WriteShort(count1, 2 字节)
```

`0x99551` 内 `mov ecx,1` → `0x994FC` → `MSG_WriteData(len=1)`，因此 **`0x04` = 1 字节整字节写（DIRECT）**。

## 3. 客户端候选：三条调用点

| 调用点 | 进入前状态 | 是否显式比较 0x04 |
|---|---|---|
| `0x3514F0`（`0x3512A0`） | 先 `0x352570` 读 4 字节；`0xA2660` 用其局部 msg | **无** |
| `0x352FA7`（`0x352F80`） | `inc [esi+0x1c]`（+1 字节）后进入 | **无** |
| `0x352FB4`（`0x352F80`） | 越界分支，同样 +1 后进入 | **无** |

## 4. 关键等价链（INFERRED，强）

```
0x354697 (case 6)
  → 0x1AC190 MSG_InitReadOnly(buf, 0x20000)
  → 读 4 字节长度
  → 读该长度载荷
  → 0x3546F3 call 0x352F80
        → 0x352FA1 inc eax
        → 0x352FA2 mov [esi+0x1c], eax     ; 消息游标 +1
        → 0x352FA7 jmp 0xA2660             ; body reader
```

服务端：`0x04`(1B) → `count1`(2B) → body。
客户端：进入 `0xA2660` 时游标已 +1，随后 `0xA26B2` 读 2 字节 `count1`（DIRECT）。

**两侧互补（CROSS）：** 客户端恰好跳过 1 字节，与服务端 1 字节 `0x04` 位置一致。

## 5. 为什么仍不能升级为 PROVEN

| 缺口 | 说明 |
|---|---|
| 无 `cmp [byte], 4` | 客户端在该层未见值校验；跳过的字节内容未被静态验证 |
| 分派键语义未定 | `0x3547D0` 的 1 字节键与服务端 `0x04` 的对应关系未由常量比较证明 |
| case 编号 ≠ opcode | `0x354100` 的 case 0..8 是内部枚举值，非 wire 字节 |

## 6. 最小新增证据

| ID | 缺口 | 最小证据 | 需要授权 |
|---|---|---|---|
| G-04-1 | 外层 `0x04` 分派 | `0x3547D0` 读取值的取值范围/生产者，或 case 6 键与 `0x04` 的常量比较 | 否（纯静态） |
| G-04-2 | 跳过字节内容 | `0x352F80` 进入前缓冲区内该字节的写入者 | 否（纯静态） |
"""

# ---------- 04 TERMINATOR 06 ----------
files["04_TERMINATOR_06_READ_PATH.md"]=r"""# 04 — 0x06 读取路径 / TERMINATOR 0x06 READ PATH

---

## 1. 裁定

| 问题 | 裁定 |
|---|---|
| `0x06` 读取路径 | **BLOCKED** |
| `0x06` 位宽 | **BLOCKED** |
| `0x06` 字节对齐 | **BLOCKED** |
| `0x06` 终止语义 | **BLOCKED** |

服务端写入侧为 DIRECT；客户端读取侧在本轮静态范围内**未定位**。

## 2. 候选位置（按消息层级分开登记，禁止合并）

| 上下文 | 服务端写入点 | 层 | 客户端读取 | 裁定 |
|---|---|---|---|---|
| Configstring 尾 | `WriteByte(6)` @ `0xA0997` | 服务端 message | **未定位** | BLOCKED |
| Gamestate 尾 | `WriteByte(6)` @ `0xA22F8` | 服务端 message | **未定位** | BLOCKED |
| Snapshot 内标记 | `0xA4CAF` | snapshot 内部 | **未定位** | BLOCKED |
| Snapshot 外层选择器 | `0x87104`（0x05/0x06） | outer selector | **未定位** | BLOCKED |

## 3. 服务端 Configstring 尾（DIRECT）

```asm
0A098C  mov dword [esp+4], 6
0A0994  mov [esp], edi
0A0997  call 0x499551        ; WriteByte(msg, 6)
0A099C  cmp dword [edi+0x14], 0
0A09A0  sete al
```

`0x99551` 内 `mov ecx,1` → `0x994FC`，`len=1`。因此服务端侧至少可证：**写入 1 字节、值为 6、并且是 Configstring 体结束后的第一个写入**。

## 4. 客户端读取搜索（本轮）

| 搜索 | 范围 | 结果 |
|---|---|---|
| `0xA2660` 全函数 | RVA `0xA2660..0xA2975` | 读完 A3 段 `dec/jne` 后直接 `ret` @0xA2975；**无 0x06 读取** |
| `0x3532F0` 收尾读端 | 读 1 字节后 `cmp ecx,0x81` | 是另一标记（0x81），**非 0x06** |
| 直接 `cmp == 4 / 6` 定值 | `0x350000..0x360000`、`0xA2000..0xA3000` | 命中 **0** |
| `0x1AC670 MSG_ReadBits` 调用点 | 全节 126 处 | 其中 `0xA2660` 6 处全部为字段位读取，无 0x06 判定 |
| `0x1AC1D0 MSG_ReadData` 调用点 | 全节 25 处 | `0xA2660` 仅 `0xA26B2`（count1=2B）；`0xA2DC1` 属另一函数 `0xA2D91` |

**说明：** E-09 曾把 `0xA2DC1` 当作 `0xA2660` 内第二处读点，本轮按函数边界复核：`0xA2D91` 是独立入口（`push ebp` @0xA2D91），不属于 `0xA2660`。

## 5. 5. 字段宽度 / 字节对齐 / 终止语义 三分离

| 属性 | 服务端 | 客户端 | 结论 |
|---|---|---|---|
| 字段宽度 8 bit | `WriteByte(6)`：`0x99551 ECX=1` 路径（1 字节） | **无读取证据** | 服务端 DIRECT；端到端 BLOCKED |
| 字段起始按字节对齐 | 服务端 `[msg+0x10]=0` @0xA07E6 将 bitpos 归零，之后按字节写 | **无读取证据** | 服务端 DIRECT；端到端 BLOCKED |
| 字段具有终止语义 | 写点紧跟 body，且是结束写入 | **无读取证据** | 服务端 DIRECT；端到端 BLOCKED |

**纪律：** 以上三行**不得互相推导**。8 bit 不能推出对齐；对齐不能推出终止。

## 6. 最小新增证据

| ID | 缺口 | 最小证据 | 授权 |
|---|---|---|---|
| G-06-1 | Configstring 尾 `0x06` 读取点 | 客户端在 `0xA2660` 返回后的调用者里对 1 字节的常量比较 | 否 |
| G-06-2 | 对齐语义 | 读取原语是否使用 bitpos 或字节游标 | 否 |
| G-06-3 | 终止语义 | 读到 6 后的循环退出/消息结束分支 | 否 |
| G-06-4 | 端到端互通 | 原始帧字节 | **是** |
"""

# ---------- 05 BIT ALIGNMENT ----------
files["05_BIT_ALIGNMENT_RECONSTRUCTION.md"]=r"""# 05 — 位/字节对齐重建 / BIT ALIGNMENT RECONSTRUCTION

---

## 1. 服务端侧位记账（DIRECT，指令级）

### 1.1 msg 结构字段

| 偏移 | 语义 | 证据 |
|---|---|---|
| `[msg+0]` | 缓冲区指针 | `0x9949B` |
| `[msg+4]` | 字节计数 used | `add [ebx+4],eax` @0x994DD |
| `[msg+8]` | 容量 | `0x9949B` |
| `[msg+0x10]` | 位位置 bitpos | `MSG_WriteBits` |
| `[msg+0x14]` | 溢出标志 | `0x994C8` |

### 1.2 关键重同步（DIRECT）

```asm
09960A  test byte [edi+0x10], 7      ; bitpos % 8 == 0 ?
09960E  jne 0x4995DC
099610  mov eax, [edi+4]             ; used
09961F  lea edx, [eax*8]
099626  mov [edi+0x10], edx          ; bitpos = used*8  ← 强制重同步
09962B  lea ecx, [eax+1]
09962E  mov [edi+4], ecx
099631  mov byte [edx+eax], 0        ; 追加 0 字节
```

### 1.3 WriteData / WriteLenStr 不更新 bitpos（DIRECT）

- `MSG_WriteData` `0x9949B`：只 `memcpy` + `used += len`，**无 `[msg+0x10]` 访问**。
- `WriteLenStr` `0x99651`：脚本自检 `out_c09.txt` 结果 `False`，**无 `[msg+0x10]` 写入**。

**含义：** A1 字符串以裸字节写入，位字段在下一次字节边界处强制跳到 `used*8`。

## 2. 0x04 + count1 的起点（DIRECT）

```asm
0A07E6  mov dword [edi+0x10], 0      ; bitpos 归零
0A07F8  call WriteByte(4)            ; 8 bit
0A0807  call WriteShort(count1)      ; ecx=2 → 2 字节 = 16 bit
```

`0x04`(8) + count1(16) = 24 bit = **3 字节整**，因此 body 起点在字节边界上。

## 3. Configstring 三段的位长模型

## 3.1 记录格式

| 段 | 格式 |
|---|---|
| A1 | `1 bit`（连续索引）或 `1+13 bit`（绝对索引）+ 字符串 `(len+1)` 字节 |
| A2 | 10-bit 计数 + [1 或 14 bit 索引 + 10-bit 值] |
| A3 | 10-bit 计数 + [1 或 14 bit 索引 + 10-bit A + 7-bit B + 4-bit n + n×12-bit] |

## 3.2 累计位模型（从 `0x04` 首位起算）

| 场景 | 0x06 起始 bitpos（count1=16） | 模 8 |
|---|---|---|
| A1=A2=A3 空 | 44 | 4 |
| A1=[(0,'')] | 53 | 5 |
| A1=[(0,'a')] | 61 | 5 |
| A1=[(0,'a')]、A2=[(0,1)] | **72** | **0（字节对齐）** |
| A1=[(0,'a')]、A2=[(0,1),(1,2)]、A3=[(0,1023,127,[4095,1])] | 129 | 1 |
| A1=[(0,'a'),(5,'bb')] | 99 | 3 |

**结论（DIRECT 模型）：** `0x06` **不保证字节对齐**；在特定输入下可为字节对齐。

## 4. 客户端读取端位推进

| 段 | 客户端读取 | bitpos 是否推进 |
|---|---|---|
| count1 | `MSG_ReadData(...,2)` @0xA26B2 | 字节游标 +2（DIRECT） |
| A1 | `MSG_ReadBits` 13-bit + 字符串 NUL 扫描 | 位游标推进（DIRECT） |
| A2 | `MSG_ReadBits` 11-bit / 13-bit / 10-bit | 位游标推进（DIRECT） |
| A3 | `MSG_ReadBits` 10-bit / `0xA2480` | 位游标推进（DIRECT） |
| 0x06 | **未定位** | **BLOCKED** |

**客户端位读取原语（DIRECT）：** `MSG_ReadBits` `0x1AC670` 使用 `[msg+0x20]` 作 bitpos，`and 7` / `sar 3` 与 `MSG_WriteBits` 同构（LSB-first）。

**客户端字节读取原语（DIRECT）：** `MSG_ReadData` `0x1AC1D0` 逐字节读，不使用位逻辑；`0xA2660` 的 count1 用它读 2 字节。

## 5. 裁定

| 子项 | 裁定 |
|---|---|
| `0xA2660` 内字段位序为 LSB-first | **PROVEN（DIRECT）** |
| count1 = 16 bit 字节对齐读 | **PROVEN（DIRECT）** |
| `0x06` 起始 offset 可复算 | **PROVEN（模型，DIRECT）** |
| `0x06` 是否字节对齐 | **BLOCKED（因输入相关）** |
| 客户端对 `0x06` 的对齐处理 | **BLOCKED** |
"""

# ---------- 06 MATRIX ----------
files["06_CLIENT_SERVER_CONFIGSTRING_MATRIX.md"]=r"""# 06 — 客户端/服务端 Configstring 字段矩阵

> 基准：E-09 已确认的客户端 body reader `0xA2660`；服务端 `_CODOL2697_WriteConfigstrings RVA 0xA0468`。
> 等级：`DIRECT` / `CROSS`（两侧）/ `INFERRED` / `BLOCKED`
> 位偏移从 `0x04` 首位起算（服务端 count1=16 模型）。

---

## 1. 总矩阵

| # | 字段 | 客户端证据 | 服务端证据 | 位偏移 | 字节偏移 | 边界条件 | 结论 |
|---|---|---|---|---|---|---|---|
| F1 | 外层 `0x04` | `0x352FA1 inc [esi+0x1c]` 跳过 1 字节后进入 body（INFERRED） | `WriteByte(4)` @0xA07F8（DIRECT） | 0–7 | 0 | 1 字节整 | **CROSS(INFERRED)**：位置一致，值比较未证 |
| F2 | `count1` = 2 字节 | `push 2 / call MSG_ReadData` @0xA26AF–0xA26B2；`movsx word` @0xA26B7 | `WriteShort(count1)` @0xA0807，`0x99566 ECX=2` | 8–23 | 1–2 | 16 bit little-endian，`movsx` 有符号 | **PROVEN（CROSS）** |
| F3 | 索引连续性标志 | `call 0x44C8C0`（连续则 `lea edi,[ebx+1]`；否则读 13 bit） | `0x400 WriteIndexDelta`（1 bit 连续 / 1+13 bit 绝对） | 24… | — | 首索引 last=-1 | **PROVEN（CROSS）** |
| F4 | 13-bit 绝对索引 | `push 0xD / call MSG_ReadBits` @0xA26F0–0xA26F4 | 13-bit 绝对索引 | 视分支 | — | 上界 `≤0x1DD6`（0x1DD7 跳过） | **PROVEN（CROSS）** |
| F5 | 索引上限 | `cmp edi,0x1DD7; jl` @0xA2702–0xA2708 | `cmp esi,0x1DD6; ja` @0xA053E | — | — | `0x1DD7` 拒绝/跳过 | **PROVEN（CROSS）** |
| F6 | 合法区间 0..0x13 跳过 0x12 | `mov cl,[edi+0x2BD0A40]; cmp 0x14 / cmp 0x12` @0xA2728–0xA2736 | 同表区间校验 | — | — | `>=0x14` 或 `==0x12` 特殊处理 | **PROVEN（CROSS）** |
| F7 | A1 字符串 | `0xA25F0` 按 NUL 扫描（`mov cl,[eax]; test; jne`）@0xA2800；字符串处理 @0xA2751 | `WriteLenStr` @0xA096F（strlen+1 字节） | 24+Δ | 3+ | NUL 终止；长度上限 0x1FFF | **PROVEN（CROSS）** |
| F8 | A2 计数 | `push 0xB / call MSG_ReadBits` @0xA2765–0xA276C | A2 段计数 10 bit | 视 A1 长度 | — | 0 时跳过整段 | **PROVEN（CROSS）** |
| F9 | A2 条目（索引+10 bit） | `push 0xD` 索引 + `push 0xA` 值 @0xA27A4–0xA27D7 | use 10 bit 值 | — | — | 索引同 F4/F5 | **PROVEN（CROSS）** |
| F10 | A3 计数 | `push 0xA / call MSG_ReadBits` @0xA2872–0xA2879 | A3 段计数 10 bit | 视 A1/A2 | — | 0 时跳到函数尾 | **PROVEN（CROSS）** |
| F11 | A3 子过程 `0xA2480` | `call 0xA2480` @0xA28E0 | A3 记录：10+7+4+n×12 | — | — | n≤0xF；A≤0x3FF；B≤0x7F | **PROVEN（CROSS）** |
| F12 | A3 内部位宽 | `MSG_ReadBits(10/7/4/12)` @0xA2490–0xA24A7 | 10/7/4/12 | — | — | — | **PROVEN（CROSS）** |
| F13 | 外层 `0x06` | **无客户端读取证据** | `WriteByte(6)` @0xA0997 | 依输入 44/53/61/72/129… | — | 不保证字节对齐 | **BLOCKED（客户端侧）** |
| F14 | 外层 `0x04` 值比较 | 无 `cmp ...4`（四区域扫描命中 0） | 常量 4（DIRECT） | — | — | — | **BLOCKED** |

## 2. 逐字段分级的强制声明

Configstring body 字段顺序按字段独立裁定。**已 PROVEN 的字段**：F2、F3、F4、F5、F6、F7、F8、F9、F10、F11、F12。**未闭合**：F1（值比较）、F13、F14。

**禁止：** 把 F2–F12 的局部一致上升为“整条消息互操作已证实”。外层框架（F1/F13/F14）未闭合，整体互操作仍为 **BLOCKED**。

## 3. 两侧调用链对照

| 侧 | 路径 |
|---|---|
| 服务端 | `_CODOL2697_WriteGamestate` `0xA21B8` → `call _CODOL2697_WriteConfigstrings` `0xA0468` → `0xA07F8 WriteByte(4)` → `0xA0807 WriteShort(count1)` → 三段 → `0xA0997 WriteByte(6)` |
| 客户端 | `0x3547D0`(读1字节键) → `0x354100`(9项跳转表, case 6) → 读4字节长度+载荷 → `0x352F80`(+1字节) → `0xA2660`(count1 + 三段) → `ret` |

**两侧字段级顺序一致（CROSS）**；外层映射**未证**。
"""

# ---------- 07 VERDICT ----------
files["07_E10_VERDICT.md"]=r"""# 07 — E-10 总裁定 / VERDICT

> 只读静态分析。未启动游戏、未注入、未读进程内存、未修改样本。

---

## 1. 五项完成标准逐条裁定

| # | 完成标准 | 裁定 | 依据 |
|---|---|---|---|
| 1 | 外层 `0x04` 分派 | **BLOCKED** | 无客户端 `cmp 4`；仅有“进入 body 前 +1 字节”强 INFERRED（`03`） |
| 2 | `0x06` 读取路径 | **BLOCKED** | 客户端读取点未定位（`04`） |
| 3 | `0x06` 位宽（8 bit） | **BLOCKED** | 服务端 `WriteByte` 为 1 字节（DIRECT）；客户端无读取证据 |
| 4 | `0x06` 字节对齐 | **BLOCKED** | 起始 bitpos 输入相关（44/53/61/72/129…）；客户端对齐行为未知 |
| 5 | `0x06` 终止语义 | **BLOCKED** | 服务端写点位于 body 之后；客户端未见退出/终止分支 |
| 6 | Configstring body 字段顺序 | **按字段独立裁定** | F2–F12 PROVEN；F1/F13/F14 BLOCKED（`06`） |

## 2. 任务 A：调用链闭合

- `0xA2660` 直接调用点 **3 个**（全量复核）：`0x3514F0`（调用）、`0x352FA7`、`0x352FB4`（尾跳转）。
- 分布：`0x3512A0` ×1、`0x352F80` ×2。
- **更正 E-09：** 后两处在 `0x352F80`，不是 `0x352E80`。
- 找到客户端 9 项跳转表 `0x354100`（case 0..8）与选择器 `0x3547D0`。
- Configstring body 走 **case 6**（4 字节长度 + 载荷 + 跳过 1 字节），**不是 case 4**。
- 外层 `0x04` 的值级分派：**BLOCKED**。
- `.tvm0`：不在本链任何 `call/jmp` 边上，按停止条件不深入。

## 3. 任务 B：0x06 终止语义

- 服务端 Configstring 尾 `WriteByte(6)` @ `0xA0997`：**DIRECT**。
- 客户端 `0xA2660` 内**没有**读取 `0x06` 的指令。
- 四类 `0x06` 上下文（Configstring / Gamestate / Snapshot 内 / 外层选择器）分别登记，**未跨层合并**。
- 服务端位记账：`bitpos%8==0 ⇒ bitpos=used*8`；`WriteData`/`WriteLenStr` 不更新 bitpos。
- 累计位模型：`0x06` 起始可为 44/53/61/72/129…，**不保证字节对齐**。
- 读取端行为：**BLOCKED**。

## 4. 任务 C：字段级一致性

| 字段 | 裁定 |
|---|---|
| count1 2 字节 | PROVEN |
| 索引连续性标志 + 13-bit 绝对索引 | PROVEN |
| A1 字符串 | PROVEN |
| A2 计数与条目 | PROVEN |
| A3 计数与子过程 `0xA2480` | PROVEN |
| 索引上限及跳过规则 | PROVEN |
| 外层 `0x04` | BLOCKED（位置 CROSS-INFERRED，值比较未证） |
| 候选 `0x06` | BLOCKED |

## 5. 全局纪律声明

- **未**把局部字段一致升级为整条消息互操作已证实。
- **未**用构造向量冒充 Golden。
- **未**跨消息层合并 `0x06` 候选。
- **未**在 `.tvm0` 混淆区扩大搜索。

## 6. 停止条件与最小证据缺口

| ID | 缺口 | 最小新增证据 | 授权 |
|---|---|---|---|
| G-04-1 | 外层 `0x04` 分派 | `0x3547D0` 键的生产者/取值域，或 case 6 键的常量比较 | 否 |
| G-04-2 | 跳过字节内容 | `0x352F80` 入口前该字节的写入者 | 否 |
| G-06-1 | `0x06` 客户端读取点 | `0xA2660` 返回后调用者的 1 字节常量比较 | 否 |
| G-06-2/3 | 对齐与终止 | 读取原语的 bitpos/字节游标使用与退出分支 | 否 |
| G-06-4 | 端到端兼容 | 原始帧字节 | **是** |

## 7. 交付物清单

| 文件 | 状态 |
|---|---|
| `01_A2660_CALLER_INVENTORY.md` | ✔ |
| `02_OUTER_DISPATCH_CALLGRAPH.md` | ✔ |
| `03_OPCODE_04_DISPATCH_VERDICT.md` | ✔ |
| `04_TERMINATOR_06_READ_PATH.md` | ✔ |
| `05_BIT_ALIGNMENT_RECONSTRUCTION.md` | ✔ |
| `06_CLIENT_SERVER_CONFIGSTRING_MATRIX.md` | ✔ |
| `07_E10_VERDICT.md` | ✔ |
| `SHA256SUMS.txt` | ✔ |
"""

for name, content in files.items():
    with open(os.path.join(wd, name), "w", encoding="utf-8", newline="\n") as f:
        f.write(content)
print("wrote", len(files), "deliverables")
