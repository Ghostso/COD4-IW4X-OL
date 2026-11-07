# PVE-BATTLE-CONTRACT-LINEAGE-021
# CODOL Battle Server 契约恢复 + IW4X / CoD4X 血缘交叉验证

```
BATTLE_SERVER_REQUIRED            = **REFUTED**（作为"客户端不进入 Battle"的解释）
                                    理由见 §7：我们**已经开着监听 28960** 跑过 017/019，
                                    客户端**一个包都没发**（BATTLE_RX=0）——不是缺少服务器，
                                    而是根本没走到会去拨号的阶段。
BATTLE_SERVER_REQUIRED_FOR_FINAL  = STRONG CANDIDATE（要真正进对局，终究必须有人在 28960 应答；
                                    但这与"当前不进入"的因果无关）

CODOL_BATTLE_ENDPOINT             = 由 **21/5 findSessions 会话记录 ① Hostaddress** 下发
                                    （服务端由 build_session_record(host_ipv4, host_port) 构造）
                                    本工作区实测值 127.0.0.1 ; 客户端不硬编码
CODOL_BATTLE_PORT                 = 28960（由上述记录下发；**不是客户端常量**——全镜像 0x7120 只出现在 OpenSSL 数据）
CODOL_BATTLE_TRANSPORT            = UDP（SOCK_DGRAM/IPPROTO_UDP）；但**没有证据**它是标准 DTLS
CODOL_BATTLE_HANDSHAKE            = 4 步自定义：NAT(29B) → init(16B)/cookie(38B) → cookie+pubkey(219B)/ack(114B) → data(06 02 …)
CODOL_BATTLE_SESSION_CONTRACT     = 见 §8（15 项，已填 9 项，其余 UNKNOWN）

IW4X_SIMILARITY                   = LOW–MEDIUM（仅 OOB 前门/发现/心跳层面可比；IW4X **无** DTLS/ECDH；
                                    且 IW4X **没有**专用服务器源码 —— IW4X_SERVER_SOURCE_NOT_FOUND）
COD4X_SIMILARITY                  = MEDIUM（服务器骨架/状态机/快照复制可直接照结构学；
                                    但**游戏通道无任何加密**，与 CODOL 的 cookie+ECDH 握手决定性不同）

BEST_REFERENCE                    = **HYBRID**：控制面/结构学 CoD4X，OOB/发现/auth 信封学 IW4X；
                                    握手与密钥交换只能从 CODOL 自身证据来

NEXT_STEP                         = 不算血缘，先关 020 的 accepted 门（additional accepted guard）；
                                    只有在 accepted 真正执行、且客户端真的向 28960 发包之后，
                                    "是否需要自建 Battle Server"才成为可判定问题
```

纪律核对：未改 client / Lobby / Publisher / Protocol / accepted response / SessionId / A/B / marker /
未 patch / 未 hook / 未 NOP / 未内存写入 / 未把 IW4X 或 CoD4X 当成 CODOL Server。
本轮仅新增：只读静态分析 + 三个外部仓库的浅克隆（DEV-BOOKING\_lineage021\）。

---

## §0 本轮新增证据一览

```
CODOL 侧（全新，本轮）：
  1. **socket() 全枚举**：9 处创建点，逐个给出 (af, type, proto)（§1）
  2. **套接字抽象类**：vtable 0xD8E3A8，ctor 0xC65D30，工厂 0xC65D70（分配 0x24 字节）
  3. **地址对象类**：端口在 +0x84（getter 0xB75440 / setter 0xB75420）；sockaddr 构造 0xB75340
  4. **★ 端点解析器 0x621E50**：把服务器端点写成 {+0x00=4, +0x04=ip(u32), +0x08=port(u16), +0x14=值}
     —— 且**要求传输对象（[obj+0x1F0]）处于 state 1**（[vtable+0x20]()==1）
     —— 调用者是**游戏层**（0x4F8F25 / 0x4F9075），不是匹配模块
  5. **★ 纠正一个长期错误**：客户端里的 DTLS/ECDH/secp224 是**静态链接的 OpenSSL 自带表**
     （OpenSSL x45、DTLS1_ x27、conf_def x1、X509 x119、ASN1 x138、OCSP x47、EVP_ x38）
     —— **字符串不能作为 CODOL 使用 DTLS 的证据**（§3）
  6. 会话记录 ① Hostaddress = bd_common_addr(ip, port)（codol_crypto.py:369，服务端权威字段序）

外部侧（本轮克隆 + 子代理精读）：
  iw4x-client      HEAD d1b175da… 511 文件 / 109,496 LOC（C++20，x86，premake5，只产出 DLL）
  CoD4x_Server     HEAD ddd65fc…  404 文件 / 180,284 LOC（C，GNU make，TARGETNAME=cod4x18_dedrun）
  iw4x-rawfiles    数据/二进制（iw4x.exe 3,932,160 B）—— 本地目录为空克隆（0 文件，见 §9 注）
```

---

## §1 CODOL 的 socket() 全枚举（本轮硬结果）

