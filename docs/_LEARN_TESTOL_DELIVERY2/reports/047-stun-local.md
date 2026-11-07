# 学习报告 047（重开）— `stun_local.py` 全文（184 行）

**学习范围**：`bundle\stun_local.py`（7,618 B / 184 行）全文
**性质**：全实测
**★★★ 本报告收录**Demonware 私有 STUN 的完整字节格式**与**一次"假设被否证"的完整记录**

---

## 一、★★★★★ docstring 的完整记录（第 1–32 行）

### 1.1 ★★★ 背景（第 4–6 行，逐字）

```
背景：CODOL 客户端取"公网地址"走 UDP STUN 到 stun1/2/3-tub.codol.qq.com（见 TESTOL\stun.ini）。
坏启动的遥测是 `Address Fail|result = -3`（= getPublicAddr 失败），且坏轮呈现 UDP 重传超时形态
（71/4 之后空转 29 秒）。把这三个域名指到 127.0.0.1 并由本程序确定性应答，即可把这条链路固定下来。
```

★★★ **⇒ 三个精确的遥测：**
```
`Address Fail|result = -3`
`71/4` 之后**空转 29 秒**
域名：`stun1/2/3-tub.codol.qq.com`
```

### 1.2 ★★★ 第一版假设（第 8–13 行）

```
兼容性做法：
  * 同时回 MAPPED-ADDRESS(0x0001, RFC3489) 与 XOR-MAPPED-ADDRESS(0x0020, RFC5389)，
    严格的 5389 客户端会忽略前者，3489 客户端会忽略后者。
  * 事务 ID 直接回显请求的字节 4..19（这对 5389 的 magic cookie + 96bit txid 与
    3489 的 128bit txid 都成立）。
  * 回显的地址/端口 = 客户端自己的源地址/源端口（这就是 STUN 的语义）。
```

★★★ **⇒ 第一版假设：**客户端用标准 STUN（RFC 3489/5389）**。**
**⇒ 所以同时回两种属性，兼容两代协议。**

### 1.3 ★★★★★ 抓包定因（第 15–26 行，逐字）

```
★★ 2026-10-07 03:0x 更正（抓包定因，本轮新增）：客户端**不发 RFC5389 STUN**。
    它的 `getPublicAddr` 走的是 **Demonware 私有 STUN**，两种请求：
        14 02 00 00   (类型 0x14，4 字节)
        1e 03 00      (类型 0x1E，3 字节)
    目标端口是 **3074**（UDP），不是 3478/19302：
      * 好轮 `99-Tmp\cap-nic-d6.pcapng`：客户端 192.168.5.11:22011 -> 185.34.107.128:3074，
        真服 200 ms 内回 `1502003afc12715210b9226b81020c`（15 字节）⇒ 开局正常。
      * 坏轮 `99-Tmp\cap-stun-d5.pcapng`（回环）：同样两发探针发往 **127.0.0.1:3074**
        （hosts 把 stun1/2/3-tub.codol.qq.com 指到 127.0.0.1），**0 回复** ⇒
        `71/3 UserWarning|…|Address Fail|result = -3` ⇒ `t≈54s 致命错误`。
      ⇒ 本脚本原先只听 3478/19302 ⇒ **一个探针都收不到**（这正是「STUN 假设被否证」的原因），
        坏启动因此是**必然**而非概率。响应字节形状见 `build_dw_response`。
```

### ★★★★★ 完整的抓包证据

| 项 | 值 |
|---|---|
| **请求 1** | **`14 02 00 00`**（类型 `0x14`，4 字节） |
| **请求 2** | **`1e 03 00`**（类型 `0x1E`，3 字节） |
| **目标端口** | **`3074`（UDP）**，不是 3478/19302 |
| **好轮抓包** | `99-Tmp\cap-nic-d6.pcapng` |
| 好轮流量 | `192.168.5.11:22011` → **`185.34.107.128:3074`** |
| ★ **真服应答** | **`1502003afc12715210b9226b81020c`**（**15 字节**） |
| 好轮延迟 | **200 ms 内** |
| **坏轮抓包** | `99-Tmp\cap-stun-d5.pcapng`（回环） |
| 坏轮流量 | 同样两发 → `127.0.0.1:3074` |
| 坏轮结果 | **0 回复** |
| 坏轮遥测 | **`71/3 UserWarning\|…\|Address Fail\|result = -3`** |
| 坏轮致命 | **`t≈54s 致命错误`** |

