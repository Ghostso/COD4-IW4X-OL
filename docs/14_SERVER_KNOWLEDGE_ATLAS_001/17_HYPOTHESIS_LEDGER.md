# 17 — 假设台账 / HYPOTHESIS LEDGER

> 每个假设给出：陈述、类别、支持证据、反证、当前状态、可证伪条件、下一步最小证据。
> 状态：`CONFIRMED_BY_EVIDENCE` / `STRONG_INFERENCE` / `WEAK_INFERENCE` / `OPEN` / `REFUTED` / `BLOCKED`

---

## 1. 血统类假设

### H-LIN-01：OLD/1113 服务端是 CoD4x 的 fork
- 类别：H1/H2
- 支持：`q_shared.h:6`/`qcommon.h:6` 字面 "IW4OL source code, a fork of CoD4x"；Jaccard 93–99.7%（EV-R-OldSrc）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**
- 可证伪：找到 OLD 与 CoD4x 均复制自第三份代码的证据
- 下一步：无

### H-LIN-02：OLD 与 1113 是同一源码的两个构建
- 类别：H1/H10
- 支持：216/217 文件字节相同；唯一差异 `g_sv_main.c`（EV-R-OldSrc-1113）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**
- 可证伪：发现更多差异文件
- 下一步：无

### H-LIN-03：2697 与 Old/1113 是同族骨架 + 2697 层
- 类别：H7
- 支持：同 EntryPoint/节区/Characteristics/工具链；仅 9 项导入差异；新增 `codol_2697_*` 模块（EV-S-2697, EV-2697-Modules）
- 反证：无（但缺 2697 源码，无法做行级相似度）
- 状态：**STRONG_INFERENCE**
- 可证伪：2697 与 1113 同名函数控制流哈希显著不同
- 下一步：对 2697/1113 做同名函数控制流哈希（静态）

### H-LIN-04：ol-mod 与 IW4x 无代码血统
- 类别：H11/H12
- 支持：AUDIT.md 明示；IW4/BO1/BO2 仅 CODREF/CODDIFF（EV-R-OlMod-NoIW4x）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**
- 可证伪：找到 ol-mod 引用 IW4x 源码/DLL
- 下一步：无

### H-LIN-05：CoD4x 与 IW4x 共享 Quake3 netchan
- 类别：H1
- 支持：`netchan_t` 布局 1:1（EV-Netchan-IW4x）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**
- 可证伪：发现两者 netchan 有结构性差异
- 下一步：无

### H-LIN-06：CODOL netchan 与 CoD4x/IW4x netchan 是不同实现
- 类别：H5
- 支持：CODOL 头 4/6 B、分片 6 B `{index,last,stride=1162,chunk}`、上限 1162×128；CoD4x/IW4x 头 10 B、上限 0x20000（EV-Netchan-Old/CoD4x）
- 反证：无
- 状态：**STRONG_INFERENCE**（CODOL 语义来自源码，CoD4x 来自源码；未做 2697 二进制验证）
- 可证伪：在 2697 中找到 10 B 头 netchan
- 下一步：在 2697 中定位 netchan 头常量

---

## 2. 协议类假设

### H-PRO-01：2697 reliable `0x02` 与客户端 `0xA2E50` 是同一协议角色
- 类别：H4/H5/H11
- 支持：字段顺序 long4+short2+payload 与上限 0x3FC 双向匹配（EV-2697-RC-Format, EV-C-2697-A2E50）
- 反证：客户端无 `0x02` 比较/分派；E8/E9、VA 指针、RVA 指针、跳转表全 0 命中（EV-C-2697-Dispatch-Blocked）
- 状态：**WEAK_INFERENCE**（形状匹配，绑定未闭合）
- 可证伪：**推翻**——若完整运行时映射中仍无分派；**证实**——若找到分派链或运行时命中
- 下一步：① `.rimp` 指针修复还原；② 运行时 dump/断点

### H-PRO-02：客户端 `0x06` 是 2697 的 EOF/EOS 处理
- 类别：H4/H11
- 支持：服务端多处以 `0x06` 终止（EV-2697-GS-Format, EV-2697-CS-Format, EV-2697-Snap-Outer）
- 反证：客户端无 `0x06` 读取/终止判断；`UNEXPECTED_EOF` 无直接代码引用（EV-C-2697-NoEof）
- 状态：**OPEN / NOT-OBSERVED**
- 可证伪：客户端找到 `0x06` 分支
- 下一步：在 `.tvm0` / 间接跳转表中定位客户端 switch

