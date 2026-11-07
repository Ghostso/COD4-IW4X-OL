# 06 下一步行动 / NEXT ACTIONS

按 **预期价值 / 成本** 排序。所有条目均为 **静态分析**（本阶段约束：不启动游戏/服务端、不编译、不打补丁）。未标注者为可立即执行。

> 证据等级：**VERIFIED** / **STATIC-INFERENCE** / **NOT-OBSERVED** / **BLOCKED**。

---

## 结论回顾（四项必答，先给答案）

### Q1. 新文件是否确实包含更新的服务端代码，而非仅仅打包时间较新？
**是（VERIFIED）。** 依据：
- NEW 含 **99 个 `2697` 命名符号**，在 OLD 与 1113 中 **全部不存在**；
- NEW 含 **26 个 `codol_2697_*` / `codol_weapon_2697_*` / loopback / netconst / archive-probe 源文件名串**，OLD/1113 均无；
- NEW 新增 `_SV_BuildClientSnapshot`(0x89081)、`_SV_WriteReliableCommand`(0x8612e)、`_SV_ProfileCommand2697`(0x860de) 等 NEW-only 函数；
- NEW 与 1113 共享 GCC 16.2.0 / ld 2.47 新工具链，且导入集仅差 9 项，说明 2697 增量是 **独立的 `.text` 实现层**，而非工具链假象。
- 反之，**mbedTLS 三样本均有**，不是"更新"的判据（排除项）。

### Q2. 相较旧版本增加或改变了什么？
**（VERIFIED 事实 + STATIC-INFERENCE 语义）**
1. 新增独立 **2697 wire 写通道**：`_CODOL2697_WriteGamestate/WriteSnapshot/WriteConfigstrings/WriteDeltaValue/…`（OLD/1113 无）。
2. 2697 通道在 EOF 位置写 **`0x06`**（旧通道写 `0x05`）；可靠命令 2697 分支写 **`0x02`**（旧 `0x01`），回退仍写 `0x01`。
3. 新增 **注册门控**：`_CODOL2697_WriteNativeGamestate` 在缺少"已验证客户端注册导出"时 **扣留 gamestate**；对应 `_CODOL2697_ReadRegistration` 与磁盘 `evidence\client-registration2697.txt`。
4. 新增 **发布审计 / dry-encode / netconst 校验** 路径（`_CODOL2697_PublicationAudit_f`）。
5. 新增 **2697 武器系统**（`_CODOL_BuildWeapon2697Core/Registry`、`_CODOL2697_ParseWeaponRecipe`、`_CODOL_LoadEngineWeapon2697` 等）。
6. 新增 **11 个 loopback 网络守卫**（`codol_loopback_win32.c`）。
7. 构建层面：11 节区、`.eh_fram`、DYNAMIC_BASE、EntryPoint 0x14e0（与 1113 同代配置），相对 OLD 的 20 节区/ld 2.30 是 **整体构建换代**。

### Q3. 是否值得成为后续研究的主要服务端样本？
**值得（STATIC-INFERENCE，且互通未验证）。** 理由：
- 它与 `manifest.json` 声明的 **2.6.9.7 客户端** 同源封包，客户端哈希 `353754047dbb…` 与 manifest 逐字节一致（VERIFIED）；
- 它是 **唯一含 2697 协议层** 的样本，OL/1113 都不含；
- 但 **客户端互通/进大厅 = NOT-OBSERVED**，因此"作为主样本做反向/协议研究"成立，**不能**据此宣布"可直接跑通"。

### Q4. 下一步最值得追踪的 3 条具体代码路径？
见下方"N1 / N2 / N3"。

---

## 排序行动项

### N1（最高价值，中成本）— 打通 2697 gamestate 发布链
- 目标函数：`_CODOL2697_WriteNativeGamestate`（RVA **0xa3dab**）、`_CODOL2697_WriteGamestate`（**0xa21b8**）、`_CODOL2697_ReadRegistration`（**0xa3ea0**）。
- 要做：精确恢复 2697 gamestate 的字段布局与 `0x03`…`0x06` 之间的每段结构；确认注册文件的 5 字段语义（`kind=2 / 0x6b6fb5d0 / 180 / 139 / f78302fe`）如何参与校验。
- 价值：这是"能否进入大厅"的**总线**；门控不过则 gamestate 直接不发。
- 工具：已有 `_tools\_msgbytes3.py`、`_callers*.py`、`_dis*.py` 可直接复用（无需新工具）。