★★★ **⇒ 核心结论（逐字）：**
> **本脚本原先只听 3478/19302 ⇒ 一个探针都收不到**（这正是「STUN 假设被否证」的原因），
> **坏启动因此是必然而非概率。**

★★★ **⇒ 这是全包**最有力的一句诊断**：**
```
只听 3478/19302
        ↓
★ 一个探针都收不到
        ↓
★★★ **坏启动是必然而非概率**
```

### 1.4 ★★★ 三种用法（第 28–31 行）

```
& '<PY>' stun_local.py                 # 监听 UDP 0.0.0.0:3478
& '<PY>' stun_local.py --ports 3074,3478,19302   # ← launch_chain.py 用的就是这组
& '<PY>' stun_local.py --dump          # 额外把每个收到包的前 64 字节打成 hex
```

★★ **⇒ 默认只 3478，`launch_chain.py` 传三端口组。**

---

## 二、★★★ STUN 常量（第 44–50 行）

```python
BINDING_REQUEST = 0x0001
BINDING_SUCCESS = 0x0101
MAGIC_COOKIE = 0x2112A442

ATTR_MAPPED = 0x0001
ATTR_XOR_MAPPED = 0x0020
ATTR_SOFTWARE = 0x8022
```

### ★★★ 六个标准 STUN 常量

| 常量 | 值 | 含义 |
|---|---|---|
| `BINDING_REQUEST` | **`0x0001`** | 绑定请求 |
| `BINDING_SUCCESS` | **`0x0101`** | 绑定成功应答 |
| **`MAGIC_COOKIE`** | **`0x2112A442`** | ★ RFC 5389 魔数 |
| `ATTR_MAPPED` | `0x0001` | MAPPED-ADDRESS（RFC 3489） |
| `ATTR_XOR_MAPPED` | `0x0020` | XOR-MAPPED-ADDRESS（RFC 5389） |
| `ATTR_SOFTWARE` | `0x8022` | SOFTWARE |

★★ **⇒ 这些常量**只在标准 STUN 路径用**（而客户端**不发**标准 STUN）。**

---

## 三、★★★★ `build_response` —— 标准 STUN 应答（第 64–94 行）

```python
def build_response(data, addr):
    """返回 (应答字节, 说明串)；不是 STUN Binding Request 时返回 (None, 说明)。"""
    if len(data) < 20:
        return None, "短包 %d 字节" % len(data)
    mtype, mlen = struct.unpack_from(">HH", data, 0)
    if mtype != BINDING_REQUEST:
        return None, "非 Binding Request(type=0x%04X len=%d)" % (mtype, mlen)

    tx = data[4:20]                      # 原样回显（对 5389/3489 都成立）
    cookie = struct.unpack_from(">I", data, 4)[0]

    ip = addr[0]
    port = addr[1]
    try:
        ip_be = socket.inet_aton(ip)
    except OSError:
        return None, "源地址不是 IPv4: %r" % (ip,)

    # MAPPED-ADDRESS: 0x0001, len 8, 0, family(1=IPv4), port, addr
    mapped = struct.pack(">HHBBH", ATTR_MAPPED, 8, 0, 1, port) + ip_be
    # XOR-MAPPED-ADDRESS: port ^ (cookie>>16), addr ^ cookie
    xport = port ^ (MAGIC_COOKIE >> 16)
    xip = bytes(a ^ b for a, b in zip(ip_be, struct.pack(">I", MAGIC_COOKIE)))
    xmapped = struct.pack(">HHBBH", ATTR_XOR_MAPPED, 8, 0, 1, xport) + xip
    sw = b"stun_local"
    software = struct.pack(">HH", ATTR_SOFTWARE, len(sw)) + sw

    body = mapped + xmapped + software
    hdr = struct.pack(">HH", BINDING_SUCCESS, len(body)) + tx
    return hdr + body, ("Binding Request cookie=0x%08X -> 回 MAPPED+XOR-MAPPED %s:%d"
                        % (cookie, ip, port))
```

