# COLLECT_319_20261021_132905 入库审计

日期：2026-10-21（Asia/Shanghai）

输入：`run_codol_001/runs/COLLECT_319_20261021_132905`

状态：**ACCEPTED AS PARTIAL / LATE_CAPTURE / ACE_BLOCKED**

本文件只核对已封口包、将负证据/部分证据登记到第三轮门槛。没有启动客户端、战斗服、Auth、Lobby、IIPS、dumpcap 或任何服务；没有改写 run 内证据，也没有尝试补齐迟到流量。

## 0. 判定

| 项目 | 结果 |
|---|---|
| 单次启动 | 是；同一客户端 PID `11744`，`client_launches=1`，`relaunch_attempted=false` |
| 进入大厅 | 是，manifest 明确记录 |
| 抓包时序 | **迟到**；开始于 `13:46:21.963` |
| 保留抓包 | 3 帧 TCP / 776 B，仅本地回环 `127.0.0.1:63903 <-> 127.0.0.2:3074` |
| 战斗搬运 | 1 个 4 B 载荷 `00000000`，服务端 `ACK`，客户端随后 `RST` |
| UDP 28960 | 0 帧 |
| gamestate / configstrings | 0 |
| snapshot / ACK 链 | 0 |
| consumer trace | 空占位，未采集 |
| 运行时镜像 | 0 / 58,969 页可读，全部错误 299；`BLOCKED_AFTER_ACE` |
| FF | block-0 解出 `IWffs100` / `mp_firingrange`；layer-2 和世界资产未解 |
| 第三轮线协议/可玩性 | **仍为 BLOCKED** |
| 封口入库 | `ACCEPTED AS PARTIAL`；完整性通过，不能进入协议/可玩性对照 |

这份样本的价值是“明确证明当前路径为何不闭合”，不是“得到了一局战斗的等价样本”。它没有关闭任何 P0 前置项，也没有改变 2697/3.19/CoD4x/IW4X 的交叉结论状态。

## 1. 包完整性与清单

独立复算：

| 检查 | 结果 |
|---|---|
| `hashes.sha256` 条目 | 103 |
| 格式可解析 | 103 / 103 |
| 对应文件存在 | 103 / 103 |
| SHA-256 吻合 | 103 / 103 |
| 缺失/不可读 | 0 |
| 哈希失败 | 0 |
| 清单覆盖字节 | 24,138,601 B |
| `hashes.sha256` 自身 | 不计入清单；manifest 说明其为自引用排除项 |
| 关键文件哈希 | 见下表 |

关键独立复算：

| 文件 | 字节 | SHA-256 |
|---|---:|---|
| `network/packets.pcapng` | 776 | `F644AB1921E884BD445B52BD87BB7503CFC14E3CBB2EF801554099116CE651E6` |
| `image_live/sections.json` | 1,835 | `E6194AF83666A7947DB9BB18AB157D1CC6B538ED7FD125CC4683FA54D6E18ACE` |
| `image_live/image_pages.raw` | 0 | `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` |
| `ff_layer2_probe/block0.bin` | 4,096 | `CFF95D709867445BFC1D443936EDF91FC1DDA9C7EB785BD6AC6ED2F5BBF19777` |
| `consumer_trace.jsonl` | 129 | `5CB72F2539974059D42356632A19DFC867930F969A4CD7F4449FBDEAB143A3D1` |
| `network/stream_reassembly.bin` | 4 | `DF3F619804A92FDB4057192DC43DD748EA778ADC52BC498CE80524C014B81119` |

### 1.1 自描述摘要时序差异

manifest 中 `hashes_file_sha256` 为 `A83F1CF9...F1F6`；当前 `hashes.sha256` 实际摘要为 `A6CCA88A...C455`。同时：

- 当前 `capture_manifest.json` 实际摘要为 `568C2C9B...D91F`；
- 当前 `hashes.sha256` 内部记录的 `capture_manifest.json` 行正是该摘要。

这不是证据文件哈希失配，而是 manifest 与哈希文件互相描述的时序残留：manifest 中的哈希文件摘要记录的是较早修订。manifest 自身写明了 `hashes_file_note`，且 103 条内容哈希全部吻合。本审计将其登记为**封口自引用差异**，不修改任何 run 文件、不伪造新的“封口后哈希”。

## 2. pcapng 独立解析

按 pcapng Enhanced Packet Block 重新解析，结果与索引一致：

| 帧 | 方向 | TCP 标志 | 载荷 |
|---|---|---|---|
| 1 | `127.0.0.1:63903 -> 127.0.0.2:3074` | `PSH,ACK`（`0x18`） | 4 B `00000000` |
| 2 | `127.0.0.2:3074 -> 127.0.0.1:63903` | `ACK`（`0x10`） | 0 |
| 3 | `127.0.0.1:63903 -> 127.0.0.2:3074` | `0x14`（`ACK,RST`） | 0 |

