import os
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E19_DEMONWARE_SESSION_OBJECT_DATAFLOW_001"
F={}
F["E19_788133_ATTRIBUTION.md"]="""# E19 — 0x788133 归属 / ATTRIBUTION

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
"""
F["E19_APPLICATION_CONSUMER_MAPPING.md"]="""# E19 — 应用层消费者映射 / APPLICATION CONSUMER MAPPING

> 等级：PROVEN / INFERRED / BLOCKED / REFUTED
> 前置：仅在实际数据到达后映射。

---

## 1. 已知候选对照（4 层闭包审计）

`0x6ABBC0` 的 4 层下游闭包（48 个函数）中：

| 候选 | 是否在闭包内 | 裁定 |
|---|---|---|
| 0xA2660（Configstring body reader） | **否** | 未连接 |
| 0xA2E50（reliable payload 候选） | **否** | 未连接 |
| 0x350170（demo 顶层分派器） | **否** | 未连接 |
| 0x3547D0（子帧循环） | **否** | 未连接 |
| 0x354100（子帧分派器） | **否** | 未连接 |

**裁定（REFUTED，限定范围）：未与任何已知游戏解析候选建立调用或数据流连接。**

## 2. 已有的下游消费者（PROVEN）

| 消费者 | 语义 | 是否应用层 |
|---|---|---|
| 0x6878A0 | 边界检查 + memcpy | 通用内存 |
| 0x6A9920 | 类型码 + 载荷读取 | **协议层**（非游戏应用层） |
| 0xAA84E0 | 对象分配（+0xB0） | 通用 |
| 0x6A9300 | 记录时间戳/长度（`[esi+0x498]++`，写 `[esi+0x2B8+k*4]`） | 统计/日志 |
| 0x6A93C0 | （状态 0 分支，未展开） | 未知 |
| 0x6AA770 | 清理 + 置状态 4 | 连接管理 |

**裁定（PROVEN / BLOCKED）：下游均为协议分帧、内存管理与统计，未见游戏应用层解析。**

## 3. 是否存在 opcode / 序列号 / 消息类型读取

| 检查 | 结果 |
|---|---|
| 长度字段 | **是**（4 字节前缀 → 0x6ABBC0） |
| 类型码 | **是**（1 字节 → 0x6A9920，cmp 1/2） |
| 序列号 | 未观察到 |
| 游戏 opcode（1..4 表） | **未见** |
| 子帧编号（0..8 表） | **未见** |

## 4. 是否为游戏协议消费者

| 判据（任务书判定标准） | 结果 |
|---|---|
| 可复核的指令级证据 | 有（分帧/状态机/类型码） |
| 必要数据流链 | 有（recv → 头 → 长度 → 载荷） |
| 数据进入游戏会话处理 | **未证**（类型码 1/2 与游戏 opcode 不同域） |
| 应用层消费者 | **未定位** |

**裁定（BLOCKED）：未找到游戏应用层消费者。**

## 5. 裁定

| 项 | 裁定 |
|---|---|
| 分帧与类型码读取 | PROVEN |
| 与已知游戏解析器连接 | REFUTED（限定范围） |
| 首个游戏应用层消费者 | BLOCKED |
| 类型码语义 | BLOCKED |
"""
for n,c in F.items():
    open(os.path.join(wd,n),"w",encoding="utf-8",newline="\n").write(c)
print("wrote",len(F))
