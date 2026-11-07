# 历史语料未决问题审计 — 客户端启动 / 启动器 / IIPS / IFS / 地图资产 / 大厅基础设施

审计范围：根目录 `CODOL_EX0*`、`CODOL_STANDALONE_CORE_*`、`CODOL_EXE_*`、`ICH0*`、`RESTORE00*`、`RESTORE_LOCALRM_*`、`T1_*`、`T2_*`、`CODOL_FROZEN_CHAIN_RECOVERY_*`、`CODOL_FROM_ZERO_TO_LOBBY_*`、`CODOL_RUNTIME_BLOCKER_*`、`ARTIFACT_BLOCKERS`、`BASELINE_ADJUDICATION`、`BUILD-RISK-*`、`FILE_OWNERSHIP_MANIFEST`、`NETWORK_UNLOAD_LIFECYCLE_REVIEW`、`PROJECT_CORE_DOCTRINE`、`NEXT_PHASE_PLAN`、`TAKEOVER_STATUS_*`，以及 `11_*`/`12_*`/`14_*`/`分析`/`CODOLLauncher`/`WeGame`/`restore00*`/`restore_iips_contract_00*`/`XVAL-01_*`/`XVAL-02_*`/`STRIP_PROTECTION_001`/`CODOL_FIXED_CHAIN_LOCAL`/`CODOL_LOCAL_CHAIN`/`CODOL_LOCAL_ENGINE_CHAIN_20261019`/`CODOL_ISOLATED_SANDBOX_20261019`/`CODOL_NATIVE_BATTLE_CHAIN_20261019`/`_LEARN_TESTOL_DELIVERY(2)`/`CODOL_2697_SERVER_STATIC_ANALYSIS_20261011`/`CODOL_ANALYSIS_20261020`。

证据分级用语（全部沿用源报告自己的口径）：`PROVEN` = 有字节/指令/运行时直接证据；`CLAIMED` = 报告自述但未给可复现证据；`OFFLINE` = 离线自测通过（不等于客户端验证）；`SIMULATED` = 合成对等体/代理对象通过；`OFFICIAL` = 官方零售客户端实测。

已知基线（不重复登记）：`enable_iips=0` 导致 6 秒崩溃并已按 `enable_iips=1` 修复；固化链只能经 `run_codol_001/run_frozen_chain_once.py` 启动；`REF_LOBBY_KIT` 受保护不可改。

---

## 摘要表

| # | 标题 | 报告 | 状态 | 证据等级 |
|---|---|---|---|---|
| 1 | IIPS QoS 前置条件内容未知 | ICH017_IIPS_BOUNDARY_SYNTHESIS.md | OPEN | CLAIMED |
| 2 | IFS2.dll 运行时 0/6+ 次加载 | ICH016_IIPS_LOADER_CAUSALITY.md | OPEN | PROVEN(负面) |
| 3 | 调试器观测被反作弊阻断（双向死锁） | ICH015_PRE_STAGE1_DIVERGENCE.md | BLOCKED | PROVEN |
| 4 | 0x8189FEC 数值语义不可定 | ICH013_IIPS_INITIALIZATION_GATE.md | UNVERIFIED | PROVEN(零引用) |
| 5 | IFS 依赖"必要但不充分" | restore_iips_contract_001/…DECISION.md | OPEN | PROVEN |
| 6 | IIPS provider 契约卡在步骤1→2 之间 | restore_iips_contract_001/…DECISION.md | OPEN | PROVEN |
| 7 | SeCreateGlobalPrivilege 候选前置未验证 | restore_iips_contract_001/…DECISION.md | UNVERIFIED | CLAIMED |
| 8 | 0xFFFFFFFF 终止来源未知 | restore_iips_contract_001/…DECISION.md | OPEN | 未定 |
| 9 | `iipsinit` 身份被前轮误判 | ICH017_IIPS_BOUNDARY_SYNTHESIS.md | CONTRADICTORY | PROVEN(后者) |
| 10 | IIPS 成功路径从未运行时观测 | ICH014_IIPS_FOUR_STAGE_FAILURE.md | OPEN | PROVEN(负面) |
| 11 | Engine continuation gate 未定位 | ICH039_DECISION.md | BLOCKED | PROVEN(负面) |
| 12 | VM interpreter / ISA 未定位 | ICH041_DECISION.md | BLOCKED | PROVEN(负面) |
| 13 | .tvm0 解密 routine 未定位 | ICH058_DECISION.md | BLOCKED | CLAIMED |
| 14 | .tls scheduler 假设被证伪 | ICH059_DECISION.md | CONTRADICTORY | PROVEN |
| 15 | Anchor A/B 是 VM 常量池噪声 | ICH046_DECISION.md | CONTRADICTORY | PROVEN |
| 16 | 96 项表身份 = 复合/GFx 接口 | RESTORE003_DECISION.md | CONTRADICTORY | PROVEN |
| 17 | Resource→FF 桥接被自我证伪 | ICH051_DECISION.md | CONTRADICTORY | PROVEN |
| 18 | Slot 41 caller 为 VM 不透明 | ICH053_DECISION.md | BLOCKED | PROVEN(负面) |
| 19 | Root Object 运行时地址不可恢复 | ICH043_DECISION.md | BLOCKED | PROVEN(负面) |
| 20 | Engine 从不调用 RM / GetRM | RESTORE_ENGINE_BRIDGE_003_DECISION.md | CONTRADICTORY | PROVEN |
| 21 | ICH-027 的 IIPS→FF 契约被运行时否定 | ICH054_DECISION.md | CONTRADICTORY | PROVEN |
| 22 | Game Init / Frontend 入口不存在于明文 | ICH055_DECISION.md | OPEN | PROVEN(负面) |
| 23 | 有 FF 文件也未触发 FF 打开 | ICH034_BEFORE_AFTER.md | OPEN | PROVEN(负面) |
| 24 | "IIPS gate crossed" 结论被推翻 | ICH030_PROXY_VALIDATION.md | CONTRADICTORY | PROVEN(后者) |
| 25 | "ResourceManager ABI" 大部分虚构 | RESTORE_LOCALRM_006_DECISION.md | CONTRADICTORY | PROVEN |
| 26 | RM 语义仍 UNKNOWN | RESTORE_LOCALRM_006_DECISION.md | OPEN | PROVEN |
| 27 | Release 后单例悬空（原版即如此） | RESTORE_LOCALRM_006_DECISION.md | NOT_IMPLEMENTED | PROVEN |
| 28 | LocalRM_v3 导出目录错位 4 字节 | restore003/…DECISION.md | NOT_IMPLEMENTED | PROVEN |
| 29 | 0x480 vs 0x410 对象尺寸矛盾 | ICH028_LOCAL_COMPAT_SURFACE.md | CONTRADICTORY | PROVEN(后者) |
| 30 | Base+0x306A `ecx=3` 写入者未知 | CODOL_EX017_WRITER_RESULT.md | OPEN | PROVEN(负面) |
| 31 | Base bootstrap 退出契约未知 | CODOL_STANDALONE_CORE_010_BOOTSTRAP_CONTRACT.md | BLOCKED | PROVEN |
| 32 | CORE-013 无唯一静态目标 | CODOL_STANDALONE_CORE_013R_TARGET_RESOLUTION.md | BLOCKED | PROVEN |
| 33 | 观察者诱发行为分叉 | CODOL_EX028_OBSERVER_DIVERGENCE.md | OPEN | PROVEN |
| 34 | 调试附加权限不可得 | CODOL_EX058_RESULT.md | BLOCKED | PROVEN |
| 35 | argv 提供者槽 0xCA827C API 身份未证 | CODOL_EX032_ARGV_PROVIDER_SEMANTICS.md | UNVERIFIED | CLAIMED |
| 36 | `-q/-qa/-src=tgp` 语义未决 | CODOL_EX035_Q_QA_GATE_AND_BOOTSTRAP.md | UNVERIFIED | CLAIMED |
| 37 | 历史真实命令行从未找到 | CODOL_EX033_HISTORICAL_CLIENT_COMMANDLINE.md | BLOCKED | PROVEN(负面) |
| 38 | TCLS 共享内存/签名布局未知（写零缓冲） | CODOLLauncher/CODOL_LAUNCHER_V1.md | OPEN | CLAIMED |
| 39 | 谁创建 tcls_core.exe 未知 | CODOL_EX066_TCLS_PROTOCOL_CLOSURE.md | BLOCKED | PROVEN(负面) |
| 40 | TCLS payload PID / GameID 生成未知 | CODOL_EX067_TCLS_SHARED_MEMORY_LAYOUT.md | OPEN | PROVEN(负面) |
| 41 | TenProxy `Invoke(0x566)` 未解包调用点未知 | CODOL_EX068_NATIVE_TENPROXY_BRIDGE.md | OPEN | PROVEN(负面) |
| 42 | TCLS 状态值 0x63/0x18/0x11 语义未知 | CODOL_EX065_TCLS_UPSTREAM_BOUNDARY.md | OPEN | PROVEN(负面) |
| 43 | EXE 明文函数图仅部分 | CODOL_EXE_CORE_002_PLAIN_TEXT_FUNCTION_MAP.md | OPEN | PROVEN |
| 44 | Launcher 源码编译失败、BOOT_DEPTH 卡 2 | CODOLLauncher/logs/_run_fixed.txt | NOT_IMPLEMENTED | PROVEN |
| 45 | AlwaysofflineRe 拒绝"unknown executable image" | TAKEOVER_STATUS_20261019.md | OPEN | PROVEN |
| 46 | 宿主 SizeOfImage 门禁不符 | TAKEOVER_STATUS_20261019.md | OPEN | PROVEN |
| 47 | Dedicated 两难：IIPS 弹窗 vs 直接退出 | TAKEOVER_STATUS_20261019.md | OPEN | PROVEN |
| 48 | 历史本地链成功样本不可复现 | CODOL_LOCAL_ENGINE_CHAIN_20261019/HANDOFF…md | UNVERIFIED | CLAIMED |
| 49 | 转储工具入口基准错误 | CODOL_LOCAL_ENGINE_CHAIN_20261019/HANDOFF…md | NOT_IMPLEMENTED | PROVEN |
| 50 | 原生战斗链缺地图资产 | CODOL_NATIVE_BATTLE_CHAIN_20261019/logs/combat_server.log | OPEN | PROVEN |
| 51 | 原生战斗链 selftest 4 项失败 | CODOL_NATIVE_BATTLE_CHAIN_20261019/README.md | PARTIALLY_RESOLVED | PROVEN |
| 52 | NIFS 清单分隔符自相矛盾 | ICH033_NIFS_FORMAT.md / ICH034_BEFORE_AFTER.md | CONTRADICTORY | PROVEN(后者) |
| 53 | layer-2 世界资产从未导出 | CODOL_ANALYSIS_20261020/THIRD_ROUND_PREREQUISITES.md | OPEN | PROVEN |
| 54 | mp_firingrange clipmap 解析失败 | 记忆/ICH033–034 与 R3-A07 | OPEN | PROVEN |
| 55 | Pmove / 碰撞常量缺失 | …THIRD_ROUND_PREREQUISITES.md | OPEN | CLAIMED |
| 56 | 0x02→0xA2E50 分派 BLOCKED | …08_CLIENT_OPCODE_DISPATCH_TRACE/F5_FINAL_EVIDENCE_MATRIX.md | BLOCKED | PROVEN(负面) |
| 57 | 客户端 0x06 语义未知 | …07_PROTOCOL_BIDIRECTIONAL_TRACE/E5_COMPATIBILITY_MATRIX.md | BLOCKED | PROVEN(负面) |
| 58 | 0x03 实时消费者只有 demo 路径 | XVAL-01_…/XVAL01_CONFLICT_REGISTER.md | BLOCKED | PROVEN |
| 59 | 恢复镜像缺末节 .tp3（49MB） | …09_CLIENT_RECOVERY_BOUNDARY/G4_BLOCKER_AND_DECISION.md | BLOCKED | PROVEN |
| 60 | .rimp 重放规则未闭合 | 14_SERVER_KNOWLEDGE_ATLAS_001/11_OPEN_QUESTIONS.md | PARTIALLY_RESOLVED | PROVEN |
| 61 | 恢复镜像生成器未知 | …09_CLIENT_RECOVERY_BOUNDARY/G1_RECOVERY_AUDIT.md | BLOCKED | PROVEN(负面) |
| 62 | XVAL-01 ".data 99.86% 缺失"被推翻 | XVAL-02_…/XVAL02_FINAL_DECISION.md | OBSOLETE | PROVEN |
| 63 | count1/A2 位宽旧记录仍在档 | XVAL-01_…/XVAL01_CONFLICT_REGISTER.md | CONTRADICTORY | PROVEN |
| 64 | 2697 注册 5 字段语义未知（扣留 gamestate） | 12_CODEC_MVP_001/05_UNKNOWN_SEMANTICS.md | OPEN | PROVEN |
| 65 | 2697 runtime-assets / 原包未核验 | 11_CUSTOM_SERVER_FEASIBILITY_001/07_FINAL_RECOMMENDATION.md | UNVERIFIED | 未定 |
| 66 | 3.19 游戏通道传输栈未定 | XVAL-01_…/XVAL01_CONFLICT_REGISTER.md | BLOCKED | PROVEN |
| 67 | 记录层加密原语 / XOR 密钥来源未知 | 14_…/11_OPEN_QUESTIONS.md | OPEN | CLAIMED |
| 68 | COOKIE_ECHO 189 vs 219 | 14_…/10_EVIDENCE_CONFLICTS.md | CONTRADICTORY | 双留 |
| 69 | 协议号 187 vs 1 | 14_…/10_EVIDENCE_CONFLICTS.md | CONTRADICTORY | 双留 |
| 70 | 3.19 运行时镜像仅 4.5% 覆盖 | CODOL_ANALYSIS_20261020/THIRD_ROUND_PREREQUISITES.md | OPEN | PROVEN |
| 71 | ACE 后内存全页不可读 | …COLLECT_319_…_INTAKE_AUDIT.md | BLOCKED | PROVEN |
| 72 | 无真实战斗抓包（UDP 28960 = 0） | 同上 | OPEN | PROVEN |
| 73 | booking 生效但无 mmstart/战斗 UDP | …AUDIT_INDEX.md | OPEN | PROVEN |
| 74 | 收口声明与残留进程不一致 | …DIAGNOSTIC_RUNS_…_CLOSURE_AUDIT.md | CONTRADICTORY | PROVEN |
| 75 | 受保护集 8/9（marketplace_store） | …NEXT_RUN_BASELINE_DECISION_20261021.md | BLOCKED | PROVEN |
| 76 | run_all.py 共享 GAME_ROOT + 6 次重试 | 同上 | OPEN | PROVEN |
| 77 | 黄金源目录含 208 个运行残留 | 同上 | OPEN | PROVEN |
| 78 | `ol_deploy` after_build 副作用风险 | BUILD-RISK-XMAKE-AFTER-BUILD-001.md | OPEN | PROVEN |
| 79 | T-1 残留未验证项 | T1_ACCEPTANCE_REPORT.md | PARTIALLY_RESOLVED | PROVEN |
| 80 | 9 个插件专属文件无测试目标 | T1_ACCEPTANCE_REPORT.md | NOT_IMPLEMENTED | PROVEN |
| 81 | 真实 Frida 运行时从未执行 | T2_3_REGRESSION_REPORT.md | UNVERIFIED | PROVEN |
| 82 | PID 身份仅名字级 | T2_1_G1_PROCESS_IDENTITY_REPORT.md | OPEN | PROVEN |
| 83 | TESTOL 清单 1/769 哈希不符 | _LEARN_TESTOL_DELIVERY2/reports/010-…md | OPEN | PROVEN |
| 84 | TESTOL 无 inject_ayria.on | _LEARN_TESTOL_DELIVERY/reports/009-…md | NOT_IMPLEMENTED | PROVEN |
| 85 | TESTOL preflight 误报 / deploy 只比大小 | _LEARN_TESTOL_DELIVERY2/reports/013-…md | OPEN | PROVEN |
| 86 | STRIP_PROTECTION 候选无验证结论 | STRIP_PROTECTION_001/logs/unpack.log | UNVERIFIED | PROVEN |

