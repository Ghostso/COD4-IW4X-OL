# COMBAT_V0_1_NEXT_001_DATAFLOW.md

> 配套：[COMBAT_V0_1_NEXT_001_CALLCHAIN.md](COMBAT_V0_1_NEXT_001_CALLCHAIN.md) ·
> [COMBAT_V0_1_NEXT_001_BLOCKER.md](COMBAT_V0_1_NEXT_001_BLOCKER.md)
> 镜像：`image_best.bin`，基址 **0x400000**；**纯静态，未启动/未附加客户端**
> ★ 本文件**只追踪运行时数据流，未修改任何密钥、booking 应答、协议字段或服务器实现**。

---

# A. endpoint 数据流

## A.1 源：21/5 findSessions 响应对象

协议侧（已冻结参考实现 `REF_LOBBY_KIT/codol_crypto.py`）给出两种地址块布局：

| 布局 | 长度 | 目标 | 来源函数 |
|---|---|---|---|
| `Normal24` | 24 B | `addr[0..3]=127.0.0.1`、`addr[4..5]=0x2071`；`addr[18..23]` 同一端点 | `build_mission_session_object` |
| `Extended67` | 67 B | `addr[0..3]=127.0.0.1`、`addr[4..5]=0x2071`；`addr[60..65]=127.0.0.1:28960`；`addr[66]=1`（NAT 分类） | `build_mission_session_object(firing_range=True)` |
| `bdCommonAddr` | 37 B | `ep + (00 FF 00 FF 00 00)×4 + ep + 01` | `build_session_record`（258B 记录） |

## A.2 消费：**本镜像内的独立发现**

桥接函数 `0x6293B0` 调用 `0xB95C50`（`0x62942B`），随后构造一个
**0x150 字节的局部地址块**并传给 battle-connect `0x470360`。

battle-connect 从该对象读取的偏移：

| 读偏移 | 指令 | 覆盖字节 |
|---|---|---|
| `+0x00` | `0x47047F rep movsd`(16 dwords) + `0x470484 movsw` + `0x470486 movsb` | 0x00..0x42 |
| `+0x43` | `0x470481 mov ecx,[eax+0x43]` | 0x43..0x46 |
| `+0x47` | `0x470471 mov edx,[eax+0x47]` | 0x47..0x4A |
| `+0x4B` | `0x47048A mov ecx,[eax+0x4b]` | 0x4B..0x4E |
| `+0x4F` | `0x470492 mov edx,[eax+0x4f]` | 0x4F..0x52 |
| `+0x53` | `0x470498 mov ecx,[eax+0x53]` | 0x53..0x56 |
| `+0x57` | `0x4704A0 mov edx,[eax+0x57]` | 0x57..0x5A |

⇒ 源对象**至少 0x5B 字节**，但被使用的有效区间是 **0x00..0x5A**。
拷贝量 69 B（0x43+2+1）与"有效 0x5B 字节"在数值上接近，说明设计上
**地址块 ≈ 0x43（67）字节 + 少量尾部字段**。

**与协议侧交叉验证**：`codol_crypto.py` 中已冻结的注释写明
"*`0xB95C50` 要求地址块长度 0x43(=67)*"。
本镜像在 `0x470360` 读到 `+0x43` 这个边界并需要 0x5B 字节，**与 67B 布局自洽**。

> ★ 这解决了 CALLCHAIN §4 的 U6 的一半：
> **67B（`Extended67`）是战斗连接真正使用的地址块布局**，
> 24B（`Normal24`）在本镜像内**没有任何消费点被找到**。

## A.3 24B / 67B 的使用位置

| 布局 | 本镜像内的消费点 |
|---|---|
| **67B** | `0x6293B0` → `0xB95C50` → battle-connect `0x470360` 读 `+0x43..+0x57`（**CONFIRMED**） |
| **24B** | **未找到**（搜索 `0x18`/`24` 作为地址块长度的校验点均未命中战斗路径） |
| **37B** | **未找到**（`0x25`/`37` 校验点未命中战斗路径） |

