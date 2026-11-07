# CODOL-ISSUE-0012 — `dwRoomMatch::Init` 从未被调用（MyEventHandler 零实例）

> 深度取证档案 · 2026-10-29
> **★ 2026-10-29 更新（E1 1359 MB 转储）：本轮 `memberCount=0`，因此未取得新证据，
> 但独立复现了 `dwRoomMatchUber` 堆实例为 0，并否证了"存在第二条创建路径"。**
> 详见 `run_codol_001\runs\E1_20261029_103001\DUMP_FORENSICS.md §3`。

---

## 01. 问题基本信息

| 项 | 值 |
|---|---|
| Issue ID | `CODOL-ISSUE-0012` |
| 完整标题 | `dwRoomMatch::Init()` 从未执行，导致局部类 `MyEventHandler` 零实例，建房回调 `0x63B500` 永不被调用 |
| 所属系统 | `lobby` / 客户端房间子系统 |
| 优先级 | **P0** |
| 当前状态 | `OPEN` |
| 首次发现 | 2026-10-27（`EARLIEST_20261027_123806` 转储分析） |
| 最近验证 | 2026-10-27 12:38（转储 `snap_002`, t=79.7 s） |
| 首次发现任务 | `GATE_B_INIT_PATH_20261027` |
| 最近调查任务 | 本任务（仅复核，未新增转储） |
| 客户端版本 | 3.19.26.22 / 1649370 |
| 服务端版本 | 不适用（纯客户端问题） |
| Git | UNKNOWN |
| 阻塞可玩战斗 | 是（房间入口） |
| 上游依赖 | 无（本 Issue 是最上游可观测点） |
| 下游依赖 | ISSUE-0013（状态机停状态 1）、ISSUE-0009（准备按钮）、ISSUE-0020（房间入口连接） |

**版本区分**：全部证据来自 3.19 运行期转储。`0x63B500` 等地址**仅对 3.19 / 1649370 有效**。

---

## 02. 问题的精确定义

**预期行为**
进入大厅/房间阶段时，引擎调用 `dwRoomMatch::Init()`；该函数定义局部类 `MyEventHandler`
并实例化它注册事件监听；当服务端返回 createRoom 后，`MyEventHandler` 的 slot[1]
（`0x63B500`）被调用 → `0x63E510` 创建 `dwRoomMatchUber` → 自动开局状态机开始跑。

**实际行为**
在 1,478 MB 全量转储中搜索 vtable `0x00DC78F0`（`MyEventHandler` 的 vtable）的实例：**0 个**。

**偏差**
链在**第一环**就断了：不是"建房失败"，是"从未尝试建房"。

**失败边界（逐层）**

| 层 | 结论 | 证据 |
|---|---|---|
| 引擎是否调用 `dwRoomMatch::Init` | ❌ **FIRST_UNPROVEN_EDGE** | 无实例即无执行 |
| `MyEventHandler` 是否创建 | ❌ 0 实例 | 转储扫描 |
| `0x63B500` 是否被调用 | ❌ 不可能 | 依赖上一步 |
| `0x63E510` 是否执行 | ❌ | `[0x82E1514]` 有**无条件写**在分配前（`0x63E5D6`），实测为 0 ⇒ 函数体一句都没跑 |
| `dwRoomMatchUber` 是否创建 | ❌ `[0x82E1518] = 0`（修复前） | 转储 |

---

## 03. 历史发现过程

| 日期 | 任务/转储 | 观察 | 假设 | 结果 |
|---|---|---|---|---|
| 2026-10-27 上午 | `MEMDUMP_20261027_v4` | `[0x82E1518]=0` | "dwRoomMatchUber 从未创建" | 成立 |
| 2026-10-27 | 同上 | 闸门 B = `[dwRoomImp+0x10614]` 恒 0 | "闸门 B 是根因" | **部分推翻**（属不同类） |
| 2026-10-27 12:38 | `EARLIEST_20261027_123806/snap_002`（1478 MB） | vtable `0x00DC78F0` 零实例 | "Init 未调用" | **成立** |
| 2026-10-27 13:27 | `EARLIEST2_20261027_132645` | `memberCount` 0→1 后 `[0x82E1518]=0x3ACA0CD8` | "memberCount 是闸门" | 成立（对象出现）但仍未连接 |
| 2026-10-28 | `READY_BUTTON_ROOT_CAUSE_CLOSED` | 符号层确认 `MyEventHandler` 是 `Init` 的局部类 | 独立复核 | 成立 |

