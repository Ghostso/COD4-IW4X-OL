# 学习报告 056（重开）— `source\` 结构与 `README.md` 逐字节

**学习范围**：`source\` 的完整目录结构 + `source\README.md`（3,487 B / 66 行）
**性质**：全实测
**★★★ 本报告揭示**ol-mod 的完整职责划分**与**"兼容名不能改"的 ABI 原因**

---

## 一、★★★★★ `source\` 的完整规模（实测）

| 目录 | 文件数 | 体积 |
|---|---|---|
| **`build\`** | **221** | ★★★ **140.71 MB** |
| `docs\` | **75** | **15.74 MB** |
| **`src\`** | **286** | **15.05 MB** |
| `tools\` | **148** | **5.39 MB** |
| `assets\` | 55 | 3.15 MB |
| `tests\` | 24 | 2.20 MB |
| `distribution\` | 7 | 1.47 MB |
| `.agents\` | 59 | 0.92 MB |
| `runtime-assets\` | 15 | 0.25 MB |
| `references\` | 12 | 0.22 MB |
| `.xmake\` | 11 | 0.04 MB |
| `config\` | 3 | 0.00 MB |

### ★★★ 合计

```
目录总计 : 916 文件 / 185.14 MB
+ 11 个根文件
---
927 文件（与报告 001 的实测一致）
```

★★★ **⇒ `build\` 占 **140.71 MB（76%）** —— 而 `README` 说它"没有附带"（报告 011/012 已记录）。**

★ **⇒ 真正的源码（`src\`）只有 **15.05 MB**。**

---

## 二、★★★★★ `src\` 的六个子目录（实测）

| 子目录 | 文件数 | 体积 |
|---|---|---|
| **`game_server\`** | **196** | **14.20 MB** |
| `backend\` | 65 | 0.65 MB |
| `shared\` | 10 | 0.11 MB |
| `localnetworking\` | 6 | 0.07 MB |
| `platformwrapper\` | 7 | 0.02 MB |
| **`client_bridge\`** | **2** | **0.01 MB** |

★★★ **⇒ `game_server` 占 **14.20 / 15.05 = 94.4%** —— 战斗服是绝对主体。**

★ **⇒ `client_bridge\` 只有 2 个文件（README 未提，报告 011 已发现）。**

---

## 三、★★★★★ `source\README.md` 的目录职责表（第 7–22 行，逐字）

```text
src/backend/              DW3 控制面插件
src/game_server/          游戏服务器与协议实现
tests/                    对应模块的自动化测试和 fixtures
assets/backend/1004/      CODOL 后端资产
assets/profile_seed/1004/ 原版初始玩家状态，仅缺失时安装
distribution/             CODOL-only x86 分发契约与闭源兼容组件
tools/runtime/            运行时观察和原生客户端流程自动化
tools/distribution/       干净 staging 与保留玩家状态的安装工具
tools/profile/            Profile、库存和商城工具
tools/reverse/            IDA/idalib 分析与注释工具
references/client_probe/  历史客户端伪链路和协议探针
docs/references/          带来源归属的外部文章、翻译和参考资料
docs/devlog/              面向人类读者的中文开发历程
.agents/                  Agent 约束、当前状态和研究文档
```

### ★★★★★ 十二个目录的完整职责

| # | 目录 | 职责 |
|---|---|---|
| **1** | **`src/backend/`** | **DW3 控制面插件** |
| **2** | **`src/game_server/`** | **游戏服务器与协议实现** |
| 3 | `tests/` | 自动化测试和 fixtures |
| 4 | `assets/backend/1004/` | CODOL 后端资产 |
| 5 | **`assets/profile_seed/1004/`** | ★ **原版初始玩家状态，仅缺失时安装** |
| 6 | **`distribution/`** | ★★ **CODOL-only x86 分发契约与闭源兼容组件** |
| 7 | **`tools/runtime/`** | ★★★ **运行时观察和原生客户端流程自动化** |
| 8 | `tools/distribution/` | 干净 staging 与保留玩家状态的安装工具 |
| 9 | `tools/profile/` | Profile、库存和商城工具 |
| 10 | **`tools/reverse/`** | ★★ **IDA/idalib 分析与注释工具** |
| 11 | `references/client_probe/` | 历史客户端伪链路和协议探针 |
| 12 | `docs/references/` | 带来源归属的外部文章、翻译和参考资料 |
| 13 | `docs/devlog/` | ★ **面向人类读者的中文开发历程** |
| 14 | `.agents/` | Agent 约束、当前状态和研究文档 |

★★★ **⇒ 第 6 条揭示了**闭源组件的来源**（见 §五）。**

★★ **⇒ 第 7 条 `tools/runtime/` 就是 `launch_chain.py` 注释里提到的 `CodolGame.py` 所在地。**

★ **⇒ 第 10 条 `tools/reverse/` 有 **IDA/idalib 工具** —— 说明作者用 IDA 做逆向。**

★★ **⇒ 第 13 条 `docs/devlog/` 是**中文开发历程**（`README` 说"面向人类读者"）。**

---

## 四、★★★★★ "兼容文件名不能改"的**完整原因**（第 41–48 行，逐字）

```markdown
构建产物位于 `build/bin/<mode>`。逻辑目标使用新命名：

