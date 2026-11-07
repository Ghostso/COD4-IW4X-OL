# -*- coding: utf-8 -*-
from pathlib import Path
OUT=Path(r"D:\BaiduNetdiskDownload\使命召唤OL\E27_DEMONWARE_SERVER_PEER_DISCOVERY_001")
files={}

files["E27_NEGATIVE_EVIDENCE_BOUNDARIES.md"]=r'''# E27 负向证据与边界

> 纪律：区分「当前搜索范围未命中」「所有已枚举模块未命中」「已证明某模块不承担」「已证明生态缺少」。不得用一次零命中证明全局不存在。

## 1. 已执行的否定搜索

| # | 搜索 | 范围 | 覆盖 | 结果 | 边界声明 |
|---|---|---|---|---|---|
| N1 | `CLIENTCHAL`/`BDDATA`/`HMAC mismatch`/`Bad recv counter`/`Bad frame/payload size` | `server2697\` 全部文件 | **12,511 / 12,511（100%）**，ASCII + UTF-16LE | **0 命中** | 全字节覆盖；结论限"2697 服务端生态内不存在" |
| N2 | `bdCore`/`bds`/`demonware` | 同上 | 100% | `bdCore` 0；`bds` 57（**全为二进制字节巧合**）；`demonware` 2（致谢表/注释） | 已逐个核验命中性质 |
| N3 | 4 个 PE 模块的导入/导出/字符串 | 4 个模块全量 | 100% | 仅 iD-Tech/loopback 语义；无 Demonware 模块名 | 覆盖全部 PE |
| N4 | `0xAB85` 帧结构 / Demonware 帧头 | `codol_dedrun.exe` + 3 辅助 PE | 100% | 0 个 Demonware 帧构造 | 反证 `codol_dedrun.exe` 不承担 Demonware |
| N5 | `server2697\` 是否存在 lobby/Demonware 目录 | 目录树 | 100% | 无（仅 `runtime-assets`/`scripts`/`script-overlay2697`/`native`/`evidence`） | — |
| N6 | `lobby_runtime2697.py` 是否协议实现 | 单文件 | 全文 | 否——显卡/资源 trap 补丁（`apply_video_setting`、`build_file_gate`） | 反证"名称含 lobby 即为大厅实现" |
| N7 | 工作区文本类全量（`CLIENTCHAL`/`BDDATA`） | 113,920 文本文件 | 文本扩展名 | 108 命中，**全部**为对端实现/历史逆向/本项目产物 | 范围限文本扩展名（见 §3） |

## 2. 已证明"不承担"的模块（明确的 REFUTED）

| 假设 | 裁定 |
|---|---|
| `codol_dedrun.exe` 承担 Demonware 会话 | **REFUTED**（E-26 + 本轮 N1/N4） |
| `client_room2697.dll` 承担 Demonware 会话 | **REFUTED**（N1，导出仅 `LocalRoomPump`） |
| `client_native_loopback.dll` 承担 Demonware 会话 | **REFUTED**（N1，导出仅 `LocalMatchBegin`） |
| `client_loopback_guard.exe` 承担 Demonware 会话 | **REFUTED**（N1；且为 x64，仅 fwpuclnt/RPCRT4） |
| `lobby_runtime2697.py` 是 2697 大厅协议实现 | **REFUTED**（N6） |
| 2697 服务端生态包含 Demonware 组件 | **REFUTED（范围内，100% 字节覆盖）** |

## 3. 未覆盖/盲区（不得据此断言不存在）

| 盲区 | 说明 |
|---|---|
| 工作区**非文本**二进制（数万 `.ff`/`.dll`/`.exe` 等） | 范围 B 仅扫文本扩展名；可能含未识别的对端二进制 |
| 2697 服务端**运行时**解包/注入内容 | 冻结约束禁止运行时读取；`client_room2697.dll` 等可能运行时加载它处代码 |
| 线上真实服务端（腾讯/Demonware 生产环境） | 不在冻结样本内，不可获取 |
| `runtime-assets` 中 `.ff` 内的 GSC/脚本字节 | 已全量读入做 ASCII 扫描，但 `.ff` 内部压缩/编码结构未逐一解包 |
| 其它工作区目录（`CODOLServer\_mainline\` 的 900+ 运行时镜像 `image_best.bin` 等） | 属运行时 dump 产物，未纳入本轮（且与 E-27 目标无直接关系） |

## 4. 措辞边界（必须遵守）

- ✅ 正确："**2697 服务端生态（12,511 文件）内不存在 Demonware 协议实现**。"
- ❌ 错误："Demonware 服务端不存在。"（**存在**，在 `ol-mod-olfinal`/`REF_LOBBY_KIT`。）
- ✅ 正确："`codol_dedrun.exe` **不承担** Demonware 会话（已证）。"
- ❌ 错误："2697 客户端无法使用 Demonware。"（客户端**是** Demonware 客户端；只是对端不在该包内。）
- ✅ 正确："Demonware 对端引用的客户端地址（`0x9CE310` 等）在 2697 恢复镜像中**不成立**。"
- ❌ 错误："2697 客户端与 Demonware 对端协议不兼容。"（需先重新定位，见 E27-NEXT-GATE。）

## 5. `bds` 命中的逐一澄清（防误读）

57 处 `bds`/`BDS` 中：
- **0** 处指代 Demonware 的 "bds"（Backend Data Service）；
- 2 处在 `evidence\attachment-registry2697.json/.txt`（属其它 token 的子串）；
- 55 处在 `.ff`/`.iwi`/`.mp3`/模型二进制中，为 `62 64 73` 三字节巧合。

**不得**把 `bds` 计数当作 Demonware 证据。
'''

