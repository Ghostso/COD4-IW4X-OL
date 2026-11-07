# CODOL-TARGET-PROTOCOL-TRACE-009 — 3.19.26.22 大厅 / 战斗 / 交接链静态追踪

**任务性质：** 只读静态协议取证与边界确认（大厅 A / 战斗 B / 交接 C 三层独立建账）。
**日期：** 2026-10-13（Asia/Shanghai）
**目标版本（本轮固定）：** CODOL **3.19.26.22**，Build **1649370**，构建日期 **2021-05-07**
**目标游戏目录：** `D:\BaiduNetdiskDownload\使命召唤OL\COD OL`
**代码修改：** 无。未改服务器源码、FREEZE-005、原始游戏文件、原始抓包与运行时镜像。产物仅写入本目录。

---

## 1. 首要结论（必须先读）

1. **存在一份与目标版本直接绑定的协议证据源：** `_e1_regression\ol-mod-olfinal`（分支 `OLfinal-live`）在源码中以 `CODREF(1649370)` / `CODDIFF(1649370)` 标注，且其引擎绑定常量为
   `ExpectedTimestamp = 0x6096930A`、`ExpectedImageSize = 0x0E5D6000` —— 与本轮目标 EXE 的 PE 时间戳 `0x6096930A` 相同，属**同一构建（1649370）**。
   其 `references\client_probe\CodolJoinTrace.py` 注释明确写出「**Current 3.19.26.22 IDB**」。
2. **三层协议可以分别给出函数级边界**，且全部落在目标 EXE 映像内（`SizeOfImage 0x0E659000`）：
   - **A 大厅**：Demonware 大厅协议（`LobbyProtocol`，加密消息 `0x86`，阶段 clientHeader→clientAuth→established）+ 匹配/预约（`mmbook/mmstart`）。
   - **B 战斗**：DTLS 风格握手（NAT/INIT/COOKIE）→ netchan（序列/分片）→ 服务端命令 `0..5` → gamestate/configstring/snapshot 解析。
   - **C 交接**：`mmbook` → `accepted` 应答 → 客户端 `[matching+0x288]` 闩锁 → `mmstart` → 战斗端点。
3. **交接链当前卡在客户端闩锁**：所有历史运行中 `[matching+0x288]` **从未为 1**，`mmstart` 从未被构造/发送，`BATTLE_28960` **NOT_OBSERVED**。这是「大厅→战斗」唯一已定位的缺失跳变。
4. **战斗接收链已能给出分派顺序**（packetEvent → netchanProcess → decodeMessage → parseServerMessage → parseGameState/parseConfigStrings/parseSnapshot → parsePacketEntities/Clients/Aux → readDelta…），但**帧内位宽与 delta baseline 仍未逐字段闭合**。
5. 本轮**不修改任何源码**，不宣称客户端可交互进图，不进入协议实现。

---

## 2. 目标二进制核验（分析对象先行）

| 对象 | 路径 | 大小 (B) | SHA-256 | PE 时间戳 | SizeOfImage |
|---|---|---:|---|---|---|
| 入口 EXE | `COD OL\codoMP_client_shipRetail.exe` | 7,841,344 | `36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537` | `0x6096930A` | `0x0E659000` |
| 主引擎 DLL | `COD OL\codoMP_client_shipRetailBase.dll` | 60,327,992 | `ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20` | `0x5E552E55`(2020-02-25) | `0x3991000` |
| DLL 重定向变体 | `...\codoMP_client_shipRetail.exe.local\...Base.dll` 及 `...Base.dll.local\...` | 60,327,992 | `3d2b338da69f2544fe29db8d3da3b3c2de92f5de9e8b5a9fb085a4c4ecc20dfd` | 同主 DLL | 同主 DLL |

**纪律：** EXE 与两个 DLL 必须分别登记；变体与主 DLL **仅差 6 字节**（`0x27D80C..0x27D811`），RVA/函数边界不得混用而未声明。

**运行时镜像（已解壳，非本轮生成）：** `CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin`，10,899,456 B，映射 `VA 0x00400000..0x00E65000`。其为当前客户端的解壳映像，是 `CodolJoinTrace.py` 中「Current 3.19.26.22 IDB」地址的落地载体。