---

## 详细条目

### 1 — IIPS QoS 前置条件内容未知
**报告**：`ICH017_IIPS_BOUNDARY_SYNTHESIS.md`
**引证**：> "UNKNOWN: 1. What exact condition the QoS helper checks 2. What value the QoS helper returns and why"
**已证 vs 声称**：分叉点（`iips.dll+0x98D2 test al,al`）是静态 PROVEN；QoS helper 的检查对象是 CLAIMED。`ICH018_QOS_RETURN_VALUE_ATTRIBUTION.md` 给出 `tqos_create → WSOCK32!select() → 负值 → AL=0`，但同一文件自评 `DEPENDENCY_CAUSALITY = CANDIDATE`。
**状态**：OPEN（诊断值 `8189FEC` 为显示值后，此项仍是真正的入口前置）。
**后续证据**：`restore_iips_contract_001` §8c 把边界重述为"窗口创建与 `LoadLibrary("IFS.dll")` 之间的未满足前置"，比 QoS 更窄，但未关闭。

### 2 — IFS2.dll 运行时从未加载
**报告**：`ICH016_IIPS_LOADER_CAUSALITY.md`
**引证**：> "Run 1 … IFS2.dll: NOT OBSERVED / Run 2 … NOT OBSERVED / Run 3 … NOT OBSERVED"；> "IFS2.dll IMAGE_LOAD: 0/3 (STABLE)"
**已证 vs 声称**：3/3 正常 `-q` 运行中 `iips.dll` 稳定加载、`IFS2.dll` 从不出现（PROVEN 负面）；"从未被调用"是推断（ICH016 自己写 `NOT_OBSERVED` 而非 `FAILED`）。
**状态**：OPEN。
**后续证据**：`ICH017_IIPS_HIGH_RES_LOADER_TRACE.md` 以 1ms 分辨率 0/3 排除亚毫秒瞬时加载。

### 3 — 调试器观测被反作弊阻断（双向死锁）
**报告**：`ICH015_PRE_STAGE1_DIVERGENCE.md`
**引证**：> "iips.dll NEVER loads under debugger / Exit code = 0xE06D7363 / Anti-cheat (TenProtect) prevents iips.dll from loading"
**已证 vs 声称**：PROVEN。报告自述这是"constraint boundary"而非实验失败。唯一被认可的非侵入路线是内核 ETW callstack，未执行。
**状态**：BLOCKED。
**后续证据**：`CODOL_EX058_RESULT.md` 的 A/B/C/D 四次尝试同样失败（`DebugActiveProcess … error 5`；附加成功者 `0xC0000409 before iips.dll load`）。

### 4 — 0x8189FEC 数值语义不可定
**报告**：`ICH013_IIPS_INITIALIZATION_GATE.md`
**引证**：> "0x8189FEC_STATIC_REFERENCE_COUNT = 0 / 8189FEC_CLASS = STATIC_UNKNOWN (runtime-computed / packed-VM-generated)"
**已证 vs 声称**：零静态引用 PROVEN；"是 IIPS 失败状态码"是 CLAIMED。
**状态**：UNVERIFIED。
**后续证据**：`ICH035R_8189FFCE_ANALYSIS.md` 改判为 `TYPE = DIAGNOSTIC_VALUE`；`ICH052_DECISION.md` 进一步写 "8189FEC 与 Resource Event / FF / Zone / Asset 无直接关联"。多次改判本身说明该值不能作为控制流判据。