files["E27_UNIFIED_REGISTER_DELTA.md"]=r'''# E27 统一登记簿增量

## 1. 开工基线核对（以 E-26 实际交付为准）

任务书给定基线：总权重 425，加权得分 201.5，认知完备率 47.41%，I4 权重 216，I4 加权得分 105.6，I4 完备率 48.89%，实时互操作 NOT-OBSERVED。

对 E-26 实际交付 `E26_UNIFIED_REGISTER_DELTA.md` §3/§4 复算：

| 项 | 任务书基线 | E-26 交付值 | 逐项复算 | 裁定 |
|---|---:|---:|---:|---|
| 总权重 | 425 | 425 | 349 + (8+8+8+8+5+8+5+5+8+5+3+5) = 425 | 一致 |
| 加权得分 | 201.5 | 201.5 | 169.5 + 32.0 = 201.5 | 一致 |
| 认知完备率 | 47.41% | 47.41% | 201.5 / 425 = 47.412% | 一致 |
| I4 权重 | 216 | 216 | 168 + (8+8+8+8+8+8) = 216 | 一致 |
| I4 加权得分 | 105.6 | 105.6 | 81.6 + 24.0 = 105.6 | 一致 |
| I4 完备率 | 48.89% | 48.89% | 105.6 / 216 = 48.889% | 一致 |
| 实时互操作 | NOT-OBSERVED | NOT-OBSERVED | — | 一致 |

**登记簿与 E-26 交付一致，无差异，可继续使用。**

## 2. 本轮新增问题

| Q ID | 协议层 | 问题 | 影响 | 权重 | 状态 | 解决度 | 加权贡献 | 证据 |
|---|---|---|---|---|---|---|---|---|
| Q-80 | 生态/清单 | 2697 服务端生态的文件/模块全清单 | I2 | 3 | **PROVEN** | 1.0 | 3.0 | E27-INVENTORY（12,511 文件 / 1742.0 MB / 4 PE，100% 字节覆盖） |
| Q-81 | 生态/归属 | 2697 服务端生态是否含 Demonware 组件 | I4 | 8 | **REFUTED** | 0.0 | 0.0 | E27-SIGSEARCH（`CLIENTCHAL`/`BDDATA` 0 命中，4 PE 全覆盖） |
| Q-82 | 生态/归属 | `codol_dedrun.exe` 之外 3 个 PE 是否承担 Demonware | I3 | 5 | **REFUTED** | 0.0 | 0.0 | E27-MODULE（导出仅 Loopback/Guard；0 标记） |
| Q-83 | 生态/对端 | Demonware 会话协议的服务端对端实现是否存在（工作区） | I4 | 8 | **PROVEN** | 1.0 | 8.0 | E27-CROSSWALK（`Crypto.cpp` L205-207；`codol_crypto.py::derive_session_keys`） |
| Q-84 | 生态/对端 | 对端密钥派生是否与客户端 E-21 字符串一致 | I4 | 8 | **PROVEN** | 1.0 | 8.0 | E27-CROSSWALK（`CLIENTCHAL`→16B / `BDDATA`→72B 切分 20/20/16/16） |
| Q-85 | 生态/对端 | 对端帧结构（`0xAB85` + AES-128-CBC + HMAC-SHA1[:8]） | I3 | 5 | **PROVEN** | 1.0 | 5.0 | E27-CROSSWALK（`codol_crypto.py` 文档头逐字段 + 实现） |
| Q-86 | 生态/适配 | 对端实现是否直接适用于 2697 客户端 | I4 | 8 | **REFUTED** | 0.0 | 0.0 | E27-CROSSWALK（对端引用的 `0x9CE310` 在 2697 镜像不成立；面向 1.1.1.13/3.3.3.3） |
| Q-87 | 生态/分层 | Demonware 控制面与 iD-Tech 对局面是否分层共存 | I3 | 5 | **INFERRED（强）** | 0.6 | 3.0 | E27-CROSSWALK（客户端同时含两族标记；对端为 TCP 大厅，`codol_dedrun` 为 UDP 17733） |
| Q-88 | 生态/清单 | 2697 客户端是否为 Demonware 客户端 | I3 | 5 | **PROVEN** | 1.0 | 5.0 | E27-SIGSEARCH（`bdLobby`2 / `dwLobby`1 / `dwRoom`38 / `CLIENTCHAL`1 / `BDDATA`1） |
| Q-89 | 生态/对端 | 2697 客户端 Demonware 帧的魔数/解码入口 | I4 | 8 | BLOCKED | 0.0 | 0.0 | E27-BLOCKERS（`0x686210` 为写入 `0xDEADBEEF`，解码入口未定位） |
| Q-90 | 生态/对端 | 2697 Demonware 服务端模块的物理位置 | I4 | 8 | BLOCKED | 0.0 | 0.0 | E27-BLOCKERS（生态内 0 命中；生态外对端为其它构建） |
| Q-91 | 生态/方法学 | `bds`/`demonware` 在 2697 生态内的命中性 | I2 | 3 | **REFUTED** | 0.0 | 0.0 | E27-NEGATIVE（`bds` 57 全为字节巧合；`demonware` 2 为致谢表/注释） |

## 3. 重算（统一口径）

- 基线（E-26）：总权重 425，加权得分 201.5。
- 本轮新增（权重 / 得分）：
  - Q-80：+3 / +3.0
  - Q-81：+8 / +0.0
  - Q-82：+5 / +0.0
  - Q-83：+8 / +8.0
  - Q-84：+8 / +8.0
  - Q-85：+5 / +5.0
  - Q-86：+8 / +0.0
  - Q-87：+5 / +3.0
  - Q-88：+5 / +5.0
  - Q-89：+8 / +0.0
  - Q-90：+8 / +0.0
  - Q-91：+3 / +0.0
- 权重合计 +74；得分合计 +32.0
- **新总权重：425 + 74 = 499**
- **新加权得分：201.5 + 32.0 = 233.5**
- **新认知完备率：233.5 / 499 = 46.79%**
- **I4**：
  - 新增 I4 项：Q-81(+8)、Q-83(+8)、Q-84(+8)、Q-86(+8)、Q-89(+8)、Q-90(+8)
  - I4 权重：216 + 48 = **264**
  - I4 得分：105.6 + (0+8.0+8.0+0+0+0) = **121.6**
  - **I4 加权完备率：121.6 / 264 = 46.06%**
- 实时互操作：**NOT-OBSERVED**（未变）

## 4. 校验

- 权重：425 + (3+8+5+8+8+5+8+5+5+8+8+3) = 425 + 74 = 499 ✅
- 得分：201.5 + (3.0+0+0+8.0+8.0+5.0+0+3.0+5.0+0+0+0) = 201.5 + 32.0 = 233.5 ✅
- I4 权重：216 + (8+8+8+8+8+8) = 264 ✅
- I4 得分：105.6 + (0+8.0+8.0+0+0+0) = 121.6 ✅
- I4 率：121.6 / 264 = 46.0606% ≈ 46.06% ✅

> 说明：认知完备率由 47.41% 降至 46.79%，因本轮新增 4 项 `REFUTED`（0 分）与 2 项 `BLOCKED`（0 分）。这是**诚实记录**的结果——本轮的核心价值是**负面结论**（生态缺失 + 对端存在于别处），不追求比率增长。

## 5. 历史修订保留

- E-19 "type 1 -> size 1" 仍为 `REFUTED`。
- E-21 "0xA85AD0 属 .tvm0" 仍为 `REFUTED`。
- E-22 "五地址属 .data BSS" 仍为 `REFUTED`（Q-48）。
- E-23 "0x6AB310 无直接调用" 仍为 `REFUTED`（Q-54）。
- E-25 "0x83/0x84/0x85 经同一应答队列" 仍为 `REFUTED`（Q-65）。
- E-26 "CLIENTCHAL/BDDATA 在服务端不存在" 仍为 `REFUTED`（Q-71，范围=`codol_dedrun.exe`）。
- 本轮新增 `REFUTED`：Q-81/Q-82/Q-86/Q-91；**并更正 E-26 的措辞**（见 §6）。
- 不改变既有问题权重；认知完备率不代表互操作完成率。

## 6. 对 E-26 结论的精确化（非改写）

E-26 结论"服务端无 Demonware 模块与该族字符串"应精确为：**"`codol_dedrun.exe`（对局面）内无 Demonware；2697 服务端生态内亦无"**。本轮新增的关键事实是：**Demonware 对端存在于生态外**（`ol-mod-olfinal` C++、`REF_LOBBY_KIT` Python），但面向 `1.1.1.13`/`3.3.3.3` 客户端构建。E-26 原文保留，本处为补充精确化。
'''

