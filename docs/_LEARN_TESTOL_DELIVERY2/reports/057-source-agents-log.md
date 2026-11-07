# 学习报告 057（重开）— `source\AGENTS.md`（20,629 B）验收日志

**学习范围**：`source\AGENTS.md` 前 110 行（按日期倒序的验收记录）
**性质**：全实测
**★★★ 本报告揭示**ol-mod 的验收方法论**与**持续未解决的问题清单**

---

## 一、★★★★★ 文件的真实性质

```markdown
# Factory teleporter links and staged return accepted — October 2
```

★★★ **⇒ `AGENTS.md` 不是"Agent 约束"，而是**按日期倒序的验收日志**。**

★ **⇒ 每条记录的结构完全相同：**
```
# <功能名> accepted — <日期>
<英文摘要：测试了什么 + 通过了什么 + 未验证什么>
<中文摘要（逐句对应英文）>
<具体开关 + 证据链接>
```

★★ **⇒ 中英双语**逐条对照** —— 说明是给两类读者看的。**

---

## 二、★★★★★ 一条完整记录的结构（第 1–26 行，逐字）

### 2.1 标题（第 1 行）

```markdown
# Factory teleporter links and staged return accepted — October 2
```

### 2.2 ★★★ 英文摘要（第 3–9 行，逐字）

```
Based on upstream c52b156 (complete dual-wield behavior), with no newer upstream
commit at final review. Factory solo and simultaneous two-player staged travel
playtests passed; the same gameplay binary passed two-real-client Nuketown FFA.
Release, seven suites, 50ms server regression, 223-review partial source audit,
four audit-validator tests and frozen gameplay/source identity checks passed.
Simultaneous travel used explicit debug godmode; that run does not validate damage
or revival. No new long-session performance claim or recovered paid-travel claim.
```

### ★★★★★ 七类验收项

| # | 验收项 | 内容 |
|---|---|---|
| **1** | **上游基线** | **`c52b156`**（complete dual-wield behavior），"no newer upstream commit" |
| **2** | **Factory 单人 + 双人 staged travel** | playtests **PASS** |
| **3** | **同构建 Nuketown FFA** | 两真实客户端 **PASS** |
| **4** | **Release 构建** | PASS |
| **5** | **七个套件（seven suites）** | PASS |
| **6** | **50ms 服务器回归** | PASS |
| **7** | **223 条部分源码审计** | PASS |
| **8** | **四个 audit-validator 测试** | PASS |
| **9** | **冻结 gameplay/source 一致性检查** | PASS |

★★★ **⇒ **九项验收**，其中三项有精确数字：**
```
223-review partial source audit
four audit-validator tests
50ms server regression
```

### ★★★★★ 明确声明的"未验证"（第 8–9 行）

```
Simultaneous travel used explicit debug godmode; that run does not validate damage
or revival. No new long-session performance claim or recovered paid-travel claim.
```

★★★ **⇒ 三条**明确的免责声明**：**
```
① 双人传送用了**显式 debug 无敌** ⇒ **不验证伤害/救援**
② **不声称**修复了长期性能
③ **不声称**恢复了付费传送脚本
```

★★ **⇒ 这是**极高质量的验收记录**（明确区分"验证了什么"与"未验证什么"）。**

### 2.3 ★★★ 具体开关（第 11–16 行）

```
`OLMOD_FACTORY_TELEPORTERS=1` (with INTERACTABLES) adds shared pad/core linking,
initiator-only native stopwatch, machine power presentation and phased PAP access
gate. `OLMOD_FACTORY_BO1_TELEPORT_TRAVEL=1` separately opts into BO1-derived staged
return travel: charge, per-player effect rooms and safe mainframe arrivals.
The combined change also retains helper-only treatment progress/movement lock and
corrects the loopback-only opt-in battery key to the focused player (default F6).
```

★★★ **⇒ 两个开关 + 六个功能点：**
```
OLMOD_FACTORY_TELEPORTERS=1          （需配合 INTERACTABLES）
  ├─ shared pad/core linking
  ├─ initiator-only native stopwatch
  ├─ machine power presentation
  └─ phased PAP access gate

OLMOD_FACTORY_BO1_TELEPORT_TRAVEL=1  （BO1 衍生）
  ├─ charge
  ├─ per-player effect rooms
  └─ safe mainframe arrivals
```

★★ **⇒ 且提到**电池键默认 `F6`**（`loopback-only opt-in battery key`）。**

### 2.4 ★★★ 证据链接（第 17–18 行）

```markdown
Read [link evidence](.agents/research/factory-teleporter-links-20260929.md) and
[staged travel evidence](.agents/research/factory-bo1-travel-20261001.md).
```

