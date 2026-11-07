# 02 — 游戏网络接收路径候选清单

口径:每个候选给出**准确函数边界 / 直接调用者与被调用者 / 使用的 socket API /
缓冲区与长度来源 / 关键分支 / 与 TQOS 关系 / 是否可追到游戏状态消费者 / 支持与反证**。
函数边界来自「≥3 连续 `0xCC` 后继 + 直接调用目标 + `55 8B EC` 序言」合成的函数索引
(见 `scripts/analyze_048.py`),个别处再用 `ret/int3` 人工核对。

> 严禁仅凭地址相邻、字符串相邻或命名判定业务归属。下表每条都给出可复核 RVA。

---

## 1. 候选总表

| ID | 区域 / 代表函数 | 类别 | socket API(实测) | 上游调用者数 | 与 TQOS(P1)关系 | 可追到游戏状态消费者 | 判定 |
|---|---|---|---|---|---|---|---|
| RX-CAND-001 | `0x85D2E0`/`0x85D5A0`/`0x85D870`/`0x85E6F0` | TQOS/QoS 平台 | `select`+`recv`+`send` | 1 | **本体** | 否 | `CONFIRMED_PLATFORM` |
| RX-CAND-002 | `0x87BA50`→`0x87BE00` | 通用 select+recv 原语 | `select`+`recv` | 1(P1 内部) | P1 使用 | 否 | `PLATFORM_PRIMITIVE` |
| RX-CAND-003 | `0x87C110`/`0x87D5A0`/`0x87ED70` | 腾讯 TDR 解包 | 无(纯内存) | 1 / 4 | P1 内部 | 否 | `TDR_NOT_NETFIELD` |
| RX-CAND-004 | `0x865350`..`0x865790`(P4) | **独立 socket 服务端簇** | `socket`/`bind`/`listen`/`accept`/`select`/`recv`/`send`/`sendto`/`recvfrom` | **0** | 无 | 否(调用者 0) | `UNREACHED_ENTRY` |
| RX-CAND-005 | `0x876870`..`0x876F42`(P5) | **独立 socket 客户端簇** | `socket`/`connect`/`select`/`recv`/`send`/`getsockname` | 见 §3 | 无 | 否(仅内部) | `CLIENT_TRANSPORT` |
| RX-CAND-006 | `0x1C13A0` + `0x1C1EE0` | **连接无关(OOB)命令分派/解析** | 无(经 `0x873A00`→P5) | 2 | 无 | 部分(见 `03`) | `CONFIRMED_HANDSHAKE_LAYER` |
| RX-CAND-007 | `0x1BF300` + `0x0F8FB0` + `0x0F8C50/0F8CF0/0F8D70` | 连接无关收发泵 | 间接(经 P5/队列) | 3 / 1 | 无 | 否 | `OOB_PUMP` |
| RX-CAND-008 | `0x6CBC58`/`0x6CC022` | libcurl/HTTP `select` | `select` | 0(间接) | 无 | 否 | `HTTP_NOT_GAME` |
| RX-CAND-009 | `0x6D3DE0`/`0x6D4360`/`0x6D6BE0` | 第三方网络库 `recv` | `recv`+`select` | 0 | 无 | 否 | `THIRD_PARTY` |
| RX-CAND-010 | `0x7B15E0` | `recvfrom` 包装 | `recvfrom`+`sendto` | 1(`0x873FC0`/P5) | 无 | 否 | `P5_PRIMITIVE` |
| RX-CAND-011 | `0x37FBF0` | TCP `socket`+`bind` 辅助 | `socket`/`bind`/`ioctlsocket`/`closesocket` | 1(`0x37FCD0`) | 无 | 否 | `AUX_TCP` |
| RX-CAND-012 | `0x87BE00` | TQOS recv 本体 | `recv`+`select` | 1(`0x87BA50`) | **本体** | 否 | `CONFIRMED_PLATFORM` |
| RX-CAND-013 | 低地址区 `0x053760`..`0x115xxx` | **引擎主机/游戏更新** | 无 socket(`net_disconnect` 字符串) | 2 | 与 P1 无交叉 | **部分**(`gamestateupdate`) | `GAME_LOGICAL` |
| RX-CAND-014 | `0x37DBC0` (含 `0x37DC99`/`0x37DDE8`) | 引擎 UI/状态汇(调用 `CA_GAMESTATE`+错误分派) | 无 socket | 0 | 无 | 间接 | `GAME_UI_SINK` |