### 5 — IFS 依赖"必要但不充分"
**报告**：`restore_iips_contract_001/RESTORE_IIPS_CONTRACT_001_DECISION.md` §8b
**引证**：> "IFS_DEPENDENCY = NECESSARY_BUT_NOT_SUFFICIENT (CONFIRMED)"
**已证 vs 声称**：单因子实验（沙箱内把 `IFS2.dll` 暴露为 `IFS.dll`）使 `LoadLibraryA("IFS.dll") = PASS`，但 `IIPSHostApp 已启动 : False`、`命名对象出现 : 无`。属于 PROVEN 的单变量实验。
**状态**：OPEN（负结论，缩小到"IFS 步骤上游"）。
**后续证据**：`restore_iips_contract_002` 只复制了该矩阵的四格沙箱，未见独立结论文件（目录内无 `.md`）。

### 6 — IIPS provider 契约卡在步骤 1→2
**报告**：`restore_iips_contract_001/RESTORE_IIPS_CONTRACT_001_DECISION.md` §8c
**引证**：> "CONTRACT_ADVANCES_PAST_STEP_1 = NO (CONFIRMED) / ROOT_BLOCKING_CONDITION = 步骤 1 与步骤 2 之间未被满足的前置条件"
**已证 vs 声称**：三次可比运行中 1. 窗口 3/3、2. `IFS.dll` 0/3、3. `IIPSHostApp.exe` 0/3、4. 管道 0/3、5. ShareState 0/3 —— PROVEN。
**状态**：OPEN。
**后续证据**：与条目 2 同源，但观测仪器不同（AboProbe vs 模块轮询）；不合并是因为本条把边界收窄到"窗口已创建之后"。

### 7 — SeCreateGlobalPrivilege 候选前置未验证
**报告**：`restore_iips_contract_001/RESTORE_IIPS_CONTRACT_001_DECISION.md` §8d
**引证**：> "UNMET_PRECONDITION_CANDIDATE = SetPrivilege / SeCreateGlobalPrivilege 不可得 / LEVEL = CANDIDATE"
**已证 vs 声称**：观测进程令牌 `SeCreateGlobalPrivilege = ABSENT` 是 PROVEN；目标进程是否停在此步是 CLAIMED（报告自己写明"既不能证明目标进程的 SetPrivilege 步骤确实失败，也不能证明 provider 就停在这一步"）。
**状态**：UNVERIFIED。
**后续证据**：项目主链一律以提权代理（`elevated_agent.py`）运行，与"普通权限令牌"这一前提不同；该候选是否已被提权运行间接排除，未见专门对照。

### 8 — 0xFFFFFFFF 终止来源未知
**报告**：`restore_iips_contract_001/RESTORE_IIPS_CONTRACT_001_DECISION.md` 判定块
**引证**：> "FFFFFFFF_SOURCE = UNKNOWN (found in all images 17221/43239/9080 times; mere presence is not attribution)"
**已证 vs 声称**：常量在多个映像中高频出现（PROVEN）；归因 UNKNOWN。
**状态**：OPEN。
**后续证据**：`RESTORE_ENGINE_BRIDGE_003_DECISION.md` 记录条件 B 自退出 `0xFFFFFFFF @30.6s`，同样未归因。

### 9 — `iipsinit` 身份被前轮误判
**报告**：`CODOL_EX047_IIPS_INITIALIZATION_CONTRACT.md`（旧说法）对 `restore_iips_contract_001/RESTORE_IIPS_CONTRACT_001_DECISION.md` §1（新结论）
**引证（旧）**：`CODOL_EX047_IIPS_INITIALIZATION_CONTRACT.md` 第 45–50 行：> "And immediately before: ``` iipsinit Environment List Box / WIN_IIPS_INIT_ERROR / 8189FEC ```"（`iipsinit` 被写成窗口枚举里的一项，读作"窗口/初始化环节"；`restore003/RESTORE_ENGINE_BRIDGE_003_DECISION.md` 条件 A 表同样记 `iipsinit 文本 = "Environment List Box"`）
**引证（新）**：> "IIPSINIT_MEANING = MSVC DECORATED SYMBOL NAME (\"?iipsinit\"), NOT a window class or title literal, NOT an initialization function name"
**已证 vs 声称**：新结论 PROVEN（EXE 文件偏移 `0x75B90C` 处 `3F 69 69 70 …` 即 `?iipsinit`，位于 RTTI/符号表邻居区）。
**状态**：CONTRADICTORY（旧表述作废）。
**后续证据**：`restore_iips_contract_001` §1 给出邻居 `.?AVdwRoom@@` / `.?AVdwRoomImp@@`，与本项目其它 RTTI 结论一致。

### 10 — IIPS 成功路径从未运行时观测
**报告**：`ICH014_IIPS_FOUR_STAGE_FAILURE.md`
**引证**：> "IIPS_SUCCESS_PATH = STATIC_CONFIRMED (iips.dll + 0x9A2B..0xA831) / IIPS_SUCCESS_TO_ENGINE = UNKNOWN (success path never observed at runtime)"
**已证 vs 声称**：成功分支静态 PROVEN；运行时 UNKNOWN。
**状态**：OPEN。

### 11 — Engine continuation gate 未定位
**报告**：`ICH039_DECISION.md`
**引证**：> "STATIC/DYNAMIC_OBSERVABILITY = INSUFFICIENT / ENGINE_CONTINUATION_GATE = NOT_LOCATED"
**已证 vs 声称**：RM 注入后 30s 内 0 状态差分（PROVEN 负面）；"阻塞点在 VM/平台"是推论。
**状态**：BLOCKED（用户态观测边界）。
**后续证据**：`ICH043_DECISION.md`、`ICH049/050/051/052/053` 逐轮下沉，最终停在 VM 不透明。

### 12 — VM interpreter / ISA 未定位
**报告**：`ICH041_DECISION.md`
**引证**：> "VM_INTERPRETER = NOT_LOCATED / VM_ISA = NOT_RECOVERED / VM_ENGINE_CALL = NOT_OBSERVED / NEXT_TARGET = STOP_NO_FURTHER_SCAN"
**已证 vs 声称**：`ICH057_DECISION.md` 进一步怀疑"VM ISA 概念可能不适用"，模型需重定义。
**状态**：BLOCKED。
**后续证据**：`ICH059_DECISION.md` 冻结 PRCL 静态分析。

### 13 — .tvm0 解密 routine 未定位
**报告**：`ICH058_DECISION.md`
**引证**：> ".tvm0 中 Engine code 的加密不是简单 XOR。需要进一步分析才能确定加密算法。当前状态：UNKNOWN（未能定位解密 routine）"
**已证 vs 声称**：加密非平凡（CLAIMED，基于线性解码比 0.0378）；算法 UNKNOWN。
**状态**：BLOCKED。
**后续证据**：`CODOL_EXE_DEEP_ANALYSIS.md` 记 `.tvm0 linear decode ratio: 0.0378`、`RWX .tp3 linear decode ratio: 0.0010`，同样只能给"关系 UNKNOWN"。

### 14 — .tls scheduler 假设被证伪
**报告**：`ICH059_DECISION.md`
**引证**：> "所有 .tls 中的 API 名称引用都是 IMPORT NAME TABLE (INT) 条目"；> "TLS_PRCL_ROLE = UNKNOWN (data confirmed, scheduler function NOT found)"
**已证 vs 声称**：PROVEN。ICH-058 的 `.tls = PRCL scheduler` 假设被推翻。
**状态**：CONTRADICTORY（假设作废）。
**后续证据**：`ICH059_DECISION.md` 末段列出四种仍可能位置（`.tls` 代码、`.tvm0` 自包含、ordinal-1 直执行、运行时生成），全部未定位。

### 15 — Anchor A/B 是 VM 常量池噪声
**报告**：`ICH046_DECISION.md`
**引证**：> "0x00CA0000 的 90 hits 是 VM bytecode stream 中的伪随机字节匹配（dword 恰好等于这些地址值），不是地址引用"
**已证 vs 声称**：PROVEN（`0x00E83C18`、`0x009B9C00` 在 `.tls` 中 0 命中，说明表槽是运行期动态生成）。
**状态**：CONTRADICTORY（ICH-043/044 曾把 Anchor A/B 当候选 continuation）。
**后续证据**：`ICH053_DECISION.md` 确认 Slot 41 caller 无 native 调用者。

### 16 — 96 项派发表身份 = 复合/GFx 接口
**报告**：`RESTORE003_DECISION.md`
**引证**：> "此前的 \"Engine Root Object\" 模型整体错误"；> "约 41 个函数是 GFx"
**已证 vs 声称**：PROVEN（26 个函数 push Scaleform/GFx 格式串）。
**状态**：CONTRADICTORY。
**后续证据**：`RESTORE005_DECISION.md` 把 96 项表定为 `COMPOUND_INTERFACE`，Group B/C 语义仍 UNKNOWN。

### 17 — Resource→FF 桥接被自我证伪
**报告**：`ICH051_DECISION.md`
**引证**：> "0x009C19C0 不是 FF/Zone loader。它是一个 dynamic array resize/truncate 函数。"；> "PROCESS_ITEM_TO_FF = CONFIRMED → **REFUTED**"
**已证 vs 声称**：PROVEN（0x76 字节函数体无任何文件/FF 字符串引用）。
**状态**：CONTRADICTORY（ICH-050 的 CONFIRMED 作废）。
**后续证据**：`ICH052_DECISION.md` 把该链改判为 `resource slot allocation/management`。