### H-PRO-03：snapshot 内部 `0x06`（RVA 0xA4CAF）不是外层 EOF
- 类别：H4/H11
- 支持：其后仍有 HUD 与第二遍 actors/entities 写入（EV-2697-Snap-Seq）
- 反证：无
- 状态：**STRONG_INFERENCE**
- 可证伪：抓到完整 snapshot 帧，发现消息在内部 `0x06` 结束
- 下一步：客户端 snapshot 解码闭环

### H-PRO-04：2697 外层终止符由 archive 激活选择 `0x05`/`0x06`
- 类别：H7
- 支持：RVA 0x87104 依 `_CODOL_Target2697ArchivesActive` 分支（EV-2697-Snap-Outer）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**（指令级）
- 可证伪：无
- 下一步：确认 `0x16D` 语义

### H-PRO-05：2697 gamestate 起始 `0x03` 与旧 configstring `0x03` 是不同上下文
- 类别：H7/H11
- 支持：2697 gamestate 起 `0x03` 终 `0x06`；旧 configstring `0x03` 终 `0x05`（EV-2697-MsgTypes）
- 反证：无
- 状态：**STRONG_INFERENCE**
- 可证伪：找到统一 opcode 表
- 下一步：恢复 2697 通道的 opcode 表

### H-PRO-06：CODOL 战斗通道未使用标准 DTLS
- 类别：H5/H12
- 支持：OpenSSL 字符串是静态链接自带表（EV-DTLS-OpenSSL）；有 bdDTLS 风格自定义记录层
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**（“未使用标准 DTLS”）
- 可证伪：找到调用标准 DTLS API 的调用链
- 下一步：无

### H-PRO-07：COOKIE_ECHO 189 B（1.1.1.13 系列）
- 类别：H4
- 支持：`codol_handshake.c:47` `n == 189`；OFFLINE_001 裁决 B 对 1.1.1.13/22011 成立
- 反证：C#、DEV-BOOKING-021 记 219 B（EV-DTLS-Conflict）
- 状态：**OPEN（对 1.1.1.13 已裁决；对 2.6.9.7 UNKNOWN）**
- 可证伪：C-2697 抓包
- 下一步：抓 C-2697 握手

### H-PRO-08：2697 需要“注册导出”门控才能发布 gamestate
- 类别：H6/H8
- 支持：双门控指令级 + withheld 返回 0（EV-2697-Gate）；注册文件格式与 sscanf 模板匹配（EV-Registration）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**（机制）；**OPEN**（合法放行路径完整与否）
- 可证伪：找到绕过门控仍发布 gamestate 的路径
- 下一步：恢复 5 字段语义与 `+0x78F4` 设置路径

### H-PRO-09：内部 codec 187 与出站 protocol 1 是两个不同层
- 类别：H11
- 支持：`codol_wire.h:8` `CODOL_PROTOCOL 187`；`codol_connect.c:91` 出站 `protocol 1`；实机二分 187 卡住、1 能连（EV-Protocol-Conflict）
- 反证：无
- 状态：**STRONG_INFERENCE**
- 可证伪：找到两者一致的路径
- 下一步：抓 connectResponse

---

## 3. 架构类假设

### H-ARC-01：OLD/1113 生命周期来自公共 Quake3/CoD 骨架
- 类别：H1/H3
- 支持：源码（EV-Old-Init/Frame/Recv）+ 版权链（Id/Ninja/TheKelm）
- 状态：**CONFIRMED_BY_EVIDENCE**
- 可证伪：发现自有实现
- 下一步：无

### H-ARC-02：ol-mod 是“重用原生引擎内核 + 插件重实现控制面”
- 类别：H5/H9
- 支持：AUDIT.md（Injector32/Bootstrapper32 + 三个 lifecycle exports）；`FrameHook`/`EngineBindings`
- 状态：**STRONG_INFERENCE**
- 可证伪：找到独立引擎实现
- 下一步：核对 `EngineBindings.cpp` 的原生函数绑定

