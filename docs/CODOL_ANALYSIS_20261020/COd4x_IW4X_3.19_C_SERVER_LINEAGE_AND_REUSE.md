# CoD4x 21.2 / IW4X / CODOL 3.19 C 战服：血缘与借鉴审计

> **阶段标记：初步交叉材料，暂缓使用。**
> 本文早于用户要求的“先三项目独立审计、全部完成后再交叉验证”规则，包含跨项目比较。不得把它当作 CoD4x 或 IW4X 的独立审计结论；正式交叉阶段开始后，必须逐条重新取证并替换本文的临时判断。

日期：2026-10-20（Asia/Shanghai）

范围：只读分析。没有启动游戏、大厅、战斗服或客户端，没有修改受保护的 `REF_LOBBY_KIT`、`CODOL_VERIFIED_GOLDEN_20261019`、原始客户端或任何运行目录。

本文以 **CODOL 3.19.26.22 / Build 1649370** 为目标客户端，讨论“C 语言外部战斗服”可借鉴什么。CoD4x 与 IW4X 是参考实现，不是 CODOL 线协议的替代物。

### 基线审计注记

本次只新增本文。受保护核心（`run_all.py`、`nt10.py`、`lobby_server.py`、`fake_auth_tls.py`、`codol_crypto.py`、`make_local_ca.ps1`）的 SHA-256 均仍与 `_golden_hashes.json` 一致。

但审计同时发现两项**既有**基线异常，不能忽略：

- `REF_LOBBY_KIT/tas_off.flag`、`REF_LOBBY_KIT/poke_off.flag` 存在；当前 `verify_frozen_chain.py` 将二者判为 `runtime-state`，因此整链自检当前返回失败。
- `REF_LOBBY_KIT/marketplace_store.py` 的当前 SHA-256 为 `E44358F0EB951B62C244A136A181952C26850E841D537BCB70EBB0FFC5DD034E`（50,022 B），manifest 期望 `28B4A1BE67DE06F41E789E723F8BEFECF1EA5AC7B2A3CA20CFEF557A6F571A16`（46,226 B）。10 月 16 日之后的多份运行日志均已记录同一 mismatch。

这两项不是本文分析造成的；本文未回滚、改名、删除或修复它们。若把当前 `REF_LOBBY_KIT` 当作“基线完全有效”的来源，必须先按项目规则处理这两项状态。

## 0. 结论先行

1. **CoD4x 21.2 与 CODOL 3.19 不是同一协议实现。** CoD4x 是 Call of Duty 4/IW3 系谱的专用服务器；CODOL 3.19 是 IW4 系谱经过腾讯长期定制的客户端。相同端口和相似函数名不构成协议兼容证据。
2. **IW4X 也不是可直接复用的 CODOL 专服。** 本工作区中的 `IW4X/iw4x-client` 是加载到 Modern Warfare 2 2010 引擎上的 DLL 客户端工程（C++20，构建目标 `SharedLib`），其 dedicated 模式依赖 MW2 进程内固定地址；仓库内没有 CoD4x 那样的 `sv_main.c`/`sv_client.c` 完整专服引擎。
3. **真正可借鉴的是服务器工程逻辑，而不是 wire 常量。** 可迁移的是：单线程帧循环、连接/会话状态机、收发缓冲所有权、分片与重放窗口、快照帧历史和基线裁剪、超时与重连策略、诊断与离线回放。
4. **CODOL 3.19 的最终战斗协议仍有明确缺口。** 本地已有证据能证明 OOB 握手词法、部分接收循环和类型分派表存在；但 in-match `recv -> opcode -> gamestate/configstring/snapshot -> game state` 的完整消费链尚未闭合。因此不能把 2697、legacy3333 或 CoD4x 的 netchan 直接升级成“3.19 已验证实现”。
5. **推荐走“骨架借鉴 + 本地证据驱动”的路线。** 用 CoD4x 的模块边界和生命周期约束 C 服架构；用 IW4X 学习客户端接收/扩展的隔离方式；把 3.19 的状态、opcode 和字段实现保留为显式证据门控。

## 1. 三方身份与血缘

### 1.1 公开可证的谱系

