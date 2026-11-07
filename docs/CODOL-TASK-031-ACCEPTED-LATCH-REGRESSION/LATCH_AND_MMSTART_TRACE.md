# LATCH_AND_MMSTART_TRACE — 因果链逐项取证

> ⚠ **证据效力更正（第二次修订）：**
> 本次运行客户端停在 **"100" 弹窗错误**，**未进入大厅**（`rc=-1 / 0xFFFFFFFF`）。
> 因此本文件**步 1–8 的动态列全部为 `INVALID_PRECONDITION`**，仅**原样保留**原始观测，**不得**作为正常流程证据。
> **静态反汇编部分独立保留**，等级继续区分 `CONFIRMED` 与 `INFERRED`。

**目标镜像：** `CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin`
（`17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045`，10,899,456 B，基址 `0x00400000`，`SizeOfImage 0x0E659000`）
**静态方法：** Capstone 逐条反汇编 + 全镜像线性扫描；**无插桩**。

---

## 0. 静态部分（**独立保留，不受本次启动失败影响**）

### 0.1 `accepted` 解析入口与指纹门 —— `CONFIRMED`

| 项 | 结论 | 证据 |
|---|---|---|
| 指纹门字符串 | **CONFIRMED** | `0xDC69B0` = `6d 6d 62 6f 6f 6b 20 61 63 63 65 70 74 65 64 00`，前 15 字节即 `"mmbook accepted"` |
| 门比较指令 | **CONFIRMED** | `0x6326D7 push 0xf` / `0x6326DA push 0xDC69B0` / `0x6326DF call 0xC3C678` |
| 比较语义 | **CONFIRMED** | `0xC3C678` 逐 **字节**比较（`mov dl, byte ptr [eax]` / `cmp dl, byte ptr [ecx-4]`），**非宽字符** |
| 解析函数 | **CONFIRMED** | `0x632680`，`ret 0x14`（2 个被调用方弹栈 = 5 个栈参数），`this = ecx` |
| `arg5` 指向何处 | **INFERRED** | 依调用约定推断为"内层数据起点"；**未定位调用者，故不是 CONFIRMED** |

### 0.2 条件链（地址与分支 —— `CONFIRMED`）

| 序 | 地址 | 条件 | 失败去向 |
|---|---|---|---|
| G1 | `0x63268D` | `byte[esi+0x278] != 0` | `je 0x6328EB` → 清零 A/B |
| G2 | `0x63269B` | `dword[0x76446B0] < 3` | `jge 0x6328EB` → 清零 A/B |
| G3 | `0x6326AA` | `dword[esi+0xE360] >= 0` | `jl 0x6328ED` → 清零 A/B（同清理块：写 `0x3A048/0x3A04C = 0` + `memset(esi+0x3A050,0,0x40)`） |
| **G6** | `0x6326D7` | `strncmp(arg5,"mmbook accepted",15)==0` | `jne 0x632876` → 失败出口 |
| G4 | `0x6326B9` | `arg1 == [esi+0x3A048]` | `jne 0x632916` → 清零 A/B |
| G5 | `0x6326C8` | `arg2 == [esi+0x3A04C]` | `jne 0x632916` → 清零 A/B |
| G7 | `0x6326FB` / `0x632707` | `[+0x75D8]==arg1` 且 `[+0x75DC]==arg2` | 不匹配 → `0x632712` 失败出口 |

**成功路径（`0x632736` 起，`CONFIRMED`）：** 于 `0x632745` 写局部成功标志后，**直接调用 `0x632070`（`mmstart` 构造器）**，并在 `0x63280B` 写 `byte[esi+0x288] = 1`。

> 即 **`mmstart` 构造与闩锁置 1 是同一次成功处理内的两个副作用**，不是"闩锁先、构造后"的串联。

### 0.3 闩锁写入/读取与复位风险 —— `CONFIRMED`

| 项 | 结论 | 证据 |
|---|---|---|
| 以立即数写 **1** 于字节域 `+0x288` | **CONFIRMED** | 全镜像该指令模式（`c6 86 88 02 00 00 01`）**仅 1 处**：`0x63280B`（在 `0x632680` 成功分支内） |
| 该闩锁的字节读点 | **CONFIRMED** | `0x634402`：`cmp byte ptr [ebx+0x288], 0` |
| 同一对象域另有 word 写 | **CONFIRMED** | `0x62F47A`（`mov word[edi+0x288], bx`）、`0x634B13`（`mov word[ebx+0x288], 0`）。word 覆盖 `0x288/0x289` 两字节 → **闩锁存在被复位的静态来源**，属时序风险 |
| `+0x288` 全部位移引用 | **CONFIRMED** | 全镜像 86 处 `disp==0x288`；分属**多个不同结构体**，不得混用。仅上列为匹配对象语境 |

### 0.4 闩锁消费者 `0x634402` 条件公式 —— `CONFIRMED`

```
00634402  cmp byte ptr [ebx+0x288], 0     ; 闩锁
00634410  jne 0x63441B                     ; != 0 -> 置标志
00634412  cmp dword ptr [0x76446B0], 3
00634419  jl  0x634434                     ; ==0 且 [0x76446B0]<3 -> 不置标志
00634421  cmp eax, ecx                     ; eax=[ebx+0xE360], ecx=0
00634425  cmp eax, [ebx+0x7230]            ; 上界
0063442D  mov byte ptr [ebp-0x1E1], 1
```

**消费条件：** `[0x288] != 0` **或**（`[0x76446B0] >= 3` 且 `0 <= [matching+0xE360] < [matching+0x7230]`）。
函数 `0x634340` 的调用者：`0x63346E`、`0x6347F9`、`0x634F5F`（`CONFIRMED`）。