### 18 — Slot 41 caller 为 VM 不透明
**报告**：`ICH053_DECISION.md`
**引证**：> "Slot 41 的 caller 是 VM dispatch mechanism。没有 native caller 可以在不恢复 VM ISA 的前提下恢复。"
**已证 vs 声称**：PROVEN（负面）：native 侧无调用者可恢复。
**状态**：BLOCKED。

### 19 — Root Object 运行时地址不可恢复
**报告**：`ICH043_DECISION.md`
**引证**：> "Root Object 的构造发生在 VM 侧，其地址在运行时由 VM 内部计算产生，不落在任何可静态定位的 .data 段。"
**已证 vs 声称**：PROVEN：EXE 无 `.data` 段（全部为 `.tp3`/`.tvm0`），定向 dword 搜索 0 候选。
**状态**：BLOCKED。

### 20 — Engine 从不调用 RM / GetRM
**报告**：`restore003/RESTORE_ENGINE_BRIDGE_003_DECISION.md`
**引证**：> "在 9 次运行、两种 provider、60/90 秒观测窗口内，**Engine 从未调用 `GetResourceManagerII`，也从未消费任何 ResourceManager 对象。**"
**已证 vs 声称**：PROVEN（A/B 各 4 次 + B5 90s）。报告同时警告：> "`RM_VTABLE_CALLS = 0` 只表示\"在当前实验窗口和当前观测机制下未观察到\"。**不能**据此写\"Engine 不调用 ResourceManager\"。"
**状态**：CONTRADICTORY vs `ICH037_DECISION.md` 的 "GetResourceManagerII: 被调用（我们补丁了它）"。两者观测对象不同（替换 provider vs 补丁导出），但结论被后续引用时常混用。
**后续证据**：EB-003 给出条件 A 进程"活着 60s"只是模态框阻塞：> "`PROCESS_ALIVE_IS_NOT_ENGINE_OK` 条件 A 进程\"活着 60s\"只是因为模态对话框阻塞，不是成功。"

### 21 — ICH-027 的 IIPS→FF 契约被运行时否定
**报告**：`ICH054_DECISION.md`
**引证**：> "**ICH-027 的假设 \"Engine → IIPS_IsPackReady → loadfastfile\" 被运行时证据否定。** Engine 在收到 RM 指针后不调用任何 IIPS API。"
**已证 vs 声称**：PROVEN（11 个 IIPS API 调用计数全 0，除被补丁的 GetRM 各 1）。
**状态**：CONTRADICTORY。
**后续证据**：`ICH030_PROXY_VALIDATION.md`/`ICH034` 的"gate 已跨越"结论依赖该契约成立；契约被否定后这些"成功"只能读作"存活"。

### 22 — Game Init / Frontend 入口不存在于明文
**报告**：`ICH055_DECISION.md`
**引证**：> "No plain Game/Engine Init function reachable | EX-011 | CONFIRMED_ABSENCE"
**已证 vs 声称**：PROVEN（负面）：`CODOL_STANDALONE_CORE_013R_TARGET_RESOLUTION.md` 把 8 个历史 RVA 全部判为 `NOT_FILE_BACKED_OR_VIRTUAL_ONLY` 或 `ALIGNMENT_INVALID`。
**状态**：OPEN。

### 23 — 有 FF 文件也未触发 FF 打开
**报告**：`ICH034_BEFORE_AFTER.md`
**引证**：> "STOP-2: Engine FILE_NOT_FOUND → OPEN_SUCCESS: NOT DIRECTLY CONFIRMED (Engine 未主动发出 FF open 请求；FF 是被动等待的资源)"
**已证 vs 声称**：10 个 `.ff` 从 `ff_init_common_gfx_V109.ifs` 提取并部署后进程存活 30s（PROVEN），但 `LOADFASTFILE_CALLED = NO`。
**状态**：OPEN。
**后续证据**：`ICH036_DECISION.md` 部署 RM v2 后仍是 `LOADFASTFILE_CALLED = NO`；`ICH037/043` 30s 内 `loadfastfile calls = 0`。

### 24 — "IIPS gate crossed" 结论被推翻
**报告**：`ICH030_PROXY_VALIDATION.md`
**引证**：> "★ IIPS GATE CROSSED ★ … Process SURVIVED past IIPS gate"
**已证 vs 声称**：CLAIMED（"survived = gate passed"）。`RESTORE_ENGINE_BRIDGE_003_DECISION.md` 用原始 provider 复现同样"gate crossing"：> "ENGINE_GATE = PASS 两种条件都通过（约 6.5–7.3s，96 项派发表填满）"，且原文注明 `ENGINE_GATE_IS_NOT_GAME_INIT`。
**状态**：CONTRADICTORY（"gate" 并非 IIPS 通过，而是派发表填充时点）。
**后续证据**：EB-003 表：A 条件（原始 iips）有致命对话框，B 条件无；两者 gate 时刻相近。

### 25 — "ResourceManager ABI" 大部分虚构
**报告**：`RESTORE_LOCALRM_006_DECISION.md`
**引证**：> "**它全部来自 `RESTORE_LOCALRM_001/LocalRM.cpp`** —— 一个**手写的 C++ 草稿** … 而那一轮**从未编译过、从未运行过**"
**已证 vs 声称**：PROVEN（逐条对机器码：`__stdcall` REFUTED、单 vptr REFUTED、`+0x70` / `+0x3BC` 降级）。
**状态**：CONTRADICTORY（历史 ABI 断言作废）。
**后续证据**：`RESTORE_ENGINE_BRIDGE_003_DECISION.md` §3 以原始 `iips.dll` 独立复现 48/48 槽与 4 个 vptr，`STRUCTURAL_ABI_EQUIVALENCE = CONFIRMED`（机械等价，非语义等价）。

### 26 — RM 语义仍 UNKNOWN
**报告**：`RESTORE_LOCALRM_006_DECISION.md`
**引证**：> "`RESOURCE_MANAGER_SEMANTICS` 仍是 `UNKNOWN`"；分级表 `UNKNOWN (6): VTABLE_1_IS_INITIALIZE, VTABLE_2_IS_CHECKSTATE, VTABLE_3_IS_PROCESS, DESTRUCTOR_OWNERSHIP, RESOURCE_MANAGER_SEMANTICS, THREAD_SAFETY`
**已证 vs 声称**：PROVEN（标注为 UNKNOWN）。
**状态**：OPEN。
**后续证据**：`RESTORE005_DECISION.md` 独立地仍把 Group B/C 判为 UNKNOWN（"无法区分 GFx 或 Engine"）。

### 27 — Release 后单例悬空（原版即如此）
**报告**：`RESTORE_LOCALRM_006_DECISION.md`
**引证**：> "`Release(obj)` 之后再调用 `GetResourceManagerII()` 会返回悬空指针 … 这在**原始 iips.dll 中就是这样**"
**已证 vs 声称**：PROVEN（`ReleaseResourceManagerII` 不清 guard/实例槽）。
**状态**：NOT_IMPLEMENTED（有意保留原语义，未修）。
**后续证据**：报告写明 `DESTRUCTOR_OWNERSHIP = UNKNOWN`，"如果 Engine 真的走 `Release → 再 Get`，那是 003 必须观察的第一个行为点"；EB-003 观测到 `Release` 0 次，未触发。

### 28 — LocalRM_v3 导出目录错位 4 字节
**报告**：`restore003/RESTORE_ENGINE_BRIDGE_003_DECISION.md`
**引证**：> "`LOCALRM_V3_EXPORT_DIR_ALIGNMENT = DEFECT (declared 0x55360, actual 0x5535C, delta +4)` / `IMPACT = none observed (loader tolerant)`"
**已证 vs 声称**：PROVEN（重反汇编确认）。
**状态**：NOT_IMPLEMENTED（记录、不修）。

### 29 — 0x480 vs 0x410 对象尺寸矛盾
**报告**：`ICH028_LOCAL_COMPAT_SURFACE.md` 对 `RESTORE_LOCALRM_006_DECISION.md`
**引证（旧）**：> "Allocate a 0x480-byte object"
**引证（新）**：> "RM_OBJECT_SIZE = CONFIRMED (0x410)"
**已证 vs 声称**：新值 PROVEN（`push 0x410`）。
**状态**：CONTRADICTORY。
**后续证据**：`ICH029_COMPAT_SURFACE.md` 仍写 `OBJECT SIZE: 0x410 bytes`，但 `ICH028_RESOURCE_MANAGER_ABI.md` 的 `0x480` 未回改。

### 30 — Base+0x306A `ecx=3` 写入者未知
**报告**：`CODOL_EX017_WRITER_RESULT.md`
**引证**：> "writer = UNKNOWN / first valid object observed: yes (EX-016) / destination = object+4 / object+18 candidates / new value = 3"
**已证 vs 声称**：PROVEN（有效对象 `ECX=0x128A4CE8, [ECX+18]=0x0F` → 后变 `3`）。硬件写断点因对象地址随进程变化而无法固定（`CODOL_EX007_PROVENANCE.md`）。
**状态**：OPEN。
**后续证据**：`EX-006` 追溯 `3` 来自 `[0x141CE020+4]`，但同一地址跨运行不稳定。

### 31 — Base bootstrap 退出契约未知
**报告**：`CODOL_STANDALONE_CORE_010_BOOTSTRAP_CONTRACT.md`
**引证**：> "The project is not ready for implementation, and it is not proven that Base ordinal-1 is the blocker either."
**已证 vs 声称**：`BLOCKED_BY_UNKNOWN`（PROVEN：EXE 无 Entry 连接的静态延续；`ORDINAL1_RETURN = NOT_FOUND (0/12 observed)`）。
**状态**：BLOCKED。
**后续证据**：`CODOL_EX018_RET_RESULT.md` 同样：> "ordinal_1 RET: NO / RET EIP: N/A"。

