# XVAL01_OPEN_SOURCE_TRANSFERABILITY — 开源实现可迁移性审计

> 任务书 §五.F 要求对 OLD/1113、2697、CoD4x、IW4x、ol-mod **逐项**标注：可直接复用 / 需适配 / 已知不兼容 / 未验证假设 / 不能仅凭源码相似性推出的结论。
> 纪律：**相似度只能作线索，不能单独证明协议兼容**；所有引用绑定仓库、提交与文件。
> 地址/文件来源：本地副本 git HEAD 经本任务活体确认（见 `_data\INDEPENDENT_VERIFICATION_LOG.md` V-06）。

---

## 0. 参照物清单（提交已固定）

| 代号 | 本地路径 | 类型 | HEAD / 版本 | 许可 |
|---|---|---|---|---|
| OLD | `...\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\` | 服务端源码 + 二进制 | `codol_dedrun.exe` = `28366ae9…` | 源码 SPDX `AGPL-3.0-or-later` |
| 1113 | `...\CODOL.NET\Game\CODOL_1.1.1.13\CODOL_Server\` | 服务端源码（+二进制） | `codol_dedrun.exe` = `a96c5dfb…` | 同上 |
| 2697 | `...\server2697\native\bin2697\codol_dedrun.exe` | 服务端**仅二进制** | `80816711…` | 专有 |
| CoD4x | `DEV-BOOKING\_lineage021\CoD4x_Server` | AGPL 服务端源码 | git `ddd65fce1a1093017bad2dbb6840d75d11c0d56f` | AGPL-3.0 |
| IW4x | `DEV-BOOKING\_lineage021\iw4x-client` | 客户端源码（无服务端） | git `d1b175da1a25d31043246de103a702b206269e5a` | 见仓库 |
| ol-mod | `_e1_regression\ol-mod-olfinal` | CODOL 链路重建（注入式） | git `2a75bdd8872bb9f54006382a924c3006ec9affc2` | 见仓库 |

> **注意：** 本任务未取 CoD4x 提交历史/线上 HEAD，引用一律以本地 `ddd65fce` 为准。

---

## 1. 可直接复用（REUSE）

| 组件 | 来源（文件/函数） | 依据 | 使用限制 |
|---|---|---|---|
| Quake3/CoD 引擎骨架（初始化、主循环 `Com_Frame→SV_Frame`、连接状态机 `CS_FREE→CONNECTED→PRIMED→ACTIVE`） | OLD `src\sys_main.c`、`common.c`、`sv_client.c`；CoD4x 同名 | Jaccard 93–99%（E-14 09） | 是**参照**，非可编译进 2697 的成品 |
| MSG 序列化原语（`MSG_WriteByte/Short/Long/Data/String/Bits`） | OLD `src\msg.c`；`codol_net\codol_netchan.c` 调用点 | 源码 + 2697 同名符号 | 语言无关逻辑可复用；**字段层须按 2697 重验** |
| Huffman 表与初始化 | CoD4x `huffman.c` | Jaccard 99.7%（E-14 09） | 直接复用；与 2697 一致 |
| cvar / cmd 子系统 | CoD4x `cvar.c` / `cmd.c` | Jaccard 97.9% / 97.6% | 直接复用 |
| 2697 运行时资源与脚本（`runtime-assets` 1.71 GB、`scripts` 1,341 文件） | 2697 发行包 | EV-S-2697 | 可直接作本地资产底座；**非协议逻辑**（R-20：scripts 无协议） |
| 大厅套件 REF_LOBBY_KIT | 第三方 | EV-Lobby-Third/Golden | 唯一有**实机进大厅**证据的组件 |

## 2. 需适配后复用（ADAPT）

| 组件 | 适配点 | 主要缺口 |
|---|---|---|
| CoD4x 服务端事件循环 / 槽位 / 超时 / 快照复制分离 | 结构模板 | CoD4x 战斗通道**无 cookie+ECDH**，不能照抄协议 |
| CoD4x `netchan.c`（`PACKET_HEADER 10`、`MAX_MSGLEN 0x20000`） | 须替换为 CODOL 常量（1162×128、掩码 0x1fffffff） | 见 §3（不兼容） |
| ol-mod 插件/注入框架 | 形态参考 | 目标 **3.3.3.3**，非 2.6.9.7 |
| 2697 注册门控配置路径（`_CODOL2697_ReadRegistration` 0xA3EA0、双门控 +0x78F4/+0x6408） | 机制已确认 | 5 字段业务语义与合法激活路径未闭合 |
| C# 战斗服 / Codec MVP（`CODOL-Combat-Server-v0.1`、`12_CODEC_MVP_001`） | 离线传输/密码原语/会话描述符 | 字段须与真实客户端对齐；向量为 CONSTRUCTED |

## 3. 已知不兼容（REFUTED 兼容假设）

| 项 | 证据 | 后果 |
|---|---|---|
| CODOL netchan ≠ CoD4x/IW4x netchan | 头 4/6B vs 10B；分片 6B{index,last,stride=1162,chunk} vs 4B start+2B len；上限 1162×128 vs 0x20000（C-003/C-031） | 不可直接移植 netchan 实现 |
| CODOL 客户端网络栈 ≠ IW4x/CoD4x | 客户端为**虚表分派**（`.rdata 0x898588/0x898590`）+ **内联 OpenSSL 0.9.8p/ libcurl 7.38.0**（E-14 §3、E-18） | 不可移植客户端网络栈 |
| CODOL 握手（cookie + P-224 ECDH）无开源对应 | CoD4x/IW4x 均仅 XOR/无 | 必须自研 |
| `0x6ABBC0` Demonware 类型码 1/2 ≠ 游戏 opcode 0x01..0x04 | E-19 | 不可把 Demonware 分帧当游戏协议 |
| IW4x 无专用服务器源码 | 仓库仅客户端 DLL | 不可作服务器方案 |
| ol-mod 不基于 IW4x，且目标是 3.3.3.3 | AUDIT.md（EV-R-OlMod-NoIW4x） | 不可迁移到 2.6.9.7 |

## 4. 尚未验证的假设（UNVERIFIED ASSUMPTIONS）

| 假设 | 现状 | 需要的验证 |
|---|---|---|
| 2697 二进制中的 CODOL netchan 常量 ↔ OLD 源码：**同源** | 常量精确匹配（R-17），但为符号级推断 | 已在 C-003/C-036 标 PROVEN（常量级）；**实现级**仍属推断 |
| OLD 源码行号 ↔ OLD 二进制函数：**可对应** | **无 PDB/MAP**（CONFLICT-08） | 需签名匹配或 MAP/PDB |
| ol-mod 自述"双客户端 Nuketown FFA 通过" | `.runtime/natural-match` 本地**不存在** | 需本机可复现证据 |
| C# Codec ↔ 2697 服务端 | 自测通过，但字段定义与 E1–E3 反汇编**同源** → **不独立** | 需真实字节或独立来源向量 |

## 5. 不能仅凭源码相似性推出的结论（禁止升级）

1. ❌ 由"CoD4x 有 `netchan_t` 且 CODOL 也有分片"推出"netchan 兼容"——**已证不兼容**。
2. ❌ 由"OLD 是 CoD4x fork"推出"2697 协议 = CoD4x 协议"——2697 叠加了独立 2697 层（新 opcode、门控、常量）。
3. ❌ 由"ol-mod 也实现 CODOL 链路"推出"ol-mod 可用于 2.6.9.7"——目标版本不同（3.3.3.3）。
4. ❌ 由"Jaccard 高"推出"函数行为逐位相同"——相似度只作线索（E-13/E-16 已记录同源代码实际行为不同的案例）。
5. ❌ 由"IW4x 有客户端网络代码"推出"可作服务器"——IW4x 无服务器源码。

## 6. 迁移性裁定矩阵（任务书 §五.F 汇总）

| 对象 | 可直接复用 | 需适配 | 不兼容 | 未验证 |
|---|---|---|---|---|
| OLD/1113 源码 | 引擎骨架、MSG/Huffman/cvar/cmd | CODOL 专有层（握手/crypto/netchan/2697） | 与 2697 客户端无直接对接 | 源码↔二进制对应 |
| 2697 二进制 | 常量、字段序、门控机制 | — | 无源码可编译 | 客户端侧全链路 |
| CoD4x | 引擎骨架、Huffman、cvar/cmd | netchan 常量层 | 战斗握手/加密 | 线上提交差异 |
| IW4x | 无（无服务器源码） | OOB/发现/认证信封参考 | 网络栈、TLS 缺失 | 双克隆差异 |
| ol-mod | 插件/注入框架 | — | 目标版本 3.3.3.3 | 双客户端实测复现 |

---

## 7. 结论

- **服务端引擎层**（骨架/序列化/Huffman/cvar/cmd）可安全复用 CoD4x/OLD 源码；**战斗通道层**（握手/加密/netchan）必须自研或从 2697 二进制重实现。
- **客户端网络栈**在任何开源实现中都**没有**可移植对应物。
- 所有高相似度映射都已在主张表中**绑定证据等级**，未升级为"兼容"。
- 许可：OLD/CoD4x 为 AGPL/GPL，复制源码进服务端须单独评估发布义务（任务书 §范围约束 + 11_CUSTOM_SERVER_FEASIBILITY §7）。
