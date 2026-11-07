# 03 — 游戏协议字符串 → handler 反向追踪

对每个锚点:`字符串 VA/RVA/文件偏移 → 代码 xref → 所在函数 → 上游调用者 →
字符串在控制流中的使用方式 → 归属(协议解析 / 状态转换 / 错误处理 / UI)`。

文本层字符串的 xref 是 `push imm32`形式的 dword 立即数,因此用裸 dword 搜索即可定位。

---

## 1. 锚点总表

| 字符串 | VA | RVA(=off) | xref 站点 | 所在函数 | 上游调用者 | 使用方式 | 归属 |
|---|---|---|---|---|---|---|---|
| `gamestateupdate %d` | 0x00DB4700 | 0x9B4700 | 0x054B7B | 0x053760..0x0554C0 | 0x0555D0, 0x115340 | `push` 作格式串 → 0x774980 | 引擎状态/主机 |
| 同上 | | | 0x073214 | 0x073200..0x073260 | 0x053760, 0x073260, 0x073A50, 0x1C0310 | `push` 作格式串 → 0x774980 | 引擎状态/主机 |
| `EXE_CONFIGSTRINGMISMATCH` | 0x00DB46E4 | 0x9B46E4 | 0x0731E1 | 0x073180..0x073200 | 0x073409 | `push` → 0x4F82E0 (错误打印) | 错误处理 |
| 同上 | | | 0x0F2833 | 0x0F2350..0x0F2900 | 0x1BF502, 0x37DDE8 | 命令串表分支 → 0x4F82E0 | 错误处理/命令 |
| `EXE_LOSTRELIABLECOMMANDS` | 0x00DBB5E8 | 0x9BB5E8 | 0x0F2737 | 0x0F2350..0x0F2900 | 0x1BF502, 0x37DDE8 | 命令串表分支 | 错误处理 |
| 同上 | | | 0x376B14 | 0x376A60..0x376B50 | **13 个**(见 §3) | `push` → 0x5B87D0 (错误上报) | 错误上报点 |
| `EXE_SERVERCOMMANDOVERFLOW` | 0x00DBB584 | 0x9BB584 | 0x0F26C7 | 0x0F2350..0x0F2900 | 0x1BF502, 0x37DDE8 | 命令串表分支 | 错误处理 |
| `EXE_SERVERMESSAGEOVERFLOW` | 0x00DBB5A0 | 0x9BB5A0 | (同族) | 0x0F2350..0x0F2900 | 0x1BF502, 0x37DDE8 | 命令串表分支 | 错误处理 |
| `CA_GAMESTATE` | 0x00DC0974 | 0x9C0974 | 0x1C809D | 0x1C8060..0x1C8150 | 0x37DC99 | `push 4` 后调用 → 0x4F82E0 | 状态机/日志 |
| `EXE_AWAITINGGAMESTATE` | 0x00DC5F1C | 0x9C5F1C | 0x20C14C | 0x20C130..0x20C190 | 0x20C225 | `push 2` + 报错 | 错误处理 |
| `connectResponse` | 0x00DBFF0C | 0x9BFF0C | 0x1C17B5 | 0x1C13A0..0x1C1EE0 | **0x1C2040, 0x1C2112** | `push` 后 `strcmp` 分派 | **协议分派** |
| `challengeResponse` | 0x00DBFEE8 | 0x9BFEE8 | 0x1C1685 | 0x1C13A0..0x1C1EE0 | 0x1C2040, 0x1C2112 | `strcmp` 分派 | **协议分派** |
| `connectReject` | 0x00DBFEFC | 0x9BFEFC | 0x1C1756 | 0x1C13A0..0x1C1EE0 | 0x1C2040, 0x1C2112 | `strcmp` 分派 | **协议分派** |
| `heartbeatresponse` | 0x00DBFF1C | 0x9BFF1C | 0x1C18B6 | 0x1C13A0..0x1C1EE0 | 0x1C2040, 0x1C2112 | `strcmp` 分派 | **协议分派** |
| `statResponse` | 0x00DBFF30 | 0x9BFF30 | 0x1C1964 | 0x1C13A0..0x1C1EE0 | 0x1C2040, 0x1C2112 | `strcmp` 分派 | **协议分派** |
| `disconnect_ack` | 0x00DBFF40 | 0x9BFF40 | 0x1C1B0B | 0x1C13A0..0x1C1EE0 | 0x1C2040, 0x1C2112 | `strcmp` 分派 | **协议分派** |
| `getchallenge 0 "%s"` | 0x00DBFD04 | 0x9BFD04 | 0x1C071F | 0x1C05F0..0x1C0F50 | (发送构造) | **格式串** → 0x774900 组帧 | **协议构造** |
| `connect %s "%s"` | 0x00DBFE28 | 0x9BFE28 | 0x1C0D6F | 0x1C05F0..0x1C0F50 | (发送构造) | 格式串 | **协议构造** |
| `process snapshots` | 0x00DBEBD0 | 0x9BEBD0 | 0x14B5F8 | 0x14B3F0..0x172100 | 0x0746CA, 0x2177E8 | `push -1` → 0x66D930 (日志) | 客户端快照处理区 |
| `ExpectedNetConfigStringMismatch` | 0x00DB4D98 | 0x9B4D98 | 0x0778D7 | 0x077760..0x077910 | 11 个上游(UI/状态) | 格式串 → 0x4F82E0 | 错误处理 |
| `CG_ServerCommand: ` | 0x00DC61AD | 0x9C61AD | (无 dword xref) | — | — | 静态字面量,未被引用 | 未使用注释 |