方法：定位 ws2_32 IAT 槽 socket = 0xCA8548，枚举全部 call dword ptr [0xCA8548]，再读它前面的 3 个 push。
（cdecl：最后一个 push 才是第 1 个参数）

| # | 函数起点 | 调用点 | af / type / proto | 判定 |
|---|---|---|---|---|
| 1 | 0x77FBF0 | 0x77FC11 | 6 / 2 / 0x3E8(1000) | AF_IPX + SOCK_DGRAM + NSPROTO_IPX → **IPX 局域网广播** |
| 2 | 0xAD6D60 区 | 0xAD6D7F | [esi] / [esi+4] / [esi+8] | **通用 socket 包装**（三参数来自描述符）；可被 [edi+0x1B8] 钩子接管 |
| 3 | 0xBB18B0 | 0xBB18B9 | 2 / 2 / 0x11 | **AF_INET + SOCK_DGRAM + IPPROTO_UDP** |
| 4 | 0xC653D0 | 0xC653DC | 2 / 1 / 6 | AF_INET + SOCK_STREAM + IPPROTO_TCP |
| 5 | **0xC65410** | 0xC6541C | 2 / 2 / 0x11 | **AF_INET + SOCK_DGRAM + IPPROTO_UDP** ← 套接字类的 UDP 工厂（vtable +0x08） |
| 6 | 0xC768D0 | 0xC768DB | 2 / 1 / 6 | AF_INET + SOCK_STREAM + IPPROTO_TCP ← **DW 大厅 TCP** |
| 7 | 0xC7BAF0 | 0xC7BAF6 | 2 / 1 / 0 | 通用 TCP（proto 由调用方给） |
| 8 | 0xC7BB00 | 0xC7BB06 | 2 / 2 / 0 | 通用 UDP |
| 9 | 0xC7BB10 | 0xC7BB19 | 1 / arg / 0 | 通用（af=1） |

**UDP 创建点共 4 个**（0xBB18B0、0xC65410、0xC7BB00，以及通用包装 0xAD6D7F 在 type==2 时）。
其中 **0xC65410 是"套接字类"的虚方法**，类 vtable = 0xD8E3A8：

```
0xD8E3A8 +0x00 0x00C65D30 (dtor)
         +0x04 0x00C653D0  TCP create
         +0x08 0x00C65410  UDP create     ← 谁调用套接字类的 +0x08，就是"谁要 UDP"
         +0x0C 0x00C65440
         +0x10 0x00C65460
         +0x14 0x00C65480
         +0x18 0x00C654A0
  安装点：0xC65D3B / 0xC65D8A（ctor）；工厂 0xC65D70 分配 0x24 字节后装 0xD8E3A8
```

**地址对象类**：端口是 +0x84 处的 16 位字段
```
0xB75420  mov [ecx+0x84], ax   ; setter（**唯一调用者 0xBAFDFF**）
0xB75440  mov ax, [ecx+0x84]   ; getter（13 个调用者）
0xB75340                       ; 由该对象构造 sockaddr
0xC73900  ... 0xB75440 → 拷贝 0x84 字节 → 0xC76920 connect   ; 大厅/HTTP 的 TCP 连接
0xBAFDD0  ... 若 port==0 则 push 0x50(80) → 0xB75420 → connect ; **HTTP 默认 80**
```

⚠ 结论：这个"+0x84 端口"的地址类是 **TCP 侧（HTTP / DW 大厅）共用**的，
**不能**因为它在匹配模块里被读一次（0x621FD1）就断定它是 Battle 端口。

---

## §2 ★ 客户端确实有"服务器端点"机制（本轮最重要的 CODOL 新证据）

0x621E50（函数起点 0x621E50，2 个参数）——**服务器端点解析器**：

```
0x621E7D  mov esi, 0xFFFFFFF7          ; 默认错误码 -9
0x621E82  call 0x643300                ; 取全局对象
0x621E91  call 0xBAC600                ; → edi = [全局+0x1F0] = 传输对象
0x621EA0  mov edx,[edi] ; mov eax,[edx+0x20] ; call eax
0x621EA9  cmp eax, 1 ; jne 失败         ; ★ **传输对象必须处于 state 1**
0x621EB2  mov edx,[edi] ; mov edx,[edx+0x2C]   ; 查询方法
          push arg3 / push arg2 / push &局部结构
0x621ED3  call edx                     ; 查询 → esi = 结果码/长度
0x621ED7  cmp esi, 4 …
0x621F19  … 成功则写输出结构：
            0xB75440 → 端口 → **[edi+0x08]**
            memcpy → 4 字节 IP → **[edi+0x04]**
            **[edi+0x00] = 4**（类型/kind）
            **[edi+0x14] = [ebp-0xA0]**
```

调用者（**游戏层**，不是匹配模块）：
```
0x4F8F25   call 0x621E50   → 成功后按 [out], [out+4], [out+8], [out+0xC] 继续构造 0x18 字节结构
0x4F9075   call 0x621E50   → 同样，读 [out+4] 与 [out+8]，并与 [0x849B5CC] 比较
```

