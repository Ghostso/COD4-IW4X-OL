# -*- coding: utf-8 -*-
import os, io, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
ROOT=C.ROOT
def W(name,text): io.open(os.path.join(ROOT,name),"w",encoding="utf-8",newline="").write(text)

W("06_HYPOTHESIS_LEDGER.md", """# 06_HYPOTHESIS_LEDGER — 传输用途四分(H1 游戏业务 / H2 ICMP / H3 平台代理 / H4 无法归类)

任务要求:不得仅凭 socket 参数或相邻字符串定论;每项列支持/反证/缺失/下一步。

---

## 判定摘要

| 假设 | 判定 | 置信度 |
|---|---|---|
| H1 游戏业务消息接收/解析 | **部分成立:解析原语已确认;接收点未闭环** | 高(原语)/ BLOCKED(接收点) |
| H2 ICMP/网络诊断 | **成立,但属另一个模块(DLL),非本镜像业务** | 高(041) |
| H3 平台服务/代理(QoS/HTTP/反作弊) | **成立,且已与业务分离** | 高 |
| H4 受保护/覆盖缺口无法归类 | **仅对"接收点"成立** | 高 |

**综合:** 客户端**存在**游戏业务消息解析原语(net-buffer 读取器,`0x87C110/0x87D5A0`);
**接收点**因镜像覆盖缺口 **BLOCKED**;平台 QoS(TQOS)与 libcurl、ICMP 三条辅助路径已与业务分离。

---

## H1 游戏业务消息接收/解析

- **支持证据:**
  1. `0x87A890` sizeinfo 宽度决策(阈值 128/256/65536)与"剩余长度"比较;
  2. `0x87C110/0x87D5A0` 大栈帧解码器入口,按 `[ebx+8]` 类型/宽度多路 + 逐元素搬运;
  3. 诊断串 `0x99EE98..0x99F428` 明确 `net-buffer`/`net_start`/`net_end`/`sizeinfo_size`/`unit_size`。
- **反证:** 目前可复核的唯一直接调用者(`0x85D49D`)属 TQOS 平台;未见可复核的"netchan→业务分派"边。
- **缺失证据:** recv/WSARecv 接收点;缓冲分配/会话对象;游戏消息类型表。
- **下一步静态检查:** 补镜像覆盖 `.tp3 #3/#4/#5` 后,反向追 `0x87C110/0x87D5A0` 的非 TQOS 调用者。

## H2 ICMP / 网络诊断

- **支持证据:** `codoMP_client_shipRetailBase.dll 0x235F7E` = ICMP Echo(ping)(041 机器码级)。
- **反证:** 与客户端引擎 EXE 的 net-buffer 解码器分属不同模块、不同套接字族。
- **缺失证据:** 无(041 已闭合)。
- **下一步:** 无(除上游 `.tvm0` 发起者,已标 BLOCKED)。

## H3 平台服务 / 代理 / 其他辅助通信

- **支持证据:**
  1. TQOS:`0x85D2E0` 对象字段 `QOSCSPkg/Head/Body`、`QOSSSPkg*`,`udp://%s:%d`,`tqos_*`;分派器 `0x85E6F0`;
  2. libcurl/HTTP:`Could not resolve %s:%s`、`proxy`、`CONNECT %s HTTP`、`SOCKS5` 串族;
  3. 反作弊/内核:`[KernelBind]`/`SendPacket Failed`/ACE-DRV32.dll。
- **反证:** 均不具备游戏 netchan 语义(无 netfield 元素类型/状态分派)。
- **缺失证据:** 平台层与业务层的**共享缓冲**边界(是否复用同一读取器)。
- **下一步:** 确认 `0x87C110`/`0x87D5A0` 是否**仅**被平台复用,还是也服务业务。

## H4 受保护/覆盖缺口导致无法归类

- **支持证据:** recv 槽值/地址(`0xCA84E8` 等)与运行期全局(`0x76…`/`0x84…`/`0xE4…`)不在镜像内。
- **反证:** 解析原语本身完全在已覆盖 `.text` 内,已可归类为"net-buffer 解码器"。
- **缺失证据:** 接收点与业务调用者。
- **下一步:** 见 `05`/`07` 的解除条件。

---

## 相邻字符串说明(旁证,不作判定依据)

- `opcode`(`0x891F84` 等)、`netcafe`、`ReadFileEx` 等均为 Lua/调试/其他语境,未与 netchan 上下文绑定。
- `ClientOfflinePackets`/`wpcap` 属平台诊断上报,非业务 netchan。
- 判定依据始终为**指令 + 数据流 + net-buffer 语义串**,非函数名或相邻文本。
""")