---

## 3. 证据源清单（含位置与身份）

| 编号 | 证据 | 位置 | 与目标关系 | 等级 |
|---|---|---|---|---|
| E1 | 目标 EXE/DLL/变体 | `COD OL\*` | 目标本体 | CONFIRMED |
| E2 | 运行时解壳镜像 | `CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin` | 目标 EXE 解壳映射 | CONFIRMED（身份）/ 只读 |
| E3 | 客户端 PE/网络文档 | `COD OL\docs\{protocol.md,network-9goals.md,game-net-hunt-report.md,net-familyAB-report.md,rt-report-game3.md}` | 目标 DLL | CONFIRMED |
| E4 | 客户端反汇编/数据流工程 | `COD OL\scripts\*` | 目标 DLL | CONFIRMED |
| E5 | 模块加载记录 | `COD OL\ICH042_stdout.txt` | 目标 EXE+DLL | CONFIRMED |
| E6 | 真实抓包 | `run_codol_001\runs\*\pktmon.pcapng` | 目标族 | CONFIRMED（族级） |
| E7 | **1649370 绑定协议源码** | `_e1_regression\ol-mod-olfinal`（`OLfinal-live`） | 同构建（`0x6096930A`） | 参照系（须标 REFERENCE） |
| E8 | **3.19.26.22 客户端探针** | `ol-mod-olfinal\references\client_probe\{CodolJoinTrace,CodolNetchanTrace,CodolFrameTrace,CodolCgameState,CodolStartGame}.py` | 目标 EXE（EXE-relative RVA） | 强（脚本注释标注版本） |
| E9 | 预约/交接链规格 | `DEV-BOOKING\*.md`（001–030） | 目标 EXE | CONFIRMED（静态） |
| E10 | 变体 6 字节差 | 本目录 `VERSION_AND_HASH_MANIFEST.tsv` | 目标 DLL | CONFIRMED |

> **来源冲突纪律：** E7 的 `AGENTS.md` 声明其目标为「3.3.3.3 QA 客户端」，但**同仓库的 `EngineBindings` 常量与 `client_probe` 注释指向 1649370 / 3.19.26.22**。本轮按任务要求：**凡 E7 结论，只有在目标 EXE 中独立命中同一 RVA 时才升级**；否则标 `REFERENCE`。

---

## 4. 三层链路图（三张独立图，不合并）

### 4.1 A 层 — 大厅链（LOBBY）

```
[TCLS/Client.exe] --CreateProcess--> [WeGameLauncher/launcher.exe]
        |                                      |
        | 凭据 -q:/uid=/key=/ID=                | 拉起
        v                                      v
[TCLS 共享内存 TCLS_SHAREDMEMEMORY] --> [codoMP_client_shipRetail.exe]
                                               |
                                (Demonware 大厅流)
   host: formal-zone-lsg.codol.qq.com:3074 / formal-zone-auth.codol.qq.com:3074
                                               |
        LobbyProtocol: phase clientHeader -> clientAuth -> established
        frame: 加密消息 messageType=0x86, 带 AES + HMAC + 序列号
                                               |
                              服务/任务分发 (ServiceRegistry)
                  service 0x06 task 14 = Messaging::sendGlobalInstantMessage
                                               |
                          payload: 0a <u64 SessionId> 13 08 <len> <u32 25> "mmbook ..." 00
                                               |
                                        [匹配对象 matching]
                                  [this+0x278] = BOOKING_PENDING/ACTIVE
                                  reservation array @ this+0x75D8 (stride 0x238)
                                  index slot @ this+0xE360 ; A/B @ this+0x3A048/0x3A04C
                                               |
                          accepted 应答: 13 08 <u32 15> "mmbook accepted"
                          解析器 0x00632680  ->  成功写 [esp+0x28]=1  (0x00632745)
                                               |
                                    [matching+0x288] 预约闩锁
                          唯一消费者 0x00634402  ->  mmstart 构造器 0x00632070
```

### 4.2 B 层 — 战斗链（BATTLE）

