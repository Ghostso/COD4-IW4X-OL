# AUDIT — OLMod 证据基线与原生兼容性审计（2026-10-09）

被审计仓库: F:\\桌面\\ol\\ol-mod-olfinal
分支: OLfinal-live
HEAD: 3915fa9813be7255d7031c307d31ad12043dfbd4（"Restore Factory teleporter links and staged return travel", 2026-10-02T09:41:50-05:00）
与上游关系: origin/OLfinal-live，**ahead 0 / behind 0**
备份: E:\\OLMOD_BACKUP_20261009_095356（821 文件逐文件 sha256 全等；git bundle 25,788,461 B）

本审计包内含:
- AUDIT.md（本文件）
- EVIDENCE_STATUS.md（证据矩阵与等级）
- NON_CODOL_SUBSTITUTIONS.md（非 CODOL 替代审计）
- GOLDEN_COPY_SPEC.md（不可变基线规范）
- MANIFEST.json / SHA256SUMS.txt

---

## 1. 第一阶段：保护现状（已完成，PASS）

| 项 | 结果 |
| --- | --- |
| 仓库路径 | F:\\桌面\\ol\\ol-mod-olfinal |
| 分支 / HEAD | OLfinal-live / 3915fa9813be7255d7031c307d31ad12043dfbd4 |
| git status --porcelain | 0 行（审计开始前干净） |
| stash | 0 |
| untracked | 0 |
| tracked 文件 | 627 |
| 工作树总文件（含隐藏） | 821（627 工作树 + 194 .git） |
| 破坏性操作 | **未执行**任何 reset / clean / checkout 覆盖 / 批量格式化 |
| 既有运行证据 / Golden Copy | 本机不存在（已确认），因此**无覆盖风险** |

### 独立备份与验证
- 路径: E:\\OLMOD_BACKUP_20261009_095356（放在独立卷 E:，非仓库所在 F:）
- 内容: repo\\（robocopy /MIR 镜像，含隐藏文件）、ol-mod-olfinal.bundle（git bundle --all）、HEAD.txt / BRANCH.txt / STATUS_PORCELAIN.txt、baseline\\BASELINE_SHA256.txt（821 条逐文件 sha256）
- 验证: 源 821 文件 vs 备份 821 文件，**only_in_source=0 / only_in_backup=0 / hash_mismatch=0 → BACKUP_HASH_VERIFIED_OK**
- 文件计数: SRC=821, BAK=821

=> 硬停止条件检查: 工作树状态明确，备份哈希验证通过 → **未触发停止**，可继续。

---

## 2. 第二阶段：证据审计（结论）

完整矩阵见 EVIDENCE_STATUS.md。核心结论:

### 2.1 主链 11 项全部为 NOT_OBSERVED + INSTRUMENTATION_BLOCKED
mmstart -> SessionStart -> CCS -> gamestate accepted -> world spawn -> snapshots 的每一环在**源码层面都有实现**（由本 HEAD 源码直接证实），但在本环境**没有任何可核验的运行证明**:
- 全盘扫描 1,125,752 个文件，OLMod 运行产物（netchan_trace.jsonl / server_samples.jsonl / summary.json / *.log 等）**0 命中**；
- 目录 .runtime / natural-match **0 命中**；
- 文档中仅有的两条具名 summary.json（20260731_233232、20260801_014234）不在磁盘上；
- 文档中的成功数字（1201 条快照 / ~19.97 Hz / accepted 1743 / rejected 0 / checksum 0xF7E89911）**全部不可复现**。

### 2.2 已确认的文档 REFUTED 项
| 编号 | 文档声明 | 源码实际 |
| --- | --- | --- |
| R1 | server frame 以 20 Hz 编排（game_server.md:318, :526） | sv_main_mp.cpp:1074 fallback = 100 ms（10 Hz） |
| R2 | slot 超时 connecting 80s / active 240s（game_server.md:496） | sv_client_mp.hpp:457-461 = 45s / 15s |
| R3 | playerState_s = 0x3564 | sv_native_playerstate_mp.hpp:17-23 = **0x3BBC**（本构建），0x3564 属 3.3.3.3 |
| R4 | entityState_s = 0x110 | sv_native_entitystate_mp.hpp:32-36 = 0x118 |
| R5 | playerstate descriptor 235 条 | 抽取为 246 条（ClientCommandTrace.hpp:45），冲突未解决 |

