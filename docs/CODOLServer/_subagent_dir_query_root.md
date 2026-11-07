# CODOL 目录响应“空树”根因、第二跳与 TCLS 前置 HTTP 流

分析日期：2026-09-25

范围：只读分析 `run_codol_001\runs\TCLS_DIR_20260924_220810\pktmon.pcapng`、同目录 ETW/过程材料、`COD OL\TCLS` 配置与 `Dir.dll`。没有修改被分析文件，没有改 DNS、路由、网卡、防火墙，没有启停进程，没有碰 985/ACE 组件。本文件是本任务唯一新增报告。

## 结论摘要

1. **`60.29.240.113:8001` 实际是 TCLS/TGP QoS 上报端点，不是 CODOL 版本清单接口。** 配置文件把它列在“versionserver”端口列表中，但抓包中的实际请求是 `POST /` 到 `ied-tqos-tgp.qq.com:8001`，multipart 字段 `tqos` 内是 `{"Head":{"Cmd":5},"Body":{"QOSRep":...}}`；服务端只回 `HTTP/1.1 100 Continue` 和空体 `HTTP/1.1 200 OK`，没有版本号、补丁 URL、游戏服或大厅地址。
2. **`218.29.50.113:80` 和 `:443` 都是 `wegame.gtimg.com` 的 Rail/WeGame 资源链路，不是 `tcls.rail.qq.com`。** DNS 响应把 `wegame.gtimg.com` 解析到 `218.29.50.113`；80 端口 Host 是 `wegame.gtimg.com`，返回 302 到同一 Host 的 `rail_hosts.js`；443 ClientHello 的 SNI 是 `wegame.gtimg.com`，服务器证书 SAN 为 `*.gtimg.com`、`gtimg.com`。
3. **没有第二跳目录查询。** 两次 10009 连接各自只发 33 字节 `DIRTREEREQ`、各收 774 字节 `DIRTREERSP`，随后由 `tcls_core` 关闭；ETW 中 PID 19144 在第二个 774 字节接收后没有任何后续 `connect/send/recv` 网络事件（`all_etw.jsonl` 行 10509--10512 后，PID 19144 最后一条就是 close）。全 pcap 在第二条 774 字节响应之后也没有新的目录魔数 `0a 09 64 1a`，没有客户端出站 33/774 目录 TLV。注意：全局 pcap 后面存在其他进程、其他协议的网络流，不能把它们称为 TCLS 第二跳。
4. **`dirsystemconfig.cfg` 是高熵加密/混淆数据，尚未成功解密；已能确认的候选算法是 Tenio 自定义 KSA + 逐字节替换/XOR 流，而不是简单单字节 XOR。** `TCLS.dll` 的既有反汇编完整给出 KSA、掩码、MSVCRT LCG 和 transform；用文件时间候选、默认 key、`11111111`、`configcfg` 等离线尝试，没有得到明文键名。已知键名来自 `Dir.dll` 的 UTF-16LE 字符串池，只能作为目标 schema，不能冒充已解密结果。
5. **`CDir::OnMessageRecvDirData` 的 `Empty tree!` 是客户端解析/构建目录树后的空结果判定，不是“网络没有返回数据”。** 本次网络响应确实是 774 字节、含合法头、`dir_root` 和多组节点块；但其节点内容只有地区/测速结构，没有 CODOL 可进入的游戏服条目。`Dir.dll` 中错误字符串为 `[Dir][CDir::OnMessageRecvDirData] ERROR! Empty tree!`，而运行链随后仍能让 TCLSHost 报 `result: true` / `SendServerDirToTgp result=1`，说明 transport/frame 收取成功与“树中有可用游戏服”是两个不同层次。

## 1. `60.29.240.113:8001`：版本服务器配置名下的 QoS HTTP

### 配置证据

`COD OL\TCLS\config\VersionServerConfig.xml` 第 3--19 行：