> 排序:按「距游戏业务接收链的接近度」降序 → RX-CAND-006 > 007 > 005/004 > 013/014 > 其余。

---

## 2. RX-CAND-001/002/003/012(TQOS 路径,继承 046)

- 函数边界与调用者集合与 046 完全一致(见 `01` §2 复现表)。
- `0x87BE00`(RX-CAND-012)是 `select`+`recv` 的直接实现,唯一入口 `0x87BA50` 是 `jmp`。
- `0x87C110`/`0x87D5A0`(RX-CAND-003)是**纯内存** TDR 解包,不调用任何 socket API
  (本轮 157,148 个调用点中未见其体内 socket 调用)。
- **定性:平台层,不是游戏 netfield/delta 解码器。** 不得再解释为游戏协议入口。

## 3. RX-CAND-004 P4(0x865300..0x866000)——独立「服务端」socket 簇

函数边界与实测 API:

| 函数 | API | 直接调用者 |
|---|---|---|
| `0x8653D0` | `socket` | 0 |
| `0x865410` | `socket` | 0 |
| `0x865460` | `listen` | 0 |
| `0x8654A0` | `accept` + `select` | 0 |
| `0x865560` | `send` | 0 |
| `0x8655B0` | `recv` | 0 |
| `0x8655E0` | `sendto` | 0 |
| `0x865610` | `recvfrom` | 0 |
| `0x865650`/`0x865690` | `htonl`/`htons` | 0 |
| `0x8656D0` | `htons`+`ioctlsocket` | 0 |
| `0x865710` | `inet_ntoa` | 0 |
| `0x865740` | `setsockopt` | 0 |
| `0x865790` | `WSACleanup` | 0 |
| `0x865E00` | `ntohl`/`ntohs` | 0 |

- **反证:** 整簇 14 个函数的直接调用者**全部为 0**,也**没有任何 dword/VA 函数指针引用**
  (本轮对 `0x8653D0`..`0x865E00` 全区间做了 `VA` 与 `RVA` 两种形式的裸 dword 扫描)。
- **因此 P4 是一个「已存在但当前映像中不可达」的自包含 socket 服务端实现模块**
  (accept/recvfrom 齐备,像内嵌的服务器/监听器),不能证明是 in-match netchan 入口。
- 不排除的替代解释:该簇由**间接/寄存器调用**或在**第 3 节不可读区**被调用。
  → 需要 E-048-1 / E-048-4 才能进一步排除。

## 4. RX-CAND-005 P5(0x876800..0x877010)——独立「客户端」socket 簇

| 函数 | API | 边界 | 调用者 |
|---|---|---|---|
| `0x876870` | (无 socket;格式化 `%I64u`) | ..0x8768D0 | 0 |
| `0x8768D0` | `socket` + `inet_ntoa` | ..0x876920 | 1 |
| `0x876920` | `connect`+`htons`+`WSASetLastError` | ..0x876A70 | 1 |
| `0x876A70` | `closesocket` | ..0x876AB0 | 1 |
| `0x876AB0` | `select` | ..0x876B40 | 2 |
| `0x876B40` | `select` | ..0x876D30 | 2 |
| `0x876D30` | `getsockname` | ..0x876DB0 | 1 |
| `0x876D80`/`0x876DB0` | `send` | ..0x876ED0 | 1 |
| **`0x876ED0`** | **`recv`** | ..0x876F22 | **1(`0x873A0E`)** |

