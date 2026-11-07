# UNKNOWN_AND_BLOCKERS — 未知项、阻塞与最早未满足条件

**目标版本：** CODOL 3.19.26.22 / Build 1649370
**日期：** 2026-10-13（Asia/Shanghai，第二次修订）
**证据效力更正：** 本次运行客户端停在 "100" 弹窗，**未进入大厅**；动态结论统一降级为 `INVALID_PRECONDITION`。

---

## 1. 最早未满足条件（更正后：**唯一成立的一条**）

> **`CLIENT_DID_NOT_ENTER_LOBBY` —— 客户端未通过已固化的正式启动链成功进入游戏，停在 "100" 弹窗错误处（`rc=-1 / 0xFFFFFFFF`）。**

这是本链**唯一成立的**最早未满足条件。它是**业务层**的前置条件，位于所有 matchmaking 业务之前。

**明确撤销的上一条表述：**
~~"客户端从未发出 `mmbook`"~~ —— 该表述**仅适用于本次错误启动会话**，
**不得**推导为"正常大厅流程不会触发 `mmbook`"。

**推论（严格）：**
1. 未进入大厅 → 无业务会话 → `mmbook` 是否触发**无从讨论**。
2. 因此 `accepted` / 闩锁 / `mmstart` / 战斗连接的动态结论**一律无效**。
3. 在"成功进入大厅且业务会话就绪"之前，**不得**执行 TASK-031 的动态基线阶段。

---

## 2. 阻塞清单（更正后）

| 编号 | 层 | 阻塞 | 状态 | 等级 |
|---|---|---|---|---|
| **BLK-031-01** | **STARTUP** | **固化启动链未复现；客户端停在 "100" 弹窗，`rc=-1`** | **OPEN（最高优先）** | **P0** |
| BLK-031-02 | METHOD | 本轮实际执行的启动链与已知成功链存在 6 项差异（含缺失 8444 portproxy） | **OPEN** | **P0** |
| BLK-031-03 | EVIDENCE | `hosts` 未逐字节还原（独立完整性事件） | **OPEN** | P1（不阻塞协议，但需闭环） |
| BLK-009-02 | BRIDGE | `accepted` 传输通道 / 调用者未定位 | OPEN | P0（静态侧） |
| BLK-009-04 | BRIDGE | 战斗端点（地址+端口）来源未定位 | OPEN | P0 |
| BLK-009-08 | A/B | `.tvm0` 虚拟化吞掉 netcode 明文 | OPEN | P1 |
| BLK-009-11 | LOBBY | `mmstart` 数字 cvar 语义未知 | OPEN | P2 |

**已因前置条件不成立而暂挂（不得记为"流程失败"）：**
`BLK-009-01`（闩锁未置 1）、`BLK-009-03`（`accepted` 形态冲突）、`BLK-009-07`（战斗端点未观测）。

---

## 3. 启动链差异（定位 "100" 错误的起点）

逐项证据见 `evidence\LAUNCH_CHAIN_DIFF.tsv`。摘要：

| 项 | 固化链（已知成功） | 本轮实际 | 匹配 |
|---|---|---|---|
| 启动脚本 | `capture_elevated_network.ps1` | `_work\lab\run_all.py` | ✗ |
| 游戏沙箱 | `sandbox_ifs1_20260923` | `sandbox_datafix_20260929` | ✗ |
| 沙箱 `dwauth.ini` | `127.0.0.1 / 0 / 127.0.0.1 / 443 / 0 / 0 / 0` | `formal-zone-lsg/auth.codol.qq.com 3074` + `0x03EA` | ✗ |
| auth 服务 | `lobby_probe_server.py` @ `8443` | `fake_auth_tls.py` @ `3074` | ✗ |
| 大厅服务 | `lobby_socket_server.py` @ `8444` | `lobby_server.py` @ `3074` | ✗ |
| portproxy | `443→8443` **与** `443→8444` | 仅 `443→8443` | **部分** |
| `iips.ini` `enable_iips` | `1` | `1` | ✓ |
| 客户端退出 | 正常跑满窗口 / `rc=0` | **`rc=-1 (0xFFFFFFFF)` @ `t=8.0s`** | ✗ |

> `CODOL_SERVER_OPERATIONS_MANUAL.md` §8：**"游戏 8 秒内 `0xFFFFFFFF` 退出 = 启动/IIPS 前置失败"**。

---

## 4. `accepted` 字节形态冲突（BLK-009-03）—— 静态部分保留

### 4.1 静态可判定（`CONFIRMED`）

- 门字符串 `0xDC69B0` = 裸 15 字节 `mmbook accepted`。
- 比较为 `push 0xf` + `call 0xC3C678`，而 `0xC3C678` 是**逐字节 `strncmp` 语义**。

### 4.2 仍不可判定（`UNKNOWN` / `INFERRED`）

