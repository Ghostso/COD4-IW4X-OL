# CODOL 计数值回绕静态审计（001）

> 任务：`CODOL-KEYFLOW-COUNTER-BOUNDARY-001`
> 范围：只读静态审计冻结的 2.6.9.7 客户端；未启动游戏/服务端，未注入，未联网，未修改正式二进制。
> 对象：Keyflow 发送序号 `[obj+0x5D4]` 与接收期望序号 `[obj+0x5D0]`。
> 结论状态：`CONFIRMED-STATIC`、`MODEL-ONLY`、`CONFLICTING-EVIDENCE`、`UNRESOLVED` 按项标注。

## 1. 基线

| 项 | 值 |
|---|---|
| 打包客户端 | `D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe` |
| 打包客户端 SHA-256 | `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1` |
| 静态反汇编样本 | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin` |
| 恢复镜像 SHA-256 | `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4` |
| ImageBase | `0x00400000` |
| 静态证据 | `_data/counter_boundary_static_evidence.json` |
| 原始 G3 输入 | `CODOL-KEYFLOW-G3-FRAME-VALIDATION-001/`，本轮只读 |
| 历史追踪 | `CODOL_KEYFLOW_EVIDENCE_TRACE_001.csv` 的 KF-19/KF-20；本轮重新反汇编核对 |

## 2. 结论摘要

| 结论 | 状态 |
|---|---|
| 发送序号和接收期望序号均存储为 32 位 dword | `CONFIRMED-STATIC` |
| 帧内序号为 4 字节、x86 little-endian 写读 | `CONFIRMED-STATIC` |
| 发送路径：帧使用当前发送值，成功发送后 `inc`，无溢出检查 | `CONFIRMED-STATIC` |
| 接收路径：先计算并写回 `expected+1`，再与旧 `expected` 做相等比较 | `CONFIRMED-STATIC` |
| 接收失败路径同时把连接状态置为 `4`；分发器在状态 `4` 时提前返回 | `CONFIRMED-STATIC` |
| `expected=0xFFFFFFFF`、收到 seq `0` 时：比较失败，期望值已变为 `0` | `CONFIRMED-STATIC` |
| 同一连接后续是否还能处理 `seq=0` 或其他帧 | `UNRESOLVED`（状态 `4` 后的生命周期未在本任务闭合） |
| 原 G3 序列号模型“失败时期望值不变” | `CONFLICTING-EVIDENCE`，应被本报告替代 |

## 3. 发送路径：`0x00AAAA10`

函数范围：`0x00AAAA10..0x00AAAE60`。该范围共反汇编 344 条指令，涉及 `[edi+0x5D4]` 的只有两条：

| 地址 | 指令 | 作用 |
|---|---|---|
| `0x00AAAB4C` | `mov eax, dword ptr [edi+0x5d4]` | 读取当前发送序号 |
| `0x00AAADA2` | `inc dword ptr [edi+0x5d4]` | 成功组装/发送后递增 |

关键顺序：

1. `0x00AAAB4C` 读取当前计数器。
2. 该值被写入 0x85 帧的 seq 字段（4 字节 copy/write 路径）。
3. 只有最终 `test bl,bl` 通过、帧进入输出队列后，`0x00AAADA2` 才执行。
4. `inc dword ptr` 没有与 `0xFFFFFFFF`、溢出标志或饱和值比较的分支。

因此静态结论为：

```text
发送帧 seq = 计数器的当前 32 位值
成功发送后计数器的下一个值 = (旧值 + 1) mod 2^32
```

发送侧不存在显式回绕处理、失败恢复或饱和分支；它是普通 32 位回绕。

## 4. 接收路径：`0x00AAAE70`

函数范围：`0x00AAAE70..0x00AAB25A`。该范围共反汇编 307 条指令，涉及 `[edi+0x5D0]` 的只有两条：

| 地址 | 指令 | 作用 |
|---|---|---|
| `0x00AAAFA4` | `mov eax, dword ptr [edi+0x5d0]` | `eax = old_expected` |
| `0x00AAAFAD` | `mov dword ptr [edi+0x5d0], edx` | 写回新值，`edx = eax + 1` |

完整相邻序列：

```text
0x00AAAFA4  mov eax, [edi+0x5D0]     ; old_expected
0x00AAAFAA  lea edx, [eax+1]         ; 32-bit addition, wraps naturally
0x00AAAFAD  mov [edi+0x5D0], edx     ; store new_expected before comparison
0x00AAAFB3  cmp [ebp-0x224], eax     ; compare frame seq with old_expected
0x00AAAFB9  je  0x00AAAFFD           ; equality -> continue
```

失败时 `0x00AAAFBB..0x00AAAFBD` 设置 `Bad recv counter` 诊断引用，随后走 `0x00AAAFC7..0x00AAAFDD` 错误清理。该范围内没有第二条对 `[edi+0x5D0]` 的恢复写入，也没有 `cmp ...0xFFFFFFFF`、`jo`、`jc` 或饱和分支。

### 4.1 回绕边界

当 `old_expected = 0xFFFFFFFF` 且收到的 seq 为 `0`：

```text
old_expected = 0xFFFFFFFF
new_expected = (0xFFFFFFFF + 1) mod 2^32 = 0x00000000
compare operand = old_expected = 0xFFFFFFFF
received seq    = 0x00000000
result          = mismatch -> reject
stored expected = 0x00000000
```

这是对比较顺序的直接静态结论。**不能**把它描述为“客户端接受回绕后的 0 帧”；该帧在这一条接收路径上比较失败。

### 4.2 错误路径的状态变化

失败出口调用 `0x00AAA770`。该函数在 `0x00AAA791` 执行：

```text
mov dword ptr [esi+0xC8], 4
```

反汇编调度器 `0x00AAC0C0` 在入口 `0x00AAC0EA` 检查：

```text
cmp dword ptr [esi+0xC8], 4
jne ...
```

状态为 `4` 时调度器直接返回，不再进入当前对象的消息处理。因此：

- 计数器已经回绕为 `0`，这是 `CONFIRMED-STATIC`；
- 同一连接对象的下一次分发是否会处理 seq `0`，在当前证据下是 `UNRESOLVED`；
- “会接受下一次 0”或“会恢复原值”都不能从当前静态链推出。

### 4.3 顺序与 HMAC/解密

接收函数的控制流在序列号检查之后才进入 HMAC 路径：

- 密文长度/对齐检查：`0x00AAAF73..0x00AAAF98`
- 序列号读取/回写/比较：`0x00AAAFA4..0x00AAAFB9`
- 序列号相等后跳到 `0x00AAAFFD`
- HMAC 更新/比较：`0x00AAB074..0x00AAB12D`
- AES 解密：`0x00AAB140`

因此序列号期望值的推进发生在 HMAC/解密成功之前。HMAC 或后续明文校验失败时，回写过的期望值不会在该函数范围内恢复。连接状态处理仍属于 `UNRESOLVED` 的外部后果。

## 5. 初始化/重置路径

`0x00AAB260..0x00AAB303` 是 0x83 认证完成处理函数。成功返回路径在 `0x00AAB2D4` 执行：

```text
lea ebx, [eax+1]     ; eax=0 on the success condition -> ebx=1
mov [esi+0x5D0], ebx ; receive expected = 1
mov [esi+0x5D4], ebx ; send counter = 1
mov [esi+0x5CC], 3   ; phase = established
```

这是认证完成后的初始化，不是回绕处理。它可以解释计数器重新开始为 1；不能解释 `0xFFFFFFFF` 边界本身。

## 6. 宽度、字节序与有符号性

| 项 | 结论 | 证据 |
|---|---|---|
| 存储宽度 | 32-bit dword | `mov/inc dword ptr [edi+0x5D0/0x5D4]` |
| 帧字段宽度 | 4 bytes | `push 4` 与 4B copy/write 调用 |
| 字节序 | little-endian | x86 dword store/copy；抓包 seq=1 为 `01 00 00 00` |
| 发送递增 | 32-bit modulo 2^32 | `inc dword ptr`，无溢出检查 |
| 接收递增 | 32-bit modulo 2^32 | `lea edx,[eax+1]`，32-bit 算术 |
| 比较有符号性 | 不适用 | 使用 `cmp` + `je`，只判断相等；不依赖有符号大小 |

## 7. 对照原 G3 模型

原 G3 的本地序列号模型为：

```text
if incoming != expected: reject and leave expected unchanged
```

新反汇编证据显示：

```text
old = expected
expected = (old + 1) mod 2^32   ; happens before comparison
if incoming != old: reject
```

因此：

| 用例 | 原模型 | 冻结客户端静态语义 |
|---|---|---|
| 正常 seq=expected | accept，expected+1 | accept，expected+1 |
| 重复 seq=expected-1 | reject，expected 不变 | reject，expected 已推进一层 |
| 跳号 seq>expected | reject，expected 不变 | reject，expected 已推进一层 |
| FFFFFFFF -> 0 | blocked，候选 A reject / 候选 B accept | reject，expected 写为 0；随后状态置 4 |

该差异不改变重复/跳号的**接受/拒绝结论**，但改变失败后的状态模型。原 G3 边界报告中的“expected 不变”应标记为已被本审计取代。

## 8. 最终判定

- **发送回绕：`CONFIRMED-STATIC`。** 成功发送后自然 modulo 2^32。
- **接收回绕：`CONFIRMED-STATIC` 到计数器/比较层。** `0` 在旧 expected 为 `0xFFFFFFFF` 时比较失败；回写值为 `0`。
- **后续连接行为：`UNRESOLVED`。** 错误路径设置状态 4，当前对象后续分发被阻断；外部重连/重置生命周期未闭合。
- **原 G3 无状态变化模型：`CONFLICTING-EVIDENCE`。** 必须用“先递增、后比较”的模型替代。
- **运行时结论：`NOT-OBSERVED`。** 本报告没有启动客户端或服务端。