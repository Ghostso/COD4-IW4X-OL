# TQoS QOSCSPkg + 大厅 HTTP 请求 —— 精简协议规格

日期：2026-09-25
输入（只读）：
- `run_codol_001\runs\EARLY_HANDLE_SCAN\hits.jsonl`（4000 条命中，1.6+ GB 二进制内存扫描结果）
- `CODOLServer\KEY_CONTEXT_20260925.txt`（TDR/schema 名称池转储）

方式：只做只读静态提取。未注入 Frida、未启动游戏、未改网络。
证据口径：`VA` = 命中记录里的虚拟地址（十六进制）；`offs` = `KEY_CONTEXT` 文件内字节偏移。

---

## 1. TQoS QOSCSPkg / QOSGetRes / GameSvrIPList / ConndIPPortList 字段顺序

### 1.1 包结构（三级嵌套，名称顺序即 TDR 声明顺序）

`KEY_CONTEXT` offs `10088`：
```
QOSCSPkg → QOSCSPkgHead + QOSCSPkgBody
QOSCSPkgHead = Magic . ruHeadLen . BodyLen . Cmd . ProtoVer . Seq
QOSCSPkgBody = QOSCSQosRep.QOSConndIPPortList.QOSGetRes.QOSRep
```

`QOSCSPkgHead` 字段（按名称池出现顺序，**顺序可信度 HIGH，位宽未证明**）：

```
Magic       魔数
ruHeadLen   头长
BodyLen     体长
Cmd         命令字
ProtoVer    协议版本
Seq         序列号
```

命令枚举（offs `9907`–`10059`，顺序即枚举顺序）：
```
QOS_SPDTST_REQ / QOS_SPDTST_RES / QOS_GET_REQ / QOS_GET_RES / QOS_REP
```

### 1.2 `QOSGetReq` / `QOSGetRes`

```
QOSGetReq  = BusinessID . CltID . ServerID . QosNum . QosList . ReqIP . ReqPort
QOSGetRes  = BusinessID . QosResFlag . SpdFlag . SpdData . Res . QosList
```

`QosResFlag` 位标志（offs `13883`，字面 `|` 分隔 ⇒ 位或组合）：
```
QOS_RESFLAG_SCORE | QOS_RESFLAG_QOSLIST | QOS_RESFLAG_GAMESVR_LIST | QOS_RESFLAG_CONNDIP_LIST
```

`SpdFlag` 取值（offs `14032` 段落内 `, 0 ... 1 ...`）：`0` = 无 SpdData，`1` = 带 `SpdData`。

`SpdData` =
```
QosID( = ID ) . QosVal . DurationTime
```

### 1.3 ★ `QosCSGameSvrList` / `QOSConndIPPortList`（提问重点）

`KEY_CONTEXT` offs `11411` 原文（已去控制字节）：

```
gamesvr ... 0.0.0.0 . GameSvrNum ... GameSvr ... GameSvrIPList . ConndIP . ConndPort . Score
... QosNum ... GroupID ... QosResFlag ... QosList . ConndIPPortNum ... ConndIPPortList
... GameSvrList ... BusinessID ... CltID ... ServerID ... QosNum ... QosList . Flag . ip
```

⇒ **字段顺序（HIGH，来自 TDR 名称池连续输出）**：

| 层 | 字段序列 |
|---|---|
| `QosCSGameSvrList` | `GameSvrNum` → `GameSvr[]` |
| `GameSvr` (每项) | `GameSvrIPList` → `ConndIP` → `ConndPort` → `Score` |
| `QOSConndIPPortList` | `ConndIPPortNum` → `ConndIPPortList[]` |
| `QOSConndIPPortList` 末 | `GameSvrList` |

**每项字段宽度：UNKNOWN。** 名称池只给字段名和顺序，**不含类型/位宽**（`.tdr` 描述表里也未命中 `DIRTREE`/`QOS` 定义）。

**旁证（同族姊妹协议 QOSSS，offs `34198`）** —— 同构命名给出更明确的「IP/端口成对」证据：
```
QOSSSGetReq = BusinessID . ReqIP(=ip) . ReqPort . QosConnd . ProtoVer . Seq . QosResFlag
QOSSSGetRes = BusinessID . ReqIP(=ip) . ReqPort . Score . ProtoVer . Seq . QosResFlag . QosNum . QosList
```
注意 `QOSSSGetRes` 里 **`Score` 是单值、`ReqIP`/`ReqPort` 是标量**，而 `QOSConndIPPortList` 是**列表** ⇒
列表项 `{ConndIPPort, Score}` 与 `GameSvr{GameSvrIPList, ConndIP, ConndPort, Score}` 是两套不同结构，**不要混用同一模板**。