注意：`packet_index.csv` 的 `tcp.flags.str` 列把第 3 帧显示成近似 `A·R` 的点号占位，这是 Wireshark 文本过滤表示，不是第四种网络栈语义；原始 TCP flags `0x14` 明确为 ACK+RST。

对协议判定：

- `00000000` 只是 4 字节应用数据，不能仅凭长度/内容命名为 challenge、connect、gamestate、snapshot 或 netchan 包；
- 没有 SYN、握手初包或前后文，无法恢复服务端状态机；
- 1 个客户端载荷 + 1 个服务端 ACK + 客户端 RST 不构成双向游戏会话；
- 没有 gamestate、configstrings、snapshot、ACK 历史或可识别的 netchan 序号链；
- 过滤后的 3 帧全部是 TCP；这不能证明“战斗只走 TCP”，也不能否定缺失的 UDP/28960 或 netchan 路径；`acks.csv` 只是这三帧的 TCP ACK 字段，不是游戏层 ACK 表。
- 3 帧 776 B 是过滤后保留样本，不是原始全量抓包；manifest 记录未过滤原始包 52,131,740 B、40,999 帧、包含无关宿主流量/凭据，已删除且不在证据包内。该原始包的 `7B9B...DF8E` 摘要只能证明“曾存在一个被删除的包”，不能用于恢复其内容。

因此，`R3-A03` 仍是 `NOT_CAPTURED`；`R3-A04`、`R3-A05`、consumer trace 的缺失不是推理错误，而是本 run 明确没有相应帧。

## 3. 运行时镜像

`image_live/sections.json` 记录：

- PID `11744`；
- ImageBase `0x400000`；
- SizeOfImage `0xE659000`；
- page size `4096`；
- 总页数 `58,969`；
- 可读页 `0`；
- 不可读页 `58,969`；
- 错误码 `299 = ERROR_ACCESS_DENIED`；
- `complete=false`。

`image_pages.raw` 是 0 B，SHA 为空内容哈希；`pages.jsonl` 逐页记录 `UNREADABLE`。这说明 ACE 介入后读路径被阻断，而不是“镜像中全为 0”或“抓全了但没有写入”。

关键影响：

- 不能覆盖 `RVA 0xCA8400..0xCA8700`；
- 不能恢复 IAT；
- 不能追踪后期读包/分发代码；
- 不能把 `.tp3` 节目录或 SizeOfImage 当成函数体证据；
- 不能把 0 B raw 当成完整 dump。

正确状态是 `BLOCKED_AFTER_ACE`；下一次必须在启动前后与读取时都满足可读性/权限条件，而不是在 ACE 之后重复轮询。错误 299 连续 58,969 页不应被改写成“部分镜像”。

## 3.1 页表/页状态独立统计

对 `image_live/pages.jsonl` 逐行解析，得到：

| 项 | 复算 |
|---|---:|
| 页记录 | 58,969 |
| `READABLE` | 0 |
| `UNREADABLE` | 58,969 |
| 错误 299 | 58,969 |
| 其他错误码 | 0 |
| 原始页文件 | 0 B |

这与 `sections.json` 的 `pages_read=0`、`pages_unreadable=58969`、`raw_bytes=0` 一致。它同时证明：没有任何一页被成功读到；后续所有“读不到”都应归因于访问控制，而不是页表缺失、未提交页或地址换算。

## 4. Fastfile block-0

独立查看 `ff_layer2_probe/block0.bin`：

- 前 8 B 是 ASCII `IWffs100`；
- 后续可读 zone 名包含 `mp_firingrange`；
- block-0 已解出，但只有 4,096 B。

manifest 的状态是：

```text
block0_decrypted = true
inner_magic = IWffs100
zone_name = mp_firingrange
layout_status = BLOCK0_ONLY_LAYOUT_MISMATCH
layer2_asset_index = NOT_DECODED
```

这说明：

- `IWffs100` 是解出的内层头，不应与外层 `IWff0100/IWffu100` 混为一谈；
- 旧工具 `OlfinalFastfile.py` 的 body 对齐和 block-zero digest 假设不适用于此文件；
- `CLIPMAP_MP`、`MAP_ENTS`、ComWorld、physics 均未导出；
- block-0 解出不等于 Zone 目录已经覆盖或资产内部布局已兼容。

因此 `R3-A07` 只能登记为 `PARTIAL_BLOCK0_ONLY`。任何后续 FF 工作都应从独立的 layer-2 规格/布局恢复开始，而不是继续按旧脚本强行切块。

## 5. 保护清单与单次启动

