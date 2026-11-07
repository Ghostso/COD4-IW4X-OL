import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
p = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\CONFIRMED_RESULTS_20260928.md"
s = open(p, encoding="utf-8", errors="replace").read()

add = """

---

## 20. 大厅通道协议已破解（20260928 晚间，决定性）

本节推翻了此前 3 个错误结论，并把「无法连接大厅服务」从**未知根因**
推进到**已知协议契约**。整条链现在只剩最后一道长度/解帧门槛。

### 20.1 推翻：报告第 19 节的「端口为 0」是采样错位造成的误判

`restore_iips_contract_001/observer2/AboProbe.cs` 的 CSV 表头与写入取值
**顺序不一致**：表头 `lobConn4e8,lobConn4ec,lobConn4f0` 之后才轮到
`lobby_port9780,...`，但取值那一行把 6 个 lobby 字段全部写在前面。于是
CSV 里名为 `lobby_port9780` 的列实际装的是 `lobConn4f4`（一个堆指针），
名为 `lobby_host76a8` 的列装的是 `lobConn4f8`。

实测值一验即明：

```text
CSV 声称 lobby_host76a8 = 775369265  ->  0x2E373231  ->  ASCII "127."
CSV 声称 lobby_port9780 = 999778464  ->  0x3B9768A0  ->  堆指针低 32 位
```

也就是说 `[0x81A9780]`（端口）与 `[0x81A76A8]`（主机）**一直是对的**，
从未是瓶颈。表头已修正。

### 20.2 推翻：`[req+0xC8]` 不是「1 直接跳 4」，而是真实走完了 1 -> 2

20ms 采样下可见完整推进：

```text
t=37.048 reqC8=1  req9c=0        <- 0xBA4080 置 1，发起连接
t=37.080 reqC8=2  req9c=1 req5e8=1 <- 0xBA4127 置 2（唯一写 2 的地方）
t=37.111 reqC8=4                 <- 0xBA3456 判定失败
```

`0xBA4127` 之前有一道硬门：

```asm
00BA4114  lea ecx, [ebx+0xC4]
00BA411A  call 0xC73900          ; 连接状态查询
00BA411F  cmp eax, 1
00BA4122  jne 0xBA414B           ; 只有 eax==1 才落到 0xBA4127
00BA4127  mov dword ptr [ebx+0xC8], 2
```

`0xC73900` 返回 **1** 表示连接成功、可以收发。所以关键不是 URL，是这台
**Tenio 连接器**的可用状态。

### 20.3 根因 A：大厅主机全局 `0x81A7F34` 从未被填充

`0x00641600` 是一个「分号分隔配置串」解析器，把令牌轮流写入 4 组
host/port：

```text
字段布局（实测）：
  f0 host 0x081A76A8   f1 port 0x081A9EC4
  f2 host 0x0E51184    f3 port 0x0E513D4
  f4 host 0x081A7F34   f5 port 0x081A9780   <- 大厅用
  f6 host 0x081A9784   f7 port 0x081A9EC0
```

`0x007F34E0` 会建两个 DNS 解析对象：

- 对象 A（`0x84ABA70`）解析 **f0** `0x81A76A8`
- 对象 B（`0x84ABA74`）解析 **f4** `0x81A7F34`

而 `0x007F3600`（DNS 完成）把结果写进两个全局 URL 槽：

```asm
007F36F5  mov ecx, 0x0E3ECA10   ; <- 对象 A 的地址串
007F36FA  call 0xB76F10
007F3723  mov ecx, 0x0E3EC988   ; <- 对象 B 的地址串  = 大厅用
007F3728  call 0xB76F10
```

`0x007F3800`（大厅）随后用 `0xE3EC988` 组 URL。运行期原始字节：

```text
tplA(0xE3ECA10) = 7f 00 00 01 00 ...   -> 127.0.0.1   （正确）
tplB(0xE3EC988) = 00 00 03 ec 00 ...   -> 236.3.0.0   （垃圾）
```

因为 `0x81A7F34` 从未被写入，对象 B 的域名槽是空的，解析失败后地址
缓冲保持 BSS（全 0），退回逻辑又从主 URL 缓冲尾部取到 `00 00 03 EC`
——那正是 `0xE3EC000` 的 BSS 基址常量，所以「IP」变成 `236.3.0.0`。

**修复**：poke `0x81A7F34 = "127.0.0.1"`（本轮已加入观察器）。
修复后 `tplB` 变为 `7f 00 00 01`，`reqC8` 首次到达 **2**，客户端真的
建起了 TCP 连接到 `127.0.0.1:8443`。

### 20.4 根因 B：大厅通道不是 TLS，是明文 TCP

`reqC8` 到达 2 之后，HTTPS 探针 `8443` 记录到：

```text
{"event": "tls_fail", "error": "SSLError(1, '[SSL: WRONG_VERSION_NUMBER] ...')"}
```

客户端在该连接上发的是裸字节，不是 ClientHello。**大厅信道走明文
TCP**。（`/auth/` 走 TLS，两者不同，此前一直混为一谈。）

### 20.5 第一个大厅包（28 字节，已捕获）

把大厅端口指到明文探针 `127.0.0.1:8446` 后抓到：

```text
c8 00 00 00  c8 00 00 00  d2 00 00 00  dc 00 00 00
00 00 08 00  52 71 ca 53  2a c1 28 de
```

逐字段：

```text
0x00: 200 (u32)     -- magic / 版本 / 通道号
0x04: 200 (u32)
0x08: 210 (u32)
0x0c: 220 (u32)
0x10: 00 00 08 00   -- 标志位 bit19 = 0x00080000
0x14: 随机 u32      -- 每次运行不同
0x18: 随机 u32      -- 每次运行不同
```

它**不含票据**（请求头里的 `DW-Client-Ticket` 只有 9 字节
`FqxK/wU+rcitysaPaa8QUwA==`，`DW-Server-Ticket` 才是 128 字节），
所以这是连接器自身的握手/保活，不是业务请求。

### 20.6 决定性实验：客户端能解帧，但要求最小长度

用探针回送不同的字节流，看客户端是否接受（接受则推进到 `req9c=3`）：

| 回送 | 结果 |
|---|---|
| 无 | `req9c` 停在 1，超时 |
| 28B 原样回声 | **接受**，`sub-state 3`，连接保持 |
| 24B（`18 00 00 00` + 20B） | **拒绝**，立即 RST |
| 200B（`c8 00 00 00` + 196B 填充） | **接受**，`req9c=3` 保持 2 秒 |
| 204B（`c8 00 00 00` + 200B） | 接受后仍最终失败 |
| 208B | 拒绝 |

结论：

1. 前 4 字节是 **little-endian 长度前缀**（`18 00 00 00` = 24）。
2. 客户端把该长度 **减 4** 当作负载长度，且要求负载 **>= 200 字节**。
   - 28B 包 -> 负载 24B：够通过「连接可用」判定（`0xC73900` 返回 1），
     但不足以推进业务解帧。
   - 204B 包 -> 负载恰好 200B：能进解帧，但内容字段非法，仍失败。
3. 分帧已确认为「u32 长度前缀 + 负载」，长度门限是 **200**。

### 20.7 当前断点（精确）

```text
DNS 阶段        : 通过（tplA=127.0.0.1）
账号鉴权        : 通过（sub=9, code=700, DW_ACCOUNT_LOGIN_COMPLETE）
objC 队列校验    : 通过（lob1400=8900 lob240=2）
大厅 TCP 连接    : 通过（reqC8 到达 2，socket 真实建立）
大厅 28B 握手    : 通过（客户端接受回声，进入 sub-state 3）
大厅业务解帧     : 失败 —— 需要 >=200 字节的合法负载
```

只剩最后一个未知：**那 200 字节大厅握持负载的字段语义**。

### 20.8 新增/修改的工具

```text
CODOLServer/lobby_server/lobby_plain_probe.py   明文 TCP 探针 + 收发 hex 日志
restore_iips_contract_001/observer2/AboProbe.cs 修正 CSV 错位；新增
   lobReq644 / lobReq5e8 / lobReqC4 / lobReqLen / lobReqStr /
   dnsA / dnsB / dnsAHome / tplALen / tplAStr / tplBLen / tplBStr /
   tplAHex / tplBHex / dnsBHex / lobReqHex 探针；
   poke 追加 0x081A7F34 / 0x081A9784 / 0x081A9EC0；
   [0x081A9780] 改写为 8446（大厅明文端口）
```

复现命令：

```text
python -X utf8 CODOLServer/lobby_server/lobby_plain_probe.py \\
  --bind 127.0.0.1 --port 8446 --log CODOLServer/logs/PLAIN/x.jsonl \\
  --reply-hex <len32><payload...>

python -X utf8 CODOLServer/_mainline/auto_lobby_loop.py --rounds 1 \\
  --seconds 90 --poke-lobby-host 127.0.0.1 --poke-lobby-port 8443 \\
  --poke-lobby-globals
```

### 20.9 归档

```text
CODOLServer/archive/CONFIRMED_20260928_1900
  390 文件，SHA256 校验 390/390 通过（mismatch=0 absent=0）
```
"""

s = s.rstrip() + add
open(p, "w", encoding="utf-8", newline="\n").write(s + "\n")
print("appended", len(add), "chars")