### 1.4 常量名（容量上限，offs `13933`）

```
QOS_CS_MAGIC / QOS_CS_MAX_QOSLIST / QOS_CS_MAX_GAMESVR / QOS_CS_MAX_CONNDIP
TQOS_CS_STRING_LEN / QOS_CS_MAX_REP / QOS_MAX_RTT / QOS_MAX_STDDEV
```
⇒ **容量上限确实存在**（`MAX_GAMESVR` / `MAX_CONNDIP` / `MAX_QOSLIST`），但**具体数值未在本输入中出现**。

### 1.5 时间结构（offs `10310` 段）

```
QOSCSTime = tv_sec . tv_usec . CSendTime . SRecvTime . SSendTime
QOSSpdTstReq/QOSSpdTstRes = Rtt . StdDev . LostRate
```
旁证：字符串常量 `"Rtt......ms"`、`"StdDev.........Rtt..............ms"`、`"LostRate"` ——
**这些 `%s`/格式串紧跟在字段名之后**，是「字段后接格式化标签」的写法，可作为字段边界旁证（MEDIUM）。

### 1.6 地址协议（关键）

`KEY_CONTEXT` offs `30863`（同段出现 4 次）：
```
udp://%s:%d
```
紧邻错误串（offs `30911`）：
```
tqos_find_connd_by_ip fail / tqos_get_qosconnd_iplist fail / tqos_create_protohandle err / calloc err
```
⇒ **TQoS 的 QoS 连接探测用 `udp://host:port`**，且 `ConndIP/ConndPort` 就是喂给这个 `%s:%d` 的取值
（`tqos_get_qosconnd_iplist` 直接对应 `ConndIPPortList`）。**强度 HIGH。**

---

## 2. 大厅 / HTTP 请求的真实 URL、端口、必需头

### 2.1 大厅 HTTP 请求头（本地硬编码格式串）

`KEY_CONTEXT` offs `1547`–`1710`（同串在 offs `8071` 重复一次，属两个不同模块）：
```
CODOL/1.0
X-TransactionID: %I64u
Content-Type: text/plain
Content-Length: %u
title_id: %u
tencent_ticket: %s
Expect:
```
VA（hits.jsonl）：请求头区 `VA 0x00DC9D04`（`title_id`）、`VA 0x00DC9D14`（`tencent_ticket`）、
`VA 0x00DC9CE5`（`CODOL/1.0` / `X-TransactionID`）、同族第 2 份 `VA 0x00DC6616`。

⇒ **必需头（4 个，HIGH）**：
| 头 | 值 | 证据 |
|---|---|---|
| `User-Agent` | `CODOL/1.0`（无 `User-Agent:` 前缀，紧跟在 `PEM.cacert.pem` 之后 ⇒ 推断为 UA 字面量，MEDIUM） | offs `1547` |
| `X-TransactionID` | `%I64u` | offs `1559` |
| `Content-Type` | `text/plain` | offs `1577` |
| `title_id` | `%u` | offs `1631` |
| `tencent_ticket` | `%s` | offs `1647` |

### 2.2 ★ 大厅连接 URL 模板（本次最有价值的发现）

hits.jsonl `VA 0x00D5A0EC` / `VA 0x00D5A100`（`hits.jsonl` 第 67/68 行）：
```
%s://%s:%d/%s/title/%d/queue/%d/member/%llu
https
v1.0
```
紧邻字段名：`lsg_server_ticket`、`lsg_server_ticket_size`、`iv_seed`。

⇒ **大厅 URL = `<scheme>://<host>:<port>/<path>/title/<title_id>/queue/<queue>/member/<uid>`**

* `%s(1)` = scheme，紧邻常量 `https` ⇒ 实际取 **`https`**（HIGH）
* `%s(2)` = host，`%d` = port —— **具体主机名/端口不在本次输入中（UNKNOWN）**
* `%s(3)` = 路径段（同族另一模板用 `/auth/`，见 2.3）
* `title_id`、`queue`、`member` 为数值

### 2.3 认证 URL 模板