files["E27_NEXT_GATE_DECISION.md"]=r'''# E27 下一门禁决策

## 1. 决策

**维持 CONDITIONAL GO**，并把下一步从"继续在 2697 服务端内找 Demonware"**转向"对端复用性验证"**。本轮证明：Demonware 对端**已存在**（C++/Python 两套），只是**不在 2697 服务端包内**，且面向**另一客户端构建**。

## 2. 本轮获得的确定性收益

1. **生态清单闭合**（PROVEN）：12,511 文件 / 1742.0 MB / **4 个 PE** 全量枚举；`CLIENTCHAL`/`BDDATA` **0 命中**（100% 字节覆盖）。
2. **负面结论成立**（PROVEN）：2697 服务端生态**不含** Demonware 控制面；`codol_dedrun.exe` 是 iD-Tech 对局面（与 E-26 互证）。
3. **对端定位成功**（PROVEN）：`ol-mod-olfinal\src\backend\Demonware\`（C++）与 `REF_LOBBY_KIT\codol_crypto.py`（Python）实现了 `CLIENTCHAL`/`BDDATA` 密钥派生与 `0xAB85` 帧。
4. **派生一致性确认**（PROVEN）：两侧 `CLIENTCHAL`→16B、`BDDATA`→72B（切分 `20/20/16/16`）完全一致，与客户端 E-21 字符串对应。
5. **分层架构明确**（INFERRED 强）：Demonware = 大厅/认证控制面（TCP，`0xAB85`）；iD-Tech = 对局面（UDP 17733，3 位 clc）。
6. **适配度冲突定位**（PROVEN）：对端引用的客户端地址（`0x9CE310` 等）在 **2697 恢复镜像中不成立**。

## 3. 停止条件核对（任务书 §8）

| 停止条件 | 状态 |
|---|---|
| "找到疑似独立协议模块 → 只深入验证其协议入口与对应关系" | **部分适用**：对端已找到，但属**其它构建**；需先验证复用性 |
| "找到明确的 Demonware 服务端处理链 → 建立交叉表后停止" | 对端链**已存在**（生态外），交叉表已建（E27-CROSSWALK）；**2697 内**未找到 |
| "所有已枚举模块均无足够证据 → 报告覆盖范围、盲区与最小缺失证据" | **适用**（2697 生态内） |
| "不再扩展 `codol_dedrun.exe` 已确认不承载该握手的经典分派链" | **遵守** ✓ |

## 4. 剩余最小缺失证据

1. **2697 客户端的 Demonware 解码入口与帧魔数**：`0x686210` 为 `mov [ecx],0xDEADBEEF`（写入）；2697 是否用同一魔数、入口在哪，未闭合。
2. **对端的 2697 地址映射**：需把 `ol-mod`/`REF_LOBBY_KIT` 引用的 `1.1.1.13` 地址在 2697 恢复镜像上重新定位。
3. **2697 的 Demonware 服务端**：生态内外均未找到面向 **2.6.9.7** 的该组件。

## 5. 下一步唯一建议

**执行"对端复用性验证"**（同一工作区，无需新样本）：

1. 取 `ol-mod-olfinal\src\backend\Demonware\Crypto.cpp` 的 `deriveSessionKeys` 与 `REF_LOBBY_KIT\codol_crypto.py` 的 `derive_session_keys`，用 `DemonwareTests.cpp` 的 KAT 向量验证实现自洽（`tests\backend\DemonwareTests.cpp:2455-2478`）。
2. 在 **2697 恢复镜像**中，以 `CLIENTCHAL`(VA `0xC5B144`)/`BDDATA`(`0xC5B13C`) 的**交叉引用**为锚，定位 `expandKey`/`hmacSha1`/`sha1` 的调用点，确认 2697 是否使用**同一派生公式**（标签、长度 16/72、切分 20/20/16/16）。
3. 若公式一致 → 记录"2697 与对端同构，可复用"；随后才值得把对端的 2697 地址映射补齐。
4. 若公式不一致 → 记录首个参数/长度/顺序差异，并判定"2697 需独立 Demonware 服务端实现"（架构级阻塞）。

不建议：
- 继续在 `server2697\` 内搜索 Demonware（已 100% 覆盖，0 命中）；
- 直接运行对端实现（本轮为只读静态分析；且其面向另一构建）；
- 把认知完备率当作互通完成率。
'''

for name,content in files.items():
    (OUT/name).write_text(content,encoding="utf-8")
    print("wrote",name,len(content))