### 32 — CORE-013 无唯一静态目标
**报告**：`CODOL_STANDALONE_CORE_013R_TARGET_RESOLUTION.md`
**引证**：> "E01201_TARGET = UNRESOLVED / TARGET_STATUS = NO_UNIQUE_STATIC_TARGET / DYNAMIC_TEST_READY = NO"
**已证 vs 声称**：PROVEN（8 个归因 RVA 逐项排除）。
**状态**：BLOCKED。

### 33 — 观察者诱发行为分叉
**报告**：`CODOL_EX028_OBSERVER_DIVERGENCE.md`
**引证**：> "DEBUGGER_DIVERGENCE_CONFIRMED … MODE-B enters the fatal/exit path before any project DLL loads."
**已证 vs 声称**：PROVEN。
**状态**：OPEN（方法学限制：所有"调试下的负面结论"都受此制约）。
**后续证据**：`CODOL_EX043_STUN_INIT_RUNTIME_VALIDATION.md` 单地址调试尝试同样 "diverged before reaching 0x2212C0"。

### 34 — 调试附加权限不可得
**报告**：`CODOL_EX058_RESULT.md`
**引证**：> "`DebugActiveProcess` failed with Win32 error 5"；> "The privilege call reported `ok=True` but `GetLastError=1300` (`ERROR_NOT_ALL_ASSIGNED`)"
**已证 vs 声称**：PROVEN。
**状态**：BLOCKED。

### 35 — argv 提供者槽 0xCA827C API 身份未证
**报告**：`CODOL_EX032_ARGV_PROVIDER_SEMANTICS.md`
**引证**：> "The exact API name behind `0xCA827C` is therefore not statically proven"
**已证 vs 声称**：数据形状（`char**` + count）PROVEN；API 身份 CLAIMED。
**状态**：UNVERIFIED。
**后续证据**：`CODOL_EX034_ARGV_GATE_SEMANTICS.md` 仍为 `ARGV_PROVIDER_PARTIAL`。

### 36 — `-q/-qa/-src=tgp` 语义未决
**报告**：`CODOL_EX035_Q_QA_GATE_AND_BOOTSTRAP.md`
**引证**：> "`-q` and `-qa` are gate-only tokens with respect to `WIN_NO_TCLS`; they do not complete bootstrap."；分类 `MODE_SEMANTICS_UNRESOLVED`
**已证 vs 声称**：门禁旁路 PROVEN；语义 UNKNOWN。
**状态**：UNVERIFIED。
**后续证据**：`CODOL_EX041_POST_GATE_BOOTSTRAP_STATE_MACHINE.md` 记 `Q_QA_POST_GATE_BEHAVIOR_EQUIVALENT`（`-q` 与 `-qa` 观测等价）。

### 37 — 历史真实命令行从未找到
**报告**：`CODOL_EX033_HISTORICAL_CLIENT_COMMANDLINE.md`
**引证**：> "No historical log or dump was found in the workspace that contains the full real command line used by `Client.exe -> codoMP_client_shipRetail.exe`."
**已证 vs 声称**：PROVEN（2020 Tenproxy 日志有共享内存成功记录，但无命令行）。
**状态**：BLOCKED。

### 38 — TCLS 共享内存/签名布局未知（写零缓冲）
**报告**：`CODOLLauncher/CODOL_LAUNCHER_V1.md`
**引证**：> "The buffer is zeroed because no offset/size/encoding for `GameSignature` or `JumpSignature` is confirmed in this workspace."
**已证 vs 声称**：映射名 `TCLS_SHAREDMEMEMORY+<GamePID>` 与 `Post TCLS_TENPROXY_RESULT Message Success!` 来自历史日志（PROVEN）；结构布局 CLAIMED。
**状态**：OPEN。
**后续证据**：`CODOL_EX067_TCLS_SHARED_MEMORY_LAYOUT.md` 解出 `512 KiB` 映射与 `+0x00 = 0x40` 版本头，但仍 `PAYLOAD_PID_SOURCE = UNKNOWN`、`GAMEID_TO_GAMEPID_RELATION = UNKNOWN`。

### 39 — 谁创建 tcls_core.exe 未知
**报告**：`CODOL_EX066_TCLS_PROTOCOL_CLOSURE.md`
**引证**：> "U05  The binary that starts tcls_core.exe; no matching external host module is present in this workspace."
**已证 vs 声称**：PROVEN（负面）：`TCLS_PROCESS_CREATION = EXTERNAL_HOST_UNAVAILABLE`。
**状态**：BLOCKED。
**后续证据**：`CODOL_EX068_NATIVE_TENPROXY_BRIDGE.md` 重复同一条（U06）。

### 40 — TCLS payload PID / GameID 生成未知
**报告**：`CODOL_EX067_TCLS_SHARED_MEMORY_LAYOUT.md`
**引证**：> "PAYLOAD_PID_SOURCE = UNKNOWN"；> "GAMEID_TO_GAMEPID_RELATION = UNKNOWN"
**已证 vs 声称**：映射名/映射口径 PROVEN；payload 语义 UNKNOWN。
**状态**：OPEN。
**后续证据**：`CODOL_EX068_NATIVE_TENPROXY_BRIDGE.md`：> "U03  The upstream source/generation of the 64-bit GameID."

### 41 — TenProxy `Invoke(0x566)` 未解包调用点未知
**报告**：`CODOL_EX068_NATIVE_TENPROXY_BRIDGE.md`
**引证**：> "U01  The exact unpacked instruction in codoMP_client_shipRetail.exe that calls Invoke(0x566)."
**已证 vs 声称**：调用链 `Base:GetTSObject → TenProxy!Invoke → 0x13E3 → 0x1D70 → command 0x566` 为 `STATIC_DATAFLOW_CONFIRMED`；EXE 侧发起指令 `PACKED_UNRESOLVED`。
**状态**：OPEN。

### 42 — TCLS 状态值 0x63/0x18/0x11 语义未知
**报告**：`CODOL_EX065_TCLS_UPSTREAM_BOUNDARY.md`
**引证**：> "U07 The meaning of the state values 0x63 / 0x18 / 0x11 in sub_8DBEB / sub_8D9EF."
**已证 vs 声称**：门值集合 PROVEN；语义 UNKNOWN。
**状态**：OPEN。

### 43 — EXE 明文函数图仅部分
**报告**：`CODOL_EXE_CORE_002_PLAIN_TEXT_FUNCTION_MAP.md`
**引证**：> "EXE_PLAIN_TEXT_MAP_PARTIAL … FileSystem/Config/Localization/Window/Input/Audio/Network/Renderer/Game/Main Loop/Shutdown: UNKNOWN_SUBSYSTEM"
**已证 vs 声称**：入口 thunk 与 7 个 bootstrap 候选为 CANDIDATE；其余 UNKNOWN。
**状态**：OPEN。
**后续证据**：`CODOL_EXE_CORE_004_6212C0_DOWNSTREAM.md`：> "Plain-text caller count: 0 / Downstream edges found: 0"。

### 44 — Launcher 源码编译失败、BOOT_DEPTH 卡 2
**报告**：`CODOLLauncher/logs/_run_fixed.txt` 与 `CODOLLauncher/CODOL_LAUNCHER_V1.md`
**引证**：> "类型\"string\"必须是不可为 null 的值类型才能用作泛型类型或方法\"System.Nullable<T>\"中的参数\"T\""（`CODOLLauncher.cs:37`）
**已证 vs 声称**：编译失败 PROVEN；文档自述 `BOOT_DEPTH=2`，且加不加 TCLS 映射结果相同：> "The TCLS mapping alone did not move the observable module set beyond this in the test run."
**状态**：NOT_IMPLEMENTED（源码与盘上的 12,288 B EXE 不同步）。
**后续证据**：`logs/CODOLLauncher_20261002-221253.log` 记 `[State] FATAL_WINDOW=False`，与文档"显示致命错误窗口"不同；两处观测口径不一致。

### 45 — AlwaysofflineRe 拒绝"unknown executable image"
**报告**：`TAKEOVER_STATUS_20261019.md`
**引证**：> "`[combined/backend] Refused to apply CODOL startup patches to an unknown executable image.`"；`frame_hook=false`、`返回码 6`
**已证 vs 声称**：PROVEN（本地链日志 `native_engine_attach.jsonl` 同记 `{"stage": "frame_hook", "ok": false}`）。
**状态**：OPEN（`HANDOFF_NEXT_SESSION_20261019.md` 列为当前首要阻塞）。
**后续证据**：同文件提醒不可归因 IIPS：> "目前不能把它写成\"28961 协议坏了\"\"IIPS 8189fec\"或\"远程线程一定失败\"。"

### 46 — 宿主 SizeOfImage 门禁不符
**报告**：`TAKEOVER_STATUS_20261019.md`
**引证**：> "`EngineBindings.cpp` 的宿主门禁要求 `TimeDateStamp=0x6096930A`、`SizeOfImage=0x0E5D6000`" 而 "实际 `SizeOfImage=0x0E659000`"
**已证 vs 声称**：PROVEN（另有 `ARTIFACT_BLOCKERS.md` B3/B4：两处 RVA 字节在加壳件上均不匹配）。
**状态**：OPEN。
**后续证据**：`TAKEOVER_STATUS` 自述 `*.bak` 版本含 `0x0E5D6000`，但"只改宿主 SizeOfImage 不能直接视为已解决"。

