# 11 — 基础档案遗留问题 / OPEN QUESTIONS (BASE)

> 本文件是**基础档案层**的遗留问题。跨项目层的问题库见 `18_TEN_THOUSAND_WHYS.md`，假设台账见 `17`，验证计划见 `19`。

## 1. 样本身份类

| ID | 问题 | 状态 |
|---|---|---|
| BQ-01 | 2697 服务端源码能否获得 | BLOCKED（本地无，禁联网） |
| BQ-02 | IW4x 两份克隆差异清单 | BLOCKED（未生成） |
| BQ-03 | `iw4x-rawfiles` 空克隆能否恢复 | BLOCKED（禁联网） |
| BQ-04 | OLD 源码能否建立到二进制逐函数对应 | BLOCKED（无 PDB/MAP） |
| BQ-05 | C-2697 恢复镜像与运行时映射是否等价 | BLOCKED（无运行时 dump） |

## 2. 生命周期类

| ID | 问题 | 状态 |
|---|---|---|
| BQ-06 | 2697 是否在运行期真正激活（哪个 CVar/条件） | BLOCKED |
| BQ-07 | 2697 门控 `+0x78F4` 与 `+0x6408` 的合法放行路径 | PARTIAL（有文件格式；完整路径未闭合） |
| BQ-08 | `_CODOL_Target2697ArchivesActive` 的 `0x16D` 语义 | STATIC-INFERENCE |
| BQ-09 | 2697 关闭/资源销毁路径 | 未分析 |

## 3. 传输 / 序列化类

| ID | 问题 | 状态 |
|---|---|---|
| BQ-10 | COOKIE_ECHO 189 vs 219 谁对应 C-2697 | BLOCKED（需抓包） |
| BQ-11 | CODOL 记录层加密原语（AES? MAC?） | SOURCE-CONFLICT |
| BQ-12 | `CODOL_Xor` 对称 XOR 的密钥来源 | 未知 |
| BQ-13 | 分片 ACK/重传调度是否已实现 | OLD 自述未完成 |
| BQ-14 | 内部 codec 187 vs 出站 protocol 1 的关系 | SOURCE-CONFLICT |

## 4. 应用层类

| ID | 问题 | 状态 |
|---|---|---|
| BQ-15 | gamestate state[0]/+4/+8/+0xC 语义 | BLOCKED |
| BQ-16 | configstring body 位编码 | BLOCKED |
| BQ-17 | snapshot 完整帧边界 | BLOCKED |
| BQ-18 | 内部 `0x06` vs 外层 `0x05/0x06` 的确切分工 | STATIC-INFERENCE |
| BQ-19 | 6519 条 configstring 的 2697 对应关系 | 未分析 |
| BQ-20 | 保险 profile（secure profile）发布结构 | PARTIAL |

## 5. 客户端消费类（最高优先级）

| ID | 问题 | 状态 |
|---|---|---|
| BQ-21 | `opcode 0x02 → 分派 → 0xA2E50` | **BLOCKED**（最关键的兼容性障碍） |
| BQ-22 | 客户端 `0x06` 读取/终止判断 | NOT-OBSERVED / BLOCKED |
| BQ-23 | 客户端 `0x03` gamestate parser | BLOCKED |
| BQ-24 | 客户端 `0x04` configstring parser | BLOCKED |
| BQ-25 | snapshot delta 解码（`0x6E060` / `0x6D340`） | BLOCKED |
| BQ-26 | `.rimp` 指针修复格式 | BLOCKED（静态可尝试） |
| BQ-27 | 原始最后 `.tp3`（VA 0xDC11000 起） | BLOCKED（未恢复） |

## 6. 业务 / 平台类

| ID | 问题 | 状态 |
|---|---|---|
| BQ-28 | 2697 武器 recipe 字段语义 | BLOCKED |
| BQ-29 | PIK10 / SKU 与 2697 inventory 的关系 | STATIC-INFERENCE |
| BQ-30 | TenProxy/IIPS/TCLS 是否参与游戏通道 | **REFUTED 为“参与游戏通道”**（属启动/平台层） |
| BQ-31 | 2697 注册 5 字段语义 | PARTIAL |
| BQ-32 | 服务器记分板/HUD/安全档案的下行结构 | PARTIAL |

## 7. 遗留问题结论

1. **最高优先级的 5 个 BLOCKED**：BQ-21（0x02 分派）、BQ-22（0x06）、BQ-23/24（gamestate/configstring parser）、BQ-17（snapshot 帧边界）。
2. **最具解释力的两个新发现**：BQ-07（2697 门控）与 BQ-05（恢复镜像等价性）。
3. **静态仍可推进一项**：BQ-26（`.rimp` 指针修复格式）——唯一不依赖运行的客户端侧静态路线。
4. 其余 BLOCKED 多依赖**运行时 dump** 或**真实抓包**，需额外授权（见 `19`）。
---

# === 追加：第二轮验证后的遗留问题状态（UPDATE-2, 2026-10-12） ===

| ID | 更新前 | 更新后 | 依据 |
|---|---|---|---|
| BQ-06（2697 运行期激活开关） | BLOCKED | BLOCKED（但已知门控 CVar 名） | EV-2697-RCGate2：`CODOL2697_PROFILE_WIRE`；archive 激活 |
| BQ-07（门控放行路径） | PARTIAL | **格式链 CONFIRMED**（5 字段语义仍 OPEN） | EV-2697-RegFmt3 |
| BQ-10（COOKIE_ECHO 189 vs 219 对应 C-2697） | BLOCKED | BLOCKED（未变） | — |
| BQ-19（6519 configstring 的 2697 对应） | 未分析 | 未分析（未变） | — |
| BQ-21（`0x02 → 分派 → 0xA2E50`） | BLOCKED | **BLOCKED（范围收窄）** | `.text` 0 调用（可靠性 95.1%）；`.tvm0` 噪声；`.data` 99.86% 缺失 |
| BQ-26（`.rimp` 指针修复格式） | BLOCKED（静态可尝试） | **PARTIAL**：已解析结构（420 →`.rimp`、189 →`.text`、17 →`.rdata`、2,061 非指针含 ASCII 导入名）；**完整重放规则仍未定** | EV-C2697-RdataPtrs |
| BQ-27（原始最后 `.tp3`） | BLOCKED | BLOCKED（量化：VSize 0x03214000 ≈ 52.5 MB） | EV-C2697-PackedSecs |
| （新）BQ-33 | — | `.data` 声明 218 MB 仅 0.14% 在文件内；候选 vtable 可能缺失 | EV-C2697-DataGap |
| （新）BQ-34 | — | `.tvm0` 原始字节 E8/E9 扫描无效（可靠性 0.0%），需先解码 | EV-C2697-Tvm0Noise |
| （新）BQ-35 | — | 2697 `scripts` 不含协议逻辑（15/1341 且为游戏逻辑） | EV-Scripts-NoProto |
| （新）BQ-36 | — | 2697 `runtime-assets`（11,033 文件 / 1.7 GB）未逐文件解析 | 未核验 |

## 遗留问题优先级（更新）

1. **BQ-33 / BQ-27**（客户端镜像不完备）——现在被认定为**所有客户端侧 BLOCKED 的结构性根因**。
2. **BQ-21**（`0x02` 分派）——仍是最高业务价值，但已确认**不在** `.text` 线性调用图。
3. **BQ-34**——方法学：后续 `.tvm0` 分析必须**先解码**。
4. **BQ-07 剩余部分**（5 字段业务语义）。
5. **BQ-19 / BQ-36**（资源/索引层）——尚未触及。