hits.jsonl `VA 0x00D5A2CC`（`hits.jsonl` 第 483 行）：
```
... response_id . user_id . time_to_live . cd_key ...
https://%s:%d/auth/.ciphertext
```
⇒ **`https://<host>:<port>/auth/`**，POST 体为 `.ciphertext`；
该串紧邻 `server_ticket` / `client_ticket` / 常量 `356c4bc3`（`VA 0x00D5A31C`，疑似 IV 或 magic）。

同区另有 `VA 0x00D5A228`：`v.auth_task` + 常量
`43FCB2ACF2D72593DD7CD1C69E0F03C07229F4C83166F7B05BA0C5FE3AA3A2D93EK2`（64 hex + `K2` 尾，疑似 AES-256 key 或 ticket 前置常量）。
**该串用途未证明，仅记录位置。**

### 2.4 未发现

* `dwlobbyhost` / `blazehost` / `lobbyhost` / `demonware` 主机名 → **零命中**（`demonware` 只有 `stun.*.demonware.net` 4 条）
* 任何 `IP:port` 组合（除 `239.255.255.250:1900` SSDP）
* 端口数字常量（`hits.jsonl` 的 `port` 关键字 856 条全是 libcurl/OpenSSL 文本，`PORTS` 提取为空）

⇒ **大厅/认证主机与端口都由运行时下发，静态二进制里不落盘。强度 HIGH。**

---

## 3. 可作为本地重定向目标的域名与最可能端口

### 3.1 A 类：业务域名（有明确协议语义，**优先**）

| 域名 | 证据 | 推断端口 | 强度 |
|---|---|---|---|
| `ied-tqos.qq.com` | `hits.jsonl VA 0x00DD98A5`（`hits` 只 2 条），前文为 `\d3drg8x.dll` + 版本模板 `%d.%d%c.%d*%d` ⇒ 在**渲染/D3D 探测上下文附近** | **8000/UDP** | MEDIUM（端口来自既有运行时观测，非本输入） |
| `tqos.gamesafe.qq.com` | `hits.jsonl VA 0x14E05B61`，周围为紧凑二进制表 | **8080 / 8081** | MEDIUM |
| `exp.tcls.qq.com` | `hits.jsonl VA 0x146C5084`（protect=2），串为 UTF-16 展开 `e.x.p...t.c.l.s...q.q...c.o.m`，紧跟 `c.:.\.j.e.n.k.i.n.s...` 构建路径 | **10009 / 8080** | MEDIUM |
| `dump.gamesafe.qq.com` | `hits.jsonl VA 0x11EE2B86`（`hits` 2 条） | 80 / 443 | LOW |
| `down.safe.wegamex.com` / `.com.hk` | `hits.jsonl VA 0x146C5084` 同区 `https://down.safe.wegamex.com.hk` | **443** | MEDIUM |
| `intldlgs` | 同区紧邻 `down.safe.wegamex.com`，疑似 `intldlgs.qq.com` 截断 | 443 | LOW |
| `cod4master.activision.com` | `KEY_CONTEXT` offs `73173`，夹在 dvar 编号 `1859` / `1860` 之间 ⇒ **是 dvar 的默认值** | **20810/UDP**（COD4 经典 master 端口） | LOW（端口非本输入证据） |

### 3.2 B 类：CDN / 下载域（与大厅无关，**不要重定向**）

`down.qq.com`、`dlied1/5.qq.com`、`dlied5v6.qq.com`、`update1.dlied.qq.com`、`wgdl.qq.com`、
`dldir1/2/3.qq.com`、`dd.qq.com`、`dir3.qq.com`、`d5.qq.com`、`date.qq.com`、`rom.qq.com`、
`function.qq.com`、`dl.tcdntip.com`、`dlied1.cdntips.net`、`dd.cdntips.net`、`ied1.cdntips.net`、
`*.dlied1.cdntips.net`、`dl.txcdns.com`、`down-update.qq.com`、`down.qq.com.tcdn.qq.com`

（均为 libcurl/SSL 证书或更新器字符串，`hits.jsonl` 中成簇出现，属下载栈）

### 3.3 C 类：纯 STUN（NAT 探测，与大厅无关）

`stun.au.demonware.net` / `stun.jp.demonware.net` / `stun.eu.demonware.net`（`hits.jsonl VA 0x00D5A0xx` 区外的 `VA 1400xxxx` 段，protect=128）
`stun.us.demonware.net`（`hits.jsonl VA 0x00DC6618`，紧跟常量 `1109` 与 `127.0.0.1`）→ **3478/UDP**