R1 精确说明: sv_client_mp.cpp:1424-1426 的快照节拍确实是 50 ms（20 Hz）且带显式 TODO(CODOL)，属 [SRC] 而非已恢复契约；文档把它表述为 server frame 的 20 Hz，与 100 ms 的 frame 默认冲突。二者是两个不同的率。

### 2.3 本环境可 CONFIRMED 的一手证据
- C1-C5: 仓库内**已提交的捕获字节 fixture**（CODOL DTLS DATA + HMAC + AES-CTR 解密、getchallenge 明文、NAT intro、首个 netchan 包、EOF=5 vs 3.3.3.3 的 6），位于 tests/game_server/ServerCoreTests.cpp:27314-27391 与 :27502-27555。
- C7-C11: 全盘无运行产物、41 份客户端无一匹配记录哈希、无 Golden Copy、无 PCAP 工具、构建工具链完全缺失。

**限定**: C1-C5 是协议一致性证据，不构成 gameplay 运行验证。

### 2.4 复现能力
- 编译/运行测试: **INSTRUMENTATION_BLOCKED**（无 xmake / MSVC / cmake / ninja / vcpkg / build 目录）
- 复核任何 CODOL RVA / parser 语义: **INSTRUMENTATION_BLOCKED**（无匹配客户端、无 out.exe 1649370）
- 复现主链: **INSTRUMENTATION_BLOCKED**（无有效游戏目录）

---

## 3. 第三阶段：非 CODOL 原生替代审计（结论）

详见 NON_CODOL_SUBSTITUTIONS.md。三项:

| # | 项 | 默认 | 关闭后果 | 处置建议 |
| --- | --- | --- | --- | --- |
| S1 | BO1 donor 导航图 | 关闭（opt-in，需 OLMOD_ZM_NAV_SOURCE=bo1_hybrid 且地图为 zm_factory_sh） | 无 | 不构成默认违规，无需改动 |
| S2 | Ghosts 玻璃伤害阈值 | **开启** | **世界加载整体失败**（nullopt -> reportFailure("glass_damage_thresholds")） | **不可直接删除**；须先取得 CODOL glass_map (type 17) 阈值或定义并测试替代语义 |
| S3 | IW4 destructible 血量序列/模型名 | **开启（限 7 类 CODOL 同名 type）** | 实体退化为普通布景（不崩） | 可安全降级，但需接受玩法功能损失 |

关键澄清: 三项都是**源码内嵌数据**，不是被复制的游戏资产；树内无任何非 CODOL 二进制资产。替换模型名仍须经 CODOL 自己的 CCS 解析，因此不会引入外部模型文件。

**本任务未修改任何默认行为，未删除任何实现。**

---

## 4. 第四阶段：证据归档规范（本包）

已建立（路径均为绝对路径，哈希见 SHA256SUMS.txt）:
- AUDIT.md
- EVIDENCE_STATUS.md
- NON_CODOL_SUBSTITUTIONS.md
- GOLDEN_COPY_SPEC.md
- MANIFEST.json
- SHA256SUMS.txt

Golden Copy 的创建条件、独立备份、哈希验证、启动环境记录与回滚步骤统一在 GOLDEN_COPY_SPEC.md 中定义。要点:
- 创建条件 G1-G6（已验证客户端哈希、clean launch、双方 active world、自然 parser 进 Playing、快照 ACK 且零 overflow、summary.json 标注证据等级）。
- 冻结内容: 源码/构建/客户端/游戏目录资产哈希、启动环境全集、运行产物全集、PCAP（当前**未实现**，须显式记录 NOT_CAPTURED）。
- 独立备份至少两份、跨卷、至少一份只读。
- 验证必须由“重新计算哈希 = 记录哈希”得出；**不得仅以文档写有 PASS 作为通过依据**。

