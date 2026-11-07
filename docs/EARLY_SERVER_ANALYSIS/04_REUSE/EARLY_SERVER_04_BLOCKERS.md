# EARLY_SERVER_04 — 关键阻塞点与依赖缺口

> 阶段 4 交付物（第 3 件）。每条：现象 / 证据 / 影响 / 是否阻塞"进战斗" / 最小闭合路径。
> 证据标签沿用任务书术语。**未观察 ≠ 不存在。**

---

## 阻塞总览

| # | 阻塞 | 等级 | 阻塞进战斗 | 类型 |
|---|---|---|---|---|
| K1 | gamestate/configstrings/snapshot 序列化器未移植 | CANDIDATE | **是** | 代码缺口 |
| K2 | 密码学原语冲突（AES192/Tiger192 vs AES128/SHA1） | CONFLICT | 是（若一侧错） | 未统一证据 |
| K3 | COOKIE_ECHO 长度冲突（189 vs 219） | CONFLICT | 是 | 未统一证据 |
| K4 | 真实 C1 互操作从未在隔离环境跑通 | NOT_OBSERVED | 是 | 运行验证缺失 |
| K5 | 客户端 clc 生产端未确认 | STRONG_CANDIDATE | 否 | 静态证据缺口 |
| K6 | 武器 wire ID 1024 vs 引擎 128 槽 | CONFIRMED | 是（武器错位） | 数据映射 |
| K7 | 脚本编译错误（GSC） | CONFIRMED | 部分 | 资源/脚本 |
| K8 | 缺资产（defaultweapon_mp 等） | CONFIRMED | 是 | 资源缺口 |
| K9 | AGPL3 许可传染 | CONFIRMED | 否（法律） | 许可 |
| K10 | lobby 无认证 / 口令文件敏感 | CONFIRMED | 否 | 安全 |

---

## K1 — gamestate/configstrings/snapshot 序列化器未移植（**核心阻塞**）

- **现象**：服务端下行帧仍走 IW3 序列化器。
- **证据**：`dedicated/docs/CODOL_PORT.md:3537`「Required before a client can play」第 4 项；
  `dedicated/src/sv_snapshot.c:224 SV_WriteSnapshotToClient` / `:759 SV_SendClientSnapshot`。
  6519 configstrings，武器从 5362 起。
- **影响**：即使握手成功、推进到 CS_PRIMED，**下行世界帧不可被 CoDOL 客户端解析** → 无法进战斗。
- **最小闭合路径**：需真实 C1 或高保真回放（现有 `CodolClientReplay.cs`/`SessionGolden.cs` 可作离线对照）。
  **本轮不执行**，登记为验证需求。

---

## K2 — 密码学原语冲突 A

- **现象**：DATA 记录 keystream/MAC 原语两套实现。
- **证据**：native `codol_crypto.c:28-78`（Tiger192→key24，AES192-ECB，小端 CTR）；
  C# `CodolProtocol.cs:213-244`（AES128 + SHA1 计数器）。
- **影响**：若原生正确，C# 对真实 C1 会**全部 MAC 失败**——与 C# README「收包=0」症状一致（CANDIDATE）。
- **最小闭合路径**：对 `lobby/captures/*.jsonl` 做**离线** MAC 复算（先 AES192/Tiger192，再 AES128/SHA1）。
  **本轮不执行**。

---

## K3 — COOKIE_ECHO 长度冲突 B

- **现象**：189B（native 硬性 `n==189`）vs 219B（C# `KeyExchangeLength=219`）。
- **证据**：`codol_handshake.c:47/54`；`docs/CODOL_ASSOCIATION.md` 独立复算得 189B（自洽）；
  C# `CodolProtocol.cs:35`。
- **影响**：cookie 解析偏移不匹配 → association 无法建立。
- **最小闭合路径**：离线复算 `captures` 中 COOKIE_ECHO 真实长度；或静态反汇编 C1 `bdDTLSCookieEcho` serializer。

---

## K4 — 真实 C1 互操作未跑通

- **现象**：所有握手成功均来自**合成加密对等体**；本快照 qconsole 仅 bot 会话（184 条 status 全 `humans=0`）。
- **证据**：`docs/CODOL_ASSOCIATION.md`（合成对等体）；`dedicated/bin/home/main/qconsole.log`。
- **影响**：无法断言当前打包 build 能被真人 C1 连入。
- **最小闭合路径**：隔离环境 + 早期 C1 客户端 + 抓包（**需单独批准**）。

---

## K5 — 客户端 clc 生产端未确认

- **证据**：服务端 `sv_client.c:2505 MSG_ReadBits(...,3)` CONFIRMED；客户端发送侧未反汇编；
  lobby `protocol_map.md` B.2 实测 Python 参考服无 clc 分发器。
- **影响**：字段布局不确定 → 输入解析可能错位。
- **最小闭合路径**：静态反汇编 C1 的 `CL_SendCmd`/usercmd 序列化。

---

## K6 — 武器 wire ID 1024 vs 引擎 128 槽

- **证据**：`CODOL_PORT.md` 第 3 项；`codol/weapon/codol_weapon_state.c`（139KB）。
- **影响**：武器索引错位 → 装备/渲染错误。
- **最小闭合路径**：完成资产注册到显式武器映射表。

---

## K7 / K8 — 脚本编译错误与缺资产

- **K7**：`dedicated/bin/sys_error.txt`：`Sys_Error: script compile error bad syntax bar.x = -barWidth / 2;`（GSC 编译错误）。
- **K8**：`CODOL_MATCH_STARTUP.md`：`mp_killhouse_sh` 探针因 `defaultweapon_mp` 缺资产失败退出。
- **影响**：地图/模式无法完成初始化。
- **最小闭合路径**：修复脚本语法；补 `missingasset.csv` 所列资产。

---

## K9 — 许可

- **证据**：`dedicated/README.md`：CoD4x fork，**AGPL3**（`License.md`/`copying.md`）。
- **影响**：直接复用引擎底座将引入 AGPL3 传染义务；现有 C# 战斗服（`docs/LICENSE_POLICY_REUSE.md` 声明未复制 CoD4x/iw4x 源码）需评估。
- **最小闭合路径**：法律评估；或仅复用**契约层**（文本/文件格式，非源码）。

---

## K10 — 安全

- **证据**：`lobby/README.md`「The lobby has no authentication」；`native_server_rcon.txt`（口令，**本报告不输出**）。
- **影响**：端口暴露即任意账号冒用。
- **最小闭合路径**：仅绑 127.0.0.1（`docker-compose.yml` 已如此）。

---

## 缺失依赖清单（NOT_OBSERVED / UNKNOWN）

- 真实 C1 客户端的**隔离运行环境**（本轮未搭建）。
- 完整 `.ff` 区文件与 `client_shipRetail\chinese` 安装路径（`lobby/paths.py` 依赖，样本内未含游戏安装）。
- 运行验证工具链（XAC/TenProtect 相关**不做**分析）。

> 本文件只登记阻塞与闭合路径，**不执行**任何运行实验或补丁。