公开资料对 CODOL 的准确描述是“IW 系谱 / 基于 Modern Warfare 2 技术”的社区说法较多，但逐版本源码谱系没有公开权威材料。能稳妥落笔的是：

- CoD4x 21.2 的 README 明确说明它是 Call of Duty 4: Modern Warfare 的服务器修改版；其源码为 IW3 时代引擎底座。
- IW4X 的 README 明确说明它服务于 Call of Duty: Modern Warfare 2 (2009)；代码里 `PROTOCOL = 0x99`，并以 `iw4x.dll` + MW2 客户端为运行形态。
- CODOL 的客户端资源、脚本、引擎命名和本地逆向均落在 IW/IW4 家族；但它包含腾讯定制服务层、反作弊/平台层和长期版本重构。它不是一份公开的 IW4X 源码分支。

因此，正确说法是：

```text
CoD4x 21.2  = IW3 系谱上的开放专服实现
IW4X        = IW4 系谱上的客户端扩展/专服宿主方案
CODOL 3.19  = IW4 系谱上的腾讯定制分支
```

三者可以共享“服务器骨架思想”，不能共享“线上协议事实”。

### 1.2 本地代码证据给出的代际关系

本地旧服务端源码与样本报告显示：

- `EARLY_SERVER_ANALYSIS/13_NATIVE_TAP_BUILD_001/experiment_copy` 是 CoD4x fork，目标标为 CODOL 1.1.1.13；README 明确写着“incomplete port, not playable”。
- 该 fork 的 `src` 与 CoD4x 21.2 共用大量基础文件，但 `sv_main.c`、`sv_client.c`、`sv_snapshot.c`、`msg.c`、`netchan.c` 被大幅改写；CODOL 专用代码集中在 `src/codol`。
- `CODOL_2697_SERVER_STATIC_ANALYSIS_20261011` 分析的是 2.6.9.7 配套的 `codol_dedrun.exe`，并明确记录：2697 是 NEW-only 的独立写通道（`codol_2697_*`），旧 1113/OLD 源码树中不含 2697 源码。
- 当前客户端固定为 3.19.26.22 / Build 1649370，其运行时镜像和 2697 样本不是同一客户端构建；3.19 的客户端消费链仍需单独取证。

你可以把这条代际关系理解为：

```text
1.1.1.13   = CoD4x fork 的早期 CODOL 适配（旧源码可读，协议仍不完整）
2.6.9.7    = 新增 2697 协议/资源适配层的一代（源码不可得，只能反汇编）
3.19.26.22 = 当前目标客户端，腾讯定制深化；不能用 2697 样本直接代替
```

这是一种“骨架延续 + 定制层逐代加厚”的关系，不是三份完全相同源码的连续编译。

## 2. CoD4x 21.2 的可借鉴模块

CoD4x 的优势是完整、可读、单进程 C 服务器实现。对本项目有直接工程价值的模块如下。

### 2.1 初始化与帧循环骨架

可借鉴点：

- `Com_Init -> SV_Init -> SV_Frame` 的显式阶段化初始化；
- `SV_Frame` 固定时间步 + 网络包事件 + 游戏 world 推进 + 客户端消息发送；
- 明确的 server state（未载图/加载中/游戏中）；
- 关服、时间回绕、缓存回绕和客户端超时的集中处理。

为什么值得借：

服务器最容易失控的地方不是加密，而是“初始化、地图切换、连接/断开、快照发送”之间的生命周期。CoD4x 把这些职责拆得清楚，适合作为 C 服主循环模板。

不建议照搬：

- 它的 `sv_fps`、`PACKET_BACKUP`、快照大小和玩家状态布局是 COD4 的；
- 它的 `SV_Frame` 内嵌了大量 COD4 专属子系统（PunkBuster、XAC/更新代理等），不能整体带入 CODOL。

### 2.2 客户端槽位状态机

可借鉴点：

- `CS_FREE -> CS_ZOMBIE -> CS_CONNECTED -> CS_PRIMED -> CS_ACTIVE` 的分层；
- 每个状态只允许特定操作，例如未收到 gamestate 前不能进入 active，首个 usercmd 才触发进入世界；
- 断线后保留 zombie 槽位防止立刻复用；
- challenge、connect、gamestate 重发和重复 connect 的处理位置。

