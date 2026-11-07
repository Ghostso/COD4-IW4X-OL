# CODOL-ISSUE-0020 — BOT 房间场景下战斗服零收包

> 深度取证档案 · 2026-10-29
> 本档案的每一个技术结论都在本轮重新回到原始文件核对过；引用的结论性旧报告一律标注为二手。

---

## 01. 问题基本信息

| 项 | 值 |
|---|---|
| Issue ID | `CODOL-ISSUE-0020` |
| 完整标题 | BOT 房间场景下战斗服零收包（客户端从不向 UDP 28960 发起连接） |
| 所属系统 | `battle-network`（根在 `lobby`） |
| 优先级 | **P0** |
| 当前状态 | `OPEN` |
| 首次发现 | 2026-10-26 23:31（本审计重定：紧邻最后一次成功之后的那一轮） |
| 最近验证 | 2026-10-29 00:21（`ONCE_20261029_002046`） |
| 首次发现任务 | 2026-10-26 夜间剧情模式开局调查 |
| 最近调查任务 | 本任务 `CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053` |
| 涉及客户端版本 | **3.19.26.22 / build 1649370**（`codoMP_client_shipRetail.exe`，SHA `36997674…b537`） |
| 涉及服务端版本 | C 战斗服 `codol_battle_server.exe` 314,368 B / SHA `275B165F…`（2026-10-26 22:07 构建） |
| 相关 Git 提交 | **UNKNOWN** —— 工作区不是 git 仓库（见 ISSUE-0003），无提交历史可引用 |
| 是否阻塞可玩战斗 | **是** |
| 上游依赖 | ISSUE-0009（房间 UI）、ISSUE-0010（房间下行格式）、ISSUE-0012（`dwRoomMatch::Init`）、ISSUE-0021（mmstart 地图） |
| 下游依赖 | ISSUE-0025（位置权威）、ISSUE-0024（实体可见）、ISSUE-0032（对局接线） |

### 证据来源版本区分（强制）

| 来源 | 本 Issue 中的用途 |
|---|---|
| **3.19 / 1649370 客户端** | 唯一相关客户端；所有实机结论都来自它 |
| 2697 (`codol_dedrun.exe`) | **不相关**。2697 是家族写侧参考，本 Issue 的所有日志都来自 3.19 实机 |
| OLfinal / ol-mod 3.3.3.3 | **不相关**。仅在"mmstart 文本命令"这类家族级语法上可作旁证，本档案未使用 |
| 2.6.9.7 | **不相关** |

---

## 02. 问题的精确定义

**预期行为**
客户端在用户确认开始对局后，向大厅应答里下发的战斗服地址（本机 `127.0.0.1:28960`）发起 UDP 连接：
`NAT 探针 → DTLS Init/Cookie → ECDH 密钥交换 → getchallenge → connect → stats → heartbeat → gamestateupdate`。

**实际行为**
战斗服进程正常监听 28960，但**一包都没有收到**。`_battle_out.txt` 只有 7 行初始化输出。

**偏差**
不是"握手失败"，不是"认证失败"，而是**客户端从未创建任何指向 28960 的 socket**。

**失败边界（逐层）**

| 层 | 结论 | 证据 |
|---|---|---|
| 请求是否发出 | ✅ 发出（`6/14` mmstart 到达大厅） | `ONCE_20261029_002046/kit/lobby_srv.log` |
| 服务端是否收到 | ✅ 收到并回 ACK | 同上 |
| 服务端是否处理 | ✅ 解析出 mmstart 全文，但 **map=`?` gametype=`?`** | 同上：`★ mmstart 选择: gametype=? map=?` |
| 响应是否生成 | ✅ 回显 + 可选的 room push | 同上 |
| 客户端是否收到 | ✅ TCP 会话不断，心跳正常 | 2026-10-27 文档 §1 + 本轮日志无断连 |
| 客户端是否解析 | **UNKNOWN** | 无客户端日志、ACE 拦内存 |
| 客户端是否发起 UDP | ❌ **第一处确定失败的环节** | 战斗服零 RX；同轮客户端 UDP 端口列表不含 28960 对端（2026-10-26 文档 §端口实证） |

**失败边界一句话**：
客户端完成到 `mmstart` 的全部大厅交互，之后**没有把"要去哪台战斗服"变成一次 UDP 连接**。

---

## 03. 历史发现过程