### H-ARC-03：平台层（TCLS/IIPS/TenProxy）不参与游戏战斗通道
- 类别：H8/H9
- 支持：平台层在启动/认证阶段；游戏通道由战斗 socket 独立（EV-Battle-Endpoint/EndpointParser）
- 状态：**STRONG_INFERENCE**
- 可证伪：发现平台层参与游戏 socket 调用链
- 下一步：确认战斗 socket 创建者

### H-ARC-04：`--codol-info` 分支不开 socket
- 类别：H4
- 支持：`sys_main.c:509-517` 打印后 `return 0`
- 状态：**CONFIRMED_BY_EVIDENCE**
- 下一步：无

---

## 4. 项目专属假设

### H-2697-01：2697 层在运行期被激活需要特定 CVar/配置
- 类别：H7
- 支持：`codol_target2697*` CVar；诊断串依赖 archive 激活
- 反证：无
- 状态：**BLOCKED**（运行时未观测）
- 可证伪：运行一次观察
- 下一步：静态追踪 CVar 读取点

### H-2697-02：`0x16D` 是 archive 代次/版本标识
- 类别：H7
- 支持：`_CODOL_Target2697ArchivesActive` 判 `[edx+0x34] == 0x16D`
- 反证：无
- 状态：**OPEN**（STATIC-INFERENCE）
- 可证伪：找到该字段的写者
- 下一步：追踪 `+0x34` 写入点

### H-2697-03：2697 `scripts`（1,341 文件）含协议相关逻辑
- 类别：H6
- 支持：脚本/overlay 与 2697 配套
- 反证：未核验
- 状态：**BLOCKED**（未逐文件解析）
- 下一步：离线脚本内容聚类

### H-2697-04：2697 `runtime-assets`（1.71 GB）含 2697 专属协议/资源索引
- 类别：H7
- 支持：目录体积与 archive 挂载诊断串
- 反证：未核验
- 状态：**BLOCKED**
- 下一步：资源清单与 FF 头解析

### H-CLI-01：C-2697 恢复镜像与运行时映射不等价
- 类别：H11
- 支持：`.tp3` 未恢复；`.rimp` 改写 `.rdata` 指针表；`.tvm0` 非线性岛；无 dump（EV-C-2697-Rec-Limits）
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**（等价性未证明）
- 可证伪：获得运行时 dump 且比对一致
- 下一步：运行时 dump（需授权）

### H-CLI-02：opcode 分派位于未恢复的 `.tp3`/`.tvm0` 或运行时 VM
- 类别：H11
- 支持：无直接/间接调用者；存在非线性代码岛
- 反证：H4（客户端根本不支持该 opcode）未排除
- 状态：**OPEN**
- 可证伪：完整运行时映射中仍无回调/分派
- 下一步：`.rimp` 恢复 + 运行时 dump

### H-OPS-01：客户端不进入战斗因“上游 accepted 门”未关闭
- 类别：H9
- 支持：监听 28960 时 `BATTLE_RX=0`（EV-Battle-RX0）
- 反证：无
- 状态：**STRONG_INFERENCE**
- 可证伪：观察到客户端开始发包
- 下一步：关闭 DEV-BOOKING-020 accepted 门

---

## 5. 假设统计

| 状态 | 数量 | 编号 |
|---|---|---|
| CONFIRMED_BY_EVIDENCE | 11 | H-LIN-01/02/04/05, H-PRO-04/06/08(机制), H-ARC-01/04, H-CLI-01 |
| STRONG_INFERENCE | 9 | H-LIN-03/06, H-PRO-03/05/09, H-ARC-02/03, H-OPS-01 |
| WEAK_INFERENCE | 1 | H-PRO-01 |
| OPEN | 4 | H-PRO-02/07, H-2697-02, H-CLI-02 |
| BLOCKED | 3 | H-2697-01/03/04 |
| REFUTED（见 16 §7） | 5 | REV-001..005 |

---

## 6. 最高价值待决假设（决定后续方向）