```xml
<versionserver version="1" count="13" SectionTimeOut="5000" TotalTimeOut="600000"
  SuccessfulPort="8001;9001;10001;8002;9002;10002">
  <Server1 host="tcls.rail.qq.com"/>
  ...
  <portlist port1="8001" port2="9001" port3="10001" port4="8002" port5="9002" port6="10002" count="6"/>
</versionserver>
```

`COD OL\TCLS\config\versionserverconfigdynamic.ini` 第 1--3 行写的是：

```ini
[versionserver]
successfulserverid=10
successfulport=8002
```

所以“版本服务器”的配置命名/选择状态与本次 PID 19144 连接 `60.29.240.113:8001` 并不完全相同：本次抓包同时存在前置/探测流程，实际载荷决定了这两条 8001 流的业务性质。

### PID 19144 的 TCP 载荷

ETW `all_etw.jsonl`：

- 行 1424--1427：PID 19144 建立两条 `60.29.240.113:8001` 连接，分别发送 193 字节。
- 行 1437--1448：两条连接收到 25 字节的 `100 Continue`（ETW 的 `recv ret=25`），再发 504 字节；之后收到 99 字节的 `200 OK` 响应（对应 pcap 中的分片/重复记录）。
- 对应 pcap 唯一 TCP payload 重组：
  - 客户端端口 `55748`：pcap 唯一 payload 记录包序 1295/1395，重组总长 697 字节；`pktmon.txt` 行 21410 起是 193 字节首段，行 22874 起是 502 字节后段。差异来自 TCP/HTTP 分段与 pktmon 重复展示，HTTP 头声明 `Content-Length: 502`。
  - 客户端端口 `55749`：pcap 唯一 payload 记录包序 1317/1415，重组总长 697 字节；`pktmon.txt` 行 21666 起是 193 字节首段，行 23268 起是 502 字节后段。

重组后的请求（两条仅 boundary、QoS 数值略有差异）为：

```http
POST / HTTP/1.1
Host: ied-tqos-tgp.qq.com:8001
Accept: */*
Content-Length: 502
Expect: 100-continue
Content-Type: multipart/form-data; boundary=------------------------e28bccdbea0d36ea

--------------------------e28bccdbea0d36ea
Content-Disposition: form-data; name="tqos"

tqos={"Head":{"Cmd":5},"Body":{"QOSRep":{"BusinessID":1,"QosNum":1,"Flag":1,"QosList":[{"AppendDesc":{"Comm":{"IntList":[65536,132007,-1549230968,9232,6133,-1,0,0,0],"StrList":["d49390185510#0#0#2#20260924-220811","5F13D6C7-1148-41F0-994D-3080CE5C32EE","10000001","17179869195","1.0.0.1",""],"IntNum":9,"StrNum":6}},"QosID":6133,"QosVal":0,"AppendDescFlag":2}]}}}
```

字段级判断：`Head.Cmd=5`、`Body.QOSRep`、`QosID=6133`、网卡标识/UUID/客户端版本等都是质量/网络探测上报字段；载荷中没有版本比较请求、补丁文件名、游戏服 IP 或大厅端口。

服务器返回的完整明文为（每条连接相同）：

```http
HTTP/1.1 100 Continue

HTTP/1.1 200 OK
Date: Thu, 24 Sep 2026 14:08:09 GMT
Content-Length: 0
Connection: keep-alive

```

字节证据：100 Continue 为 `48 54 54 50 2f 31 2e 31 20 31 30 30 20 43 6f 6e 74 69 6e 75 65 0d 0a 0d 0a`，200 响应为 99 字节，见上述 pcap 包序和 `pktmon.txt` 对应 HTTP 行。**没有游戏服/大厅线索。**

## 2. `218.29.50.113:80` 与 `:443`

### 80/TCP：明文 Host 与返回体