- **`arg5` 指向哪里** —— 依赖接收通道/调用者，本轮未定位。该绑定方式为 **INFERRED**。

### 4.3 结论

> 形态冲突**仍未裁定**（无动态证据，且动态前置条件不成立）。
> 静态上"带内层前缀在 `arg5` 指内层起点时必失败"仅是该 `INFERRED` 前提下的条件式推论。

---

## 5. 接收通道未定位（BLK-009-02）—— 静态障碍

| 扫描 | 目标 | 命中 |
|---|---|---|
| `E8 rel32` | `0x632680` | 0 |
| 全镜像 `mov [mem], imm32` | `0xDC73A0` / `0xDC7840` | 0 |
| 全镜像指令位移引用 | `0xDC7360..0xDC7900` | 0 |
| 全镜像指令位移引用 | `0xDC73A0`/`0xDC7840`/`0xDC73B0`/`0xDC7850` | 0 |
| Base.dll 字符串 | `mmbook*` / `mmstart` | 0 |

两条 vtable 副本在镜像内零直接引用 → 经运行期计算/重定位数据安装；结合 `.tvm0`，静态可读面不足。

---

## 6. 完整性独立事件：`hosts`

**按更正要求，已作为独立完整性事件处理。**

| 项 | 值 |
|---|---|
| 实验前登记值（不可再获取） | 937 B / `07642387e67016546a0a1bab53522fe29becf2990740ccaa55e37c8fdfa2115a` |
| 当前文件值 | 915 B / `37756f9b5a3d050bb1b579a79032632b9c2596ab667056335da71aee22fdfa52` |
| 当前文件已保全副本 | `integrity\hosts_AS_FOUND_20261013_153351.txt` |
| 其他 hosts 制品副本 | `integrity\etc_hosts_artifacts\`（etc 目录全部 `hosts*` 只读副本） |
| 恢复所用快照 | `CODOLServer\_mainline\_hosts_snap\hosts.original`（915 B，同哈希） |
| 官方快照/还原工具 | `CODOLServer\_mainline\_z7_hosts.py`（`snapshot` / `apply` / `restore`） |

**查找实验前副本的结果（穷尽性）：**

| 搜索 | 结果 |
|---|---|
| 全盘扫描**所有 937 字节**文件并比对 SHA-256 | 检查 137 个候选，**0 个匹配** |
| 比对 `etc` 目录全部 `hosts*` 制品 | 无匹配 |
| 比对 `hosts_UHE_Backup\*.bak`（11 份） | 无匹配 |
| 比对 `CODOLServer\_mainline\_hosts_snap\*.bak` / `hosts.original` | 无匹配 |
| 复算 `clean_hosts()` + 追加块的前后形态 | 915 / 1036 B，**均不等于 937 B** |

**结论：** 实验前的 937 B 版本**在本机未找到任何可验证副本**。
可验证的**语义上等价**副本（`hosts.original`，915 B）已用于恢复，**已移除全部 CODOL 映射**。
**严格定性：** 这是一次**不可完全复原的系统配置修改**；**对协议结论无影响**（无 codol/QQ 残留行）。
该事件与本次 "100" 弹窗**无因果关系**（弹窗出现在该写入之前）。

---

## 7. 下一步（按更正指令，**先启动链，后协议**）

1. **核验并复现已固化启动链：**
   - 脚本：`run_codol_001\capture_elevated_network.ps1`
   - 沙箱：`run_codol_001\sandbox_ifs1_20260923`（`dwauth.ini` 为 `127.0.0.1/443` 形态，`sha256 7fc20c08…`）
   - 服务：`CODOLServer\lobby_server\lobby_probe_server.py` @ `8443`、`lobby_socket_server.py` @ `8444`
   - 网络：`portproxy 443→8443` **与** `443→8444`（**当前缺后者**）
2. **定位本次 "100" 弹窗错误的差异** —— 起点即 `LAUNCH_CHAIN_DIFF.tsv` 的 6 项差异。
3. **在成功进入大厅并确认业务会话就绪之前：**
   - **不执行** `mmbook` 触发链的动态回归；
   - **不修改** `accepted`；
   - **不修改** A/B 配对逻辑；
   - **不修改**服务器源码。
4. 只有**成功进入大厅且业务会话就绪**后，才重启 TASK-031 的**有效基线阶段**。

---

## 8. 纪律声明

- 未修改 `CODOL-BATTLE-SERVER-INTEGRATION-FREEZE-005`、服务器源码、原始游戏文件、原始抓包与运行时镜像。
- 未进入 snapshot 实现；未对客户端做 hook / 注入 / 断点 / 内存写。
- 未伪造结果；未捕获项标 `NOT_OBSERVED`，前置条件不成立项标 `INVALID_PRECONDITION`，未执行项标 `NOT_RUN`。
- 未把"未观测"升级为"不可能"；未把错误会话结论外推为正常流程行为。