### 3.4 D 类：低价值 / 无地址

`kf.qq.com`（客服 FAQ 链接）、`www.w3.org` / `adobe.com` / `schemas.xmlsoap.org`（XML 命名空间）、
`goo.gl` / `log.getdropbox.com` / `redirector.gvt1.com` / `www.googleapis.com`（Chromium/CEF 内置，**非游戏流量**）

---

## 4. 结论强度汇总

| 结论 | 强度 | 依据 |
|---|---|---|
| `QOSCSPkgHead` 字段顺序 | HIGH | TDR 名称池连续输出 |
| `QosCSGameSvrList`/`QOSConndIPPortList` 字段顺序 | HIGH | 同上 |
| 各字段位宽 / 类型 | **UNKNOWN** | 名称池不含类型；`.tdr` 未命中 |
| TQoS 走 `udp://%s:%d` | HIGH | 格式串 + `tqos_get_qosconnd_iplist` 同段 |
| 大厅 URL 模板 `%s://%s:%d/%s/title/%d/queue/%d/member/%llu` | HIGH | VA `0x00D5A0EC` 唯一命中 |
| 该模板 scheme = `https` | HIGH | 紧邻常量 `https` |
| 大厅 host / port | **UNKNOWN** | 全输入零命中 |
| 认证 URL `https://%s:%d/auth/` | HIGH | VA `0x00D5A2CC` |
| 必需请求头 5 项 | HIGH | offs `1547`–`1710` 连续串 |
| `ied-tqos.qq.com` 等重定向候选端口 | MEDIUM/LOW | 端口非本输入证据，标注来源 |

---

## 5. 本输入中仍缺、必须另找的东西

1. **`QOS_CS_MAGIC` 的 4 字节值**（本输入只给名称，未给字面量）
2. **`QOS_CS_MAX_*` / `TQOS_CS_STRING_LEN` 的具体数值**
3. **大厅 host + port** —— 需在 `TQMCenter.exe` / `IIPSHostApp.exe` 运行时或下发报文里取
4. **字段位宽** —— 需 `TQoS` 的实现体（不在本次两个输入中）或抓一份真实 `QOS_GET_RES` 报文
5. `356c4bc3` / `43FC B2AC…` 两个常量的用途

---

## 6. 附：证据定位速查

| 内容 | 位置 |
|---|---|
| `QOSCSPkgHead` / `QOSCSPkgBody` | `KEY_CONTEXT` offs `10088` |
| `GameSvrIPList` | `KEY_CONTEXT` offs `9771`；`hits.jsonl VA 0x00E493D3` |
| `ConndIPPortList` | `KEY_CONTEXT` offs `10277`；`hits.jsonl VA 0x00E48F65` / `0x00E49494` |
| `gamesvr` / `qosconnd` | `KEY_CONTEXT` offs `11411`；`hits.jsonl VA 0x00E49390` / `0x00E494DF` |
| `QOS_CS_MAGIC` 等常量名 | `KEY_CONTEXT` offs `13933` |
| `udp://%s:%d` + `tqos_*` 错误串 | `KEY_CONTEXT` offs `30863` / `30911` |
| `QOSSS` 姊妹协议 | `KEY_CONTEXT` offs `34198` |
| 大厅 HTTP 头 | `KEY_CONTEXT` offs `1547`；`hits.jsonl VA 0x00DC9CE5`/`0x00DC9D04`/`0x00DC9D14` |
| 大厅 URL 模板 | `hits.jsonl VA 0x00D5A0EC` / `0x00D5A100` |
| `/auth/` + `server_ticket` | `hits.jsonl VA 0x00D5A2CC` / `0x00D5A31C` |
| `auth_task` + 64-hex 常量 | `hits.jsonl VA 0x00D5A228` |
| `ied-tqos.qq.com` | `hits.jsonl VA 0x00DD98A5` |
| `tqos.gamesafe.qq.com` | `hits.jsonl VA 0x14E05B61` |
| `exp.tcls.qq.com` | `hits.jsonl VA 0x146C5084` |
| `dump.gamesafe.qq.com` | `hits.jsonl VA 0x11EE2B86` |
| `cod4master.activision.com` | `KEY_CONTEXT` offs `73173` |
| `stun.us.demonware.net` | `hits.jsonl VA 0x00DC6618` |
