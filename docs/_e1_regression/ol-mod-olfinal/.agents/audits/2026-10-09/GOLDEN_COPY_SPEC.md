# GOLDEN_COPY_SPEC — 不可变 Golden Copy 规范（2026-10-09）

本规范定义 OLMod 首个“进入战斗地图”成功版本的冻结流程。
它是本任务要求的核心交付之一，因为当前仓库**不存在任何 Golden Copy / 不可变基线 / 运行清单**（见 EVIDENCE_STATUS.md §5 C9）。

---

## 0. 背景与问题

仓库现有的哈希机制都不是里程碑基线:

| 现有机制 | 位置 | 范围 | 为什么不够 |
| --- | --- | --- | --- |
| 分发/安装 manifest | tools/distribution/StageCodolRuntime.ps1:64-77,154-164 -> build/stage/codol/ol-mod-runtime-manifest.json | 每文件 path/size/sha256/source/kind/role/installPolicy | 是**分发**清单，不是某次成功运行的冻结；build/ 当前不存在 |
| 遗留组件哈希 | distribution/runtime-components.json | 4 个归档组件 + 资产目录哈希 | 只覆盖分发输入 |
| 单轮输入冻结 | tools/runtime/CodolNaturalMatchTrace.py:435-442 | input_scenario.snapshot.json + sha256 | 只冻结**输入**，不冻结结果与二进制的整体 |
| 单轮采样完整性 | tools/runtime/CodolCaptureEvidence.py | raw sample 逐段 sha256 | 只校验采样容器完整性 |

同时，运行时目录 .runtime/ 被 .gitignore 忽略（.gitignore:4），且在本机全盘不存在，导致所有历史成功声明永久不可核验。

=> 目标: 建立**一次成功、永久冻结、可机械验证**的 Golden Copy，使“某次自然对局真的跑通了”成为一个可复核的事实而不是文档断言。

---

## 1. 创建条件（必须在同一运行中同时满足）

Golden Copy 只能在满足以下**全部**条件时创建，缺一不可:

- G1. 客户端为记录在案的已验证构建: 客户端 EXE SHA-256 == E3823FD6AFC80FB25FA84747E6E9634707B9A0B189357A5466921CDA354AF37B（或明确记录为另一构建并同时记录该构建哈希）。
- G2. 运行来自干净进程启动（clean launch），不是复用已在局内的进程。
- G3. dedicated 与客户端双方都达到 active world: server slot state=3 且 gameplay=1。
- G4. 客户端真实 parser 完成 gamestate 且进入 Playing，**不是**由 Frida 强制或合成快照造成。
- G5. 至少发送并 ACK 一份 initial full snapshot 与若干 delta snapshot，且 parser overflow_events == 0、无 Com_Error。
- G6. 生成该运行的 summary.json，且其 evidence_level 字段明确标注自然/强制范围。

**禁止**: 用 client-native-forced / frida-forced / synthetic protocol client 的结果创建 Golden Copy 并称之为“自然对局”。强制运行只能作为附带证据单独保存。

---

## 2. 冻结内容（逐文件 SHA-256）

建议目录: <artifact-root>/GOLDEN-BATTLE-001/（编号递增，绝不复用）

### 2.1 代码与产物
- VCS_COMMIT.txt: git rev-parse HEAD + git status --porcelain 的完整输出（含脏状态）+ 分支名。
- SOURCE_SHA256.txt: git ls-files 全量逐文件 sha256（与本次 Phase 1 的 BASELINE_SHA256.txt 同格式）。
- BUILD_ARTIFACTS.json: 每个部署 DLL 的路径/大小/sha256（Localnetworking.Ayria32、Platformwrapper.Ayria32、Alwaysoffline.Localnet32、CodolGameServer.Localnet32、ol_room_owner.exe）。
- CLIENT_BINARY.json: 客户端 EXE 路径/大小/sha256，以及 out.exe（若使用 OLfinal 路径）的 sha256。

### 2.2 运行环境
- LAUNCH_ENV.json: 每个进程的 OLMOD_* 环境变量全集（OLMOD_PROCESS_ROLE / SV_FRAME_MS / DEDICATED_CONTROL_PORT / CLIENT_BRIDGE_PORT / ROOM_OWNER_PORT / ZM_NAV_SOURCE / GLASS_DAMAGE_TO_* / ALLOW_UNSIGNED_FASTFILES 等）+ 启动命令行 + 启动时间 + PID。
- GAME_DIR.json: 游戏目录绝对路径、资产清单（.ff 列表及逐个 sha256）、config/codol-game-dir.txt 内容。
- HOST.json: OS 版本、CPU、内存、网络接口（本地回环/LAN 判定，因为 LAN peer 会旁路快照节拍，见 §5 风险）。

