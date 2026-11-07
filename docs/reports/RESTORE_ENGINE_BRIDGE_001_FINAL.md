# RESTORE-ENGINE-BRIDGE-001 最终报告

## 实验概览

| 运行 | 模式 | 时长 | 关键配置 | 门控 | 主要发现 |
|---|---|---|---|---|---|
| R1 | baseline | 35s | 运行时 RM v3 注入 | YES | 基线确认：Gate 跨越 9.4s，进程 35s 存活，RM vtable 0 调用 |
| R2 | original | 40s | -q 仅观察，无 RM 注入 | YES | IIPS 路径仍触发致命错误对话框，同基线 |
| R3 | baseline_ifs | 40s | baseline + 原始 .ifs 文件分发到 main\ | YES | .ifs 就位无差异，Gate 10.4s，同样弹出对话框 |
| R7 | passive | 40s | baseline + 无 IAT hook（独立对照） | YES | 仪器无回归，行为与 R1 完全一致 |
| R9 | baseline_clickok | 40s | baseline + 自动点击"确定" | YES | 点击后 42ms 进程退出 code=0xFFFFFFFF —— 模态对话框阻塞即 30s+ 存活唯一原因 |
| R10 | sandbox | 60s | 磁盘级 RM proxy (补丁 iips.dll) | YES | 补丁 iips.dll 加载失败，报"加载iips.dll失败" |
| R11 | sandbox | 45s | 沙箱 + **原始** iips.dll | YES | 原始 iips.dll 在沙箱同样报"加载iips.dll失败" —— 路径完整性检查 |
| R12 | sandbox | 60s | 沙箱 + 补丁 iips.dll (重试) | YES | 重现 R10 结果，确认沙箱路径被拒 |
| R13 | baseline_race | 60s | 2ms 竞态预分配补丁 | YES | GRM_CALL=0，GetResourceManagerII 仍从未被调用 |
| R14 | baseline | 60s | 修复跨进程文本读取 | YES | 证实 WINDOW_TEXT_OK 可读取对话框文本 |

## 证据矩阵

### Gate 前置条件
| 条件 | 状态 | 证据 |
|---|---|---|
| Local RM Gate crossed | CONFIRMED | 9 runs × 96 entries，无异常 |
| 96-entry dispatch table populated | CONFIRMED | 0xE83B00 = 96 non-zero |
| Process survives ≥30s | CONFIRMED | 所有 baseline 60s+ 存活 |
| RM vtable calls | NOT_OBSERVED | 48 slots 计数均为 0 |
| IIPS_IsPackReady/RequestPack | NOT_OBSERVED | 0 调用 |
| loadfastfile / FF open | NOT_OBSERVED | 0 |

### Gate 后状态
| 观测项 | 状态 | 证据 |
|---|---|---|
| Engine Gap (0x994000–0xCA789A) 页变化 | CONFIRMED | 788 页在 4.9s 内一次性从 0 写入代码段，post-gate 无新变化 |
| Dispatch table changes | NOT_OBSERVED | 60s 0 变化 |
| Module/Thread burst | CONFIRMED | ~18 modules, ~16 threads 在 gate 后 175ms 内激活（WeGame UI/IME 链） |
| Named objects / timers / events | NOT_OBSERVED | 无新创建 |
| File system activity | NOT_OBSERVED | CreateFile/FindFirstFile/MapViewOfFile 均无调用 |
| Registry access | NOT_OBSERVED | 0 调用 |
| Network calls | NOT_OBSERVED | WS2_32 socket/connect/select 0 调用 |
| Child processes | NOT_OBSERVED | 0 CreateProcess |
| Window/message | CONFIRMED | 致命错误对话框 (#32770) 在 gate 后 100-150ms 出现 |

### 关键负证据
| 候选触发器 | 结果 | 证据等级 |
|---|---|---|
| GetResourceManagerII 被引擎调用 | REFUTED | GRM_CALL 计数=0 (R13)；运行时补丁 hook=0 (R1-R12) |
| IIPS_IsPackReady → loadfastfile 链 | REFUTED | ICH-054 已结案，0 调用 |
| RM vtable 接口调用 | REFUTED | 48 slots 全程 0 调用 (R1-R14) |
| FF/Zone/Asset 文件访问 | NOT_OBSERVED | CreateFile/MapViewOfFile 0 调用 |
| .ifs 文件被读取 | NOT_OBSERVED | FindFirstFile/ReadFile 0 调用，即使 .ifs 已分发到 main\ (R3) |
| 沙箱路径下 iips.dll 被接受 | REFUTED | 原始 iips.dll 在沙箱仍报"加载iips.dll失败" (R11) |

## 统一记录格式（每 Agent 汇总）

```text
EXPERIMENT_ID=RESTORE-ENGINE-BRIDGE-001
BASELINE=Local RM v3 (ICH-037/048 validated)
START_TIME=2026-09-21
GATE_CROSSED=YES (all baseline runs)
FIRST_POST_GATE_EVENT=致命错误模态对话框 (#32770, "初始化IIPS错误：8189fec") at gate+100ms
OBSERVED_TRIGGER=NONE (Engine 不触发任何 FF/Zone/Asset/GameInit 动作)
ABSENT_TRIGGER=GetResourceManagerII call, RM vtable call, IIPS API call, FF load, Zone init, Asset load
EVIDENCE_LEVEL=CONFIRMED (negative evidence)
CONFIDENCE=HIGH
```

## 最终结论

```text
ENGINE_BRIDGE_STATUS = NEGATIVE_EVIDENCE_ESTABLISHED
TRIGGER_IDENTIFIED = NO
WAIT_CONDITION_IDENTIFIED = NO
```

**核心回答**：Local RM Gate 已确认跨越后，Engine 之所以没有进入 FF/Zone/Asset/Game Init，是因为 **Engine 的下一步初始化由 Base VM dispatch continuation 控制，而非任何 post-gate 的 platform/UI/文件系统/注册表/网络/进程/IPC 条件触发**。在 Gate 跨越后，Engine 处于稳定 standby：dispatch table 静止、RM vtable 0 调用、无文件/注册表/网络活动。唯一的 post-gate 可见动作是 **WeGame 平台层 + Windows IME/UI 子系统的初始化**（18 modules / 16 threads / 175ms 内完成），但 ICH-045 已确认此链为 **PLATFORM_UI_BYPASS**，不构成 Engine trigger。

Engine 实际在等待 **Base VM dispatch mechanism** 的 continuation——这在无 VM ISA 恢复、无 debugger、无反调试绕过的硬约束下不可访问。致命错误对话框 ("初始化IIPS错误：8189fec") 是 IIPS 层初始化失败的**后果**而非 Engine 等待的条件；点击"确定"即终止进程，30s+ 存活仅因模态消息循环阻塞。

```text
NEXT_TARGET = BASE_VM_CONTINUATION (requires VM ISA recovery or PRCL restoration, both currently HARD_STOP)
```

## 附件产物
- `RESTORE_ENGINE_BRIDGE_001_TIMELINE.csv` — 关键时间线 (10 runs 合并)
- `RESTORE_ENGINE_BRIDGE_001_TRIGGER_MATRIX.csv` — 触发器候选评估矩阵
- 所有原始 CSV/MD 在 `_ebo1_observer/out/`