**缓冲区与长度来源(决定性):**
`0x876ED0` 是 `recv` 的薄包装,参数来自调用者:

```
876EE2  mov eax,[ebp+0x10]   ; arg4 = flags = 0
876EE5  mov ecx,[ebp+0x0c]   ; arg3 = len
876EE8  push 0               ; flags
876EEA  push eax             ; (与下一行合并为 flags/len 传递)
876EEB  push ecx             ; len
876EEC  push edi             ; edi = [ebp+8] = socket
876EED  call [0x00CA84E4]    ; recv(socket, buf, len, 0)
```

调用者 `0x873A00`:

```
873A00  push ebp; mov ebp,esp
873A03  mov eax,[ebp+0x0c]   ; len
873A06  mov edx,[ebp+0x08]   ; buf
873A09  push eax
873A0A  mov eax,[ecx]        ; socket = *this
873A0C  push edx
873A0D  push eax
873A0E  call 0x876ED0        ; recv wrapper(sock, buf, len)
873A13  add esp,0x0c; ret 8
```

→ **P5 确实有一条 `buf/len` 直通 `recv` 的路径**,`ecx` 是对象指针(`this->sock`)。
这条路径与 `0x873FC0` 的 `recvfrom`(`0x7B15E0`)也是同一 P5 对象族。

**未证实:** `0x873A00` 的四个上游(`0x7A20D9`/`0x7A3FD6`/`0x7A42DA`/`0x7B001C`)继续上溯后
落入 `0x7A20A0`/`0x7A41D0` 自环(`0x7A41D0` 仅被 `0x7A4491` 调用,而 `0x7A4491` 在
`0x7A41D0` 体内),**该循环之上在当前可读映像中断开**。这是 in-match 接收链的首个未证实节点。

## 5. RX-CAND-006 连接无关(OOB)命令分派 + 解析(本轮最大新发现)

### 5.1 `0x1C1EE0` —— 连接无关数据报解析器(边界 0x1C1EE0..0x1C2170)

调用者:`0x0F9135`(在 `0x0F8FB0` 体内)与 `0x1C22ED`(在 `0x1C2260` 体内)。二者都在
连接无关收发泵 `0x0F8xxx` 家族内。

关键参数与数据流:

```
1C1EF4  mov ebx,[ebp+0x0c]        ; ebx = msg_t*
1C1EF7  mov eax,[ebx+0x18]        ; dataLen
1C1EFA  add eax,[ebx+0x14]        ; + readCount
1C1F09  cmp eax,4 ; jl ...        ; 至少 4 字节,否则 msg_t[0]=1 (needmore)
1C1F25  call 0x66EFD0             ; *(char*) 读当前 token 指针
1C1F2A  mov edi,0x00DBFFA0        ; "R"
1C1F31  ... strcmp(edi, token)    ; 比较 token == "R"
1C1FCC  ... loop 逐字节 0x66EFD0 + 0x4F36C0 缓冲拷入栈缓冲 [ebp-0x408]
1C2040  call 0x5C13A0             ; -> 命令分派器
1C2112  call 0x5C13A0             ; -> 命令分派器(另一分支)
```

- **缓冲区:** `[ebx+0x08]`(data 指针)、`[ebx+0x0c]`(data 长度)、`[ebx+0x10]`、
  `[ebx+0x14]`(readCount)、`[ebx+0x18]`(dataLen)、`[ebx+0x1c]`(curOffset)——
  是一个标准 `msg_t { allowoverflow, overflowed, data, maxsize, cursize, readcount,
  bit, oob, ... }` 风格的分段读取器。
- 栈缓冲 `[ebp-0x408]`(0x400 字节)承接重新拼接的 token,再交给 `0x1C13A0`。

### 5.2 `0x1C13A0` —— 连接无关命令分派器(边界 0x1C13A0..0x1C1EE0)