| 日期 | Run / 任务 | 配置指纹 | 观察到什么 | 当时假设 | 验证 | 结果 |
|---|---|---|---|---|---|---|
| 2026-10-26 16:42–22:08 | `ONCE_20261026_164227` … `_220815`（8 轮） | 沙箱根 + `mmstart map coop_train_mp_firingrange` + 不建房 | 战斗服全链路 RX | （当时不认为是问题） | — | **成功基线** |
| 2026-10-26 23:31 | `ONCE_20261026_233111` | 沙箱根 + `mmstart map coop_training_mp_cargoship` + 建房 | 零 RX | "地图选错" | 未做单变量 | 失败（区间 B 起点） |
| 2026-10-26 夜间 | 同上 | 端口实证：客户端 UDP 端口 `22011/50095/…` 无一连向 28960 | "客户端不建 socket" | 排除 ACE/`.local`/TAS | 三假设均被实测排除 |
| 2026-10-27 12:00 起 | `ONCE_20261027_120832` 等 | 根目录切换到 **`COD OL` 本体** | 仍零 RX | "换图不会改变连接" | 文档结论 | 成立但不能解释 |
| 2026-10-27 14:04 | `ONCE_20261027_140400` | 正式 kit，`memberCount=1` | dwRoomMatchUber 出现，仍零 RX | "memberCount 影响连接" | A/B | **否证**（对象出现但连接仍未发生） |
| 2026-10-27 20:24 | `ONCE_20261027_202345` | `102/7` 回显 50/50 全 0 | 仍零 RX | "102/7 清空选图" | 未单变量 | 未证 |
| 2026-10-28 全天 | `ONCE_20261028_212642` … `_235339`（12 轮） | `mmstart` 变为 `playlist 37`（**无 map**） | 仍零 RX | "mmstart 无 map ⇒ 不连" | 相关性统计 | 成立但不完备（见 §09） |
| 2026-10-29 00:21 | `ONCE_20261029_002046` | `102/7` 改回"不处理"，`mmstart playlist 37`，`mmstart` 不推 StartGame | 仍零 RX | 三者之一是根因 | 未二分 | 当前状态 |

**重要更正（本审计）**：上一轮 `03_MASTER_UNRESOLVED_ISSUES.md` 与本 Issue 的表述都把
"10-26 成功 vs 10-29 失败"当作一次退化。**磁盘证据显示这是三次独立切换**，
详见 `CONNECTION_REGRESSION_DIFFERENTIAL.md`。

**不同实验日志未被拼接**：上表每一行对应独立 run 目录，
本档案未把任何两轮日志合并成一次会话。

---

## 04. 原始证据清单

