# -*- coding: utf-8 -*-
from pathlib import Path
OUT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001")
files={}

files["E24_A87D50_BUFFER_DATAFLOW.md"]=r'''# E24 `0xA87D50` 缓冲数据流

## 1. 调用点与调用约定

**调用点**：`0x6AB146`（`0x6AAE70` HMAC 校验成功路径）

```asm
6AB140  mov  eax,[ebp-0x220]    ; = span 长度（0x6AAF9A 计算）
6AB146  mov  ecx,[edi+0x5F4]    ; ecx = 协商对象 (this)
6AB14C  mov  edx,[ecx]          ; vptr
6AB14E  mov  edx,[edx+0xC]      ; slot 索引 3
6AB151  push eax                ; arg4 = 长度
6AB152  mov  eax,[ebp-0x210]    ; span 缓冲基址（0x6AAF3D 计算）
6AB158  push eax                ; arg3
6AB159  push eax                ; arg2（与 arg3 同值）
6AB15A  lea  eax,[ebp-0x50]
6AB15D  push eax                ; arg1 = 16 字节临时块
6AB15E  call edx
6AB166  test al,al
6AB168  setne al
```

**被调函数 `0xA87D50`（RVA `0x687D50`）**：

```asm
687D50  push ebp; mov ebp,esp
687D53  mov  eax,[ebp+8]        ; arg1
687D58  lea  esi,[ecx+0xC]      ; this+0xC
687D5B  push esi                ; 第3参 = this+0xC
687D5C  push 0x10               ; 第2参 = 0x10
687D5E  push eax                ; 第1参 = arg1
687D61  call 0xACE180
687D69  test eax,eax; jne fail  ; 非0 => 失败
687D6D  mov  ecx,[ebp+0x14]     ; arg4
687D70  mov  edx,[ebp+0x10]     ; arg3
687D73  mov  eax,[ebp+0xC]      ; arg2
687D76  push esi; push ecx; push edx; push eax
687D7A  call 0xACE1B0
687D82  test eax,eax; jne fail
687D86  mov al,1; ret 0x10
```

**裁定**：`0xA87D50` 为 **thiscall + 4 栈参数 + `ret 0x10`**，返回 `bool`（1=成功，0=失败）。可写为 PROVEN。

## 2. 参数区分（更正 E-23 的表述）

E-23 写 "`(this, buf, buf, len)`"，易被读作 arg2 与 arg3 是同一缓冲。实测：

| 参数 | 来源 | 去向 |
|---|---|---|
| arg1 `[ebp+8]` | `0x6AB15A` `lea eax,[ebp-0x50]` | `0xACE180` 第1参（16 字节临时块） |
| arg2 `[ebp+0xC]` | `0x6AB159` `push eax`（= span 基址） | `0xACE1B0` 第1参 |
| arg3 `[ebp+0x10]` | `0x6AB158` `push eax`（= span 基址） | `0xACE1B0` 第2参 |
| arg4 `[ebp+0x14]` | `0x6AB151` `push eax`（= span 长度） | `0xACE1B0` 第3参 |

即：**arg2 与 arg3 确实同值**（都指向 span），但 arg1 是独立的 16 字节块；两者不混用。E-23 的括号写法在数值上正确，但掩盖了 arg1 ≠ arg2 的事实。

## 3. `0xACE180` 的 16 字节检查（arg1 → this+0x14）

```asm
6CE180  push ebp; mov ebp,esp
6CE183  mov  eax,[ebp+0xC]      ; 第2参 = 0x10
6CE186  mov  ecx,[ebp+0x10]     ; 第3参 = this+0xC
6CE189  cmp  eax,[ecx+4]        ; 比较 this+0x10 处 dword 与 0x10
6CE18C  je   0xACE195
6CE18E  mov  eax,0x10           ; 不相等 -> 返回 0x10（错误码）
6CE193  ret
6CE195  push eax                ; len
6CE196  mov  eax,[ebp+8]        ; 第1参 = arg1
6CE199  push eax
6CE19A  add  ecx,8              ; this+0x14
6CE19D  push ecx
6CE19E  call 0xB4FF60           ; memcpy(this+0x14, arg1, 0x10)
6CE1A6  xor  eax,eax            ; 返回 0 = 成功
6CE1A9  ret
```

- `0xB4FF60` 是 `memcpy`（`rep movsd` + 尾字节分支，见实测反汇编）。
- **比较对象**：`this+0x10` 处的长度字段与常量 `0x10`。
- **写入**：把 arg1 的 0x10 字节拷入 `this+0x14`。
- **失败**：返回 `0x10`。

**裁定**：该检查实际是"**16 字节定长拷入 + 长度守卫**"，不是摘要比对。可写为 PROVEN。

> 更正 E-23：E-23 描述为 `cmp [ecx], len` 形态，实测为 `cmp 0x10, [ecx+4]`（长度字段在 `this+0x10`，非 `this+0xC`）。

## 4. `0xACE1B0` 的数据流

```asm
6CE1B0  ...
6CE1CB  mov  ecx,[esi]          ; esi = this+0xC -> 描述符索引
6CE1D4  call 0xE00F7FB          ; 索引合法性/查询
6CE1E0  mov  ecx,[esi+4]        ; this+0x10 = 密钥长度
6CE1E3  cmp  ecx,1   jl fail
6CE1EC  cmp  ecx,0x80 jg fail
6CE1F9  mov  edi,[ebp+0x10]     ; arg3 = span 长度
6CE1FE  div  ecx                ; 长度整除检查
6CE206  test cl,3   jne fail    ; 4 对齐
6CE221  mov  ecx,[esi]          ; 索引
6CE223  lea  edx,[ecx+ecx*2]; shl edx,5    ; idx*0x60
6CE229  mov  ecx,[edx+0xD48F64] ; <== cipher 表项
6CE22F  test ecx,ecx
6CE231  je   0xACE25A
6CE233  ... push esi+0x88, esi+8, len, buf, this
6CE244  call ecx                 ; 表驱动函数
```

无表项分支（`0x6CE25A` 起）使用 `[edx+0xD48F48]` 的另一表指针做 XOR 流变换。

**裁定**：`0xACE1B0` 是"**长度校验 + cipher 描述符查表 + 流变换/回调**"，返回 0 表示成功。其核心数据依赖 `.data` 基址 `0xD48F48`/`0xD48F64` 的运行时表。可写为 INFERRED（强）；表的静态内容 BLOCKED。

## 5. 缓冲来源（`0x6AAE70` 内）

| 局部 | 计算点 | 含义 |
|---|---|---|
| `[ebp-0x210]` | `0x6AAF3A` `lea edx,[esi+eax]` | span 基址 = 帧基址 + 偏移 |
| `[ebp-0x220]` | `0x6AAF98` `sub eax,edx` | span 长度 |
| `[ebp-0x50]` | `0x6AAF08` `lea eax,[ebp-0x50]` | 16 字节临时块（供 `0xACE180`） |
| `[ebp-0x224]` | `0x6AAF13` | 消息码/计数器（随后与 `[edi+0x5D0]` 比较） |

`[ebp-0x50]` 在 `0x6AAF06..0x6AAF22` 由第二次 `0xA878A0` 调用填充；其内容源自入站帧（`esi` = arg1 帧缓冲）。

**裁定**：`0xA87D50` 的两个缓冲参数最终都指向**同一入站帧 span**，但用途分离：arg1 → 16 字节长度/密钥透传；arg2/arg3 → span 本体（长度 arg4）。可写为 INFERRED（强）。

## 6. 与帧码的关系

`0x6AAE70` 只在**阶段 3 + msgcode 0x85** 被调用（`0x6AC2D9..0x6AC2F0`），因此：

- `0xA87D50` 的调用**必然**发生在 msgcode == `0x85` 的路径上（PROVEN）。
- `0xA87D50` 与 `0x81/0x83/0x84` **无直接数据流**（那三条走 `0x6AB310` / `0x6AB260` / `0x6A9690`）。

| 帧码 | 是否可达 `0xA87D50` | 依据 |
|---|---|---|
| 0x81 | 否 | 走 `0x6AB310`（阶段 1） |
| 0x83 | 否 | 走 `0x6AB260`（阶段 2） |
| 0x84 | 否 | 走 `0x6A9690`（阶段 2/3） |
| 0x85 | **是** | `0x6AC2DC` → `0x6AC2F0` `call 0x6AAE70` → `0x6AB146` slot+3 |
'''

