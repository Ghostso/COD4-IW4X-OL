# 09 — E：完整载荷抓包必要性判断（Payload Capture Decision）

> 任务：`EARLY-SERVER-CLIENT-CONSUMER-001` 任务 E。
> 边界：**本轮只做静态判断，不进行抓包**。不启动客户端/服务端，不执行 `.cmd`/未知脚本，不修改原始样本与既有报告，不输出秘密材料。
> 状态词：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。
> 关联：`09_A`（服务端账本）、`09_B`（编号裁决）、`09_C`（客户端候选）、`09_D`（双端矩阵）。

---

## E.0 一句话结论

- **服务端实际写出的 snapshot opcode = `0x00`**，可由源码**静态确定** → **CONFIRMED（服务端侧）**。
- **客户端期望的 snapshot opcode 值无法由现有静态材料确定** → **UNKNOWN**（分派表 INSTRUMENTATION_BLOCKED）。
- 客户端**真实解码入口**已能定位到**函数级**（`CL_PacketEvent`/`CL_Netchan_Decode`/`CL_ParseSnapshot`），但**首字节 opcode → 处理函数的分派表**未闭合 → 该点 **INSTRUMENTATION_BLOCKED**。
- 现有样本**不完整**：原生 fixture 是**服务端输出**（未经 C1 接受验证）；`console_mp` 日志证明客户端消费的是**参考 Python 服务端**，**不是**本仓库序列化器。
- **结论：完整载荷抓包对本仓库服务端 ↔ 本客户端互通的验证是必要的**（`09_F` 给出最小实验计划，**本轮不执行**）。但**认证秘密不必暴露**即可完成。

---

## E.1 问题 1：静态源码能否确定服务端实际写出的 snapshot opcode？

**能。** → **CONFIRMED（服务端侧）**

| 证据 | 位置 | 内容 |
|---|---|---|
| 段首字节 | `codol_snapshot.c:23` | `CODOL_WriteByte(m, 0);`（每快照段首字节 = `0x00`） |
| 调用链 | `sv_snapshot.c:767` → `:224` → `codol_sv_snapshot.c:284` → `:205` → `codol_snapshot.c:8` | `SV_WriteSnapshotToClient` 经 `CODOL_PrepareClientSnapshot` 到 `CODOL_WriteSnapshotDeltaNumber` |
| 出网 | `sv_snapshot.c:642` → `:688` | CODOL 分支**不启用 Huffman**，直接 `SV_Netchan_Transmit(msg->data, msg->cursize)` |
| 实证 | `fixtures\codol_snapshot\native_bog_baseline.bin` | 首字节 `00`（本轮独立复算：`00 c8 19 00 00 00 0c 86 …`） |

> **限制**：这证明的是**服务端写 `0x00`**。它**不**证明客户端接受 `0x00`（`protocol_map.md:334` 仍标注 `svc_snapshot` = "still unknown"）。

---

## E.2 问题 2：静态分析能否定位客户端真实解码入口？

**部分能** → 入站链 **CONFIRMED（函数级存在）**；**opcode 分派表 INSTRUMENTATION_BLOCKED**。

| 环节 | VA | 证据 | 状态 |
|---|---|---|---|
| 网络消息事件入口 | `CL_PacketEvent` @ `0x00497360` | 3 个直接调用者（`0x595D6D`/`0x595DE6`/`0x595F36`）；体内做 overflowed 回滚 | **STRONG_CANDIDATE** |
| 入站解密 | `CL_Netchan_Decode` @ `0x0049C5E0` | 唯一调用者 `0x0049754A`（在 `CL_PacketEvent` 体内）；key 计算与 `ERRORS.md:439-450` 逐条吻合 | **STRONG_CANDIDATE** |
| 快照解码 | `CL_ParseSnapshot` @ `0x0049D95F`（函数起始 `0x0049D800`） | 读 `snapFlags@[ebx+0x336C]`、`nextNoDeltaEntity@0x06D36AB8`；**无 E8/E9 调用者、无 4 字节指针引用** | **STRONG_CANDIDATE（存在+语义）/ INSTRUMENTATION_BLOCKED（分派）** |
| gamestate 解码 | `CL_ParseGamestate` 串 @ `0xC49358` 等 | 仅字符串存在，指针引用为 0 | **STRONG_CANDIDATE（存在）/ UNKNOWN（地址）** |
| opcode 分派表 | — | 未在文件静态数据中找到 | **INSTRUMENTATION_BLOCKED** |

**裁决**：**“客户端有没有解码器”** → **CONFIRMED 有**；**“首字节 opcode 落到哪个处理函数”** → **仍 blocked**，因为 `CL_ParseSnapshot` 经**间接分派**调用，表项未静态找到。

---

## E.3 问题 3：是否存在可用于验证的完整、已知输入输出样本？

**部分存在，但不满足“本仓库服务端 ↔ 本客户端”的闭环。** → **NOT_OBSERVED**

| 样本 | 内容 | 方向 | 能否验证本仓库↔本客户端 |
|---|---|---|---|
| `fixtures\codol_snapshot\native_bog_*.bin`（3 个） | 原生 Windows 服务端输出的**明文快照段**（含 opcode `0x00` 到 EOF `0x05`） | s2c（服务端产出） | **否**（README 明言 “server output, not a packet accepted by C1”） |
| `console_mp*.log`（17 次到 ACTIVE） | 客户端接受**参考 Python 服务端**的 gamestate/snapshot | s2c（客户端消费） | **否**（对端是参考实现，不是本仓库） |
| `captures\wiretap-*.jsonl`（4 个） | 仅 `lobby`/`stun`/`seckey` 层事件，**无 `game` 层** | lobby | **否**（`wiretap_report.md` §4：game-server tap **未应用**） |

