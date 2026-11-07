# QOS_GET_RES 字节模板 —— 可生成规格

日期：2026-09-25
输入（只读）：`CODOLServer\SUBAGENT_PROTOCOL_SPEC.md`、`CODOLServer\KEY_CONTEXT_20260925.txt`、
`run_codol_001\runs\EARLY_HANDLE_SCAN\hits.jsonl`、`run_codol_001\runs\SINGLE_V0B\local_listeners.jsonl`
（另只读参考 `run_codol_001\runs\SINGLE_V0B\host_redirect.log`、`redirect_targets.json`）

方式：只读静态 + 已有抓包字节分析。未注入、未启动游戏、未改网络。

---

## 0. 关键反推（本次新增，强度 HIGH）

`local_listeners.jsonl` 给了**真实请求与已被接受的应答**，这是唯一的一手字节对：

```
REQ   7572 0010 0008 0003 0000 000b 00007da1 00000064 0018 0000     (24 B)
REPLY 7572 0010 0008 0004 0000 0000 00007da1 00000064 0000 0000     (24 B)
```

逐 u16be 拆解（偏移 = 字节位置）：

| 偏移 | REQ | REPLY | 字段 | 说明 |
|---|---|---|---|---|
| 0 | `7572` | `7572` | `Magic` = ASCII **`ur`** | 2 B，固定 |
| 2 | `0010` | `0010` | `ruHeadLen` = **16** | 2 B，固定（≠ 总长 24） |
| 4 | `0008` | `0008` | `BodyLen` = **8** | 2 B。`16 + 8 = 24` = 总长 ✔ |
| 6 | `0003` | `0004` | `Cmd` = 3(req) / 4(res) | 2 B |
| 8 | `0000` | `0000` | `ProtoVer` = **0** | 2 B |
| 10 | `000b` | `0000` | 未命名 u16（保持可变） | 2 B |
| 12 | `00007da1` | `00007da1` | `Seq` | 4 B，**回显** |
| 16 | `00000064` | `00000064` | `BusinessID` = **100** | 4 B，**回显** |
| 20 | `0018` | `0000` | **请求的 `Len`（=24）** | 2 B |
| 22 | `0000` | `0000` | 未命名 u16 | 2 B |

⇒ **`0x18 = 24` 不是「24 项」，而是「请求体长度 = 24 字节」这一个 u16 值。**
`ruHeadLen(16) + BodyLen(8) = 24`，与 `0x18` 完全吻合。**强度 HIGH**（三处独立自洽）。

⇒ **应答必须保持 `ruHeadLen=16` / `BodyLen=8` / 总长 24**，否则长度自洽性被破坏。
你已有的 24 字节应答被客户端接受（停止重传）证实了这一点。

### 0.1 为什么这个应答无法推进

`QOSCSPkgHead`（`KEY_CONTEXT` offs `10088`）的字段名池是：
`Magic . ruHeadLen . BodyLen . Cmd . ProtoVer . Seq` —— **只有 6 个字段**。
而 24 字节帧里除了这 6 个，还有 4 个未命名 u16/u32（偏移 10/16/20/22）。
其中偏移 16 的 `BusinessID` 由 `QOSSSGetReq = BusinessID . ReqIP . ReqPort . ...` 佐证。

⇒ 该 24 字节帧是 **`QOSCSPkg` 的最小子集（无 `QOSCSPkgBody`）**，
即你的应答**只完成了「长度/序号握手」，没有携带任何 `QOSGetRes` / `QosCSGameSvrList` / `QOSConndIPPortList` 内容**。
客户端停止重传是因为**握手被接受**，而不是因为拿到了服务器列表。**强度 HIGH。**

---

## 1. `QOSGetRes` / `QosCSGameSvrList` / `QOSConndIPPortList` 位宽判定

### 1.1 已确定（HIGH）