关键价值：把“传输已连”“控制面已握手”“gamestate 已发”“游戏已激活”拆成四个不同概念。3.19 客户端的状态值域与 CoD4x 不同，应借鉴状态边界而不是照抄枚举值。

### 2.3 UDP 地址与 socket 封装

可借鉴点：

- `netadr_t` 和 socket 类型分离；
- IPv4/IPv6 socket 打开、bind、非阻塞、广播、事件 select 的统一封装；
- `NET_OutOfBandPrint/Data` 与普通游戏包分离；
- LAN/loopback 与真实远端地址的不同处理。

不建议照搬：

- CoD4x 的 `0xFFFFFFFF + command` 是 COD4 OOB 线格式；
- CODOL 3.19 的 OOB 接收器有不同命令词表与状态门；
- IW4X 也用 `FF FF FF FF`，但这是 IW4X 的扩展 OOB，不是 CODOL 3.19 已证事实。

### 2.4 netchan、分片和重放窗口

可借鉴点：

- `Netchan_Process` 的“读序列号 -> 丢旧包 -> 组装分片 -> 交给上层”分层；
- 分片状态和消息缓冲由会话对象持有，避免跨连接污染；
- 对越界 fragment length、重复 sequence、乱序 fragment 的明确拒绝；
- 重传大消息时把“未发送缓冲区”和“接收组装缓冲区”分离。

不应照搬：

- CoD4x 的 server 头 4B + client qport 2B 结构与 CODOL 3.19 尚未被绑定；
- 3.19 客户端 P5 接收链虽然已看到 `recv`、长度和单字节分支，但 `recv` 缓冲到对象 payload 的写入点还未闭合；
- 2697 有 29-bit mask、1162×128 分片等常量，但这些常量到 3.19 客户端的绑定仍未完成。

### 2.5 快照历史与 delta 基线

可借鉴点：

- 按客户端保存最近若干帧的 player state / entity state / client state 历史；
- 选择“客户端已确认的旧帧”作为 delta 基线；
- 基线过期时回退为完整帧；
- 新实体从 baseline 发送、删除实体用哨兵/删除语义表达；
- 发送成功后才提交历史，失败时保留可恢复状态。

这是 CoD4x 最值得迁移的“数学逻辑”之一：编码器可以不同，但帧历史、基线选择、过期回退和发送后提交这套不变量是通用的。

不应照搬：

- `snapshotInfo_t`、`playerState_t`、`entityState_t` 的字段与位宽；
- 3.19 的 `0x5F830` 类型分派器与表 A/B 只有“存在和规模”证据，字段语义、位宽和 EOF 边界仍未知；
- 3.19 客户端对 snapshot `0x00` 的实际消费入口尚未闭合。

### 2.6 可靠命令与命令队列

可借鉴点：

- 服务端记录最近可靠命令，客户端 ACK 后裁剪；
- 发送窗口、重发、序号回绕、溢出恢复；
- 把命令字符串与二进制 payload 分开；
- 快照只携带尚未确认的可靠命令。

不应照搬：

- CoD4x 的 `svc_serverCommand` 编号与 `clc_3bit` 布局；
- 2697 的 `0x02 | long | short | data` 格式属于 2.6.9.7 服务端静态事实，不是 3.19 客户端已证事实；
- 3.19 客户端可靠命令的读取与分派仍未闭合。

### 2.7 诊断、限速和错误边界

可借鉴点：

- 对未知包、错误长度、无效状态、重连、超时统一结构化诊断；
- 查询接口按地址和全局速率限制，防止反射放大；
- 只在证据允许的层做 fail-closed，而不是用默认业务处理吞掉未知消息。

这对 3.19 尤其重要：目前最危险的做法不是“少实现一个功能”，而是把未知 opcode 当旧协议处理，制造看似成功但静默丢包的连接。

## 3. IW4X 的可借鉴模块

IW4X 不是 CoD4x 的 C 服务器源码替代品，但它的 IW4 客户端扩展思路非常值得阅读。

### 3.1 客户端/Server 接收分流

IW4X 在 `Network.cpp` 里实现：

