# CODOL 本地服务器配置扫描报告

扫描时间：2026-09-24
范围：`COD OL`、`run_codol_001\sandbox_ifs1_20260923`、`WeGame`、`工具\EX035_DIR`
方式：只读文件扫描、配置解析、历史日志检索；未修改文件，未启动客户端。

## 结论

当前本地明文配置中，**没有发现可直接确认为 CODOL 对战/游戏服务器的 IP:端口组合**。

发现的地址主要属于以下服务：

1. TCLS 目录服务：负责 ServerDir / 选区目录，不等于对战服。
2. TCLS 版本服务器：负责版本检查和更新，不等于对战服。
3. STUN：负责 NAT/连通性探测，不等于对战服。
4. IIPS 策略服务器：负责资源/策略通道，不等于对战服。
5. Cross LiveUpdate：负责跨产品更新，不等于 CODOL 对战服。
6. 游戏服候选：只在 `ServerDir` 返回、匹配/大厅运行时或真实载荷中继续寻找，目前未在明文配置中落地。

## 关键业务上下文

历史 TCLS 日志确认 CODOL 已登记，但只返回了目录上下文：

```text
gameID       = 29
version      = 3.19.26.22
BranchID     = 1
CrossSvrID   = 2102017
ServiceID    = 715019302
server_id    = 0
ServerDir    = result=true
SendServerDirToTgp = result=1
```

证据：`WeGame\log\tcls\log\TCLSHost_2026-9-24-1790221027.log`。

这说明 ServerDir 阶段成功，但该日志没有给出 CODOL 对战服务器的实际 IP、端口或房间地址。

## 配置分类

### 1. TCLS 目录服务

文件：`COD OL\TCLS\config\dirserver.xml`

```text
tcls.qq.com
123.151.176.103
119.84.150.46
183.61.224.121
101.91.63.192

ports: 8080, 5223, 10009
selected: server_id=1, port=8080
dynamic selected port: COD OL\TCLS\config\dirserverdynamic.ini -> 10009
```

判定：`TCLS_DIR_SERVER`。

理由：XML 注释明确写的是 `dir server`，TCLS 日志也把调用命名为 `ServerDir::FetchWithUin()`。这是选区/服务目录入口，不是已确认的游戏对战服。

### 2. TCLS 版本服务器

文件：`COD OL\TCLS\config\VersionServerConfig.xml`

```text
tcls.rail.qq.com
223.167.104.26
220.249.243.189
183.194.234.198
183.192.199.25
180.163.25.22
14.215.138.14
123.151.72.67
123.126.122.65
120.241.190.12
116.128.163.239
111.13.34.177
101.89.38.73

ports: 8001, 9001, 10001, 8002, 9002, 10002
dynamic selected: server_id=10, port=8002
```

判定：`TCLS_VERSION_UPDATE`。

理由：文件名和 `<versionserver>` 节明确表明这是版本服务；不能当作对战服地址。

### 3. WeGame agent 版本服务

文件：`WeGame\apps\agent\TCLS\config\VersionServerConfig.xml`

```text
tcls.rail.qq.com
101.91.5.199
183.195.236.84
140.206.164.64

ports: 8001, 9001, 10001, 8002, 9002, 10002
```

判定：`WEGAME_AGENT_VERSION_UPDATE`。

文件：`WeGame\apps\agent\TCLS\config\dirserver.xml`

```text
DirServer count=0
```

这表明 agent 副本当前没有独立的明文目录节点列表。

### 4. STUN 候选

文件：`COD OL\stun.ini`

```text
stun1-tub.codol.qq.com
stun2-tub.codol.qq.com
stun3-tub.codol.qq.com
```

判定：`STUN_NAT_DISCOVERY`。

这是最接近游戏业务的配置之一，但 STUN 只用于 NAT/连通性探测，不能直接当作大厅或对战服。

### 5. IIPS 策略服务器

文件：`COD OL\IIPS\IIPSHostApp.ini`

```text
Address=udp://ctrl.iips.qq.com:8000
HeartbeatInterval=60
BusinessID=3058
```

判定：`IIPS_POLICY_CHANNEL`。

历史启动抓包中 `:8081` 的 UDP 流量对应 `tqos.gamesafe.qq.com` QOS/质量上报候选；这两个通道都不是已确认的 CODOL 对战协议。

### 6. Cross 更新服务

文件：`COD OL\Cross\LiveUpdate\liveupdateinfo.ini`