⇒ **客户端确实会把"服务器地址"实体化成一个 {kind=4, ip, port} 结构，并交给游戏层使用。**
⇒ 但这条路的**前置条件是传输对象 state==1**。而 017/019 的实测是：accepted 分支从未执行，
   匹配/传输状态机停在更早的档位（t_5E8 0→1→2→3、[matching+0x278] armed 窗口只有 20~30ms）。
   也就是说：**即使有 Battle Server 在监听，客户端也不会先走到"取端点"这一步。**

---

## §3 ★ 纠正：客户端里的 DTLS / ECDH / secp224 是 OpenSSL 的表，不是 Battle 证据

本轮对 image_best.bin 做字符串普查：

```
OpenSSL    count=45    first=0x00D3686C
conf_def   count=1     first=0x00D4A476      ← crypto\conf\conf_def.c（OpenSSL 配置解析器）
SSLv3      count=2     first=0x00D3685C
TLSv1      count=3     first=0x00D36864
DTLS1_     count=27    first=0x00D55DB0      ← 全是 OpenSSL 的 DTLS 状态名
secp224    count=2     first=0x00D3D628
OCSP 47 / X509 119 / ASN1 138 / BN_mod 11 / EVP_ 38
mbedTLS    count=0     wolfSSL count=0
```

再看引用关系（关键）：
```
DTLS@0xD55DB0        dword refs = [0xE37C64]      ← 只在数据区被引用
secp224r1@0xD3D628   dword refs = [0xE32C98, 0xE32C9C]
且邻域是：
  0xE32C80: secp224k1 / 0xE32C88=0x2C8 / ...
  0xE32C98: secp224r1 / 0xE32CA0=0x2C9 / ...
  0xE32CB0: secp256k1 / ...
  0xE37C40: DTLS1_SEND_HELLO_VERIFY_REQUEST / DTLS1_SEND_SERVER_CERTIFICATE /
            DTLS1_SEND_SERVER_HELLO / DTLS1_SEND_SERVER_KEY_EXCHANGE /
            DTLS1_WRITE_APP_DATA_BYTES / GET_CLIENT_FINISHED / GET_CLIENT_HELLO /
            GET_CLIENT_MASTER_KEY / GET_SERVER_FINISHED / GET_SERVER_HELLO
```

⇒ 这是**静态链接进客户端的 OpenSSL** 的曲线名表 / DTLS 状态名表。
⇒ **"CODOL 客户端有 DTLS/ECDH/secp224 子系统"这一长期判断，作为"Battle 使用 DTLS"的证据，是不成立的**
   （此后只能记为：客户端链接了 OpenSSL，可被任何模块使用）。
⇒ 保留的有效证据只有一条：**10-06 21:28 在 28960 上真实抓到的 4 步握手**（见 §4）。

---

## §4 CODOL Battle 通道的实际契约（来自 28960 的真实抓包，非字符串推断）

来源：battle_srv.log 2026-10-06 21:28:19–21:29:25（收包=155 / NAT=2 / init=1 / keyex=1 / data=151 / 会话=1），
并由 battle_server.py 逐条复现（其源码注释即契约文档）。

```
步骤 1  NAT 遍历
        客户端发 29 B，**首字节 13**；服务端回同包、**首字节改 12**；尾 3 字节 7f 00 00 01 20 71
步骤 2  初始化（我方曾称 "DTLS init"）
        客户端发 16 B：  01 02 0000 0000 clientTag(2) 01 00 00 00 00 00 00 00
        服务端回 38 B cookie：含 serverTag(2) / 本机 IP:port / u64 1
步骤 3  握手（cookie + 公钥）
        客户端发 219 B： 03 02 serverTag(2) | cookie(38B) | ...(67B) | u64 1 | 公钥(100B)
        服务端派生传输密钥后回 **114 B key-exchange ack**（含服务端公钥 100B）
步骤 4  数据帧
        06 02 serverTag(2) | seq(2) | hmac(8) | len(2) | cipher
        密钥流 = AES（由 SHA1 派生），完整性 = HMAC-SHA1 前 8 B
密钥派生  ECDH P-224 → 共享 x 坐标 28 B 大端 ‖ securityKey(16B) = 44 B → SHA1 → 20 B → 补 0 到 24 B
          AES 用前 16 B，HMAC 用全部 24 B
securityKey = 16 个 0x01（**不是 0**）
上层载荷  客户端发 getchallenge / connect（\name\M7-E8S6Client）/ stats；
          之后 30 B OOB 心跳 ×9，再每约 0.5 s 一个 **14 B usercmd**（01 00 00 00 00 00 00 00 00 00 00 00 00 02）
          → 约 60 s 后客户端连发 20 次 cancelConnect 并停止
服务端下行 10-06 那次 **TX_GAMESTATE = 0**（从未下发 game state）；
          10-07 修复后才出现 TX_GAMESTATE seq=1 state=259B，随后 141 B 快照 @128Hz
```