PID 19144 的 ETW 行 1370--1371 表明它在 `22:08:12.733` 建立 `218.29.50.113:80` 并发送 84 字节。对应重复记录中的 pcap/`pktmon.txt` 行 16256 起，唯一请求是：

```http
GET /bin_res/ossjson/rail_hosts.js HTTP/1.1
Host: wegame.gtimg.com
Accept: */*

```

服务器响应由 pcap 重组为 260 字节（`pktmon.txt` 行 17032 起）：

```http
HTTP/1.1 302 Found
Location: https://wegame.gtimg.com/bin_res/ossjson/rail_hosts.js
Content-Length: 0
X-NWS-LOG-UUID: 5759600658407836263
Connection: keep-alive
Server: Lego Server
Date: Thu, 24 Sep 2026 14:08:08 GMT
X-Cache-Lookup: Return Directly

```

因此 80 端口是 WeGame Rail host 配置资源的重定向入口，不是 `tcls.rail.qq.com` 的版本 API。

### 443/TCP：SNI、证书与返回体边界

PID 19144 的 ETW 行 1434--1435 表明它随后连接 `218.29.50.113:443`，发送 517 字节 ClientHello。对应 pcap 的唯一 TLS ClientHello 在包序 335，载荷首部为：

```text
16 03 01 02 00 ...
```

ClientHello 扩展中存在可读字符串 `wegame.gtimg.com`（包序 335 的 payload 偏移 `0xDB` 附近；同一 517 字节载荷还含 `http/1.1` ALPN）。这就是 SNI/Server Name。

服务器回传是 TLS 加密流，不能把其应用层 HTTPS 返回体当作明文 HTTP；但证书链可从 TLS Certificate 记录离线解析。pcap 重组的服务器流包含 4 张证书，叶证书：

- Subject：`CN=*.gtimg.com, O=腾讯科技（北京）有限公司, ST=北京市, C=CN`（中文由证书 DER 解码，终端显示可能受 GBK 影响）。
- SAN：`*.gtimg.com`, `gtimg.com`。
- Issuer：`CN=DNSPod RSA OV, O=DNSPod, Inc., C=CN`。

因本次抓包没有 TLS 会话密钥，**443 的应用层返回体本身不可解密读取**；可以确认的返回内容是 TLS ServerHello/Certificate/加密 Application Data，而不是明文 HTTP。证书和 SNI 已足够确认它是 `wegame.gtimg.com` 资源链路，不是 `tcls.rail.qq.com`。

DNS/Host 交叉证据：`pktmon.txt` 第 323--379 行反复查询 `wegame.gtimg.com`，DNS 回答 CNAME 链后给 A `218.29.50.113`；第 1162 行为明文 Host，第 2050 行为 302 Location。

## 3. 是否有第二跳地区节点查询

### 明确回答

**没有。** 在本次运行/本次 pcap 中，没有观察到“拿到 774 字节地区目录后，再向某个地区节点以 33/774 字节量级 TLV 请求游戏服列表”的第二跳。

### 10009 两次连接的完整证据

两次客户端请求的唯一有效 payload 都是同一 33 字节：

```text
0a 09 64 1a 00 00 00 07 2a 9e 54 26 00 00 17 71
00 00 00 01 00 00 00 00 00 00 00 00 00 02 30 00 00
```

- 第一连接：客户端 `192.168.5.11:55917`，pcap 包序 40983，`pktmon.txt` 的对应 payload 展开在 `CODOLServer\_tcls_payload.txt` 第 341--376 行；服务端 774 字节在包序 43631，文件第 5--32 行展示其完整 hexdump。
- 第二连接：客户端 `192.168.5.11:55926`，pcap 包序 44017；服务端 774 字节在包序 46357。`pktmon.txt` 中对应出站 33 字节为第 845172 行起，服务端 774 字节为第 46357 个 pcap 记录对应区域。
- `all_etw.jsonl`：第一条 10009 connect 为行 9478，发 33 字节为行 9485/9577；第二条 connect 为行 9955，发 33 字节为行 9956/10053；第二条收 774 字节为行 10509，然后 10511--10512 close。