files["E24_HANDSHAKE_OPCODE_DIRECTION_MATRIX.md"]=r'''# E24 握手与消息码方向交叉表

## 1. 分派总表（`0x6AC0C0`，实测）

```asm
6AC0EA  cmp [esi+0xC8], 4        ; 已失败 -> ret false
6AC10E  cmp [esi+0xC8], 2        ; 必须进行中
6AC178  mov eax,[esi+0x5CC]      ; 握手阶段
6AC183  mov al,[ebp-0xE]         ; 报文码
```

| 连接状态 `[+0xC8]` | 握手阶段 `[+0x5CC]` | 报文码 | 目标 | 备注 |
|---|---|---|---|---|
| 4 | — | — | 直接 `ret false`（`0x6AC106`） | 连接已终止 |
| ≠2 | — | — | 跳过分派（`0x6AC119`→`0x6AC3B4`） | — |
| 2 | 1 | `0x81` | `0x6AB310` | 本论；成功置阶段 2 |
| 2 | 1 | `0x04` | `0x6AAA770` | 失败/终止 |
| 2 | 2 | `0x83` | `0x6AB260` | 成功则置阶段 3 |
| 2 | 2 | `0x84` | `0x6A9690` | 带 1 个输出指针 |
| 2 | 3 | `0x85` | `0x6AAE70` | HMAC/计数器校验 |
| 2 | 3 | `0x84` | `0x6A9690` | 同阶段双码 |
| 2 | 其他 | 其他 | `0x6AC38C` 日志 + `0x6AAA770` | 未识别 |

## 2. 逐码评估

### 0x81

- **产生位置**：`0x6AB655`（`mov byte ptr [ebp-0x171], 0x81`，在 `0x6AB310` 内组装应答）。
- **消费位置**：`0x6AC186`（`cmp al,0x81`）→ `0x6AC192` `call 0xAAB310`。
- **方向证据**：**无直接收发 API 关联**。但在 `0x6AB910` 处出现 `"CLIENTCHAL"` 字面标签（VA `0xC5B144`），为客户端挑战语义的字符串线索（非调用边证据）。
- **与协商对象关系**：处理函数 `0x6AB310` 自身**创建** `[edi+0x5F4]` 对象（`0x6AB9DA`）。
- **与 HMAC/接收计数器**：无。此分支不调用 `0x6AAE70`。
- **等级**：控制流关联 **PROVEN**；方向 **BLOCKED**。

### 0x83

- **产生位置**：未找到明确的字节写指令（`cmp al,0x83` 仅一处即 `0x6AC1CA`）。成因：该值来自入站帧解析结果（`[ebp-0xE]`），不由本镜像常量直接生成。
- **消费位置**：`0x6AC1CA` → `0x6AC1D6` `call 0xAAB260`（RVA `0x6AB260`）。
- **方向证据**：无直接收发边。
- **与协商对象关系**：间接——`0x6AB260` 是阶段 2 处理函数，前置的 `[+0x5F4]` 对象由阶段 1（`0x6AB310`）创建。
- **与 HMAC/接收计数器**：`0x6AB2ED` 在 `0x6AB260` 成功路径写 `[+0x5D0]=3`（接收计数器被置 3）。
- **等级**：控制流关联 **PROVEN**；方向 **BLOCKED**。

### 0x84

- **产生位置**：未找到字节写常量（同上，来自入站解析）。
- **消费位置**：`0x6AC240`（阶段 2）与 `0x6AC300`（阶段 3）→ 均 `call 0x6A9690`（RVA `0x6A9690`）。
- **方向证据**：无。
- **与协商对象关系**：无直接边。
- **与 HMAC/接收计数器**：两条 0x84 分支**都**调用 `0x6AAA770`（置连接状态 4），即该码在进入处理函数后**立即**触发失败态（`0x6AC269`/`0x6AC329`）。这一点是与其它码的显著差异。
- **等级**：控制流关联 **PROVEN**；语义（为何 0x84 直接失败）**BLOCKED**。

### 0x85

- **产生位置**：未找到字节写常量。
- **消费位置**：`0x6AC2DC` → `0x6AC2F0` `call 0x6AAE70`。
- **方向证据**：**唯一有方向线索的码**。`0x6AAFA4` 读 `[edi+0x5D0]` 并递增后与消息携带值比较，失败置字符串 `"Bad recv counter"`（VA `0xC5B110`），因此该计数器语义为**接收计数器**，偏向入站。
- **与协商对象关系**：**直接**——`0x6AB146` 取 `[edi+0x5F4]` 调用 slot+3（`0xA87D50`）。
- **与 HMAC/接收计数器**：**直接**——16 字节 XOR/OR 比较（`0x6AB0E6..0x6AB12D`）失败置 `"HMAC mismatch"`（VA `0xC5B0EC`）。
- **等级**：控制流与字段关联 **PROVEN**；入站方向 **INFERRED（强）**。

## 3. 汇总表

| 码 | 产生 | 消费 | 方向证据 | 与协商对象 | 与 HMAC/计数器 | 等级 |
|---|---|---|---|---|---|---|
| 0x81 | `0x6AB655`（构造应答） | `0x6AC192` → `0x6AB310` | 无（仅 `CLIENTCHAL` 字符串线索） | **创建者**（`0x6AB9DA`） | 无 | 控制流 PROVEN / 方向 BLOCKED |
| 0x83 | 未找到常量 | `0x6AC1D6` → `0x6AB260` | 无 | 间接（前序对象） | 写 `[+0x5D0]=3` | 控制流 PROVEN / 方向 BLOCKED |
| 0x84 | 未找到常量 | `0x6AC25B`/`0x6AC31B` → `0x6A9690` | 无 | 无直接边 | 两分支均转 `0x6AAA770` | 控制流 PROVEN / 语义 BLOCKED |
| 0x85 | 未找到常量 | `0x6AC2F0` → `0x6AAE70` | 接收计数器语义 | **首次使用者**（slot+3） | HMAC 比较 + 计数递增 | 控制流 PROVEN / 入站 INFERRED(强) |

## 4. 阶段机（`[+0x5CC]` 写入点全量）

| 值 | 写点 | 语境 |
|---|---|---|
| 0 | `0x6A1310` | 会话初始化 |
| 0 | `0x6A13F0` | 释放路径 |
| 1 | `0x6AA470` | 阶段 1 建立（`call 0x6AA230` 后） |
| 任意 | `0x6A154F` | `mov [esi+0x5CC], [ebp+8]` 通用设置器 |
| 2 | `0x6ABB01` | `0x6AB310` 成功收尾 |
| 3 | `0x6AB2ED` | `0x6AB260` 成功收尾（同时写 `[+0x5D0]=3`、`[+0x5D4]=3`） |

读点：`0x6AC178`（分派器）。

**裁定**：阶段 "0→1→2→3" 的字段序列 **PROVEN**；把 1/2/3 命名为"挑战/应答/确认"或"握手 A/B/C" **无独立证据，标 BLOCKED**。

## 5. 不得推断项

- 不得因 `CLIENTCHAL`/`BDDATA` 字符串出现就断言 0x81/0x85 的确切协议语义（字符串是构造器参数，不是调用边）。
- 不得把 0x84 的"直接失败"解释为"非法消息"，因为 `0x6A9690` 的返回语义尚未闭合。
- 不得把 `[+0x5D0]` 的递增方向单独作为 0x81/0x83/0x84 的方向证据。
'''