```text
addr=http://cross.qq.com
peerudpurl=pdldir0.qq.com
peerudpport=8000
peertcpurl=pdldir0.qq.com
peertcpport=443
stunip=stun.qq.com
stunport=8000
netudpurl=xuanfengnet.qq.com
netudp=8000
nettcpurl=xuanfengnet.qq.com
nettcp=80
onlineserver=fs_hello.qq.com
onlineserverudpport=8000
onlineservertcpport=443
url2hashurl=fs_conn.qq.com
url2hashport=443
hash2urlurl=fs_h2u.qq.com
hash2urlport=443
stateserverurl=fs_report.qq.com
stateserverport=443
```

判定：`CROSS_LIVEUPDATE`。

这些地址属于 Cross/JStar 更新和状态上报配置，不能当作 CODOL 对战服。

### 7. Cross 更新参数中的“在线服务器”字段

文件：`COD OL\Cross\LiveUpdate\liveupdateinfo.ini`

```text
onlineserver=fs_hello.qq.com
onlineserverudpport=8000
onlineservertcpport=443
stateserverurl=fs_report.qq.com
stateserverport=443
```

判定：`CROSS_LIVEUPDATE_ONLINE_STATE`。

虽然字段名含有 `onlineserver`，但它位于 `CrossLiveUpdate` 的 `[XFParam]`，并且与 `fs_conn.qq.com`、`fs_h2u.qq.com`、`fs_report.qq.com` 同组，语义是 Cross/JStar 更新在线状态和文件服务，不是 CODOL 对战服务器。

## 配置文件完整性

扫描时记录的关键文件哈希见：

```text
COD OL\TCLS\config\dirserver.xml
COD OL\TCLS\config\VersionServerConfig.xml
COD OL\stun.ini
COD OL\IIPS\IIPSHostApp.ini
COD OL\TCLS\mmog_data.xml
COD OL\GameBabyConfig.dat
```

本轮没有修改这些文件。`WeGame\TCLS\TCLSCoreConfig.ini` 仍保持原始长度 992、原始 SHA256 `93ABC97354CBD0DD95A913F12FB21675194A4CF3DD7B153616DCDEC08CD25996`。

## 明确排除的文件

### `GameBabyConfig.dat`

这是 XML 文本，内容是安全/性能检查配置：

```text
GameName=codoMP_client_shipRetail.exe
EnableTGOC=0
IgnoreDlls=TenSLX.dll, TerSafe.dll, codoMP_client_shipRetailbase.dll
```

没有服务器地址。

### `mmog_data.xml`

CODOL 版本文件只含：

```text
Version=3.19.26.22
Uin=0
WorldID=0.0.0.0
```

没有游戏服务器地址。

### `Game.dat`、`commonconfig.cfg`、`updateconfig.cfg`、`config_mp.cfg`

这些文件均为二进制/加密或高熵内容。按 ASCII/UTF-16 可打印字符串提取，没有得到可信的对战服 URL、主机名或 IP:端口。当前不把乱码、随机字节或十六进制子串解释成配置。

## 与运行时记录的交叉验证

已有 AFD 运行时记录显示：

```text
UDP sendto -> 122.96.96.225:8081
DNS         -> tqos.gamesafe.qq.com
TCP         -> 61.182.140.173:80/443
TCP         -> 218.69.49.90:443
```

这些连接与本地配置的 QOS、更新、CEF/HTTP(S) 形态一致；采集没有提供载荷，也没有提供能把某个连接标成“对战服务器”的调用栈。

## 当前真正缺口

要找到游戏服务器，需要继续追踪以下任一证据：

1. ServerDir 成功之后的 LaunchGame / 登录会话上下文是否包含游戏服地址。
2. 匹配对象 `MatchMaking_FIND_SERVERS_Query` 的运行时实例和返回内容。
3. `dwRoomMessage*` / `P2PInfo` 相关对象的真实 def-use。
4. 游戏进程进入大厅/匹配后的载荷型抓包，而不是当前只有长度的 AFD ETW。
5. 可能存在于 `.tvm0`、Tenio/TNSDK 或运行时解密配置中的服务器字段。

## 结论等级

```text
明文配置发现：        HIGH
目录/版本/IIPS分类：   HIGH
STUN候选分类：         HIGH
对战服务器地址：       NOT_FOUND
对战协议端口：         UNKNOWN
对战载荷格式：         UNKNOWN
```

本报告没有把目录服务器、版本服务器、IIPS、QOS 或 STUN 地址冒充为游戏服务器。