### 0.5 `mmstart` 构造器 —— `CONFIRMED`

| 项 | 证据 |
|---|---|
| 入口 | `0x632070` |
| 调用者（仅两处 `E8`） | `0x632776`（`0x632680` 成功路径）、`0x62FA3E` |
| 格式串 | `0xDC6800`：`mmstart sv_resetServer; 2486 %d; 3265 %d; 2489 %d; 2574 %d; playlist %d; %s %d; roomChatChannelID %llu; …` |
| 分支变体 | `0xDC6914`（`2634 1; start_map_rotate…`）、`0xDC6930`（`start_map_rotate_once`） |
| 字段来源 | `[edi+0x105F8]/0x105FC/0x105FE/0x10604/0x105D8` |

### 0.6 接收通道 / 调用者 —— `UNKNOWN`（未闭合）

穷尽性扫描结果：

| 扫描 | 目标 | 命中 |
|---|---|---|
| `E8 rel32` | 函数 `0x632680` | **0** |
| 全镜像 `mov [mem], imm32` | vtable `0xDC73A0` / `0xDC7840` | **0** |
| 全镜像指令位移引用（mem/imm） | `0xDC7360..0xDC7900` | **0** |
| 全镜像指令位移引用 | 恰为 `0xDC73A0`/`0xDC7840`/`0xDC73B0`/`0xDC7850` | **0** |
| Base.dll 字符串 | `mmbook` / `mmbook accepted` / `mmstart` / `MM_RESERVE_CMD_REQUEST` | **0** |

解析器只作为两条 vtable 副本（`0xDC73A0` / `0xDC7840`）的第 5 槽出现，二者前段相同、在 `0xDC73D8` / `0xDC7868` 分叉。两地址在静态镜像内**零直接引用** → 经运行期计算/重定位数据安装，结合 `.tvm0` 虚拟化，静态可读面系统性不足。

### 0.7 变体 B 的条件式判定 —— `INFERRED`

**前提：** `arg5` 指向 blob 内层数据起点（上文 0.1 的 `INFERRED`）。

| 变体 | 内层首 15B | 过 G6？ |
|---|---|---|
| A（当前 kit：裸 15B + NUL） | `mmbook accepted` | **是** |
| B（ol-mod 存档：内层 `u32(15)` 前缀） | `\x0f\x00\x00\x00mmbook acce` | **否**（前提成立时） |
| C（023 前形态：内层 `u32(16)` 前缀） | `\x10\x00\x00\x00mmbook acce` | **否**（前提成立时） |

> **限制条件（不得省略）：** 若线上先剥掉一层前缀再传 `arg5`，则 B 也能过。
> **在接收通道/调用者未定位前**，`accepted` 形态冲突**仍未裁定**。

---

## 1. 动态部分（**统一 `INVALID_PRECONDITION`，仅原样保留**）

> 前置条件：**客户端须成功进入大厅且业务会话就绪**。本轮**未满足**（停在 "100" 弹窗，`rc=-1 / 0xFFFFFFFF`）。

| 步 | 环节 | 静态 | 本轮动态（更正后） |
|---|---|---|---|
| 1 | `mmbook` 请求 / A/B 配对 | CONFIRMED | **INVALID_PRECONDITION**（`6/14` 未出现，**仅限本次错误会话**） |
| 2 | `accepted` 字节 / 通道 | 字节门 CONFIRMED；通道 UNKNOWN | **INVALID_PRECONDITION** |
| 3 | 处理函数 / 分支 | CONFIRMED | **INVALID_PRECONDITION** |
| 4 | `[matching+0x288]` 0→1 | 写入点 CONFIRMED | **INVALID_PRECONDITION** |
| 5 | `0x634402` 消费条件 | CONFIRMED | **INVALID_PRECONDITION** |
| 6 | `0x632070` 构造 | CONFIRMED | **INVALID_PRECONDITION** |
| 7 | `mmstart` 发送 | INFERRED | **INVALID_PRECONDITION** |
| 8 | 战斗连接 | — | **INVALID_PRECONDITION** |

**三种未观测形态的区分：**
- **函数未执行**：`0x632680` / `0x632070` / `0x634402`。**但其根因是会话被前置错误截断，不反映正常流程。**
- **函数执行但条件不满足**：**本轮不适用**。
- **观察手段未捕获**：`[matching+0x288]`（未挂专门采样器 + 会话未进入预约阶段）。

**最早的未满足条件（唯一成立的）：** **客户端未成功进入大厅**（`rc=-1 / 0xFFFFFFFF`，停在 "100" 弹窗）。
在它之前，`mmbook` 是否触发、`accepted` 取何形态等，**均无法讨论**。

---

## 2. 静态证据脚本

| 脚本 | 作用 |
|---|---|
| `_work\static_verify\anchors.py` | 字符串/代码锚点字节核对 |
| `_work\static_verify\dis_632680.py` | 解析器全反汇编（G1–G7） |
| `_work\static_verify\dis_632680_tail2.py` | 成功/失败出口与清理路径 |
| `_work\static_verify\dis_cmp.py` | `0xC3C678` 逐字节比较函数 |
| `_work\static_verify\dis_632070.py` | `mmstart` 构造器 |
| `_work\static_verify\dis_634340.py` | 闩锁消费者 `0x634402` |
| `_work\static_verify\dis_word288.py` | 两处 word 写（复位风险） |
| `_work\static_verify\scan_288.py` | `+0x288` 全镜像读写扫描（86 处） |
| `_work\static_verify\xrefs.py` | `0x632680/0x632070` 调用者扫描 |
| `_work\static_verify\scan_vt.py` | 两条 vtable 引用扫描（0 命中） |
| `_work\static_verify\base_strings.py` | Base.dll 字符串扫描（0 命中） |
