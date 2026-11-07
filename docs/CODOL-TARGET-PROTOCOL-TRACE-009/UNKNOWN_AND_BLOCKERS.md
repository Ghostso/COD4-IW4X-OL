# UNKNOWN_AND_BLOCKERS — 未定位消费者、未确认字段与下一步最小任务

**目标版本：** CODOL 3.19.26.22 / Build 1649370
**日期：** 2026-10-13（Asia/Shanghai）

---

## 1. 阻塞总览

| 编号 | 层 | 阻塞 | 等级 | 影响 |
|---|---|---|---|---|
| BLK-009-01 | BRIDGE | `[matching+0x288]` 闩锁从未为 1 | P0 | 客户端从不发送战斗首包 |
| BLK-009-02 | BRIDGE | `accepted` 传输通道未定位 | P0 | 无法安全构造预约应答 |
| BLK-009-03 | BRIDGE | `accepted` 字节形态冲突（带/不带 u32 前缀） | P0 | 可能导致闩锁不置位 |
| BLK-009-04 | BRIDGE | 战斗端点（地址+端口）来源未定位 | P0 | 无法下发战斗服务器位置 |
| BLK-009-05 | BATTLE | snapshot 帧内位宽 / delta baseline 未闭合 | P0 | 无法实现正确 snapshot |
| BLK-009-06 | BATTLE | 实体增删 / entityId 映射未闭合 | P0 | 无法实现实体同步 |
| BLK-009-07 | BATTLE | 战斗端点从未被观测 | P0 | 整条战斗链缺实测 |
| BLK-009-08 | A/B | 加壳 `.tvm0`（约 31 MB）吞掉 netcode 明文 | P1 | 静态面不可直接定位游戏 netcode |
| BLK-009-09 | LOBBY | `accepted` 调用者（ARG1..ARG4）未追踪 | P1 | 无法确定帧字段 |
| BLK-009-10 | BRIDGE | 大厅连接战斗期间去留未知 | P1 | 状态机不完整 |
| BLK-009-11 | LOBBY | `mmstart` 数字 cvar 语义未知（901/2486/2490/3265/2489/2574/2500） | P2 | 命令语义不完整 |
| BLK-009-12 | BATTLE | 参考源码/探针版本归属需逐条核验 | P1 | 防跨版本混用 |

---

## 2. 逐项详证

### BLK-009-01 — 闩锁未完成（P0，首要）

- 事实：`[matching+0x288]` 的唯一消费者 `0x00634402` 驱动 `mmstart`；但 019/023/024/025/029 全部运行中 `this288` **从未为 1**。
- 证据：`DEV-BOOKING\OLMOD-CODOL-BOOKING-BATTLE-BRIDGE-030.md` §8/§16。
- 影响：`mmstart` 从未构造/发送 ⇒ 战斗首包从未出现。
- 最小解除证据：见 §3（单变量回归 031）。

### BLK-009-02 — `accepted` 传输通道（P0）

- 事实：已排除直接 `call 0x632680`、普通虚调用、Base.dll 处理；`response channel = UNKNOWN`。
- 证据：`BOOKING_PROTOCOL_SPEC-002.md` §4/§8。
- 注意：`0x85` 通道属 **2.6.9.7** 证据；ol-mod 的 `DedicatedControl` / `ClientSessionBridge` 是**自建桥**，不得当作客户端事实。
- 最小解除证据：定位 `0x803830` 返回对象的网络抽象类型，确定 TCP/UDP/IPC/共享内存之一。

### BLK-009-03 — accepted 字节形态冲突（P0）

- 事实：ol-mod 存档断言为**带 u32 前缀**（`13 08 | 13 00 00 00 | 0f 00 00 00 | "mmbook accepted"`）；本项目 023 之后实现**去掉前缀**，疑为 REGRESSION。
- 未裁定：两者均未在目标客户端单变量复现。
- 最小解除证据：§3 实验。

### BLK-009-04 — 战斗端点来源（P0）

- 事实：`Booking -> 28960 linkage = UNKNOWN`；`BATTLE_28960 = NOT_OBSERVED`。
- 最小解除证据：追 `0x633FE0` 回调注册对象接口，与 `mmstart` 输出字段建立数据流。

### BLK-009-05 — snapshot 帧内位宽 / delta baseline（P0）

- 事实：解析器入口与 readDelta 系列 RVA 已确认（`0x0046D170`/`0x005A27F0`/`0x005A3670`），但**逐字段位宽与 baseline 未闭合**。
- 最小解除证据：对 `playerStateFields 0x00855F70`（235×12B）与 `parseSnapshot` 做位宽逐条对齐；需要一条真实 snapshot 样本。

### BLK-009-06 — 实体增删 / entityId（P0）

- 事实：`parsePacketEntities 0x0046C2F0` 已定位；新增/删除规则与 entityId→槽映射 `UNKNOWN`。
- 最小解除证据：`parsePacketEntities` 内 `readFieldIndex 0x005A3250` 的分支分析 + 真实帧。

