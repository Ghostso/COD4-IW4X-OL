# 10 — E-14 总裁定 / VERDICT

> 只读静态分析 + 公开源码研究。原始样本未修改，哈希与基线一致。

---

## 1. 十二个最终问题

**Q1. 哪些机制存在可证实的源码继承关系？**
- OLD/1113 = **CoD4x 的 fork**（字面 `q_shared.h:6` + Jaccard 93–99%）→ **同源已证实**
- OLD ≡ 1113（82/83 字节相同）→ **同源已证实**
- 2697 = Old/1113 同族 + 2697 层（符号 + 常量级）→ **同源已证实**
- CoD4x ↔ IW4X 共享 Quake3 netchan（`netchan_t` 1:1）→ **同源已证实**
- ol-mod 独立于 IW4X → **同源已证实（否定关系）**

**Q2. 哪些只是架构相似，不能直接移植？**
- OLD/1113 ↔ 2697 的**客户端分派逻辑**：架构类比，不可移植
- CODOL 客户端网络栈 ↔ IW4X/CoD4x：**架构不同**（虚表 + TLS），不可移植
- Snapshot 实现：机制相同、实现不同
- `0x60E5B0`：通用 C 运行时格式化器，非协议机制

**Q3. 2697 与经典引擎的确定差异？**
| 机制 | 差异 | 裁定 |
|---|---|---|
| netchan | CODOL 分片层接管（`CODOL_NetchanProcess`） | **PROVEN** |
| Reliable Command | 2697 `0x01`/`0x02` 形态，CoD4x 无 | **PROVEN** |
| Gamestate | 字段序 `{i32,cstr,cstr,i32,<cfgsub>,i32,i32,0x06}` | **PROVEN** |
| Configstring | `0x04` 子帧头 + 2B count1 + 11b A2 count（**本轮修订**） | **PROVEN** |
| Snapshot | `0xA4FA0`/`0xA4860`，Jaccard 67%（与 CoD4x 分歧最大） | **PROVEN** |

**Q4. 哪些开源实现可用于解释客户端候选函数？**
- `0x60E5B0`：通用 `vsnprintf`（C 运行时，非特定开源项目）
- `0x605220`→`0x672460`：**OpenSSL 0.9.8p**（客户端字符串直接证明）
- `MSG_ReadBits`/`MSG_ReadData`：CoD4x/IW4X 形状一致（**实现高度相似**）
- 其余（虚表、分派）：**无对应**

**Q5. `0x60E5B0` 是否已证明属于实时网络协议处理链？**
**否（REFUTED）。** 它是 `vsnprintf` 风格格式化器；`0x6029A0` → `0x60E5B0` 是 **recv 错误日志路径**。

**Q6. 两个网络虚表槽位的构造者是否已定位？**
**否（BLOCKED）。** 已证 `0x898588`/`0x898590` 含 `0xb75a50`/`0xb75ab0`（recv/recvfrom 槽位），但写入虚表指针的构造函数未定位。

**Q7. `0x605220` 路径与状态机路径是否存在可证实汇合？**
**否（REFUTED）。** 两条路径 6 层闭包分别为 7 与 39 个函数，**共享下游 = 0**；且 `0x605220` 实为 TLS 读路径。

**Q8. 是否找到实时 Gamestate `0x03` 消费者？**
**否（BLOCKED）。** 已定位的 `0x34FD80(1)` 属 demo 链，字段序与服务端冲突。

**Q9. `0xA2660` 是否能被认定为实时 Configstring body reader？**
**不能（BLOCKED）。** 字段级行为 PROVEN；3 个调用点均属 demo 链，实时上游未定位。

**Q10. 哪些服务器模块可安全复用开源实现？**
| 模块 | 裁定 |
|---|---|
| Huffman / cvar / cmd / `sv_init_mp` | **可直接复用** |
| netchan 基础 + MSG 原语 | **可直接复用**（引擎部分） |
| netchan 传输、Gamestate、Snapshot | **改造后复用** |
| 可靠命令 2697 形态 | **必须依 CODOL 证据重新实现** |
| 客户端网络栈 | **不能复用** |