⇒ **INFERRED（偏强）**：战斗连接需要 67B 地址块。
但"客户端是否**拒绝** 24B 块"未被证实（未见长度校验的拒绝分支），故为 INFERRED 而非 CONFIRMED。

## A.4 endpoint → socket API 的合流

| 步骤 | RVA | 数据 |
|---|---|---|
| 地址对象构造 | `0x4704BE call 0x7BFD70` | 入参：`[ebp-0xc0]` 构造出的地址结构；`al=1` 表成功 |
| 失败分支 | `0x4704CA` | `"EXE_HOSTUNREACH"` → `0x4F82E0(msg, 2)` |
| **写入 netchan** | `0x470510` | `[ebx+0x14] = [ebp-0x60]` |
| | `0x470516` | `[ebx+0x18] = [ebp-0x5c]` |
| | `0x47051C` | `[ebx+0x1c] = [ebp-0x58]` |
| | `0x470522` | `[ebx+0x20] = [ebp-0x54]` |
| | `0x47052D` | `[ebx+0x24] = [ebp-0x50]` |
| **读出并组包** | `0x5C072E..0x5C074A` | 读 `[ebx+0x14],[+0x18],[+0x1c],[+0x20],[+0x24],[+0x28]` → 压栈 24B |
| | `0x5C075A` | `call 0x675260` |
| 投递 | `0x67512B` | `call dword ptr [0xCA8128]` |

其中 `ebx = [0x331C0C8] ^ 0xD362501F`（netchan 对象指针）。

⇒ **CONFIRMED**：endpoint 从 session 对象流入 netchan `+0x14..+0x28`，
再由每帧状态机读出，与 `"getchallenge 0 \"%s\""` 一起送入发包路径。
**这是"endpoint 被消费的函数"= `0x470360`（消费）+ `0xB95C50`（解析）。**

## A.5 `mmbook accepted` 是否参与 socket 创建

**否（不参与 socket 创建），但它是一个必要的触发+匹配条件。**

| 作用 | 证据 |
|---|---|
| 触发桥接 | `0x63285A call 0x6293B0`（在 accepted PASS 路径上） |
| 置会话状态 | `0x63280B mov byte [esi+0x288],1`、`0x632827 mov byte [0x849B61C],1` |
| 通知 listener | `0x632824` 循环 → `vtable+0x24(1,0)` |
| **携带必须匹配的 u64** | `0x6326B9` 比较 `[ebp+8]` 与 `[esi+0x3A048]`；`0x6326C8` 比较 `[ebp+0xc]` 与 `[esi+0x3A04C]`；**不等即 `0x632916 ret 0x14`** |
| 该 u64 同时出现在 **mmbook 请求**里 | `0x62F736/0x62F73C` 与 `0x62F742/0x62F748` 把预约项 `+0x168/+0x16c` 写进 A/B，再由 `0x62F7EA` 格式化成 `"mmbook %d %s %d"` |
| 不参与 socket 创建 | accepted handler 内**没有**任何 netchan 写入（`+0x14..+0x28` 的写点只在 `0x470360`） |

⇒ **accepted 只影响会话状态并作为 gate；创建 socket 所需地址由它触发的桥接写入。**

### A.5b ★ 消息里那对 u64 的来源已闭合（本次追加）

`[ebp+8]/[ebp+0xc]` 必须匹配的 `[esi+0x3a048]/[esi+0x3a04c]`，
由 **mmbook 请求构造器 `0x62F6EF`** 写入：

```
0x62F736  mov ecx,[edi+0x168]     ; 预约项 +0x168
0x62F73C  mov [esi+0x3a048],ecx   ; -> A
0x62F742  mov edx,[edi+0x16c]     ; 预约项 +0x16c
0x62F748  mov [esi+0x3a04c],edx   ; -> B
0x62F7E0  push "mmbook"           ; 0xDC6724
0x62F7E5  push "%s %d %s %d"      ; 0xDC672C
0x62F7EA  call 0x774980           ; -> "mmbook <A> <base64> <B>"
0x62F7F9  mov ecx,[esi+0x3a04c]   ; 再次取 B
0x62F809  mov ecx,[esi+0x3a048]   ; 再次取 A
0x62F801/0x62F819  mov edx,[edx+0x150] ; call edx  -> 发送请求
```