W("07_UNKNOWN_BLOCKED.md", """# 07_UNKNOWN_BLOCKED — 未解决问题、原因与解除阻断

**镜像:** `image_best.bin` sha `17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045`
**性质:** 只读静态分析。未启动游戏,无动态调试/注入/hook/内存转储。

---

## 1. 已确认 vs 未确认

| 层级 | 状态 | 说明 |
|---|---|---|
| 游戏网络消息**读取器/解码器** | **CONFIRMED_DIRECT** | `0x87A890`/`0x87C110`/`0x87D5A0` + net-buffer 串 |
| 消息类型**分派(平台层)** | **CONFIRMED_DIRECT** | `0x85E6F0`(TQOS),非业务 |
| 游戏业务消息**接收点** | **BLOCKED** | recv 槽/地址不在镜像覆盖 |
| 游戏业务消息**类型表** | **UNKNOWN** | 未定位 in-match opcode 表 |

> 040/041 的 DLL 侧"无 netchan"仅适用该 DLL 的 `.text` 可达范围,不外推到本 EXE 镜像。

---

## 2. 未解决项

| 编号 | 层级 | 未解决项 | 等级 | 原因 | 解除所需证据 |
|---|---|---|---|---|---|
| U-042-01 | 接收 | `recv/WSARecv` 具体接收点与其 API 名 | `BLOCKED` | IAT 槽 `0xCA84E8/0xCA84E4/0xCA853C` 值落在镜像未覆盖节区 | 覆盖 `VA 0x0E5C9000`+ 的完整镜像 |
| U-042-02 | 数据流 | `0x87C110/0x87D5A0` 的**非 TQOS** 调用者 | `UNKNOWN` | 已覆盖 `.text` 内唯一直接调用者为 TQOS(`0x85D49D`);业务调用者可能在未覆盖节区 | 完整镜像或运行期只读追踪 |
| U-042-03 | 语义 | in-match 应用层消息类型/opcode 表 | `UNKNOWN` | 未定位绑定 netchan 上下文的分派 | 由 U-042-02 承接 |
| U-042-04 | 缓冲 | net-buffer 的分配/`net_start/net_end` 初始化点 | `UNKNOWN` | 初始化可能在未覆盖节区 | 完整镜像 + 数据流 |
| U-042-05 | 保护 | 主 DLL `.tvm0`/`.tls` 内是否含业务入口 | `BLOCKED` | 未解码,不生成 x86 调用图 | `.tvm0` 解码(单独授权) |
| U-042-06 | 平台 | 平台层与业务层是否复用同一读取器 | `UNKNOWN` | 需业务调用者证据 | 同 U-042-02 |

---

## 3. 阻断项(覆盖缺口)

| 编号 | 区 | 事实 | 影响 |
|---|---|---|---|
| B-042-01 | `.tp3 #3` | `VA 0x00A16000`,VSize `0x0DBB1CC0`;镜像仅前 `0x62000` 字节 | 运行期全局/对象不可解析 |
| B-042-02 | `.tp3 #4/#5` | `VA 0x0E5C8000/0x0E5C9000`;镜像仅部分 | recv/WSA 槽值不可解析 |
| B-042-03 | 磁盘 EXE | `.tp3` 加壳(低熵均匀 7.1);线性反汇编不含处理函数 | 不能替代恢复镜像 |
| B-042-04 | 主 DLL | `.tvm0 31MB`/`.tls 15.5MB` 受保护 | 不静态展开 |

**未伪造闭环:** 凡进入未覆盖节区/受保护区的边,一律 `BLOCKED`/`UNKNOWN`。

---

## 4. 反过度声称声明

1. 本报告**不**主张已恢复完整游戏消息格式;仅确认存在 net-buffer 解码原语与平台分派器。
2. 本报告**不**据函数名/相邻串推断协议语义。
3. 本报告**不**主张与 OLD/2697/OL-mod/CoD4x/IW4x 任一实现相同。
4. 本报告**不**把 TQOS 分派器当作游戏业务分派器。
""")

W("08_CROSS_PROJECT_MATRIX.md", """# 08_CROSS_PROJECT_MATRIX — 六方交叉验证就绪度

**原则:** 只有在客户端**消费者与消息语义**获得足够证据后,才可把发现加入跨项目协议矩阵。
任何服务器端既有实现都不能替代客户端证据。

| 项目 | 已知 | 与 042 的对接点 | 就绪度 |
|---|---|---|---|
| **CODOL 客户端(本任务)** | net-buffer 读取器(0x87C110/0x87D5A0)已确认;接收点 BLOCKED | — | **部分** |
| OLD | 服务器侧 netchan(13B 等) | 需客户端消息布局对照 | NOT READY(缺客户端业务语义) |
| 2697 | 服务器侧 netchan | 同上 | NOT READY |
| OL-mod | 待核 | 同上 | NOT READY |
| CoD4x | netfield/msg 语义(公开) | 可与 0x87A890 sizeinfo 128/256/65536 语义对照 | CANDIDATE(仅原语级) |
| IW4x | 同上 | 同上 | CANDIDATE(仅原语级) |

**结论:** 当前仅达到**原语级**可比(`sizeinfo` 宽度阈值、`unit_size/count` 布局)。
**尚不**可比对 opcode/消息语义——需先闭合 U-042-02/03。

**禁止:** 以服务器已实现某协议为由,认定客户端存在对应解析器。
""")

print("wrote 06/07/08")