files["E24_NEGATIVE_EVIDENCE_BOUNDARIES.md"]=r'''# E24 负向证据与边界

> 纪律：静态搜索未命中 ≠ 全局不存在。每条注明范围与未覆盖区域。

## 1. 已执行的否定搜索

| # | 搜索 | 范围 | 结果 | 边界声明 |
|---|---|---|---|---|
| N1 | `0x6AB310` 的 `E8` 引用 | 全 `.text`（RVA `0x1000..0x7AD90B`） | 1 处（`0x6AC192`） | 仅覆盖 `E8`；`FF /2` 等间接形式另测 |
| N2 | `0x6AB310` 的 `E9` 引用 | 全 `.text` | 0 处 | 覆盖 `E9` rel32 |
| N3 | `0x6AB310` 的指针形式 | 全文件 4 字节扫描（VA `00AAB310`、RVA `006AB310`） | 均 0 命中 | 不覆盖运行期计算的指针 |
| N4 | `0x6AB310` 的 `.rimp` 修复 | `.rimp` 全量 0x2A00 字节 | 0 命中 | 覆盖全部修复区 |
| N5 | TLS 回调 | 数据目录 TLS | `AddressOfCallBacks` 数组首元素 = 0 | 覆盖静态 TLS |
| N6 | `[edi+0x5F4]` 写点 | 全 `.text` 中 `disp=0x5F4` 的指令 | 写点 2 个（`0x6AB9B3`、`0x6AB9E7`）；读点 3 个 | 覆盖显式 disp 编码 |
| N7 | `[+0x5CC]` 写点 | 全 `.text` 中 `disp=0x5CC` 的 `C7` 立即数写 | 6 个（见阶段机表） | 未覆盖 `mov [reg],[reg]` 形式的间接写 |
| N8 | `[+0x5F4]` 的 vtable 槽 | vtable `0xC5A31C` 全 16 槽 | 槽+3 = `0xA87D50` | 槽+5 = `0x0DEC9E7A`（`.tvm0`） |

## 2. 未覆盖区域（盲区）

1. **`.data` BSS 表**：`0xACE1B0` 依赖的 `0xD48F48` / `0xD48F64`（cipher 描述符表）位于 `.data` RawSize 之外，磁盘无字节，**内容静态不可得**。
2. **`.tvm0` 内部**：`0xDF4A028`、`0xDF9AA45`、`0xDF6216D`、`0xDF6F97C`、`0xDFCE62D` 等入口仅登记，未解码。
3. **应答→socket 的边**：`0x6AB310` 构造的应答缓冲（`0x6ABAC0` 后填入）未找到到 `send` 的静态调用边。
4. **0x83/0x84/0x85 的产生侧**：入站帧码由 `0xA85AD0`/`0xA85BE0` 解析产生（`.tvm0` 参与），未在本轮展开。
5. **间接写**：`mov [reg],[reg]` 形式的 `[+0x5CC]` 写入未系统排查。

## 3. REFUTED / 更正记录

| 主张 | 来源 | 裁定 |
|---|---|---|
| `0x6AB310` "rel32 搜索得 0，可能经跳板/间接调用" | E-23 `E23_NEXT_GATE_DECISION.md` | **REFUTED**：唯一直接调用者 `0x6AC192`；E-23 自有工具已输出该结果 |
| `[edi+0x5F4]` 写点 "只是字段赋值" | E-23 `E23_INDIRECT_DISPATCH_RECOVERY.md` | **更正**：是"释放旧对象 + 换新对象"对 |
| `0xA87D50` 参数 `(this, buf, buf, len)` | E-23 | **更正**：arg1 ≠ arg2；arg1 是 16 字节块，arg2/arg3 才是 span |
| `0xACE180` 为 "cmp [ecx], len" | E-23 | **更正**：实测 `cmp 0x10, [ecx+4]`，且执行 `memcpy` |

## 4. 不得用作补足的方式

- 不得用 `CLIENTCHAL`/`BDDATA` 字符串断言 0x81/0x85 的确切协议语义。
- 不得用阶段编号 1/2/3 与消息码 0x81/0x83/0x85 的数值邻近推断对应关系（虽实测确有一一对应，但需控件流证据而非数值）。
- 不得把认知完备率表述为协议互通完成率。
'''

for name,content in files.items():
    (OUT/name).write_text(content,encoding="utf-8")
    print("wrote",name,len(content))
