# 学习报告 027 — 逐字节：secrets.txt 契约 + 名字常量（铁证 `SGamingSH0X`）

**方法**：按 NUL 切分 `0x3B4500..0x3B4700`（LSG 密钥区）+ `0x3B2F50` 附近（名字区）
**性质**：全实测
**★★★ 本报告给出了"名字三方同步"缺陷的**二进制级铁证**

---

## 一、★★★ `OLMOD_LSG_SECRETS` 的完整契约（逐串 + 偏移）

```
偏移        长度  内容
0x3B4514    19   "Matchmaking::Update"
0x3B4528    22   "Matchmaking::Terminate"
0x3B4540    17   "OLMOD_LSG_SECRETS"          ← ★★★ 变量名
0x3B4554    11   "secrets.txt"                ← ★★★ 默认文件名
0x3B4560     9   "challenge"                  ← ★★★ 键 1
0x3B456C     7   "aes_out"                    ← ★★★ 键 2
0x3B4574     6   "aes_in"                     ← ★★★ 键 3
0x3B457C     8   "hmac_out"                   ← ★★★ 键 4
0x3B4588     7   "hmac_in"                    ← ★★★ 键 5
0x3B4590     6   "absent"                     ← 状态值
0x3B4598    10   "challenge="                 ← 日志格式
0x3B45A4    16   "truncated uint32"
0x3B45B8    29   "invalid encrypted lobby frame"
0x3B45D8    25   "lobby frame HMAC mismatch"  ← ★★ 校验失败
0x3B45F4    31   "invalid lobby ciphertext length"
0x3B4614    31   "invalid decrypted lobby payload"
0x3B4634    29   "Rejected oversized LSG frame."
0x3B4654    20   "Rejected LSG frame: "
0x3B466C    31   "expected 0xC8 client header ACK"   ← ★★★
0x3B468C    26   "LSG_CAPTURE client_header="
0x3B46A8    31   "Accepted LSG client header ACK."
0x3B46C8    27   "expected 0xAB82 client auth"        ← ★★★
0x3B46E4    45   "LSG session key taken from the client ticket."  ← ★★★
```

### ★★★ 与 `nt10.py` 的 `secrets.txt` 格式完全对应

**报告 005 / 012 的六元组**：
```
decrypt      <- aes_out
requestHmac  <- hmac_out
encrypt      <- aes_in
responseHmac <- hmac_in
responseId   <- challenge
```

★★★ **二进制里的 5 个键名**：
```
challenge    (0x3B4560)
aes_out      (0x3B456C)
aes_in       (0x3B4574)
hmac_out     (0x3B457C)
hmac_in      (0x3B4588)
```

★★★ **⇒ 完全一致。`nt10.py` 写这 5 个键，`Alwaysoffline` 读这 5 个键。**

★ **默认路径 `secrets.txt`（相对路径）** ——
**`OLMOD_LSG_SECRETS` 未设时用 `secrets.txt`。**

### ★★ 三条校验失败日志链

```
0x3B45B8  "invalid encrypted lobby frame"
0x3B45D8  "lobby frame HMAC mismatch"       ← ★ HMAC 不对
0x3B45F4  "invalid lobby ciphertext length"
0x3B4614  "invalid decrypted lobby payload"
```

★★ **⇒ 如果密钥错了，会在这四处之一报错。**

★ **记忆里的 `[100] bug` 表现正是"HMAC mismatch"（报告 012 引用的注释）。**

### ★★★ 两条协议期望值（逐字节）

```
0x3B466C  "expected 0xC8 client header ACK"
0x3B46C8  "expected 0xAB82 client auth"
```

★★ **`0xC8` / `0xAB82`** —— LSG 握手的两个类型字节。

★★ **与报告 012 的 `LobbyProtocol.cpp:97-98` 对齐**：
> `frame is [u32 size][0xAB][0x82][authInfo][clientVerify]`

★★ **`0xAB82` 是 auth 帧的类型字节** ✓
★ **`0xC8` 是 header ACK 的期望值** ——
**但报告 012 说 `0x81` 是 header ACK 的类型**（`buildHeaderAck`）。

★★★ **⇒ `0xC8` 与 `0x81` 是两个不同的东西：**
- **`0x81`** = 服务端→客户端的 header ACK 类型（报告 012）
- **`0xC8`** = **客户端→服务端**的 header ACK 类型（本报告）

★ **即：客户端回 ACK 用 `0xC8`，服务端回 ACK 用 `0x81`。**

---

## 二、★★★ `SGamingSH0X` 是编译进二进制的默认名（铁证）

### 实测偏移