**★ 关键**：`memberCount=1` 之后 `dwRoomMatchUber` **出现了**，
但 `MyEventHandler` 的零实例问题**没有被重新测量**。
即：**`Init` 是否仍然没被调用，在 memberCount 修复之后是 UNKNOWN。**

这是本档案最重要的未决点。

---

## 04. 原始证据清单

| Evidence ID | 类型 | 路径 | 状态 | 能证明 | 不能证明 |
|---|---|---|---|---|---|
| EV-0012-01 | 内存转储 | `run_codol_001\runs\EARLIEST_20261027_123806\snap_002.bin`（1478.5 MB，t=79.7 s，失败块 0） | **存在** | vtable `0x00DC78F0` 零实例 | 修复后是否仍为零 |
| EV-0012-02 | 覆盖图 | `…\snap_00k_cover.bin` | 存在 | 每字节是否真读到 | — |
| EV-0012-03 | 时序日志 | `…\log.txt` | 存在 | 句柄 t+15.23 s，首读 `4d5a9000` | — |
| EV-0012-04 | 转储 | `run_codol_001\runs\EARLIEST2_20261027_132645\snap_003/004`（各 1630 MB） | 存在 | memberCount 修复后 dwRoomMatchUber 出现 | `MyEventHandler` 实例数（**未测**） |
| EV-0012-05 | 分析文档 | `docs\GATE_B_INIT_PATH_20261027.md` | 二手 | 完整因果链 | — |
| EV-0012-06 | 符号证据 | 同上 §"第三层"：`0x63B500` 在常量区只出现于 `0x00DC78F0` | 二手 | vtable 归属 | — |

**MISSING_PRIMARY_EVIDENCE**：修复后（10-27 14:04 之后）**没有任何一次转储重新统计 `0x00DC78F0` 实例数**。

---

## 05. 源码级定位

不适用（客户端二进制问题）。服务端侧只有一个相关点：

`lobby_server.py:1002` —— `11/13 createRoom` 应答：
```python
ob.u64(ROOM_ID); ob.u32(1); ob.u32(1); ob.u64(ROOM_SECOND_ID)
ob.bool_(False); ob.bool_(False); ob.u32(1)
```
| 项 | 值 |
|---|---|
| 输入 | `11/13` |
| 输出 | 37 B 对象 |
| 与 Issue 的关系 | 该应答触发了 `dwRoomMatchUber` 创建；但**没有触发 `MyEventHandler`** |

---

## 06. 客户端逆向定位

| 项 | 值 |
|---|---|
| 映像 | `codoMP_client_shipRetail.exe` 7,841,344 B / `36997674…b537` |
| ImageBase | `0x00400000`；DllCharacteristics `0x8100`（**无 ASLR**） |

| 符号/函数 | VA | RVA | 证据 | 已证实 | 未证实 |
|---|---|---|---|---|---|
| `MyEventHandler` vtable | `0x00DC78F0` | `0x9C78F0` | 常量区唯一引用 | 归属确定（RTTI `. ?AVMyEventHandler@?5??Init@dwRoomMatch@@SAXXZ@`） | 是否有实例（修复后） |
| `0x63B500` 建房回调 | `0x0063B500` | `0x23B500` | vtable slot[1] | 是 `MyEventHandler` 虚函数 | 调用条件 |
| `dwRoomMatchUber` vtable | `0x00DC795C` | `0x9C795C` | RTTI | 确认 | — |
| 自动开局状态机 | `0x0063C5E0` | `0x23C5E0` | vtable +0x68 | 属 `dwRoomMatchUber` | 是否被调用 |
| `dwRoomImp` vtable | `0x00DC7274` | `0x9C7274` | RTTI | 闸门 B 在其 +0x64 | — |
| 创建函数 | `0x0063E510` | `0x23E510` | 反汇编 | `0x63E5D6` 有无条件写 | 调用者 |

**关键反汇编（无条件写，用来判定"函数是否执行过"）**
```asm
0063E510  ...
0063E5D6  mov [0x82E1514], ecx     ← 在分配(0x63E5DC)之前，无条件
0063E5DC  ...（分配）
```
实测 `[0x82E1514] = 0` ⇒ **函数体一句都没执行**。