⇒ **mmbook 请求同时携带 (A,B)，而 accepted 校验也要求 (A,B)**。
即：**客户端把自己发出的预约 id 对，作为"服务端必须回显"的凭据。**
（与既有抓包 `"mmbook 796 AQAAAAAAAAA= 0"` 完全吻合。）

## A.6 不同分支是否使用不同地址/协议

| 分支 | 调用点 | 地址来源 | 协议 |
|---|---|---|---|
| accepted 路径 | `0x63285A` | 桥接 `0xB95C50` + `0x150` 局部块 | 同一 netchan；未发现差异 |
| 预约槽初始化 | `0x62CD8B` | 同一桥接 | 同一 netchan；未发现差异 |

⇒ **UNKNOWN**：没有找到"分支决定地址/协议"的代码。
同时也没有反证 —— 需在 U2（listener 注册源）闭合后才能判定。

---

# B. socket 数据流

## B.1 传输层边界（战斗 netchan 侧路径）

```
0x5C075A call 0x675260
  0x675260  snprintf/strlen -> 私有栈缓冲 [ebp-0x800]（上限 0x800）
            再把这些参数交给下一层
  0x6751F0  [ebp+0xc] 分流: 0/1 -> 直接返回 0 ; 2 -> 0x6750A0 ; 其它 -> 0x77FB80(错误)
  0x6750A0  [ebp+8]<1  -> 0x7872C08 环槽 (idx = [0x788680C] & 0x3F, 槽宽 0x4F0)
            [ebp+0x18] -> 0x7867768 表 (项 0x62C8) ; 槽内 +0x4E8/+0x4EC 记标志
  0x67512B  call dword ptr [0xCA8128]
```

- `0x675260` 被 **22 处**直接调用，是通用"网络消息投递"入口。
- `0x6750A0` **只有 1 个调用者**（`0x675234`），即路径唯一。
- `[0xCA8128]` 在全镜像被 **657 处** `call dword ptr` 引用 → 通用网络动作。

## B.2 UDP socket 创建链（独立子系统）

```
0xC5D7CA  push "udp://%s:%d"
0xC5D7DB  call 0xC3F57E              (sprintf)
0xC5D7EF  call 0xC7B8F0              (create)
            0xC7B8F0 call 0xC7B810   (解析协议 -> 类型值)
            cmp eax,-1               (失败即返回)
            0xC7B966 mov eax,[edi+4] ; dec eax ; cmp eax,6 ; jmp [eax*4+0xC7BA1C]
            0xC7B97B call 0xC7BB00               0xC7B982 call 0xC7BAF0    |  7 路协议分派
            0xC7B989 push 1 ; call 0xC7BB10  /
            0xC7B99A push 1 ; push esi ; call 0xC7BB20   (fd 选项)
            0xC7B9AE call 0xC7B510   (解析目标地址)
0xC5D8CE  call 0xC7B8F0              (第二处)
```

**地址与端口来源**：`0xB510` 解析的是 `udp://host:port` 字符串（由 `%s:%d` 从上游结构生成），
即**端口来自运行时结构，不是常量** —— 与本镜像内
**`0x2071`(28960) 立即数命中数 = 0** 的实测一致（含 `mov ax,0x2071`、`pushw`、
大小端两种编码全部为 0）。

## B.3 创建时机与触发条件

- 触发在 `0xC5D7xx` 的**连接/中继表枚举**内（循环 `0xC5D760..0xC5D7A2`，
  上限 `[ebx+0x62C]`），逐条把 "udp://%s:%d" 组装并创建。
- **与战斗 netchan 的关系 = UNKNOWN**（CALLCHAIN U3）。本镜像内没有从
  netchan 对象到 `0xC7B8F0` 的调用链证据。

## B.4 连接失败/条件不满足的分支（已定位）

