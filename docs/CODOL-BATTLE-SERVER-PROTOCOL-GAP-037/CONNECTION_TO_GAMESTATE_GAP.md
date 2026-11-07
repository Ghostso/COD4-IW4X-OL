# CONNECTION_TO_GAMESTATE_GAP — 从客户端发起连接到收到可解析游戏状态

**目标：** CODOL 3.19.26.22 / Build 1649370  
**基线：** 034 目标镜像证据、035 OOB 状态机、FREEZE-005、正式服务器源码。  
**纪律：** 没有目标版本真实抓包；没有 E2E；任何未闭合字段不得猜测。

---

## 1. 目标链路的阶段性结论

| 阶段 | 目标客户端证据 | 服务器实现 | 测试 | 当前判定 |
|---|---|---|---|---|
| 客户端状态准备 | `[0x076446B0] ∈ {3,4,5,6}`（034/035） | 无独立状态门 | 035 84 项离线测试 | `CLIENT_CONFIRMED` + `TEST_VERIFIED`（模块级） |
| OOB getchallenge | `getchallenge 0 "%s"` @ `0x1C071E` | 有 challengeResponse | 有离线文本测试 | 部分 `CLIENT_CONFIRMED` |
| OOB connect | state 4 有 connect + 28 键 userinfo | 有 connect 处理 | 有自测 | 文本载荷映射 `UNKNOWN` |
| OOB challengeResponse | 字面量 @ `0xDBFEE8`；容器 `0x1C13A0` | 有 | 有自测 | 是否比较/日志 `UNKNOWN` |
| OOB connectResponse | 字面量 @ `0xDBFF0C`；容器 `0x1C13A0` | 有 | 有自测 | 是否比较/日志 `UNKNOWN` |
| DTLS-like cookie/key exchange | 目标未定位对应入口 | 有完整实现 | 有 KAT/往返 | `SERVER_IMPLEMENTED`，非 `CLIENT_CONFIRMED` |
| 数据帧封装 | 目标未定位对应入口 | 有 HMAC/AES | 有自测 | `SERVER_IMPLEMENTED` |
| 连接内 netchan | `netchanProcess` 真实入口 `UNKNOWN` | legacy + 2697 两套 | 有离线自测 | 不能证明目标一致 |
| 服务端消息 opcode | 0..5 分派表未定位 | 有 legacy/2697 分派 | 有自测 | `UNKNOWN` |
| gamestate/configstring | 解析族存在；字段/顺序未知 | 有 legacy 与 2697 构造 | 有自测 | 目标格式未闭合 |
| 首个 snapshot | 帧边界/基线/实体无证据 | 有 legacy；2697 禁用 | 有 legacy 位流自测 | 目标格式 `UNKNOWN` |
| 客户端收到可解析状态 | 无真实抓包、无 E2E | 无 | 无 | `UNKNOWN` |

---

## 2. 逐步缺口

### 2.1 OOB 状态门（已知最多，仍非全闭合）

目标直接证据：

- RVA `0x1C05F0` 发送器。
- 状态门 `[0x076446B0] ∈ {3,4,5,6}`。
- 状态 3 → `getchallenge 0 "%s"`。
- 状态 4 → `connect` + 28 键 userinfo（035 更正 034）。
- 状态 5 → `stats`。
- 状态 6 → `heartbeat`。
- 节流：状态 3/4 用 3000；状态 5 用 100；状态 6 用 500。
- 挑战失败上报 `EXE_CLIENTFAILEDTOCHALLENGE`。

仍未闭合：

- 3000/100/500 的业务语义。
- 状态 4 的键→值映射。
- 状态 5 stats 分帧/长度。
- OOB 入站信封、长度、分隔规则。
- 响应字面量用于比较还是日志。
- `cancelConnect` 具体副作用。

**工程含义：** 035 的独立 OOB 模块可继续作为离线规格，但当前不产出可发送报文（因 U-07/U-09）；接入正式服务器前必须先补齐这些证据。

### 2.2 DTLS-like / 数据帧

目标 034 没有定位目标客户端的 cookie/key exchange/数据帧入口，因此服务器现有实现只能标：

- `SERVER_IMPLEMENTED`
- `TEST_VERIFIED`（KAT、往返、篡改检测）
- **不能**标 `CLIENT_CONFIRMED`
- **不能**标 `E2E_VERIFIED`

服务器实现位置：

- `CodolProtocol.cs:73-244`
- `ClientLogic.cs:87-245`
- `ClientLogic.cs:698-704`

### 2.3 连接内消息入口（最关键阻塞）

034 已确认：