---

## 5. Git 状态变化（本任务造成的唯一改动）

审计前: 干净（porcelain 0 行）。
审计后:
```
?? .agents/audits/
```
- 唯一变化是**新增未跟踪目录** .agents/audits/（本审计包）。
- **未修改任何既有文件**，未提交，未推送（origin 未触碰）。
- 如需撤销: 删除 .agents/audits/2026-10-09/ 即可回到审计前状态（备份与 manifest 另行保留）。

---

## 6. 已确认的问题（CONFIRMED）

1. 构建工具链完全缺失，7 个测试套件无法执行。
2. 本机不存在匹配的 CODOL 客户端（41 份副本仅 2 个构建，均不匹配 E3823FD6...）。
3. 配置的游戏目录 D:\\codo_3.19.26.13_fresh\\Co Online 不存在。
4. 全盘不存在任何 OLMod 运行产物；所有里程碑声明不可核验。
5. 仓库内无 Golden Copy / 不可变基线 / 运行清单。
6. 仓库内无任何 PCAP 工具。
7. 文档与源码存在系统性数值偏差（R1-R5），其中 R3/R4 是 ABI 尺寸，跨构建假定会直接导致内存布局错误。
8. Ghosts 玻璃阈值是硬依赖：移除会使世界加载失败。
9. S2/S3 两处非 CODOL 数据默认开启，与任务禁令冲突。

---

## 7. 尚未解决的阻塞项（UNRESOLVED）

| # | 阻塞 | 影响 | 解除条件 |
| --- | --- | --- | --- |
| B1 | 无编译器/构建工具链 | 无法验证任何测试或构建 | 安装 MSVC + xmake + vcpkg，或提供预构建产物 |
| B2 | 无匹配客户端（E3823FD6... / out.exe 1649370） | 无法复核任何 CODOL RVA/parser/字段 | 取得匹配构建 |
| B3 | 无有效游戏目录与 .ff 资产 | 无法复现主链、无法取 CODOL 原生玻璃/可破坏数据 | 取得完整 CODOL 3.3.3.3 安装 |
| B4 | 无 PCAP 采集流程 | 无法满足“PCAP/协议记录”交付 | 建立 pktmon 式采集并归档 |
| B5 | 无 Golden Copy | 无法把任何结论从 NOT_OBSERVED 提升为运行 CONFIRMED | 先解除 B1-B3，再按 GOLDEN_COPY_SPEC.md 冻结 |
| B6 | 真实 live 交接文档不在本机（CODOL-main / OLFINAL-FFA-HANDOFF.md） | 无法确认 OLfinal 分支的最新意图 | 提供该仓库 |

---

## 8. 下一步所需的最小条件

要达到“可核验的自然对局 + Golden Copy”，最小条件是**同时**具备:
1. SHA-256 = E3823FD6AFC80FB25FA84747E6E9634707B9A0B189357A5466921CDA354AF37B 的客户端（或 out.exe build 1649370）；
2. 一个包含完整 .ff 资产的 CODOL 游戏目录；
3. 可构建 ol_game_server 的工具链（MSVC + xmake + vcpkg x86-windows-static OpenSSL）。

三者缺一，任何“已打通”结论都只能是文档声明，不能升级为运行证据。

---

## 9. 审计纪律声明

- 未执行 reset / clean / checkout 覆盖 / 批量格式化。
- 未覆盖任何既有运行证据或 Golden Copy（本机不存在，已确认）。
- 未修改任何既有文件；本审计包为新增未跟踪文件。
- 未推送到 origin。
- 未调查已关闭的 WeGame / TCLS / IIPS / 启动器路线（仅记录其产物存在，未展开）。
- 证据等级严格区分 CONFIRMED / REFUTED / NOT_OBSERVED / INSTRUMENTATION_BLOCKED，未以文档 PASS 代替验证。