| 位置 | 条件 | 结果 |
|---|---|---|
| `0x4704C6 test al,al` / `jne 0x4704D9` | 地址对象构造失败 | `0x4704CA` → `"EXE_HOSTUNREACH"` |
| `0x4704F2 test al,al` / `jne 0x470505` | 第二段解析失败 | `0x4704F6` → `"EXE_HOSTUNREACH"` |
| `0x5C0762 test al,al` / `jne 0x5C0F1B` | getchallenge 投递失败 | `0x5C076A` → `"EXE_CLIENTFAILEDTOCHALLENGE"` |
| `0x6326B9`/`0x6326C8` `jne 0x632916` | **预约 u64 不匹配** | **handler 立即 `ret 0x14`，无任何提示**（★ 见 BLOCKER） |
| `0x63268D` `je` / `0x63269B` `jge` / `0x6326AA` `jl` | 闸门 1/2/3 | 静默退出 |

---

# C. 密钥数据流（只追踪，不改动）

> ★ 任务明确要求：**不得因默认值不一致就直接得出"密钥不匹配是当前根因"**。
> 下面把"定义 / 覆盖 / 最终消费者"三者分开标注，并明确区分
> **会话密钥**、**ECDH 派生输入**、**其他字段**。

## C.1 战斗接收端（第一版战斗服）的密钥

| 项 | 位置 | 值/行为 | 等级 |
|---|---|---|---|
| 定义 | `config/combat_server.cfg` → `sv_securitykey`（留空） | 落入 `ServerConfig.SecurityKeyHex = ""` | CONFIRMED |
| 覆盖 | `ServerConfig.SecurityKey()` | 仅当 `SecurityKeyHex` 为 32 位 hex 且非全 0 才用；否则返回 `CodolProtocol.DefaultSecurityKey` | CONFIRMED |
| 最终消费者 | `ClientLogic` 构造时 `_securityKey = cfg.SecurityKey()` → `P224.DeriveTransportKey(priv, peer, securityKey)` | 参与 `SHA1(ECDH 共享x(28B 大端) ‖ securityKey(16B)) + 00000000` | CONFIRMED |
| 默认值 | `CodolProtocol.DefaultSecurityKey = Filled(0x01, 16)` | `01×16` | CONFIRMED |
| 实际运行值 | `--export-session` 实测 | `battle_security_key.txt = 01010101010101010101010101010101` | CONFIRMED |

## C.2 大厅侧的密钥

| 项 | 位置 | 值/行为 | 等级 |
|---|---|---|---|
| 定义 | `REF_LOBBY_KIT/lobby_server.py` `SEC_KEY = b"\x00" * 16` | `00×16` | CONFIRMED（源码） |
| 用途 1 | `cc.build_session_record(..., security_key=SEC_KEY)` → 写进 **258B 记录的 field 6（16B blob）** | 下发给客户端 | CONFIRMED（源码） |
| 用途 2 | 写文件 `battle_security_key.txt`（`SEC_KEY_FILE`），供战斗服读取 | 本机**未验证是否真的被战斗服读到** | UNKNOWN |
| 最终消费者 | 客户端从 21/5 记录里取出该 16B，用于与战斗服做 ECDH 派生 | **未在本镜像内定位到读取点** | UNKNOWN |

## C.3 这 16B 到底是"会话密钥"还是"派生输入"

**结论：它既不是独立的会话密钥，也不是可选的元数据；它是 ECDH 派生函数的一个显式输入。**

理由（全部来自已冻结参考实现 + 本机战斗服自测，非推断）：

1. `P224.DeriveTransportKey` 的输入是 **(服务端私钥, 对端公钥, securityKey16)**，
   输出 24B 传输密钥；战斗服自测断言"双方独立互推的传输密钥逐字节一致"。
2. 若把它换成"会话密钥"，则它必须由握手本身协商出来 —— 但它在**握手之前**就由
   21/5 session 对象下发，不符合"协商产物"的时序。
3. 因此它的角色是 **KDF 的静态盐/预共享输入**（preset input），
   与 DTLS 的 `ECDH` 共享秘密**一起**决定传输密钥。

⇒ **CONFIRMED**：16B = **ECDH 派生的静态输入（预共享盐）**，不是会话密钥本体。