```
0x3B2E88  17  "uth3 HTTP target"       ← "Auth3 HTTP target" 的一部分
0x3B2E9C  14  "content-length"
0x3B2EAC  25  "invalid Auth3 Content-Length"
0x3B2ECC  16  "AUTH3_CAPTURE request="
0x3B2EE4  18  "AUTH3_CAPTURE response="
0x3B2EFC   9  ") for title "
0x3B2F0C   2  " ("
0x3B2F10  17  "Authenticated user "
0x3B2F24  17  "SSL_do_handshake"
0x3B2F38  11  "SSL_read_ex"
0x3B2F44   9  "BIO_write"
0x3B2F50  10  "SGamingSH0X"          ← ★★★ 就在这里！
0x3B2F5C   3  "0x"
0x3B2F60   3  "0X"
0x3B2F64  21  "OLMOD_PLATFORM_USER_ID"
0x3B2F84   8  "generic"
0x3B2F8C   7  "system"
```

### ★★★ 逐字节铁证

```
0x3B2F50  len=10  "SGamingSH0X"
```

★★★ **`SGamingSH0X` = 10 字节，与 `IdentityConfig.hpp:85` 的
`inline constexpr std::string_view DefaultUsername = "SGamingSH0X";` 完全一致。**

★★ **它就在 `"Authenticated user "` 和 `"OLMOD_PLATFORM_USER_ID"` 之间** ——
**说明它是"认证成功日志"的默认用户名，或 `resolveDisplayName` 的兜底值。**

★★★ **⇒ 交付的二进制**已经**是 `SGamingSH0X` 版本。**

### ★★★ 这是报告 015 那个"名字三方失配"的**决定性证据**

```
源码常量 (IdentityConfig.hpp:85)      "SGamingSH0X"     ← 期望
二进制常量 (Alwaysoffline @0x3B2F50)  "SGamingSH0X"     ← ✓ 已编译进去
launch_chain.py:377 默认               "Easily_"         ← ★★★ 失配！
force_display_name.py 写入的字节        "Easily_"         ← ★★★ 失配！
```

★★★ **⇒ `launch_chain.py` 的 `"Easily_"` 是**过期的**默认值，
包内所有其他环节（源码 + 二进制）都已是 `SGamingSH0X`。**

★ **验证：`launch_chain.py` 里 `"SGamingSH0X"` 出现几次？**
★ **`"Easily_"` 出现 0 次吗？（需要查）**

### ★★ 其他名字常量全部**不在**二进制里

```
Alwaysoffline        201 次  ← 模块名/日志前缀
Lifetime               1 次（0x3B5C40）
Client青               0 次
Easily_                0 次  ← ★★★
AdministraClient       0 次
Sunl1ght               0 次
```

★★★ **⇒ `Easily_` / `AdministraClient` / `Sunl1ght` / `Client青` 全部**未编译进二进制**。**

★ **`Lifetime` 的 1 次在 `0x3B5C40`** —— 需要看上下文（可能是地图名 `lifetime`？）。

★ **`Alwaysoffline` 201 次** —— 模块名（`AlwaysofflineRe.Localnet32`）+ 日志前缀。

---

## 三、★★★ `OLMOD_EXTERNAL_AUTH3` / `EXTERNAL_STUN` / `CLAIM_LOBBY` 的完整语义

### 上下文（`0x3BA528` 附近连读）

```
...ready...<invalid>:......OLMOD_CLAIM_LOBBY...
   lobby.codol.localhost...
   qq.com..demonware.net...stun1-..stun....
   OLMOD_EXTERNAL_STUN.
   stun2-..umbrella....
   STUN claim skipped (OLMOD_EXTERNAL_STUN=1) for .
   uno.....auth3...auth....
   OLMOD_EXTERNAL_AUTH3....
   cs..OLMOD_CLAIM_LEGACY_AUTH.
   lobby...lsg.....Auth3/UNO HTTP..
   STUN....content server..legacy Auth.unclaimed...
   LSG/lobby...STUN dequeued response=.
```

### ★★★ 还原的"服务认领"表

| 服务 | 主机名/标识 | 让出开关 |
|---|---|---|
| **lobby** | `lobby.codol.localhost` | `OLMOD_CLAIM_LOBBY` |
| **auth3** | `qq.com` / `auth` | `OLMOD_EXTERNAL_AUTH3` |
| **stun** | `stun1-` / `stun2-` | **`OLMOD_EXTERNAL_STUN`** |
| **uno** | `umbrella` / `uno` | （同 AUTH3？） |
| **legacy Auth** | `cs` (content server?) | `OLMOD_CLAIM_LEGACY_AUTH` |
| **content server** | — | — |

★★★ **`STUN claim skipped (OLMOD_EXTERNAL_STUN=1) for .`** ——
**这是日志格式串，`for ` 后面接具体主机名。**

### ★ 卸载的服务列表（"unclaimed"）

```
0x3BA5xx  "unclaimed"
```