★★ **⇒ 每条验收都有**对应的研究文档**（在 `.agents/research/`）。**

### 2.5 ★★★ 边界声明（第 19–21 行，逐字）

```
Native assets/consumers are distinguished from reconstructed timing/selection.
PAP weapon upgrading and peripheral travel steam/heat-sink choreography remain
outside this contribution. Launchers, binaries, media and IDBs remain excluded.
```

★★★ **⇒ 三条边界：**
```
① **原生资产/消费者** 与 **重建的时序/选择** 严格区分
② PAP 武器升级 + 周边蒸汽/散热片编排 **不在本次贡献内**
③ ★★ **启动器、二进制、媒体、IDB 都不提交**（"remain excluded"）
```

★★ **⇒ 第 ③ 条与 `source\README.md` 的"不含"清单**一致**。**

### 2.6 ★★ 中文摘要（第 23–26 行）

```
Factory传送连接与分阶段回传已通过单人、双人以及同构建Nuketown FFA验收。
独立开关启用BO1衍生重建，不声称恢复CODOL原版付费传送脚本；原生消费者与重建
策略分别记录。双人传送使用测试无敌，不冒充伤害/救援验证。升级武器及周边蒸汽效果
尚未包含；自动检查与冻结源码一致性通过，不提交本地启动工具或原生资源。
```

★★★ **⇒ 中文摘要是英文的**逐句对应翻译**（信息完全一致）。**

★ **⇒ 且用词精确：**"不声称"、"不冒充"。**

---

## 三、★★★★★ 六条验收记录的时间线（9/25 – 10/2）

| 日期 | 标题 | 核心功能 |
|---|---|---|
| **Oct 2** | Factory teleporter links and staged return | 传送器 + BO1 分阶段回传 |
| **Sep 29** | Factory cooperative revival and arrival hold | 合作救援 + 入场锁定 |
| **Sep 27** | Local Factory co-op and held weapons | 合作 + 手持武器 |
| **Sep 27** | Factory special rewards | 特殊奖品（Ray Gun/Wunderwaffe） |
| **Sep 26** | Factory mystery box | 神秘箱 |
| **Sep 25** | Factory perks, ammo and battery HUD | 技能机 + 弹药 + 电池 HUD |

★★★ **⇒ 六条记录，全部围绕 **Factory（僵尸工厂）** —— 这是**主要开发方向**。**

★ **⇒ 时间跨度 **9/25 – 10/2**（8 天，6 次验收）。**

★★ **⇒ 每次验收都包含**七项套件 + Release + 50ms 回归 + 源码审计**（条目数递增：171 → 187 → 194 → 196 → 202 → 223）。**

---

## 四、★★★★★ 持续未解决的问题（逐条收集）

### 4.1 ★★★ Factory 帧耗时（多次提及）

**Sep 27（special rewards）**：
```
A severe Factory slowdown remains open:
late average frame138ms, primarily begin/end phases, already slow before
Tesla equip. No root cause or performance fix established.
```

**Sep 27（local co-op）**：
```
Known long-session slowdown is not fixed.
```

★★★ **⇒ 一个**持续未解决的严重性能问题**：**
```
Factory 后期平均帧 **138 ms**
        ↓
主要在 **begin/end 阶段**
        ↓
★ **在装备 Tesla 之前就已经慢**
        ↓
★★★ **无根因、无修复**
```

★★ **⇒ 且明确："不得描述为性能修复"。**

### 4.2 ★★ 其他未完成项（Sep 27 local co-op）

```
Remote admission, special/dual-hand weapon presentation, reconnect/revive and
empty-server lifecycle remain open.
```

★★ **⇒ 四项未完成：**
```
① 远程准入（remote admission）
② 特殊/双持武器表现
③ 重连/复活
④ 空服生命周期
```

### 4.3 ★★ PAP 与传送器（Sep 26）

```
Teleporters, Pack-a-Punch, upgrade registration and experimental special-reward
combat are excluded and preserved separately.
```

★ **⇒ 当时（9/26）被排除的三项，到 10/2 已实现传送器（`OLMOD_FACTORY_TELEPORTERS`）。**

★★ **⇒ 说明这些是**分阶段交付**的。**

---

## 五、★★★★ 验收方法的完整模板（从六条记录提炼）

### ★★★★★ 每次验收的九个步骤

```
① 确认上游基线（commit hash）
② 功能 playtest（单人 / 双人）
③ 同构建 Nuketown FFA（两真实客户端）
④ Release 构建
⑤ 七个套件（seven suites）
⑥ 50ms 服务器回归
⑦ N 条部分源码审计（171 → 223，递增）
⑧ audit-validator 测试
⑨ 冻结 gameplay/source 一致性检查
```