- 增量字段类型分派器 `0x5F830`。
- 类型表 A：索引 `0x460550`，314 项，目标表 `0x46040C`，81 分支，默认 `0x50`。
- 类型表 B：索引 `0x4606E4`，136 项，目标表 `0x46068C`，22 分支，默认 `0x15`。
- 调用链：`0x5F830 ← 0x208432 (in 0x208380) ← 0x1FFB88 (in 0x1FF820) ← 0x20059B`。
- `0x1FF820` 读取 `[ebx+0xa0]`、`[ebx+0xa4]`、`[ebx+0xf0]`。

034 未确认：

- `0x20059B` 所在函数入口。
- `netchanProcess` 真实入口。
- 服务端消息 opcode 分派表。
- gamestate/configstring 解析函数与逻辑字段的一一对应。
- 消息边界和终止条件。

**这是“收到可解析游戏状态”之前的直接阻塞。** 在它闭合前，任何 gamestate/configstring/snapshot 编码都缺少目标入口与字段依据。

### 2.4 gamestate 与 configstring

目标直接证据：

- 解析族入口：`0x6D060 / 0x6D360 / 0x6D6E0 / 0x6D870 / 0x6D960 / 0x6D9D0 / 0x6DA30 / 0x6DAE0 / 0x6DCF0 / 0x6E030 / 0x6E0A0`。
- 调用骨架：`0x6E030 → 0x6DCF0 → 0x6DAE0 → 0x6D6E0` 等。
- `gamestateupdate %d` 字面量，引用点 `0x054B7A` / `0x073213`。
- `0x25/0x92` 禁用字节规则在目标 configstring 区间 0 命中。

未确认：

- 哪个函数对应 parseGameState / parseConfigStrings。
- 读取顺序与前置条件。
- 索引宽度、索引上界、是否 index-skip。
- 字段类型与结束条件。
- 与 snapshot 的先后关系。

**服务器 2697 写入器不能被当作目标事实**，因为其来源是 2697 服务端 RVA，不是 3.19.26.22 客户端。

### 2.5 首帧 snapshot

见 `SNAPSHOT_DELTA_GAP.md`。核心结论：目标版本帧边界、delta 基线、实体增删、编号映射全部 `UNKNOWN`。

---

## 3. 最小完整链路（当前证据允许的表述）

```text
客户端状态 ∈ {3,4,5,6}
  -> 发出 getchallenge / connect / stats / heartbeat（目标已确认）
  -> 服务器回应 challengeResponse / connectResponse（服务器已实现；目标接收语义部分未知）
  -> 建立连接内通道（目标入口 UNKNOWN；服务器自实现）
  -> 服务端消息 opcode 分派（目标 UNKNOWN；服务器自实现）
  -> gamestate/configstring（目标解析族存在；字段 UNKNOWN；服务器构造的是旧协议）
  -> 首帧 snapshot（目标 UNKNOWN；服务器 legacy 位流无目标证据）
  -> 客户端解析并进入游戏（无 E2E，UNKNOWN）
```

---

## 4. 证据缺失项

| 缺失项 | 影响 | 最小验证方法 |
|---|---|---|
| 目标 netchanProcess 入口 | 无法判断分片/序号层 | 静态：从重建缓冲向上交叉引用；只读观测需单独授权 |
| 目标 opcode 分派表 | 无法判断 gamestate/configstring/snapshot 进入点 | 静态：由 `0x20059B` 向上定位，再找消息类型比较 |
| gamestate/configstring 函数语义 | 无法构造目标格式 | 静态：逐函数反汇编 + 调用者/参数绑定 |
| configstring 索引编码 | 无法编码表项 | 静态：找索引读写与边界比较 |
| snapshot 帧边界 | 无法构造 snapshot | 静态：找消息终结符/长度/下一条消息起点 |
| delta 基线 | 无法构造增量 | 静态：找上一帧指针/历史缓存 |
| 实体增删/编号 | 无法同步实体 | 静态：找实体表索引换算与删除分支 |
| OOB 入站信封/长度 | 035 模块不能产出可发报文 | 静态：`0x1C13A0` 分支体与长度比较 |
| 目标真实抓包 | 无法 E2E | 本任务禁止；需后续单独授权 |

---

## 5. 结论

从客户端发起连接到收到可解析游戏状态，**OOB 的前半段证据最成熟，连接内消息入口的证据最薄弱**。在应用层入口、opcode、gamestate/configstring 字段与 snapshot 边界未闭合前，服务器现有编码只能算“服务端自证实现”，不能算“目标客户端兼容实现”。