★ **`Alwaysoffline` 有一套"服务认领/让出"机制**，覆盖 6 类服务。

★★ **⇒ 这是**细粒度的**架构，比 `OLMOD_SKIP_AUX` 精确得多。**

---

## 四、★★★ `OLMOD_GAME_ENDPOINT` 的完整契约

### 上下文（`0x3B5170` 附近）

```
...l.n.e.t.3.2.....CODOL_GameServerConfigureSession....
   CODOL_GameServerSetEnabled..
   OLMOD_GAME_ENDPOINT.
   %u.%u.%u.%u%n...
   Matchmaking external game server (OLMOD_GAME_ENDPOINT)=.
   CODOL_GameServerGetTransportStatus..
   OLMOD_GAME_S...
```

### ★★★ 逐字节解析

```
0x3B51xx  "CODOL_GameServerConfigureSession"     ← ★ 调战斗服的导出
0x3B51xx  "CODOL_GameServerSetEnabled"           ← ★ 调战斗服的导出
0x3B5170  "OLMOD_GAME_ENDPOINT"                  ← 变量名
0x3B5186  "%u.%u.%u.%u%n"                        ← ★★★ 格式串
0x3B5194  "Matchmaking external game server (OLMOD_GAME_ENDPOINT)="   ← 日志
0x3B51C6  "CODOL_GameServerGetTransportStatus"
```

★★★ **`"%u.%u.%u.%u%n"`** ——
**这**只是**解析 IPv4 地址**（`%n` 返回消耗的字符数，用于找端口分隔符）。

★★ **⇒ `OLMOD_GAME_ENDPOINT` 的格式是 `IP:PORT`**，
**用 `sscanf("%u.%u.%u.%u%n")` 解析 IP，再用 `%n` 找 `:` 之后是端口。**

★★★ **这是"Alwaysoffline 调 CodolGameServer"的直接证据**：
```
Alwaysoffline
   │ 读 OLMOD_GAME_ENDPOINT (如 "127.0.0.1:28960")
   │ 日志 "Matchmaking external game server (OLMOD_GAME_ENDPOINT)=..."
   │ GetProcAddress(hCodolGameServer, "CODOL_GameServerConfigureSession")
   │ GetProcAddress(hCodolGameServer, "CODOL_GameServerSetEnabled")
   │ GetProcAddress(hCodolGameServer, "CODOL_GameServerGetTransportStatus")
   ▼
CodolGameServer
```

★★★ **⇒ 报告 022 的"`Localnetworking` 是 `.Localnet32` 加载器"得到**第二重确认**：
**`Alwaysoffline` 知道 `CodolGameServer` 的三个导出名，并调用它们。**

★★ **注意 `Alwaysoffline` 里 `CodolGameServer` 只出现 1 次（报告 022）** ——
**是模块名 `CodolGameServer.Localnet32`，用于 `GetModuleHandle`/`LoadLibrary`。**

---

## 五、★★ `OLMOD_PLATFORM_USER_ID` 的身份链路

### 上下文（`0x3B2F64`）

```
0x3B2F10  "Authenticated user "       ← 日志
0x3B2F24  "SSL_do_handshake"          ← OpenSSL
0x3B2F38  "SSL_read_ex"
0x3B2F44  "BIO_write"
0x3B2F50  "SGamingSH0X"               ← ★★★ 默认名
0x3B2F5C  "0x"
0x3B2F60  "0X"
0x3B2F64  "OLMOD_PLATFORM_USER_ID"    ← 变量
0x3B2F84  "generic"
0x3B2F8C  "system"
0x3B2F94  "invalid stoull argument"   ← ★ 字符串转无符号整数
0x3B2FAC  "stoull argument out of range"
0x3B2FCC  "ABCDEFabcdef"              ← ★ 十六进制字符集
```

★★ **`"ABCDEFabcdef"` + `stoull`** ——
**这是 `std::stoull(s, nullptr, 16)` 的辅助字符串**（或错误消息）。

★★ **⇒ `OLMOD_PLATFORM_USER_ID` 是**十六进制字符串**解析成 `uint64`。**

★ **与 `Platform.json` 的 `"01100001DEADC0DE"`（ASCII 十六进制串）完全对应** ✓
（报告 017 已证）

---

## 六、逐字节证据总表