### 47 — Dedicated 两难：IIPS 弹窗 vs 直接退出
**报告**：`TAKEOVER_STATUS_20261019.md`（22:06 段）
**引证**：> "`enable_iips=1` 触发 IIPS 错误，`enable_iips=0` 导致客户端退出"；> "`CODOL_GameServerGetStatus` 返回 `enabled=0 frame=0 serverTime=0`，证明 `Com_Frame` 循环未运行"
**已证 vs 声称**：PROVEN（探针返回值）。
**状态**：OPEN。
**后续证据**：`HANDOFF_NEXT_SESSION_20261019.md` §2.2 把 `enable_iips=0` 描述为本地链隔离手段，与本条"退出"冲突；两者沙箱不同（`sandbox_repro_test_20261019` vs `datafix`），但报告未显式对照，属未解释差异。

### 48 — 历史本地链成功样本不可复现
**报告**：`CODOL_LOCAL_ENGINE_CHAIN_20261019/HANDOFF_NEXT_SESSION_20261019.md`
**引证**：> "该日志只能作为成功时序样本，不能直接当作当前链已经成功。"
**已证 vs 声称**：历史 `local_native_server.log` 内容（PID 19576、`ConfigureSession status=0`、UDP 28960 归属）为 CLAIMED 记录，未复跑。
**状态**：UNVERIFIED。

### 49 — 转储工具入口基准错误
**报告**：`CODOL_LOCAL_ENGINE_CHAIN_20261019/HANDOFF_NEXT_SESSION_20261019.md`
**引证**：> "当时入口反汇编使用了模块基址，不是 PE AddressOfEntryPoint，因此 reverse_report.json 里的入口反汇编不能直接作为结论。"
**已证 vs 声称**：PROVEN（自述缺陷）。
**状态**：NOT_IMPLEMENTED（修正步骤写在 §4 第五步，未见执行记录）。

### 50 — 原生战斗链缺地图资产
**报告**：`CODOL_NATIVE_BATTLE_CHAIN_20261019/logs/combat_server.log`
**引证**：> "`地图 mp_firingrange 未在已登记资产中找到 —— v0.1 仍按配置启动，但客户端可能因缺少地图资源而无法进入战斗`"
**已证 vs 声称**：PROVEN（同时 `未找到地图资产目录（map_assets / _map_extract）`）。
**状态**：OPEN。
**后续证据**：`README.md` 的"成功条件"没有地图资产要求，而日志把地图缺失列为风险 —— 验收判据与运行事实不一致。

### 51 — 原生战斗链 selftest 4 项失败
**报告**：`CODOL_NATIVE_BATTLE_CHAIN_20261019/README.md`
**引证**：> "离线 selftest 当前通过 251 项；4 项失败来自复制后的运行环境（临时目录权限和缺少源码指纹目录）"
**已证 vs 声称**：PROVEN（失败项已归类）。
**状态**：PARTIALLY_RESOLVED。
**后续证据**：同类失败在 `12_CODEC_MVP_001/04_CODEC_TEST_RESULTS.md` 也出现：> "111 通过，3 失败 … `%TEMP%\\codol_sess_* UnauthorizedAccessException`"，说明是环境性而非协议性。

### 52 — NIFS 清单分隔符自相矛盾
**报告**：`ICH033_NIFS_FORMAT.md` 对 `ICH034_BEFORE_AFTER.md`
**引证（旧）**：> "Manifest: null-separated .ff paths"
**引证（新）**：> "`Manifest 使用 CRLF (\\r\\n) 分隔（不是 null 分隔！）`"
**已证 vs 声称**：新结论 PROVEN（10 个条目 1:1 对应 10 个 IWff 块）。
**状态**：CONTRADICTORY（`ICH033_DECISION.md` 与 `ICH033_NIFS_FORMAT.md` 未回改）。
**后续证据**：`ICH034_NIFS_BLOCK_INDEX.csv` 只有表头（`block_index,manifest_offset,ff_path,iwff_offset,iwff_size,version`）无数据行 —— 支撑该结论的机读表未落盘，属证据制品缺口。

### 53 — layer-2 世界资产从未导出
**报告**：`CODOL_ANALYSIS_20261020/THIRD_ROUND_PREREQUISITES.md`（R3-A07）
**引证**：> "FF containers are present … but no verified extracted structures"；> "Export layer-2 CLIPMAP_MP, MAP_ENTS, ComWorld and physics/XModel collision with hashes and references."
**已证 vs 声称**：PROVEN（`COLLECT_319_…_INTAKE_AUDIT.md`：> "FF block-0 解出 `IWffs100` / `mp_firingrange`；layer-2 和世界资产未解"）。
**状态**：OPEN。

### 54 — mp_firingrange clipmap 解析失败
**报告**：`_LEARN_TESTOL_DELIVERY2/reports/452-navgraph-table-aipaths-is-empty-in-every-zone.md`（另见 `CODOL_ANALYSIS_20261020/THIRD_ROUND_PREREQUISITES.md` R3-A07 与 `ICH033_DECISION.md`）
**引证**：> "// the `aipaths` asset that should hold it is EMPTY in every shipped zone."
**已证 vs 声称**：PROVEN：`mp_firingrange.ff` 31,332,485 B 存在，但 clipmap / 导航资产无可信导出；项目记忆亦记"材质私有非公共"。
**状态**：OPEN。

### 55 — Pmove / 碰撞常量缺失
**报告**：`CODOL_ANALYSIS_20261020/THIRD_ROUND_PREREQUISITES.md`（R3-A08）
**引证**：> "Generic movement physics notes exist; target values and runtime consumption remain open"
**已证 vs 声称**：CLAIMED（通用物理笔记存在）；目标值 UNKNOWN。
**状态**：OPEN。
**后续证据**：`C_SERVER_WORLD_COLLISION_AUDIT.md` 记 `p.X/p.Y 更新之后与快照编码之前` 的调用缺口，未给出常量。

### 56 — 0x02→0xA2E50 分派 BLOCKED
**报告**：`CODOL_2697_SERVER_STATIC_ANALYSIS_20261011/08_CLIENT_OPCODE_DISPATCH_TRACE/F5_FINAL_EVIDENCE_MATRIX.md`
**引证**：> "`opcode 0x02 → 分派 → RVA 0xA2E50 → 字段读取`：**未形成完整静态证据链，标记 BLOCKED。**"
**已证 vs 声称**：字段形状两端 PROVEN；分派 PROVEN 负面（E8/绝对 VA/裸 RVA/跳转表全 0）。
**状态**：BLOCKED。
**后续证据**：`14_SERVER_KNOWLEDGE_ATLAS_001/22_SERVER_START_GATING_AUDIT.md` 准入 `CONDITIONAL GO`，但禁止"客户端能正确解析 configstring"类结论。

### 57 — 客户端 0x06 语义未知
**报告**：`CODOL_2697_SERVER_STATIC_ANALYSIS_20261011/07_PROTOCOL_BIDIRECTIONAL_TRACE/E5_COMPATIBILITY_MATRIX.md`
**引证**：> "客户端 `0x06` EOF/EOS 处理 `NOT-OBSERVED/BLOCKED` … 未找到可复现读取或终止指令。服务端写入不能证明客户端支持。"
**已证 vs 声称**：服务端写点 PROVEN（`0xA4CAF` 内部、`0x87104` 外层选择）。
**状态**：BLOCKED。

### 58 — 0x03 实时消费者只有 demo 路径
**报告**：`XVAL-01_LOCAL_NETWORK_EVIDENCE_CROSS_VALIDATION/XVAL01_CONFLICT_REGISTER.md`（CONF-X04）
**引证**：> "已证 0x03 消费者**属 demo 路径**，其字段序与服务端实时 writer **冲突（REFUTED，限定范围）**；**实时消费者 BLOCKED**。"
**已证 vs 声称**：demo 归属为"强推断（非 PROVEN）"。
**状态**：BLOCKED。

### 59 — 恢复镜像缺末节 .tp3（49MB）
**报告**：`CODOL_2697_SERVER_STATIC_ANALYSIS_20261011/09_CLIENT_RECOVERY_BOUNDARY/G4_BLOCKER_AND_DECISION.md`
**引证**：> "**不能支持\"原版客户端绝对不存在某调用/分派\"的负面结论。**"
**已证 vs 声称**：PROVEN：原始末节 `.tp3` VA `0xDC11000`、VSZ `0x3214000`；恢复镜像同址只有 `.rimp`（VSZ `0x2964`）。
**状态**：BLOCKED。
**后续证据**：`XVAL-02_…/XVAL02_FINAL_DECISION.md` 确认"末节 `.tp3` 的 **49.14 MB 虚拟尾部未恢复**（是否含游戏代码未证）"。

### 60 — .rimp 重放规则未闭合
**报告**：`14_SERVER_KNOWLEDGE_ATLAS_001/11_OPEN_QUESTIONS.md`（BQ-26 更新）
**引证**：> "**PARTIAL**：已解析结构（420 →`.rimp`、189 →`.text`、17 →`.rdata`、2,061 非指针含 ASCII 导入名）；**完整重放规则仍未定**"
**已证 vs 声称**：结构计数 PROVEN；重放规则 UNKNOWN。
**状态**：PARTIALLY_RESOLVED。

### 61 — 恢复镜像生成器未知
**报告**：`CODOL_2697_SERVER_STATIC_ANALYSIS_20261011/09_CLIENT_RECOVERY_BOUNDARY/G1_RECOVERY_AUDIT.md`
**引证**：> "生成脚本/构建元数据 | 未在 Launcher、分析目录或恢复目录中找到独立的 aplib 解包/重建脚本 … BLOCKED"
**已证 vs 声称**：PROVEN（负面）。`XVAL-02` 只做 aplib 保真重算，仍非原始生成链。
**状态**：BLOCKED。