## C.4 ECDH 派生与 DTLS 初始化的关系

| 阶段 | 战斗服侧 | 客户端侧（本镜像） |
|---|---|---|
| NAT 遍历 29B | `TryBuildNatReply`（首字节 0D→0C，尾部 6B 必须等于对端自身地址） | 构造点**未定位**（NAT 探针常量未在镜像内命中字节序列） |
| DTLS init 16B → cookie 38B | `TryBuildInitAck` + `FinalizeCookie`（含 [24:30] 本地地址、[10:14] HMAC 签名） | **未定位** |
| cookie+公钥 219B → ack 114B | `TryParseKeyExchange` → `P224.DeriveTransportKey` | **未定位** |
| 数据帧 `06 02 ...` | `BuildData/TryReadData`（serverTag 取 cookie[14:16]） | **未定位** |

本镜像内**存在**这些算法的证据：
`"secp224r1"`@`0xD3D628`、`"secp224k1"`@`0xD3D634`、
`"ECDH-*"`@`0xD5611D..`、`"DTLS1_*"`@`0xD55DB0..` —— 说明客户端**静态链接了
一套含 DTLS/ECDH 的密码库**（字符串形态指向 mbedTLS/OpenSSL 系）。
但这些字符串的**代码引用点未建立**（`0xD3D628` 与 `0xD55DB0` 的
`push imm32` / `mov reg,imm32` 交叉引用 = **0 命中**），
原因是该库的字符串是通过**运行时基址 + 偏移**寻址，而非立即数。

⇒ **UNKNOWN**：客户端 ECDH/DTLS 的调用点与参数装配。

## C.5 关于"两侧默认值不一致"

已实测（本机，非推断）：

| 侧 | 默认 `securityKey` |
|---|---|
| 大厅 `lobby_server.py` `SEC_KEY` | `00 00 ... 00`（16×0x00） |
| 战斗服 `CodolProtocol.DefaultSecurityKey` | `01 01 ... 01`（16×0x01） |

**但这个不一致目前不是首要阻断点，理由（三条都必须同时成立）：**

1. 若客户端根本没走到 ECDH 阶段（连 getchallenge 都没发），
   那么 securityKey 用什么值**完全不影响**结果 —— 而本任务的证据正指向这一层（见 BLOCKER）。
2. 客户端**是否真的使用** 21/5 记录里那个 16B 作为派生输入，在本镜像内**未定位**
   （C.2 最后一行 = UNKNOWN）。在拿到该证据前，不能断言"客户端会拿 00×16"。
3. 任务明确要求不得据此直接修改 —— 本节**未修改任何密钥**。

⇒ 该不一致应作为**次要风险**记录与验证，**不是**本任务定位出的首要阻断点。

---

# D. 数据流速查图

```
[21/5 响应: session 记录 258B]
   ├─ field 6: 16B securityKey ──────────────┐  (用途: ECDH 静态输入)
   ├─ 地址块 67B @ +0 ──┐                    │
   └─ SessionId u64 ──┐ │                    │
                      │ │                    │
                      │ └─> 0xB95C50 (解析) ─┴─> 0x150B 局部地址块
                      │                              │
                      │                              v
                      │                   0x470360 (battle-connect)
                      │                     读 +0x43/+0x47/+0x4B/+0x4F/+0x53/+0x57
                      │                     call 0x7BFD70 (失败 -> EXE_HOSTUNREACH)
                      │                              v
                      │                     netchan [0x331C0C8][+0x14..+0x28]
                      │                              v
                      │                    0x5C05F0 case0: "getchallenge 0 \"%s\"" + 24B
                      │                              v
                      │                    0x675260 -> 0x6751F0 -> 0x6750A0
                      │                              v
                      │                    call [0xCA8128]  (身份 UNKNOWN)
                      │
                      └─> 预约 A/B @ +0x3A048/+0x3A04C  <── 与 mmbook 消息 [ebp+8]/[ebp+0xc] 比较
                                                              (0x6326B9 / 0x6326C8)  ★ 闸门
```