- `ol_backend` -> `AlwaysofflineRe.Localnet32`
- `ol_game_server` -> `CodolGameServer.Localnet32`

最终兼容文件名暂时不能更改，因为源码化 Localnetworking 的插件发现 ABI
和现有游戏目录仍依赖这些固定名称。

迁入代码中的 `AlwaysofflineRe`、`CodolGameServer` namespace 也暂时原样保留，
以保证首个 xmake 基线可以逐文件验证。后续可在独立、行为不变的提交中逐模块改名，
避免把命名重构与协议修复混在一起。
```

### ★★★★★ 三个关键信息

**① 两个逻辑目标的名字映射**

```
ol_backend      →  AlwaysofflineRe.Localnet32    ← ★★★ 带 Re
ol_game_server  →  CodolGameServer.Localnet32    ← ★ 不带 Re
```

★★★ **⇒ **与 `xmake.lua` 的 `set_filename` **完全一致**（报告 015）。**

**② ★★★ "兼容文件名不能改"的精确原因**

> **因为源码化 Localnetworking 的插件发现 ABI 和现有游戏目录仍依赖这些固定名称。**

★★★ **⇒ 两个依赖方：**
```
① **源码化 Localnetworking 的插件发现 ABI**   ← 它扫 *.Ayria32 / *.Localnet32
② **现有游戏目录**                          ← 已有文件用这些名字
```

**③ ★★ namespace 也保留**

> 迁入代码中的 `AlwaysofflineRe`、`CodolGameServer` namespace 也暂时原样保留，
> 以保证首个 xmake 基线可以逐文件验证。

★★ **⇒ 说明这是**迁移中间态**（保留原名以便逐文件验证）。**

★ **⇒ 且明确："后续可在独立、行为不变的提交中逐模块改名，避免把命名重构与协议修复混在一起。"**

★★★ **⇒ 这是**优秀的重构纪律**（命名重构与功能修复分开）。**

---

## 五、★★★★ `distribution\` 的闭源组件来源（第 52 行，逐字）

```markdown
`build/stage/codol` 是由 manifest 驱动生成的游戏目录 overlay，只包含 title `1004`、
PE32 组件和必要资产。闭源 Injector/Bootstrapper/Platformwrapper 来自已核对的
`ayriax3/1` 原版；Localnetworking、backend 与 game server 使用当前构建产物。
详见 [`distribution/README.md`](distribution/README.md)。
```

### ★★★★★ 组件的来源分类

| 组件 | 来源 |
|---|---|
| **Injector / Bootstrapper / Platformwrapper** | ★★★ **闭源，来自 `ayriax3/1` 原版** |
| **Localnetworking / backend / game server** | **当前构建产物**（ol-mod 自研） |

★★★ **⇒ 这解答了"哪些是原版、哪些是重实现"：**
```
闭源原版：Injector32.exe / Bootstrapper32.dll / Platformwrapper.Ayria32
        ↓
ol-mod 自研：Localnetworking.Ayria32 / Alwaysoffline.Localnet32 / CodolGameServer.Localnet32
```

★★ **⇒ 与报告 053 的 `Re` 后缀**完全对应**：**
```
带 Re  =  ol-mod 重实现（LocalnetworkingRe / AlwaysofflineRe）
不带 Re =  原版闭源（Platformwrapper.Ayria32 —— ★ 但内部名是 PlatformwrapperRe！）
```

★★★ **⇒ 注意矛盾：**
```
README 说 Platformwrapper 是**闭源原版**
但 Platformwrapper.Ayria32 的内部 DLL 名是 **PlatformwrapperRe.Ayria32**（带 Re）
        ↓
★ 说明：**Platformwrapper 也是 ol-mod 重实现**，README 的说法可能过时
```

★ **⇒ 或 `distribution\` 里另有一份闭源原版（`distribution\legacy\Ayria\`）。**

---

## 六、★★★ 安装时的保留策略（第 54–59 行）

```markdown
安装到游戏目录时，已有 `Publicprofile`、`the.json` 和后续运行时创建的
`Inventory.json` 默认不会被覆盖：

```powershell
powershell -ExecutionPolicy Bypass -File .\tools\distribution\InstallCodolRuntime.ps1 `
  -GameDirectory "E:\path\to\CODOL_Experience_V3.3.3.3_FULL"