### BLK-009-07 — 战斗端点从未观测（P0）

- 事实：`plugins/Logs` 与 AFD ETW 记录中，目标客户端族**无任何**游戏 UDP 双向会话（`docs/rt-report-game3.md` §9/§10）；所有流量被 80/443/CEF/心跳解释。
- 等级说明：这是**强否定结论**：在这段采集里游戏网络层没有建立任何连接。

### BLK-009-08 — `.tvm0` 虚拟化（P1）

- 事实：目标 EXE/DLL 均有 `.tvm0`（EXE 约 `0x4000`，DLL 约 31 MB）；`docs/network-9goals.md` §13.2.4 证明 WKNet 字段写入落在 `.tvm0` 内，静态不可解码。
- 影响：游戏 netcode 明文面系统性缺失；「扫描未命中」不等于「不存在」。

### BLK-009-09 — accepted 调用者（P1）

- 事实：`0x632680` 为 `ret 0x14`（5 参数），但 EXE 内**未找到**匹配的 5 参数虚调用点；`ARG1/ARG2` 必须等于 A/B，但**由哪个帧字段携带未知**。
- 证据：`BOOKING_PROTOCOL_SPEC-002.md` §6。

### BLK-009-10 — 大厅连接去留（P1）

- 事实：战斗连接期间大厅连接**保留/关闭/复用/异步**四者均无证据。

### BLK-009-11 — `mmstart` cvar 语义（P2）

- 事实：构造器 `0x632070` 与格式串已确认；`901/2486/2490/3265/2489/2574/2500` 的字段含义 `UNKNOWN`。

### BLK-009-12 — 版本归属核验（P1）

- 事实：`_e1_regression\ol-mod-olfinal` 的 `AGENTS.md` 自称目标为「3.3.3.3 QA」，但其 `EngineBindings` 常量与 `client_probe` 注释指向 **1649370 / 3.19.26.22**。
- 纪律：本轮对 E7 结论一律要求「目标 EXE 内独立命中同一 RVA」才升级；其余标 `REFERENCE`。

---

## 3. 下一步最小任务（唯一）

### TASK-031 — 单变量回归实验（判定闩锁与 accepted 形态）

**目的：** 判定 `accepted` blob 形态是否为 `[matching+0x288]` 不置 1 的原因。

**步骤（仅两变量）：**
1. 把 `accepted` blob 恢复为 ol-mod 存档形态的**精确字节**：
   ```
   13 08 | 13 00 00 00 | 0f 00 00 00 | 6d6d626f6f6b206163636570746564
   ```
   （即 `FR_BOOKING_ACCEPTED = b"mmbook accepted"`，15 字节，无 NUL；外层写 `u32(15)` —— 回滚 023）
2. 恢复 019 的 A/B 对齐（`codol_crypto` L542 = SessionId），使 G4/G5 可通过。
3. **不引入其他变量。**

**判据：**
- 若 `[matching+0x288]` 由 0 → 1 **且** lobby 日志出现 `mmstart` 命令 ⇒ 存档形态成立、023 被证伪。
- 若仍为 0 ⇒ blob 形态不是唯一原因，回到 BLK-009-01 继续分叉。

**条件：** 独立、受控的本地测试环境；**不登录/不连接第三方线上服务**；未执行则以 `NOT_RUN` 记录。

**为什么这是最小任务：** 它是唯一能把「大厅预约」与「战斗首包」连起来的可验证实验；在此之前，任何战斗协议实现都缺少真实客户端首包。

---

## 4. 对本地战斗服务器的最小实现条件

| 条件 | 状态 | 说明 |
|---|---|---|
| 战斗入口：OOB `getchallenge`/`connect` | 已知形状 | 可按 REFERENCE 实现探针 |
| DTLS 握手（NAT/INIT/COOKIE，67B bdCommonAddr） | 已知形状 | 需按 67B 修正 |
| netchan（1154B/128/新分片头） | 已确认 | 可直接实现 |
| 服务端命令 0..5（EOF=5） | 已确认 | 可直接实现分派 |
| gamestate/configstring 编码 | REFERENCE | 索引表需按 1649370 重建 |
| snapshot 帧 | **未闭合** | 缺位宽与 baseline |
| **大厅→战斗闩锁** | **未闭合** | 缺 accepted 形态与通道 |
| 战斗端点下发 | **未闭合** | 缺来源 |

> **结论：** 现有本地服务器**不能**使目标客户端完成初始化并进入可交互状态，首要缺口是 **C 层交接（BLK-009-01/02/03/04）**，其次是 **B 层 snapshot（BLK-009-05/06）**。

---

## 5. 纪律声明

- 未修改 FREEZE-005、正式服务器源码、原始游戏文件、原始抓包与运行时镜像。
- 未跨版本套用 2.6.9.7 / 3.3.3.3 / IW4X 结论。
- 未把大厅登录成功等同于战斗连接成功；未把收到 gamestate 等同于可交互。
- 未伪造测试结果；未执行的动态验证标 `NOT_RUN`。
- 未进入协议实现。