---

## 2. 逐项分析

### 2.1 `EXE_LOSTRELIABLECOMMANDS`(可靠命令锚点)

**使用点 `0x376B14`** 位于函数 `0x376A60..0x376B50`:

```
376A70  imul edi,edi,0x824            ; 每个客户端 0x824 字节
376A76  mov eax,[edi+0x81918DC]
376A82  lea ecx,[eax+edx]
376A85  cmp ecx,0x3E8                 ; 与 1000 比较
376A8D  mov esi,[edi+0x28]
376A94  cmp eax,0x3E8 ; jge ...
376A9F  call 0x7769F0                 ; 上报/复位
376AB0  lea ecx,[edi+0x414]           ; 20 * 0x34 表遍历
...
376B0B  cmp dword ptr [0x84B0E48], edi ; 若计数非 0
376B13  push 0xDbb5E8                 ; <- "EXE_LOSTRELIABLECOMMANDS"
376B1B  push 0x84AeFF8
376B20  call 0x5B87D0                 ; 错误上报
```

**判定:这是「可靠命令丢失 / 溢出」的**错误上报点**,不是分派点,也不是 ACK 处理。**
证据:控制流在 `0x376B20` 调用统一的错误上报函数 `0x5B87D0`(同族中 `0xF2350` 的
`EXE_*` 分支也走 `0x4F82E0`);没有任何「读包 → 表选择 → 调用处理」的特征。

**反向追踪:** 该函数 `0x376A60` 的 13 个上游调用者(046 记录,本轮复现):

`0x07A662, 0x07EBEA, 0x07F702, 0x081338, 0x081F57, 0x1B7D11, 0x1B8882,
 0x1B9516, 0x1BAE87, 0x1BC009, 0x1BC5C2, 0x1BC8F1, 0x376B7E`

其中 `0x376B7E` 与字符串使用点同函数相邻(距离 1 字节),属同一上报路径。
其余 12 个分布在 0x07xxxx / 0x1Bxxxx 两个引擎区域,**没有一个**落在 P4/P5 簇内。

**不能排除:** 这些调用者本身可能是网络事件处理函数(引擎 netchan 的上层),
但**本轮没有指令级证据**把它们的输入连到某个 socket `recv`。

### 2.2 `gamestateupdate %d`

两处使用(`0x054B7B`、`0x073214`)都是**格式化打印**:

```
054B7A  push 0xDB4700         ; "gamestateupdate %d"
054B7F  mov [edi+8], edx
054B82  call 0x774980         ; 变参格式化
054B87  lea ecx,[edi+0x14]
...     call 0x675260         ; 字符串比较
```