```
```

★★★ **⇒ 三个**不覆盖**的文件：**
```
Publicprofile    （公开档案）
the.json         （玩家种子）
Inventory.json   （运行时创建的库存）
```

★★ **⇒ 这与 `ol-mod-runtime-manifest.json` 的 `installPolicy: "if-missing"`（报告 005）**完全一致**。**

★★★ **⇒ 且示例路径是 **`CODOL_Experience_V3.3.3.3_FULL`** ——**
**⇒ 再次确认这是 **3.3.3.3** 的源码树（报告 016 已记录版本号冲突）。**

---

## 七、★★★★ `README` 第 3 行的项目定位（逐字）

```markdown
`ol-mod` 用于恢复《使命召唤 Online》**QA 客户端离线运行**所需的**控制面与游戏服务器链路**。
仓库只保留继续开发需要的源码、测试、资产和工具；
**旧 Ayria/Project Nova 名称仅在插件 ABI、固定加载路径或历史证据需要时保留。**
```

★★★ **⇒ 三个关键点：**
```
① 目标是 **QA 客户端**（不是零售版）
② 恢复的是 **控制面 + 游戏服务器链路**
③ ★ 旧名 Ayria/Project Nova **只在 ABI/路径/证据需要时保留**
```

★★ **⇒ 第 ③ 条解释了为什么**文件名是 Ayria32/Localnet32**（ABI 需要）。**

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ `build\` | **221 文件 / 140.71 MB（76%）** |
| 2 | ★ `src\` | **286 文件 / 15.05 MB** |
| 3 | `docs\` | 75 文件 / 15.74 MB |
| 4 | `tools\` | 148 文件 / 5.39 MB |
| 5 | ★★★ **`game_server` 占 src 的 94.4%** | 196 文件 / 14.20 MB |
| 6 | ★ `client_bridge` | **2 文件**（README 未提） |
| 7 | ★★★ 目录职责 | 14 条（backend/game_server/tests/assets/distribution/tools×4/references/docs×2/.agents） |
| 8 | ★★★ 名字映射 | `ol_backend`→**`AlwaysofflineRe.Localnet32`** / `ol_game_server`→`CodolGameServer.Localnet32` |
| 9 | ★★★★ **"不能改名"的原因** | **源码化 Localnetworking 的插件发现 ABI + 现有游戏目录** |
| 10 | ★★ namespace 保留 | 迁移中间态（逐文件验证） |
| 11 | ★ 重构纪律 | **"命名重构与协议修复不混在一起"** |
| 12 | ★★★★★ **闭源组件来源** | **Injector / Bootstrapper / Platformwrapper 来自 `ayriax3/1` 原版** |
| 13 | ★★★ ol-mod 自研 | **Localnetworking / backend / game server** |
| 14 | ★★ 不覆盖三文件 | **`Publicprofile` / `the.json` / `Inventory.json`** |
| 15 | ★★ 示例路径 | **`CODOL_Experience_V3.3.3.3_FULL`**（3.3.3.3 确认） |
| 16 | ★ 项目定位 | **恢复 QA 客户端离线运行的控制面 + 游戏服务器链路** |
| 17 | ★★ 旧名保留条件 | **插件 ABI / 固定加载路径 / 历史证据** |

---

## 九、结论

### 1. ★★★★★ **`build\` 占 76%（140.71 MB）**，而 README 说"没有附带"

★ **⇒ 这是交付包最大的**声明与实际不符**（报告 011/012 已记录）。**

### 2. ★★★ **`game_server` 占 src 的 94.4%**（战斗服是绝对主体）

### 3. ★★★★★ **"兼容名不能改"的原因是插件发现 ABI**

```
源码化 Localnetworking 的插件发现 ABI
        ↓
扫 *.Ayria32 / *.Localnet32
        ↓
★ 所以文件名必须保持
```

### 4. ★★★★ **闭源组件来源已明确**：`ayriax3/1` 原版

★ **⇒ 但 `Platformwrapper` 的内部名带 `Re` ⇒ **README 的说法可能过时**。**

### 5. ★★★ **三个不覆盖的玩家文件**（`Publicprofile` / `the.json` / `Inventory.json`）

### 6. ★★ **示例路径 `CODOL_Experience_V3.3.3.3_FULL`** 再次确认 3.3.3.3

### 7. ★★ **重构纪律**：命名重构与协议修复分开（优秀的工程实践）

---

## 十、下一步

- `source\AGENTS.md`（20,629 B）与 `AGENTS-OLFINAL.md`（18,677 B）
- `source\.agents\` 的 59 个文件（模块文档 + 研究文档）
- `source\docs\devlog\` 的中文开发历程
- `source\tools\runtime\CodolGame.py`（`launch_chain.py` 注释反复引用的）