**⚠ 名称纠正**：把第 2/3 步叫 "DTLS" 是**我们的命名**，不是证据。
真实 DTLS 的 ClientHello ≥ 40 B，而实测第 2 步只有 **16 B**，第 4 步的帧头是自定义的
06 02 serverTag seq hmac8 len，既不是 DTLS record 头（content_type/version/epoch/sequence），
也不符合 CoD4X/IW4X 的 netchan（netchan 头是 outgoingSequence int + qport short）。
⇒ 正确的表述是：**CODOL Battle 使用一套自定义的"cookie + ECDH P-224 + HMAC/流加密"握手，
   它借用了 DTLS 式的原语，但不是 DTLS 协议。**

---

## §5 IW4X 侧结论（子代理精读 iw4x-client HEAD d1b175da）

```
IW4X_SERVER_SOURCE_NOT_FOUND = **成立**
  · premake5.lua:216-217 只构建 **SharedLib 'iw4x'**（一个 DLL）；源树里**没有**任何
    sv_main.c / sv_client.c / sv_snapshot.c / netchan.c 的服务器实现
  · 专用服务器二进制是**预编译且闭源**的 iw4x-rawfiles\iw4x.exe（3,932,160 B）
  · 源码里只有 SV_* 的**函数指针地址表**（Game/Server.cpp:5-27）与 hook 点
  · getchallenge 在 src 里 **0 命中**；28960 在 src 里 **0 命中**
IW4X 的网络面只有"前门"（控制面）：
  · 线格式：FF FF FF FF + ASCII 命令 + '\n' + 载荷（Network.cpp:184-229）
  · OOB 动词：getinfo/infoResponse、getstatus/statusResponse、getInfo、
    discovery/discoveryResponse、resolveAddress、print、rcon、rconSafe、
    sessionSyn/Ack/Fin、nodeListRequest/Response、connect、heartbeat、getplaylist
  · connect 的认证信封：Proto::Auth::Connect{signature,publickey,token,infostring}；
    校验链 Auth.cpp:155-274（xuid == SHA1(pubkey)[:8]、ECDSA VerifyMessage、
    proof-of-work GetZeroBits ≥ sv_securityLevel 默认 23）
  · matchtype 分类 0 NO_MATCH / 1 PARTY_LOBBY / 2 DEDICATED_MATCH / 3 PRIVATE_PARTY（Party.cpp:25-32）
  · 发现：HTTP master（master.iw4x.io/v1/servers/iw4x?protocol=0x99）+ node 兜底 + LAN 广播（25000–35000）
  · 心跳：SendCommand(master, "heartbeat", "IW4")（Dedicated.cpp:163-178）
  · PROTOCOL = 0x99（Structs.hpp:3）
IW4X **没有** DTLS/ECDH/secp224（src 全 0 命中）；游戏通道**无传输加密**
  · 加密只用于 (a) connect 信封的 ECDSA 签名 (b) FastFile zone 载荷
可复用比例：**约 10–15%**（约 6 个文件 / ~2000 行 / 全仓 109,496 行）——只有 OOB 前门
不可复用：快照/基线/delta 压缩、netchan 可靠+分片传输、usercmd 摄入、客户端槽位状态机、
          超时/限速、服务端地图 spawn（引擎内部，只有地址）
数据结构（可直接照抄布局）：
  netchan_t        sizeof == 0x62C（Structs.hpp:7099-7119）
        outgoingSequence 0x00 | sock 0x04 | dropped 0x08 | incomingSequence 0x0C |
        remoteAddress 0x10 | qport 0x24 | fragmentSequence 0x28 | fragmentLength 0x2C |
        fragmentBuffer 0x30 | fragmentBufferSize 0x34 | unsentFragments 0x38 |
        unsentFragmentStart 0x3C | unsentLength 0x40 | unsentBuffer 0x44 |
        unsentBufferSize 0x48 | prof 0x4C(0x5E0)
  netadr_t         sizeof == 20（Structs.hpp:7082-7090）: type 0x00 | ip 0x04 | port 0x08 | ipx[10] 0x0A
  connstate 枚举   CA_DISCONNECTED 0 / CA_CONNECTING 3 / CA_CHALLENGING 4 / CA_CONNECTED 5 /
                   CA_LOADING 7 / CA_PRIMED 8 / CA_ACTIVE 9
  server 侧        CS_FREE 0 / CS_ZOMBIE 1 / CS_CONNECTED 3 / CS_ACTIVE 5
```

---

## §6 CoD4X 侧结论（子代理精读 CoD4x_Server HEAD ddd65fc）