★★★ **⇒ 这是一个**极其严格的验收流程**（九项全过才算 accepted）。**

★★ **⇒ 且**每次都要"同构建 Nuketown FFA"** —— 用一张标准图做回归基准。**

★ **⇒ 源码审计条目数**递增**（171 → 187 → 194 → 196 → 202 → 223）⇒ 覆盖面逐步扩大。**

---

## 六、★★★ 关键开关清单（从六条记录收集）

| 开关 | 引入日期 | 功能 |
|---|---|---|
| `OLMOD_FACTORY_INTERACTABLES=1` | **Sep 26** | 神秘箱生命周期 |
| `OLMOD_FACTORY_TELEPORTERS=1` | **Oct 2** | 传送器连接 |
| `OLMOD_FACTORY_BO1_TELEPORT_TRAVEL=1` | **Oct 2** | BO1 分阶段回传 |
| `OLMOD_ZM_COOP_REVIVE=1` | **Sep 29** | 合作救援 |
| `OLMOD_FACTORY_ENTRY=1` | **Sep 29** | 入场 **3100ms** 移动锁定 |
| `OLMOD_ZM_COOP_SPAWN_ZONES=1` | **Sep 27** | 合作区域并集刷怪 |

★★ **⇒ 六个开关，全部是 `OLMOD_FACTORY_*` / `OLMOD_ZM_*` 前缀。**

★ **⇒ 与报告 026 的 126 个 `CodolGameServer` 变量**部分重合**（`OLMOD_FACTORY_*` 系列）。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ 文件性质 | **按日期倒序的验收日志**（不是约束文档） |
| 2 | ★★ 语言 | **中英双语**（逐条对照） |
| 3 | 记录数（前 110 行） | **6 条** |
| 4 | 时间跨度 | **2026-09-25 – 2026-10-02** |
| 5 | ★★★ 上游基线 | **`c52b156`**（complete dual-wield behavior） |
| 6 | ★★★ **九项验收** | 基线 / 功能 playtest / 同构建 FFA / Release / 七套件 / 50ms 回归 / 源码审计 / audit-validator / 冻结一致性 |
| 7 | ★★ 源码审计条目数 | **171 → 187 → 194 → 196 → 202 → 223**（递增） |
| 8 | ★★★ **免责声明** | 双人用 **debug 无敌** ⇒ 不验证伤害/救援；不声称性能修复；不声称恢复付费脚本 |
| 9 | ★★★ **持续未解决** | **Factory 后期平均帧 138ms**，无根因无修复 |
| 10 | ★ 其他未完成 | 远程准入 / 双持武器 / 重连复活 / 空服生命周期 |
| 11 | ★★ 六个开关 | `FACTORY_INTERACTABLES` / `FACTORY_TELEPORTERS` / `FACTORY_BO1_TELEPORT_TRAVEL` / `ZM_COOP_REVIVE` / `FACTORY_ENTRY` / `ZM_COOP_SPAWN_ZONES` |
| 12 | ★ `FACTORY_ENTRY` 参数 | **3100ms** 移动锁定 |
| 13 | ★ 电池键默认 | **`F6`** |
| 14 | ★★ 证据链接 | 每条记录都有 `.agents/research/*.md` |

---

## 八、结论

### 1. ★★★★★ **`AGENTS.md` 是验收日志**，不是约束文档

★ **⇒ 六条记录，全部围绕 **Factory（僵尸工厂）**。**

### 2. ★★★★★ **九项验收流程极其严格**

```
上游基线 → 功能 playtest → 同构建 FFA → Release → 七套件
→ 50ms 回归 → N 条源码审计 → audit-validator → 冻结一致性
```

### 3. ★★★★★ **免责声明是最高质量的工程实践**

```
双人用 debug 无敌 ⇒ **明确声明不验证伤害/救援**
        ↓
★ 不把"能跑通"当成"功能正确"
```

### 4. ★★★★ **Factory 后期 138ms 帧耗时是持续未解决的严重问题**

★ **⇒ "无根因、无修复"，且明确"不得描述为性能修复"。**

### 5. ★★★ **源码审计条目数递增**（171 → 223）⇒ 覆盖面逐步扩大

### 6. ★★ **六个 `OLMOD_FACTORY_*` / `OLMOD_ZM_*` 开关**

---

## 九、下一步

- `source\AGENTS.md` 剩余（第 110 行起，约 300 行）
- `source\AGENTS-OLFINAL.md`（18,677 B）
- `source\.agents\modules\`（4 个模块文档）
- `source\docs\devlog\`（中文开发历程）
- `source\tools\runtime\CodolGame.py`