- OOB 数据统一前置四字节；
- `OnClientPacket` / `OnClientPacketRaw` 按命令名注册回调；
- 在处理前检查包长度、地址和回调键；
- 对未知包回退到原引擎路径，而不是伪造业务成功。

可借鉴点：

- “协议识别层”和“业务 handler 层”分离；
- 原始包回调保留 msg_t，文本回调只传切片；
- 回调注册表可测试、可观测、可记录来源。

### 3.2 Dedicated 模式的门控与主循环

IW4X 的 `Dedicated.cpp` 展示了：

- 通过 `-dedicated` 选择角色；
- 关闭渲染、音频、启动画面等客户端子系统；
- 初始化 fastfile、执行配置、启动事件循环；
- 定时发送 heartbeat、转发 GUID、重置时间回绕。

可借鉴点：

- 专服角色与客户端角色显式分离；
- 子系统的“禁用”集中管理；
- 专服定时任务独立于游戏帧处理器。

不可照搬：

- 它依赖 MW2 的固定 RVA（如 `0x60BE98`、`0x47DDB2`）和 `iw4x.dll` 注入；
- 这些地址与 CODOL 3.19 客户端不兼容；
- CODOL 的专服启动链与 CoD4x 独立进程不同，更不能把 IW4X 的 hook 方式移入 3.19。

### 3.3 玩家连接认证信封

IW4X 的 `Auth.cpp` 用 protobuf `Proto::Auth::Connect {signature, publickey, token, infostring}`：

- 客户端签名 challenge；
- 服务端按公钥计算 XUID；
- 校验 Steam/XUID/安全等级；
- 然后进入 `SV_DirectConnect`。

可借鉴点：

- 认证是连接前的独立层；
- 认证数据与 engine userinfo 分离；
- 服务端不直接信任 `connect` 中的自述身份；
- 身份、票据、挑战、userinfo 各自有验证边界。

不可照搬：

- IW4X 的 ECC/protobuf/Steam 身份链不是 CODOL 的 TCLS/Demonware/腾讯票据链；
- CODOL 3.19 的 `connect %s "%s"` 与 challengeResponse 载荷仍未完全闭合；
- 不能把 `0x99`、IW4X `connect` protobuf 或它的 `xuid == SHA1(pubkey)[:8]` 规则用于 CODOL。

### 3.4 需要从 IW4X 学习、而不是复制的部分

- 服务器状态文本模型：`getstatus/statusResponse` 的字段组织可以借鉴；
- matchtype / party / dedicated 的分离可以借鉴；
- “协议版本显式选择”和“版本不匹配清晰拒绝”必须借鉴；
- 不可复制的部分是所有固定地址、协议号和 CODOL 未证字段。

## 4. 3.19 本地证据能支持什么

### 4.1 已可进入实现的部分

| 模块 | 3.19 本地证据 | 可做的工作 |
|---|---|---|
| 进程/服务生命周期 | 已有单进程外部战服与运行审计 | 先实现 socket、会话表、帧时钟、超时和诊断 |
| OOB 词表与方向 | `getchallenge 0 "%s"`、`connect %s "%s"`、`challengeResponse`、`connectResponse` 等有客户端 xref | 建解析器、边界检查、状态机骨架；用 `SIMULATED` 夹具测试 |
| 收包驱动 | P5 `0x7A20A0` 的 recv 链与单字节分支有直接静态证据 | 实现“单字节事件 -> 会话对象”的基础层；不把对象构造宣称为 payload 已复制，也不把 P5 自动归为 OOB 或 in-match |
| OOB 分派 | `0x1C13A0` 的 token `strcmp` 与状态转换已证 | 单独实现连接无关命令分派；不把 `0x1C13A0` 当作 in-match opcode |
| 类型分派器 | `0x5F830` 与两套表存在 | 建立 table/evidence registry；解析未知索引时 fail-closed |
| 旧会话生命周期 | 本地 C#/Python 实验已有状态机经验 | 把状态分层迁移到 C，不复制旧协议字段 |

### 4.2 不能直接进入最终实现的部分

