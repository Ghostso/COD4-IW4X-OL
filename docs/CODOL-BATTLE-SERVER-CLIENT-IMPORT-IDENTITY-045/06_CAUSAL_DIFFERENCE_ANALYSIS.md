# 06_CAUSAL_DIFFERENCE_ANALYSIS — 因果差异分析

**任务:** CODOL-BATTLE-SERVER-CLIENT-IMPORT-IDENTITY-045(只读静态)。
**目标:** 区分(1)可解释为**版本演化**的差异,与(2)仍存在**竞争性解释**的差异。
**纪律:** 不用相似函数名/编号/结构认定协议相同;不由服务端写包代码推断客户端已消费。

---

## 1. 只有一方有证据、另一方缺失(不可归因版本演化)

| # | 差异 | 证据状态 | 归类 |
|---|---|---|---|
| 1 | 客户端收包 = `select`+`recv`(045 新证);OLD/2697/OLMod/CoD4x/IW4x 的收包侧本任务未复核 | 客户端 `CONFIRMED`;其余 `NOT-OBSERVED`(非"不同") | **不可归因**;需对每一方独立取证据 |
| 2 | OLD/2697 服务端线常量(187/1162/0x1fffffff;0x01/0x05) | 服务端源码级 `VERIFIED`;客户端**无对应绑定** | **服务端单侧事实**,不得外推 |
| 3 | 2697 新编号(0x03/0x04/0x06)、注册门控、netconst 发布审计 | 服务端 `VERIFIED`;客户端 `BLOCKED` | **不可归因** |
| 4 | 客户端 net-buffer 长度编码(标签 0xC;阈值 128/256/65536) | 客户端 `CONFIRMED`;其余各方未提供等价字节证据 | 客户端自证;不可用于判定他方 |

## 2. 可合理解释为**版本演化**的差异(有双侧或同族证据)

| # | 差异 | 双侧证据 | 演化解释 | 置信 |
|---|---|---|---|---|
| E1 | 服务端编号代际:`0x01/0x05`(legacy) vs `0x02/0x06`(2697) | 2697/07/E3、E2 明确"legacy 回退 0x01/0x05,2697 分支 0x02/0x06";同一样本内可切换 | 同一代码基的**通道换代**,非两个不相关协议 | `CONFIRMED`(服务端侧) |
| E2 | 服务端工具链换代:OLD(ld 2.30,20 节区,无 DYNAMIC_BASE) → 2697(ld 2.47,11 节区,`.eh_fram`,DYNAMIC_BASE) | 2697/03_BINARY_DIFF §1 | 构建配置整体换代 | `VERIFIED` |
| E3 | 客户端二进制时间戳 `0x6096930A`(2021-05) vs 客户端 DLL `0x5E551315`(2020-02) | 本任务 PE 头 | DLL 早于主 EXE,属**同包内不同期组件**,非协议差异本身 | `CONFIRMED` |
| E4 | OLMod 记录 CODREF:"CODOL 0x005A5960 使用序列标志 0x80000000/0x40000000/0x20000000,分片头为 index,last-index,1154 步长,payload length;不是旧 qport/start/length 布局" | OLMod `net_chan_mp.cpp:692-695`(CODREF) | 与 CoD4x `fragmentStart(MSG_ReadLong)/fragmentLength(MSG_ReadShort)` 的**旧布局**相比,CODOL 分片头**已换代** | `ARCHITECTURAL_ANALOGY`(OLMod 声明层) |

> E4 说明:**若** OLMod 的 CODREF 准确,则 CODOL 分片头与 CoD4x 的 `start/length` 布局是**版本演化**关系。
> 但本任务**未能用现有客户端证据独立复现 1154** —— 045 在节区 #1 找到多个 `1154/1162` 立即数候选
> (见 `evidence/p01_fragment_constants.txt`、`p02_fragment_context.txt`),**均未绑定到 netchan 调用链**。
> 故 E4 记为**有据推断**,不作 `CONFIRMED`。

## 3. 仍存在**竞争性解释**的差异(必须并列保留)

### C1. 分片步长 `1154`(OLMod)对 `1162`(OLD `codol_wire.h`)