### 62 — XVAL-01 ".data 99.86% 缺失"被推翻
**报告**：`XVAL-02_IMAGE_INTEGRITY_AND_REGISTER_AUDIT/XVAL02_FINAL_DECISION.md`
**引证**：> "XVAL-01 的\"`.data` 99.86% 缺失\"**不成立**——它是 PE `VirtualSize`/`SizeOfRawData` 的 BSS 比"
**已证 vs 声称**：PROVEN（两文件 `.data` raw 各 300,544 B，SHA-256 同为 `661843e2…5462f`）。
**状态**：OBSOLETE（旧结论作废）。
**后续证据**：`XVAL02_NEGATIVE_EVIDENCE_REASSESSMENT.md` 反而把 0 命中升级为"更强发现"，但同时保留 `.tvm0` / BSS / 末节 `.tp3` 三重盲区，不得升级为"客户端不支持"。

### 63 — count1/A2 位宽旧记录仍在档
**报告**：`XVAL-01_LOCAL_NETWORK_EVIDENCE_CROSS_VALIDATION/XVAL01_CONFLICT_REGISTER.md`（CONF-X01/X02）
**引证**：> "E-08 的 \"10 bit\" 记录错误；**原文保留**"；> "**16 bit（2 字节 LE）PROVEN；8 bit REFUTED**"
**已证 vs 声称**：两侧独立反汇编 PROVEN。
**状态**：CONTRADICTORY（已裁决但旧规格文本未删改，实施侧仍需参数化）。
**后续证据**：`14_…/22_SERVER_START_GATING_AUDIT.md` 要求 `count1` 宽度"做成可配置参数（因 BLK-2 未定）" —— 与 XVAL-01 的 RESOLVED 冲突，属未同步。

### 64 — 2697 注册 5 字段语义未知（扣留 gamestate）
**报告**：`12_CODEC_MVP_001/05_UNKNOWN_SEMANTICS.md`
**引证**：> "2697 原生注册/激活 … 未决: 合法、可复现、非绕过式的完整配置路径。等级: BLOCKED/NOT-OBSERVED。"
**已证 vs 声称**：扣留行为 PROVEN：> "`CoDOL 2697 gamestate withheld: verified client registration export is required`"；字段语义 UNKNOWN。
**状态**：OPEN。
**后续证据**：`11_OPEN_QUESTIONS.md` BQ-07 由 BLOCKED → "格式链 CONFIRMED（5 字段语义仍 OPEN）"。

### 65 — 2697 runtime-assets / 原包未核验
**报告**：`11_CUSTOM_SERVER_FEASIBILITY_001/07_FINAL_RECOMMENDATION.md`
**引证**：> "2697 `runtime-assets`（11,033 文件 / 1.7 GB）未逐文件解析"
**已证 vs 声称**：清单 PROVEN；内容 UNKNOWN。
**状态**：UNVERIFIED。
**后续证据**：`THIRD_ROUND_PREREQUISITES.md` R3-A10：> "original `server2697` directory is not visible"，2697 只能作"派生证据源"。

### 66 — 3.19 游戏通道传输栈未定
**报告**：`XVAL-01_LOCAL_NETWORK_EVIDENCE_CROSS_VALIDATION/XVAL01_CONFLICT_REGISTER.md`（CONF-X05）
**引证**：> "**主张 A REFUTED**（TLS 读取仅 1 字节就绪探测，明文从未外传；E-15）；libcurl/OpenSSL 归属更新模块。**游戏协议传输栈仍是 BLOCKED**（明文 UDP 最可能，但未闭合）。"
**已证 vs 声称**：TLS 假设 REFUTED（PROVEN）；UDP 明文 CLAIMED。
**状态**：BLOCKED。

### 67 — 记录层加密原语 / XOR 密钥来源未知
**报告**：`14_SERVER_KNOWLEDGE_ATLAS_001/11_OPEN_QUESTIONS.md`（BQ-11/BQ-12）
**引证**：> "CODOL 记录层加密原语（AES? MAC?） | SOURCE-CONFLICT"；> "`CODOL_Xor` 对称 XOR 的密钥来源 | 未知"
**已证 vs 声称**：存在自研记录层 PROVEN；原语/密钥 CLAIMED。
**状态**：OPEN。
**后续证据**：`XVAL01_UNSUPPORTED_CLAIMS.md` 把 C-004（`CODOL_Xor` body）列为单源，需"反汇编 2697 `CODOL_Xor` 调用点 + 密钥来源"。

### 68 — COOKIE_ECHO 189 vs 219
**报告**：`14_SERVER_KNOWLEDGE_ATLAS_001/10_EVIDENCE_CONFLICTS.md`
**引证**：> "全局状态：`SOURCE-CONFLICT`（保留）——**两个数字可能分别对应不同版本/不同阶段的 packet**。"
**已证 vs 声称**：双方来源均记录；无目标抓包裁决。
**状态**：CONTRADICTORY。
**后续证据**：`XVAL01_CONFLICT_REGISTER.md` 复核"仍成立；静态不可裁决"；`restore_iips_contract_001` 的 `TCLS` 链路不涉及此值。

### 69 — 协议号 187 vs 1
**报告**：`14_SERVER_KNOWLEDGE_ATLAS_001/10_EVIDENCE_CONFLICTS.md`
**引证**：> "影响：任何\"CODOL 协议号 = X\"的断言。状态：`SOURCE-CONFLICT`（内部选择 vs 出站线值），**不强行统一**。"
**已证 vs 声称**：实机二分"187 卡住客户端，1 能连"（`codol_connect.c:89-91` 注释）为 CLAIMED。
**状态**：CONTRADICTORY。

### 70 — 3.19 运行时镜像仅 4.5% 覆盖
**报告**：`CODOL_ANALYSIS_20261020/THIRD_ROUND_PREREQUISITES.md`（R3-A01）
**引证**：> "Current image covers only about 4.513% of SizeOfImage; IAT slots and runtime globals lie beyond EOF, so static xrefs cannot prove a complete dispatcher."
**已证 vs 声称**：PROVEN（`image_best.bin` 10,899,456 B / SHA `17cef6e0…`）。
**状态**：OPEN。
**后续证据**：`WELCOME_CODOL_CLIENT_INDEPENDENT_AUDIT.md` 明确"不得把本项目镜像当作 `R3-A01` 的解"。

### 71 — ACE 后内存全页不可读
**报告**：`CODOL_ANALYSIS_20261020/COLLECT_319_20261021_132905_INTAKE_AUDIT.md`
**引证**：> "运行时镜像 | 0 / 58,969 页可读，全部错误 299；`BLOCKED_AFTER_ACE`"
**已证 vs 声称**：PROVEN（`image_pages.raw` 0 字节）。
**状态**：BLOCKED。
**后续证据**：`DIAGNOSTIC_RUNS_20261021_…_CLOSURE_AUDIT.md` 复现：> "PID 9964；OpenProcess 错误 5；全页扫描未执行"。

### 72 — 无真实战斗抓包（UDP 28960 = 0）
**报告**：`CODOL_ANALYSIS_20261020/COLLECT_319_20261021_132905_INTAKE_AUDIT.md`
**引证**：> "UDP 28960 | 0 帧"；> "战斗搬运 | 1 个 4 B 载荷 `00000000`，服务端 `ACK`，客户端随后 `RST`"
**已证 vs 声称**：PROVEN（3 帧 TCP / 776 B，且抓包迟到）。
**状态**：OPEN。
**后续证据**：`THIRD_ROUND_BLOCKER_STATUS_AUDIT_20261021.md` 同记 `udp_28960_packets = 0`，并把 `3 帧 TCP` 列为"不得当作战斗会话"。

### 73 — booking 生效但无 mmstart / 战斗 UDP
**报告**：`CODOL_ANALYSIS_20261020/AUDIT_INDEX.md`
**引证**：> "后者出现 20 次 `mmbook accepted`、0 次 `mmstart`、UDP/28960 零收包"
**已证 vs 声称**：PROVEN（DIRECT_20261021_145654）。
**状态**：OPEN。
**后续证据**：R3-A11 最小解除条件"Capture lobby/booking response, chosen battle endpoint, client connect attempt"未满足。

### 74 — 收口声明与残留进程不一致
**报告**：`CODOL_ANALYSIS_20261020/DIAGNOSTIC_RUNS_20261021_144241_145654_CLOSURE_AUDIT.md`
**引证**：> "发现残留 Python 服务进程与端口监听，收口声明与现场不一致"
**已证 vs 声称**：PROVEN（3074/28960 仍在监听）。
**状态**：CONTRADICTORY（属运行规范违反，非技术未知）。

### 75 — 受保护集 8/9（marketplace_store）
**报告**：`CODOL_ANALYSIS_20261020/NEXT_RUN_BASELINE_DECISION_20261021.md`
**引证**：> "`REF_LOBBY_KIT\\marketplace_store.py` is 50,022 B while `_golden_hashes.json` expects 46,226 B. The current protected set is therefore 8/9."
**已证 vs 声称**：PROVEN。`GOLDEN-LOBBY-001\\REF_LOBBY_KIT` 逐字节 9/9，但迁移未授权。
**状态**：BLOCKED（`baseline_migration=BLOCKED_PENDING_USER_DECISION`）。