| 模块 | 当前缺口 | 正确的临时处理 |
|---|---|---|
| in-match opcode | 未闭合 `recv` 缓冲 -> opcode 读取 -> handler 链 | 用未知 opcode 拒绝 + 结构化记录；保留候选注册接口 |
| P5 业务归属 | `recv`、对象分配和单字节分支已证，但 payload 写入点与上层业务语义仍未知 | 保留为“传输候选”，不得标成 OOB 或 in-match |
| gamestate | 只看到日志串与解析族，没有字段级消费者 | 保留内部 GameStateModel，不输出猜测线格式 |
| configstring | 解析族存在但索引/上界/结束符未知 | 建带边界的本地表，不映射到线上 |
| snapshot | 帧起止、delta 基线、实体增删未知 | 先做帧容器和基线选择算法，保持编码器关闭 |
| reliable command | 客户端读取/ACK 语义未知 | 先做内部序号/重传模型，不生成 3.19 wire |
| usercmd | 只有项目侧实现与实验，官方线格式未闭合 | 作为内部移动模型，不当作最终协议 |

### 4.3 3.19 与 2697 的关系

2.6.9.7 的 2697 报告已经能证明：

- 2697 有独立 `codol_2697_*` 写入层；
- gamestate 使用 `0x03` 起始、`0x06` 终止；
- configstring 使用 `0x04`，尾部 `0x06`；
- reliable command 有 `0x02 | long | short | payload` 新格式，可回退 `0x01`；
- snapshot 是 entities -> clients -> glass -> hud -> `0x06`。

但这仍不等于 3.19：

- 3.19 客户端镜像里 `0x06` 的真实消费者没有定位；
- 3.19 的 `0x03/0x04/0x06` 网络读取路径没有闭合；
- `CODOL2697_PROFILE_WIRE` 的启用条件、注册门控和资源门控尚未运行验证；
- 2697 镜像与 3.19 客户端是不同构建。

因此 2697 对 3.19 的价值主要是“服务端 how-to 参考”，不是“目标协议金样”。

## 5. 推荐 C 服架构

建议把 C 服分为六层，层间只通过有明确所有权的结构通信。

```text
[1] Platform / lifecycle
    signal, clock, logging, config, graceful shutdown

[2] UDP transport
    socket, poll, recv/send, address, datagram budget, rate limit

[3] Session / channel
    OOB handshake, channel state, timeout, reconnect, resend

[4] Wire codec
    exact 3.19 framing (evidence-gated), fragmentation, replay window

[5] World / snapshot
    entity/client/player state, frame history, delta base, visibility

[6] Diagnostics / replay
    hex capture, offline vectors, validation, evidence registry
```

### 5.1 各层不可越界

- Platform 不解释游戏包；
- Transport 不写玩家状态；
- Session 不猜 gamestate 字段；
- Wire codec 不能把未知 opcode 当 legacy；
- World 不知道 socket 细节；
- Diagnostics 不改变业务状态。

### 5.2 建议的最小状态机

```text
NEW
  -> HANDSHAKE_SENT
  -> CHALLENGE_RECEIVED
  -> CONNECT_SENT
  -> CONNECTED
  -> WIRE_ESTABLISHED
  -> PRIMED
  -> ACTIVE
  -> DISCONNECTED
```

其中：

- `CONNECTED` 只表示 OOB connect 层完成；
- `WIRE_ESTABLISHED` 需要 3.19 的真实 data/reliable 层证据；
- `PRIMED` 表示 gamestate 已发送或确认，不能仅凭 UDP 端口打开了就进入；
- `ACTIVE` 需要客户端真实消费者证据。

### 5.3 建议的收包函数分解

```c
int udp_poll_once(server_t *s, uint32_t budget_ms);
int session_receive(server_t *s, session_t *se, const uint8_t *buf, size_t len);
int wire_decode(session_t *se, const uint8_t *in, size_t in_len,
                uint8_t *out, size_t out_cap, size_t *out_len);
int message_dispatch(session_t *se, const uint8_t *msg, size_t len);
```

每个函数都返回“完整/需要更多数据/拒绝原因”，不要用 0/1 混淆“未完成”和“成功”。

## 6. 证据门控

每个实现单元必须带证据标签：

