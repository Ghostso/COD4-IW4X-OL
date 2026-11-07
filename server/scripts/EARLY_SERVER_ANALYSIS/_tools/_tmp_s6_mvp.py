# -*- coding: utf-8 -*-
import io, os
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\06_ASSESSMENT"
md = r"""# EARLY_SERVER_06 — 最小验证计划

> 阶段 6 交付物（第 2 件）。**本轮只提交计划，不执行任何运行实验或兼容性补丁。**
> 每项实验标注：目的 / 前置 / 步骤 / 预期观察 / 成功判据 / 风险 / 隔离要求 / 是否需批准。

---

## 实验分层

- **Tier 0 — 纯离线（不启动服务端、不连客户端）**：可立即执行（但仍遵守"本轮不执行"约束，待批准）。
- **Tier 1 — 隔离运行（需批准）**：启动样本服务端或客户端。
- **Tier 2 — 端到端（需批准 + 严格隔离）**：真实 C1 ↔ 服务端。

---

## E1（Tier 0）— 离线复算 DATA MAC，判定冲突 A

- **目的**：确定 DATA 记录使用 **AES192/Tiger192** 还是 **AES128/SHA1**。
- **前置**：`lobby/captures/*.jsonl`（4 天流量捕获）；`dedicated/src/codol/net/codol_crypto.c`；C# `Aes128.cs`/`CodolProtocol.cs`。
- **步骤**：对一条已记录 DATA 记录，用同一 `(shared_x, securityKey, counter, ciphertext)`：
  1. 按 native `CODOL_EncryptRecord`（Tiger192→key24，AES192-ECB，小端 CTR，HMAC-SHA1 截 8B）复算 MAC；
  2. 按 C# 原语（AES128 + SHA1 计数器）复算 MAC；
  3. 比对记录头 `[6:14]` 的 8B MAC。
- **预期观察**：仅一种原语能验通。
- **成功判据**：某一侧 MAC 逐字节匹配。
- **风险**：低（只读、离线）。**隔离**：无。**批准**：需（本轮不执行）。

## E2（Tier 0）— 离线复算 COOKIE_ECHO 长度/偏移，判定冲突 B

- **目的**：确定 COOKIE_ECHO 是 **189B** 还是 **219B**。
- **前置**：`captures` 中 COOKIE_ECHO 记录；`codol_handshake.c:47/54`；C# `CodolProtocol.cs:35`。
- **步骤**：取真实 COOKIE_ECHO 记录，测量总长度；按 native 偏移（公钥@89、id@106）与 C# 偏移（公钥@119、u64@111）分别解析，看哪个自洽。
- **预期观察**：长度与字段偏移只与一侧吻合。
- **成功判据**：长度 + 字段偏移一致。
- **风险**：低。**批准**：需。

## E3（Tier 0）— 会话描述符对齐

- **目的**：确认 258B session 记录 + 16B securityKey 的下发形态。
- **前置**：`lobby/handoff/*`；C# `SessionDescriptor.cs`；`build/bin/session_descriptor/*.bin`。
- **步骤**：对 `session_record_258.bin` 与 `mission_*.bin` 做逐字节比对；核对 securityKey 与 ECDH 输入关系。
- **成功判据**：现有 C# 描述符与早期 lobby 产物逐字节一致（或差异被解释）。
- **风险**：低。**批准**：需。

## E4（Tier 0）— 契约层闭环核对

- **目的**：确认 lobby↔战斗服文本契约完整。
- **前置**：`game_admissions.txt`、`startgame.txt`、`map_selection.state.json`、`codol_admission.c`、`codol_match_status.c`、`match_server_control.py`。
- **步骤**：逐字段对照名册行格式、`sh1x_status` 字段、5 条 RCON 命令。
- **成功判据**：字段一一对应，无缺项。
- **风险**：低。**批准**：需。

## E5（Tier 1）— 服务端无客户端自检（隔离）

- **目的**：确认当前 build 能加载目标地图而不因缺资产/脚本失败退出。
- **前置**：隔离目录；样本 `bin/home`；`--codol-info` 先做无 socket 检查。
- **步骤**：先 `--codol-info`（不开 socket、不载资产）；再在隔离副本尝试载 `mp_killhouse_sh`，观察 `missingasset.csv` 与 `sys_error.txt`。
- **预期观察**：初始化到 leaves/configstrings，或明确失败点。
- **成功判据**：载图不因缺资产/脚本崩溃。
- **风险**：中（启动二进制）。**隔离**：必须（独立目录、不连公网）。**批准**：需。

## E6（Tier 2）— 早期 C1 ↔ 服务端 端到端（需批准 + 严格隔离）

- **目的**：判定真人 C1 能否越过 CS_PRIMED 进入世界。
- **前置**：早期 C1（`CODOL_Client\codoMP_client_shipRetail.exe`）；隔离网络；抓包。
- **步骤**：启动服务端 → 启动 C1 → 抓包观察握手→gamestate→首个 usercmd。
- **预期观察**：是否收到可解析 gamestate；是否进入世界。
- **成功判据**：C1 进入世界并发出 usercmd。
- **风险**：高（运行客户端/服务端；**不做**任何保护绕过）。**隔离**：必须。**批准**：需（单独）。

---

## 不做什么（本轮约束重申）

- **不启动**样本服务端、**不运行** `.cmd`/安装包/未知工具。
- **不做**反调试/反作弊绕过；**不恢复**真实凭据（`native_server_rcon.txt` 口令不外泄）。
- **不修改**样本；**不合并**到现有 CODOL 工作目录。

---

## 建议执行顺序

`E1 → E2 → E3 → E4`（全 Tier 0，零风险） → 视结论决定是否申请 `E5`/`E6`。
"""
with io.open(os.path.join(OUT,"EARLY_SERVER_06_MINIMAL_VALIDATION_PLAN.md"),"w",encoding="utf-8",newline="") as f:
    f.write(md)
print("written", len(md))