### “之后所有出站”筛选

以第二条 774 字节响应的 pcap 记录包序 **46357** 为边界，扫描其后所有唯一 TCP 帧：

- 后续唯一 TCP 帧：16232；流：551，说明 pcap 后面确实有其他进程/模块继续产生网络流。
- 后续仍出现的唯一 33 字节 payload 在包序 **136493**，方向为 `116.130.228.169:8080 -> 192.168.5.11:55866`，字节为 `5b7d0769bc4b5aff49819125fd809f7db85dff5085b611dffaa02536253ed5be29`，不是目录魔数，且是服务器到客户端、不是 tcls_core 出站。
- 后续唯一 774 字节 payload 只是包序 **46358** 的同一条 10009 服务端响应的 TCP/pktmon 重复展示；若把边界设到该响应完成后的包序 46827，后面 `len=774` 为 0、目录魔数命中为 0、客户端出站 `len=33/774` 均为 0。
- `all_etw.jsonl` 在 PID 19144 行 10509 收 774 后，行 10511--10512 关闭 socket；PID 19144 没有后续网络事件。后续 pcap 流不能归因给 TCLS 第二跳。

因此，地区树并不会在这次链路中触发一个可见的“地区节点 -> 游戏服列表”网络查询。当前 `[100]` 根因应继续按“目录响应可解析但无可用 CODOL 游戏服条目/启动元数据”追，而不是寻找遗漏的第二个目录服务器地址。

## 4. `dirsystemconfig.cfg` 解密判定

### 原始文件形态

`COD OL\TCLS\config\dirsystemconfig.cfg`：1144 字节；原始前 32 字节：

```text
cb 3a de 97 09 df 15 5f 08 ac 77 c0 12 e5 0f c1
f2 71 65 86 c1 b9 4d 8b d3 3e 12 c2 b5 38 72 50
```

全文件字节熵约 7.817 bit/byte，ASCII 明文比例很低；固定周期重复相等率也接近随机（周期 1/2/4/8/16/32/64/128/256 均约 0.2%--0.6%），不支持“一个固定字节循环 XOR”。

### 已确认的 Tenio 自定义算法边界

反汇编证据在 `analysis_logs\TCLS_tas_ksa.txt`：

- 第 10--56 行：8 字节 key 每字节分别 XOR 固定掩码 `8A E6 9B F3 C1 7D 40 25`。
- 第 69--105 行：把 key2 两个 BE32 异或成 seed。
- 第 112--136 行：256 轮 `state = state * 0x343FD + 0x269EC3`、`j=(state>>16)&0xff`、交换 S-box。
- 第 137--167 行：flag=0 时生成逆表。

`analysis_logs\TCLS_tas_cipher.txt` 第 75--123 行显示逐字节 transform：按 flag 做索引 XOR、8 字节滚动 key、S-box 查表、再次 XOR。`analysis_logs\TCLS_cipher_core.txt` 第 59--97、127--135 行显示 key getter：从文件 `GetFileTime` 取得 8 字节 key，时间为 0 时回退 `0x46D14CF9 / 0xEF1DC888`。`analysis_logs\handoff_recovery.md` 第 73--97 行给出了同一算法的整理版；`COD OL\scripts\tas_crypt.py` 第 9--38、49--92 行是离线实现。

这说明：**算法家族已确认是 Tenio/TAS 自定义 KSA+S-box+XOR，而不是简单 XOR；但不能直接证明 `dirsystemconfig.cfg` 使用的就是这个 key/flag/包装路径。**

### 离线尝试结果

对 `dirsystemconfig.cfg` 尝试了：

