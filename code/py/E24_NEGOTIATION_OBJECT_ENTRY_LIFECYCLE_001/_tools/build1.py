# -*- coding: utf-8 -*-
from pathlib import Path
OUT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001")
files={}

files["E24_EXECUTIVE_SUMMARY.md"]=r'''# E24 执行摘要

## 一句话结论

`0x6AB310`（VA `0xAAB310`，`.text`）**入口已闭合**：它只有一个直接调用者 `0x6AC192`，位于会话分派器 `0x6AC0C0` 的 `[esi+0x5CC]==1 && msgcode==0x81` 分支；该函数是**握手协商的应答状态机**（构造 `[edi+0x5F4]` 协商对象、按报文标签 `CLIENTCHAL`/`BDDATA` 重组应答、并把 `[edi+0x5CC]` 从 1 推进到 2），`[edi+0x5F4]` 对象的 slot+3（`0xA87D50`）在 `0x6AAE70` 的 0x85 HMAC 校验成功路径被调用，执行"16 字节头校验 + 表驱动解密/提交"。

## 关键事实

1. **入口唯一且确定**：全 `.text` 的 `E8` rel32 扫描中，指向 RVA `0x6AB310` 的仅 `0x6AC192`；无 `E9` 跳板、无函数指针表项（VA/RVA 4 字节指针扫描均 0 命中）。
2. **触发条件可确定**：
   - `0x6AC0C0` 要求 `[esi+0xC8]==2`（会话进行中）；
   - 解析出 `msgcode`（`[ebp-0xE]`）与 `[esi+0x5CC]`（握手阶段）；
   - `[esi+0x5CC]==1` 且 `msgcode==0x81` ⇒ 调用 `0x6AB310`；
   - 同阶段 `msgcode==0x04` ⇒ 走失败路径 `0x6AAA770`（置 `[+0xC8]=4`）。
3. **协商对象生命周期**：
   - **构造/赋值**：`[edi+0x5F4]` 由 `0x6AB9E7` 赋值，值为 `0x6AB9DA call 0xA87BA0` 返回的对象（vtable `0xC5A31C`）；赋值前 `0x6AB9B3` 先把旧对象经 `[ecx]` slot0 释放并清零。
   - **首次使用**：`0x6AB146`（`0x6AAE70` 成功路径）取 `[edi+0x5F4]`，经 `[ecx]→[edx+0xC]` 调用 slot+3。
   - **释放**：析构序列 `0x6AA14D..0x6AA177` 对 `+0x5F0`、`+0x5F4` 各做一次"slot0 虚调用 + 置 0"。
   - **复用**：重新握手时再次执行 `0x6AB9B3` 清零 + `0x6AB9E7` 换新。
4. **`0xA87D50` 缓冲语义**：
   - 约定 `thiscall` + 4 栈参数 + `ret 0x10`：`(this, buf, buf, len)`；
   - 对 `this+0xC` 先做 `0xACE180(arg1, 0x10, this+0xC)`：比较 `arg1` 缓冲长度字段与 `0x10`，相等则 `memcpy`（`0xB4FF60`）把 0x10 字节从 `arg1` 拷入 `this+0x14`；不等返回 `0x10`（失败）；
   - 成功则 `0xACE1B0(arg2, arg3, len, this+0xC)`：校验 `len`（1..0x80、可整除、4 对齐），经 `[this+0x10].slot0` 取描述符，从 cipher 表基址 `0xD48F48`/`0xD48F64` 取函数指针；无表项时做 XOR 流变换。返回 0 表示成功。
   - `this+0x14` 的 16 字节是**构造期预设的常量密钥表**，两处调用传入的 `arg1` 是**不同的临时缓冲**，但校验后均与同一份密钥比较。
5. **握手阶段字段 `[esi+0x5CC]`**：writer 为 `0x6A1310`(0 复位)、`0x6A13F0`(0 释放)、`0x6A154F`(由 `[ebp+8]` 任意设置)、`0x6AA470`(1)、`0x6ABB01`(2)、`0x6AB2ED`(3)；reader 为 `0x6AC178`（分派器）。这构成显式的握手阶段机。
6. **协商报文标签**：`0x6AB310` 构造的应答里使用字符串 `CLIENTCHAL`（VA `0xC5B144`）与 `BDDATA`（VA `0xC5B13C`），并写入 opcode 常量 `0xD2`(长度前缀)、`0xAB`、`0x82`、`0x81`，最终设置 `[+0x5CC]=2`。

## 逐目标裁定

| 目标 | 裁定 |
|---|---|
| `0x6AB310` 入口 | **PROVEN**：唯一直接调用者 `0x6AC192`，条件 `[+0x5CC]==1 && msgcode==0x81` |
| `[edi+0x5F4]` 赋值 | **PROVEN**：写 `0x6AB9E7`/清 `0x6AB9B3`；对象 `0xA87BA0`，vtable `0xC5A31C` |
| `0xA87D50` 调用约定 | **PROVEN**：thiscall，4 栈参数，`ret 0x10` |
| `0xACE180` 16 字节检查 | **PROVEN**：长度相等判定 + `memcpy` 0x10 字节到 `this+0x14` |
| `0xACE1B0` 数据流 | **INFERRED（强）**：长度校验 + 表驱动（`0xD48F48/0xD48F64`）流变换，返回 0=成功 |
| `[+0x5CC]` 握手阶段 | **PROVEN**（字段读写序列）；阶段编号的业务命名 **BLOCKED** |
| `0x81/0x83/0x84/0x85` 与握手阶段绑定 | **PROVEN**：阶段1→0x81/0x04；阶段2→0x83/0x84；阶段3→0x85/0x84 |
| 方向（入站/出站） | **INFERRED（弱）**：0x85 路径读接收计数器，偏入站；其余未独立证实 |

## 被证伪/更正的假设

- **E-23「`0x6AB310` 入口搜索得 0，可能经跳板/间接调用」→ REFUTED**：其自有工具 `t21_callers2.py` 已打印"RVA 0x6AB310 : 1 [0x6ac192]"，却未写入报告。
- E-23「`[edi+0x5F4]` 的写入者 `0x6AB9B3`/`0x6AB9E7` 只是字段赋值」→ 更正：二者是**旧对象释放 + 新对象换入**，属构造/销毁对。
- 「`0xA87D50` 的 `(this,buf,buf,len)` 两个相同缓冲参数」→ 更正：`0xA87D50` 的 arg1 与 arg2/arg3 实为**不同**参数（`0x6AB15A` 的 `lea [ebp-0x50]` 是 arg1，`[ebp-0x210]` 是 arg2/arg3）；`0x6AAE70` 把它们传给 `0xACE180`(arg1) 与 `0xACE1B0`(arg2/arg3)。

## 剩余阻塞项

1. `[+0x5CC]` 阶段编号（0/1/2/3）与协议语义命名（是否"挑战/应答/确认"）无独立证据。
2. `0xACE1B0` 依赖的 `.data 0xD48F48`/`0xD48F64` 表位于 BSS 尾部，磁盘无字节，**静态不可解析**。
3. `0x6AB310` 生成的应答报文最终由哪个发送路径写出（未找到该缓冲到 socket 的静态边）。
4. 方向绑定仅对 0x85 路径有"接收计数器"支持。

## 下一步唯一建议

解析 `0x6AB310` 末尾构造的应答缓冲（`0x6ABAC0` 后经 `0x6ABAAA`/`0x6ABABB` 填入的 `[esi+8]`/`[esi+0x10]`/`[ebp-0x38]` 数据）去向，确认它是否经 `0x6AA230` 入队到发送缓冲，从而闭合"应答→socket"的最后一条边；这是唯一能把握手阶段从静态状态机推进到端到端数据流的边界。
'''