| 标签 | 用途 |
|---|---|
| `E3_19_STATIC` | 3.19 客户端/服务端二进制直接证据 |
| `E2_69_2697` | 2.6.9.7 服务端静态事实，仅参考 |
| `E1_1_COD4X` | CoD4x 源码事实，仅架构/算法参考 |
| `E_IW4X` | IW4X 源码事实，仅 IW4 客户端/扩展参考 |
| `PROJECT_ARTIFACT` | 本地实验实现，未等同官方协议 |
| `UNKNOWN` | 只有接口，不得产生线上字节 |

建议在 C 代码里把“协议实现”和“证据 id”绑定，例如：

```c
typedef struct {
    uint8_t opcode;
    const char *evidence_id;
    int (*handler)(session_t *, const uint8_t *, size_t);
} codol_opcode_entry_t;
```

未带 `evidence_id` 的注册必须被启动期拒绝。这样可避免未来把 2697 或旧协议悄悄混入 3.19。

## 7. 不建议采纳的做法

1. **直接把 CoD4x 的 `sv_main/sv_client/sv_snapshot` 替换进 C 服。** 运行时结构、固定字段和协议版本都会错。
2. **直接把 IW4X 的 `iw4x.dll` 逻辑或 fixed RVA 移入 CODOL 3.19。** 客户端构建、模块布局和保护层不同。
3. **把 2697 写入器当作 3.19 目标协议。** 它只能说明“2.6.9.7 的服务端可能这样写”，不能证明 3.19 客户端会读。
4. **用现有 Python/C# 实跑字节作为 3.19 官方 golden。** 那只是项目产物，不能升级为客户端事实。
5. **未知 opcode 落到 default echo。** 这会让错误在后续变成静默丢包，浪费大量定位时间。

## 8. 立即可以推进的工程顺序

### P0：把参考逻辑变成可测试的 C 模块

- `server_clock`：固定步长、最大帧时间、时间回绕；
- `netadr`：地址规范化、比较、端口字节序；
- `session_table`：槽位、状态、超时、重连；
- `ring_buffer`：接收缓冲、发送缓冲、分片组装；
- `evidence_registry`：协议条目与证据 id。

这些不依赖 3.19 最终 wire，可以先写单元测试。

### P1：实现唯一已具备证据的 OOB 层

- 词表、方向、长度限制、重复请求、挑战超时；
- 所有响应先走 `SIMULATED` 夹具；
- 保留“响应载荷未证”标记，不把模拟字节当 golden。

### P2：闭合 3.19 的接收边

唯一关键问题仍然是：

```text
recv/recvfrom 缓冲 -> 会话对象 payload -> opcode 读取 -> handler
```

在此之前，不要写 gamestate/configstring/snapshot 的 3.19 编码器。可以写容器、边界检查、delta 选择算法和离线测试，但不能输出目标 wire。

### P3：引入服务器级不变量测试

- 同一会话不重复绑定 slot；
- 旧 sequence 被拒绝；
- 乱序/缺片不会误拼；
- 超时/重连不会泄漏 entity；
- 快照只在成功发送后提交 history；
- 未知 opcode 不改变状态机。

## 9. 最终判断

### 血缘

- CoD4x 21.2：IW3 系谱、开放 C 专服、强工程骨架参考。
- IW4X：IW4 系谱、客户端扩展与专服宿主方案，适合学习 IW4 客户端接收/版本边界。
- CODOL 3.19：IW4 系谱的腾讯定制分支，当前目标；其具体服务层和线协议必须由 3.19 证据决定。

### 借鉴价值

| 来源 | 服务器骨架 | 网络传输 | 游戏协议 | 客户端兼容细节 |
|---|---:|---:|---:|---:|
| CoD4x 21.2 | 高 | 高（算法） | 低（COD4） | 低 |
| IW4X | 中（宿主） | 中（IW4 客户端） | 低（MW2/IW4X） | 中 |
| 2697 服务端样本 | 中 | 中（服务端事实） | 中（2.6.9.7） | 低（非 3.19） |
| 3.19 本地逆向 | 待建 | 部分 | 部分/未闭合 | 目标唯一依据 |

### 一句话

**借 CoD4x 的骨架、学 IW4X 的边界、用 3.19 的证据决定字节。** 这条路线既能加速 C 战服工程，又不会把参考实现的协议误当成目标协议。
