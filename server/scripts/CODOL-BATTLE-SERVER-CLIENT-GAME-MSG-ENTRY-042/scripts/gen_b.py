# -*- coding: utf-8 -*-
import os, io, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C
ROOT=C.ROOT
def W(name,text): io.open(os.path.join(ROOT,name),"w",encoding="utf-8",newline="").write(text)

W("02_CLIENT_NET_TRANSPORT_MAP.md", """# 02_CLIENT_NET_TRANSPORT_MAP — 客户端网络传输层次图

**证据等级:** `[D]`=CONFIRMED_DIRECT `[F]`=CONFIRMED_DATAFLOW `[X]`=CONFIRMED_CROSSREF `[?]`=UNKNOWN `[B]`=BLOCKED

---

## 1. 层次与模块归属

```
  层                 归属模块                       证据/入口                     本任务状态
 -------------------------------------------------------------------------------------------------
 L0 socket/recv     引擎 EXE(镜像未覆盖节区)       0x76xxxxxx / 0x84xxxxxx        [B] BLOCKED
 L1 netchan/编解码  引擎 EXE .text(镜像已覆盖)      0x87C110 / 0x87D5A0            [D] 已定位
     消息缓冲读取   net-buffer 诊断串              0x99EE98..0x99F428             [D] 已定位
 L2 平台 QoS 分派   引擎 EXE .text(镜像已覆盖)      0x85E6F0(TQOS)                 [D] 平台层
 L3 连接期 OOB      引擎 EXE .text                  0x1C05F0 命令族                 [D] 连接期
 L4 HTTP/代理       libcurl(同镜像内, 单独族)      "Could not resolve"/"proxy"     [D] 独立
 L5 ICMP ping       codoMP_...Base.dll 0x235F7E     041 已判                       [D] 独立
 L6 反作弊/平台通道  .rdata "SendPacket/Kernel*"     ACE/TenGuard 驱动通信           [X] 非游戏netchan
```

---

## 2. 与 040/041 的边界

- 040/041 分析的是 **DLL `codoMP_client_shipRetailBase.dll`**;其唯一独立 socket 簇 = ICMP ping。
- 本轮分析的是 **客户端引擎 EXE 的恢复镜像 `image_best.bin`**;`.text` 内存在 CoD 风格 **netchan/netbuffer 解码器**。
- 两者是**不同模块**,不得互相替代:041 的"无 netchan"结论只适用于该 DLL 的 `.text` 可达范围。

---

## 3. ICMP / libcurl / 平台代理 / 游戏业务 分离(摘要)

| 类别 | 识别证据 | 结论 |
|---|---|---|
| ICMP ping | `WSASocketW(AF_INET,SOCK_RAW,1)` + ICMP type/seq/checksum(DLL `0x235F7E`) | 诊断,与业务无关(041) |
| libcurl / HTTP 代理 | `Could not resolve %s:%s` / `proxy` / `SOCKS5` / `CONNECT %s HTTP` | 平台下载/HTTP,独立簇 |
| 平台 QoS(TQOS) 代理 | 对象字段 `QOSCSPkg*`/`QOSSSPkg*`,`udp://%s:%d`,`tqos_*`,分派器 `0x85E6F0` | 平台 QoS,非业务 netchan |
| 游戏业务 netchan | net-buffer 读取器 `0x87C110/0x87D5A0` + `net_start/net_end/sizeinfo` | **业务消息解析,已定位** |
| 反作弊/内核通道 | `[KernelBind]`/`SendPacket Failed`/ACE-DRV32.dll | 平台/反作弊,非业务 |
""")