files["E24_6AB310_ENTRY_CLOSURE.md"]=r'''# E24 `0x6AB310` 入口闭合

## 1. 映像与地址口径

- 冻结恢复镜像 SHA-256 = `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4`（复核一致）。
- ImageBase = `0x400000`。本文地址默认 RVA；等价 VA = RVA + `0x400000`。
- `0x6AB310` RVA ↔ VA `0xAAB310`，属 `.text`（VA `0x001000..0x7AD90B`）。

## 2. 函数边界与序言

`0x6AB310` 起点由反向 `0xCC` 填充确定（前一条指令为 `ret 0xc`，`0x6AB306..0x6AB30F` 为 `0xCC`）：

```asm
6AB310  push ebp
6AB311  mov  ebp, esp
6AB313  push -1
6AB315  push 0xB98749          ; SEH scope table
6AB31A  mov  eax, fs:[0]
6AB321  sub  esp, 0x194
6AB331  push ebx / esi / edi
6AB33E  mov eax,[ebp+0xC]      ; arg2
6AB341  mov ebx,[ebp+0x10]     ; arg3
6AB344  mov esi,[ebp+8]        ; arg1
6AB349  mov edi, ecx           ; this
...
6ABB8E  ret 0xC
```

**调用约定：thiscall（ECX=this）+ 3 个栈参数，`ret 0xC`。**

对应 `0x6AC192` 处调用形态（`0x6AC18A..0x6AC192`）：

```asm
6AC18A  mov  edx,[ebp-0x14]    ; 解析出的负载缓冲指针
6AC18D  push edi               ; arg3 = 有效长（[esi+0xAC]-1）
6AC18E  push edx               ; arg2 = 负载指针
6AC18F  push ebx               ; arg1 = 帧缓冲基址
6AC190  mov  ecx, esi          ; this = 会话对象
6AC192  call 0xAAB310          ; == RVA 0x6AB310
```

## 3. 入口闭合（三种入口形式逐一排查）

| 入口形式 | 方法 | 结果 |
|---|---|---|
| 直接 `E8` | 全 `.text` rel32 扫描，`target = insn_VA+5+rel` | **1 处**：`0x6AC192` |
| `E9` 跳板 | 同上扫描 opcode `0xE9` | **0 处** |
| 函数指针表 / vtable | 全文件 4 字节扫描 VA 形式 `00AAB310` 与 RVA 形式 `006AB310` | **均 0 命中** |
| `.rimp` 修复 | `.rimp` 全量字节扫描（VA/RVA 形式） | **0 命中** |
| TLS 回调 | 数据目录 TLS `AddressOfCallBacks` 数组首元素 | `0x00000000`（空） |

**裁定**：`0x6AB310` 的入口是**唯一直接调用**，不存在跳板、函数指针或间接注册路径。可写为 PROVEN。

## 4. 上游触发条件

调用链（自外向内）：

```text
0x68EEF1 / 0x68F02C   会话循环
   call 0x6AC3D0      跳板: push ebp; mov ebp,esp; pop ebp; jmp 0x6AC0C0
0x6AC0C0   会话分派器 (thiscall, 2 栈输出参数, ret 8)
  6AC0EA  cmp [esi+0xC8], 4      ; 已失败 -> 返回 false
  6AC10E  cmp [esi+0xC8], 2      ; 必须处于"进行中"
  6AC121  call 0x6AABE60         ; 维护/推进
  6AC130  call 0x6A9570          ; 准备
  6AC13D  mov  ecx,[esi+0xB0]    ; 载荷对象
  6AC143  call 0xDF4A028         ; .tvm0: 取数据指针
  6AC148  mov  edi,[esi+0xAC]    ; 帧长
  6AC168  call 0xA85AD0          ; 解析出 msgcode(= [ebp-0xE]) 与 offset(= [ebp-0x14])
  6AC178  mov  eax,[esi+0x5CC]   ; 握手阶段
  6AC17E  cmp  eax, 1
  6AC183  mov  al,[ebp-0xE]      ; msgcode
  6AC186  cmp  al, 0x81          ; 阶段1 + 0x81 -> 0x6AB310
  6AC192  call 0xAAB310
```

判定逻辑（`0x6AC178..0x6AC2F7`）可整理为：

| 阶段 `[esi+0x5CC]` | msgcode | 目标函数 |
|---|---|---|
| 1 | `0x81` | `0x6AB310`（**本论**） |
| 1 | `0x04` | 失败路径 `0x6AAA770` |
| 2 | `0x83` | `0x6AB260` |
| 2 | `0x84` | `0x6A9690`（分配私有对象 0x1C） |
| 3 | `0x85` | `0x6AAE70`（HMAC/计数器校验） |
| 3 | `0x84` | `0x6A9690` |
| 其他 | — | `0x6AC38C` 日志 + `0x6AAA770` |

**裁定**：`0x6AB310` 受"连接状态 `[+0xC8]==2`"与"握手阶段 `[+0x5CC]==1` + 报文码 `0x81`"双重控制。可写为 PROVEN。

## 5. 与 E-23 的差异

E-23 `E23_NEXT_GATE_DECISION.md` 记录："`0x6AB9D8` 所在函数（起点 `0x6AB310`）……当前 rel32 搜索得 0 —— 说明它可能经跳板/间接调用"。

实测：E-23 自带工具 `_tools/t21_callers2.py` 运行即输出 `RVA 0x6AB310 VA 00AAB310 : 1 ['0x6ac192']`，与报告结论矛盾。这是**报告与自有工具不一致**，非证据冲突。裁定为 REFUTED 并记入负向证据。
'''