| Evidence ID | 类型 | 绝对路径 | SHA-256 | 定位 | 版本 | 能证明 | **不能**证明 | 独立复核 |
|---|---|---|---|---|---|---|---|---|
| EV-0020-01 | 大厅日志 | `D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ONCE_20261029_002046\kit\lobby_srv.log` | `c6578c99ec80b37b15817956d2b6871a0ab4c7a0102ee25c62cb2a81c5a01d46` | 41,315 B；mmstart 行在 `00:21:51` | 3.19 | 本轮 mmstart 全文、map/gametype 解析为 `?` | 客户端是否解析了应答 | ✅ 本轮读取 |
| EV-0020-02 | 战斗服日志 | `…\ONCE_20261029_002046\kit\_battle_out.txt` | `53628f0e61173091e1581d5df456a1c16b140ae3db074abbd85ee53530e22851` | 358 B / 7 行 | C 服 | 零 RX | 客户端是否尝试过 | ✅ 本轮读取 |
| EV-0020-03 | 大厅日志（成功） | `…\ONCE_20261026_220815\kit\lobby_srv.log` | `bf650058ea8027f0222bcd80ef922da9fdfbdc079a9cc11a5f895374bc2c2cea` | 31,613 B | 3.19 | 成功轮的 mmstart 原文 `map coop_train_mp_firingrange;2654 ;` | 该轮为何选中该图 | ✅ 本轮读取 |
| EV-0020-04 | 战斗服日志（成功） | `…\ONCE_20261026_220815\kit\_battle_out.txt` | `01c49dec1e25bb209fa1be39c26211a5639dd86858732a8f263244d97784a909` | 64,012,556 B | C 服 | `TX_NAT_REPLY 29B` → `KEY_EXCHANGE_OK` → `RX_OOB getchallenge` → `connect` → `stats` → `heartbeat` 全链 | 客户端 map 加载是否成功 | ✅ 本轮读取 |
| EV-0020-05 | 大厅日志（第一次失败） | `…\ONCE_20261026_233111\kit\lobby_srv.log` | `495b9501823e8cb16725ba0d7c6f47ea1a28fb1c4a2f2194616c6822d5cd2394` | 29,382 B | 3.19 | 失败轮 mmstart 带 map 仍零 RX | — | ✅ 本轮读取 |
| EV-0020-06 | 战斗服日志（第一次失败） | `…\ONCE_20261026_233111\kit\_battle_out.txt` | `1b6a6dbe34c4a7af4b01abd60457a391dde0919eccc8e2c527526e491685d93c` | 379 B / 7 行 | C 服 | 零 RX | — | ✅ 本轮读取 |
| EV-0020-07 | 全量运行矩阵 | 34 个 `runs\*\kit\lobby_srv.log` + `_battle_out.txt` | 逐文件哈希见 `EVIDENCE_INDEX.json` | 见差分文档 §1 | 3.19 | `map==coop_train_mp_firingrange && 不建房` 与 RX 100% 共变 | 因果方向 | ✅ 本轮重算 |
| EV-0020-08 | 启动根目录 | `…\ONCE_20261026_220815\chain_pos.txt` 第 1 行 / `…\ONCE_20261027_120832\chain*.txt` 第 1 行 | 见索引 | 第 1 行 `--root` | — | 成功=沙箱，10-27 12:00 后=本体 | 是否影响连接 | ✅ 本轮读取 |
| EV-0020-09 | 大厅源码 | `CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py` | `ff4732041b673d89fa2bf1f14d4540d7c5806eb859b1087634618ab12e5a8dfc` | 行 1090–1150 | 工作 kit | mmstart 处理逻辑 + coop_map 自校正闭环 | 客户端行为 | ✅ 本轮读取 |
| EV-0020-10 | 战斗服源码 | `CODOL_SERVER_319_20261021\src\battle\battle_service.c` | `7e56b9b7e9206018f4fb742ecb117e759197509e1c10006f972edccc0021677e` | 行 1061–1140 | C 服 | UDP 包入口 `codol_battle_service_on_packet` | — | ✅ 本轮读取 |

**缺失的原始证据**

| 项 | 标记 | 二手材料范围 |
|---|---|---|
| 10-26 成功轮的客户端内存转储 | **MISSING_PRIMARY_EVIDENCE** | 无；最近转储为 `EARLIEST2_20261027_132645`（失败区间） |
| 任意一轮的网络抓包（pcap） | **MISSING_PRIMARY_EVIDENCE** | 从未采集（`THIRD_ROUND_PREREQUISITES R3-A03` 至今 OPEN） |
| 用户每轮实际点击的 UI 入口截图 | **MISSING_PRIMARY_EVIDENCE** | 只能从 mmstart 形态反推 |

---

## 05. 源码级定位

### 5.1 服务端（战斗服）——唯一入口

**文件**：`CODOL_SERVER_319_20261021/src/battle/battle_service.c`
**函数**：`codol_battle_service_on_packet`
**行号**：1061–1140
**调用者**：`main.c:29` 的 `battle_sink()` ← `codol_transport_set_packet_sink(server, battle_sink, server)`
（`main.c:112`）← `codol_transport_poll()`（`main.c:160`）

```c
void codol_battle_service_on_packet(codol_battle_service_t *svc,
                                    const codol_netadr_t *from,
                                    const uint8_t *pkt, int len)
{
    if (!svc || !from || !pkt || len <= 0) return;
    /* ① NAT 遍历 */
    n = codol_battle_try_nat_reply(&svc->battle, pkt, len, reply, sizeof(reply));
    ...
```

| 项 | 值 |
|---|---|
| 输入 | UDP 原始包 + 来源地址 |
| 输出 | 无（副作用：调用 `svc->send`） |
| 前置条件 | UDP socket 已 `bind 0.0.0.0:28960`（`main.c:104`） |
| 失败返回 | 无声返回（`len<=0` 或各 try 全败时直接 return，**不打日志**） |
| 与 Issue 的关系 | 这是"零收包"的**观测点**：只要客户端发了任何包到这里就会打日志 |

**关键**：该函数对"任意包"都会打 `TX_NAT_REPLY` / `TX_DTLS_INIT_ACK` / `KEY_EXCHANGE_OK` / `RX_CLIENT_GAME_HEADER` 之一。
三者在失败轮全部缺失 ⇒ **不是"包来了但没识别"，是"包根本没来"**。