| 排名 | 假设 | 为什么重要 | 最小证据 |
|---|---|---|---|
| 1 | H-PRO-01（0x02 ↔ 0xA2E50） | 决定 2697 客户端能否消费可靠命令 | `.rimp` 还原 或 运行时 dump |
| 2 | H-CLI-02（分派在 `.tp3`/`.tvm0`/VM） | 决定所有客户端侧静态结论的上限 | 运行时 dump |
| 3 | H-PRO-08（注册门控合法路径） | 决定能否合法发布 gamestate（进大厅总线） | 5 字段语义 + `+0x78F4` 路径 |
| 4 | H-CLI-01（恢复镜像等价性） | 决定客户端静态证据是否可信 | 运行时 dump 比对 |
| 5 | H-OPS-01（accepted 门） | 决定能否让客户端进入战斗拨号 | 关 020 accepted 门 |
---

# === 追加：第二轮验证后的假设状态更新（UPDATE-2, 2026-10-12） ===

> 本轮实际执行了 E-01/E-02/E-03/E-04/E-05/E-06/E-14/E-15。原始输出见 `_analysis\RAW_RESULTS_BUNDLE.txt`。

## 状态变更表

| 假设 | 变更前 | 变更后 | 依据 |
|---|---|---|---|
| H-LIN-06（CODOL netchan 与 CoD4x/IW4x 不同实现） | STRONG_INFERENCE | **CONFIRMED_BY_EVIDENCE** | R-17：2697 二进制含 `0x489`/`0x24500`/`0x70CC729`，与 CODOL `codol_wire.h` 常量精确对应 |
| H-LIN-03（2697 = 同族骨架 + 2697 层） | STRONG_INFERENCE | **CONFIRMED_BY_EVIDENCE（符号 + 常量双证）** | R-17（常量）+ R-06（legacy writer 并存） |
| H-PRO-03（内部 `0x06` ≠ 外层 EOF） | STRONG_INFERENCE | **CONFIRMED_BY_EVIDENCE（指令级）** | R-18/E-03：`0xA4CAF` 写 6 之后仍 `call 0x49f2e5`(HUD)、`0x4a1a65`(entities) |
| H-PRO-05（旧/2697 通道并存） | STRONG_INFERENCE | **CONFIRMED_BY_EVIDENCE** | R-17（`_CODOL_NetchanProcess` 在 OLD/1113/2697 均存在，RVA 不同） |
| H-PRO-01（`0x02` ↔ `0xA2E50` 同协议角色） | WEAK_INFERENCE | **WEAK_INFERENCE（未变；负面证据加强）** | R-14/R-15：`.text` 0 调用且扫描可靠性 95.1% |
| H-CLI-01（恢复镜像 ≠ 运行时） | CONFIRMED_BY_EVIDENCE | **CONFIRMED_BY_EVIDENCE（量化）** | R-12：`.data` 仅 0.14% 在文件内 |
| H-CLI-02（分派在 `.tp3`/`.tvm0`/VM） | OPEN | **OPEN（范围收窄）** | R-14：分派不在 `.text` 线性直接调用图；候选 = `.tvm0` 未解码部分 / 缺失 `.data` / 运行时回调 |
| H-2697-03（scripts 含协议逻辑） | BLOCKED | **REFUTED（就“协议逻辑”而言）** | R-20：1,341 脚本仅 15 个含相关标记，均为游戏逻辑脚本 |
| H-PRO-08（注册门控机制） | CONFIRMED(机制)/OPEN(路径) | **CONFIRMED(机制)/CONFIRMED(格式链)/OPEN(5 字段业务语义)** | R-19：三变体格式串 + `sscanf` 返回 3 + kind∈{1,2} + CRC + `+0x6408` |
| H-PRO-09（codec 187 vs 出站 1） | STRONG_INFERENCE | STRONG_INFERENCE（未变） | 本轮未触及 |

## 新增假设

### H-CLI-03：候选 vtable 位于缺失的 `.data`（99.86%）
- 类别：H11
- 支持：R-12（`.data` 声明 0x0D05C420，仅 0x49600 在文件内）；但 R-13 显示已存在的 0.14% **确实含** 2,375 个 →`.text` 指针
- 反证：若 `0xA2E50` 从不通过 vtable 调用，则缺失 `.data` 不解释零调用
- 状态：**OPEN**（与 H-CLI-02 并列，不互斥）
- 可证伪：获得运行时 `.data` 或完整恢复后仍无指向 `0xA2E50` 的表项
- 下一步：运行时 dump；或还原 `.rimp`/`.tp3` 中 `.data` 初始化来源