- **解释 α(版本演化):** CODOL 客户端 vs OLD 服务端属不同代;步长在代际间改变。
- **解释 β(单一来源错误):** 两者其一(或两者)是重建/推断值,并非从最终版客户端读出。
- **反证:** 本任务未在客户端镜像中把任一数值绑定到分片头构造;045 的立即数命中的是 `0x69D1B0` 一带的**成表返回值**
  (`mov eax,0x482; ret`)与其它无关函数,不构成 netchan 证据。
- **裁定:** `UNKNOWN`(竞争性解释未消解)。关闭条件:在客户端定位分片头写入者并读出步长。

### C2. 消息编号语义:OLD/2697 的 `svc_*` 与 IW4x/CoD4x 枚举

- **解释 α:** CODOL 的编号沿用/派生自 iw4/CoD4x,但版本不同 → 编号偏移。
- **解释 β:** CODOL 在 OLD 中已重新定义(`svc_enum` 与 `wire` 字节**不混用**;2697/04 明确警告不能混用枚举序与实际字节)。
- **裁定:** `UNKNOWN`。无论 α/β,**都不能**用枚举相同来认定协议相同。

### C3. `0x85D96E` 解码函数的层次归属(业务 vs 平台)

- 045 已证明收包链:`socket → select+recv(0x87BE00) → 长度 → 0x87D5A0`。
- **解释 α(业务层):** `0x85Dxxx` 簇直接服务游戏业务消息。
- **解释 β(平台层):** 与 042 的 TQOS `0x85E6F0`(同样调用 thunk `0x87BA50`)同属平台 QoS,业务另有调用者。
- **反证:** 045 找到**两个** thunk 调用者(`0x85D96E`、`0x85E71A`),分属不同函数;`0x85E71A` 明确在 TQOS 分派器内,`0x85D96E` 所在函数尚未定性。
- **裁定:** `UNKNOWN`。关闭条件:判定 `0x85Dxxx` 函数的上游业务调用者。

### C4. 045 新证与 044 旧判的冲突(已裁定,记录用)

- 044 判 `0x87BE00`"更像文件读"(BE-01,`UNKNOWN/BLOCKED`)。
- 045 用**槽序号身份** + **参数布局** + **WSA 错误域**三项独立证据判为 `select`+`recv`。
- **裁定:** 045 **推翻** 044 的 C4;`H2` = `REJECTED`。044 的文件**不改写**,差异并列保留于 `08_NEXT_ACTION_DECISION.md` 的勘误段。

## 4. 方法论风险(本任务实际遇到并已规避)

本项目族**反复出现 VA/RVA 混用**,已造成两处独立误判:

1. **040–044(客户端 EXE):** 把绝对 VA `0x0CA84E8` 当 RVA,误判"超出 EOF" → 阻断项 A-01 长期挂起。**045 已纠正。**
2. **2697 项目:** 其 `08_CLIENT_OPCODE_DISPATCH_TRACE/F4_ADDRESS_AND_IMAGE_VALIDITY.md` 明确记录曾把 VA `0x5AC1D0` 当 RVA,"否则会得到错误的无调用者/错位入口结论"。

**结论:** 任何"无调用者/无引用/超出 EOF"的**否定性结论**,必须先声明地址空间(RVA 还是 VA),再做全空间双形式核对。
本任务对 `0x87BA50`/`0x87BE00` 的调用者扫描已**同时按 VA 形式与裸 RVA 形式**核对(见 `evidence/m01_callers.txt`)。

## 5. 因果链总结

```
  版本演化(可解释):  CoD4x start/length 分片  --->  CODOL index/last-index/stride/length (OLMod CODREF, 推断)
  服务端代际(可解释): legacy 0x01/0x05/0x02/0x03  --->  2697 0x02/0x06/0x03/0x04 (服务端 VERIFIED)
  竞争性(未决):      1154 (OLMod)  <==?>  1162 (OLD codol_wire.h)   [客户端未裁决]
  竞争性(未决):      0x85Dxxx 业务层  <==?>  平台层(TQOS 邻近)
  已裁定:            H1 select+recv (CONFIRMED)   推翻   H2 ReadFile (REJECTED)
```