manifest 记录：

- 冻结入口 `REF_LOBBY_KIT/run_all.py`，SHA `2AAA...CDA6`；
- 客户端 EXE SHA `3699...B537`；
- PID 11744；
- 单次启动，未自动重启；
- 进入大厅；
- 未过滤原始抓包删除原因是凭据/无关宿主流量。

保护清单摘要：

| 字段 | 值 |
|---|---|
| 检查项 | 9 |
| 与 golden 匹配 | 8 |
| 预存冲突 | `marketplace_store.py`（实际 50,022 B，golden 期望 46,226 B） |
| 本 run 是否改坏该文件 | 否，manifest 记为 `changed_by_this_run=false` |
| `write_dwauth` 额外文件不在 manifest | 是 |
| 运行副本 | `run_all.py`、`nt10.py` 被覆盖 |

这里的“8/9”不能写成“保护文件全部通过”。`marketplace_store.py` 是**运行前既有冲突**，不是本 run 新引入，也不是可忽略项。它会影响后续对冻结链的完整性与可复现性判断；应按 baseline 冲突处理，而不是直接改写或重建 golden。

`write_dwauth` 额外生成文件同样需要作为运行产物登记，不能因为未被 golden 枚举就当成无影响。

## 6. 进程与清理

manifest 的 addendum 记录了：

```text
dumpcap = false
client = false
ports_3074 = 0
udp_28960 = 0
iips_auth_lobby_battle = false
```

这与用户给出的“当前没有客户端、dumpcap、3074 监听或 28960 UDP 端点”一致。本审计只核对声明与包内证据；没有重新启动进程，也没有重新探测本机端口。

清理对证据解读的影响：

- 迟到抓包是不可补齐的，不能靠事后重放或从摘要推断 Auth/Lobby 首段；
- 被删除的未过滤 pcap 不可恢复为本包证据；保留的 3 帧仅可作为负证据；
- 0 B 镜像不是“等待后自动可读”的暂态，而是一次 `ERROR_ACCESS_DENIED` 封口结果；
- 封口后仍应保留“事后已无 3074/28960”的证据，但不应把它解释为协议不存在。

## 6.1 运行时间线：迟到抓包的可证边界

manifest 明确给出：

| 事件 | 时间（Asia/Shanghai） | 是否在抓包内 |
|---|---|---|
| run 创建 | `13:29:05.221` | 否 |
| 抓包开始 | `13:46:21.963` | 起点 |
| 未过滤抓包首包 | `13:46:22.173` | 是（原包已删） |
| 保留游戏流首包 | `13:46:46.169` | 是 |
| 保留游戏流末包 | `13:47:10.771` | 是 |
| run 封口 | `14:08:00` | 否 |
| addendum | `14:16:00` | 否 |

另外，用户给出的 Auth/TLS 与首段 Lobby 发生在 `13:44:27`，早于抓包开始。因此本包的“未采集”不是“流量未发生”，而是**采集启动晚于事件**。这会把 Auth/Lobby 的缺失归为 `LATE_CAPTURE`，不是 `NOT_PRESENT_IN_SCOPE`。

对下一轮的要求因此不是仅“抓 3074”，而是先证明 dumpcap 已运行，再进行唯一一次冻结链启动，并保持同一 PID 直到实际进入战斗。

## 7. P0 重新映射

| 前置项 | 本 run 贡献 | 状态 |
|---|---|---|
| R3-A01 完整加载镜像 | 0/58,969 页，ACE 阻断 | 仍开放；负证据成立 |
| R3-A02 recv → payload → consumer | 无消费链 | 仍开放；`NOT_BOUND` |
| R3-A03 同 PID 双向战斗 | 3 帧过滤流，1 个 4 B 载荷 | 仍开放；`NOT_CAPTURED` |
| R3-A04 gamestate/configstrings | 0 帧 | 仍开放 |
| R3-A05 两帧 snapshot/ACK | 0 帧 | 仍开放 |
| R3-A06 状态/字段消费 | 无 consumer trace | 仍开放 |
| R3-A07 layer-2 世界资产 | block-0 only；布局冲突 | 仍开放；`PARTIAL_BLOCK0_ONLY` |
| R3-A08 Pmove/trace | 无 | 仍开放 |
| R3-A09 规则 | 无 | 仍开放 |
| R3-A10 2697 原始包 | 无 | 仍开放 |
| R3-A11 booking/端点点下发 | 无 | 仍开放 |

`p0_closed = 0 / 11`。本包相较上一轮多了一个明确的“迟到/ACE/零战斗”负结果，而不是一个可开始线协议对照的正样本。

## 8. 为什么不能启动第三轮对照

不能满足以下任一必要条件：