files["E24_NEGOTIATION_OBJECT_LIFECYCLE.md"]=r'''# E24 协商对象生命周期

## 1. 对象标识

| 项 | 值 |
|---|---|
| 字段 | `[edi+0x5F4]`（`edi` = 会话 this） |
| 构造器 | `0xA87BA0`（RVA `0x687BA0`，`.text`） |
| vtable | `0xC5A31C`（`.rdata`，RVA `0x85A31C`） |
| 对象大小（构造时分配） | `0x394`（`0x6AB9C2 push 0x394` → `0x0DF9AA45` 分配器） |
| 首次使用点 | `0x6AB146`（`0x6AAE70` 成功路径） |

## 2. 构造器 `0xA87BA0`

```asm
687BA0  push ebp; mov ebp,esp
687BC9  push 0x10
687BCB  call 0xA888A0          ; 基类/子对象构造
687BD0  push 0xC5BEB0          ; 类型描述符（含函数指针表）
687BDC  mov  dword ptr [esi], 0xC5A31C    ; <== 写入本对象 vtable
687BE2  call 0xACBAF0
687C07  mov eax, esi; ret
```

- 静态调用者仅两处：`0x6AB97A`、`0x6AB9DA`（均在被调用函数 `0x6AB310` 内）。
- 构造器自身是 thiscall（ECX=this，无栈参数），返回 this。

## 3. 字段写入点（全量）

`[edi+0x5F4]` 的确定写入点：

| 写点 | 指令 | 语义 |
|---|---|---|
| `0x6AB9B3` | `mov dword ptr [edi+0x5F4], 0` | 旧对象经 slot0 释放后清零 |
| `0x6AB9E7` | `mov dword ptr [edi+0x5F4], eax` | 换入 `0x6AB9DA` 构造的新对象 |

紧邻的 `[edi+0x5F0]`（另一对象字段，同构造器）：写 `0x6AB953`(清 0)、`0x6AB983`(换新)，构造调用 `0x6AB97A`。

释放序列（析构路径 `0x6AA100` 起）：

```asm
6AA14D  mov  ecx,[esi+0x5F0]
6AA155  je   skip
6AA157  mov  eax,[ecx]; mov edx,[eax]; push 1; call edx   ; slot0(1) = 删除
6AA15F  mov  dword ptr [esi+0x5F0], 0
6AA165  mov  ecx,[esi+0x5F4]
6AA16D  je   skip
6AA16F  mov  eax,[ecx]; mov edx,[eax]; push 1; call edx   ; slot0(1) = 删除
6AA177  mov  dword ptr [esi+0x5F4], 0
```

**裁定**：对象生命周期为"构造 → 赋字段 → 首次使用（slot+3）→ 析构删除并清零 → 可再次构造替换（USE-REPLACE 模式）"。可写为 PROVEN。

## 4. 读取点（全量）

| 读点 | 函数 | 用途 |
|---|---|---|
| `0x6AB146` | `0x6AAE70` | 成功路径取对象，调用 slot+3 |
| `0x6AB99C` | `0x6AB310` | 换入新对象前取旧对象做删除 |
| `0x6AA165` | 析构 | 删除并清零 |
| `0x41DE91` / `0x41DF7A` | 渲染/相机路径 | 与 `[+0x5F0]` 二选一（同型对象，非本协议对象） |

## 5. 与连接/帧字段的关系

| 字段 | 含义（据 E-22/E-23 与实测） | 与本对象关系 |
|---|---|---|
| `[+0xC8]` | 连接状态（1/2/4） | 分派器要求 ==2 才可能到达 `0x6AB310`；失败置 4 |
| `[+0xAC]` | 帧长 | `0x6AB5D1` 读入应答；`0x6AC148` 读入解析 |
| `[+0xB0]` | 载荷对象 | `0x6AC13D` 取数据指针 |
| `[+0x5D0]` | 接收计数器 | 由 `0x6AB2ED` 写 3（与阶段 3 同步） |
| `[+0x5CC]` | **握手阶段** | `0x6ABB01` 由本函数从 1 推进到 2 |
| `[+0x5E0]`/`[+0x620]`/`[+0x624]` | 协商输入（server nonce/长度等） | `0x6AB3A9`/`0x6AB3C6`/`0x6AB5C1` 写入 |
| `[+0x5D8]` | 协商输出 | `0x6AB5A6` 写入 |
| `[+0x52C]`/`[+0x530]` | 32 位能力/NAT 标志 | `0x6AB479`/`0x6AB49E` 读入应答 |

**裁定**：本对象的创建与"握手阶段 1 → 2 的推进"直接耦合；创建发生在 `0x6AB310` 的应答组装完成之后（`0x6ABB01` 置阶段 2 之前）。

## 6. 状态推进与失败

```text
[+0x5CC]==1 且 msgcode==0x81
  └─ 0x6AB310
       ├─ 解析 arg1/arg2/arg3 (0xA878A0)
       ├─ 写 [+0x620]/[+0x624]/[+0x5E0] 协商输入
       ├─ arg1 首 dword == 0xD2 ? 否则 0x6ABB91 失败
       ├─ 构造应答 (0x6AB4C3.., 含 0x400 字节、CLIENTCHAL/BDDATA)
       ├─ 填 [ebx+8]/[ebx+0x10]/[ebp-0x38] 到应答 (0xDF6F97C)
       ├─ 成功 (0x6ABAC0 置 1)
       │    ├─ 构造新 [+0x5F0] 对象 (0x6AB97A)
       │    ├─ 构造新 [+0x5F4] 对象 (0x6AB9DA)
       │    ├─ 调用 slot+1 (0x6AB9FE, vtable+4 = 0xA87C30) 取 0x10 字节
       │    ├─ 0x6AA230(this, data0, data1) 入队/提交
       │    └─ [+0x5CC] = 2   (0x6ABB01)
       └─ 失败 (0x6ABACB 置 0) → 日志 0x43A7C0 → 0x6AAA770 置 [+0xC8]=4
```

**裁定**：成功即推进阶段并换入新对象；失败即终止连接状态。可写为 PROVEN（结构层面）。
'''

for name,content in files.items():
    (OUT/name).write_text(content,encoding="utf-8")
    print("wrote",name,len(content))