### H-CLI-04：`.tvm0` E8/E9 命中不可作调用者证据
- 类别：H11
- 支持：R-15 —— `.tvm0` 内 29,474 个 E8 字节，目标在映像内的 23,184 个中，落在函数入口的 = **0**（0.0%）；而 `.text` 为 95.1%
- 反证：无
- 状态：**CONFIRMED_BY_EVIDENCE**
- 影响：直接**排除**“`.tvm0` 单条命中 = 调用者”的推理（此前 F2/F3 已正确地不采纳该命中，本轮给出定量依据）

## 方法学修正记录（自查）

| 项 | 内容 |
|---|---|
| 错误 | 第一轮 `_analysis` 早期脚本把 **VA** 当作 **RVA** 传入区段映射，误得“`0xA2E50` 位于 thunk 中段（真实入口 0x4A2E40）”的中间结果 |
| 发现 | 用交接值双向校验映射（`0x1AC1D0→0x1AB5D0`、`0xA2E50→0xA2250`）时发现不一致 |
| 纠正 | 改为 `file_offset = PointerToRawData + (RVA − VirtualAddress)`；重跑全部扫描 |
| 纠正后结论 | 与既有 F2/F3 报告**一致**（`.text` 0 调用） |
| 保留 | 错误中间结果与纠正过程一并保留，供审计（H11“分析工具造成假象”的实例） |

---

# === 追加：E-09 后的假设台账（UPDATE-4, 2026-10-12） ===

## 状态变更

| 假设 | 变更前 | 变更后 | 依据 |
|---|---|---|---|
| **H-CS-01**：客户端存在 configstring body 消费者 | OPEN/BLOCKED | **CONFIRMED_BY_EVIDENCE**（RVA 0xA2660） | EV-09-02 |
| **H-CS-02**：两侧字段顺序一致 | UNKNOWN | **CONFIRMED_BY_EVIDENCE**（逐字段） | EV-09-02 |
| **H-CS-03**：`count1` = 16 位 | WEAK | **CONFIRMED_BY_EVIDENCE** | EV-09-03 |
| **H-CS-04**：`count1` = 8 位 | OPEN | **REFUTED** | EV-09-03 |
| **H-CS-05**：`0x06` 端到端终止 | BLOCKED | **PARTIAL**（服务端闭合 / 客户端 BLOCKED） | EV-09-04/05 |
| **H-CS-06**：A1 字符串占位（位流） | 隐含假设 | **REFUTED**（不占位） | EV-09-04 |
| **H-CLI-05**：客户端共享位读取器 = 0x1A07B0 | （E-08 记为事实） | **REFUTED** → 实为 **0x1AC670** | EV-09-01 |

## 新增假设

### H-CS-07：外层消息分派器读取 `0x04`/`0x06`
- 类别：H4（协议规范）
- 支持：服务端有明确 `0x04`/`0x06` 写入；客户端 `0xA2660` 无此逻辑 ⇒ 必在别处
- 反证：可能在 `.tvm0` 或运行时；
- 状态：**OPEN**（BLK-7）
- 可证伪：若在 `0xA2660` 的调用者链中找不到任何读 `0x04`/`0x06` 的 switch
- 下一步：对 `0xA2660` 的 3 个调用者（`0x3512A0` / `0x352E80`）做控制流还原，并向上追踪

### H-CS-08：`0x06` 是"位流内 8 位常量"
- 类别：H4
- 支持：写入侧解析为 `WriteByte(6)`（= `WriteBits(6,8)`），与其它字段共用位游标
- 反证：读侧未定位；若客户端按**字节**对齐定位，则为"外部标记"
- 状态：**OPEN**（BLK-8）
- 可证伪：找到客户端读 `0x06` 的位级比较，或抓到一段 body 后 `0x06` 落在非字节边界的真实帧
- 下一步：同 H-CS-07

## 假设统计（E-09 后）

| 状态 | 数量（含前几轮） |
|---|---|
| CONFIRMED_BY_EVIDENCE | 15（+4） |
| STRONG_INFERENCE | 9 |
| PARTIAL | 2（+1） |
| OPEN | 6（+2） |
| REFUTED | 8（+3） |
| BLOCKED | 3 |