### 2.3 运行结果（来自 CodolNaturalMatchTrace 的既有产物名）
- summary.json（含 schema_version / outcome / current_phase / evidence_level）
- netchan_trace.jsonl
- server_samples.jsonl
- frame_trace.jsonl + frame_trace.summary.json
- dedicated_asset_trace.jsonl
- cbuf_commands.jsonl
- viewmodel_trace.json
- input_scenario.snapshot.json（输入冻结）
- 日志: CodolGameServer.log、AlwaysofflineRe.Localnet32.log、Logs/Localnetworking.log、Ayria/Logs/ol-mod-processes.json
- 截图: 至少 1 张进入战斗地图后的世界渲染，含时间戳。

### 2.4 协议记录（PCAP）
- 现状: 仓库内**无任何 PCAP 工具**（grep 0 命中），因此该项目前为**未实现**。
- 要求: 冻结前必须建立采集流程。格式建议参考本机已有的 Windows 自带 pktmon（旧项目曾产出 pktmon.pcapng，1.6-115 MB）；采集需限定在 dedicated UDP 端口与客户端之间，并同轮记录端口号。
- 若本轮确实无法采集，必须在 MANIFEST.json 中显式写 pcap: NOT_CAPTURED 并说明原因，**不得留空或省略该项**。

---

## 3. 独立备份要求

- Golden Copy 必须至少有**两份**独立副本，且位于不同卷（例如 E: 与另一物理卷）。
- 至少一份为**只读**（Windows: attrib +R 或 ACL 只读），并在冻结报告中记录该设置的实际状态。
- 备份必须包含 §2 全部内容；备份后重新计算全部 sha256 并与源逐项比对。
- 本次 Phase 1 已建立可用模板: E:\\OLMOD_BACKUP_20261009_095356（821 文件，逐文件 sha256 全等，git bundle 25,788,461 B）。Golden Copy 的备份应沿用同一验证流程。

---

## 4. 哈希验证流程（机械可复核）

1. 冻结写盘后，生成 SHA256SUMS.txt: 每行 "<sha256>  <相对路径>"，路径排序稳定。
2. 生成 MANIFEST.json，包含: goldenId、createdAt、git HEAD、客户端 EXE sha256、G1-G6 逐项通过证据的引用、以及每个文件的 {path,size,sha256}。
3. 验证命令（任何人可独立执行）:
   - 重新计算全部 sha256，与 SHA256SUMS.txt 逐行比对，要求 0 差异。
   - 重新核对 git HEAD 与客户端 EXE sha256 是否等于 MANIFEST 记录值。
4. **禁止**以“文档里写了 PASS”作为通过依据；通过必须由“重新计算哈希 = 记录哈希”得出。

---

## 5. 已知风险（冻结时必须一并记录）

- 快照节拍: sv_client_mp.cpp:1418-1421 对 **LAN/loopback peer 直接旁路** rate delay，只有非 LAN peer 才加 50 ms（sv_client_mp.cpp:1424-1426，带 TODO(CODOL)）。因此本地测试观察到的 snapshot 频率**不能**直接当作 CODOL 远程客户端速率契约的证据。HOST.json 必须记录 peer 被判为 LAN 还是 remote。
- 帧率: sv_main_mp.cpp:1074 默认 100 ms（10 Hz），与 game_server.md:318/:526 声称的 20 Hz server frame 不一致（见 EVIDENCE_STATUS.md R1）。冻结时必须记录实际 OLMOD_SV_FRAME_MS 值。
- 非 CODOL 替代默认状态: 玻璃阈值默认开启（Appmain.cpp:1394-1430），可破坏物 IW4 数据默认开启（sv_destructible_mp.cpp:11-19）。冻结必须记录这些默认是否生效、对应环境变量是否设置，否则“CODOL 原生”声明不成立。
- 证据缺失的仓库约定: .runtime/ 被 .gitignore 忽略。Golden Copy **不得**只放在 .runtime 下，否则会再次丢失。

---

## 6. 回滚步骤

Golden Copy 本身不应被回滚（它是只读事实）。回滚针对的是“产生它的工作树状态”:

1. 停止所有相关进程（tools/runtime/CodolGame.py stop；stop 未生效则按 PID 终止，PID 见 Ayria/Logs/ol-mod-processes.json）。
2. 若需恢复到审计前状态: 在 F:\\桌面\\ol\\ol-mod-olfinal 执行 git checkout -- . 前先确认 git status 只含本次新增的 .agents/audits/ 与（若已提交）Golden Copy 相关提交；不要对未知脏状态执行 checkout。
3. 恢复备份: 从 E:\\OLMOD_BACKUP_<stamp>\\repo 使用 robocopy /MIR 回写，或 git bundle 恢复全部 refs。
4. 回滚后必须重新执行 §4 的哈希比对，确认等于 BASELINE_SHA256.txt。
5. 记录回滚前后的 git status 与哈希对照。

---

## 7. 与证据等级的关系

Golden Copy 一旦建立，可把对应结论从 NOT_OBSERVED 提升为 CONFIRMED（运行时验证），但**仅限被冻结运行实际覆盖的范围**。不得外推到未在该运行中出现的模式、地图、武器或玩家数量。