### 76 — run_all.py 共享 GAME_ROOT + 6 次重试
**报告**：`CODOL_ANALYSIS_20261020/NEXT_RUN_BASELINE_DECISION_20261021.md`
**引证**：> "The original `run_all.py` hard-codes `GAME_ROOT = …sandbox_datafix_20260929`; it also defaults to `--retries 6`, so it can relaunch a client several times in one invocation."
**已证 vs 声称**：PROVEN，与单次启动/隔离规则冲突。
**状态**：OPEN。
**后续证据**：`CODOL_FROZEN_CHAIN_RECOVERY_20261020.md` 已用 `run_frozen_chain_once.py` + 一次性令牌（`runs/.frozen_launch_used`）在**外层**规避；受保护文件本体未改（正确），但因此任何绕过外层入口的调用仍不安全。

### 77 — 黄金源目录含 208 个运行残留
**报告**：`CODOL_ANALYSIS_20261020/NEXT_RUN_BASELINE_DECISION_20261021.md`
**引证**：> "That golden source is not a clean runtime directory: it contains 208 top-level files including old logs, certificates, session files, `tas_off.flag`, `poke_off.flag` …"
**已证 vs 声称**：PROVEN。
**状态**：OPEN（清理规则未批准）。
**后续证据**：项目记忆已记同类坑：新 run 的 kit 从上一轮整目录复制会带上旧 `_c_battle_out.txt`，导致门控误判"已进图"。

### 78 — `ol_deploy` after_build 副作用风险
**报告**：`BUILD-RISK-XMAKE-AFTER-BUILD-001.md`
**引证**：> "任何**未显式限定目标**的构建调用——**包括 `--dry-run`**——都可能触发它。"
**已证 vs 声称**：PROVEN（`F1`：`xmake build --dry-run` 实际执行了 `after_build` 的 `os.vrunv`）。
**状态**：OPEN（仅登记，代码层消除需授权）。
**后续证据**：本轮之所以"无损害"只因 `config/codol-game-dir.txt` 指向不存在目录 —— 报告自己写明"这是偶然的、脆弱的保护"。

### 79 — T-1 残留未验证项
**报告**：`T1_ACCEPTANCE_REPORT.md` §5
**引证**：> "UV-2 | **真实的 `closesocket` 失败路径** | `stop()` 的失败分支只由 IAT 伪造覆盖"；> "UV-7 | 9 个插件专属文件（含 `FrameHook.cpp`）的正确性 | 不在任何测试目标内"
**已证 vs 声称**：`checks=124 failures=0` 为 OFFLINE。FF-1（端口释放）与 FF-2（`lastSocketError`）后已实施（`T1_FF1_PORT_RELEASE_REPORT.md`：> "`checks=112 failures=0`"），FF-3/FF-4 明确 `NOT IMPLEMENTED`。
**状态**：PARTIALLY_RESOLVED。
**后续证据**：`T2_RUNTIME_VALIDATION_PREREQUISITES.md` 仍把真实 socket 行为列为待授权。

### 80 — 9 个插件专属文件无测试目标
**报告**：`T1_ACCEPTANCE_REPORT.md`
**引证**：> "UV-7 … T-1 的通过**不能**外推到它们 … 需新建插件边界测试目标（报告 §4.3 的 T1 方案，未实施）"
**已证 vs 声称**：PROVEN（`NEXT_PHASE_PLAN.md` P1-2 仍为待授权项）。
**状态**：NOT_IMPLEMENTED。

### 81 — 真实 Frida 运行时从未执行
**报告**：`T2_3_REGRESSION_REPORT.md`
**引证**：> "修复后的注入脚本**从未在任何真实 Frida 运行时中执行过**"
**已证 vs 声称**：`OFFLINE`：工具 34/0、调用方 59/1（既有）、`checks=124 failures=0`；`E-Runtime = 0 项`（`T2_2_RUNTIME_READINESS_REVIEW.md` §10）。
**状态**：UNVERIFIED（"已修复"仅离线/自测证据）。
**后续证据**：`T2_4_RUNTIME_AUTHORIZATION_REQUEST.md` 仍是"申请"，未执行。

### 82 — PID 身份仅名字级
**报告**：`T2_1_G1_PROCESS_IDENTITY_REPORT.md`
**引证**：> "R1 身份是名字级的：只比对映像基名，不校验构建号/映像哈希/签名，同机同名不同构建无法区分"
**已证 vs 声称**：PROVEN（自述限制）。
**状态**：OPEN。
**后续证据**：`T2_3_REGRESSION_REPORT.md`：> "终止前的身份复核把 PID 复用窗口**缩小但未消除** … 身份是 名称 + 路径 + SHA-256，**不是**密码学签名。"

### 83 — TESTOL 清单 1/769 哈希不符
**报告**：`_LEARN_TESTOL_DELIVERY2/reports/010-manifest-verify-result.md`
**引证**：> "`payload/Ayria/Plugins/Localnetworking.Ayria32  manifest=AF0E22FD2F4A77D1 actual=4E9BFDC33635EA2F`"
**已证 vs 声称**：PROVEN，且报告自认是上一轮会话覆盖所致（"上一轮我重新编译并覆盖了"）。
**状态**：OPEN（包完整性；原版无法恢复，见项目记忆）。
**后续证据**：`deploy.ps1` 只比大小（`_LEARN_TESTOL_DELIVERY2/reports/013-preflight-deploy.md`：> "只比大小 … 同大小不同内容永远不更新"），因此该文件即使内容错了也永远不会被部署修正。

### 84 — TESTOL 无 inject_ayria.on
**报告**：`_LEARN_TESTOL_DELIVERY/reports/009-inject-switch-final-verdict.md`
**引证**：> "四个全部落空。"；> "`nt10.py:1373  _inject = False`"
**已证 vs 声称**：PROVEN（四处零命中）。推论链：不加载插件 → 无 28960/3074。
**状态**：NOT_IMPLEMENTED（与"项目正常"的用户声明冲突，报告自己列出三类未验证可能性）。
**后续证据**：项目记忆记"真正加载插件的入口是 `source\\tools\\runtime\\CodolGame.py launch`"，即 README 双击流程本就不完整。

### 85 — TESTOL preflight 误报 / deploy 只比大小
**报告**：`_LEARN_TESTOL_DELIVERY2/reports/013-preflight-deploy.md`
**引证**：> "本报告发现 `preflight.ps1` 有一处**误报逻辑**、`deploy.ps1` 有一处**静默跳过**"
**已证 vs 声称**：PROVEN（逐字节）。
**状态**：OPEN。
**后续证据**：同在 `_LEARN_TESTOL_DELIVERY2/reports/012-build-md.md`：> "BUILD.md 与 README **在 `source\\build\\` 上自相矛盾**，且**映射表有一处致命偏差**"，并泄漏 `D:\\Program Files\\xmake\\xmake.exe` / `E:\\Source\\Repos\\Main\\vcpkg` 两个作者机路径（属另一条文档缺陷，合并记入本条）。

### 86 — STRIP_PROTECTION 候选无验证结论
**报告**：`STRIP_PROTECTION_001/logs/unpack.log`（及 `candidate.json` / `stub_candidate.json`）
**引证**：> "`ap32_candidates=0`"；`candidate.json` 只记 "`removed_section … va 241004544` / `new_size_of_image 241004544`"
**已证 vs 声称**：制品存在（`work\\candidate_no_guard.exe` 7,802,880 B、`work\\candidate_stub.exe` 7,806,976 B），脚本注释称 > "Offline candidate: keep the real engine sections and replace the protection tail with a minimal import/entry stub."；**没有任何**"该候选能否启动 / 是否等价"的结论文件。
**状态**：UNVERIFIED。
**后续证据**：`ARTIFACT_BLOCKERS.md` B6 的"加壳候选与去壳目标等价性"仍为 `UNKNOWN`，本目录未解除它。

---

## 附：需要在最终合并时注意的三类"伪已解决"

1. **OFFLINE 当验证**：`T1_ACCEPTANCE_REPORT.md` / `T2_3_REGRESSION_REPORT.md` / `12_CODEC_MVP_001/04_CODEC_TEST_RESULTS.md` 的 `checks=… failures=0`、`26/26 PASS`、`111 通过 3 失败`，全部是离线自测；三份报告本身都显式声明了 `E-Runtime = 0`、`客户端兼容 = NOT-OBSERVED`。
2. **SIMULATED 当互通**：`ICH030`–`ICH036` 的"gate crossed / process survived"用的是内存补丁的本地 RM，`RESTORE_ENGINE_BRIDGE_003_DECISION.md` 用原始 provider 复现了同一个"gate"，证明该时点与 IIPS 成功无关（`ENGINE_GATE_IS_NOT_GAME_INIT`）。
3. **"进程存活"当成功**：`ICH031`–`ICH037` 的 `PROCESS_LIFETIME = 30+ seconds`；EB-003 明确指出条件 A 的 60s 存活只是模态对话框阻塞（`PROCESS_ALIVE_IS_NOT_ENGINE_OK`）。

## 附：目录可读性备注

- `分析/`：无任何 `.md`，只有 CSV/JSON/py 脚本（`00_baseline_module_hashes.csv`、`02_runtime_xrefs.json` 等），按"报告语料"口径不可读，仅作数据源。
- `WeGame/`：纯二进制与配置，无 `.md`；`Tenio.ini` / `protocol_cs.tdr` / `tpf_ui.vfs` 未在本任务范围内解析。
- `restore_iips_contract_002/`：**无任何 `.md`**（只有 `mk_sandbox.py`、`run_matrix.ps1`、observer 与 `runs/*_console.txt`），其结论只能由 `runs/` 日志与非结论文件反推；文中引用仅取脚本 docstring 与日志原文。
- `STRIP_PROTECTION_001/`：只有脚本与 `logs/*.json|log`，无结论文档。
- `CODOLLauncher/logs/`：11 份日志，其中 2 份（`20261002-221253` / `20261002-221120`）与文档叙述的 `FATAL_WINDOW=True` 不符（实为 `False`），已在条目 44 记录。
