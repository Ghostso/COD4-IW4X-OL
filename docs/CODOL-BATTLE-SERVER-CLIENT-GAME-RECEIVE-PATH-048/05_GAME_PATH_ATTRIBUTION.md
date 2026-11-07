# 05 — 业务归属判定、反证与替代解释

## 1. 判定方法(先定后判)

一个候选只有在同时满足下列三点时才升级为「游戏业务路径」:

1. 有**直接指令/数据流**把 socket 返回值连到该候选的输入;
2. 该候选的控制流体现「**读消息 → 选择 opcode/命令 → 调用处理**」;
3. 处理的下游进入**游戏状态**或**游戏消息队列**,而非日志/UI/错误上报。

只用「地址相近」「字符串紧邻」「函数名相似」「结构同宽」判定的,一律降级。

## 2. 归属判定表

| 候选 | 判定 | 判定依据(直接) | 反证 |
|---|---|---|---|
| TQOS/QoS(P1/P2/P3) | `PLATFORM_LAYER` | `udp://%s:%d`;`tqos_create_protohandle`;TDR 解包 | 与游戏串区无交叉(046) |
| P4 socket 簇 | `UNREACHED_MODULE` | accept/recvfrom 齐备,但调用者 0、指针引用 0 | 无 |
| P5 socket 簇 | `CLIENT_TRANSPORT` | `this->sock` + `recv(buf,len)` 直通 | 无游戏串;上游环断裂 |
| OOB 分派(`0x1C13A0`) | **`GAME_HANDSHAKE_LAYER`** | token `strcmp` → 分支 → 状态转换;被连接无关解析器唯一调用 | 非 in-match |
| OOB 泵(`0x0F8FB0`) | `OOB_TRANSPORT_PUMP` | 队列报文 → `0x1C1EE0` → `0x1C13A0` | 体内无 socket;生产者不明 |
| `EXE_LOSTRELIABLECOMMANDS` | `ERROR_REPORTER` | 上报函数 `0x5B87D0`;13 上游远离 P4/P5 | 无 ACK 逻辑 |
| `gamestateupdate %d` | `ENGINE_DIAG_LOG` | 变参格式化 `0x774980` | 宿主为巨型主机函数 |
| `CA_GAMESTATE` | `STATE_LOG` | 上游 `0x37DBC0`(UI/状态汇) | 非状态消费者 |
| `EXE_CONFIGSTRINGMISMATCH` / `ExpectedNetConfigStringMismatch` | `ERROR_HANDLER` | 格式串 + `0x4F82E0` | 无索引读/写 |
| `process snapshots` | `DIAG_LOG` | `push -1` + `0x66D930` | 无 EOF/netfield 逻辑 |

## 3. 关键否证(本轮新增/复核)

| 否证 | 内容 | 证据 |
|---|---|---|
| N-4-1 | P4「服务端 socket 簇」**不是**当前映像中可达的 in-match 入口 | 14 函数调用者 0、dword 指针 0 |
| N-4-2 | `EXE_LOSTRELIABLECOMMANDS` 宿主是**错误上报**,不是 reliable 分派 | `0x376B20 call 0x5B87D0`;分支无 opcode 选择 |
| N-4-3 | `gamestateupdate %d` 是**日志格式串**,不是 opcode 名 | 宿主 27 个字符串 push 全为 HUD/字体/诊断 |
| N-4-4 | 连接无关分派**不是** in-match opcode 分派 | 唯一调用者 `0x1C1EE0`(连接无关解析器) |
| N-4-5 | 复活映像**没有**大面积空洞 → 「找不到」不因缺页 | 长常量串仅占 0.83% |
| N-4-6 | 046 的 TQOS 归属**独立复现**通过 | `01` §2 |

## 4. 支持性证据(可开始实现的依据)

| 编号 | 证据 | 级别 |
|---|---|---|
| S-4-1 | 连接无关 token 词表(RVA 0x9BFCE8..0x9BFFA0)及其方向 | `DIRECT_STATIC` |
| S-4-2 | 客户端**自身**对服务端 token 的 `strcmp` 比较点(0x1C1685..0x1C1DF0) | `DIRECT_STATIC` |
| S-4-3 | 客户端**自身**构造的请求格式串(`getchallenge 0 "%s"`、`connect %s "%s"`) | `DIRECT_STATIC` |
| S-4-4 | P5 `recv`/`send`/`recvfrom` 的 `buf/len` 直通 | `DIRECT_STATIC` |
| S-4-5 | 重建的调用图对 046 已知边的复现(P1/P3/13 上游) | `CROSS_VALIDATED` |

## 5. 替代解释(尚未排除)

| 替代解释 | 为什么不能排除 | 需要的证据 |
|---|---|---|
| in-match 解析器在被压缩的第 3 节区 | 0xA16000 之后仅 0x4F000 可读 | 完整 XSo 映像(E-048-1) |
| in-match 入口经**虚表/回调注册** | 本轮无法跟踪指针表写入 | 数据流到 vtable 写入点 |
| in-match 入口经**间接 `call edx/esi`** | 目标在运行时才知 | 只读调用栈采样(E-048-4) |
| P5 的上游循环由**另一个模块**以函数指针启动 | 未找到指针引用 | 同上 |
| 游戏数据走 **CEF/HTTP 侧信道**(非 UDP) | 存在大量 curl/CEF 调用 | 需要网络侧抓包证据(不在本轮) |

## 6. 恢复映像不完整时的陈述纪律(强制)

- 本轮所有「排除」都写成「**在已检查范围/映像内**未观察到」,不写「程序中不存在」。
- 第 3 节区不可读(仅 0x4F000/0xDBB1CC0 可读)→ **该范围内任何结论都是 BLOCKED**,不是负证据。
- 不得把「某函数没有直接调用 decoder」当作「它不是网络入口」的证明。
- 不得把「某字符串没有 xref 到 P4/P5」当作「游戏接收路径不存在」的证明。
- 不得把「某个 decoder 与 TQOS 共用结构」扩展为「所有调用者都属于 TQOS」。
- 不得把「游戏字符串位于某函数附近」当作「该函数处理对应消息」。
- 不得因参考项目存在同名函数就推断最终 CODOL 使用相同格式。

## 7. 与 046 结论的一致性

| 046 结论 | 本轮处置 |
|---|---|
| 045 链 = TQOS 平台层 | ✅ 继承,独立复现,不重复消耗 |
| TQOS 与游戏串区无交叉 | ✅ 继承 |
| 13 个可靠命令上游不成 P4/P5 交集 | ✅ 复现;本轮进一步定性其为**错误上报** |
| 移动资料是项目侧制品 | ✅ 继承;047 已隔离为内部模型 |

## 8. 结论

- **A(是否闭环):否。** 
- 唯一可**直接开始实现**的协议模块:连接无关(握手/连接状态)层。 
- 最小断点:in-match 接收→消费者边(P5 消费循环 `0x7A41D0` 之上,或 OOB 泵队列的
  socket 生产者)。
