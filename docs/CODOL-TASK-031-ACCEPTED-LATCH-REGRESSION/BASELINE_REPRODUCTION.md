# BASELINE_REPRODUCTION — 阶段 0（**INVALID_PRECONDITION**）

> ⚠ **证据效力更正（2026-10-13 第二次修订）：**
> 本次运行的客户端停在 **"100" 弹窗错误**处，**未通过已固化的正式启动链成功进入游戏**。
> 因此本文件**不是**有效基线复现，而是**一次前置条件不成立的错误启动会话记录**。
> 其中的一切"未观测"结论**只适用于本次错误会话**，**不得**外推为正常大厅流程的行为。

---

## 0. 前置条件判定：**不成立**

| 项 | 已知成功的固化链 | 本轮实际 | 结论 |
|---|---|---|---|
| 启动脚本 | `capture_elevated_network.ps1` | `_work\lab\run_all.py` | 不同 |
| 游戏沙箱 | `sandbox_ifs1_20260923` | `sandbox_datafix_20260929` | 不同 |
| 沙箱 `dwauth.ini` | `127.0.0.1 / 443 / …` | `formal-zone-*.codol.qq.com 3074` | 不同 |
| auth 服务 | `lobby_probe_server.py` @ `8443` | `fake_auth_tls.py` @ `3074` | 不同 |
| 大厅服务 | `lobby_socket_server.py` @ `8444` | `lobby_server.py` @ `3074` | 不同 |
| portproxy | `443→8443` **与** `443→8444` | 仅 `443→8443`（缺 8444） | 不完整 |

**客户端退出码 = `-1 (0xFFFFFFFF)`，`t=8.0s` 与 `t=40.0s`。**
`CODOL_SERVER_OPERATIONS_MANUAL.md` §8 的定义：**"游戏 8 秒内 `0xFFFFFFFF` 退出 = 启动/IIPS 前置失败"**。

> 故：**连"进入游戏"这一最外层前置条件都未满足。**

逐项差异见 `evidence\LAUNCH_CHAIN_DIFF.tsv`。

---

## 1. 运行条件（如实记录，供后续比对）

| 项 | 值 |
|---|---|
| 宿主 | `M7-E8S3\M7-E8S6` |
| 实验副本 | `_work\lab`（`lobby_server.py` `2eb0cdd1…`、`codol_crypto.py` `e836c63a…`、`run_all.py` `2aaa8847…`、`nt10.py` `05863eba…`、`battle_server.py` `71bb7beb…`） |
| 启动方式 | `agent_client.py run python -X utf8 <lab>\run_all.py --secs 200` |
| 客户端插桩 | 无（无 hook / 注入 / 断点 / 内存写） |
| 首次运行 | 因实验副本缺证书资产失败（`fake_auth_tls.py` 找不到 `_rsa.txt`）—— **纯环境问题**，已隔离并补入资产后重跑 |
| 客户端退出 | `rc=-1 (0xFFFFFFFF)` @ `t=8.0s`（重试轮 @ `t=40.0s`） |

---

## 2. 局部通信链观测（**仅证明局部活动**）

```
[15:14:50] === 大厅连接建立 ('127.0.0.1', 62085) ===
[15:14:50]   <- 客户端 hello (28 字节)
[15:14:50]   -> 0x81 (26 字节)
[15:14:50]   <- 0x82 stage1 (153 字节)
[15:14:50]   -> 0x83 (14 字节)  [challenge 来源: kdf-session]
[15:14:50]   [keys] ★ 试解命中: 密钥组 src=kdf-session ...
[15:14:50]   ★ 解密成功 #1 seq=1 hmac=OK marker=0x86 service=71 ver=0x03 task=4 declared=84
```

**正确解读（更正要求）：**
- 上述只**证明局部通信链有活动**（握手帧格式与加密/HMAC 链可工作）。
- **不能**证明**大厅业务状态已就绪**。客户端停在 "100" 弹窗，业务会话未建立。
- 本轮的 `service 6 / task 14`（`mmbook`）未出现，**仅适用于本次错误启动会话**；
  **不得**由此推导"正常大厅流程不会触发 `mmbook`"。

