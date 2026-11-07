# -*- coding: utf-8 -*-
import os
wd=r"D:\BaiduNetdiskDownload\使命召唤OL\E17_RECV_ENTRYPOINT_ATTRIBUTION_001"
F={}
F["E17_DEPENDENCY_GRAPH.md"]="""# E17 — 依赖图 / DEPENDENCY GRAPH

> 图例：✔ 已满足 / ✘ 未满足 / ⚠ 部分

---

## 1. 网络输入 → 应用层 依赖链

```
[socket API]
   ├─ recv (7 处) ──┬─ 0x602441  -> 错误日志 ✘非游戏
   │                ├─ 0x6029BE  -> "Recv failure" ✘
   │                ├─ 0x6052AB  -> TLS 探测 ✘(HTTP 更新)
   │                ├─ 0x76D65C  -> thunk ✘
   │                ├─ 0x775A6C  -> socket 抽象 ⚠未归属
   │                ├─ 0x784F7D  -> 0x784F60 (Demonware) ✘
   │                └─ 0x788133  -> 未闭合 ⚠
   │
   ├─ recvfrom (3 处) ─┬─ 0x1B0BA1 -> ICMP ping ✘
   │                   ├─ 0x6B4E3C -> 0x6B4DE0 (Demonware) ✘
   │                   └─ 0x775ADE -> socket 抽象 ⚠未归属
   │
   └─ (无 WSARecv/WSARecvFrom 导入)

   应用层游戏消息分派器：✘ 未定位
        实时 Gamestate 0x03 消费者：✘ 未定位
        Configstring body 0xA2660 实时归属：✘ BLOCKED
```

## 2. 本轮闭合的子图

```
0x783B70 ──call──> 0x784F60 ──call──> recv
   │                    │
   │                    └──> [0xD47370] = WSA 错误码
   │                    └──> [0xD47374] = 状态 2
   │
0x783F00 ──call──> 0x6B4DE0 ──call──> recvfrom
   │                    │
   │                    ├──> ntohs -> [ebx]
   │                    └──> [0xD47388/0xD47398] += 统计
   │
   └──> 0x84 字节栈副本 -> 0xA84CE0（Demonware 交付）
```

## 3. 关键未闭合依赖

| 结论 | 未满足依赖 | 后果 |
|---|---|---|
| 游戏入站路径 | 未定位任何游戏特征消费者 | BLOCKED |
| 0x775A50/0x775AB0 归属 | 虚表实例化路径未定位 | BLOCKED |
| 0x788133 (recv) 归属 | 未审计 | BLOCKED |

## 4. 与 E-16 依赖图的衔接

E-16 结论：E-13 的 2 条候选（0x1B0430、0x78772D）被排除。
E-17 结论：E-13 清单中另外 2 条候选（0x6B4DE0、0x784F60）也被排除。

累计：E-13 的 9 个收包函数中，已归属 7 个（均非游戏）；剩余 2 个为 0x775A50/0x775AB0（socket 抽象虚表）。
"""
F["E17_UNIFIED_QUESTION_REGISTER_UPDATE.md"]="""# E17 — 统一问题库更新 / QUESTION REGISTER UPDATE

> 继承 E-15 权重标度（I4=8 / I3=5 / I2=3 / I1=1；PROVEN=1.0，INFERRED(强)=0.6，BLOCKED=0.0）。
> 不静默改写历史分母。

---

## 1. 本轮新增问题

| Q ID | 协议层 | 问题 | 影响 | 权重 | 当前等级 | 解决度 | 成本 | 阻塞开工 |
|---|---|---|---|---|---|---|---|---|
| Q-20 | 传输 | 0x6B4DE0 归属（Demonware recvfrom 封装） | I2 | 3 | PROVEN | 1.0 | C1 | 否 |
| Q-21 | 传输 | 0x784F60 归属（Demonware recv 封装） | I2 | 3 | PROVEN | 1.0 | C1 | 否 |
| Q-22 | 传输 | Demonware 栈是否为游戏会话路径 | I3 | 5 | BLOCKED | 0.0 | C2 | 是 |
| Q-23 | 传输 | 0x775A50/0x775AB0 虚表归属（最后一个未归属 recv/recvfrom 簇） | I4 | 8 | BLOCKED | 0.0 | C2 | 是 |

## 2. 分母变更记录

| 项 | 值 |
|---|---|
| E-16 末总权重 | 103 |
| 本轮新增权重 | 3 + 3 + 5 + 8 = 19 |
| **本轮末总权重** | **122** |

## 3. 解决率重算

- E-16 加权得分 = 36
- 本轮新增得分 = 3×1.0 + 3×1.0 + 5×0.0 + 8×0.0 = 6
- **本轮末加权得分 = 42**
- **风险加权解决率 = 42 / 122 = 34.43%**

## 4. 趋势

| 轮次 | 总权重 | 加权得分 | 解决率 |
|---|---|---|---|
| E-15 | 91 | 32 | 35.2% |
| E-16 | 103 | 36 | 34.95% |
| **E-17** | **122** | **42** | **34.43%** |

**解读（纪律）：** 解决率连续三轮微降，原因是**不断新增"待归属的收包簇"作为高权重问题**，而非已有结论退化。这反映"搜索面变清晰的同时，分母在扩大"。不得只报 34.43% 而省略分母 122 与口径。

## 5. 与历史记录的关系

| 来源 | 关系 |
|---|---|
| E-15 | 权重标度直接继承，未修改 |
| E-16 | 分母 103 被扩展为 122（新增、未改写） |
| E-13 | 本轮 REFUTED 其清单中 2 条候选 |
"""
F["E17_GATING_AUDIT.md"]="""# E17 — 开工准入审计 / GATING AUDIT

> 追加修订，不覆盖 14_SERVER_KNOWLEDGE_ATLAS_001/22_SERVER_START_GATING_AUDIT.md 及 E-09..E-16 的对应审计。

---

## 1. 判据状态变化（相对 E-16）

| # | 判据 | E-16 | E-17 | 依据 |
|---|---|---|---|---|
| G-33 | 0x1B0430 归属 | 通过 | 通过 | 维持 |
| G-34 | 0x78772D 归属 | 通过 | 通过 | 维持 |
| G-36（新） | 0x6B4DE0 归属 | — | 通过 | recvfrom 封装（EV-17-01） |
| G-37（新） | 0x784F60 归属 | — | 通过 | recv 封装（EV-17-02） |
| G-38（新） | Demonware 栈是否游戏路径 | — | 未通过 | 7 层无游戏解析器（EV-17-08） |
| G-32 | 实时 0x03 消费者 | 未通过 | 未通过 | 仍未定位 |

E-16：通过 26 / 部分 4 / 未通过 3 -> E-17：通过 28 / 部分 4 / 未通过 4。

## 2. 收包原语归属总表（本轮全量）

| 调用点 | 归属 | 等级 |
|---|---|---|
| 0x602441 / 0x6029BE | 错误日志 | PROVEN |
| 0x6052AB | TLS 探测（HTTP 更新） | PROVEN |
| 0x76D65C | thunk | INFERRED |
| 0x775A6C / 0x775ADE | socket 抽象虚表 | INFERRED |
| 0x784F7D | Demonware recv 封装 | PROVEN（职责） |
| 0x788133 | 未闭合 | BLOCKED |
| 0x1B0BA1 | ICMP ping | PROVEN |
| 0x6B4E3C | Demonware recvfrom 封装 | PROVEN（职责） |

**归属完成率（收包原语）：7/9 有明确归属，2/9 未闭合（0x775A50/0x775AB0 簇、0x788133）。**

## 3. 准入裁定

### 3.1 可继续（纯静态，无需授权）

| 工作 | 目标 |
|---|---|
| A-17-1 | 定位 0x775A50/0x775AB0 虚表（.rdata 0x898588/0x898590）的构造者（Q-23） |
| A-17-2 | 审计 0x788133（recv，0x78772D 区段）的真实调用者 |
| A-17-3 | 若有公开 Demonware 接口文档，交叉验证 Q-22 |

### 3.2 仍不可宣称

- 不得宣称 Demonware 栈承载游戏协议（本轮 BLOCKED，7 层内无游戏解析器）。
- 不得宣称实时 Gamestate 消费路径已定位。
- 不得宣称 0xA2660 是实时 Configstring body reader。
- 不得在 Q-22/Q-23 解除前宣称互操作性。

### 3.3 裁定

**CONDITIONAL GO（维持放宽）。** 服务器 Gamestate 编码器可实现服务端自洽版本（依 E-14/E-15 已证字段序）；客户端实时消费链仍 BLOCKED。

## 4. 进入服务器协议实现阶段的准入条件

| 条件 | 状态 |
|---|---|
| 服务端字段序已证（Reliable/Gamestate/Configstring） | ✔ 满足 |
| 客户端实时消费者定位 | ✘ 未满足（Q-05） |
| 客户端 0x04/0x06 值级识别 | ✘ 未满足（Q-06/Q-08） |
| 收包入口归属 | ⚠ 7/9 已归属，2/9 未闭合 |

**结论：可实现服务端，不可宣称互通。**
"""
F["E17_EXECUTIVE_SUMMARY_APPEND.md"]=""
# remove empty helper key
F.pop("E17_EXECUTIVE_SUMMARY_APPEND.md",None)
for n,c in F.items():
    open(os.path.join(wd,n),"w",encoding="utf-8",newline="\n").write(c)
print("wrote",len(F))
