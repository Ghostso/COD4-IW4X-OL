# CLIENT_STATE_TRANSITIONS — 客户端连接状态机与 OOB 状态门

**分析对象：** `image_best.bin`，`17cef6e0…`
**地址约定：** `file_offset = RVA = VA - 0x400000`

---

## 1. 连接状态全局量（本轮直接读到）

| 全局 VA | 引用它的关键位置 | 用途 | 等级 |
|---|---|---|---|
| `0x076446B0` | `0x1C0607`（OOB 发送器）、`0x6D06A` 区域、共 **240** 处 imm32 引用 | **连接状态**（0..6 取值域） | **CONFIRMED**（作为状态量） |
| `0x076446A2` | `0x208386`（`cmp byte […],0`） | 布尔门（增量路径） | **CONFIRMED**（存在）/ 语义 `UNKNOWN` |
| `0x076446D8` | `0x1C0790` | 布尔门（OOB 分支） | **CONFIRMED**（存在）/ 语义 `UNKNOWN` |
| `0x0331C0C8` | `0x1C0611` | 被 `xor 0xD362501F` 解密的指针 | **CONFIRMED**（存在）/ 目标对象 `UNKNOWN` |
| `0x082C3B58` | `0x5F836` / `0x2083AD` / `0x6D064` | **本地客户端索引** | **CONFIRMED** |
| `0x01C1D188` | `0x5F83F` / `0x2083B3` / `0x6D069` | **客户端对象表**（`[idx*4 + …]`） | **CONFIRMED** |
| `0x0C7AF6A8` | `0x1C0693` | 时间基准（与 `[ebx+8]`/`[ebx+0x30]` 相减） | **CONFIRMED**（作为时间源） |
| `0x00E3F240` | 各函数序言 | 栈金丝雀（`__security_cookie`） | **CONFIRMED** |

> 说明：`0x76446B0` 等位于未初始化 `.data`（超出文件 raw 长度），因此静态读到的字节为 `OUT`；这不影响其**引用点**证据。

---

## 2. 连接状态取值域（`[0x76446B0]`）

在本目标中被直接比较的取值：

```
0x1C0635  cmp [0x76446B0], 3   ; 允许
0x1C063A  cmp [0x76446B0], 4   ; 允许
0x1C063F  cmp [0x76446B0], 6   ; 允许
0x1C0644  cmp [0x76446B0], 5   ; 允许
0x1C0647  jne -> 直接返回       ; 其余值 = 不发送 OOB
```

**OOB 命令按状态换算：**
```
0x1C06FB  add eax, -3
0x1C06FE  cmp eax, 3
0x1C0701  ja  -> 0x1C0F0C
0x1C0707  jmp dword ptr [eax*4 + 0x5C0F3C]
```

| `[0x76446B0]` | 索引 `eax-3` | 分支入口 | OOB 命令（已证字面量） |
|---|---:|---|---|
| **3** | 0 | `0x1C070E` | **`getchallenge 0 "%s"`** |
| 4 | 1 | `0x1C0776` | 未命名（走 `%08x%08x` 令牌构造） |
| 5 | 2 | `0x1C0E07` | `stats` 族（`0xDBFE38`）+ 0x800 缓冲 |
| 6 | 3 | `0x1C0EBB` | **`heartbeat`** |

**状态 3 → 挑战，状态 6 → 心跳** 是**强证据**：两条分支的字面量分别被 `push` 进
构造调用，且构造参数来自同一对象 `[ebx+0x14..0x28]`。

---

## 3. 三级门（OOB 发送的完整前置条件）

```
门 1（状态）  : [0x76446B0] ∈ {3,4,5,6}            否则 0x1C0F1B 返回
门 2（对象）  : ecx != 0 && ebx != 0
                && [ebx+0x100260] != 1              否则 0x1C0F1B 返回
门 3（节流）  : 状态 3/4 -> (now - [ebx+0x30]) >= 0xBB8  (3000 ms)
                状态 5   -> (now - [ebx+8])  >= 0x64   (100)
                状态 6   -> (now - [ebx+8])  >= 0x1F4  (500)
```

**已证**：三个门各自的条件与目标地址（`CONFIRMED`）。
**未证**：`[ebx+8]` / `[ebx+0x30]` / `[ebx+0x100260]` 的**精确语义**（`INFERRED`：分别近于
"上次命令时间" / "上次状态时间" / "进行中标志"）。

---

## 4. 状态机的可观测结果（错误码字面量）

| 字面量 | 字符串 VA | 关联分支 |
|---|---|---|
| `EXE_HOSTUNREACH` | `0x00DB45C4` | `0x1C0687`（跳表 A 的 `[0]`/`[3]` → `0x1C067A` 分支，`0x1BE700` 判定失败） |
| `EXE_CLIENTFAILEDTOCHALLENGE` | `0x00DBB708` | `0x1C076A`（挑战校验失败分支，`push` + `push 2`） |
| `EXE_MATCHENDED` | `0x00DBB314` | 见 `0x5BF9EA` 区域的匹配结束路径 |
| `EXE_DISCONNECTED` | `0x00DBB300` | 见 `0x5BF9EA` 区域 |

**`EXE_CLIENTFAILEDTOCHALLENGE` 的存在是本轮的重要旁证**：它证明目标客户端**确实**会
对挑战应答做校验，并把失败上报为可观测错误码。这与 `challengeResponse` 字面量
（引用点 `0x1C1684`，容器函数 `0x1C13A0`）互相印证。

---

## 5. 与冻结服务器状态模型的对照（只读）

| 冻结服务器 | 目标 | 判定 |
|---|---|---|
| `ClientState`：Free → Connected → ClientLoading → Active（来源：`sv_client_mp.cpp`，同构建**服务端**源码） | 目标客户端存在 `[0x76446B0]` 状态量，取值域含 3/4/5/6 | **方向一致**，但**取值映射不同**（服务端 0..3 vs 客户端 3..6） |
| `slot->state = ClientState::Active` @ `gamestateupdate stage==6` | 目标状态 6 对应 **`heartbeat`** OOB 构造（非 Active 赋值） | **不可直接套用** |
| `nextSnapshotTime = now`，`deltaMessage = -1` | 目标侧**未定位** | **暂缓** |

**结论：** 冻结服务器的 `ClientState` 枚举**不能**用于目标客户端的 `[0x76446B0]`。
两者是不同的状态空间（服务端 slot 状态 vs 客户端连接阶段）。**不得混用。**

---

## 6. 本轮可用的状态机事实汇总（供测试向量使用）

| 事实 | 等级 |
|---|---|
| `[0x76446B0] ∈ {3,4,5,6}` 才允许发送 OOB | **CONFIRMED** |
| 状态 3 → `getchallenge 0 "%s"` | **CONFIRMED** |
| 状态 6 → `heartbeat` | **CONFIRMED** |
| 状态 3/4 节流 3000 ms | **CONFIRMED** |
| 状态 5 节流 100、状态 6 节流 500 | **CONFIRMED** |
| 挑战失败上报 `EXE_CLIENTFAILEDTOCHALLENGE` | **CONFIRMED** |
| 主机不可达上报 `EXE_HOSTUNREACH` | **CONFIRMED** |
| 状态 4 的具体命令文本 | `UNKNOWN` |
| 状态 5 的 `stats` 具体格式 | `UNKNOWN` |
| 状态值与"已连接/加载中/活动"的**业务命名** | `UNKNOWN` |

> 以上 7 条 `CONFIRMED` 是本轮**唯一**可进入离线测试向量设计的状态机事实。
