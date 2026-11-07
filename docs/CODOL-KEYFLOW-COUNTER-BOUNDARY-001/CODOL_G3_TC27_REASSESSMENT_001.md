# TC-27 重评估（001）

> 任务：`CODOL-KEYFLOW-COUNTER-BOUNDARY-001`
> 原状态：`BLOCKED-INSUFFICIENT-SPEC`
> 新状态建议：`CONFIRMED-STATIC`；测试状态可由阻塞改为 **PASS（静态行为记录）**，但不得标为运行时 PASS。

## 1. 直接证据

冻结恢复镜像：`codol2697-static-candidate.bin`
SHA-256：`24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4`

接收函数 `0x00AAAE70` 内的关键序列：

```text
0x00AAAFA4  mov eax, dword ptr [edi+0x5D0]  ; old expected
0x00AAAFAA  lea edx, [eax+1]                ; new expected, modulo 2^32
0x00AAAFAD  mov dword ptr [edi+0x5D0], edx  ; store before compare
0x00AAAFB3  cmp dword ptr [ebp-0x224], eax  ; compare frame seq to old expected
0x00AAAFB9  je  0x00AAAFFD                  ; only old-expected equality passes
```

函数范围内对 `[edi+0x5D0]` 的扫描结果只有这两条引用：

- `0x00AAAFA4`：读；
- `0x00AAAFAD`：写。

同一范围没有 `jo`、`jc`、`0xFFFFFFFF` 比较或饱和分支。控制流也没有在比较失败时恢复旧值。

## 2. `0xFFFFFFFF -> 0` 静态行为

| 步骤 | 值 |
|---|---:|
| 旧 expected | `0xFFFFFFFF` |
| 收到 seq | `0x00000000` |
| 计算的新 expected | `0x00000000` |
| 比较左/右 | `0x00000000` / `0xFFFFFFFF` |
| 比较结果 | 不等 -> reject |
| 回写后的 expected | `0x00000000` |

因此：

- **拒绝**回绕后的 `0` 帧：`CONFIRMED-STATIC`。
- **接收期望值发生 32 位回绕**为 `0`：`CONFIRMED-STATIC`。
- **失败时仍保留旧 expected**：`REFUTED`。

## 3. 失败后的连接状态

失败路径调用 `0x00AAA770`，其中：

```text
0x00AAA791  mov dword ptr [esi+0xC8], 4
```

`0x00AAC0C0` 调度器在 `0x00AAC0EA` 检查状态 4：

```text
cmp dword ptr [esi+0xC8], 4
jne ...
```

状态为 4 时不再处理该对象。静态上可以确认“计数器被写为 0、状态被写为 4”；但不能仅凭此证明外部连接生命周期，因此：

- 同一连接下下一次 seq=0 是否会被处理：`UNRESOLVED`；
- 是否立即断开、重连或复用对象：`UNRESOLVED`；
- 是否存在外部状态重置后再接受 seq=0：`UNRESOLVED`。

## 4. 发送侧同边界

发送函数 `0x00AAAA10`：

```text
0x00AAAB4C  mov eax, dword ptr [edi+0x5D4]  ; frame uses current value
...
0x00AAADA2  inc dword ptr [edi+0x5D4]       ; after successful send
```

- 当前发送值为 `0xFFFFFFFF` 时，帧 seq 写为 `0xFFFFFFFF`。
- 成功发送后发送计数器自然变为 `0x00000000`。
- 发送侧无额外溢出分支；状态：`CONFIRMED-STATIC`。

## 5. TC-27 的新判定

原测试允许“接受或拒绝，需记录”。现在行为已被直接记录：

```text
expected=0xFFFFFFFF, incoming=0
=> reject
=> expected becomes 0
=> connection state becomes 4
=> later dispatch behavior UNRESOLVED
```

建议登记：

```text
TC-27 = PASS (STATIC BEHAVIOR RECORDED)
```

该 PASS 的含义仅是“冻结静态行为已确定并记录”，**不是**运行时通过，也不证明真实服务端会允许或拒绝同一回绕序列。

## 6. 对 G3 的影响

- TC-27 的 `BLOCKED-INSUFFICIENT-SPEC` 可由本任务静态证据关闭。
- 原 G3 中“失败时 expected 不变”的序列号模型被修正为“先递增、后比较”。
- 重复/跳号的接受/拒绝结果不变，但失败后的状态不同。
- G3 仍不能因此自动升级为无条件通过：错误路径的连接后果、运行时行为和大长度兼容性仍未闭合。
- 实时互通仍为 **NOT-OBSERVED**。