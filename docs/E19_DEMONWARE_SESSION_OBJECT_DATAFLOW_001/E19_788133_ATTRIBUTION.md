# E19 — 0x788133 归属 / ATTRIBUTION

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED

---

## 1. 是否为真实网络原语调用点（PROVEN）

    78812E  push 0
    788130  push edx
    788131  push ebx
    788132  push esi
    788133  call dword [0xBAE490]     ; recv（IAT 直接调用）
    788139  test eax,eax / jns
    78813D  mov esi,[0xBAE4DC]        ; WSAGetLastError
    788143  call esi
    788145  cmp eax,0x2733 / je 0xB88172
    78814C  call esi
    78814E  cmp eax,0x2733 / je 0xB88172
    788157  mov eax,0xFFFFFFFE        ; -2

**裁定（PROVEN）：`0x788133` 是真实的 `recv` **直接调用点**，不是 thunk（函数体内含错误处理逻辑）。**

## 2. 所属函数边界（PROVEN，更正 E-13/E-16 记录）

| 项 | 值 |
|---|---|
| callgraph 归属 | `0x78772D`（prologue 启发式） |
| **真实 prologue** | **0x787B2F 附近**（最近 `push ebp`） |
| 差异原因 | `0x78772D` 与其后函数间存在无标准 prologue 的代码块，启发式失效 |
| 真实函数职责 | 含 recv + 错误码 0x2733（WSAEWOULDBLOCK）处理 |

**裁定（PROVEN）：`0x788133` 的真实所属函数≠`0x78772D`（时间戳函数）。这更正了 E-16 的"0x78772D 区段"标注。**

## 3. 与 `0x6ABBC0` 的关系（REFUTED）

| 检查 | 结果 |
|---|---|
| 直接调用边 | 无 |
| 数据流 | 无共享缓冲区/对象 |
| 4 层闭包大小 | 0x6ABBC0=48 函数；0x78772D 段=140 函数 |
| 共享下游 | 3 个（0x749B31 cookie 检查、0x3622AC、0x755F08）——**均为通用工具函数** |

**裁定（REFUTED，限定范围）：`0x788133` 与 `0x6ABBC0` 状态机**不属同一路径**；仅共享通用工具函数，不构成路径证据。**

## 4. 是否扩大扫描

按任务书要求：**不扩大**。已记录归属与关系，停止。

## 5. 裁定

| 项 | 裁定 |
|---|---|
| 是否 recv 直接调用点 | PROVEN（是） |
| 是否 thunk | REFUTED |
| 真实所属函数 | 更正为 0x787B2F 附近的函数 |
| 与 0x6ABBC0 关系 | REFUTED（无关系） |
| 与状态机同路径 | REFUTED（限定范围） |
