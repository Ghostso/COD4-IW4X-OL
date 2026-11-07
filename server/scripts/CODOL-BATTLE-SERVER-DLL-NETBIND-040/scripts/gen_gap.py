# -*- coding: utf-8 -*-
import io, os
ROOT=r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-DLL-NETBIND-040"
def W(n,t): io.open(os.path.join(ROOT,n),"w",encoding="utf-8",newline="").write(t)

hdr=["GAP_ID","LAYER","CLIENT_EVIDENCE","CLIENT_STATUS","SERVER_MODULE","SERVER_IMPLEMENTATION","SERVER_STATUS","NOTE"]
rows=[
 ("GAP-040-001","UDP 收发","隐藏 IAT: recvfrom/recv/sendto 槽 + 真实 FF15 调用点","CLIENT_CONFIRMED","Net/UdpTransport.cs","Socket(Dgram/Udp) + ReceiveFrom/SendTo","SERVER_ONLY","客户端网络栈形态未知; 不得据服务器 .NET Socket 反推客户端"),
 ("GAP-040-002","传输封装","客户端接收为 SOCK_RAW/ICMP 候选对象 (WSASocketW af=2,type=3,proto=1)","UNKNOWN","Engine/ClientLogic.cs + Codol/CodolProtocol.cs","DTLS-init/cookie + AES/HMAC 数据帧","SERVER_ONLY","客户端 raw/内核通道 vs 服务器 UDP 封装, 无对应证据"),
 ("GAP-040-003","OOB 处理","未见客户端 OOB 解析 (getchallenge/connect/challengeResponse 串仅在 EXE/服务器)","UNKNOWN","Codol/CodolProtocol.cs (IsOob/OobCommand/BuildOob)","OOB 文本命令 + NAT/DTLS 阶段","SERVER_ONLY","服务器 OOB 语义来自实机抓包, 非来自本 DLL 证据"),
 ("GAP-040-004","netchan","客户端 netchan 状态未定位 (接收后无序列/分片表证据)","UNKNOWN","Codol/Codol2697Protocol.cs + Engine/ClientSession.cs","2697 netchan (4B/6B 头, 0x1FFFFFFF mask) 与 legacy 13B","SERVER_ONLY","不得将 2697/13B 结构映射到客户端"),
 ("GAP-040-005","消息缓冲","客户端接收缓冲 = 栈 [ebp-0x10C], 0x100B; 未拷贝到持久缓冲","PARTIAL","Engine/ClientLogic.cs","服务器自建 byte[] 缓冲 + TryReadData","SERVER_ONLY","客户端缓冲生命周期为函数栈局部; 服务器为托管数组"),
 ("GAP-040-006","应用层解析","客户端应用层 opcode 分派未定位","UNKNOWN","Engine/ClientLogic.cs HandlePlain() + Codol/ClientCommandReader.cs","按类型/命令解析 (HandlePlain/ClientCommandReader)","SERVER_ONLY","不得主张服务器解析器与客户端一致"),
 ("GAP-040-007","socket/event 模型","客户端用 WSAEventSelect+WSAEnumNetworkEvents+WSAWaitForMultipleEvents (事件驱动)","CLIENT_CONFIRMED","Net/UdpTransport.cs","阻塞式 ReceiveFrom + ReceiveTimeout=1ms 轮询","SERVER_ONLY","模型差异明确: 客户端事件驱动 vs 服务器轮询"),
 ("GAP-040-008","保护区","3 导出与入口点均在 .tvm0; VM 未解码","CLIENT_CONFIRMED","(无)","(无)","SERVER_ONLY","静态不可达; 与服务器无关"),
 ("GAP-040-009","地址/ABI","客户端 ImageBase 0x10000000, i386, ASLR","CLIENT_CONFIRMED","(无)","服务器 .NET AnyCPU/x86 独立进程","SERVER_ONLY","两者 ABI 无关; 不得共享地址假设"),
]
lines=["\t".join(hdr)+"\n"]
for r in rows: lines.append("\t".join(r)+"\n")
W("SERVER_IMPLEMENTATION_GAP.tsv","".join(lines))
print("SERVER_IMPLEMENTATION_GAP.tsv rows:",len(rows))
