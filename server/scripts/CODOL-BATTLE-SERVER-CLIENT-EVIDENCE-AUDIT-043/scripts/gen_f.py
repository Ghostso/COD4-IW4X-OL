# -*- coding: utf-8 -*-
import os, io, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
ROOT=C.ROOT
def W(n,t): io.open(os.path.join(ROOT,n),"w",encoding="utf-8",newline="").write(t)

# ISSUE LEDGER: risk-weighted, A/B/C
issues = [
 # ID, class, weight, issue, status, close_condition, evidence
 ("A-01","A",10,"客户端 socket/recv 接收点未确认(读 API 槽值在镜像外)","BLOCKED","命中覆盖 0x0E5C9000+ 的镜像并解析 0xCA84E8/0xCA84E4/0xCA853C 槽;或证明接收走另一可静态定位路径","04_IMAGE_COVERAGE_AND_BLOCKERS.md BE-01"),
 ("A-02","A",10,"业务层调用 net-buffer 解码器的边未闭合(唯一可复核调用者为 TQOS)","UNKNOWN","在完整镜像或只读运行期追踪中定位非 TQOS 调用者","03_CALLER_AND_DATAFLOW_AUDIT.md §2.1"),
 ("A-03","A",9,"客户端消息类型分派/opcode 表未定位(in-match)","UNKNOWN","给出读 opcode → 分派表 → handler 的可复核指令链","03 §5 / 06 matrix"),
 ("A-04","A",9,"Gamestate 客户端消费语义不明(0x03/0x02)","BLOCKED","客户端 0x03 网络读取与状态转换的指令级证据","05 matrix / 2697 E5"),
 ("A-05","A",9,"Configstrings 客户端消费语义不明(0x04/0x03)","BLOCKED","客户端 0x04 网络读取/存储的指令级证据","05 matrix / 2697 E5"),
 ("A-06","A",9,"Snapshot/Delta/EOF 客户端解码未闭合","BLOCKED","客户端 snapshot 分帧 + netfield 解码 + EOF 分支证据","05 matrix / 2697 E5"),
 ("A-07","A",8,"样本身份矛盾:记录客户端 E3823FD6 本机不存在;实际 3699b537 不匹配","UNKNOWN","取得匹配 E3823FD6 的构建,或工程方确认改用 3699b537 并更新基线","01 §7"),
 ("A-08","A",8,"可靠命令 0x01/0x02 客户端分派未独立证实","UNKNOWN","客户端读 0x01/0x02 并进入处理器的指令链","05 matrix"),
 ("A-09","A",7,"平台层(TQOS/QoS)与业务层边界未证分离","UNKNOWN","证明 0x87C110/0x87D5A0 是否服务业务,或界定复用范围","03 §2.1"),
 ("B-01","B",5,"旧/2697 wire 常量(PROTOCOL=187/FRAG=1162)未与客户端字节绑定","CANDIDATE","客户端出现等值常量或分片字段","05 / 2697 04"),
 ("B-02","B",4,"OLMod 含 2 处默认开启的非 CODOL 资产替代","CONFIRMED(风险)","以 CODOL 原生资产替换,或明确隔离与回滚","OLMOD MANIFEST"),
 ("B-03","B",4,"客户端 netfield 元素类型域未穷举([ebx+8] 仅 2 处引用)","UNKNOWN","穷举类型取值与对应解码分支","02 §2.2"),
 ("B-04","B",3,"客户端 0x744B20/0x7CD790 等辅助函数语义已定位但未与业务绑定","CROSS_VALIDATED","业务路径调用链","02 §4"),
 ("C-01","C",2,"恢复镜像多副本(4 构建)命名混淆","CROSS_VALIDATED","统一以完整 SHA-256 绑定引用","01 §5"),
 ("C-02","C",2,"042 report 措辞(dispatching/sizeinfo helper)需修订","CONFIRMED","以 043 勘误为准(不改历史交付物)","10_CORRECTION_LOG.md"),
 ("C-03","C",2,"六方仅达原语级可比","CROSS_VALIDATED","获得业务级证据后扩展矩阵","05/06"),
]
W("07_SERVER_READINESS_ISSUE_LEDGER.tsv",
 "ISSUE_ID\tCLASS\tRISK_WEIGHT\tISSUE\tSTATUS\tCLOSE_CONDITION\tEVIDENCE_LOCATION\n"+
 "\n".join("\t".join((a,b,str(w),c,d,e,f)) for a,b,w,c,d,e,f in issues)+"\n")

