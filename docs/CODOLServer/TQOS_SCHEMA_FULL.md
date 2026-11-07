# TQoS / QoS 协议完整 Schema（静态提取，来自 exe 内嵌字段名表）

日期：2026-09-25
来源：`COD OL\codoMP_client_shipRetail.exe` 内嵌的 TDR 风格字段名表
换算：**VA = 文件偏移 + 0x714000**

---

## 1. 两套包结构（客户端 / 服务端）

```
客户端： QOSCSPkg        = QOSCSPkgHead + QOSCSPkgBody
         QOSCSPkgHead / QOSCSPkgBody
服务端： QOSSSPkg        = QOSSSPkgHead + QOSSSPkgBody
         QOSSSPkgHead / QOSSSPkgBody
```

### 1.1 客户端侧常量（VA 0x00E48C80 起）

```
QOS_CS_MAGIC
QOS_CS_MAX_QOSLIST
QOS_CS_MAX_GAMESVR
QOS_CS_MAX_CONNDIP
QOS_CS_STRING_LEN
QOS_CS_MAX_REP
QOS_CS_ADINFO_STR_LEN
QOS_CS_ADINFO_BLOB_LEN
QOS_CS_ADINFO_MAX_INT
QOS_CS_ADINFO_MAX_STR
QOS_MAX_RTT
QOS_MAX_STDDEV
```

### 1.2 结果标志位（VA 0x00E48D5C 起）

```
QOS_RESFLAG_SCORE
QOS_RESFLAG_QOSLIST
QOS_RESFLAG_GAMESVR_LIST
QOS_RESFLAG_CONNDIP_LIST
```
⇒ 我们的 variant-3 应答用的 `flag = 0xF`（四个位全置）**在语义上是对的**。

### 1.3 客户端消息/结构

```
QOS_APPEND_DESC_NO / QOS_APPEND_DESC_QQGAME / QOS_APPEND_DESC_COMM
QOS_SPDTST_REQ / QOS_SPDTST_RES        ← 测速请求/应答
QOS_GET_REQ   / QOS_GET_RES            ← 获取请求/应答  (cmd 3 / cmd 4)
QOS_REP
QOSCSPkgHead / QOSCSTime
QOSSpdTstReq / QOSSpdTstRes / QOSSpdData
QOSGetReq / QOSCSQos / QOSAppendDesc*
QOSCSQosRep / QOSConndIPPortList        ← 【关键】连接地址端口列表
QOSGetRes / QOSRep / QOSCSPkgBody / QOSCSPkg
```

### 1.4 服务端侧常量（VA 0x00E43DE0 起）

```
QOS_SS_MAGIC
QOS_SS_MAX_QOSLIST
TQOS_SS_STRING_LEN
QOS_SS_MAX_REP
QOS_SS_ADINFO_STR_LEN / QOS_SS_ADINFO_BLOB_LEN / QOS_SS_ADINFO_MAX_INT / QOS_SS_ADINFO_MAX_STR
QOS_SS_MAX_BUF_LEN
QOS_SS_APPEND_DESC_NO / _QQGAME / _COMM
QOS_SS_GET_REQ / QOS_SS_GET_RES / QOS_SS_REP
QOSSSPkgHead / QOSSSQos
QOSSSAppendDescNo/QQGame/Comm / QOSSSAppendDesc
QOSSSQosRep / QOSSSRep / QOSSSGetReq / QOSSSGetRes / QOSSSPkgBody / QOSSSPkg
```

### 1.5 相关函数名

```
tqos_create_protohandle
tqos_find_connd_by_ip
tqos_get_qosconnd_iplist
QOS_TRANSACTION_ID
STUNServerPing / STUNServerPingResult
```

---

## 2. 已知的线上字节（实测，来自实验 A）

### 2.1 客户端请求（QOS_GET_REQ，cmd=3，24 字节）

```
75 72 00 10 00 08 00 03 00 00 00 0b <seq:u32> <BusinessID:u32=100> 00 18 00 00
'u' 'r'|ruHeadLen=16|BodyLen=8|Cmd=3|ProtoVer=0|Reserved=0x0B|Seq|BusinessID|24|0
```
- `0x18=24` = 整包字节长度（16+8），**不是列表数**

### 2.2 我们的应答（variant 3，268 字节）

```
75 72 00 10 00 fc 00 04 00 00 00 00 <seq> <BusinessID=100> 00 0f
00 00 00 18|<24 x (127.0.0.1, 8000, score=0)>   (猜测布局)
```

---

## 3. 对 `[100]` 深层原因的意义

完整链路推测（基于本 schema）：

```
STUNServerPing                              ← STUN 探测
   ↓
tqos_create_protohandle / tqos_get_qosconnd_iplist
   ↓
客户端发 QOSCSPkg{ QOSGetReq(QOS_GET_REQ, BusinessID=100) }   → UDP 8000
   ↓
服务端应 QOSSSPkg{ QOSSSGetRes(含 QOSCSQosRep / QOSConndIPPortList) }
   ↓
游戏从中取 ConndIPPortList → 作为大厅/战斗服连接目标
   ↓
若取不到可用端点（或包不合法）→ dwLobby 拿不到地址 → 画 [100] 无法连接大厅服务
```

**⇒ 深层原因（候选，待验证）**：
`[100]` 不是"连不上某台服务器"，而是 **"服务器发现（TQoS/STUN）没有给出可用端点"** ——
即大厅地址的下发通道失效，dwLobby 自然连不上。

**实验 A 的不利证据需要解释**：
我们把 `ied-tqos.qq.com` 改写到本地并应答（客户端接受、不重传），`[100]` 仍出现。
可能原因：
1. 应答的**包体布局**与 `QOSSSPkg` 真实结构不符（`QOS_SS_MAGIC` / `QOS_SS_MAX_*` 等未按格式给）
2. 客户端还需要 **STUN** 成功（`STUNServerPing`），单独答 TQoS 不够
3. 大厅地址**另有下发通道**（GDP/其他 HTTP），TQoS 只是质量探测

---

## 4. 产物

```
CODOLServer\_mainline\_qos_schema.py     字段名全表
CODOLServer\_mainline\_stun_cfg.py       STUN 配置项
CODOLServer\_mainline\_dw_cmds.py        dw_* 命令/dvar 全表
CODOLServer\EXPERIMENT_A_RESULT.md      实验 A 结果
```
