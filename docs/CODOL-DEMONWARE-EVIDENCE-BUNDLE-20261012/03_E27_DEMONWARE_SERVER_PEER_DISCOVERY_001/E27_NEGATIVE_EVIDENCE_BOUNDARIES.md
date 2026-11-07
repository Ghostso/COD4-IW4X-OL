# E27 负向证据与边界

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