# 90% computation with fixed weights
A=[i for i in issues if i[1]=="A"]; B=[i for i in issues if i[1]=="B"]; Cc=[i for i in issues if i[1]=="C"]
def solved(st): return st in ("CONFIRMED","CROSS_VALIDATED")
tot=sum(i[2] for i in issues); sol=sum(i[2] for i in issues if solved(i[4]))
allA=sum(i[2] for i in A); solA=sum(i[2] for i in A if solved(i[4]))
allB=sum(i[2] for i in B); solB=sum(i[2] for i in B if solved(i[4]))
allC=sum(i[2] for i in Cc); solC=sum(i[2] for i in Cc if solved(i[4]))
lines=["# 09_NEXT_ACTION_DECISION — 下一步决策与 90% 计算","",
 "## 1. 风险加权解决率(固定总集与权重,先定后算)",
 "",
 "| 类别 | 权重合计 | 已解决权重 | 解决率 |",
 "|---|---|---|---|",
 "| A(开工前阻断) | %d | %d | %.1f%% |"%(allA,solA,100.0*solA/allA),
 "| B(可带风险) | %d | %d | %.1f%% |"%(allB,solB,100.0*solB/allB),
 "| C(后续完善) | %d | %d | %.1f%% |"%(allC,solC,100.0*solC/allC),
 "| **合计** | **%d** | **%d** | **%.1f%%** |"%(tot,sol,100.0*sol/tot),
 "",
 "> `UNKNOWN`/`BLOCKED` **不计**已解决;哈希通过/脚本通过/函数定位成功**不自动**等于协议问题解决。",
 "> A 类解决率 %.1f%% —— **关键 A 类问题未解决,不满足开工准入**。"%(100.0*solA/allA),
 "",
 "## 2. 结论:是否确需额外取证",
 "",
 "**是,但仅限一条边**:`BE-01`(socket/recv → 读包原语)是**现有静态材料无法解决**且**实质影响协议判断**的边。",
 "其根因是恢复镜像未覆盖 `.tp3 #3/#5`(读 API IAT 槽与运行期全局在此)。",
 "",
 "- **不默认为全部问题请求运行期取证。** A-02/A-03/A-09 等边在补足该节区镜像后**可能静态闭合**。",
 "- 因此建议的**最小**补充证据 = 覆盖 `VA 0x0E5C9000+` 与 `0x76xxxxxx` 的运行期镜像(只读),",
 "  **不**要求动态调试/hook;这属于'后续独立取证建议',本任务不执行也不授权。",
 "",
 "## 3. 唯一推荐下一步(择一,按优先级)",
 "",
 "1. **(首选)** 取得覆盖 `.tp3 #3/#4/#5` 的只读运行期镜像,以闭合 BE-01/BE-03 并解析读 API 槽;",
 "   若成功,再一次性闭合 A-01/A-02/A-03/A-09。",
 "2. **(并行、无需新样本)** 在同一 `17cef045` 镜像内继续:**穷举 `0x87C110`/`0x87D5A0` 的类型域**与",
 "   **间接调用/跳转表**(`FF /2`、`FF /4`、`jmp [reg*4+disp]`)以确认是否存在**业务**调用路径;预期收益有限但零成本。",
 "3. **(流程)** 由工程方裁决样本身份矛盾(A-07):取得 `E3823FD6` 或正式认可 `3699b537` 并更新基线。",
 "",
 "## 4. 明确不启动的事项",
 "",
 "- 不在本任务开始正式服务器实现(未授权)。",
 "- 不据服务端(OLD/2697/OLMod)实现反推客户端协议。",
 "- 不据 CoD4x/IW4X 架构等同认定协议一致。",
]
W("09_NEXT_ACTION_DECISION.md","\n".join(lines)+"\n")
print("wrote 07/09")
print("weighted: A %.1f%%  B %.1f%%  C %.1f%%  total %.1f%%"%(100.0*solA/allA,100.0*solB/allB,100.0*solC/allC,100.0*sol/tot))