### 5.2 大厅（决定客户端该连哪）

**文件**：`CODOL_VERIFIED_GOLDEN_20261019/lobby_server.py`
**函数**：`reply_objects()`（行 731 起）内的 `mmstart` 分支（行 1090–1150）

```python
m = re.search(rb"mmstart[^\x00]{0,512}", body)
if m:
    full_cmd = m.group(0)
    ...
    _map = re.search(r"\bmap\s+([^;\s]+)", _cmd_txt)
    _gt  = re.search(r"\bg_gametype\s+([^;\s]+)", _cmd_txt)
    log("       ★ mmstart 完整命令: %s" % _cmd_txt)
    log("       ★ mmstart 选择: gametype=%s map=%s" % (...))
```

| 项 | 值 |
|---|---|
| 输入 | `6/14` 的 payload |
| 输出 | ACK + 可选 pushes |
| 副作用 | **写 `coop_map.txt`、写 `active_room.json`**（行 1120–1143） |
| 失败返回 | 无；解析不到 map/gt 时 `_map`/`_gt` 为 None，**只记日志不报错** |
| 与 Issue 的关系 | ① 它决定下一次 `21/5 findSessions` 回哪张图；② 它的日志是判断"客户端要打哪张图"的唯一窗口 |

### 5.3 多版本实现比较

| 版本 | 大小 | mmstart 处理差异 |
|---|---|---|
| `REF_LOBBY_KIT/lobby_server.py`（受保护） | 76,410 B | 无 mmstart 自校正闭环 |
| `CODOL_VERIFIED_GOLDEN_20261019/lobby_server.py`（工作） | 88,162 B | 有 `coop_map.txt` 闭环 |
| 失败区间 D 的 kit | 108,173–109,705 B | 有；另加 room push、`102/7` 分支 |

⇒ 三个版本的 `mmstart` 分支行为**不完全相同**，任何"服务端行为"结论都必须注明用的是哪份。
本 Issue 的源码定位以**工作 kit 88,162 B** 为准。

---

## 06. 客户端逆向定位

| 项 | 值 |
|---|---|
| 客户端映像 | `COD OL\codoMP_client_shipRetail.exe`，7,841,344 B，SHA `36997674…b537` |
| ImageBase | `0x00400000` |
| DllCharacteristics | `0x8100`（**DYNAMIC_BASE 未置位 ⇒ ASLR 关闭**） |
| 验证过的关键地址 | 见下表 |

| 语义 | VA | RVA | 证据 | 已证实 | 未证实 |
|---|---|---|---|---|---|
| 连接状态 值→名 映射 | `0x005C8060` | `0x1C8060` | 反汇编跳表 0..10 | 存在且映射正确 | 无人调用（`call 0x5C8060` 零命中，走间接调用） |
| CA 状态名串 | `0x00DC0900`–`0x00DC0990` | — | 同上 | 11 个名字 | — |
| `getchallenge` / `connect %s "%s"` 参数表 | — | — | `READY_BUTTON_NO_RESPONSE §5` | 是**战斗服 connect 命令参数表** | 不是 UI 状态变量（已纠正） |
| 战斗服地址来源 | — | — | 未定位 | — | **FIRST_UNPROVEN_EDGE** |

**必须检查的四类陷阱（本 Issue 的结论是否踩到）**

| 陷阱 | 本 Issue 是否踩到 |
|---|---|
| RVA/VA 混淆 | **否**。本 Issue 未用绝对地址做数据结论 |
| 混用不同客户端版本地址 | **否**。全部实机均 3.19 |
| 把 TQOS/TDR 路径当游戏网络路径 | **否**。本 Issue 不涉及该函数族 |
| 把静态字符串出现当作函数一定执行 | **否**。`getchallenge` 只用来确认参数表存在 |
| 把 2697/IW4X/CoD4x 结构直接套用 | **否** |

**第一条未闭合边（客户端侧）**：
"客户端收到含战斗服地址的应答" → "客户端创建 UDP socket 连 28960"。
需要什么才能闭合：一次**带抓包**的成功/失败对照，或能读活进程时观察 socket 创建。

---

## 07. 网络协议级定位

本 Issue 的协议分析只在**大厅 TCP 3074** 一侧有字节证据；战斗服 UDP 28960 一侧零样本。

### 7.1 大厅侧（已有字节）