| 字段 | 位宽 | 证据 |
|---|---|---|
| `Magic` | 2 B ASCII `ur` | 实帧 |
| `ruHeadLen` | u16be = 16 | 实帧 |
| `BodyLen` | u16be = 8 | 实帧，与 `0x18` 自洽 |
| `Cmd` | u16be | 实帧（req 3 / res 4） |
| `ProtoVer` | u16be = 0 | 实帧 |
| `Seq` | **u32be** | 实帧偏移 12 |
| `BusinessID` | **u32be** = 100 | 实帧偏移 16 + `QOSSSGetReq` 字段序 |
| 请求 `Len` | u16be = 24 | 实帧偏移 20，三处自洽 |

### 1.2 仍未确定（UNKNOWN）—— 必须显式声明

名称池只给字段名，**不给类型**。以下全部 UNKNOWN：

* `GameSvrNum` / `ConndIPPortNum` / `QosNum` —— 计数是 u8 / u16 / u32？
* `GameSvrIPList` —— 是 `u32 个数 + u32[]`，还是 `u16 个数 + 字符串表`？
* `ConndIP` —— u32be IPv4？字符串？独立 `IP` 结构（见下）？
* `ConndPort` —— u16？u32？
* `Score` —— u16？u32？float？
* `QosResFlag` —— u16？u32？
* `SpdFlag` —— u8？u16（旁证 `, 0 ... 1 ...` 是 u16 形态，MEDIUM）？

### 1.3 可用的间接约束（MEDIUM）

`KEY_CONTEXT` offs `30863` 段落里，`QOSSS` 的 IP 字段独立成一个结构（注意其内部子字段序）：
```
GrpN . IP . IntNum . IntList . StrNum . StrList . Resvlen . Resv . Bloblen . Blob . Uin . Time
```
⇒ **`IP` 不是裸 u32，而是一个带 `IntNum/IntList`+`StrNum/StrList` 双分支的复合结构**
（整数形式 or 字符串形式二选一）。`ConndIP` 很可能复用同一结构。
**这直接否定了「`ConndIP` 是裸 u32be」这个最省事的假设。** 强度 MEDIUM（同族协议推断，未在 QOS_CS 侧直接证实）。

同段落还有 `Res.StatType . StatID . Reserved1 . Reserved2` ⇒ `Res` 是含保留字段的子结构。

---

## 2. `build_qos_get_res()` —— 三个候选模板

三种候选**并列**，按证据强度排序。**不要只用一个。** 全部保持 `ruHeadLen=16` / `BodyLen=8` / 总长 24 的握手骨架
（该骨架已被实测接受），因此**先让握手继续成立，再逐步替换尾部**是推荐策略。

### 候选 A（强度最高：保持 24 字节骨架，只在尾部写入 IP/端口）

**依据**：24 字节帧已被接受；`Cmd=4` 表示响应；尾部偏移 20/22 在请求里是 `0018 0000`。
把偏移 20..23 改成 `IP:port` 的紧凑编码（`127.0.0.1:8000` → `7f000001` + `1f40`）。

```python
def build_qos_get_res_A(req, ip='127.0.0.1', port=8000):
    import struct, socket
    seq  = struct.unpack_from('>I', req, 12)[0]
    biz  = struct.unpack_from('>I', req, 16)[0]
    ipn  = struct.unpack('>I', socket.inet_aton(ip))[0]
    out  = bytearray()
    out += b'ur'                      # 0  Magic
    out += struct.pack('>H', 16)      # 2  ruHeadLen
    out += struct.pack('>H', 8)       # 4  BodyLen  (16+8=24)
    out += struct.pack('>H', 4)       # 6  Cmd = RES
    out += struct.pack('>H', 0)       # 8  ProtoVer
    out += struct.pack('>H', 0)       # 10
    out += struct.pack('>I', seq)     # 12 Seq   (echo)
    out += struct.pack('>I', biz)     # 16 BusinessID (echo)
    out += struct.pack('>H', ipn >> 16)   # 20 IP high16
    out += struct.pack('>H', (ipn & 0xFFFF))  # 22 IP low16
    assert len(out) == 24
    return bytes(out)
```