```
形态   纯专用服务器；q_shared.h:51 **无条件 #define DEDICATEDONLY**（17 处 ifndef 把客户端/渲染编译掉）
       makefile:16 TARGETNAME = **cod4x18_dedrun**；产品串 "Call of Duty 4 - Modern Warfare Dedicated Server"
       32 位（-m32 -msse2）；C(gnu11) 为主；src 非 vendored = 404 文件 / 180,284 行
网络层 src\sys_net.c（sockets，3,998 行）+ netchan.c（489 行）+ sv_net_chan.c + net_game.c
UDP    sys_net.c:1599 socket(PF_INET, SOCK_DGRAM, IPPROTO_UDP)（NET_IP4Socket）；bind:1667；FIONBIO:1614
       **PORT_SERVER 28960**（net_game_conf.h:46）★ 与 CODOL 通告的端口数值相同（但相同不代表血缘）
OOB    NET_OutOfBandPrint = 4 个 0xFF（0xFFFFFFFF）+ 文本（netchan.c:509-512）；
       收侧 sv_main.c:1943-1950 读 int，== -1 → SV_ConnectionlessPacket
握手（完整且可作模板）
  C→S  getchallenge <clientChallenge>
  S→C  challengeResponse <challenge> <clientChallenge> 0 xproto 18
       其中 challenge = **NET_CookieHash(from)** = SHA1(ip[4] ‖ port[2] ‖ 58B 随机密钥)（netchan.c:600）
  C→S  connect "<userinfo>"（带 challenge/qport/protocol/name/password/xver）
  SV_DirectConnect（sv_client.c:138）：challenge != NET_CookieHash(from)
       → "error\nNo or bad challenge for address.\n"
       → 槽位分配（重连复用 / 反 DoS / 私有位 / connectqueue）→ Netchan_Setup → **CS_CONNECTED**
  S→C  connectResponse（sv_client.c:562-564）
  然后 SV_SendClientGameState → CS_PRIMED → svc_gamestate + configstrings + baselines
  客户端首个 usercmd → SV_ClientEnterWorld → **CS_ACTIVE**（sv_client.c:1191）
状态机 clientConnectState_t { FREE, ZOMBIE, CONNECTED, PRIMED, ACTIVE }（server.h:60-67）
复制   sv_snapshot.c：SV_BuildClientSnapshot 891 / SV_WriteSnapshotToClient 109 /
       SV_SendClientSnapshot 538 / SV_SendClientMessages 1078；delta vs frames[PACKET_BACKUP] +
       16 MB archivedSnapshotBuffer
加密   **游戏通道无加密**：SV_Netchan_Encode（sv_net_chan.c:79）只是 **XOR 混淆**，
       key = challenge ^ serverId ^ messageAcknowledge（:52）/ challenge ^ outgoingSequence（:85）
       mbedtls 只被 HTTPS 更新客户端使用（httpftp.c:1202-1251，MBEDTLS_SSL_TRANSPORT_STREAM）
       **无 DTLS / 无 ECDH / 无密钥交换**
netchan_t 布局与 IW4X 1:1 对应（netchan.h:55-79；多一个 upperqport@0x26）
       ⇒ 这是**共同的 Quake3 血统**证据，**不是** CoD4X↔CODOL 的血缘证据
```

---

## §7 ★ 关键问题：缺少 Battle Server 是否足以解释"客户端不进入 Battle"？

**答：REFUTED（作为解释）。** 而且这不是"很可能"，是有直接实验证据的。

### 7.1 支持的证据（全部为已发生的事实）

```
E1  **我们已经在 28960 上开着监听**跑过相关运行。
    battle_srv.log 记录 anchor 之后共 64 次 battle_server 启动（51 次绑 127.0.0.1、12 次绑 0.0.0.0），
    017/019 的运行期间服务器确实在监听（0.0.0.0:28960，pid 2404 直到 10-08 20:47 仍在监听）。
E2  **客户端一个包都没发**：所有 anchor 之后的真实运行，battle 侧统计恒为
    收包=0 NAT=0 init=0 keyex=0 data=0 会话=0（battle_srv.log 中 2499 条 [stat] 里仅 4 条非零，
    而那 4 条都属于 10-06 21:28 那次——发生于 accepted 尚未被研究、且监听刚起的那一次）。
E3  **客户端从未提及 28960**：n10_battlefix_20261007.txt 中字符串 28960 出现 **0 次**。
    （也就是说：客户端连"打算连 28960"的痕迹都没有。）
E4  **accepted 分支从未执行**：017 采样 0/281+433 行、019 采样 0/267 行，[matching+0x288] 恒为 0。
E5  **端点解析器有前置状态门**：0x621E50 在取端点前要求传输对象 state==1；
    客户端在观测中从未到达该状态（t_5E8 只到 3，armed 窗口仅 20~30 ms）。
E6  **客户端的实际网络活动只在 lobby TCP**：0x85 帧、21/5 查询、6/14 mmbook 重试（3~9 秒一次）。
```

### 7.2 结论分级（按要求的五个档）