1. **同一 PID 的完整时间线**：本 run 的抓包起点晚于 Auth/TLS 和首段 Lobby，且没有战斗建立过程。
2. **双向真实战斗流量**：只有单个 4 B TCP 载荷 + ACK + RST；没有 gamestate/configstrings/snapshot、ACK 链、fragment 或可靠重传。
3. **同一会话的 consumer trace**：consumer_trace 是明确空占位，不是“从 3 帧里推断出来的空结果”。
4. **完整可读镜像**：0 页可读，错误 299，且是 ACE 之后。
5. **世界资产可解析**：只有 FF block-0，旧 layer-2 布局冲突，资产族均未导出。

缺少任一项时，不能把 `127.0.0.1:3074` 的 4 B 样本称为 netchan 起点，也不能把 ACE 阻断后的零镜像解释为“3.19 代码不可见但可重构”。正确的下一轮是**新 run 中先抓包，再单次启动冻结链，再实际进入一局**；不是修补本 run。

## 9. 下一轮准入与采集顺序

只允许在新 run 目录中进行；本 run 已封口，不再追加。

最低采集顺序：

1. **先启动 dumpcap**，确认捕获设备与过滤器，再启动冻结链；记录 capture start < client process creation < Auth/TLS < Lobby < battle。
2. **单次启动**原始冻结链，禁止自动重启；失败则在新的 run 重试，而不是复用本目录。
3. **保持同一 PID**；在进程创建后先验证可读性，再进入战斗；若 ACE/保护导致 299，立即登记为阻断，不进行无意义全页轮询。
4. **捕获真实战斗**：至少一对双向应用载荷、gamestate/configstrings、两帧 snapshot 与 ACK；保存未过滤原始包或经严格脱敏的可复现过滤方案。
5. **采集 consumer trace**：recv buffer → length → opcode → parser → state delta，必须能与同一帧的字节对应。
6. **导出世界资产**：先完成 layer-2 zone 目录，再导出 CLIPMAP_MP/MAP_ENTS/ComWorld/physics；不要把 block-0 当 layer-2。
7. **保存清理前后进程状态**、保护文件前后哈希和 baseline 冲突，不把“停止进程”当成协议成功。

成功门槛不是“看到某个窗口”或“抓到任意 3074 帧”，而是同一 PID、同一会话、完整双向链、可对应的 consumer 变更和资产可用性同时成立。

## 10. 入库判定

**Integrity**：通过。103 条文件哈希全部复算一致，0 缺失，0 不匹配。封口自引用差异已登记，不改写原包。

**Evidence completeness**：不通过。迟到抓包、0 字节镜像、0 UDP/28960、无 gamestate/snapshot/ACK、无 consumer trace，FF 只有 block-0。

**Protocol/playability**：不启动。当前不能形成第三轮线协议、兼容性或可玩性结论。

**Process/cleanup**：按 manifest/addendum 登记为已关闭；本审计未重新启动任何组件。

**Overall**：`PARTIAL / LATE_CAPTURE / ACE_BLOCKED`。这是有价值的负证据包，不能替代同 PID 双向战斗会话。

## 11. 与先前第三轮审计的关系

- 不修改 `THIRD_ROUND_INTAKE_AUDIT.md` 对上一包 60 文件 / 58 哈希的既有判定；
- 不修改 `THIRD_ROUND_PREREQUISITES.md` 的 P0 开放状态；
- 不修改 CoD4x/IW4X 的独立冻结；
- 不修改 2697/3.19 的 `UNKNOWN` 矩阵；
- 不把 `Welcome_CODOL_client-main` 的客户端研究方法混入本 run 的协议证据。

本包只新增一条第三轮负证据链：**迟到抓包 + ACE 后不可读 + 3 帧 TCP/3074 占位 + FF block-0 only**。

## 12. 证据入口

- [CAPTURE_CLOSURE.md](D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/runs/COLLECT_319_20261021_132905/CAPTURE_CLOSURE.md)
- [capture_manifest.json](D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/runs/COLLECT_319_20261021_132905/capture_manifest.json)
- [hashes.sha256](D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/runs/COLLECT_319_20261021_132905/hashes.sha256)
- [sections.json](D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/runs/COLLECT_319_20261021_132905/image_live/sections.json)
- [packets.pcapng](D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/runs/COLLECT_319_20261021_132905/network/packets.pcapng)
- [block0.bin](D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/runs/COLLECT_319_20261021_132905/ff_layer2_probe/block0.bin)
- [packet_index.csv](D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/runs/COLLECT_319_20261021_132905/network/packet_index.csv)
- [consumer_trace.jsonl](D:/BaiduNetdiskDownload/使命召唤OL/run_codol_001/runs/COLLECT_319_20261021_132905/consumer_trace.jsonl)