**陷阱检查**

| 陷阱 | 是否踩到 |
|---|---|
| RVA/VA 混淆 | 否（转储按模块基址展开，本档案给的是 VA 与 RVA 两份） |
| 跨版本地址混用 | 否（全部 3.19） |
| TQOS/TDR 误认 | 否 |
| 静态字符串≈执行 | 否（用"无条件写"判定，不用字符串） |
| 套用外部结构 | 否 |

**FIRST_UNPROVEN_EDGE**：引擎在什么条件/时机调用 `dwRoomMatch::Init()`。

---

## 07. 网络协议级定位

不直接适用。相关协议点：`11/13` 应答（见 §05）与 `6/5` 订阅（ISSUE-0017）。
本 Issue 判定：**即使 `11/13` 完全正确，若 `Init` 未被调用，建房回调仍不会触发**。

---

## 08. 数据流与调用链

```
[引擎初始化房间子系统]
   │                                     UNKNOWN ← ★ FIRST_UNPROVEN_EDGE
   ▼
[dwRoomMatch::Init()]                    CONTRADICTED（MyEventHandler 零实例）
   │
   ▼
[MyEventHandler 实例化 + 注册监听]        CONTRADICTED
   │
   ▼
[11/13 createRoom 应答到达]              PROVEN（服务端确实发了）
   │
   ▼
[0x63B500 被调用]                        CONTRADICTED
   │
   ▼
[0x63E510 → 创建 dwRoomMatchUber]        PROVEN **在 memberCount=1 后**（EV-0012-04）
   │
   ▼
[自动开局状态机 0x63C5E0]                PROVEN 存在；停在状态 1
```

**⚠️ 这条链有一个内部矛盾**：如果 `MyEventHandler` 零实例导致 `0x63B500` 不被调用，
那么 `0x63E510` 也不该执行——但 `memberCount=1` 之后 `dwRoomMatchUber` **确实出现了**。

**可能的解释（必须验证）**：
- (a) `dwRoomMatchUber` 由**另一条路径**创建（不经过 `0x63B500`）；
- (b) `memberCount=1` **也**让 `MyEventHandler` 出现了（即 `Init` 被调用了）；
- (c) 修复后的转储里 `MyEventHandler` 其实非零，只是**没人去测**。

**这是本 Issue 最关键的技术疑点**，见 §09 的 H0。

---

## 09. 根因分析

| Hypothesis | 解释 | 支持 | 反对 | 状态 |
|---|---|---|---|---|
| **H0** 修复后 `MyEventHandler` 其实已有实例 | `memberCount=1` 同时触发 `Init` | `dwRoomMatchUber` 出现了 | 从未重测 | **必须最先验证** |
| **H1** `Init` 依赖某条大厅应答，该应答未发 | 前置数据缺失 | 用户假设（"大厅功能缺损"） | 未指向具体应答 | 中可信 |
| **H2** `Init` 依赖游戏内某状态（非网络） | 如进入某个 UI 页 | — | 无证据 | 低可信 |
| **H3** `Init` 在加密节，调用点静态不可见 | `.tp3` VSize 219 MB / RawSize 401 KB | 属实 | 不影响运行时判定 | 事实，非根因 |

**裁决**：H0 未排除之前，**不能宣布"Init 未调用"是当前状态的根因**。
10-27 的零实例结论对应的是 **memberCount=0 的那一版**。

---

## 10. 历史修复尝试

| 时间 | 改动 | 结果 |
|---|---|---|
| 2026-10-27 14:04 | `memberCount` 0→1 | `dwRoomMatchUber` 出现；`MyEventHandler` **未重测** |
| 2026-10-28 | 无 | — |

---

## 11. 当前代码状态

服务端侧无相关代码。客户端侧：`Init` 的调用点仍未知。

---

## 12. 精准复现方法

**取证型复现（不是行为复现）**：

1. 用当前正式 kit 启动客户端（需授权）
2. 用 `CODOLServer/_mainline/dump_earliest.py <outdir> 200 6` 在**早期窗口**内抢句柄
3. 拿到 `snap_00N.bin`
4. 扫描 vtable `0x00DC78F0` 的实例数（注意按模块基址换算）
5. 同时扫描 `0x00DC795C`（`dwRoomMatchUber`）作**阳性对照**