```
"缺少 Battle Server 足以解释客户端不进入 Battle"  = **REFUTED**
    理由：E1 + E2 + E3 —— 有服务器在监听、客户端零发包、且从未提及该端口。
    缺服务器既不是充分条件，也**不是当前的近因**。

"客户端不进入 Battle 的近因"                      = **PROVEN = accepted 门未通过**
    理由：E4 + E5 —— accepted 未执行 ⇒ 传输状态未达 state 1 ⇒ 端点解析器根本不会被成功调用。

"要真正进入对局终究需要有人在 28960 应答"          = **STRONG CANDIDATE**
    理由：逻辑必然（E2 的反面：一旦客户端开始发包，必须有应答方），但从未被观测验证。
    注意：这与"当前不进入的原因"是两个不同命题，不要混为一谈。
```

⚠ 必须写清的反面：**本轮没有证明"客户端永远不会连 28960"**。
   我们只证明了"在我们已做过的所有运行里，它没连"。
   若将来 accepted 门被打开，客户端开始发包，那时"是否需要自建 Battle Server"才成为可判定问题。

---

## §8 CODOL_BATTLE_SERVER_CONTRACT（15 项；未知一律标 UNKNOWN）

| # | 契约项 | 取值 | 等级 | 证据 |
|---|---|---|---|---|
| 1 | Listen address | 由 21/5 会话记录 ① Hostaddress 下发；本工作区值 127.0.0.1。服务端能否绑 0.0.0.0 | CANDIDATE | codol_crypto.py:369 bd_common_addr(host_ipv4, host_port)；实测日志 127.0.0.1:28960 |
| 2 | Listen port | **28960** | CONFIRMED | 21/5 记录下发；且真实客户端曾在该 UDP 端口上完整握手（10-06 21:28，收包=155） |
| 3 | Transport | **UDP**（AF_INET + SOCK_DGRAM） | CONFIRMED | 客户端 UDP 工厂 0xC65410 / 0xBB18B0；抓包为 UDP |
| 4 | Initial client packet | 29 B NAT 探测，**首字节 13** | CONFIRMED | battle_srv.log RX#1/#2；battle_server.py:401-408 |
| 5 | Server response | 回同 29 B，**首字节改 12** | CONFIRMED | 同上 |
| 6 | Session establishment | 16 B init（01 02 …）→ 38 B cookie；219 B cookie+公钥 → 114 B key-exchange ack；随后进入 06 02 数据帧 | CONFIRMED（三步都真实发生过） | battle_srv.log RX#3/#4/#5-#7；battle_server.py:412-499 |
| 7 | Authentication / session token | 传输密钥 = SHA1(ECDH P-224 共享 x（28B BE）‖ securityKey（16B）) → 20B → 补到 24B；securityKey = 16 个 0x01 | CANDIDATE | battle_server.py:17-20,328-355,452-499；**没有观测到任何 per-session ticket** |
| 8 | Match identity | **UNKNOWN** | UNKNOWN | battle 通道上从未观测到 matchId；playlist/roomId 只出现在 lobby 侧记录里 |
| 9 | Map | **UNKNOWN（在 battle 通道上）** | UNKNOWN | map 名走 lobby（21/5 记录第 3 项 map_name；coop_map.txt 自纠环）；battle 通道未见 map 传递 |
| 10 | Playlist | **UNKNOWN（在 battle 通道上）** | UNKNOWN | playlist 在 21/5 请求/记录里（PLAYLIST_VERSION=796） |
| 11 | Player identity | **UNKNOWN**；connect 串里出现过 \name\M7-E8S6Client | UNKNOWN | battle_srv.log decode；未观测到 uid/CODOID 在 battle 通道 |
| 12 | State synchronization | 服务端→客户端：game state 259 B + 141 B 运动快照 @128 Hz；客户端→服务端：14 B usercmd 每约 0.5 s | CANDIDATE | 我方实现（battle_server.py）+ 10-06 观测到 usercmd；但 **game state 从未被真实客户端确认**（TX_GAMESTATE=0 in that session） |
| 13 | KeepAlive | 客户端发 30 B OOB 心跳（观测到 ×9）；间隔约数秒 | CANDIDATE | battle_srv.log RX#8+ |
| 14 | Disconnect | 客户端连发 20 次 cancelConnect 后停止 | CONFIRMED（客户端行为） / UNKNOWN（服务端应如何应答） | battle_srv.log 21:29:24-25 |
| 15 | Error handling | **UNKNOWN** | UNKNOWN | 未观测 |

**契约可信度总评**：第 1–6 + 14 项有**真实抓包**支撑，是本轮最硬的资产；
第 7/12/13 项来自我方实现与部分观测，属 CANDIDATE；
第 8/9/10/11/15 项**在 battle 通道上完全 UNKNOWN** —— 任何声称"CODOL battle 有 matchId/ticket/map 字段"
的说法目前都**没有证据**。

---

## §9 三方特征矩阵（每个单元格带等级）

等级：CONFIRMED / CANDIDATE / UNKNOWN / NOT_OBSERVED