- Tenio 默认 key；
- `dirsystemconfig.cfg`、`Dir.dll`、`TCLS.dll`、`Client.exe`、`TenBase.dll`、`commonconfig.cfg`、`updateconfig.cfg` 的 LastWriteTime 生成 key；
- 低位/高位交换、字节反序等 key 变体；
- `11111111`、`configcfg` 等已知试探 key；
- flag=0/1。

没有得到可信 INI/plaintext 结构，也没有命中 `AutoRefreshServerList`、`LogicalGameServerNode`、`DHINFO` 等已知键。已有 `analysis_logs\handoff_recovery.md` 第 157--159 行也明确记录：同一 file-time cipher 对 `commonconfig.cfg`/tlog brute 失败。因此本报告**不宣称已解密**，也不把 `analysis_logs\dirsystemconfig.cfg.dec` 当作成功明文：该文件仍是 1144 字节高熵输出。

### 明文键名的静态证据

`COD OL\TCLS\Tenio\Dir.dll` 的 UTF-16LE 字符串池命中：

- `AutoRefreshServerList`：文件偏移 `0xCD620/0xCD680/0xCD6E0`；
- `MinRefreshPeriod`：`0xCD64C`；
- `AutoRefreshPeriod`：`0xCD6AC` 等；
- `isp_to_node`：`0xCD7DC`；
- `GetRoleInfoFromDir`：`0xCDD38`；
- `EnterFullStateServer`：`0xCD8F4/0xCD93C`；
- `IsSendAllServInSameGroup`：`0xCDAB4`；
- `NeedSkinSwitch`：`0xCDC64`；
- `IsUTF8`：`0xCDC88`；
- `ClickDisableServer`：`0xCD9D0`；
- `DHINFO`：`0xCDE1A`；
- `Relation`：`0xCC2F8`、`0xCDDC4`、`0xCDE08`、`0xCDE30` 等。

本版 `Dir.dll` 字符串池中没有直接命中 `LogicalGameServerNode`、`EntryTipsServer`、`RencenSvr`/`RencenSvrCount` 的完整 UTF-16LE 字符串；这不否定它们可能来自别的 DLL、配置或不同版本。已知键名只能说明期望的配置 schema，不能反推出 cfg 的明文内容。

## 5. `Empty tree!` 的确切语义

### 服务器返回的内容不是空帧

服务端响应的 774 字节在 `CODOLServer\_tcls_blocks.txt` 第 4--32 行逐字节展开：

- offset `0x00` magic `0a 09 64 1a`；
- offset `0x04` length `0x2ec=748`，总长 `26+748=774`；
- offset `0x08` ServiceID `0x2a9e5426=715019302`；
- offset `0x20` 起 payload 有 `dir_root`，字符串起点 offset `0x37`；
- 地区块从 `0x60` 起，名字长度/节点属性/测速字段均有值；
- `www.qq.com:443;1004` 位于响应 offset `0x180/0x1ee/0x25c/0x2cb`，其短 URL 位于 `0x19f/0x20d/0x27b/0x2ea`。

这不是 server 返回 `0` 字节、也不是 TCP 读失败。目录包至少包含地区节点的结构化记录。

### 客户端侧错误字符串与分支

`Dir.dll` UTF-16LE 字符串：

- `[Dir][CDir::OnMessageRecvDirData] ERROR! Empty tree!` 位于文件偏移 `0xCE60C`（同一尾部短串 `Empty tree!` 位于 `0xCE65E`）；
- `[Dir][CDir::SetDirMapInfo]total Server Count is %d` 位于 `0xCD122`、`0xCD18E` 附近；
- `DIRTREERSP` 位于 `0xCE718`，且其代码引用落在文件偏移 `0x23F23/0x24097`，对应 VA `0x10023F23/0x10024097`。

错误字符串的唯一直接代码引用可定位到 `Dir.dll` VA `0x100247B8`：

```asm
100247B8  push 0x100ce60c       ; "[Dir][CDir::OnMessageRecvDirData] ERROR! Empty tree!"
100247BD  mov  eax,[ebp-0x10]
100247C0  add  eax,0xf1
100247C5  push eax
100247C6  call 0x10003a3f         ; 错误/日志输出
```