### ★★★ 标准 STUN 应答的完整布局

```
STUN 头（20 字节）
+0x00  2  BINDING_SUCCESS (0x0101)
+0x02  2  body 长度
+0x04 16  ★ 事务 ID（原样回显 data[4:20]）

MAPPED-ADDRESS 属性
+0x00  2  ATTR_MAPPED (0x0001)
+0x02  2  len = 8
+0x04  1  0（保留）
+0x05  1  family = 1（IPv4）
+0x06  2  port
+0x08  4  ip

XOR-MAPPED-ADDRESS 属性
+0x00  2  ATTR_XOR_MAPPED (0x0020)
+0x02  2  len = 8
+0x04  1  0
+0x05  1  family = 1
+0x06  2  port ^ (MAGIC_COOKIE >> 16)    ← ★ 0x2112
+0x08  4  ip ^ MAGIC_COOKIE

SOFTWARE 属性
+0x00  2  ATTR_SOFTWARE (0x8022)
+0x02  2  len = 10
+0x04 10  "stun_local"
```

★★★ **⇒ XOR 算法：**
```python
xport = port ^ (MAGIC_COOKIE >> 16)     # = port ^ 0x2112
xip   = ip   ^ MAGIC_COOKIE             # 逐字节 XOR
```

★★ **⇒ 这是**标准的 RFC 5389 XOR-MAPPED-ADDRESS 算法**。**

★ **⇒ 但**这段代码在交付包里**永远不会被执行**（客户端不发标准 STUN）。**

---

## 四、★★★★★ `build_dw_response` —— Demonware 私有 STUN（第 97–131 行）

### 4.1 ★★★ 格式定义（第 100–104 行，逐字）

```
形状（真服抓包，`cap-nic-d6.pcapng`，15 字节，0x14 与 0x1E 都是 15 字节）：
    <type+1> 02 00 <mapped_ip:4> <mapped_port:2 LE> <server_ip:4> <server_port:2 LE>
实例（好轮真服回的 0x14 应答）：
    15 02 00 | 3a fc 12 71 | 52 10 | b9 22 6b 81 | 02 0c
    = 15 0200 58.252.18.113:4178 185.34.107.129:3074
```

### ★★★★★ 完整的 15 字节布局

| 偏移 | 大小 | 内容 | 实例值 |
|---|---|---|---|
| **`0x00`** | 1 | **`type + 1`** | **`15`**（`0x14+1`） |
| **`0x01`** | 2 | **`02 00`**（`AF_INET` 小端） | `02 00` |
| **`0x03`** | 4 | **mapped_ip** | **`3a fc 12 71`** = **`58.252.18.113`** |
| **`0x07`** | 2 | **mapped_port（小端）** | **`52 10`** = **`4178`** |
| **`0x09`** | 4 | **server_ip** | **`b9 22 6b 81`** = **`185.34.107.129`** |
| **`0x0D`** | 2 | **server_port（小端）** | **`02 0c`** = **`3074`** |
| **合计** | **15** | | |

★★★ **⇒ 三个关键点：**
```
① `type + 1`（0x14→0x15，0x1E→0x1F）
② 所有多字节字段都是**小端**（`<H`）
③ 15 字节固定
```

### 4.2 ★★★ 与老外归档的差异（第 106–109 行，逐字）

```
老外归档字节（`02-tools\scripts\laowai-patched\tests\backend\ServerTests.cpp:95-114`）同布局，
只是 mapped 填占位 `F0 00 00 01`、且 0x1E 取 9 字节（不带 server 字段）。
这里**照本机客户端实测接受过的 15 字节形态**（两种类型都 15 字节）：
本机全在 loopback，mapped 就是客户端自己的源地址，server 就是本应答器。
```

★★★ **⇒ 两处差异：**

