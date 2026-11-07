# -*- coding: utf-8 -*-
import io, os
OUT = r"D:\BaiduNetdiskDownload\使命召唤OL\EARLY_SERVER_ANALYSIS\04_REUSE"
os.makedirs(OUT, exist_ok=True)
md = r"""# EARLY_SERVER_04 — 复用兼容性报告

> 阶段 4 交付物（第 2 件）。基于阶段 0–3 已确认证据 + 本轮对样本的只读复核。
> 分类：**A 直接复用 / B 可移植适配 / C 仅供参考 / D 暂不可用 / E 已排除**。
> 证据标签：CONFIRMED / STRONG_CANDIDATE / CANDIDATE / UNKNOWN / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED。
> 完整逐项清单见 `EARLY_SERVER_04_REUSE_MATRIX.csv`（48 项：A=10 / B=18 / C=12 / D=2 / E=6）。

---

## 0. 一句话结论

样本服务端的**高复用价值集中在"契约层"与"协议层"**：明文 OOB 连接文法、`sh1x_status` 状态行、
准入名册、loopback RCON 控制面、以及 lobby↔战斗服的**纯文本/文件契约**——这些语言无关、已被实测旁证，可**直接复用（A 类）**。
**协议与业务逻辑主体（B 类）** 是 CoD4x fork 上的 CoDOL 原生移植，骨架完整但**面向真实 C1 的关键序列化器未收敛**。
**最核心的阻塞**不是"缺程序"，而是 **gamestate/configstrings/snapshot 序列化器未移植**（PORT §4）与 **两个未统一的密码学冲突（A/B）**。

---

## 1. 可直接复用（A 类，10 项）

判定标准：不依赖缺失组件、接口已被独立证据（实测/双端文本）旁证、无需改字节即可对接。

| id | 资产 | 复用点 | 关键证据 | 前提/风险 |
|---|---|---|---|---|
| R08 | `codol_connect.c` | getchallenge / connectResponse 文本文法 | 客户端字符串表 + lobby 实测 | protocol 字段=1（非 187）；文本契约 |
| R09 | `codol_match_status.c` | `sh1x_status ...` 状态行 | 代码 + qconsole 实测行 | 无 |
| R10 | `codol_admission.c` | 名册行准入 | 代码 + `game_admissions.txt` 样例 | key 即凭据，勿外泄 |
| R27 | `lobby/dw-capture.py`+`paths.py` | 本地大厅监听/分发 | README + 端口实测 | 1.1.1.13 专用；无认证 |
| R28 | `lobby/demonware/*` | wire + 6 服务 | 包 docstring + selftests | 版本锁定 |
| R33 | `lobby/handoff/*` | 选图 + RCON 启动战斗 | 5 条命令序列实测 | 依赖 loopback RCON |
| R40 | `lobby/selftests/*` | 离线回归 | 11 套绿 | 无 |
| R41 | 状态/契约文件 | 大厅↔战斗服接口 | 文本样例 | 口令敏感 |
| R19 | `codol/stats/*` | 结算→回写契约 | `match_report.json` | 字段语义待补 |
| R20 | `dedicated/tests/*` | 兼容性回归基座 | 127 文件 | 无 |

> 说明：A 类的"直接复用"针对的是**接口/契约**（文本行、文件格式、RCON 命令、明文 OOB 文法），
> 而非"整个程序拿来即跑"。R01（服务端主程序）本身因 PORT §4 未完成而**不属 A 类**。

---

## 2. 可移植/适配（B 类，18 项）

判定标准：逻辑完整、可独立提取，但存在明确的接口差异、依赖条件或版本锁定。

### 2.1 传输与协议核心（R07/R11/R12）
- **R07 `codol/net` 核心**（crypto/association/handshake/ecdh/netchan/wire/network）：合成加密对等体已跑通
  handshake→CS_PRIMED 并收到重组 gamestate（`docs/CODOL_ASSOCIATION.md`）。移植前**必须先解决冲突 A（AES192/Tiger192 vs AES128/SHA1）与 B（COOKIE_ECHO 189 vs 219）**。
- **R11 net 辅助**（usercmd_queue/pure/msg/client_command/atomic_file）：服务端 clc 分发器 CONFIRMED；
  客户端 clc 生产端未确认（缺口 F）。
- **R12 `codol/snapshot`（76 文件）**：**核心阻塞**——`SV_WriteSnapshotToClient` 仍用 IW3 序列化器（PORT §4），
  6519 configstrings（武器从 5362 起）语义未接通。

### 2.2 引擎与资产（R01/R03/R06/R17/R18/R22）
- **R01 主程序**：架构骨架完整、可跑 bots，但面向真实 C1 可玩性 REFUTED（作者自述）。
- **R03 插件**：依赖 R01 的 185 `Plugin_*` 导出 ABI；部分插件涉及审查/反作弊，复用需合规评估。
- **R06 引擎底座**：AGPL3 传染性许可，需整体评估。
- **R17 assets / R18 collision / R22 GSC 脚本树**：接口清晰但版本锁定 1.1.1.13。

### 2.3 大厅业务（R29/R30/R31/R32/R34/R35/R36/R42）
- store/career/catalogue/notices/ffwriter 均为**数据驱动**（progression_tables.json、marketplace_catalogue.json 等），
  迁移时主要成本在**数据表对齐**而非代码重写。
- **R42 tools**：编排逻辑可移植，但**本轮不执行**任何样本 .cmd/服务。

---

## 3. 仅供参考（C 类，12 项）

判定标准：逻辑清晰但版本差异显著，或用于**理解未知**而非直接使用。

- **R13 `codol/player`（87 文件）**、**R14 `codol/weapon`（64 文件）**、**R15 `codol/vehicle`（48）**、
  **R16 `codol/script`（150）**：锁定 1.1.1.13 的 pmove 布局与武器 wire ID 1024（引擎仅 128 槽）。
  可解释战斗生命周期、武器数据模型、载具物理、GSC 内置桥；**若现客户端同版本可升级为 B**，否则仅参考。
- **R21 dedicated/docs（280+）**：知识与证据参考，但含**作者自述 vs 实测日志的冲突**（见 §6）。
- **R23/R24/R25/R26/R37/R38/R39/R43**：日志、存档、动画树、B3 状态、真人档案、流量捕获、文档、启动脚本——
  均为理解/离线复算来源。

---

## 4. 暂不可用（D 类，2 项）

判定标准：缺失关键依赖 / 需外部不可用服务 / 专有格式无法识别；**须给合理本地替代**。

| id | 资产 | 障碍 | 本地替代 |
|---|---|---|---|
| R05 | `Kernel33.dll` + `patcher/*` | 依赖**打包的** 1.1.1.13 客户端与 C1.exe；令 TenProtect 不执行属**反保护绕过**，超出任务约束 | 使用已解包/自研启动器，不做保护绕过 |
| R45 | `build/`（pyenv/pyinstaller） | 体积大（332 MiB）、平台绑定、可重建 | 本地自建等价 Python 环境 |

---

## 5. 已排除（E 类，6 项）

判定标准：证据足以排除复用价值。

| id | 资产 | 排除理由 |
|---|---|---|
| R02 | `codol_dedrun_next.exe` | 与 R01 **逐字节相同**（同 SHA-256） |
| R04 | `pexports.exe` | 第三方导出转储工具，非游戏组件 |
| R44 | `resource/icon.*` | 图标，与战斗复原无关 |
| R46 | `_clone_backup_*/_purge_backup_*` | 历史副本，与主树重复 |
| R47 | `dedicated/.git` | 无有效提交（BUILD_NUMBER=0） |
| R48 | `*.o` / `*.pyc` / `__pycache__` | 可由源码重建的编译中间产物 |

---

## 6. 必须保留的冲突证据（不强行统一）

1. **可玩性冲突**：`dedicated/README.md` 与 `docs/CODOL_PORT.md:3537`「Required before a client can play」6 项未完成 →
   自称 **incomplete port, not playable**；但 `docs/CODOL_IMPLEMENTATION_PASS.md` / `CODOL_MP_TRIAGE_20260929.md:13`
   记录 2026-09 真人 C1 进入 Killhouse 游玩。**本快照 qconsole.log 全部 184 条 status 均 `humans=0`（仅 12 bots）**。
   正确表述：**docs 声称 9 月真人测试通过基线；本快照自身运行日志未证实真人 C1 可连入当前打包 build**。
2. **密码学原语冲突 A**：native AES192/Tiger192（`codol_crypto.c`）vs C# AES128/SHA1。
3. **COOKIE_ECHO 长度冲突 B**：native 189B vs C# 219B。
4. **协议号冲突 C**：内部 codec 187 vs connectResponse protocol 1（设计分离，非 bug）。
5. **svc 值冲突 D**：CODOL wire 1/5 vs 非 CODOL 4/7（须用 1/5）。

---

## 7. 覆盖率与未审计边界

- **已审计**：顶层结构、12 个真实服务端 PE、`codol/*` 9 区域目录级清单、协议核心源码、lobby 8 包、状态/契约文件、patcher 文档。
- **未逐行审计**：`codol/script`(150)、`codol/player`(87)、`codol/snapshot`(76)、`codol/weapon`(64)、`codol/vehicle`(48) 的**函数级**语义（本轮为目录级 + 代表文件）。
- **受阻**：真实 C1 互操作、gamestate/snapshot 序列化收敛——**需运行验证，本轮只登记需求**（见 06 最小验证计划）。
- **未观察 ≠ 不存在**：`getstatus`/`svc_download` 等分支存在但客户端未观测发送。
"""
with io.open(os.path.join(OUT,"EARLY_SERVER_04_COMPATIBILITY_REPORT.md"),"w",encoding="utf-8",newline="") as f:
    f.write(md)
print("written", len(md))