> 注：此模板**把 port 塞不进去**（24 B 已满）。如果必须带端口，用候选 B。

### 候选 B（强度中：扩展到 32 B，尾部追加 IP+port）

**依据**：`BodyLen` 可随实际体长变化（它不是常数，只是本次恰好 8）。
保留前 24 B 语义，追加 8 B：`u32be IP + u16be Port + u16be 0`，并把 `BodyLen` 改成 `8+8=16`。

```python
def build_qos_get_res_B(req, ip='127.0.0.1', port=8000):
    import struct, socket
    seq = struct.unpack_from('>I', req, 12)[0]
    biz = struct.unpack_from('>I', req, 16)[0]
    ipn = struct.unpack('>I', socket.inet_aton(ip))[0]
    body = bytearray()
    body += struct.pack('>I', ipn)            # 8 B 起：IP
    body += struct.pack('>H', port)           # 12 B：Port
    body += struct.pack('>H', 0)              # 14 B：Reserved
    out  = bytearray()
    out += b'ur'
    out += struct.pack('>H', 16)              # ruHeadLen 不变
    out += struct.pack('>H', len(body))       # BodyLen 变为 16
    out += struct.pack('>H', 4)               # Cmd = RES
    out += struct.pack('>H', 0)
    out += struct.pack('>H', 0)
    out += struct.pack('>I', seq)
    out += struct.pack('>I', biz)
    return bytes(out) + bytes(body)           # 合计 24 + 8 = 32 B
```

### 候选 C（强度最低但最接近 §1 字段名池：显式写 `QosResFlag` + 两个列表头）

**依据**：字段名池给出 `QOSGetRes = BusinessID . QosResFlag . SpdFlag . SpdData . Res . QosList`
及 `QOS_RESFLAG_CONNDIP_LIST | QOS_RESFLAG_GAMESVR_LIST` 的组合。
计数宽度取 **u16**（`QOSSS` 旁证 `, 0 ... 1 ...` 是 u16 形态，MEDIUM）；
`ConndIP` 按 §1.3 的复合结构**先按 `IntNum=1 + IntList=[u32]` 试**。

```python
def build_qos_get_res_C(req, ip='127.0.0.1', port=8000):
    import struct, socket
    seq = struct.unpack_from('>I', req, 12)[0]
    biz = struct.unpack_from('>I', req, 16)[0]
    ipn = struct.unpack('>I', socket.inet_aton(ip))[0]
    # 推测的 flag 位值（顺序即枚举序，值本身 UNKNOWN，先用 1/2/4/8）
    FLAG_SCORE, FLAG_QOSLIST, FLAG_GAMESVR_LIST, FLAG_CONNDIP_LIST = 1, 2, 4, 8
    flag = FLAG_CONNDIP_LIST | FLAG_GAMESVR_LIST

    body = bytearray()
    body += struct.pack('>I', biz)            # BusinessID
    body += struct.pack('>I', flag)           # QosResFlag       (宽 UNKNOWN)
    body += struct.pack('>H', 0)              # SpdFlag = 0 -> 无 SpdData
    # QOSConndIPPortList
    body += struct.pack('>H', 1)              # ConndIPPortNum   (宽 UNKNOWN)
    body += struct.pack('>I', ipn)            #   ConndIP   (复合结构首分支简化)
    body += struct.pack('>H', port)           #   ConndPort (宽 UNKNOWN)
    body += struct.pack('>I', 0)              #   Score     (宽 UNKNOWN)
    # QosCSGameSvrList
    body += struct.pack('>H', 1)              # GameSvrNum       (宽 UNKNOWN)
    body += struct.pack('>I', ipn)            #   GameSvrIPList  (简化)
    body += struct.pack('>I', ipn)            #   ConndIP
    body += struct.pack('>H', port)           #   ConndPort
    body += struct.pack('>I', 0)              #   Score
    # QosList
    body += struct.pack('>H', 0)              # QosNum = 0

    out  = bytearray()
    out += b'ur'
    out += struct.pack('>H', 16)
    out += struct.pack('>H', len(body))
    out += struct.pack('>H', 4)               # Cmd = RES
    out += struct.pack('>H', 0)
    out += struct.pack('>H', 0)
    out += struct.pack('>I', seq)
    out += struct.pack('>I', biz)
    return bytes(out) + bytes(body)
```