| 项 | 老外 | 本实现 |
|---|---|---|
| **mapped 地址** | **占位 `F0 00 00 01`** | ★ **真实客户端源地址** |
| **`0x1E` 应答长度** | **9 字节**（不带 server 字段） | ★★ **15 字节**（含 server） |

★★ **⇒ 本实现的选择理由："照本机客户端实测接受过的 15 字节形态"。**

### 4.3 ★★★ 实际实现（第 111–131 行）

```python
if not data:
    return None, None
t = data[0]
if t == 0x14:
    kind = "0x14 NAT"
elif t == 0x1E:
    kind = "0x1E ADDR"
else:
    return None, None                      # ★ 不是 DW 类型 ⇒ 交给标准 STUN
if len(data) < 3:
    return None, "DW 类型 %s 但只有 %d 字节" % (kind, len(data))
try:
    mapped_ip = socket.inet_aton(addr[0])
except OSError:
    return None, "DW %s 源地址不是 IPv4: %r" % (kind, addr)
server_ip = socket.inet_aton("127.0.0.1")
body = struct.pack("<H", socket.AF_INET) + mapped_ip + struct.pack("<H", addr[1]) \
    + server_ip + struct.pack("<H", local_port)
resp = bytes([t + 1]) + body
```

### ★★★★★ 三个设计要点

**① 两种类型的语义（第 114–117 行）**

```python
if t == 0x14:   kind = "0x14 NAT"
elif t == 0x1E: kind = "0x1E ADDR"
```

★★★ **⇒ 两种类型：**
```
0x14  →  "NAT"     （探测 NAT 类型 / 公网地址）
0x1E  →  "ADDR"    （探测服务器地址）
```

**② 最小的长度检查（`< 3`）**

★ **⇒ 只要求 3 字节（因为 `0x1E` 请求只有 3 字节）。**

**③ `server_ip` 硬编码 `127.0.0.1`**

★★ **⇒ 因为本机全在 loopback，`server` 就是本应答器。**

---

## 五、★★★★ `serve` —— UDP 监听循环（第 134–161 行）

```python
def serve(port, dump):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(("0.0.0.0", port))              # ★ 绑所有接口
    except OSError as e:
        log("!! 绑定 UDP %d 失败: %r" % (port, e))
        return                                  # ★ 单端口失败不拖垮其他
    log("监听 UDP 0.0.0.0:%d" % port)
    while True:
        try:
            data, addr = s.recvfrom(4096)
        except Exception as e:
            log("recv 异常 %r" % (e,))
            continue
        if dump:
            log("  <- %s:%d %d 字节: %s" % (addr[0], addr[1], len(data),
                                           data[:64].hex(" ")))
        resp, note = build_dw_response(data, addr, port)   # ★ 先试 DW
        if note is None:
            resp, note = build_response(data, addr)        # ★ 再试标准 STUN
        log("  %s:%d %s" % (addr[0], addr[1], note))
        if resp:
            try:
                s.sendto(resp, addr)
                log("     -> 已回 %d 字节" % len(resp))
            except Exception as e:
                log("     !! 回包失败 %r" % (e,))
```

★★★ **⇒ 五个要点：**
```
① 绑 **`0.0.0.0`**（所有接口）
② ★ 单端口失败**不拖垮其他**（`return`）
③ ★★ **先试 DW 私有 STUN，再试标准 STUN**（`note is None` 表示不认识）
④ `recvfrom(4096)`（STUN 包很小）
⑤ `--dump` 打印前 **64 字节** hex
```

★★ **⇒ 第 ③ 条的两级回退设计很清晰：**
```python
resp, note = build_dw_response(...)     # 不认识 ⇒ (None, None)
if note is None:
    resp, note = build_response(...)    # 标准 STUN
```

★ **⇒ 但如前所述，标准 STUN 分支**永远不会被触发**。**

---

## 六、★★★ `main` —— 多端口启动（第 164–179 行）

