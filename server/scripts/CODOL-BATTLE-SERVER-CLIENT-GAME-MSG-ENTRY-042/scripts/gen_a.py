# -*- coding: utf-8 -*-
"""042 deliverable generator. Read-only analysis evidence -> markdown/tsv deliverables."""
import sys, os, io, hashlib, struct, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
ROOT=C.ROOT

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for c in iter(lambda: f.read(1<<20), b''): h.update(c)
    return h.hexdigest()

def W(name, text):
    io.open(os.path.join(ROOT,name),"w",encoding="utf-8",newline="").write(text)

DLL_SHA="ef75220de1d6973f34c7069f5bf211b11bd61520c6c0de1882f7359fa5bc6a20"
IMG_SHA="17cef6e0a5e7b8d14fb97b5fdd846061187c6a722cfa3c5d432bee37872fd045"
EXE_SHA="36997674b18f2896de5e9d755686f6922af10708f355175714058d0a0172b537"

# ---------------- 00_INDEX ----------------
W("00_INDEX.md", """# CODOL-BATTLE-SERVER-CLIENT-GAME-MSG-ENTRY-042

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
""")

# ---------------- 01_EXECUTIVE_SUMMARY ----------------
W("01_EXECUTIVE_SUMMARY.md", """# 01_EXECUTIVE_SUMMARY — 客户端游戏业务消息入口

**目标模块:** CODOL 最终版客户端(恢复镜像 `image_best.bin` 为主)。
**性质:** 只读静态分析。未启动游戏,无动态调试/注入/hook/内存转储。

---

## 1. 核心结论

1. **游戏网络消息读取器已定位(CONFIRMED_DIRECT)。** 恢复镜像 `.text` 内存在一族函数,其诊断串为
   `; net-buffer NOT enough: real_len<%d> sizeinfo_size<%u> net_start<%p> net_end<%p>`(RVA `0x99EE98`)、
   `; string/wstring length error … net_start<%p> net_end<%p> custom_size<%u>`(`0x99EEF0/0x99EF50`)、
   `; wstring from net-buffer format error …`(`0x99F428`)。引用这些串的代码:
   - `0x87A890`(sizeinfo 帮助:按 `unit_size` 计算 sizeinfo 宽度 2/3/4/5,与外部 `[ebp+0x14]` 剩余长度比较),
   - `0x87C110`(解码器入口:`mov eax,0x17F4` 栈帧、参数 5 个、`[ebx + 8]` 类型/元素调度),
   - `0x87D5A0`(另一解码器入口:`0x180C` 栈帧、双缓冲参数校验)。
2. **net-buffer 语义由串与指令双重确认:** `net_start/net_end/real_len/sizeinfo_size` 均为内存指针/长度,
   被 `cmp/jbe/ja` 直接比较与推进 → 这是**网络消息缓冲的部分解析**(不是字符串/本地化/font)。
3. **游戏业务分派器:存在,但在本任务证据中仅确认平台 QoS 层。** RVA `0x85E6F0` 读取 `word [esp+6]`
   (消息类型)并按 `4`/`6` 分派到 `0x85E4F0`/`0x85E5C0`。该对象构造(`0x85D2E0`)使用字段名
   `QOSCSPkgHead/QOSCSPkgBody/QOSSSPkg…` 及 `udp://%s:%d`、`tqos_*` → **TQOS(QoS)平台层**,**非**游戏业务 netchan。
4. **真正的接收点(recv/WSARecv)本轮无法在镜像内取证:** 相关地址(`0x76xxxxxx` 等)属于镜像
   `.tp3 #3+#4+#5`(`VA 0x0E5C9000` 等),恢复镜像**未提供这些节区** → **BLOCKED**。
5. **未据服务器实现外推:** 本任务不使用 2697/legacy/CoD4x/IW4x 结构补客户端语义。

---

## 2. 关键 RVA 一览

| RVA | 角色 | 等级 |
|---|---|---|
| `0x87A890` | net-buffer sizeinfo 帮助 | CONFIRMED_DIRECT |
| `0x87C110` | netfield/元素解码器入口(#1) | CONFIRMED_DIRECT |
| `0x87D5A0` | netfield/元素解码器入口(#2) | CONFIRMED_DIRECT |
| `0x99EE98/0x99EEF0/0x99EF50/0x99EFB8/0x99F290/0x99F428` | net-buffer 诊断串 | CONFIRMED_DIRECT |
| `0x85E6F0` | 消息类型分派器(word[esp+6]→4/6) | CONFIRMED_DIRECT(TQOS 平台层) |
| `0x85E4F0/0x85E5C0` | 分派处理函数 | CONFIRMED_DIRECT |
| `0x85D2E0..0x85ED80` | TQOS QOSCSPkg/QOSSSPkg 对象族 | CONFIRMED_CROSSREF |
| `0x73180` | `gamestateupdate`/`EXE_*CONFIGSTRINGMISMATCH` 处理调用点 | CONFIRMED_CROSSREF |
| `0x1C05F0..0x1C2700` | OOB 连接命令族(`getchallenge`/`connect`/`connectResponse`/`challengeResponse`) | CONFIRMED_DIRECT(连接期,非 netchan) |

---

## 3. 限制

1. 恢复镜像 `image_best.bin` 覆盖 `.text`(`0x1000..0x8a8000`)与部分 `.rdata/.data`(`0x8a8000..0xa65000`);
   `.tp3 #3+#4+#5`(`VA 0x0E5C9000` 等,运行期地址 `0x76xxxxxx`)缺失 → recv/socket 证据 **BLOCKED**。
2. 磁盘 EXE 的 `.tp3` 为加壳/加密(低熵均匀 7.1,线性反汇编不含该处理函数),不能替代恢复镜像。
3. 主 DLL `.tvm0`(31MB)/`.tls`(15.5MB)未解码 → 不生成 x86 调用图。
4. 不据函数名/相邻字符串推断协议语义;net-buffer 结论以**指令 + 数据串**双重支撑。

---

## 4. 下一步(唯一最高价值)

> **补取覆盖 `.tp3 #3/#4/#5`(VA `0x0E5C9000`+)的客户端运行期内存镜像,定位对 `0x87C110/0x87D5A0`
   的调用者与 socket/recv→netchan 缓冲→该解码器的数据流。**

该步解除 `U-042-01`(接收点未闭环)。若无法补取,则退一步:在 `.text` 内做全量 `net_*/recv` 候选与
`0x87C110` 调用者(仅 `0x85D49D`,属 TQOS)之外的第二族调用者扫描。

---

## 5. 明确声明

未执行真实客户端 E2E;未启动游戏。**未宣布**与 OLD/2697/OL-mod/CoD4x/IW4x 任一协议相同。
""")

print("wrote 00/01")