### N2（高价值，中成本）— 精确化 2697 snapshot 与 `0x06` 终止语义
- 目标函数：`_CODOL2697_WriteSnapshot`（**0xa4fa0**）、`_CODOL2697_WriteSnapshotReached`（**0xa4860**）。
- 要做：逐段还原 entities→clients→glass→hud 的字段（`_CODOL2697_WriteEntities` 0xa1a65 / `_WriteClients` 0xa01ec / `_ReachHud` 0x49f2e5），确认 `0x06` 是"段终止"还是"消息终止"。
- 价值：直接回答"旧版 0x05 是否被 0x06 取代"这一协议核心疑问。

### N3（高价值，中成本）— 恢复可靠命令 `0x02` 封装
- 目标函数：`_SV_WriteReliableCommand`（**0x8612e**）、`_SV_ProfileCommand2697`（**0x860de**）、`_CODOL2697_ProfileCommandBytes`（**0x85d32**）。
- 要做：还原 `MSG_WriteByte(2) + MSG_WriteLong + MSG_WriteShort + MSG_WriteData` 的画像结构，明确"哪些命令走 2697 映射、哪些回退到 `0x01`"。
- 价值：这是 NEW 与客户端服务器命令交互的**主要新路径**。

---

### N4（高价值，中成本）— 反汇编客户端侧对称实现
- 目标文件：`codoMP_client_shipRetail.exe`（`353754047dbb…`）、`client_room2697.dll`、`client_native_loopback.dll`。
- 要做：在客户端搜索 `0x06` 接收分支、2697 相关字符串/函数，验证服务端新字节是否被客户端识别。
- 价值：**唯一**能把互通从 NOT-OBSERVED 推向可判定的静态路径。

### N5（中价值，低成本）— 追踪 2697 启用开关
- 目标串/符号：`CODOL2697_PROFILE_WIRE`、`CODOL_INVENTORY2697`、`CODOL_RUNTIME_WEAPONS2697`、`WireFixture2697`。
- 要做：定位这些 CVar 的注册与读取点，判断 2697 通道是否有运行时开关、默认是否启用。
- 价值：解释"为何旧通道仍在、2697 通道如何被选中"。

### N6（中价值，低成本）— 2697 武器系统字段级分析
- 目标符号：`_CODOL_BuildWeapon2697Core`（0xf38d7）、`_CODOL_BuildWeapon2697Registry`（0xf48eb）、`_CODOL2697_ParseWeaponRecipe`（0xf4e6f）、`_CODOL_LoadEngineWeapon2697`（0x164307）。
- 价值：2697 武器是相对旧版最"重"的新增子系统，可能影响装备/大厅展示。

### N7（低价值 / 低成本，可选）— 2697 归档探测与地图挂载
- 目标符号：`codol_archive_probe.c`、`_CODOL_MountTarget2697Archives`（0x1400c3）、`_CODOL_Target2697ArchivesActive`（0x140133）。
- 价值：解释 map mount / archive 相关诊断串，非核心。

---

## 成本/价值矩阵

| ID | 价值 | 成本 | 是否新工具 | 建议 |
|---|---|---|---|---|
| N1 | 高 | 中 | 否 | **立即做** |
| N2 | 高 | 中 | 否 | **立即做** |
| N3 | 高 | 中 | 否 | **立即做** |
| N4 | 高 | 中 | 否 | 次优先（需客户端反汇编脚本） |
| N5 | 中 | 低 | 否 | 可并行 |
| N6 | 中 | 低 | 否 | 可并行 |
| N7 | 低 | 低 | 否 | 可选 |

---

## 当前局限与阻塞

| 项 | 状态 |
|---|---|
| 2697 层源码 | **BLOCKED**（旧包源码树 `grep 2697` = 0 命中，本地无 2697 源码） |
| 客户端是否接受 0x06 / 0x02 | **NOT-OBSERVED** |
| 运行期互通 / 进大厅 | **NOT-OBSERVED** |
| `scripts\`（1,341 文件）是否含 2697 协议脚本 | 未核验（未逐文件解析） |
| `runtime-assets\`（11,033 文件 / 1.71 GB）是否含 2697 专属协议/resource | 未核验（仅目录清单） |

---

## 本阶段交付物索引

| 文件 | 内容 |
|---|---|
| `01_SAMPLE_IDENTITY.md` | 样本身份、哈希、PE 元数据、目录清单 |
| `02_DIRECTORY_DIFF.md` | 目录/文件级差异 |
| `03_BINARY_DIFF.md` | PE/导入/导出/节区/字符串/符号差分 |
| `04_PROTOCOL_PATHS.md` | 连接、gamestate、snapshot、可靠命令代码路径 |
| `05_CLIENT_COMPATIBILITY.md` | 与已知客户端行为的关联与分级 |
| `06_NEXT_ACTIONS.md` | 本文件 |
| `SHA256SUMS.txt` | 报告与派生文件哈希 |