```python
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ports", default="3478",
                    help="逗号分隔；默认 3478（STUN 标准端口）")
    ap.add_argument("--dump", action="store_true", help="打印每个收到包的 hex")
    a = ap.parse_args()
    ports = [int(x) for x in a.ports.split(",") if x.strip()]
    log("stun_local 启动，端口 %s（magic cookie 0x%08X）" % (ports, MAGIC_COOKIE))
    ts = [threading.Thread(target=serve, args=(p, a.dump), daemon=True) for p in ports]
    for t in ts:
        t.start()
    try:
        while True:
            time.sleep(3600)                # ★ 每小时醒一次
    except KeyboardInterrupt:
        log("退出")
```

★★★ **⇒ 三个要点：**
```
① `--ports` 默认 **`3478`**（★ 单端口 —— 会漏掉 3074）
② 每个端口一个 **daemon 线程**
③ 主线程 `sleep(3600)` 保持存活
```

★★ **⇒ 第 ① 条是**默认值陷阱**：**
```
默认只 3478  ⇒  ★ 一个探针都收不到（docstring 已明说）
必须传 `--ports 3074,3478,19302`
```

★ **⇒ 而 `launch_chain.py:317-318` **确实传了**三端口组 ⇒ 不会踩这个坑。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ 坏启动遥测 | `Address Fail\|result = -3` / `71/4` 后空转 **29 秒** |
| 2 | ★★★★★ **DW 请求 1** | **`14 02 00 00`**（类型 `0x14`，4 字节） |
| 3 | ★★★★★ **DW 请求 2** | **`1e 03 00`**（类型 `0x1E`，3 字节） |
| 4 | ★★★ **目标端口** | **`3074`（UDP）** |
| 5 | ★★ 好轮真服 | **`185.34.107.128:3074`**，15 字节，200 ms |
| 6 | ★★★ 真服应答字节 | **`1502003afc12715210b9226b81020c`** |
| 7 | ★★★★★ **核心结论** | **"只听 3478/19302 ⇒ 一个探针都收不到 ⇒ 坏启动是必然而非概率"** |
| 8 | ★★★ 15 字节布局 | `<type+1> 0200 <mapped_ip:4> <mapped_port:2LE> <server_ip:4> <server_port:2LE>` |
| 9 | ★ `type+1` | `0x14→0x15` / `0x1E→0x1F` |
| 10 | ★ 字段字节序 | **全小端（`<H`）** |
| 11 | ★★ 老外差异 | mapped 占位 `F0 00 00 01`；`0x1E` 只 **9 字节** |
| 12 | ★ 本实现选择 | **15 字节（两种类型都）** |
| 13 | ★ 两种类型语义 | `0x14`=**NAT** / `0x1E`=**ADDR** |
| 14 | ★ `server_ip` | 硬编码 **`127.0.0.1`** |
| 15 | 绑定 | **`0.0.0.0`** |
| 16 | ★★ 两级回退 | 先 DW，后标准 STUN（后者永不触发） |
| 17 | ★★★ 默认端口陷阱 | **`--ports` 默认只 `3478`** ⇒ 必漏 |
| 18 | 标准 STUN 常量 | `0x0001`/`0x0101`/`0x2112A442`/`0x0001`/`0x0020`/`0x8022` |

---

## 八、结论

### 1. ★★★★★ **"坏启动是必然而非概率"** 是本次学习最有力的一句诊断

★ **⇒ 只听 3478/19302 ⇒ 一个探针都收不到。**

### 2. ★★★★★ **Demonware 私有 STUN 的 15 字节格式**已完全定案

```
<type+1> 0200 <mapped_ip:4> <mapped_port:2LE> <server_ip:4> <server_port:2LE>
```

### 3. ★★★ **`0x14` = NAT 探测 / `0x1E` = 地址探测**

### 4. ★★★ **实测优先于参照**（老外 `0x1E` 9 字节，本机要 15 字节）

### 5. ★★ **默认 `--ports 3478` 是陷阱**（`launch_chain.py` 正确覆盖）

### 6. ★★ 标准 STUN 分支是**死代码**（客户端不发）

---

## 九、下一步

- `force_display_name.py`（19,288 B）
- `bundle\` 五个证书文件
- `payload\` 四个插件 PE + 四个 loader 二进制
- `payload\` 18 个小 map lua + `cha.lua`/`zm.lua` 剩余
- `source\` 结构与关键文档