**Q11. 阻止端到端兼容验证的最小未知项？**
1. **应用层消息分派器**（TLS 解密后数据去向）— 最大缺口
2. 实时 `0x03` 消费者
3. `0x04`/`0x06` 客户端值级识别
4. 网络虚表构造者

**Q12. 能否计算风险加权解决率？**
**不能（BLOCKED）。** 缺少数值权重与问题项全集。可给出的**非加权**计数：
- 本次任务书列出的 12 个决策问题：**已裁定 12/12**（其中 PROVEN/REFUTED 9 项，BLOCKED 3 项）
- 但"风险权重"（每项对服务器互操作的影响程度）**未经定义**，因此无法计算加权率。
**所需补充：** ① 问题项全集（含 E-01..E-13 遗留项）；② 每项的风险权重（1–5 或类似标度）；③ 每项的裁定分级到数值的映射规则。

## 2. 关键发现（本轮）

| # | 发现 | 等级 |
|---|---|---|
| 1 | `0x60E5B0` 是 vsnprintf，**否定了 E-13 的"协议状态机"假设** | PROVEN |
| 2 | `0x6029A0` → `0x60E5B0` 是 recv **错误日志**路径 | PROVEN |
| 3 | `0x605220` → `0x6104D0` → `0x672460` 是 **TLS（OpenSSL 0.9.8p）读路径** | PROVEN |
| 4 | 客户端内联 **OpenSSL 0.9.8p 16 Nov 2010** | PROVEN |
| 5 | 网络虚表 `.rdata 0x898588`/`0x898590`（recv/recvfrom 槽位） | PROVEN |
| 6 | `0x605220` 与 `0x6029A0` 路径 **无汇合** | REFUTED |
| 7 | A2 计数两侧均为 **11 bit**（E-08 的 10 bit 记录为错） | PROVEN（修订） |
| 8 | CODOL 分片常量（1161/0x70CC729）在**客户端 0 命中** | PROVEN |

## 3. 对 E-13 的修订

| E-13 结论 | E-14 修订 |
|---|---|
| `0x60E5B0` 是协议状态机候选 | **REFUTED**（vsnprintf） |
| `0x6029A0` 是协议处理候选 | **REFUTED**（错误日志） |
| `0x605220` 是独立协议路径候选 | **REFUTED**（TLS 读） |
| 实时入口 4 条候选 | **收窄为 2 条**（`0x1B0430`、`0x78772D`） |

## 4. 下一轮最小任务

| 优先级 | 任务 | 范围 |
|---|---|---|
| 1 | 定位 **TLS 解密后数据的去向**（`0x605220` 上游的明文入口） | `0x605220` 的调用者 `0x602BC0`/`0x612E80` |
| 2 | `0x1B0430` 的 30+ IAT 间接调用目标解析 | `0x1B0430` 内 |
| 3 | 网络虚表构造者 | `.rdata 0x898588` 引用点 |
| 4 | `0x78772D` 的 `.tvm0` 边界（停止条件） | 不扩大 |

## 5. 交付物清单

| 文件 | 状态 |
|---|---|
| `01_REPOSITORY_AND_VERSION_INVENTORY.md` | ✔ |
| `02_SOURCE_LINEAGE_AND_FORK_MATRIX.md` | ✔ |
| `03_NETWORK_AND_MESSAGE_SYSTEM_COMPARISON.md` | ✔ |
| `04_GAMESTATE_CONFIGSTRING_SNAPSHOT_MATRIX.md` | ✔ |
| `05_CODOL_BINARY_MAPPING_MATRIX.md` | ✔ |
| `06_60E5B0_AND_NETWORK_VTABLE_AUDIT.md` | ✔ |
| `07_605220_PATH_AND_CONVERGENCE_AUDIT.md` | ✔ |
| `08_REALTIME_GAMESTATE_CONSUMER_VERDICT.md` | ✔ |
| `09_REUSABLE_COMPONENTS_AND_PROTOCOL_DELTAS.md` | ✔ |
| `10_E14_VERDICT.md` | ✔ |
| `SHA256SUMS.txt` | ✔ |