- 宿主函数 `0x053760..0x0554C0` 是一个巨大的**主机/引擎更新函数**(体内 27 个字符串
  push:字体、HUD 图标、`net_disconnect`、`killicon*`,以及 `gamestateupdate %d`)。
- **判定:`gamestateupdate %d` 是引擎状态机的日志/诊断输出,不是网络消息的 opcode 名。**
- 反向追踪到 `0x073200`/`0x0731E0` 两个小函数,再上溯到 `0x053760`(环)。
  这些函数读取的是**引擎内部状态**,不是收包缓冲。

### 2.3 `CA_GAMESTATE` 与 `EXE_AWAITINGGAMESTATE`

- `CA_GAMESTATE` @ `0x9C0974`,唯一 xref `0x1C809D`(函数 `0x1C8060..0x1C8150`),
  上游 `0x37DC99`(即在 `0x37DBC0` 的 UI/状态汇函数内)。
- `EXE_AWAITINGGAMESTATE` @ `0x9C5F1C`,唯一 xref `0x20C14C`(函数 `0x20C130..0x20C190`),
  上游 `0x20C225`。
- 两处都是**错误/诊断字符串**,`push` 后调用报错函数。**不是状态消费者本身。**

### 2.4 `EXE_CONFIGSTRINGMISMATCH` 与 `ExpectedNetConfigStringMismatch`

- `EXE_CONFIGSTRINGMISMATCH` 有两处:xref `0x0731E1`(小函数 `0x073180..0x073200`)
  与 `0x0F2833`(命令串表函数 `0x0F2350`)。
- `ExpectedNetConfigStringMismatch` @ `0x9B4D98`,xref `0x0778D7`(函数 `0x077760..0x077910`),
  上游 11 个(UI/状态区)。
- **判定:均为错误处理路径的格式串。** 没有任何一处体现「按 configstring 索引读/写表」。

### 2.5 `connectResponse` / `challengeResponse` / …(唯一的协议分派)

`0x1C13A0` 体内的分派模式(对每个 token 一致):

```
1C1684  mov eax,0x7FFFFFFF
1C1685  push 0xDBFEE8        ; "challengeResponse"
1C168A  ... call 0x7745E0     ; 带长度上限的字符串比较
1C168F  test eax,eax ; je    ; 命中则跳入该命令处理
```

- 每个命中分支组装 6 个 `[ebp+0x0c..0x20]` 参数后 `call 0x1C1300`(子处理/状态转换)。
- 该函数**只被 `0x1C1EE0` 调用**(连接无关解析器),证明这是**握手层的分派**,不是 in-match。
- **这是本轮唯一能确证「字符串 → handler → 分派」的协议路径。**

### 2.6 `process snapshots`

- xref `0x14B5F8`,函数 `0x14B3F0..0x172100`(巨型客户端函数)。
- 该点 `push 0xDBEBD0; push -1; call 0x66D930` → **日志/开发打印**。
- 无 socket 调用;不能据此认定快照解码入口。

---

## 3. 反向追踪结论

| 字符串类别 | 是否构成 opcode/消息处理器 | 依据 |
|---|---|---|
| `connectResponse`/`challengeResponse`/... | **是**(连接无关层) | `strcmp` → 分支 → 状态转换 |
| `EXE_LOSTRELIABLECOMMANDS`/`EXE_*OVERFLOW` | 否(错误上报) | 统一错误上报函数 |
| `gamestateupdate %d`/`CA_GAMESTATE`/`EXE_AWAITINGGAMESTATE` | 否(诊断/日志) | 变参格式化 / 报错函数 |
| `EXE_CONFIGSTRINGMISMATCH`/`ExpectedNetConfigStringMismatch` | 否(错误处理) | 格式串 + 报错函数 |
| `process snapshots` | 否(日志) | `push -1` + 日志函数 |

**禁止:** 不得因字符串名含 `gamestate`/`configstring`/`reliable` 就把它当作 opcode 或
消息处理器;必须看控制流是否「读缓冲 → 选择分支 → 调用处理」。
