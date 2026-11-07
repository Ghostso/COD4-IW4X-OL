# XVAL01_INVENTORY — 本地网络资料盘点与来源分类

> 任务：`XVAL-01_LOCAL_NETWORK_EVIDENCE_CROSS_VALIDATION`
> 生成日期：2026-10-12（Asia/Shanghai）
> 性质：**只读档案盘点 + 交叉验证**。未运行目标客户端/服务端，未注入，未读进程内存，未抓包，未修改任何冻结样本或历史报告。
> 本文件回答任务书第一阶段（§三）与第二阶段前提（§四）：**我们本地到底有哪些资料、它们各自属于哪一类证据。**

---

## 0. 盘点方法与口径

1. **先枚举、后判断**：本任务不假定任何资料存在。目录树经 `Get-ChildItem -Recurse` 全量枚举（工作区根 `D:\BaiduNetdiskDownload\使命召唤OL`，样本兄弟目录 `D:\BaiduNetdiskDownload`）。
2. 规模：工作区 253,014 文件 / ≈362 GB；其中网络相关主体不在"工具/"（20 万文件，主要为逆向工具链/依赖）而集中在 **E 系列证据包 + 知识档案 + 原始样本 + 运行时证据目录**。
3. **证据分层**（贯穿全部交付物）：
   - `PRIMARY-BINARY` — 原始可执行/恢复镜像（可复算，直接证据）。
   - `PRIMARY-SOURCE` — 随服务器分发的原始 C 源码（可复算，直接证据）。
   - `SECONDARY-ANALYSIS` — 由本项目产出的反汇编/交叉报告（**二次整理**；本身不是证据，须回溯其引用的原始字节/指令）。
   - `RUNTIME-EVIDENCE` — 实机运行/抓包记录（第一手运行证据；须区分平台层与游戏层）。
   - `OPEN-SOURCE-REF` — 外部开源仓库本地副本（参照物，不是 CODOL 证据）。
   - `MODEL-GENERATED` — 由 AI/脚本自动生成的叙述性结论（最低可信层，须逐条回溯）。
4. 完整可追溯清单（路径 / 体积 / **活体 SHA-256** / 版本 / 引用位置）见 `XVAL01_SOURCE_PROVENANCE.csv`（本任务重新计算，非转录）。

---

## 1. 顶部结论：资料盘点发现的五件事

| # | 发现 | 意义 |
|---|---|---|
| I1 | 三类**原始证据**齐备：2.6.9.7 客户端（打包+恢复镜像）、2697 服务端、OLD/1113 服务端**含可编译源码** | 交叉验证有真实锚点，不是纯二手叙述 |
| I2 | 最强的**一手运行证据在"大厅/平台层"**（GOLDEN-LOBBY-001 实机；`_combat_next011` 44 帧 HMAC 校验通过），**不在游戏战斗层** | 直接决定"哪些结论已证、哪些不能证" |
| I3 | 客户端恢复镜像存在**结构性缺口**（`.data` 缺 99.86%、末节 `.tp3` 未恢复、`.tvm0` 未解码） | 所有"客户端分派未找到"都是**弱否定**，不能升格为"客户端不支持" |
| I4 | 服务端侧已由**指令级**证据跨到源码级（2697 常量 ↔ OLD 源码常量精确匹配） | 服务端 writer 规格可信度高 |
| I5 | 存在一条**被多份资料混称**的证据：平台/预订层（service 21/5 等）常被当作"游戏协议" | 必须硬性分层，否则会把平台证据误当战斗证据 |

---

## 2. 原始二进制样本（PRIMARY-BINARY）

