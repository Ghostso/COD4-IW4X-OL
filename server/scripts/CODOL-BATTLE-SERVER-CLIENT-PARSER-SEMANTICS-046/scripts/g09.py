# -*- coding: utf-8 -*-
import sys,os
sys.stdout.reconfigure(encoding="utf-8")
os.chdir(os.path.dirname(os.path.abspath(__file__)))
def W(n,s): open(n,"w",encoding="utf-8",newline="\n").write(s); print("wrote",n,len(s))

W("05_CLIENT_PATH_MAPPING.md", r"""# 05_CLIENT_PATH_MAPPING

**核心工作包 C4:** 官方客户端候选路径 ↔ 项目侧移动实现的映射结果。
**允许取值:** `DIRECT_MAPPING` / `PARTIAL_MAPPING` / `STRUCTURAL_SIMILARITY_ONLY` / `CONTRADICTED` / `UNKNOWN` / `BLOCKED`。

---

## 1. 官方客户端候选路径(本任务重新定性)

| 路径 ID | 位置 | 性质 | 等级 |
|---|---|---|---|
| P1 | `0x85D2E0 / 0x85D3A0 / 0x85D5A0 / 0x85D870 / 0x85E6F0 / 0x85EB50` | **TQOS / QoS 平台层**(QOSCSPkg/QOSSSPkg,TDR 解包,`udp://`) | DIRECT_STATIC |
| P2 | `0x87BE00`(+`0x87BA50`) | 通用 `select+recv` 原语(P1 使用,亦可能被其他簇使用) | DIRECT_STATIC |
| P3 | `0x87C110 / 0x87D5A0 / 0x87ED70 / 0x87EDB0 / 0x879AC0` | 腾讯 **TDR** 通用序列化框架(net-buffer 解包、scratch、wcslen、长度前缀写入) | DIRECT_STATIC |
| P4 | `0x8653xx–0x866xxx` | 独立 socket 簇:`socket+bind+listen+accept+select+recv+sendto+recvfrom`;**无邻近字符串** | 观察到(`DIRECT_STATIC` 存在性) / `UNKNOWN` 语义 |
| P5 | `0x8768xx–0x877xxx` | 独立 socket 簇:`socket+connect+select+recv+send`;**无邻近字符串** | 观察到 / `UNKNOWN` 语义 |
| P6 | `0x6CBxxx–0x6D8xxx` | 多个网络包装(`Recv failure: %s`、`Send failure: %s`、`Immediate connect fail`、`Local Interface %s`) | 观察到 / `INFERRED`=通用 HTTP/libcurl 风格 |
| P7 | 低地址区 `0x00054xxx`–`0x00376xxx` | **游戏协议串所在区**:`gamestateupdate %d`、`CA_GAMESTATE`、`EXE_CONFIGSTRINGMISMATCH`、`connectResponse`、`EXE_LOSTRELIABLECOMMANDS` | DIRECT_STATIC(存在) / 与 P2/P3 **无交叉引用** |

> **P7 是本任务最重要的"反向证据":** 真正的游戏协议诊断串全部位于**远离 TQOS 的低地址区**,
> 说明 045 选定的链**不是**游戏协议所在区域。

---

## 2. 映射矩阵:官方候选 ↔ 项目侧移动实现

项目侧实现清单(来自移动物理资料):

| 代号 | 项目侧制品 | 性质 |
|---|---|---|
| R1 | `CodolClientCommandReader.cs` | usercmd 混合编码读/写参考实现 |
| R2 | `CodolMotionSnapshot.cs` | snapshot/PlayerState **写侧**构造器 |
| R3 | `usercmd-native-vectors.json` | usercmd 编解码测试向量 |
| R4 | `playerstate-motion-trace.json` / `demo-player-fields-trace.json` | 离线字段/cursor 追踪 |
| R5 | `demo_parse.py` | demo 解包器(读侧) |
| R6 | `battle_server.py` / `CodolLocalBattleServer.cs` | 本地战斗服(UDP:28960) |
| R7 | `nt10.py` | 进程内存 playerstate 探针 |

| 官方候选 | 项目侧制品 | 裁定 | 依据 |
|---|---|---|---|
| P1 (TQOS) | R1–R7 | **UNKNOWN** | 无任何共享字节/调用/字段值;项目侧战斗服是**独立 UDP 实现** |
| P2 (`select+recv`) | R6(UDP 收包) | **STRUCTURAL_SIMILARITY_ONLY** | 都是"收 UDP",但 P2 归 TQOS;R6 是 Python `UdpClient`,无共享代码 |
| P3 (TDR 解包) | R5(demo 解包) | **STRUCTURAL_SIMILARITY_ONLY** | 都是"变长/位域解包",但**无共享缓冲、无交叉引用、无字段值对应** |
| P3 (TDR) | R1/R3(usercmd) | **CONTRADICTED** | `0x87C110/0x87D5A0` 归 TQOS/TDR(§02);usercmd 编码与 TDR net-buffer 元数据模型不一致 |
| P3 (TDR) | R2/R4(snapshot) | **CONTRADICTED** | 同上;snapshot 字段表来自项目侧构造,trace 为未完成离线跟踪 |
| P4/P5(无串 socket 簇) | R6(UDP:28960) | **UNKNOWN** | 未定位 P4/P5 的上层语义;不能排除其中一个即游戏 netchan |
| P7(游戏协议串) | R1/R2/R6 | **PARTIAL_MAPPING**(仅字符串名) | `gamestateupdate/CA_GAMESTATE/configstrings/reliable/snapshot` 等名与 CoD 术语一致;**但**无字节级/调用级对应 |
| — | R7(内存偏移) | **UNKNOWN**(对官方) | 偏移由探针在**运行中的客户端**读出,但**不与**任何官方反汇编符号绑定 |

---

## 3. 关键否证

| 否证 | 内容 |
|---|---|
| N-1 | `0x87C110/0x87D5A0` 不构成"官方 usercmd/snapshot 解码器":其调用者/字符串全属 TQOS/TDR |
| N-2 | 045 的"接收链"不构成"游戏业务解析入口":上层是 `tqos_create_protohandle` |
| N-3 | 移动资料的字段宽度表**不能**反推官方线格式:它由**项目侧写侧代码**定义(见 `04` C2 表末列全"否") |
| N-4 | 项目侧实跑成功(能走/能开枪)**不等于**官方协议已复原:它只证明"客户端接受了这些构造字节" |

---

## 4. 下一步定位方向(不越界)

1. 对 P4(`0x865xxx`)、P5(`0x876xxx`)做上游调用者分析与结构识别 → 判定哪一个是 in-match netchan。
2. 在 P7 区域(`0x00054xxx` / `0x000732xx` / `0x001C17B5` 等)定位 `gamestateupdate`/`configstring`/
   `reliable` 的**读写点**,反向找其输入缓冲来源。
3. 检查 P7 输入缓冲是否来自 P4/P5 的收包函数(共享缓冲/调用链证据)。
""")
print("DONE")