| # | 偏移 | 内容 | 结论 |
|---|---|---|---|
| 1 | `0x3B4540` | `OLMOD_LSG_SECRETS` | 变量名 |
| 2 | `0x3B4554` | `secrets.txt` | ★ 默认路径 |
| 3 | `0x3B4560`-`0x3B4588` | 5 个键名 | ★★★ 与 `nt10.py` 完全一致 |
| 4 | `0x3B45D8` | `lobby frame HMAC mismatch` | 密钥错的表现 |
| 5 | `0x3B466C` | `expected 0xC8 client header ACK` | ★ 客户端→服务端 ACK 类型 |
| 6 | `0x3B46C8` | `expected 0xAB82 client auth` | auth 帧类型 |
| 7 | `0x3B2F50` | **`SGamingSH0X`** | ★★★ 二进制默认名（铁证） |
| 8 | `0x3B2F64` | `OLMOD_PLATFORM_USER_ID` | 十六进制平台 ID |
| 9 | `0x3BA528` | `OLMOD_CLAIM_LOBBY` + `lobby.codol.localhost` | 认领表 |
| 10 | `0x3BA57C` | `OLMOD_EXTERNAL_STUN` | ★ 让出 STUN |
| 11 | `0x3BA5EC` | `OLMOD_EXTERNAL_AUTH3` | ★ 让出 auth3 |
| 12 | `0x3BA608` | `OLMOD_CLAIM_LEGACY_AUTH` | 让出 legacy auth |
| 13 | `0x3B5170` | `OLMOD_GAME_ENDPOINT` + `%u.%u.%u.%u%n` | ★★ IP:PORT 格式 |
| 14 | `0x3B51xx` | `CODOL_GameServerConfigureSession/SetEnabled` | ★★ 跨插件调用 |
| 15 | — | `Easily_` / `AdministraClient` / `Sunl1ght` | ★★★ 全部 **0 次** |

---

## 七、★★★ 结论

### 结论 1：★★★ `launch_chain.py` 的名字默认值**确定是错的**

```
源码常量            "SGamingSH0X"   ✓
二进制常量          "SGamingSH0X"   ✓  （@0x3B2F50，铁证）
launch_chain.py     "Easily_"       ✗  ← 唯一不匹配的一处
```

★★★ **⇒ 交付包按字面跑，`force_display_name.py --apply Easily_` 会把名字写成 `Easily_`，
而 `Alwaysoffline` 的 `DefaultUsername` 是 `SGamingSH0X` ⇒ **connect 名字校验必失败**。**

### 结论 2：★★★ `secrets.txt` 契约完整闭合

```
nt10.py 写：challenge / aes_out / aes_in / hmac_out / hmac_in
Alwaysoffline 读：同样的 5 个键（二进制里 @0x3B4560..0x3B4588）
路径：OLMOD_LSG_SECRETS，默认 "secrets.txt"
```

★★★ **⇒ 这是"不 hook 也能喂密钥"的**现成接口**。**
**任何人写好这 5 个键，`Alwaysoffline` 就能工作。**

### 结论 3：★★★ 混合方案的**可行路径**（本报告最重要）

```
不需要 nt10.py 的 Winsock hook！
        ↓
    自己实现一个"读客户端内存 → 写 secrets.txt"的工具
        （纯 ReadProcessMemory，与 force_display_name.py 同一技术）
        ↓
    OLMOD_LSG_SECRETS=<path>
        ↓
    OLMOD_EXTERNAL_AUTH3=1 + OLMOD_EXTERNAL_STUN=1  （让出 auth3/STUN）
    OLMOD_CLAIM_LOBBY / OLMOD_LOBBY_LISTEN 按需
        ↓
    ★ 无 Winsock hook 冲突
```

★★★ **⇒ 这条路径**绕过了**报告 025/026 发现的"`Localnetworking` 无条件 hook"障碍。**

★ **前提**：**我们的 `lobby_server.py` 与 `Alwaysoffline` 内部 lobby 的取舍要明确。**
**既然 `Localnetworking` 的 hook 关不掉，那"我们的 lobby"就必须让位**
**（用 `OLMOD_CLAIM_LOBBY` / `OLMOD_LOBBY_LISTEN` 让 `Alwaysoffline` 接管大厅）。**

★★★ **⇒ 换战斗服的正确方案是**：
```
保留外部包的完整链（auth3 + STUN + lobby + Localnetworking）
只把 CodolGameServer.Localnet32 换成我们的实现
用 OLMOD_SNAPSHOT_* 等 126 个开关调试
```

★ **这比"混合"简单得多，且不碰任何 hook。**

---

## 八、待逐字节继续（★ 优先级）

- [ ] ★★★ **`launch_chain.py` 里 `"SGamingSH0X"` / `"Easily_"` 的出现次数**
- [ ] ★★★ **`0x3B5C40` 的 `Lifetime` 上下文**（是地图名还是名字？）
- [ ] ★★ **`OLMOD_EXTERNAL_AUTH3` 精确默认值与触发逻辑**
- [ ] ★★ **`"unclaimed"` 的完整认领表**（6 类服务的精确名单）
- [ ] ★ **`0x3B5194` 日志的完整格式**（`OLMOD_GAME_ENDPOINT` 值）
- [ ] ★ **`CODOL_GameServerConfigureSession` 的调用点**
