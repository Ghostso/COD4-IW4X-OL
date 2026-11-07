# E27 协议标记定向搜索

## 1. 搜索方法（可回溯）

| 项 | 值 |
|---|---|
| 范围 A | `runtime\game\server2697\` 全部 **12,511** 文件（含 `.ff`/`.iwi`/`.mp3` 二进制） |
| 范围 B | 工作区全量文本类文件 **113,920** 个（`.py/.md/.txt/.json/.js/.c/.cpp/.h/.pyc/.lua/.gsc/.cfg/.ini/.log/.csv`） |
| 编码 | ASCII **与** UTF-16LE 双向变体 |
| 标记集 | `bdCore`、`bds`、`demonware`、`CLIENTCHAL`、`BDDATA`、`HMAC mismatch`、`Bad recv counter`、`Bad frame/payload size` |
| 输出 | `_data\sigsearch_all.txt`、`_data\bdtags_ws.txt`（含文件路径 + SHA-256 前 16 位） |
| 目录清单 | `_data\inventory.txt`、`_data\file_list.txt`、`_data\module_hashes.txt` |

## 2. 范围 A：2697 服务端生态结果

| 标记 | 命中文件数 | 说明 |
|---|---:|---|
| `CLIENTCHAL` | **0** | — |
| `BDDATA` | **0** | — |
| `HMAC mismatch` | **0** | — |
| `Bad recv counter` | **0** | — |
| `Bad frame/payload size` | **0** | — |
| `bdCore` | 0 | — |
| `demonware` / `Demonware` / `DEMONWARE` | **2** | `scripts\maps\_credits.gsc`（制作人员表）、`scripts\maps\mp\gametypes\_codol_chat.gsc`（注释） |
| `bds` / `BDS` | 57 | **全部为二进制资源中的字节巧合**（见 §2.1） |

### 2.1 `bds` 命中的性质（重要）

57 个 `bds`/`BDS` 命中里：
- 2 个在 `evidence\attachment-registry2697.json/.txt`（文本，属其它词的子串）；
- 其余 55 个分布在 `.ff`/`.iwi`/`.mp3`/模型二进制中，**ASCII 三字节巧合**（例如浮点/纹理数据中 `62 64 73`）。**不构成协议证据**。

### 2.2 `demonware` 命中的性质（重要）

| 文件 | 行 | 内容 | 性质 |
|---|---|---|---|
| `scripts\maps\_credits.gsc` | 1764/1917/1955/1957/1958 | `initATVICredits_demonware()`、`// Managing Director, Demonware`、`addCenterHeading(&"CREDIT_DEMONWARE")` | **制作人员表**，非协议 |
| `scripts\maps\mp\gametypes\_codol_chat.gsc` | 11 | `// ... on this build that is the Demonware service-102 channel (room.say / room.say2team / party.say, docs/service102_chat.md), because C1.exe has NO 'say' reliable client command` | **注释**：说明"某一构建"的聊天走 Demonware service-102；**不是** 2697 服务端的实现 |

**裁定**：范围 A 内**没有**任何 Demonware 协议实现；`demonware` 仅出现在致谢表与一条注释中。**PROVEN（范围内）。**

## 3. 范围 B：工作区全量文本结果（Demonware 对端存在）

`CLIENTCHAL`/`BDDATA` 在 **108** 处命中（成对出现），分布于 5 类：

| 类 | 代表路径 | 性质 |
|---|---|---|
| **1. C++ 对端实现** | `_e1_regression\ol-mod-olfinal\src\backend\Demonware\Crypto.cpp` | `expandKey(secret,"CLIENTCHAL",16)` / `expandKey(secret,"BDDATA",72)`（L206-207） |
| **2. Python 对端实现** | `REF_LOBBY_KIT\codol_crypto.py`、`GOLDEN-LOBBY-001\REF_LOBBY_KIT\*`、`REF_LOBBY_KIT_CAP009\*` | `derive_session_keys`、`expand_key`、帧编解码 |
| **3. 历史逆向手册** | `CODOLServer\HANDOFF_20260930_REVERSE_MANUAL.md`、`KEY_CONTEXT_20260925.txt`、`_mainline\_kdf13d0.py` | `0xD5A4E0 "BDDATA"`、`0xD5A4E8 "CLIENTCHAL"`（**打包客户端** VA） |
| **4. 本项目 E21-E27 交付物** | `E21..E27\*` | 我们自己的报告/脚本 |
| **5. 其它研究** | `run_codol_001\strings_found.txt`、`_e1_regression\ol-mod-olfinal\.agents\research\dw3_feasibility.md` | 研究产物 |

## 4. 关键对比：打包客户端字符串位置

| 客户端 | `BDDATA` VA | `CLIENTCHAL` VA |
|---|---|---|
| **打包** `codoMP_client_shipRetail.exe`（2.6.9.7） | `0xD5A4E0` | `0xD5A4E8` |
| **恢复镜像** `codol2697-static-candidate.bin` | `0xC5B13C` | `0xC5B144` |

（两镜像 VA 不同是 aplib 重排所致；**字符串内容与相邻次序一致**，因此是同一客户端。）

## 5. `0xAB85` 帧标记搜索

| 对象 | `0x00 0xAB` 命中 | `0xAB 0x85` 命中 | 说明 |
|---|---:|---:|---|
| 2697 打包客户端 | 18 | 由恢复镜像验证 | Demonware 帧类型字节 |
| 恢复镜像 | — | **0（对齐）** | 帧类型属**运行时**写入，非静态表 |
| `codol_dedrun.exe` | 0 表项 | 0 | 无 Demonware 帧结构 |

**裁定**：Demonware `0xAB85` 帧标记**不在** 2697 服务端任何模块中；只在客户端与生态外的对端实现中。**PROVEN。**

## 6. 搜索的边界声明

- 范围 A 为 **100% 字节覆盖**（12511/12511）。
- 范围 B 限于**文本类扩展名**；未对工作区全部二进制（数万 `.ff`/`.dll` 等）做全量扫描，故范围 B 的"未命中"**不等于**全局不存在。
- 字符串命中仅证明"文件包含该内容"；用途判定均另附**引用位置/上下文**（见上表"性质"列）。
