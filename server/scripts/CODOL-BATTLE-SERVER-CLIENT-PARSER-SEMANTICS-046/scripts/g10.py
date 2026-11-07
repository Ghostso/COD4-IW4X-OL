# -*- coding: utf-8 -*-
import sys,os
sys.stdout.reconfigure(encoding="utf-8")
os.chdir(os.path.dirname(os.path.abspath(__file__)))
def W(n,s): open(n,"w",encoding="utf-8",newline="\n").write(s); print("wrote",n,len(s))

W("06_SIX_WAY_CROSS_VALIDATION.md", r"""# 06_SIX_WAY_CROSS_VALIDATION

**核心工作包 D:** 六方协议/架构对照(延续 045)+ 新增移动物理维度。
**对象:** OLD / 2697 / OL-mod(ol-mod-olfinal) / CoD4x / IW4x / 最终 CODOL 客户端。
**关系类型(限定):** `DIRECT_LINEAGE` · `DIRECT_CALL_MAPPING` · `ARCHITECTURAL_ANALOGY` · `STRUCTURAL_SIMILARITY` · `NAME_ONLY` · `CONTRADICTION` · `UNKNOWN` · `BLOCKED`。

**每项必录:** 对象 / 证据来源 / 直接观察 / 对应关系 / 证据等级 / 反证 / 未知项。

---

## 0. 严禁的推导(本任务全程不采用)

- ❌ IW4x 有相似 Pmove ⇒ CODOL 必然使用完全相同的 Pmove。
- ❌ 2697 存在某字段 ⇒ 最终客户端必然以相同布局传输该字段。
- ❌ 项目侧参考代码可运行 ⇒ 官方客户端内部一定具有相同实现。
- ❌ 两个 decoder 字段宽度相同 ⇒ 两者处理同一业务消息。
- ❌ 服务端能构造某种快照 ⇒ 客户端一定按预期消费它。

**源码相似性 / 结构相似性 / 线协议匹配 / 业务语义一致性 —— 四者分别评价,不互相替代。**

---

## 1. 新增/更新维度矩阵(移动物理维度)

| # | 维度 | 对象 | 证据来源 | 直接观察 | 对应关系 | 证据等级 | 反证 | 未知项 |
|---|---|---|---|---|---|---|---|---|
| M1 | usercmd 编码及角度 | 最终 CODOL 客户端 | 本任务:全映像搜索 | **未**在官方映像内定位 usercmd 解码器;`svc_/clc_/netchan` 字符串 = 0 命中 | `UNKNOWN` | UNKNOWN | 无(只是未找到) | 官方 usercmd 解码点 |
| M1b | usercmd 编码及角度 | 项目侧(移动资料) | `CodolClientCommandReader.cs`;`usercmd-native-vectors.json`(20 组) | 混合位/字节游标;Delta(1位 present + 宽度 + key);yaw=`ushort`,`×360/65536` | `DIRECT_ARTIFACT`(仅对该产物) | DIRECT_ARTIFACT | 测试向量是合成数据;真实日志缺原始文件 | 官方是否同构 |
| M1c | usercmd 角度 | OLD / 2697 / OLMod / CoD4x / IW4x | 045 `05_PROTOCOL_EVIDENCE_MATRIX.tsv`;CoD4x `net_chan.h`;IW4x `Structs.hpp` | 各自 usercmd 结构存在(angles 字段) | `ARCHITECTURAL_ANALOGY` | REPORT_ONLY(未重查) | 无字节级对应 | 是否同一编码 |
| M2 | 混合缓冲区读取规则 | 最终 CODOL 客户端 | 本任务:`0x87C110`/`0x87D5A0` 反汇编 | 变长 `sizeinfo` 逐元素解包;net_start/net_end 边界 | 归属 **TDR**(腾讯),`DIRECT_STATIC` | DIRECT_STATIC | 无到游戏快照的边 | 游戏侧是否另有混合读 |
| M2b | 混合缓冲区读取规则 | 项目侧 | `demo_parse.py` `MixedReader`;trace `cursor` | 位游标 + 字节游标双游标 | `DIRECT_ARTIFACT` | DIRECT_ARTIFACT | `demo-player-fields-trace.json` 未完成(`Unclassified call`) | 与官方一致性 |
| M3 | snapshot 字段编码 | 最终 CODOL 客户端 | 本任务:全映像搜索 | `snapshot` 仅 Flash/工具链命中;官方网络 snapshot 解码未定位 | `UNKNOWN` | UNKNOWN | 无 | 官方 snapshot 解码点 |
| M3b | snapshot 字段编码 | 项目侧 | `CodolMotionSnapshot.cs`(写侧);`demo_parse.py`(读侧);`demo-player-fields-trace.json` | 32 字段,部分宽度由 cursor 量出;大量 idx 语义未定 | `DIRECT_ARTIFACT` | DIRECT_ARTIFACT | trace 未完成;`camera-motion.json` 缺失 | 完整字段语义 |
| M3c | snapshot 字段编码 | 2697 / OLD | 045/2697 报告(`svc_snapshot=0xA4FA0`,`EOF`) | 服务端有 snapshot/EOF 概念 | `NAME_ONLY` | REPORT_ONLY | 无客户端字节对应 | 线布局 |
| M4 | PlayerState 与预测态职责边界 | 最终 CODOL 客户端 | 本任务:未在映像内定位 | 未观察到 | `UNKNOWN` | UNKNOWN | 无 | 内存↔网络的桥 |
| M4b | PlayerState 与预测态职责边界 | 项目侧 | `docs` §2/§9;`playerstate-fields.json`;`nt10.py` | 内存偏移(`+0x30 origin`、`+0xa4 gravity`、`+0xb0 speed` 等);预测态/权威态双副本 | `DIRECT_ARTIFACT`(**内存布局**) | DIRECT_ARTIFACT | 判别依赖同源扫描,非独立 | **网络编码**格式 |
| M5 | netfield 机制 | 最终 CODOL 客户端 | 本任务:`0x879AC0`/`0x87A890` 归 TDR | 变长长度前缀 + 元素类型跳表(值与 `>0x14` 拒绝) | 归属 **TDR** | DIRECT_STATIC | 042 的 CoD-netfield 归因被推翻 | 游戏侧 netfield |
| M5b | netfield 机制 | IW4x / CoD4x / OLMod | CoD4x `net_chan.h`;IW4x 源码 | 各自 netfield/delta 机制 | `ARCHITECTURAL_ANALOGY` | REPORT_ONLY | 未复核 | 语义一致性 |
| M6 | gamestate | 最终 CODOL 客户端 | 本任务字符串 xref | `gamestateupdate %d`→RVA`0x54B7B`/`0x73214`;`CA_GAMESTATE`→`0x1C809D`;`EXE_AWAITINGGAMESTATE`→`0x20C14C` | **字符串存在,消费链未闭合** | DIRECT_STATIC(串)/UNKNOWN(链) | 与 045 选定链无交叉 | 客户端 gamestate 读取/转换 |
| M6b | gamestate | OLD / 2697 / OLMod | 045 `P06`;2697 报告 | OLD 写 2,5;2697 `0x03`/`0x02` | `NAME_ONLY` | REPORT_ONLY | 版本代际差异 | 客户端 opcode |
| M7 | configstrings | 最终 CODOL 客户端 | 本任务字符串 xref | `EXE_CONFIGSTRINGMISMATCH`→`0x731E1`/`0xF2833`;`EXE_POSSIBLECONFIGSTRINGMISMATCH`→`0x731CF`;`ExpectedNetConfigStringMismatch`→`0x778D7` | 字符串存在,消费链未闭合 | DIRECT_STATIC(串)/UNKNOWN(链) | 无 | 0x04 读取/存储 |
| M8 | snapshot | 最终 CODOL 客户端 | 045 | `0x87D5A0` 归 TDR(本任务) | `CONTRADICTION`(原归因) | DIRECT_STATIC | 4/4 调用者 TQOS | 官方 snapshot 解码 |
| M9 | reliable commands | 最终 CODOL 客户端 | 本任务字符串 xref | `EXE_LOSTRELIABLECOMMANDS`→`0xF2737`/`0x376B14`;`EXE_SERVERCOMMANDOVERFLOW`→`0xF26C7`;`EXE_ERR_RELIABLE_CYCLED_OUT` 无 xref | 字符串存在,分派未闭合 | DIRECT_STATIC(串)/UNKNOWN(分派) | 无 | 客户端 0x01/0x02 分派 |
| M10 | TQOS 与游戏网络边界 | 最终 CODOL 客户端 | 本任务:`05` P1/P3/P7 | **已证分离**:TQOS 群 `0x85Dxxx/0x87Cxxx/0x87Dxxx`;游戏协议串在 `0x0005x–0x00376x`;两者无交叉引用 | **`CONFIRMED`(边界存在)** | DIRECT_STATIC | 未把游戏侧连到 socket | 游戏侧收包点 |
| M11 | 移动/碰撞/重力/权威更新 | 最终 CODOL 客户端 | 本任务:未定位官方 Pmove/netchan | 未观察到 | `UNKNOWN` | UNKNOWN | 无 | 官方 Pmove 是否在客户端 |
| M11b | 移动/碰撞/重力/权威更新 | 项目侧 | `docs` §5/§9(镜像预测态 4 次对照) | 客户端自行 Pmove 后由服务端回发预测态;重力/落地/爬箱成立 | `DIRECT_ARTIFACT` | DIRECT_ARTIFACT | 橡皮筋时序原始数据缺失 | 与官方权威模型差异 |
| M11c | 移动物理 | IW4x | `iw4x-client/src/Game/PlayerMovement.cpp`;`Components/Modules/PlayerMovement.cpp` | 存在 Pmove 实现 | `ARCHITECTURAL_ANALOGY`(**仅此**) | REPORT_ONLY | 无 CODOL 对应证据 | 常量/函数是否相同 |

---

## 2. 与 045 六方矩阵的关系

- 045 的 `04_SIX_WAY_ARCHITECTURE_MATRIX.tsv`(42 条)与 `05_PROTOCOL_EVIDENCE_MATRIX.tsv`(11 维)
  **继续有效**,本任务**不改写**它们。
- 本任务**更新**其中 3 项,并新增移动维度:

| 045 项 | 045 结论 | 046 更新 |
|---|---|---|
| P02 网络传输与缓冲区 | `select+recv 0x87BE00`(`CONFIRMED`) | **收窄**:该原语由 TQOS 使用;通用原语本身无业务语义 → 归属改判见 `02` |
| P04 消息类型分派 | `TQOS 0x85E6F0`(平台层);业务 opcode `UNKNOWN` | **不变**;本任务确认其词法属 TQOS |
| P08 Snapshot | `0x87D5A0 为通用反序列化原语`(接收链闭合) | **改判**:`0x87D5A0` 为 **TDR** 解包器,非 CoD snapshot 原语;snapshot 语义仍 `UNKNOWN` |
| P09 Netfield/Delta | `解码器 0x87C110/0x87D5A0 类型分支{C,1,21,22}` | **改判**:归 TDR;`0x879AC0` 亦归 TDR;不得称 CoD netfield |
| P10 客户端状态机 | 收包→解码链已闭合 | **改判**:该链为 TQOS 内部;业务状态机仍 `BLOCKED` |

---

## 3. 关系类型统计(本任务新增/更新项)

| 关系类型 | 计数 | 说明 |
|---|---|---|
| `DIRECT_STATIC_EVIDENCE`(客户端) | 3 | TDR 归属、TQOS 归属、游戏串区分离 |
| `DIRECT_ARTIFACT_EVIDENCE`(项目侧) | 5 | usercmd/snapshot/PlayerState/镜像预测/Pmove |
| `CONTRADICTION` | 2 | 042 CoD-netfield 归因、045 业务链归因 |
| `ARCHITECTURAL_ANALOGY` | 4 | CoD4x / IW4x / OLD / OLMod |
| `NAME_ONLY` | 3 | 2697 snapshot/EOF、gamestate/configstring 编号 |
| `UNKNOWN` | 5 | 官方 usercmd/snapshot/gamestate/configstring 消费点、官方 Pmove |
| `BLOCKED` | 2 | 第3节区不可读、未恢复区 |
""")
print("DONE")