| Feature | CODOL | IW4X | CoD4X |
|---|---|---|---|
| Client/Server architecture | **CONFIRMED**：客户端 + 外部大厅(127.0.0.1:3074) + 外部战斗端点 | **CONFIRMED**：DLL hook 闭源 exe，角色运行时选 | **CONFIRMED**：纯服务端 cod4x18_dedrun |
| Lobby/session separation | **CONFIRMED**：DW 大厅 TCP（0x7F3800/0xC768D0/0xC76920 + DW_LOBBY_CONNECTED）与战斗端点分离 | **CONFIRMED**：Party/Steam 大厅 + matchtype 0..3 | **NOT_OBSERVED**：无大厅/无匹配服务，只有 master 注册 |
| Dedicated server | **CANDIDATE**：端点由 21/5 下发、我们绑 UDP 28960；客户端无服务端实现 | **CANDIDATE**：com_dedicated 模式存在，但二进制闭源（IW4X_SERVER_SOURCE_NOT_FOUND） | **CONFIRMED**：DEDICATEDONLY 无条件定义 |
| UDP transport | **CONFIRMED**：socket(2,2,0x11) @0xC65410/0xBB18B0；战斗在 UDP 28960 | **CONFIRMED**：引擎 Sys_SendPacket（NS_CLIENT1） | **CONFIRMED**：sys_net.c:1599 |
| Connection handshake | **CONFIRMED**：4 步自定义（NAT→init/cookie→cookie+pubkey/ack→data） | **CANDIDATE**：getinfo→infoResponse→CL_ConnectFromParty；引擎 getchallenge 不在源码 | **CONFIRMED**：getchallenge→challengeResponse→connect→SV_DirectConnect→connectResponse |
| Session identifier | **CONFIRMED**：SessionId u64 0x1122334455667788（记录 #2；A/B 用 #7） | **CANDIDATE**：Session::Frame challenge（且 DISABLE_SESSION）；Steam lobby ID | **CANDIDATE**：sv_serverid + per-client challenge（非 UUID） |
| Match identifier | **CANDIDATE**：roomId 字符串 / sessionId / playlist / map（都在 lobby 记录里） | **CANDIDATE**：Steam lobby ID / matchtype | **NOT_OBSERVED** |
| Server endpoint | **CONFIRMED**：21/5 记录 ① Hostaddress；客户端 0x621E50 产出 {kind=4,ip,port} | **CONFIRMED**：HTTP master + node + LAN 广播 | **CONFIRMED**（注册方向）：heartbeat 到 master，PORT_SERVER 28960 |
| Ticket/reservation | **CANDIDATE**：matching reservation 数组 this+0x75D8/stride 0x238 + 6/14 mmbook 预约；battle 通道上未见 ticket | **NOT_OBSERVED**（游戏通道）：仅密码保留位 + Steam 桩 | **CONFIRMED**（但语义不同）：私有位 + connectqueue；master token = 服务器注册用 |
| DTLS | **NOT_OBSERVED**：字符串是 OpenSSL 表；16 B init 远短于真实 DTLS ClientHello；帧头自定义 | **NOT_OBSERVED**：src 0 命中 | **NOT_OBSERVED**：mbedtls 只用于 HTTPS 更新 |
| ECDH | **CANDIDATE**：219 B 包里带 100 B 公钥、我方以 P-224 派生密钥并被接受 | **NOT_OBSERVED** | **NOT_OBSERVED** |
| secp224 | **CANDIDATE**：同上（字符串本身来自 OpenSSL，不作证据） | **NOT_OBSERVED** | **NOT_OBSERVED**（mbedtls 表仅 HTTP） |
| Map loading | **CANDIDATE**：map 名随 21/5 记录下发；coop_map.txt 自纠环 | **CONFIRMED**：客户端 fastfile 列表 + R_LoadGraphicsAssets；SV_SpawnServer 只有地址 | **CONFIRMED**：SV_SpawnServer 4739 / d3dbsp + _load.ff |
| FastFile/Zone | **CONFIRMED**：IWff0100 / IWffs100；main*.ff 层一已解（RSA zone key）；974 个 .ifs | **CONFIRMED**：ZoneKey 1191B DER RSA + rsa_decrypt_key_ex + ctr_start | **CONFIRMED**：7 个固定 zone + DB_LoadXAssets + db_load.cpp |
| Server game state | **CANDIDATE**：我方 259 B game state + 141 B 快照，但唯一真实会话 TX_GAMESTATE=0（未被确认） | **CANDIDATE**：引擎内部，只有 SV_* 地址 | **CONFIRMED**：SV_WriteGameState 3262 / svc_gamestate |
| Client game state | **CONFIRMED**：14 B usercmd 真实观测 | **CONFIRMED**：clientConnection_t（0x615E8） | **CONFIRMED**：usercmd + SV_UserMove |
| Dedicated server lifecycle | **UNKNOWN** | **CANDIDATE**：Dedicated.cpp 初始化/关闭；二进制闭源 | **CONFIRMED**：SV_Init/SV_Frame/heartbeat/Shutdown |
| Network state machine | **CANDIDATE**：传输 state==1 门（0x621E50）、[matching+0x278] armed、t_C8/t_5E8 序列 | **CONFIRMED**：CA_* 与 CS_* 枚举 | **CONFIRMED**：clientConnectState_t 及其转移 |