**预期**：若 H0 成立，`0x00DC78F0` 实例数 ≥ 1。

> ⚠️ 窗口限制：建房在 t≈80–100 s，而早期窗口约 t≈24 s。
> 因此**必须在建房前抓到 `Init` 的实例化时刻**，或在建房后另找可读窗口（见 ISSUE-0045）。

---

## 13. 最小验证实验

**实验 E6（重测 MyEventHandler）**

| 项 | 内容 |
|---|---|
| 变量 | 无（只做测量，不改行为） |
| 输入 | 当前正式 kit 的一次转储（`snap_003`/`snap_004`，建房后） |
| 通过判据 | `0x00DC78F0` 实例数 ≥ 1 ⇒ H0 成立，本 Issue 作废 |
| 失败判据 | 实例数 = 0 且 `dwRoomMatchUber` 非零 ⇒ **存在第二条创建路径**（重大发现） |
| 成本 | 1 次转储（已有工具） |

---

## 14. 修复方案

**根因未定 ⇒ 不提供补丁。**

若 E6 证明 H0：本 Issue 关闭。
若 E6 证明存在第二条创建路径：改写整个"房间链"的因果图，本 Issue 降级。

---

## 15. 修复影响分析

本 Issue 本身无代码可改，影响分析见其下游（ISSUE-0013 / 0009 / 0020）。

---

## 16. 验收标准

**取证型验收**（本 Issue 是诊断问题，不是功能问题）：

1. 有一份建房**之后**的转储
2. 其中 `0x00DC78F0` 实例数被明确统计（0 或 ≥1）
3. 同转储里 `0x00DC795C` 实例数作为阳性对照被统计
4. 两者关系被写入文档

---

## 17. 回归测试

| 测试 | 证明 | 不能证明 |
|---|---|---|
| E6 | `MyEventHandler` 当前是否存在 | 它为什么存在/不存在 |
| — | — | — |

---

## 18. 最终技术结论

**当前状态**：`OPEN`。证据仍陈旧；本轮（memberCount=0）无法回答。

**已经证明的事实**：
1. 在 memberCount=0 的那次运行里，`MyEventHandler` 零实例（2026-10-27）。
2. `0x63B500` 是该 vtable 的 slot[1]。
3. memberCount=1 之后 `dwRoomMatchUber` 确实出现过（`EARLIEST2_20261027_132645`）。
4. **2026-10-29 E1 转储（memberCount=0）独立复现**：
   `dwRoomImp` 有 1 个堆实例（`0x3EAEA240`），`dwRoomMatchUber` 与 `MyEventHandler` **堆实例均为 0**；
   `0x63BCD1`/`0x63C014` 只是代码中的 vtable 引用，不是实例。
   ⇒ **在 memberCount=0 的进程里没有任何"第二条创建路径"**。

**尚未证明的事实**：
- memberCount=1 状态下 `MyEventHandler` 是否存在（2026-10-29 仍未测）。
- 若不存在，`dwRoomMatchUber` 经由哪条路径创建。

**第一条未闭合证据链**：`memberCount=1` → `dwRoomMatchUber 出现` 之间缺一环。

**当前最可信根因**：**无法给出**。原结论与 EV-0012-04 的矛盾仍未解。

**下一步最小实验**：E6 —— **必须在 memberCount=1 的 kit 上重跑转储**。
本轮 E1 已证明转储工具链可用（句柄 t=97 s、快照 1359 MB、覆盖建房后 73 秒），
所以 E6 只差"换 kit"这一步。

**最小修复条件**：E6 的结果。

**完成验收标准**：§16。

**是否可以交给开发 Agent 直接修复：NO**
必须先完成：**E6（memberCount=1 + 转储重测）**。
工具障碍已解除，仅剩 kit 版本问题。

---

## 19. 修改影响分析

见 §15。

## 20. 可测量的验收标准

见 §16。

## 21. 回归测试方案

见 §17。

## 22. 修复准备度

**INVESTIGATION_READY**

- **下一步**：E6：必须在 memberCount=1 的 kit 上重跑转储并统计 0x00DC78F0 实例数。
- **上游依赖**：见 §01
