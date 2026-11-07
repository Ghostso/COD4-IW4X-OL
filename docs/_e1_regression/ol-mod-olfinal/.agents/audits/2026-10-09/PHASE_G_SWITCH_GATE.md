# PHASE_G_SWITCH_GATE — 目标工件补齐与切换门禁（阶段 G，2026-10-09）

新阶段记录；**不覆盖**任何已冻结的审计基线（STAGE1–STAGE6 全部复验通过）。

## 0. 一句话结论

**目标工件仍未补齐：`out.exe` `NOT_FOUND`，CODOL 地图资产 `0`。G3 的重新标定已完成（79 项守卫，仅 1 项匹配），G4 的切换决策包已就绪——但证据不足以建议切换。**

| 门禁 | 状态 |
| --- | --- |
| G1 候选客户端 | **`NOT_FOUND`**（阻塞） |
| G2 同构建地图资产 | **`0`**（阻塞） |
| G3 重新标定构建绑定 | **已完成（只记录差异，未修改）** |
| G4 切换决策 | **待你批准** |

---

## G1 — 候选客户端：`NOT_FOUND`

本轮对已授权根（`C:\Games`、`D:\BaiduNetdiskDownload`、`E:\`、`F:\桌面`、`G:\`）重新做**有界**搜索:
- 匹配 `out.exe` 的名字 → **0 个**
- 匹配 `codoMP_client_shipRetail.exe` → 40 份副本，仍只有**两个不同构建**，**均不匹配**批准目标 `E3823FD6...`

### 你需要提供
| 项 | 要求 |
| --- | --- |
| 文件 | OLFinal **unpacked** `out.exe` |
| 或 | 其**明确来源** + **完整 SHA-256** |

**收到后我只做身份核验，不自动改正式哈希。** 核验命令:
```
Get-FileHash <path>\out.exe -Algorithm SHA256
```

---

## G2 — 同构建地图资产：`0`

在 CODOL 专属根（`D:\BaiduNetdiskDownload\使命召唤OL`、`D:\codo_3.19.26.13_fresh`、`E:\Program Files\Tencent\TGP\sandbox_codo`、`E:\CODOL_SANDBOX`）内:
- `.ff` 总数 = **52**
- 地图模式（`^(mp|zm|coop|sp)_` 且非 playlist） = **0**

**重要排除**：更宽范围扫描曾在其他游戏目录命中 **2,621** 个地图模式 `.ff`（IW4X `E:\IW4X\zone\patch`、Infinite Warfare `E:\SteamLibrary\...`、MWII `G:\Call.of.Duty.Modern.Warfare.II.Campaign`）。**这些全部不是 CODOL 资产，已排除**，不得计入。

### 你需要提供
该构建发布的**至少一个真实地图 `.ff`**（例如 `mp_crash_tropical.ff` / `mp_nuked.ff` / `zm_factory_sh.ff`），并说明它来自**与候选客户端同一安装**。
**`mp_playlists.ff` 不接受**（它是播放列表发布文件，分类为 `playlists`）。

---

## G3 — 重新标定构建绑定（已完成，**只记录差异，未修改任何东西**）

### 方法
从源码机械提取**全部**构建守卫，并逐一在两个候选上比对:
- `src/game_server/EngineBindings.cpp` 中的 `std::array<std::uint8_t, N> *Prefix{...}` 定义（自 `:755` 起）
- `EngineBindings.hpp` 中的 `*Rva = 0x...` 常量（`:440-1024`）
- `ClientProcessPatches.cpp` 的显式 RVA（如 `UnsignedFastfileVerificationRva = 0x8371A`，`:207`）

解析结果: **prefix 数组 104 个**、**RVA 常量 170 个**、成功配对 **79 对**。

### 结果（两个候选完全一致）

| 指标 | 候选 A `36997674…` | 候选 B `7B31168D…` |
| --- | --- | --- |
| 检查的守卫数 | 79 | 79 |
| **匹配** | **1** | **1** |
| **不匹配** | **78** | **78** |
| 无法映射 | 0 | 0 |

**唯一匹配的守卫是 `ByteDirectionsPrefix` @ `0xA51C70`**，期望字节 `4F9606BF0000000044C4593F`。
注意它是**数据常量**（两个 little-endian float + 一个零），**不是代码序言**。

### 显式要求的两个核验点
| 核验点 | 期望 | 候选 A 实测 | 候选 B 实测 | 结果 |
| --- | --- | --- | --- | --- |
| RVA `0x8371A`（`ClientProcessPatches.cpp:207-211`） | `837C2408010F94C0` | *(已核验)* **不匹配** | *(已核验)* **不匹配** | MISMATCH |
| `ComFramePrefix` @ `0x0FEA20`（`EngineBindings.hpp:440`） | `558BEC5657` | `03C1E00650` | `03C1E00650` | MISMATCH |

其他代表样例（全部不匹配）:
- `DBFindXAssetHeaderPrefix` @ `0x09CF30`: 期望 `558BEC83E4F8`，实测 `00B045CC8D56`
- `DBLinkXAssetEntryPrefix` @ `0x09DA10`: 期望 `558BEC83EC248B450C8B`，实测 `FFE826270012023E0080`
- `PmoveSinglePrefix` / `MsgInitPrefix` / `LevelZoneLoadPrefix` 等同样不匹配

### 为什么这不等于“确定不兼容”（关键限定）

两个候选都是**加壳镜像**。节区元数据（本次实测）:

| 节区 | VirtualSize | RawSize | **VS/RAW** | 熵（抽样） |
| --- | --- | --- | --- | --- |
| `.tp3` #1（含 RVA 0x8371A） | 0x8A689A | 0x593000 | 1.6x | **7.119 / 8** |
| `.tp3` #2 | 0x16DA70 | 0x16E000 | 1.0x | 5.299 / 8 |
| `.tp3` #3 | **0xDBB1CC0** | **0x62000** | **573.9x** | 4.600 / 8 |
| `.tvm0` | 0x4000 | 0x2000 | 2.0x | 6.288 / 8 |
| `.tp3` #7 | 0x82000 | 0x6000 | **21.7x** | **7.337 / 8** |

解读:
- 存在 **573.9x** 的 VirtualSize/RawSize 比 —— 该节区在磁盘上只占 400 KB 却声明 230 MB 虚拟空间，是**加壳/解压描述符**的典型特征；
- 主代码节区熵高达 **7.1–7.3 / 8**，远高于正常 x86 代码（约 6.0–6.5），提示**加密或压缩**；
- 因此**文件字节不代表运行时的内存镜像**。

=> 结论: 对这 78 项不匹配，**不能**推断为“确定不兼容”，也**不能**推断为“兼容”。文件级比对**无法判定**这两个候选的构建身份。判定需要**加载客户端并读取内存字节**——属未授权操作，本阶段不做。

### 若切换构建，需要重新标定的对象（**仅记录差异，未修改**）

**A. 硬绑定 3.3.3.3 哈希 `E3823FD6...` 的工具（必须重新标定）**
| 文件 | 位置 |
| --- | --- |
| `tools/runtime/CodolMapEntDump.py` | `:20` `EXPECTED_IMAGE_SHA256`；校验于 `:172-174` |
| `tools/runtime/CodolGlassAssetDump.py` | `:20`；校验于 `:267-269` |
| `tools/runtime/CodolNetfieldDump.py` | `:20`；校验于 `:161-163` |
| `tools/runtime/CodolWeaponHitLocationDump.py` | `:19`；校验于 `:160` |
| `tools/reverse/catalogs/codol_builtin_matrix.json` | `:8` `codol_client_sha256` |

**B. 已经具备双构建能力（切换成本较低）**
| 文件 | 证据 |
| --- | --- |
| `tools/runtime/CodolMatchFlow.py` | `:86` 起已有独立的 `"1649370"` 表；`:26-27` 说明该列来自 CODOL-main tree 的 `re/olfinal/matchflow-1649370.json`；`:83` 记录 vtable 75 vs 88 项的差异 |
| `tests/game_server/PlayerDataDefTests.cpp` | `:273` 载入 `mp_playerdata.def.1649370.bin`，`:278` 载入 `mp_playerdata.def.3333.bin` —— **两个构建的 fixture 都已存在** |
| `tests/game_server/Fixtures/` | 同时含 `profile-69420.olfinal.document.bin` 与 `profile-seed.3333.document.bin` |
| `tests/game_server/ServerCoreTests.cpp` | 大量 `CODDIFF(1649370)` 注解（如 `:6857`、`:7198`、`:12733`、`:15371`） |

**C. 需要评估但尚未量化的**
- 全部 79 项守卫的**内存**验证（需加载客户端）；
- `EngineBindings.hpp` 中 170 个 RVA 的逐个有效性；
- 结构布局（`playerState_s` 本构建 `0x3BBC`、`entityState_s` `0x118`）在 OLFinal 上是否一致；
- 协议常量与 netfield 表；
- S2 玻璃阈值 / S3 destructible 的原生数据来源。

---

## G4 — 切换决策包（**等待你明确批准**）

### 证据矩阵

| # | 判据 | 期望 | 实际 | 证据等级 | 是否满足 |
| --- | --- | --- | --- | --- | --- |
| 1 | 候选 `out.exe` 存在 | 一个 unpacked 客户端 | 0 个 | CONFIRMED（有界搜索） | **否** |
| 2 | 候选身份 = 批准哈希 | `E3823FD6...` | 40 份副本无一匹配 | CONFIRMED | **否** |
| 3 | 静态守卫匹配 | 79/79 | **1/79**（且唯一匹配是数据常量） | CONFIRMED | **否** |
| 4 | 加壳导致的判定不可靠性 | —— | VS/RAW 573.9x、熵 7.34/8 | CONFIRMED | 已记录（限定） |
| 5 | 同构建地图资产 | ≥1 真实地图 `.ff` | CODOL 根内 **0** | CONFIRMED | **否** |
| 6 | 构建关联证据 | 显式声明 | 无（无候选可关联） | UNKNOWN | **否** |
| 7 | 内存级身份核验 | 加载后比对 RVA | 未执行（未授权） | NOT_RUN | **否** |
| 8 | 双构建工具准备度 | —— | 部分工具已双构建（见 G3-B） | CONFIRMED | 部分 |

### 切换影响清单

| 影响面 | 若切到 OLFinal | 现状 |
| --- | --- | --- |
| 4 个 dump 工具的强制哈希 | 必须重新标定（G3-A） | 硬绑 3.3.3.3 |
| `codol_builtin_matrix.json` 的客户端哈希 | 必须重新标定 | 硬绑 3.3.3.3 |
| 79 项构建守卫 + 170 个 RVA | 需在**内存**上重新核验（当前文件级不可判定） | 全部按 3.3.3.3/1649370 记录 |
| 结构布局（playerState `0x3BBC` / entityState `0x118`） | 需重新核验 | 按当前构建 |
| 协议常量 / netfield 表 | 需重新核验 | 按当前构建 |
| 地图资产 | 需同构建提供（当前 0） | 无 |
| 测试 fixture | `PlayerDataDefTests` 已双构建；其余需评估 | 部分就绪 |
| 现有审计基线 | **保持不变**，新增记录 | 冻结中 |

### 决策所需的最小证据（缺一不可）
1. **unpacked `out.exe` 本体**（或明确来源 + 完整 SHA-256）；
2. 该文件 **RVA `0x8371A` 实测 = `837C2408010F94C0`**，且 `ComFramePrefix @0x0FEA20` 等记录守卫一致（**一次比对即可定论**）；
3. **同一构建**的地图 `.ff`（≥1 个真实地图 + SHA-256）；
4. 对 4 个 3.3.3.3-hard-pinned 工具的**重新标定计划**（我可以出方案，但需你批准之后才动）。

### 门禁结论

**证据不足以建议切换到 OLFinal 构建。** 已满足的门禁为 0/3（G1、G2 均阻塞；G3 只完成“差异记录”这一半）。**在你提供 §G1/G2 的工件之前，不进入构建或运行验证阶段，不安装工具链。**

---

## 基线冻结声明

- 现有 **6 个未推送提交保持不变**：`6d2705d`、`e237e25`、`1276b72`、`2823393`、`f0d1b82`、`5b0ea05`；
- **未推送、未 amend、未 reset、未改写历史**；
- 工作树干净，`src/` 修改 = 0；
- 未安装任何工具、未构建、未启动游戏、未抓包、未生成 Golden；
- 未修改任何期望哈希、RVA、ABI、协议常量或 S2/S3 默认行为。