| Offset（payload 内） | Length | Field | Encoding | Evidence |
|---|---|---|---|---|
| 0 | 6 | `mmstart` | ASCII | EV-0020-01 |
| — | — | `map <name>;` | ASCII（**成功轮存在，失败轮 D 缺失**） | EV-0020-03 vs 01 |
| — | — | `g_gametype coop;` | ASCII | 同上 |
| — | — | `roomChatChannelID <u64>` | ASCII 十进制 | 同上 |
| — | — | `2486/3265/2489/2574/2500` | ASCII 整数，语义 **UNKNOWN** | 同上 |

**证据等级**：`C-bytes`（官方客户端字节，单向）。

### 7.2 战斗服侧

| 报文 | 方向 | 成功轮 | 失败轮 |
|---|---|---|---|
| NAT 探针 | C→S | ✅ `TX_NAT_REPLY 29B` | ❌ 零 |
| DTLS Init | C→S | ✅ `TX_DTLS_INIT_ACK 38B` | ❌ |
| 密钥交换 | C→S | ✅ `KEY_EXCHANGE_OK … 114B` | ❌ |
| `getchallenge` | C→S | ✅ `RX_OOB cmd='getchallenge 0 "e7c8a98a6b4c2d0e"'` | ❌ |
| `connect` | C→S | ✅ 含 `\name\…\xuid\…\natType\3\rank\69\…` | ❌ |
| `stats` | C→S | ✅ `index=0 total=764 count=1` | ❌ |
| `heartbeat` | C→S | ✅ 持续 | ❌ |

**不得**因为"协议已实现"而推断"客户端会接受"——本 Issue 恰恰是协议可用但连接未发生。

### 7.3 关键字节对照（成功轮 getchallenge）

```
RX_OOB cmd='getchallenge 0 "e7c8a98a6b4c2d0e"'
   ↑ e7c8a98a6b4c2d0e = 0x6B4C2D0E 低-高字节序 = 房间对象 +0x30 的 8 字节标识
```
见 `docs/ROOM_OBJECT_LAYOUT_20261028.md`：房间对象 `+0x030 = 6B4C2D0E E7C8A98A`。
⇒ **`getchallenge` 的 challenge 串来自客户端自己的会话标识**，与本机 `battle_security_key` 无关。

---

## 08. 数据流与调用链

```
[用户点击 剧情/PvE 或 BOT 房间的"开始"]
        │                                   PROVEN（mmstart 到达大厅）
        ▼
[客户端 → 大厅 6/14 mmstart]                PROVEN  EV-0020-01/03
        │
        ▼
[lobby_server.reply_objects mmstart 分支]
  ├─ 解析 map/gametype                      PROVEN（成功轮 map 非 ?）
  ├─ 写 coop_map.txt                         PROVEN（成功轮日志"已记住剧情地图"）
  ├─ 写 active_room.json                     PROVEN
  └─ 回 ACK / 可选 room push                 PROVEN
        │
        ▼
[客户端解析应答：拿到战斗服地址]             UNKNOWN  ← ★★ FIRST_UNPROVEN_EDGE
        │
        ▼
[客户端创建 UDP socket → 28960]             CONTRADICTED（失败轮零 RX）
        │
        ▼
[NAT → DTLS → ECDH → getchallenge → connect] PROVEN（成功轮全线）
        │
        ▼
[stats / heartbeat / gamestateupdate]        PROVEN（成功轮）
        │
        ▼
[服务端 TX_GAMESTATE → TX_SNAPSHOT]          PROVEN（成功轮）
        │
        ▼
[客户端进图]                                 PROVEN（RUNENC4BIT_20261024_1102，二手）
```

**FIRST_UNPROVEN_EDGE** = "客户端解析应答 → 创建 UDP socket"。

要闭合它需要：
1. 成功/失败的**同一客户端**抓包对照；或
2. 能读活进程时观察 `connect()`/`sendto()` 调用（当前被 ACE 封死，见 ISSUE-0045）。

---

## 09. 根因分析