### 2.1 本轮实际分派到的 service/task（原始记录，保留）

```
10/12 x2   10/21 x19   12/6 x1   29/10 x1   3/53 x1   6/5 x1
71/4 x1    71/7 x1     71/9 x1   71/10 x1   71/13 x1
8/1 x1     8/2 x1      9/14 x1   93/1 x1
80/70 x1   80/107 x1   80/119 x1 80/173 x1  80/174 x1  80/230 x1
```

（`6/14` 计数 = 0；`mmbook` = 0；`accepted` = 0。**均为本次错误会话的原始记录，不做外推。**）

---

## 3. 客户端侧与战斗侧（**统一降级为 `INVALID_PRECONDITION`**）

| 指标 | 原样观测 | 更正后的效力 |
|---|---|---|
| `accepted` 构造/字节/通道/接收路径 | 未发生 | **INVALID_PRECONDITION** |
| 处理函数 `0x632680` | 未触达 | **INVALID_PRECONDITION** |
| `[matching+0x288]` 0→1 | 未观测到（恒 0） | **INVALID_PRECONDITION** |
| `0x634402` 消费路径 | 未执行 | **INVALID_PRECONDITION** |
| `0x632070` 构造器 | 未执行 | **INVALID_PRECONDITION** |
| `mmstart` 序列化/发送 | 未观测到 | **INVALID_PRECONDITION** |
| 战斗端点连接 | `battle_srv.log` 全程 `收包=0 NAT=0 init=0 keyex=0 data=0 会话=0` | **INVALID_PRECONDITION** |

**三种未观测形态的区分（任务书 §四 要求）：**

- **"函数未执行"**：`0x632680` / `0x632070` / `0x634402` —— 缺输入信号。**但该"缺输入"的根因是会话被前置错误截断，不反映正常流程。**
- **"函数执行但条件不满足"**：本轮**不适用**（相关函数均未执行）。
- **"观察手段未捕获"**：`[matching+0x288]` —— 本轮未挂专门采样器，且会话未进入预约阶段。

---

## 4. 阶段 0 判定（更正后）

```
BASELINE_REPRODUCED            = NO
PRECONDITION_SATISFIED         = NO   （客户端未成功进入大厅；停在 "100" 弹窗）
CLIENT_ENTERED_LOBBY           = NO   （rc=-1 / 0xFFFFFFFF）
CLIENT_EXIT_CODE               = -1 (0xFFFFFFFF)
PROTOCOL_HANDSHAKE_ACTIVITY    = OBSERVED  （仅证明局部通信链活动，不等于业务就绪）
MMBOOK_ISSUED                  = NOT_OBSERVED_IN_THIS_FAILED_SESSION_ONLY
ACCEPTED_SENT                  = NOT_OBSERVED_IN_THIS_FAILED_SESSION_ONLY
MATCHING_288                   = INVALID_PRECONDITION
MMSTART                        = INVALID_PRECONDITION
BATTLE_28960                   = INVALID_PRECONDITION
```

> **阶段 0 结论：** 前置条件不成立，**不构成有效基线**。
> 不得据此对 `accepted` 形态、闩锁成因或大厅业务流程下任何结论。

---

## 5. 原始证据（**原样保留，未改写**）

| 文件 | 内容 |
|---|---|
| `evidence\P0_lab_lobby_srv.log` | 错误会话的大厅服务全程 |
| `evidence\P0_lab_auth3074.log` | 会话密钥下发 |
| `evidence\P0_lab_battle_srv.log` | 战斗服务 0 收包 |
| `evidence\P0_nt10_main.txt` / `P0_nt10_retry_a2.txt` | 客户端退出码与探针输出 |
| `evidence\LAUNCH_CHAIN_DIFF.tsv` | **固化链 vs 本轮执行的逐项差异（定位 "100" 错误的起点）** |