| ID | 样本 | 体积(B) | SHA-256（本任务实测） | 版本/身份 |
|---|---|---|---|---|
| BIN-C-2697 | 2.6.9.7 客户端（打包） | 9,964,656 | `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1` | 目标客户端，TenProtect 包装 |
| BIN-C-2697-REC | aplib 静态恢复镜像 | 12,571,648 | `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4` | `.text` 与打包客户端逐字节一致（E-06）；**非运行时 dump** |
| BIN-S-2697 | 2697 原生服务端 | 7,295,919 | `80816711946a5392abab81a625a516f24fb4d649e9b8008fc5a4e506be750ea1` | 唯一含 2697 协议层的服务端，**无源码** |
| BIN-C-1113 | 1.1.1.13 客户端 | 20,918,752 | `904436480938632a856b39dea73fb94c9682b5a0ebf7fa619ecd5dd5475ed3b6` | 旧通道客户端 |
| BIN-S-1113 | 1113 服务端 | 8,622,389 | `a96c5dfb5386f166a0e1d4262b8fdecf9835b856cf1a863f891ead4eda5cb6e9` | 与 OLD 同源 |
| BIN-S-OLD | OLD 服务端 | 8,469,493 | `28366ae992310bfe41d3c8975ec8dbc36e4de202ce438c1266e1a09e335dd98a` | CoD4x fork（IW4OL） |
| BIN-C-3333 | 3.3.3.3 QA 客户端 | 7,841,344 | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` | ol-mod 目标 |

**核对结论：** 上述 7 个哈希与 `14_SERVER_KNOWLEDGE_ATLAS_001\00_SAMPLE_MATRIX.md` / `E14\01` 登记值**逐一吻合**（本任务独立重算）。注意工作区另存有 40+ 份**同名的 7,841,344 B 客户端副本**（`工具\EX*`、`run_codol_001\sandbox*` 等），全部为 `36997674…`（3.3.3.3），**不是** 2.6.9.7；引用时必须按 SHA-256 而非文件名判身份。

---

## 3. 原始源码（PRIMARY-SOURCE，仅 OLD/1113 具备）

位置：`CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\dedicated\src\codol\net\`

| 文件 | 体积 | 承载的协议主题 | 活体 SHA-256（前 16） |
|---|---|---|---|
| `codol_wire.h` | 2,079 | netchan 常量、XOR、分片 struct | `771ef00f3d807339…` |
| `codol_netchan.c` | 4,767 | CODOL_NetchanProcess/分片 | `d97fef845a3d9d71…` |
| `codol_network.c` | 24,170 | CODOL_NetworkReceive、NAT/INIT/COOKIE/DATA | `feb5bd4a0e78cd31…` |
| `codol_handshake.c` | 3,199 | 握手（COOKIE_ECHO 189B 侧） | `f9be49f76c6d1a66…` |
| `codol_crypto.c` | 4,662 | 记录层加解密 | `caad3e3ce1a8f681…` |
| `codol_ecdh.c` | 3,751 | P-224 ECDH | `b3a0d1b26b09c78f…` |
| `codol_connect.c` | 3,564 | connectResponse 协议串 | `4e0de96c02584aa6…` |

**关键限制（勿混同）：**
- 该源码是 **OLD/1113（目标 1.1.1.13）** 的源码，**不是** 2697 源码。2697 的协议层只能反汇编。
- 依据 `REVISION_LOG` REV-017 / `E08\06`：本档案中**至少三次**发生过把 Capstone 的 **VA** 当作 **RVA** 查区段表的误读，导致伪结论。源码行号结论与二进制 RVA 结论**必须分开标注**。

---

## 4. 二次分析证据包（SECONDARY-ANALYSIS）

### 4.1 总知识档案
| ID | 目录 | 规模 | 定位 |
|---|---|---|---|
| SYN-ATLAS | `14_SERVER_KNOWLEDGE_ATLAS_001` | 67 文件 | 服务端全景 + 跨项目/跨版本/跨协议交叉验证（含 10/11/14/15/17/18/20/21 号专章） |
| SYN-2697SA | `CODOL_2697_SERVER_STATIC_ANALYSIS_20261011` | 231 文件 | 2697 服务端静态分析（含 07 双向 trace、08 客户端分派 trace、09 恢复边界） |

### 4.2 逐命题客户端/服务端逆向系列（E 系列）
| ID | 目录 | 主题 | 本轮状态 |
|---|---|---|---|
| EV-E06 | `E06_TVM0_STATIC_DECODE_001` | `.tvm0`→aplib；调用图完备性；`0xA2E50` 不可达 | 基础方法学 |
| EV-E08 | `E08_CONFIGSTRING_BODY_001` | configstring body 字段 | **部分被 E-09/E-14 更正** |
| EV-E09 | `E09_CONFIGSTRING_BLOCKERS_001` | 客户端 consumer `0xA2660`、count1 宽度 | **关键**：body 层两侧一致性 |
| EV-E10 | `E10_CONFIGSTRING_DISPATCH_001` | 外层/子帧分派器初探 | 层级归属被 E-11 更正 |
| EV-E11 | `E11_GAMESTATE_SUBFRAME_001` | 顶层 `0x350170`、子帧 `0x354100` | 分派器定位 |
| EV-E12 | `E12_REALTIME_GAMESTATE_CONSUMER_001` | 环形缓冲、demo 归属 | `0x350170`=demo（强推断） |
| EV-E13 | `E13_RECV_RINGBUFFER_TRACE_001` | 收包→环形缓冲 | **REFUTED**（限定范围） |
| EV-E14 | `E14_CROSS_PROJECT_PROTOCOL_AND_NETWORK_001` | 开源对照 + A2 位宽裁定 | **关键**：A2=11b |
| EV-E15 | `E15_TLS_PLAINTEXT_TO_APPLICATION_001` | TLS/明文 | TLS=更新模块；明文链 REFUTED |
| EV-E16 | `E16_SOCKET_EVENT_GAME_SESSION_ATTRIBUTION_001` | socket 事件归属 | `0x1B0430`=ICMP、`0x78772D`=工具 |
| EV-E17 | `E17_RECV_ENTRYPOINT_ATTRIBUTION_001` | recv 入口归属 | Q 库分母 122 |
| EV-E18 | `E18_SOCKET_VTABLE_CONSTRUCTOR_AND_INDIRECT_DISPATCH_001` | libcurl vtable 身份 | Q 库分母 142 |
| EV-E19 | `E19_DEMONWARE_SESSION_OBJECT_DATAFLOW_001` | Demonware 会话状态机 | **0x6ABBC0 分帧器 PROVEN**；游戏绑定 BLOCKED |

### 4.3 其它二次产物
- `EARLY_SERVER_ANALYSIS\`（含 `03_PROTOCOL`、`09_CLIENT_CONSUMER_001`；另有 `11..16` 原生 tap 设计与工具链系列）
- `11_CUSTOM_SERVER_FEASIBILITY_001`、`12_CODEC_MVP_001`、`CODOL-Combat-Server-v0.1`、`OfflineServer`
- `CODOL_OLMOD_AUDIT_20261009_094312\AUDIT.md`（ol-mod 血统审计）
- `REVERSE_ENGINEERING_COMPLETE.md`（387 KB）、`DEV-REVIEW\MASTER-POST-LOBBY-FULL-HISTORY-001.md`（150 KB）等长文报告
- 工作区根目录遗留的**中英混排叙述报告**（`T1_*`、`T2_*`、`ICH0xx_*`、`RESTORE*`、`ex0xx_*` 等）

> **二次分析纪律：** 上述报告是**结论的搬运工，不是证据**。本任务在 `XVAL01_PROTOCOL_CLAIM_MATRIX.csv` 中一律要求回溯到其引用的**原始字节/指令/RVA**，并对关键断言做了活体反汇编复核（见 `_data\INDEPENDENT_VERIFICATION_LOG.md`）。

---

## 5. 运行时/抓包证据（RUNTIME-EVIDENCE）

| ID | 位置 | 内容 | 层 | 关键性质 |
|---|---|---|---|---|
| RT-GOLDEN-LOBBY | `GOLDEN-LOBBY-001\REF_LOBBY_KIT` | 2026-10-05 首次进正式大厅 | 大厅 | **唯一第一手"进入大厅"实证** |
| RT-COMBAT-NET | `_combat_next011`（agent/verify 为独立复核副本） | 44 帧明文帧清单，含 header magic `ab85`、HMAC 校验、service/task=21/5、6/14 | **平台/预订** | `all_hmac_ok=true`；**`accepted_present=false`（无 accepted 推送）** |
| RT-DEV-BOOKING | `DEV-BOOKING\runtime_net_001` | 运行时网络记录 | 平台/预订 | 第三方案例 |
| RT-DEV-BOOKING-CH | `DEV-BOOKING\runtime_net_ch003` | 运行时网络记录 | 平台/预订 | — |
| RT-PLAINTEXT-FF | `_PLAINTEXT_PROJECT` | FF 资源 L1 AES-192-CTR 解密 | 资产（非会话） | 10/10 双 CRC；**与游戏会话无关** |

**必须保留的分层事实：**
- `_combat_next011` 的 service/task 值（21/5、6/14）与 `GOLDEN-LOBBY` 套装属**同一平台/预订协议域**（`_gist_tmp`、REF_LOBBY_KIT 的 21/5 与 6/14），**不是**游戏战斗 opcode（0x00..0x06）域。
- 任务书 §五.E 要求"后端服务通信与游戏实时消息路径必须分别判断"——本盘点确认：**项目全部可复现抓包都落在后端/平台域**。

---

## 6. 开源参考本地副本（OPEN-SOURCE-REF）

| ID | 仓库副本 | 本地 git HEAD（本任务实测） | 备注 |
|---|---|---|---|
| OSS-COD4X | `DEV-BOOKING\_lineage021\CoD4x_Server` | `ddd65fce1a1093017bad2dbb6840d75d11c0d56f` | 含源码；CODOL 之共同祖先 |
| OSS-IW4X-A | `DEV-BOOKING\_lineage021\iw4x-client` | `d1b175da1a25d31043246de103a702b206269e5a` | **仅客户端**，无专用服务器源码 |
| OSS-OLMOD | `_e1_regression\ol-mod-olfinal` | `2a75bdd8872bb9f54006382a924c3006ec9affc2` | 目标 3.3.3.3；自述不基于 IW4x |

**已知缺口：** IW4x 存在**第二个克隆**（`0699a7e5…`），两份差异清单未建立；`iw4x-rawfiles` 为空克隆。→ 引用"IW4x 的行为"必须带 HEAD。

---

## 7. 缺口与"未找到"清单（本任务新增，避免"假定存在"）

| 缺口 | 状态 | 影响 |
|---|---|---|
| 2.6.9.7 客户端**运行时解包 dump** | 全盘不存在 | 恢复镜像 ≡ 运行时映射**无法证明** |
| 2697 **战斗通道抓包** | 不存在 | 无字节级双向闭合 |
| 2697 客户端/服务端**任一实机互通**记录 | 不存在 | 互通=NOT-OBSERVED |
| OLD 源码 ↔ OLD 二进制**符号绑定**（PDB/MAP） | 不存在 | 源码行号与 RVA 结论不能互证 |
| IW4x 双克隆差异清单 | 未建立 | HEAD 歧义风险 |
| 2697 `runtime-assets`（11,033 文件 / 1.7 GB）逐文件解析 | 未做 | 可能含协议表，属未核验面 |
| `_combat*` 的原始**加密前/后字节与密钥** | 部分（见 L2 项目） | 是否可复算需另立预算 |

---

## 8. 与任务书"证据分层"要求的对应

| 任务书要求区分 | 本盘点对应集合 |
|---|---|
| 原始源码 | §3（仅 OLD/1113） |
| 原始二进制证据 | §2 |
| 人工笔记 | 散见于 `DEV-*`、根目录 `T*`/`ICH*` 报告（`SECONDARY-ANALYSIS` / 文字记录） |
| 二手资料 | §4.3、`DEV-BOOKING` 报告 |
| 历史推断 | E 系列中期结论（多已被 E-09..E-19 supersede，见 `XVAL01_CONFLICT_REGISTER.md`） |

> 下一步（主张表、交叉对照、冲突裁决、开源可迁移性、未决阻塞、问题库重算）分别见本目录其余 10 个交付物。