**结论**：**缺**一个“本仓库 CODOL 服务端 → 本客户端”的**完整下行载荷样本**。这正是抓包要补的缺口。

---

## E.4 问题 4：哪些问题可以通过源码继续解决？

| 问题 | 现状 | 能否继续用源码解决 |
|---|---|---|
| 服务端每种消息的首字节/布局 | 已解（`09_A`） | ✅ 已解决 |
| 两套 svc 编号的关系 | 已解：独立、无转换、`svc_ops_e` 不可达（`09_B`） | ✅ 已解决 |
| snapshot 服务端首字节 | 已解 = `0x00` | ✅ 已解决 |
| configstring 位级布局 | 已解（`codol_configstrings.c:269-286`） | ✅ 已解决 |
| 客户端是否存在解码器 | 已解：存在 | ✅ 已解决 |
| 客户端**入站解密/分派链**函数级位置 | 部分解（`CL_PacketEvent`→`CL_Netchan_Decode`） | ⚠️ 边际收益低（分派表间接化） |
| 客户端 opcode **分派表** | 未解 | ❌ 源码不可解（VMProtect/运行时构造） |
| 客户端**期望的 snapshot opcode 值** | 未解 | ❌ 源码不可解 |

**裁决**：源码侧已接近边界。**继续静态源码投入的边际收益低**，除“分派表逆向”外无高价值待解问题——而分派表本身 **INSTRUMENTATION_BLOCKED**。

---

## E.5 问题 5：哪些问题必须观察真实游戏层载荷？

必须依赖**真实游戏层（game 层）下行载荷**的问题：

1. 客户端**实际接受**的 snapshot opcode 值（`0x00`？其他？）。
2. 本仓库服务端流是否被客户端**逐字节接受**（`CL_ParseSnapshot` 是否真的进入、有无 `bad command byte`/`overflowed`）。
3. 客户端 `CL_ParseGamestate` / `CL_GetSnapshot` 的**真实调用点**（静态 xref 为 0）。
4. gamestate 内 configstring 子流的**位级**解析是否与本仓库一致（const-vs-nonconst）。
5. `CA_PRIMED` 转换与 `nextNoDeltaEntity`/`snapFlags` 的**运行时**取值关系。

→ 这些问题对应 **INSTRUMENTATION_BLOCKED / UNKNOWN**，**只能**通过观察真实载荷 + 客户端日志解决。

---

## E.6 问题 6：最小抓包需要哪些字段、报文方向和前后状态信息？

**最小字段集**（详见 `09_F` 的完整计划）：

| 类别 | 必需字段 |
|---|---|
| 方向 | `s2c`（下行，主）与 `c2s`（上行，仅取 ACK 序号以对齐） |
| 传输头 | `serverMessageSequence`、`reliableAcknowledge`、`serverId`（**可截断为 u8**，用于 XOR key 复算） |
| 游戏层 | **解密后**的 svc 首字节 `op`、`u32 serverTime`、`u8 deltaNum`、`u8 snapFlags`、EOF 字节 |
| gamestate | `map`、`gametype`、`fs_crc`、`seq`、`op`、configstring 计数 |
| 客户端状态 | `console_mp.log` 的 `CA_*` 转换行、`Received gamestate … bytes`、`configStrings: N`、`oldMessageNum/newSnap.messageNum` |
| 前后状态 | 连接建立前后的 `CA_CONNECTED/LOADING/PRIMED/ACTIVE`；首个基线帧与后续 delta 帧 |

**最小报文方向**：`s2c` 必须；`c2s` 只需 ACK/`clc_move` 序号（用于 key 与 delta base 对齐）。

---

## E.7 问题 7：是否可以在不暴露认证秘密的情况下完成捕获与分析？

**可以。** → **CONFIRMED（可行性判断）**

- 只需记录**解密后的游戏层 svc 字节与结构字段**（opcode、长度、计数、EOF）。
- **握手密钥 / MAC / 认证令牌 / `c1_keys.bin` 内容**一律**不落盘**（或落盘前即剥离）。
- XOR key 只记**复算所需的 u8 分量**（`serverMessageSequence`、`challenge`、`serverId`），这些是**报文头字段**，非长期秘密。
- 抓包点选在**已解密**的 `_send_snapshot_now` / `build_gamestate` 出网点（见 `wire_interception.md` §4），**天然绕过**认证材料。

---

## E.8 抓包必要性裁决矩阵

| 待验证问题 | 静态材料是否足够 | 是否必须抓包 | 状态 |
|---|---|---|---|
| 服务端写出的 snapshot opcode | ✅ 足够 | 否 | **CONFIRMED** |
| 两套 svc 编号关系 | ✅ 足够 | 否 | **CONFIRMED** |
| 客户端**期望的** snapshot opcode | ❌ 不足 | **是** | **UNKNOWN** |
| 本仓库流被客户端逐字节接受 | ❌ 不足 | **是** | **NOT_OBSERVED** |
| 客户端分派表 / `CL_ParseGamestate` 调用点 | ❌ 不足（VMProtect） | **是** | **INSTRUMENTATION_BLOCKED** |
| configstring 位级一致性 | ⚠️ 部分 | **是**（低优先） | **CANDIDATE** |

---

## E.9 停止条件与边界

- **不**在无真实载荷的情况下继续反复反编译服务端资产或泛化客户端反编译（边际收益已耗尽）。
- **不**将候选 RVA/字符串引用升级为“已确认函数语义”。
- 抓包实验的**前置条件、观察指标、停止条件、脱敏要求**见 `09_F_NEXT_ACTIONS.md`（**本轮不执行**）。