```
[战斗服务器 UDP 端点]  (目标端点未观测; BATTLE_28960 = NOT_OBSERVED)
        |
        | 连接无包(带外):  FF FF FF FF + "getchallenge" / "connect" / "gamestateupdate" / "heartbeat"
        | profile stats:  <ProfileStatsPrefix> + chunkIndex + payload
        v
[DTLS 风格握手]
   NAT 探针 (首字节 0x0D -> 应答 0x0C)
   INIT (type 0x02)  ->  INIT_ACK (38B cookie)
   COOKIE_ECHO       ->  COOKIE_ACK (114B: 67B bdCommonAddr + 8B securityId + 100B ECDH 公钥)
   派生: digest(20B) -> aesKey(16B) / hmacKey(24B) / iv(seq, tag)
        |
        v
[非带内数据包解析]  packetEvent 0x00467520
        |
        v
[netchan] netchanProcess 0x005A5960   (CODREF 一致)
   sequence mask 0x1FFFFFFF ; 分片 1154B ; 最多 128 分片 ; 最大消息 0x20000
   flags: 0x80000000 分片 / 0x40000000 可靠 / 0x20000000 分片确认
   分片头: sequence(4) | index(1) | lastIndex(1) | stride(2) | length(2)
        |
        v
[decodeMessage 0x0046BF80]  ->  [parseServerMessage 0x0046E6A0]
        |
        |  服务端命令 opcode（OLfinal 取值：0/1/2/3/4/5，无 6）
        +--> 0 snapshot        -> parseSnapshot 0x0046D170
        +--> 1 serverCommand   (文本)
        +--> 2 binaryCommand   (二进制文本)
        +--> 3 gamestate       -> parseGameState 0x0046DEA0
        +--> 4 configstring    -> parseConfigStrings 0x0046DB20
        +--> 5 EOF             (OLfinal 终止符；3.3.3.3 为 6)
        |
        +--> parsePacketEntities 0x0046C2F0 / parsePacketClients 0x0046CC60 / parsePacketAux 0x0046C840
        +--> parseMatchState 0x0046D060 / parsePlayerState 0x005A4230
             readBit 0x00400C370 / readBits 0x005A13A0 / readFieldIndex 0x005A3250
             readDeltaField 0x005A27F0 / readDeltaEntity 0x005A3670
             playerStateFields 0x00855F70 (235 fields x 12B)
        |
        v
[连接状态机]  connectionState 0x0162E7EC ; encodedClientActive 0x0162E838
   Free -> Connected(connect) -> ClientLoading(gamestate 到达) -> Active(gamestateupdate stage=6)
```

### 4.3 C 层 — 交接链（BRIDGE，与 A/B 分开）

```
[A 层输出] "mmbook <A> <B> ..."  经 service 0x06 / task 14
        |
        v
[服务端预约应答]  accepted blob
   13 08 13 00 00 00 | 0f 00 00 00 | "mmbook accepted"
   (u32 前缀 + 15B 文本, 无 NUL)
        |
        v
[客户端 accepted 解析器 0x00632680]  (ret 0x14, 5 参数)
   必须回显 A/B:  [ebp+8] == [this+0x3A048], [ebp+0xC] == [this+0x3A04C]
   成功副作用: 0x00632745 写 [esp+0x28] = 1
        |
        v
[matching+0x288] 闩锁  --(唯一消费者 0x00634402)-->  mmstart 构造器 0x00632070
        |
        v
[B 层输入]  mmstart 命令 / 战斗端点(地址+端口)
   状态: [matching+0x288] 从未为 1  =>  mmstart 从未发送  =>  BATTLE_28960 NOT_OBSERVED
```

---

## 5. 三层边界一句话总结

- **A 大厅边界**：Demonware 加密帧（`0x86`）之内是服务/任务（`service 0x06 / task 14`）；大**厅出口**是 `mmbook` 预约请求与 `accepted` 预约应答。
- **B 战斗边界**：UDP 带外包（`FF FF FF FF` + 文本命令）与 DTLS 数据包（type `0x06`）是**入口**；netchan 之后是服务端命令 `0..5` 的**分派**；`3/4/0` 分别进入 gamestate / configstring / snapshot。
- **C 交接边界**：`accepted` 应答 → `[matching+0x288]` 闩锁 → `mmstart`。这是**独立于 A/B 的第三层**，因为它的失败点（闩锁未置 1）不在任何一层的网络解析里。