| Hypothesis | 技术解释 | 支持证据 | 反对证据 | 状态 | 验证方法 | 成本 |
|---|---|---|---|---|---|---|
| **H1** 地图不在客户端可加载集合 ⇒ 不连 | 客户端在 select-session 后校验地图可用性，不可用则静默放弃 | 8/8 成功全为 `coop_train_mp_firingrange`；26/26 失败为其它图或图缺失 | 区间 B/C **带**可用地图名（cargoship 的 `.ff` 在盘上，13.6 MB）仍失败 | **高可信（未证）** | 差分实验 E2 | 1 轮 |
| **H2** 进入路径（PvE 直接开局 vs 房间内开始） | 房间路径需先完成"准备"（ISSUE-0009），未完成则不开局 | 成功 8 轮全部**不建房**；失败全部建房 | 无法区分：与 H1 完全共线 | **高可信（未证）** | 差分实验 E3 | 1 轮 |
| **H3** `102/7` 回全 0 清空选图 | 服务端告诉客户端"你什么都没选" | 区间 C 有 102/7 且失败 | **区间 B 完全没有 102/7 也失败**；**区间 D 已改回不处理仍失败** | **已排除为普遍原因** | — | — |
| **H4** `memberCount` 影响连接 | 房间成员数 0 ⇒ 不出发 | — | 区间 B 已=1 仍失败；10-27 文档已记 | **已排除** | — | — |
| **H5** mmstart 推 StartGame 打断 | 自造 109B StartGame 让客户端等错东西 | — | 区间 B **未推** StartGame（"仅空应答"）仍失败 | **已排除** | — | — |
| **H6** 战斗服未启动 / 端口占用 | — | — | 失败轮 `_battle_out.txt` 头部完整（监听成功） | **已排除** | — | — |
| **H7** 沙箱 vs 本体环境差异 | 本体中 IIPS/资源层行为不同 | D4：成功=沙箱；10-27 12:00 起=本体 | 区间 B **同一沙箱**仍失败 | **已排除为区间 B 原因**；对区间 C/D 仍可能是共因 | E1（在沙箱里跑一次） | 1 轮 |
| **H8** 房间下行推送格式错误让客户端停在房间状态 | 见 ISSUE-0010 | 失败轮都伴随自造 room push | 区间 B 的 room push 只是"回显频道推送"，非新格式 | **低可信** | 由 ISSUE-0010 的实验覆盖 | 多轮 |
| **H9** `task_params.txt` 里的未知指令 | 区间 B 起出现 `6c080800000002000000000000000500000000` | 仅在失败区间出现 | 未定位写入者与语义 | **低可信** | 查写入点 | 中 |

**结论：不能写单一根因。** H1 与 H2 是仅剩的两个高可信候选，且历史数据无法分离。

---

## 10. 历史修复尝试

| 时间 | 文件 | 改动 | 改前 | 改后 | 结果 | 是否保留 |
|---|---|---|---|---|---|---|
| 2026-10-07 | `codol_crypto.py` | `coop_map.txt` 自校正 | 21/5 恒回 `mp_firingrange` | 按上次 mmstart 的 map 回 | 使 10-26 8 轮成功 | ✅ 保留 |
| 2026-10-26 22:xx | `lobby_server.py` | mmstart 记录全文 | 只记 token | 记 map/gametype | 使成功可诊断 | ✅ |
| 2026-10-27 14:04 | `lobby_server.py:1002` | `memberCount` 0→1 | 0 | 1 | dwRoomMatchUber 出现；**连接未恢复** | ✅ |
| 2026-10-27 | `lobby_server.py` | `102/7` 回显 50/50 全 0 | 空 ACK | 555B 回显 | **每 5 秒重发，更差** | ❌ 已回滚为不处理 |
| 2026-10-28 | kit | mmstart 不推 StartGame | 推 109B | 仅空应答 | 仍零 RX | ✅ 保留 |
| 2026-10-28 | kit | `mmstart` 变成 `playlist 37` | 由客户端产生 | — | 仍零 RX | （客户端行为，非我们改） |

**为什么都没有彻底解决**：全部改动都在"服务端如何回答"这一侧，
而失败边界 `FIRST_UNPROVEN_EDGE` 在**客户端如何把回答变成 socket**这一侧。
没有任何一次实验改变过 H1（地图）或 H2（入口路径）这两个自变量。

---

## 11. 当前代码状态

| 检查项 | 结论 | 位置 |
|---|---|---|
| 相关逻辑是否仍存在 | ✅ 是 | `battle_service.c:1061`；`lobby_server.py:1090` |
| 是否被重构/覆盖 | ❌ 否 | — |
| 是否存在回归 | **是**：`mmstart` 分支现在只记日志、返回 ACK；`coop_map.txt` 自校正仍生效但输入无 map | `lobby_server.py:1102-1143` |
| 死代码 | `build_startgame_payload` 仍被调用（区间 D 已不推） | `lobby_server.py:1147` |
| 无调用者的功能 | 无（本 Issue 范围） | — |
| 测试专用分支 | 无 | — |
| 硬编码值 | `ROOM_ID = 0x1122334455667788`；`GAME_IP/GAME_PORT` | `lobby_server.py` 顶部 |
| 缺 ACK/超时/异常 | 战斗服 `on_packet` 对未知包**静默返回**（无日志） | `battle_service.c:1070` |