### 9.1 关于"血缘"的严格结论

```
· 端口 28960 **相同**（CODOL 通告值 = CoD4X PORT_SERVER）——**不构成血缘证据**，数值巧合。
· netchan_t 布局 IW4X 与 CoD4X **1:1 相同** —— 这是二者共同的 **Quake3 血统**证据，
  **不是** CODOL 的血缘证据（CODOL 未发现该结构）。
· CODOL 的战斗握手（cookie + ECDH P-224 + HMAC/AES 流）在 IW4X 与 CoD4X 中**都不存在**
  （IW4X 无加密；CoD4X 只有 XOR 混淆）。⇒ **CODOL 的战斗通道是三者中最独特的**。
· 因此：**CODOL_BATTLE_ARCHITECTURE = DISTINCT（在战斗通道/握手/密钥交换这一层）**，
  而在**服务器工程骨架**这一层可以借用 CoD4X（DISTINCT + HYBRID 的组合）。
```

---

## §10 最终硬结论

```
CODOL_BATTLE_ARCHITECTURE = **DISTINCT**（战斗通道/握手/加密层面）
                             + **HYBRID**（服务器骨架可借 CoD4X、OOB/发现可借 IW4X）
    · 支持 DISTINCT：cookie+ECDH 握手、06 02 帧头、16 B init —— IW4X/CoD4X 均无
    · 支持 HYBRID：连接状态机/槽位/超时/快照复制这些"服务器工程"部分是通用的

IW4X_REFERENCE_VALUE = **LOW–MEDIUM**
    · 可用：OOB 帧（0xFFFFFFFF+cmd+\n）、OOB 动词集、connect 认证信封结构、
            发现(master/node/LAN)、心跳、netchan_t/netadr_t 布局
    · 致命缺口：**没有服务端源码**（IW4X_SERVER_SOURCE_NOT_FOUND）；无 DTLS/ECDH

COD4X_REFERENCE_VALUE = **HIGH（作为服务器骨架模板） / LOW（作为战斗协议模板）**
    · 可用：sys_net 事件循环、clientConnectState_t、槽位/队列/超时策略、
            gamestate 与 configstring 的分离、快照/归档复制、master 心跳
    · 不可用：握手与加密（CoD4X 只有 XOR 混淆，CODOL 是 cookie+ECDH+HMAC）

BEST_REFERENCE = **HYBRID**（控制面 CoD4X + OOB/auth 信封 IW4X；握手只信 CODOL 自身证据）

NEXT_STEP（下一阶段进入条件）：
  1. 先关 **020 的 accepted 门**（additional accepted guard）；
  2. 只有当 accepted 执行、且客户端真的向 28960 发包之后，
     才用 §8 的契约去评估"是否自建 Local Battle Server"；
  3. **在此之前不要写 Battle Server**——因为 §7 已证明它不是当前阻塞点。
```

---

## §11 本轮产出与遗留

### 11.1 产出
```
DEV-BOOKING\PVE-BATTLE-CONTRACT-LINEAGE-021.md      ← 本报告
DEV-BOOKING\scripts\_021_battle.py                 ← 只读分析工具（sock / sweep）
DEV-BOOKING\scripts\_021_strs.py                   ← 字符串普查工具
DEV-BOOKING\_lineage021\iw4x-client                ← IW4X 浅克隆（511 文件 / 109,496 行）
DEV-BOOKING\_lineage021\CoD4x_Server               ← CoD4X 浅克隆（404 非 vendored 文件 / 180,284 行）
DEV-BOOKING\_lineage021\iw4x-rawfiles              ← 空克隆（0 文件）★ 遗留
```

### 11.2 遗留 / UNKNOWN
```
U-1  iw4x-rawfiles 克隆结果为 0 文件（git 报 exit 1，但仅 stderr 有进度输出）。
     影响：iw4x.exe（3,932,160 B）与默认 cfg/playlists 未能读取。
     不影响本轮结论（IW4X 服务端源码本来就不存在）。
U-2  套接字类 vtable +0x08（0xC65410，UDP）的**调用者**未定位：
     需要先找到 0xD8E3A8 实例的创建者（工厂 0xC65D70 的调用者），
     才能穷尽"客户端在何处要 UDP"。这是本轮未做完的一条线。
U-3  0x621E50 的传输对象 [全局+0x1F0] 的具体类型与 state 语义未展开
     （只知 state==1 是前置条件）。
U-4  battle 通道上的 matchId / map / playlist / player identity：仍全部 UNKNOWN。
U-5  10-06 21:28 那次会话究竟是真实游戏客户端还是实验重放，日志本身无法区分（S4 的 U-1）。
U-6  0x4F8F25 / 0x4F9075 两个游戏层调用点所在函数的完整语义未展开。
```

（全文完 · STATIC ONLY · 未修改任何 CODOL 文件 / 未修改 Server · 未把外部项目当作 CODOL Server）