---

## 3. 推荐决策路径

1. **先证实候选 A** —— 它与已被接受的 24 B 帧只差 4 字节内容，改动最小，且保持长度自洽。
2. 若 A 被接受但仍不推进，**试候选 B**（32 B）—— 这是「增加端口」的最小增量。
3. 只有 A/B 都失败，才用候选 C；C 依赖 3 个 UNKNOWN 假设（flag 值、计数宽度、`ConndIP` 形态），
   必须准备好按 §1.3 的复合 `IP` 结构改写。

**判定「被接受」的信号**：客户端停止重传（与本次 24 B 应答相同）。
但注意——**「停止重传」只证明握手通过，不证明拿到了服务器列表**。要区分这两者，
需要看客户端在应答后是否发出**后续包**（本输入中未出现）。

---

## 4. 强度汇总

| 结论 | 强度 |
|---|---|
| `0x18` = 请求 `Len` = 24，非「24 项」 | **HIGH**（`16+8=24` 三处自洽） |
| `Magic=ur` / `ruHeadLen=16` / `BodyLen=8` / `Cmd=3→4` / `ProtoVer=0` / `Seq=u32` / `BusinessID=u32` | **HIGH**（实帧） |
| 现有 24 B 应答只是握手，不含任何服务器列表内容 | **HIGH**（`BodyLen=8` 容不下字段名池要求的字段） |
| `ConndIP` 不是裸 u32，而是 `IntNum/IntList`+`StrNum/StrList` 复合结构 | MEDIUM（`QOSSS` 同族推断） |
| `SpdFlag` 是 u16 形态 | MEDIUM（`, 0 ... 1 ...` 形态） |
| 所有计数/Score/QosResFlag 的位宽 | **UNKNOWN** |
| `QOS_RESFLAG_*` 的具体位值 | **UNKNOWN**（名称池只给名称） |
| `QOS_CS_MAGIC` 字面值 | **UNKNOWN** |

---

## 5. 本输入仍缺

1. **一份真实的 `QOS_GET_RES` 报文**（最直接，一次性解决全部位宽）
2. `QOS_CS_MAX_*` / `TQOS_CS_STRING_LEN` 数值
3. `QOS_RESFLAG_*` 位值
4. `IP` 复合结构的精确子字段宽度（`IntNum`/`StrNum`/`Resvlen`/`Bloblen` 各自宽度）
5. 客户端在收到合法 `QOS_GET_RES` 后的**下一跳**是什么（决定「是否推进」的判据）

---

## 6. 附：新增证据位置

| 内容 | 位置 |
|---|---|
| 24 B 请求实帧 | `SINGLE_V0B\local_listeners.jsonl` 第 2 行 `data_hex` |
| 24 B 应答实帧 + 解析 | `SINGLE_V0B\local_listeners.jsonl` 第 3 行 `sent_hex` / `req_parsed` |
| 监听端口集合 | `SINGLE_V0B\host_redirect.log`：`tcp=[80,443,3074,8000,8081,10009,10010,20810,28960] udp=[80,443,3074,8000,8081,20810,28960]` |
| 已成功打补丁的域名+地址 | `SINGLE_V0B\redirect_targets.json`（`ied-tqos.qq.com@0x00DD98A0`、`stun.*@0x00D5A9xx`、`cod4master.activision.com@0x00DBD558`） |
| `QOSSS` IP 复合结构 | `KEY_CONTEXT` offs `30863` |