- 唯一调用者:`0x1C2040`、`0x1C2112`(都在 `0x1C1EE0` 的解析体内)。
- 体内对下列**观察到的字符串**逐条 `push imm32` + `strcmp` 分派(本轮实测 xref):

| 命令 token | RVA | 比较点 RVA |
|---|---|---|
| `challengeResponse` | 0x9BFEE8 | 0x1C1685 |
| `connectReject` | 0x9BFEFC | 0x1C1756 |
| `connectResponse` | 0x9BFF0C | 0x1C17B5 |
| `heartbeatresponse` | 0x9BFF1C | 0x1C18B6 |
| `statResponse` | 0x9BFF30 | 0x1C1964 |
| `disconnect_ack` | 0x9BFF40 | 0x1C1B0B |
| `echo` | 0x9BFF50 | 0x1C1B4B |
| `keyAuthorize` | 0x9BFF58 | 0x1C1BC3 |
| `loadingnewmap` | 0x9BFF70 | 0x1C1CAB |
| `fastrestart` | 0x9BFF90 | 0x1C1DF0 |

- `connectResponse` 命中后进入子处理 `0x1C15AB`,`0x1C15AB` 的唯一调用者是 `0x1F18BE`
  (`0x1F1860` 体内,`connectResponse` 的**消费点**,读取 `hnetaddress` 并写入会话时间)。

### 5.3 关键判定

- 这是**连接无关(握手)层**,不是 in-match 消息层;它证明「客户端有一个真实的
  连接无关命令解析器 + 分派器」,但**不**证明 in-match opcode 表。
- `connectResponse` 字符 xref(RVA `0x9BFF0C`)与 046 报告一致。

## 6. RX-CAND-007 连接无关收发泵(0x1BF300 / 0x0F8xxx)

- `0x1BF300`(边界 0x1BF300..0x1BF3E0)是**发送/直连入口**:`0x1BF1C0` → 组帧 →
  `0x675310` → `0x1BF300` 内 `0x1BF3BC call 0x0F8FB0`(把包推进连接无关泵)。
  调用者:`0x1BF52D`(在 `0x1BF3E0` 体内)、`0x37976B`、`0x37C2F5`。
- `0x0F8FB0`(边界 0x0F8FB0..0x0F9155)是泵循环:从队列取包(`0x621E50`)、
  组装供 `0x1C1EE0` 的 `msg_t`,调用 `0x5C1EE0`(解析器)。
- `0x0F8C50`/`0x0F8CF0`/`0x0F8D70` 是三个「推包入队 + 触发泵」的包装。
- **这些函数的体内没有任何 socket API 调用**;它们消费的是**已经收好、已入队**的报文。
  → 断点在此:队列的生产者(真正的收包点)在当前可读映像里**没有连到这几个消费者**。

## 7. 负证据(已排除的候选)

| 候选 | 检查范围 | 排除条件 | 不能排除的解释 |
|---|---|---|---|
| P4 整簇 = in-match netchan | 14 函数全部直接调用者 + 裸 dword 指针扫描 | 调用者 0、指针引用 0 | 第 3 节不可读区 / 寄存器间接调用 |
| TDR(0x87C110/0x87D5A0)= netfield | 函数体 + 157k 调用点 | 体内无 socket;上游全属 TQOS 簇 | 无(046 已定) |
| P5 四上游 = in-match 解析入口 | `0x7A20A0`/`0x7A41D0` 上溯 | 上溯落入自环,之上断开 | 环上方的函数在第 3 节 |
| `0x376B14` 13 调用者 = in-match 收包 | 13 个上游 | 全部远离 P4/P5(046) | 间接调用/虚表 |
| 低地址区串 = 网络入口 | `gamestateupdate`/`CA_GAMESTATE` 等 | 串位于引擎逻辑/UI 区,不含 socket | 引擎自有 netchan |

**注意(遵守 046 禁令):**「某函数没有直接调用 decoder」「某串没 xref 到 P4/P5」
**不能**推出「它不是网络入口」。上表只把「已检查范围内的观察」写成负证据。
