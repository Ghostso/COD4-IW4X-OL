# CODOL-BATTLE-SERVER-CLIENT-GAME-MSG-ENTRY-042

**任务:** 定位**最终版客户端游戏业务消息接收与解析入口**的可复核静态证据链。
**前置:** 040(Battle DLL 网络绑定) / 041(recvfrom 0x235F7E = ICMP ping,非业务)/ 038/039(应用层入口 UNKNOWN)。
**日期:** 2026-10-13 (Asia/Shanghai)  **性质:** 只读静态分析(未启动游戏;无动态调试/注入/hook/内存转储;
未修改原始 EXE/DLL/恢复镜像/正式源码/FREEZE-005)。
**工作目录:** `CODOL-BATTLE-SERVER-CLIENT-GAME-MSG-ENTRY-042`(独立)。

---

## 0. 一句话结论

在**恢复镜像 `image_best.bin`(CODOL Client EXE, sha `17ce…f045`)**的 `.text` 内,**已直接定位到游戏网络
消息缓冲读取器**(`net-buffer` 语义,RVA `0x87a890/0x87c110/0x87d5a0` 等)与**消息结构解码器**
(`0x87c110` 入口,条件/循环操作基于 `[ebx + 8]` 字段/元素类型与位宽与元素数,可解析
`sizeinfo+payload` 网络布局。功能族判为 **CoD netfield/delta 反序列化**(`CONFIRMED_DIRECT`)。
镜像内同时解析出 TQOS(QoS)消息分派器(`0x85e6f0`,消息类型字 `word [esp+6]` 分派 4/6),
并判为 **平台 QoS 层,非游戏业务**(`CONFIRMED_DIRECT`)。

**接收点(recv/WSARecv)本身**:位于镜像未提供的后续节区
(`.tp3 #3` + 运行期地址 `0x76xxxxxx/0x84xxxxxx/0xe4xxxxxx`),当前恢复镜像**未包含** →
`BLOCKED`。因此"接收点 → 消息读取器"这一边在本任务内**未闭环**,不伪造。

---

## 1. 三层判定(验收口径)

| 层级 | 本任务判定 | 依据 |
|---|---|---|
| 游戏业务消息**读取器/解码器** | **CONFIRMED_DIRECT** | `image_best.bin` `.text` 内 `0x87a890/0x87c110/0x87d5a0`;`net-buffer` 诊断串 `0x99EE98..0x99F428` |
| 游戏业务消息**类型分派** | **CONFIRMED_DIRECT(仅 TQOS 平台层)** | `0x85e6f0` 读 `word[esp+6]` 分派 4/6;`QOSCSPkg/QOSSSPkg`+`udp://`+`tqos_*` |
| 游戏业务**接收点(recv)** | **BLOCKED** | recv slot/地址 `0x76…/0x84…/0xe4…` 不在恢复镜像覆盖范围 |

---

## 2. 三模块身份

| 模块 | 文件 | SHA256 | 地址约定 | 状态 |
|---|---|---|---|---|
| 客户端引擎(恢复镜像) | `image_best.bin` | `17ce…f045` | ImageBase `0x400000`;`file_offset = RVA = VA-0x400000` | **主要证据来源** |
| 客户端引擎(磁盘 EXE) | `codoMP_client_shipRetail.exe` | `3699…b537` | `.tp3` 加密/加壳;线性反汇编不可靠 | 仅作身份对照 |
| 引擎模块(磁盘 DLL) | `codoMP_client_shipRetailBase.dll` | `ef75…6a20` | ImageBase `0x10000000`;`.tvm0/.tls` 受保护 | 网络边界=ICMP ping(041) |

---

## 3. 交付物

| 文件 | 内容 |
|---|---|
| `01_EXECUTIVE_SUMMARY.md` | 结论/限制/下一步 |
| `02_CLIENT_NET_TRANSPORT_MAP.md` | 客户端网络传输层次图与模块归属 |
| `03_MESSAGE_ENTRY_CANDIDATES.tsv` | 消息入口候选逐项证据 |
| `04_NET_BUFFER_READER.md` | net-buffer 读取器/解码器指令级证据 |
| `05_RECEIVE_PATH.md` | 接收路径(socket→recv→buffer)与 BLOCKED 边界 |
| `06_HYPOTHESIS_LEDGER.md` | ICMP / libcurl / 平台代理 / 游戏业务 四分 |
| `07_UNKNOWN_BLOCKED.md` | 未解/阻断项与解除条件 |
| `08_CROSS_PROJECT_MATRIX.md` | 六方交叉验证就绪度 |
| `SHA256SUMS.txt` / `FILE_HASH_MANIFEST.tsv` | 完整性校验 |
| `evidence/` | 反汇编转储、字符串归属、调用点 |
| `scripts/` | 只读分析脚本 |

## 4. 状态定义

`CONFIRMED_DIRECT`(机器码直接) / `CONFIRMED_DATAFLOW`(可追踪数据流) / `CONFIRMED_CROSSREF`(交叉引用) /
`CONFIRMED_ABSENT`(范围内穷举否定) / `CANDIDATE` / `UNKNOWN` / `BLOCKED`(保护区/覆盖缺口)。
