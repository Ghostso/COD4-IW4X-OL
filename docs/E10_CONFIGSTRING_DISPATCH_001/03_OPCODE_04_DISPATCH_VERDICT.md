# 03 — 外层 0x04 分派裁定 / OPCODE 0x04 DISPATCH VERDICT

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


## 7. 层归属补正（新增，重要）

本轮复核出一条会改变解释的层级事实：

```
0xA21B8 _CODOL2697_WriteGamestate
  |- 0xA224C WriteByte(3)                     ; 顶层 opcode = 0x03
  |- 0xA225A WriteInt32(version)
  |- 0xA2269/0xA2279 WriteLenStr(map) / WriteLenStr(mode)
  |- 0xA2288 WriteInt32(field4)
  |- 0xA22C1 call 0xA0468 _CODOL2697_WriteConfigstrings   <- 内层帧
  |       |- 0xA07F8 WriteByte(4)              ; * 0x04 是 Gamestate 内部帧头
  |       |- 0xA0807 WriteShort(count1)
  |       |- ... A1/A2/A3 ...
  |       |- 0xA0997 WriteByte(6)
  |- 0xA22D9 WriteInt32(fieldC)
  |- 0xA22E8 WriteInt32(field8)
  `- 0xA22F8 WriteByte(6)                      ; 顶层 Gamestate 尾
```

**结论（DIRECT）：** 任务书所称的“外层 `0x04`”是**相对于 Configstring body 的外层**，即 **Gamestate 内部子帧的帧头**；它**不是**顶层 wire opcode（顶层是 `0x03`）。

| 层 | 标识 | 证据 |
|---|---|---|
| 顶层 wire opcode | `0x03`（Gamestate） | 服务端 `0xA224C`；客户端 `0x354100` 键域 0..8 |
| Configstring 内层帧头 | `0x04` | 服务端 `0xA07F8`（位于 `0xA22C1` 调用内） |
| Configstring 内层尾 | `0x06` | 服务端 `0xA0997` |
| Gamestate 顶层尾 | `0x06` | 服务端 `0xA22F8`（**与上行不同层，禁止合并**） |

**因此：** 客户端 `0x354100` 的 9 项跳转表是**顶层**消息分派器，**不是**内层 `0x04` 的分派器。内层 `0x04` 的客户端处理仍为 **BLOCKED**（`0x352F80` 的 +1 字节为强 INFERRED）。
