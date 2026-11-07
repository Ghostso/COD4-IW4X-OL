# -*- coding: utf-8 -*-
import sys,os
sys.stdout.reconfigure(encoding="utf-8")
os.chdir(os.path.dirname(os.path.abspath(__file__)))
def W(n,s): open(n,"w",encoding="utf-8",newline="\n").write(s); print("wrote",n,len(s))

W("07_A_BLOCKERS_STATUS.md", r"""# 07_A_BLOCKERS_STATUS

**核心工作包 E:** 五项 A 类关键客户端语义问题最新状态 + 固定权重闭环率。
**基线:** 045 `07_SERVER_READINESS_ISSUE_LEDGER.tsv` / `08_NEXT_ACTION_DECISION.md`。
**口径纪律:** 权重、分母、定义**未变**;045 历史统计**保留**为基线,可对比。

---

## 1. 固定权重与闭环率(先定后算,口径未改)

沿用 043/045 的 A/B/C 分类与权重(A=79,B=16,C=6,合计 101);
**只计入被完全关闭的项**;部分解决不计。

| 口径 | A(权重79) | B(16) | C(6) | 合计(101) |
|---|---|---|---|---|
| 043 基线 | 0 | 3 | 6 | 9 |
| **045 基线** | **10 (12.7%)** | 3 | 6 | **19** |
| **046(本轮)** | **17 (21.5%)** | 3 | 6 | **26 (25.7%)** |

### 1.1 本轮唯一新增的 A 类关闭项

| 项 | 权重 | 关闭依据 |
|---|---|---|
| **A-09**(平台层 TQOS 与业务层边界未证分离) | **7** | 本任务**证得** 045 链 `0x85D96E→0x87BA50→0x87D5A0` 整体属 `tqos_create_protohandle` 的 TQOS/TDR 路径,并证得游戏协议串区(TQOS 之外)与 TQOS 群**无交叉引用** → 边界**已可证分离**。见 `02`、`06` M10 |

**说明(防止误读):**
- A-09 的关闭是**边界定义**的关闭,与 042/045 的**协议语义**归因错误被纠正直接相关;
  **不是**新增移动资料带来的。
- A-01(10)仍计入 045 的已关闭权重(API 身份已定:`select`/`recv`/`WSAGetLastError`);
  但本任务**收窄其业务含义** —— 它证明的是"存在 socket 原语",**不**证明"存在游戏收包点"。
- A-02 保持 `OPEN`(见 §2),**不计**入已解决权重。

### 1.2 显式声明

> 哈希通过、脚本通过、函数数量、边数量、六方矩阵条目数 —— **都不代表**协议还原完成度。
> 对下列**五项关键客户端消费语义**,本轮解决率仍为 **0%**。

---

## 2. 045 A-01…A-09 逐项最新状态

| ID | 权重 | 045 状态 | 046 状态 | 本轮依据 |
|---|---|---|---|---|
| A-01 | 10 | CLOSED_BY_045 | **CLOSED**(身份) / 业务含义收窄 | `02` §1.2~1.3;045 `03_IO_PATH_EVIDENCE.tsv` |
| A-02 | 10 | PARTIALLY_RESOLVED | **OPEN(重述)** | 045 链为降为平台内部边;游戏消息解码入口仍**未定位** |
| A-03 | 9 | OPEN | **OPEN** | in-match opcode 表仍未定位;仅 TQOS 信封类型域已知 |
| A-04 | 9 | OPEN | **OPEN** | `gamestateupdate` 串 xref 已定位(`0x54B7B`/`0x73214`)但**消费链未闭合** |
| A-05 | 9 | OPEN | **OPEN** | `EXE_CONFIGSTRINGMISMATCH` xref 已定位(`0x731E1`/`0xF2833`)但**读取/存储未闭合** |
| A-06 | 9 | OPEN | **OPEN(收窄)** | `0x87D5A0` 归 TDR;snapshot 网络解码**仍未定位** |
| A-07 | 8 | OPEN | **OPEN** | 工程裁决项,本轮不消解 |
| A-08 | 8 | OPEN | **OPEN** | `EXE_LOSTRELIABLECOMMANDS` xref 已定位(`0xF2737`/`0x376B14`)但**分派未闭合** |
| A-09 | 7 | PARTIALLY_RESOLVED | **CLOSED** | `02` 全链归因 TQOS;`06` M10 边界分离 |

---

## 3. §七要求的"五项关键客户端语义问题"逐项评估

对每项:现有证据 / 移动资料是否提供新证据 / 缺失的最小证据 / 可静态解决部分 / 受恢复映像限制部分 / 下一步最低成本取证。

### 3.1 Gamestate

| 项 | 内容 |
|---|---|
| 现有证据 | 串 `gamestateupdate %d`(VA `0xDB4700`)被 `0x54B7B`、`0x73214` 引用;`CA_GAMESTATE`(`0x1C809D`);`EXE_AWAITINGGAMESTATE`(`0x20C14C`)。**均为低地址区,与 045 链无交叉** |
| 移动资料新证据 | **无**(移动资料不含 gamestate 线格式) |
| 缺失最小证据 | 从一个"读包缓冲"到 gamestate 状态转换的**直接数据流** |
| 可静态解决 | 对 `0x54B7B`/`0x73214`/`0x1C809D` 做上游调用者 + 缓冲来源分析 |
| 受限部分 | 第3节区(`RSize 0x62000`)不可读 |
| 最低成本取证 | 静态:从上述 xref 反查读取点(无需新样本) |
| 状态 | **OPEN / UNKNOWN** |

### 3.2 Configstrings

| 项 | 内容 |
|---|---|
| 现有证据 | `EXE_CONFIGSTRINGMISMATCH`(`0x731E1`,`0xF2833`);`EXE_POSSIBLECONFIGSTRINGMISMATCH`(`0x731CF`);`ExpectedNetConfigStringMismatch`(`0x778D7`);另有 `mp/constBaselinesTable.csv` 等资产路径 |
| 移动资料新证据 | **无** |
| 缺失最小证据 | 客户端 configstring 索引→字符串存储的指令级读/写点 |
| 可静态解决 | 对 `0x731E1`/`0xF2833`/`0x778D7` 反查 |
| 受限部分 | 同上 |
| 状态 | **OPEN / UNKNOWN** |

### 3.3 Snapshot

| 项 | 内容 |
|---|---|
| 现有证据 | 045 的 `0x87D5A0` 被本任务**改判为 TDR**;项目侧 snapshot 写侧 `CodolMotionSnapshot.cs` + 宽度表 |
| 移动资料新证据 | 有,但**仅项目侧**:宽度表(`DIRECT_ARTIFACT`);trace 未完成 |
| 缺失最小证据 | 官方 snapshot 的**分帧 + netfield + EOF** 客户端解码链 |
| 可静态解决 | 从游戏协议串区找 snapshot/EOF 读取点 |
| 受限部分 | 第3节区 |
| 状态 | **OPEN / UNKNOWN** |

### 3.4 opcode

| 项 | 内容 |
|---|---|
| 现有证据 | 仅 TQOS 信封类型域(`0x85E6F0`,`word[esp+6]`);**不是** in-match opcode |
| 移动资料新证据 | **无** |
| 缺失最小证据 | `读 opcode → 分派表 → handler` 的可复核指令链 |
| 可静态解决 | 在游戏协议串区附近找 `switch/cmp` 分派 |
| 受限部分 | 见 §3.1 |
| 状态 | **OPEN / BLOCKED(业务表)** |

### 3.5 reliable commands

| 项 | 内容 |
|---|---|
| 现有证据 | `EXE_LOSTRELIABLECOMMANDS`(`0xF2737`,`0x376B14`)、`EXE_SERVERCOMMANDOVERFLOW`(`0xF26C7`)、`EXE_ERR_RELIABLE_CYCLED_OUT`(无 xref);045 记录的 `0x01/0x02` 形状来自 2697 = `REPORT_ONLY` |
| 移动资料新证据 | **无**(但 `CodolClientCommandReader.cs` 的 `opcode==2 → seq(4)+ASCII string` 与"可靠命令"**形状相似**,仅 `STRUCTURAL_SIMILARITY_ONLY`) |
| 缺失最小证据 | 客户端 `0x01/0x02`(或本项目实际编号)的读取 + 入队点 |
| 可静态解决 | 从 xref 反查 |
| 状态 | **OPEN / UNKNOWN** |

---

## 4. 与 045 的可比性声明

- 旧口径(043/045)与本轮口径**完全一致**(权重、分母、定义均未改)→ **可直接比较**。
- 变化量:`A 10→17`(+7,仅 A-09);`总计 19→26`。
- **五项关键项解决率 045 = 0%,046 = 0%(不变)。**
- 因此:**即使 A 类闭环率升到 21.5%,仍远不足以宣称"具备完整的服务器协议实现依据"。**
""")
print("DONE")
