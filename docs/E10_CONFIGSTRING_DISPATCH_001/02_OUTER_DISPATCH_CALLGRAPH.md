# 02 — 外层分派调用图 / OUTER DISPATCH CALLGRAPH

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
| 函数入口 | RVA `0x352F80`（前驱 `0x352E80` 在 `0x352F24` 已 `ret`） | DIRECT |
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
| case 7 | `0x354740` 经同一函数指针读 1 字节到 `[esi+0x723c24]` | DIRECT |
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


## 8. 层级补正（见 03 §7）

`0x04` 是 **Gamestate 内部子帧帧头**（服务端 `0xA22C1` 调用 `0xA0468` 后由 `0xA07F8` 写入），顶层 opcode 为 `0x03`。

因此：
- `0x3547D0` + `0x354100`（9 项）是**顶层**分派器，键域 0..8；
- 它**不**负责内层 `0x04` 的判定；
- 内层 `0x04` 的客户端判定仍为 **BLOCKED**，仅由 `0x352F80` 的 +1 字节行为给出强 INFERRED。