W("03_MESSAGE_ENTRY_CANDIDATES.tsv",
"""CAND_ID\tROLE\tMODULE_OR_IMAGE\tRVA\tVA\tINSTRUCTION_EVIDENCE\tDATAFLOW_EVIDENCE\tCALLER_CALLEE\tSTATUS\tNOTE
ME-001\tnet-buffer sizeinfo helper\timage_best.bin\t0x87A890\t0xC7A890\tpush ebp;mov ebp,esp;push ecx;mov ebx,[ebp+0xC];...;movzx eax,word[edx+esi*2];call 0xB44B20;call 0xBCD790;cmp edi,0x80/0x100/0x10000;mov ecx,[ebp+0x14];cmp eax,[ecx]\tunit_size from [ebp+8] table; running total edi; residual = [ebp+0x14] pointer\tcaller 0x879CE3\tCONFIRMED_DIRECT\tnet-buffer sizeinfo width (2/3/4/5) = CoD netfield sizeinfo
ME-002\tnet-buffer deserializer #1\timage_best.bin\t0x87C110\t0xC7C110\tmov eax,0x17F4;call 0xC43280;...;loads 5 args from stack;refs net-buffer error strings\treads [esi+0x28]/[esi+0x2C];uses 0x87A890;compares counts [esp+0x20];loops elements\tcaller 0x85D49D (TQOS)\tCONFIRMED_DIRECT\tentry into netfield/element decode; string anchor 0x99EE98
ME-003\tnet-buffer deserializer #2\timage_best.bin\t0x87D5A0\t0xC7D5A0\tmov eax,0x180C;call 0xC43280;validates [ebp+0x10]/[ebx]/[ebx+4]/[edi]/[edi+4] non-null\tdual buffer args;calls 0x87ED70\tcallers 0x85D3DB/0x85D418/0x85D9B5/0x85D9F7 (TQOS)\tCONFIRMED_DIRECT\tpaired with ME-002; string anchor 0x99EFB8
ME-004\tmessage-type dispatcher\timage_best.bin\t0x85E6F0\t0xC5E6F0\tcall 0x87BA50 (read);test eax;then movzx eax,word[esp+6];sub eax,2;je 0x85E7B0;sub eax,2;jne 0x85E7DE\tmessage type word read at [esp+6] after read;branches type 4 and 6\tcaller 0x85EB16;handlers 0x85E4F0/0x85E5C0\tCONFIRMED_DIRECT\tTQOS platform QoS dispatcher (NOT game netchan)
ME-005\tpacket read primitive\timage_best.bin\t0x87BE00\t0xC7BE00\tsub esp,0x110;...;call [0xca84E8];test eax;jns;call [0xca853C];sub eax,0x2714\treturn value used as byte length;calls slot 0xca84E8\tcallers 0x85D96E,0x85E71A\tCONFIRMED_DIRECT\tpacket receive into stack buffer (slot target not present -> BLOCKED)
ME-006\tOOB connect command family\timage_best.bin\t0x1C05F0..0x1C2700\t0x5C05F0\tstate gate cmp eax,3/4/5/6;jmp [eax*4+table];pushes "getchallenge 0 \\"%s\\""(0x1C071F)/"connect"(0x1C0D6F)/"connectResponse"(0x1C17B5)\tcommand literals referenced by imm32\t\u2014\tCONFIRMED_DIRECT\tconnection-phase OOB, not in-match netchan
ME-007\tgamestateupdate apply\timage_best.bin\t0x73180\t0x473180\tcmp [0x331c0C8];xor 0xD362501F;call 0x4730A0;push 0xDB46C0/0xDB46E4 ("EXE_*CONFIGSTRINGMISMATCH");call 0x4F82E0\treads global state;\u2014\t\u2014\tCONFIRMED_CROSSREF\tapplies game state update + reports mismatch (game-side)
ME-008\tapplication opcode dispatch (in-match)\t\u2014\tUNKNOWN\t\u2014\tnot located in covered image\t\u2014\t\u2014\tUNKNOWN\trequires .tp3 #3/#4/#5 coverage (BLOCKED)
ME-009\trecv/socket receive point\t\u2014\tUNKNOWN\t\u2014\taddresses 0x76xxxxxx/0x84xxxxxx not present in image\t\u2014\t\u2014\tBLOCKED\tbeyond image coverage
ME-010\tlibcurl/HTTP transport\timage_best.bin\t~0x620000..0x744000\t\u2014\t"Could not resolve"/"proxy"/"CONNECT %s HTTP"/"SOCKS5" strings\t\u2014\t\u2014\tCONFIRMED_DIRECT\tplatform HTTP, separate from game netchan
""")

print("wrote 02/03")