---

## 6. 交付物清单

| 文件 | 内容 |
|---|---|
| `00_INDEX.md` | 本文件（摘要 / 目标版本 / 文件索引 / 三张链路图 / 结论） |
| `LOBBY_PROTOCOL_TRACE.md` | A 层：大厅分派链、消息、状态机 |
| `BATTLE_PROTOCOL_TRACE.md` | B 层：战斗接收/分派/初始化/快照消费链 |
| `LOBBY_BATTLE_BRIDGE.md` | C 层：交接数据、调用链、状态时序 |
| `PROTOCOL_BOUNDARY_MATRIX.tsv` | 函数/消息/端点/字段的协议归属与证据等级 |
| `CALL_CHAIN_EVIDENCE.tsv` | 调用者/被调用者/RVA/数据流/证据出处 |
| `STATE_TRANSITION_MATRIX.tsv` | 状态转换触发条件与证据 |
| `UNKNOWN_AND_BLOCKERS.md` | 未定位消费者、未确认字段、下一步最小任务 |
| `VERSION_AND_HASH_MANIFEST.tsv` | 全部分析对象路径/哈希/PE 身份/版本关联 |
| `SHA256SUMS.txt` | 本轮交付物完整性清单 |

---

## 7. 验收标准回答（见各专项文件详证）

1. **大厅收发与分派边界**：Demonware 加密帧 `0x86` + 服务/任务注册表；`service 0x06 task 14` 承载 `mmbook`。详见 `LOBBY_PROTOCOL_TRACE.md`。
2. **战斗收发与分派边界**：UDP 带外 + DTLS `0x06` → packetEvent → netchan → decodeMessage → parseServerMessage → `0..5`。详见 `BATTLE_PROTOCOL_TRACE.md`。
3. **大厅→战斗状态转换**：由 `accepted` → `[matching+0x288]` → `mmstart` 驱动；当前该闩锁未闭合。详见 `LOBBY_BATTLE_BRIDGE.md`。
4. **被战斗连接实际消费的大厅数据**：`mmbook` 的 A/B 配对号（`[this+0x3A048/0x3A04C]`）必须被 `accepted` 回显；战斗端点字段来源 `UNKNOWN`。
5. **进入 gamestate/configstring/snapshot**：`connect` → `ClientLoading`（gamestate 到达）→ 命令 `3/4/0` 分派；`gamestateupdate stage=6` 才 → `Active`。
6. **证据等级**：见 `PROTOCOL_BOUNDARY_MATRIX.tsv`（`CONFIRMED`/`INFERRED`/`REFERENCE`/`UNKNOWN`）。
7. **本地战斗服务器缺口**：见 `UNKNOWN_AND_BLOCKERS.md` §最小条件。

---

## 8. 执行结论（简明）

- **已确认链路**：目标 EXE 身份；战斗接收/分派顺序与 netchan 常量；DTLS 握手分组形状；服务端命令 `0..5`；大厅服务/任务与 `mmbook` payload 形状；`accepted` 字节与解析器地址。
- **未确认边界**：snapshot 逐字段位宽与 delta baseline；`accepted` 的调用者与传输通道；战斗端点（地址/端口）来源；`[matching+0x288]` 为何未置 1。
- **对本地最终版战斗服务器的直接影响**：可据此实现/校正**战斗入口（DTLS + netchan + 命令分派）**，但**必须**同时解决 C 层闩锁，否则客户端不会发出任何战斗首包。
- **下一项最小任务**：**单变量回归实验 031** —— 以 ol-mod 存档形态的 `accepted` blob（带 u32 前缀）重放，观察 `[matching+0x288]` 是否 0→1 且客户端是否构造/发送 `mmstart`。这是唯一能解锁 B 层实测的最小验证。
- 未达证据条件时不进入协议实现、不修改冻结基线。
