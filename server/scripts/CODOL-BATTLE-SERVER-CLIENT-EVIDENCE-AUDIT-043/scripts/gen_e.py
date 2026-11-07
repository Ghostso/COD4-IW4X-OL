# -*- coding: utf-8 -*-
import os, io, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
ROOT=C.ROOT
def W(n,t): io.open(os.path.join(ROOT,n),"w",encoding="utf-8",newline="").write(t)

# ---------- 05 SIX-WAY CROSS VALIDATION MATRIX ----------
rows = [
 # proj, target, symbol/rva, evidence_loc, rel_type, support, contra, missing, impact
 ("CODOL-client(042)","-","net-buffer decoders 0x87A890/0x87C110/0x87D5A0","image_best.bin 17cef045; 043 evidence/dis_87A890_full.txt; dis_deser_boundaries.txt","DIRECT_LINEAGE","043 独立反汇编确认 netfield 长度编解码原语 + 6 条 net-buffer 串绑定","唯一可复核调用者为 TQOS 族;业务调用者不可见","业务调用者/接收点","需闭合业务调用者才能进协议矩阵"),
 ("OLD(server)","CODOL-client","wire constants PROTOCOL=187/FRAGMENT_SIZE=1162/SEQ_MASK=0x1fffffff","2697 dir 04_PROTOCOL_PATHS.md §0 (codol_wire.h)","WIRE_FORMAT_MATCH(CANDIDATE)","服务端 wire 常量为源码级 VERIFIED","客户端无任何 1162/0x1fffffff 常量或分派的可复核绑定","客户端读取/比较/分片指令","不得据服务端常量认定客户端一致"),
 ("OLD(server)","CODOL-client","SV_WIRE_SERVERCOMMAND=0x01 / EOF=0x05","2697 dir 04_PROTOCOL_PATHS.md §0 (sv_snapshot.c)","WIRE_FORMAT_MATCH(CANDIDATE)","旧封装三样本均写 0x01/0x05","客户端 0x01/0x05 消费未定位","客户端消息类型表","BLOCKED"),
 ("2697(server)","CODOL-client","_CODOL2697_WriteGamestate 0xA21B8 / WriteConfigstrings 0xA0468","2697 dir 07/E5_COMPATIBILITY_MATRIX.md","ARCHITECTURAL_ANALOGY","服务端门控与调用链 VERIFIED","客户端 gamestate/configstring 网络读取 BLOCKED","客户端 0x03/0x04 reader","仅有服务端一侧"),
 ("2697(server)","CODOL-client","reliable 0x02 writer 0x8612E","2697 dir 07/E5","ARCHITECTURAL_ANALOGY","服务端 0x02 编码 VERIFIED","客户端候选 0xA2E50 未绑定 opcode","客户端分派","STATIC-INFERENCE only"),
 ("2697(server)","CODOL-client","Snapshot writer 0xA4FA0 / internal EOF 0x06","2697 dir 07/E5","ARCHITECTURAL_ANALOGY","服务端序列 VERIFIED","客户端 delta/EOF 未闭合","客户端 snapshot parser","BLOCKED"),
 ("OLMod","CODOL-client","repo claims 6-stage chain closed (mmstart..snapshots)","CODOL_OLMOD_AUDIT_20261009_094312/AUDIT.md","NAME_ONLY / CONTRADICTION","OLMod 自述双客户端进局","记录的 E3823FD6 客户端本机不存在;mismatch 3699..b537","可复现证据(仓库外)","开工对象未定"),
 ("OLMod","CODOL-client","non-CODOL asset substitutions x3","CODOL_OLMOD_AUDIT_20261009_094312/MANIFEST.json","CONTRADICTION","2 处默认开启(BO1 navgraph/Ghosts glass/IW4 destructible)","与'禁用非CODOL资产'冲突","-","实现风险"),
 ("CoD4x","CODOL-client","netfield/delta architecture","IW4X/.../src (reference)","ARCHITECTURAL_ANALOGY","netfield 编码概念可比 0x87A890 阈值","无 CODOL 字节级映射","客户端类型表","仅作参照"),
 ("IW4X","CODOL-client","net_chan/msg architecture","IW4X/ComCalliope.../src","ARCHITECTURAL_ANALOGY","同类 net 序列化概念","未提供 CODOL 原始字节证据","-","仅作参照"),
 ("CODOL-client(042)","CoD4x/IW4X","sizeinfo width thresholds 128/256/65536","043 evidence/dis_87A890_full.txt","ARCHITECTURAL_ANALOGY","043 独立确认阈值与 varint","未比对具体实现","源码级对照","CANDIDATE only"),
]
W("05_SIX_WAY_CROSS_VALIDATION_MATRIX.tsv",
 "SRC_PROJECT\tTARGET_PROJECT\tSYMBOL_OR_RVA\tEVIDENCE_LOCATION\tRELATION_TYPE\tSUPPORT\tCONTRA\tMISSING\tIMPACT\n"+
 "\n".join("\t".join(r) for r in rows)+"\n")

# ---------- 06 PROTOCOL EVIDENCE MATRIX ----------
dims = [
 ("样本身份/版本","S-IMG 17cef045 = EXE 3699b537 同源(同IB/EP/时间戳);E3823FD6 out.exe 不存在","CONFIRMED/UNKNOWN","01_SAMPLE_IDENTITY_AUDIT.md"),
 ("网络 API 与传输模块","EXE 映像 .tp3#1 内含 net-buffer 编解码族;读 API IAT 槽在镜像外","CONFIRMED/BLOCKED","03/04"),
 ("消息缓冲区与长度编码","sizeinfo 写入器 0x87A890: tag 0xC + 1/2/3 字节大端;varint 0x7CD790(<=0x7F/0x7FF)","CONFIRMED","02/04 evidence/dis_87A890_full.txt"),
 ("消息边界与分片处理","未定位客户端分片/重组;服务端 OLD 有 FRAGMENT_SIZE=1162","UNKNOWN(客户端)/VERIFIED(服务端)","05"),
 ("消息类型分派","仅 TQOS 0x85E6F0 类型字分派(4/6);in-match 业务分派未定位","UNKNOWN","03"),
 ("可靠命令","服务端 0x02 writer VERIFIED;客户端候选未绑定","STATIC-INFERENCE","05"),
 ("Gamestate","服务端写 0x03/0x02;客户端读取 BLOCKED","BLOCKED","05"),
 ("Configstrings","服务端写 0x04/0x03;客户端读取 BLOCKED","BLOCKED","05"),
 ("Snapshot","服务端序列 VERIFIED;客户端 delta/EOF BLOCKED","BLOCKED","05"),
 ("Netfield / Delta 编码","客户端 0x87A890 长度编码 + 0x87C110 解码(独立确认)","CONFIRMED","02"),
 ("客户端状态机","gamestateupdate/EXE_*MISMATCH 调用点存在;语义未闭合","CROSS_VALIDATED/UNKNOWN","02(042)"),
 ("错误处理与版本适配","net-buffer 错误串 6 条与代码绑定;版本适配未知","CONFIRMED/UNKNOWN","02"),
 ("平台层 vs 业务层边界","TQOS(QoS)与业务未证分离;042 排除被收紧","UNKNOWN","03"),
]
W("06_PROTOCOL_EVIDENCE_MATRIX.tsv",
 "DIMENSION\tCLIENT_EVIDENCE\tSTATUS\tEVIDENCE_LOCATION\n"+
 "\n".join("\t".join((a,b,c,d)) for a,b,c,d in dims)+"\n")
print("wrote 05/06")