---

## 12. 精准复现方法

**环境**
- Windows 10 Pro 19045，提权 agent 在线（`CODOLServer/logs/elevated_agent.json`）
- 游戏根：沙箱 `run_codol_001\sandbox_ifs1_20260923`（E1 用）或本体 `COD OL`
- 战斗服：`codol_battle_server.exe --bind 0.0.0.0 --port 28960`

**启动前检查**
1. `python -I run_codol_001/run_frozen_chain_once.py --verify-only` → 期望 `protected baseline: OK`
2. 无残留客户端进程；3074 无监听
3. `kit/coop_map.txt` 内容 = 目标地图名

**测试输入**
UI：走**剧情/PvE 直接开局**入口（不是 BOT 房间），选择靶场关。

**预期输出（成功）**
`kit/_battle_out.txt` 出现：
```
[battle] TX_NAT_REPLY 29B
[battle] TX_DTLS_INIT_ACK 38B
[battle] KEY_EXCHANGE_OK -> ...
[battle] RX_OOB cmd='getchallenge ...'
```

**实际失败输出**
`kit/_battle_out.txt` 只有 7 行初始化，无任何 `TX_`/`RX_`。

**日志采集**：`runs\<RUN_ID>\kit\lobby_srv.log`、`kit\_battle_out.txt`、`chain_*.txt`

**停止条件**：出现第一条 `TX_NAT_REPLY`（成功）或 240 秒到期（失败）。

**清理**：战斗服进程停止；`runs/.frozen_launch_used` 令牌消耗后需 `--authorize-next-launch` 才能再跑。

> `REPRODUCTION_NOT_YET_ESTABLISHED` **不适用** —— 成功路径有完整日志可对照。

---

## 13. 最小验证实验

**实验 E1（必须先做）**

| 项 | 内容 |
|---|---|
| 只改一个变量 | 无（完全复刻 10-26 22:08 的成功条件） |
| 变量取值 | 根=沙箱、`coop_map.txt=coop_train_mp_firingrange`、PvE 直接开局、不建房 |
| 通过判据 | `_battle_out.txt` 出现 `TX_NAT_REPLY` |
| 失败判据 | 240 s 后仍只有 7 行初始化 |
| 区分哪两个假设 | H7（环境退化）vs 其它 |
| 为什么必须最先做 | 若 E1 失败，说明"成功基线本身已不可复现"，后续 E2/E3 无意义 |

**实验 E2（关键判据）**：同 E1，只把 `coop_map.txt` 与 UI 选择换成 `coop_training_mp_cargoship`。
- 若 E2 零 RX ⇒ **H1（地图）成立**
- 若 E2 有 RX ⇒ 地图不是原因，转 E3

**实验 E3**：同 E1，只把入口换成 BOT 房间。
- 若 E3 零 RX ⇒ **H2（入口路径）成立**

完整判据表见 `CONNECTION_REGRESSION_DIFFERENTIAL.md §6`。

---

## 14. 修复方案

**根因未定 ⇒ 只能给条件式方案。**

**方案 A（若 E2 证明是地图）**
| 项 | 内容 |
|---|---|
| 目标文件 | `CODOL_VERIFIED_GOLDEN_20261019/lobby_server.py` |
| 目标函数 | `reply_objects()` 内 `21/5 findSessions` 分支（行 789–849）与 `mmstart` 分支（行 1090） |
| 修改内容 | 在 `_map`/`_gt` 缺失时**拒绝回 ACK**并打出 `MAP_UNRESOLVED` 错误，而不是继续；同时在 `findSessions` 与 `mmstart` 之间做一致性断言 |
| 理由 | 当前"解析不到也照常回"掩盖了真实的分歧 |
| 前置证据 | E2 结果 |
| 副作用 | 可能让原本"看起来正常"的轮次明确失败；不影响成功基线 |
| 回滚 | 恢复原文件（kit 内单文件） |