同一函数前面的成功处理路径在 `0x10024769--0x100247B6`：处理目录数据、构造/提交节点信息，然后清理并返回；`0x100247B8` 是上游返回失败时的错误日志路径。结合日志字符串 `SetDirMapInfo ... total Server Count is %d` 和 `GetAllGameDirInfo Error when call GetDirInfo`，`Empty tree!` 的含义是**解析后的树/可用服务集合为空或构建失败**。

### 判定

对本次地区-only响应，最稳妥的分层结论是：

- **网络层/帧层：成功收到并识别 DIRTREERSP。** 774 字节、magic、长度、ServiceID、`dir_root` 均有效。
- **业务树层：没有 CODOL 游戏服条目。** 结构里只有地区/测速节点；没有大厅 host/port，也没有可进入的游戏服应用数据。
- 因此客户端最终 `Empty tree!` 是**客户端解析/过滤后可用树为空的判定**；触发根因是服务端给了“地区目录但没有游戏服叶子”的内容，而不是服务端返回了物理空树。

这也解释了为什么 TCLSHost 仍可在 `WeGame\log\tcls\log\TCLSHost_2026-9-24-1790258892.log` 第 23--48 行打印 `result: true` 和 `SendServerDirToTgp result=1`：那是 ServerDir 交换/桥接成功，不等于目录树中存在 CODOL 大厅端点。

## 证据索引与限制

| 结论 | 主要证据 |
|---|---|
| 8001 是 QoS HTTP | `all_etw.jsonl:1424--1448`；`pktmon.txt:21410--23496`；重组请求 `Host: ied-tqos-tgp.qq.com:8001` 与 `QOSRep` |
| 80 是 WeGame 302 | `all_etw.jsonl:1370--1371`；`pktmon.txt:16256--17197`；`GET ...rail_hosts.js`、`Host: wegame.gtimg.com`、`HTTP/1.1 302 Found` |
| 443 的 SNI/证书 | pcap 唯一 ClientHello 包序 335，SNI `wegame.gtimg.com`；TLS Certificate 叶证书 SAN `*.gtimg.com, gtimg.com` |
| 没有第二跳 | `all_etw.jsonl:9478--10512`；第二响应 pcap 包序 46357；边界 46827 后目录 magic/774/出站 33 均为 0 |
| 响应地区-only | `CODOLServer\_tcls_blocks.txt:4--32`；`CODOLServer\_tcls_payload.txt:7--32`；响应偏移 `0x37` 的 `dir_root`、`0x180` 等测速 URL |
| Empty tree 是客户端判定 | `Dir.dll` 字符串偏移 `0xCE60C/0xCE65E`；代码引用 VA `0x100247B8`；`TCLSHost...1790258892.log:23--48` |
| cfg 算法边界 | `analysis_logs\TCLS_tas_ksa.txt:10--167`；`analysis_logs\TCLS_tas_cipher.txt:75--123`；`analysis_logs\TCLS_cipher_core.txt:59--135` |

### 关于后续其他流

第二条目录响应之后，pcap 仍可见大量其它连接，包括 PID 18076/辅助组件访问 `116.130.228.169:8080`，以及 `218.29.50.113`、`60.29.240.113` 等继续发生的流。它们不构成 TCLS 目录第二跳：

- `tcls_core` PID 19144 的 ETW 生命周期在 10509 收 774 后即关闭；
- 后续包序 136493 的 33 字节是 `116.130.228.169:8080 -> client` 的非 magic 服务器数据，不是客户端查询；
- pcap 是整机采集，不能用“全局出现 33 字节”代替“PID 19144 发出 DIRTREEREQ”。

结论因此限定为：**本次 TCLS 目录流程没有第二跳；不是宣称整机后续所有网络流都不存在。**