**方案 B（若 E3 证明是入口路径）**
| 项 | 内容 |
|---|---|
| 目标 | `lobby_server.py` 的 room push / ready 分支 |
| 修改内容 | 让房间内开局复用 PvE 的 `(map, gametype)` 下发路径，而不是自造 room envelope |
| 前置证据 | E3 结果 + ISSUE-0010 的格式结论 |
| 副作用 | 与 ISSUE-0010/0017 强耦合 |

**不得现在写补丁**：H1/H2 都未证。

---

## 15. 修复影响分析

| 受影响面 | 影响 |
|---|---|
| 大厅 | 方案 A 会让"地图未解析"显式失败 |
| 预约 | 无 |
| 战斗连接 | 目标就是它 |
| 加密会话 | 无 |
| GameState | 若地图变了，`_gs_adapt_dynamic` 会改 header（`battle_service.c:302`） |
| Snapshot | 无直接影响 |
| Usercmd | 无 |
| 多客户端 | 无 |
| 地图加载 | 与 ISSUE-0022 联动（战斗服当前不换碰撞） |
| 历史成功基线 | 方案 A 不改成功路径 |

**回归风险**：方案 A 的错误分支可能在"本来能过"的边界上误报，需要在 E1 上回归验证。

---

## 16. 验收标准

本 Issue 视为解决，当且仅当**全部**满足：

1. `_battle_out.txt` 出现 `TX_NAT_REPLY`（客户端真的发包了）
2. 随后出现 `KEY_EXCHANGE_OK`
3. 随后出现 `RX_OOB cmd='getchallenge`
4. 随后出现 `RX_OOB cmd='connect`
5. 大厅日志与战斗服日志时间戳差 < 5 s（同一次会话）
6. 同一次运行里客户端 PID 全程不变
7. 该结果在 **E2 或 E3 的失败条件**上不再出现

⚠️ **不能**用"单元测试通过"或"模拟客户端通过"代替以上任何一条。

---

## 17. 回归测试

| 测试 | 证明 | **不能**证明 |
|---|---|---|
| `test_battle.c` / `test_crypto.c` | 服务端 NAT/DTLS/ECDH 自洽 | 客户端会发第一个包 |
| `probe_world_damage` | 世界/伤害离线可用 | 同上 |
| 本 Issue 新增：**连接回归用例** | E1 通过后，脚本断言 `TX_NAT_REPLY` 出现 | — |
| 历史成功基线回归 | E1 复现 10-26 成功形态 | 其它地图可用 |

建议新增一个 run 级断言脚本（目前不存在），把上表第 3 行变成可自动化检查。

---

## 18. 最终技术结论

**当前状态**：`OPEN`。客户端完成 mmstart 后不发起 UDP 连接；战斗服零收包。

**已经证明的事实**：
1. 战斗服监听正常、协议栈可用（10-26 8 轮全链路 RX）。
2. 失败不是"包被丢弃"——`on_packet` 对任何包都会打日志。
3. `102/7`、`memberCount`、`StartGame` 推送**都不是**普遍原因（各自被区间 B/C/D 否证）。
4. 在全部 34 次带 mmstart 的运行上，`map==coop_train_mp_firingrange && 不建房` 与 RX 出现 **100% 共变**，零反例。
5. 地图与入口路径在历史数据中完全共线，无法分离。

**尚未证明的事实**：
- 是地图、是入口路径、还是两者的组合导致客户端不连接。
- 沙箱 vs 本体是否也是共因。
- 客户端内部在哪个函数决定"不连"。

**第一条未闭合证据链**：
`客户端解析 mmstart 应答` → `客户端创建指向 28960 的 UDP socket`（`FIRST_UNPROVEN_EDGE`）。

**当前最可信根因**：两个并列候选，均为高可信未证实——
H1「所选地图不在客户端可加载集合」、H2「进入路径为房间内开始而非 PvE 直接开局」。

**下一步最小实验**：E1（复刻成功基线）→ 视结果做 E2 / E3。

**最小修复条件**：E2 或 E3 中至少一个给出确定归因。

**完成验收标准**：§16 的 7 条全部满足。

**是否可以交给开发 Agent 直接修复：NO**
必须先完成的取证：**E1 → E2 → E3 三轮差分实验**。
在这三轮之前，任何补丁都是猜测。

---

## 19. 修改影响分析

见 §15。

## 20. 可测量的验收标准

见 §16。

## 21. 回归测试方案

见 §17。

## 22. 修复准备度

**INVESTIGATION_READY**

- **下一步**：E1→E2→E3 差分：分离'地图'与'入口路径'两个共线自变量。
- **上游依赖**：见 §01
