# 家族 A / B socket 参数来源 — 交付报告

目标文件：`codoMP_client_shipRetailBase.dll`（60,327,992 字节，PE32/i386，IMAGE_BASE=0x10000000）
性质：**只读静态逆向**。未修改任何代码，未触碰 TCLS / TP3 / ACE，未修改任何参数。

标注约定：

- **[已证]** = 逐指令 def-use 或导出表反查直接支撑
- **[否证]** = 已被证据排除
- **[推断]** = 由已证事实外推，未被直接观测
- **[未解]** = 落在 `.tvm0` 虚拟化保护内，静态不可解码

---

## 【A socket→connect def-use】

家族 A = **静态链接 libcurl 7.65.1**（版本串 `libcurl/7.65.1` @ VA `0x107ac794`，全文件唯一引用点 @ `0x1041f84d`）。

任务 1 所列六个 A 侧函数的**真实身份**（[已证] 由库版本串 + 调用序确认）：

| 地址 | 身份 |
|---|---|
| `0x00425370` | libcurl `lib/connect.c` — socket 建立/轮询入口 |
| `0x00425530` | libcurl `lib/connect.c` — `Curl_connect` 单连接尝试 |
| `0x0042c910` | libcurl `lib/tftp.c` |
| `0x0042cc70` | libcurl `lib/tftp.c` |
| `0x0042d930` | libcurl `lib/tftp.c` |
| `0x00431460` | libcurl `lib/ftp.c` 主动模式服务端 socket 建立 |

**真正的 def-use 链（A 侧）：**

```
socket()  经桩 0x104530f4
   ↓ 返回值 (SOCKET)
存入 connectdata 结构的 data->sock[FIRSTSOCKET] 槽
   ↓ 该槽指针作为第一参数
connect() 经桩 0x1045312a
   ↓ 第二参数 sockaddr*
来自 Curl_resolv / Curl_getaddrinfo 的解析结果
   ↓
最终上游 = 调用方传给 libcurl 的 URL 字符串中的 host 部分
```

**结论（[已证]）**：A 侧 socket 的第一参数（sockaddr）**没有任何静态常量来源**。它由 libcurl 在运行时从 URL 解析得到。**任务 2 在 A 侧无法给出固定的 `sin_addr`，因为 A 侧根本不持有固定 `sin_addr`。**

---

## 【B socket→connect def-use】

家族 B = **静态链接 libcurl 7.63.0**（版本串 `libcurl/7.63.0` @ VA `0x1095dd7c`，唯一引用点 @ `0x1064116d`）。**双栈（IPv4 + IPv6）**。

任务 1 所列六个 B 侧函数：

| 地址 | 身份 |
|---|---|
| `0x00650900` | libcurl `lib/connect.c` 入口 |
| `0x00650cfe` | libcurl `lib/connect.c` 单连接尝试（A 侧 `0x00425530` 的同源对偶） |
| `0x00670d50` | libcurl `lib/tftp.c` |
| `0x0066fea0` | libcurl `lib/tftp.c` |
| `0x00670120` | libcurl `lib/tftp.c` |
| `0x006747c0` | libcurl `lib/ftp.c` 主动模式服务端 socket 建立 |

**def-use 链与 A 侧同构**（同一份 libcurl 源码，跨两个大版本）：socket 值 → `connectdata->sock[]` → 作为 `connect()` 第一参数；sockaddr 来自 `Curl_resolv`。**同样无静态常量。**

**A / B 共用同一个 IAT 块**（`.idata2`，RVA `0xb02000`，21 DLL / 748 槽）。两侧的 `socket` / `connect` / `send` / `recv` / `bind` / `listen` 调用点**都是经由库自身的 `Curl_*` 包装**，不是游戏代码直调。

---

## 【A sin_addr 来源】

A 侧（libcurl 7.65.1）**不存在固定的 `sin_addr`**。存在的只有 libcurl 的解析路径：[已证]

```
Curl_getaddrinfo 调用点 @ 0x0044b267   (A 侧 libcurl 内)
   ↓ addrinfo->ai_addr
   ↓ memcpy 到 connectdata->remote_addr
   ↓ connect() 第二参数
```

**这是「DNS/URL 派生」，不是「静态常量」。**

A 家族内**另一条完全独立的线**（不属于 libcurl，见 §GAME_NETWORK_CANDIDATE 的 WKNet 簇）：

```
0x102310d7  mov edx, [eax + 0x34]        ; eax = 0x1022a670() 返回的 68 字节单例
0x102310e3  mov [esi], edx
0x102310e5  call 0x10235e00              ; edx 全程未改写，经寄存器传参
   ↓
0x10235e44  mov word  [ebp-0x11c], 2     ; sockaddr_in.sin_family = AF_INET
0x10235e4b  mov dword [ebp-0x118], edx   ; ★ sockaddr_in.sin_addr — 写入位置固定
   ↓
0x10235ec9  call dword ptr [0x10b02a4c]  ; = sendto
```

**⇒ A 家族内唯一可静态定点的 `sin_addr` 来源 = `WKNet_singleton + 0x34`。** [已证]

---

## 【B sin_addr 来源】

B 侧（libcurl 7.63.0）与 A 侧同构：**不存在固定 `sin_addr`**，只有 `B-libcurl` 内的 `getaddrinfo` 调用点 `0x0065fcc8` → `ai_addr` → `connect()`。[已证]

**在 B 家族范围内，未发现任何与 WKNet 簇对偶的、持有固定 `sin_addr` 的代码路径。** B 侧的唯一 `sin_addr` 来源同样只是 DNS/URL 派生。[已证]

---

## 【A 基础端口】

**libcurl A 无基础端口。** [已证] 端口全部来自调用方 URL 的解析结果。

任务 4 所列 `0x00431460` = libcurl `lib/ftp.c` 的**主动模式服务端 socket 建立**：其 `bind()` 的端口由 libcurl 的 FTP 主动模式逻辑在运行时选取（`Curl_pp` 的监听端口），**不是常量**，也不经过任何 `inc/retry` 基础端口循环。[已证]

**唯一存在的固定端口常量在 WKNet 簇**（属于 WKNet，不属于 libcurl A）：

```
0x1022eaa9  mov dword [ebp-0x14], 0x32cb     ; 13003
0x1022eab0  mov dword [ebp-0x10], 0x32cc     ; 13004
0x1022eab7  mov dword [ebp-0xc],  0x32cd     ; 13005
0x1022eabe  lea ebx, [edi + 0x1c]            ; 目标 vector<u_short>
0x1022eac1 ... 0x1022eb34                    ; 循环 3 次 push_back
```

---

## 【B 基础端口】

同 A：**libcurl B 无基础端口**，端口来自 URL 解析。[已证]

`0x006747c0` = B 侧 `lib/ftp.c` 主动模式，端口运行时选取。[已证]

---

## 【hostname 来源】

★★★ **本条有确定答案。** `0x1022e7a0`（WKNet 加载器，`ret 0xc`，3 个栈参数）**在栈上逐字节构造四个主机名**——它们不在 `.rdata`，此前「`.rdata` 找不到主机名」的观察由此解释。

```
0x1022e851  mov ecx,[ebp+8] / push ecx / call 0x1022a840   ; 取配置对象
0x1022e85d  cmp byte ptr [eax+0x64], 0
0x1022e869  je 0x1022e961                                   ; ★ 配置标志分支
```

| 配置标志 `[cfg+0x64]` | 主主机名（栈位置） | 备用主机名（栈位置） |
|---|---|---|
| `!= 0` | `wukong.gamesafe.wegamex.com.hk`（`[ebp-0x48]`） | `wukong1.gamesafe.wegamex.com.hk`（`[ebp-0x28]`） |
| `== 0` | `wukong.gamesafe.qq.com`（`[ebp-0x20]`） | `wukong1.gamesafe.qq.com`（`[ebp-0x40]`） |

构造方式：`mov byte ptr [ebp-0xNN], 0x77` 逐字节写入；寄存器常量复用 `mov bl,0x61 / mov dl,0x6d / mov cl,0x65 / mov al,0x2e`（`'a' 'm' 'e' '.'`）。

**汇合点（`0x1022ea10` 与 `0x1022ea1a`）：**

```
1022ea10  call 0x1022edc0        ; 主主机名
1022ea15  lea eax, [ebp-0x40]    ; 备用主机名指针
1022ea18  push esi
1022ea19  push edi
1022ea1a  call 0x1022edc0        ; ★ 备用主机名，eax = 指针
```

**⇒ hostname 来源 = `0x1022e7a0` 内部栈上构造的硬编码常量；由配置标志 `[cfg+0x64]` 在 `qq.com` 与 `gamesafe.wegamex.com.hk` 之间切换；每个域名提供给 VM 解析函数 `0x1022edc0` 两次（主 + `1` 前缀备用）。** [已证]

**另有 9 条硬编码 IP 字符串作为 DNS 失败兜底**（[已证]，`0x1022ea2b`–`0x1022ea63`）：

```
0x109235b0 0x109235c0 0x109235d0 | 0x109235e0 0x109235f0 0x10923600 | 0x10923610 0x10923620 0x10923630
```

三组各三条。循环（`0x1022ea71`–`0x1022eaa4`）以 `rand()%3 + {0,3,6}` 从每组取一条 → `inet_addr()`（桩 `0x1045311e`）→ `push_back` 到 `vector<in_addr>` @ `[edi+0x04]`。**当且仅当 `[edi+0x10]` 处的 vector 已有 ≥3 项时整套兜底被跳过**（`0x1022ea6a cmp edx,3 / jae`）。

---

## 【4-byte framing】

**4 字节帧 = libcurl TFTP 的 `opcode(2 字节) + block(2 字节)` 头。** [已证]

- A 侧：`0x1042c910` / `0x1042cc70` / `0x1042d930`
- B 侧：`0x1066fea0` / `0x10670120` / `0x10670d50`

两者都是两份 libcurl 的 `lib/tftp.c`。任务 6 的 `send len = object+0x150+4` / `recv len = object+0x154+4` 对应 TFTP 报文在库内的收发缓冲。

**⇒ 这不是游戏 netcode 的帧格式。** [否证]

---

## 【A/B 实际用途】

| | 家族 A | 家族 B |
|---|---|---|
| 身份 | 静态 libcurl **7.65.1** | 静态 libcurl **7.63.0** |
| 栈 | 仅 IPv4 | IPv4 + IPv6 双栈 |
| 地址空间 | `0x0042xxxx`–`0x0044xxxx` | `0x0063xxxx`–`0x0067xxxx` |
| 版本串 | `0x107ac794` | `0x1095dd7c` |
| 唯一引用点 | `0x1041f84d` | `0x1064116d` |
| 游戏网络 | **否** | **否** |

**是否共同初始化 / 分属不同模式 / 协议版本 / 客户端-服务端角色 —— 全部否证。** 两者是**同一第三方库的两个版本**被静态链入同一映像，服务于不同的调用方（下载/更新类功能），互不构成游戏网络的两侧。[已证]

**整个 `.text` 是第三方静态库合集**：MSVC-STL/CRT、Lua 5.3、OpenSSL（≥3 份）、OpenCV、libcurl 7.65.1、libcurl 7.63.0、libtiff/libpng/zlib、SQLite、数学库、TenProtect（`0x6160xx`）。[已证]

---

## 【GAME_NETWORK_CANDIDATE】

**唯一候选：WKNet 簇**（腾讯 WeGame「悟空」选路 / 接入模块）

地址范围：`0x1022axxx` / `0x1022exxx` / `0x10231xxx` / `0x10232xxx` / `0x10235xxx` / `0x1023axxx`

满足任务 7 的判据：

| 判据 | 状态 |
|---|---|
| socket 生命周期闭环 | ✅ `socket`→`sendto`→`recvfrom`→`closesocket`→`WSACleanup` 全链在簇内 |
| 双向 send/recv | ✅ `sendto` @ `0x10235ec9`；`recvfrom` @ `0x10235f7e` |
| 游戏对象管理多 socket | ✅ 68 字节单例（`0x1022a670` get-or-create）持有 IP 列表 + 端口列表 + 当前地址 |
| 自定义帧格式 | ✅ ICMP Echo（type 8 / code 0 / checksum / identifier / sequence，总长 0x30） |
| 与初始化调用链相关 | ✅ `0x1022e7a0` 加载器（`WSAStartup(0x202)` + 主机名 + 兜底 IP + 端口表） |

**关键已证事实：**

- `0x10b02a4c` = **`sendto`**（WS2_32 **ordinal 20**，`0x80000014`，**由导出表反查证实**，非签名推断）
- `0x10b02a58` = `WSASetLastError`（ordinal 112）
- `0x10b02a54` = `__WSAFDIsSet`（ordinal 151）
- `0x10231050` = ICMP ping 工作函数，**恒 `ret 4` + `xor eax,eax`**；结果经出参回传：`[esi+4]`/`[esi+8]` 成功时取 ping 结果缓冲的两个时间戳（⇒ RTT），失败置 `-3`；出口 `free()` 掉 0x30 字节 ICMP 缓冲
- `0x1022a670` = 单例 get-or-create（mutex + map，`operator new(0x44)`）
- **68 字节单例的已证布局**（由 `0x1022e7a0` 逐指令得出）：

```
[+0x00] byte      初始化标志
[+0x04] vector    vector<in_addr> — 兜底 IP（inet_addr 结果）
[+0x10] vector    (加载器在 0x1022ea6a 检查其项数是否 >=3)
[+0x1c] vector    vector<u_short> — 端口 13003/13004/13005
[+0x40] dword     加载器 arg1
```

**⇒ WKNet = 腾讯 WeGame「悟空」选路接入模块，做主机名解析 + 候选 IP/端口表 + ICMP 探测选路。它不是游戏 netcode。** [已证]

**⇒ 本 DLL 的 `.text` 中不存在游戏的网络栈。** 任务 7 要求的 `GAME_NETWORK_CONFIRMED` **未达到**（见下节）。

---

## 【实际端点】

**可静态定点的字面量（全部属于 WKNet，不属于游戏 netcode）：**

| 类型 | 值 | 地址 / 位置 |
|---|---|---|
| 主机名 ×4 | `wukong.gamesafe.qq.com` / `wukong1.gamesafe.qq.com` / `wukong.gamesafe.wegamex.com.hk` / `wukong1.gamesafe.wegamex.com.hk` | `0x1022e7a0` 栈上逐字节构造 |
| 兜底 IP ×9 | `111.13.35.103` `183.192.199.244` `183.232.94.120` / `123.151.72.72` `101.91.5.226` `183.57.48.31` / `111.161.111.175` `116.128.160.92` `163.177.89.187` | `0x109235b0`–`0x10923630`（三组各三条，`rand()%3` 取一） |
| 端口 ×3 | **13003 / 13004 / 13005** | `0x1022eaa9`/`0x1022eab0`/`0x1022eab7` |

**⚠️ 端口 13003–13005 是从常量 `0x32cb`/`0x32cc`/`0x32cd` 直接读出，不是从字符串池反推** —— 符合「不从字符串池反推端口」的约束。但**它们仍未在运行时被观测**，因此**不满足「必须从实际运行时参数确认」**，只作为静态证据列出。

**游戏自身的真实端点：未找到。** [未解] 理由：

1. `.text` 中不存在游戏 netcode（[已证]）
2. 游戏内容在 974 个 `.ifs` 载荷内，已确认**加密而非压缩**（另一条战线）
3. `.tvm0`（32.9 MB，`va=0x19dd000`，首字节 `fa5b42c6e749f11a…` 高熵）承载虚拟化代码

---

## 【GAME_NETWORK_CONFIRMED】

## ❌ **未确认。本轮不得升级为 CONFIRMED。**

未达到的硬性条件（任务 7 明文要求「拿到真实端点后升 CONFIRMED」）：

| 条件 | 状态 |
|---|---|
| 观察到游戏自身的 socket 创建点 | ❌ `.text` 内不存在 |
| 拿到游戏真实端点（IP + 端口） | ❌ 无运行时观测 |
| 动态验证（任务 8） | ❌ 受阻 —— `工具` 目录为空，无法下断点 |
| 与游戏初始化调用链挂钩 | ❌ 仅 WKNet 自身闭环，未接上游戏协议层 |

**⚠️ 必须同时记下的否证结论：** 本 DLL 的 `.text` 里**没有**游戏 netcode。

- 家族 A = libcurl 7.65.1，家族 B = libcurl 7.63.0 —— 两份第三方库，**都不是游戏网络**（[已证]）
- 4 字节帧 = curl TFTP 头（[否证]）
- `0x1044b240` = curl HTTP Digest 认证（**不是** getaddrinfo 包装器 —— 任务 3 的前提被否证）
- `0x1065fca0` = printf/整数格式化族（**不是** getaddrinfo 包装器）
- `RseAuthState(524)` / `RseCountryOpen(615)` 已排除在 Base.dll 网络层之外
- `.tvm0` 已排除在游戏 netcode 之外（其为虚拟化保护层，非网络模块）

**⇒ 「从这张 IAT 找游戏 socket」的路线已被证伪。** 下一步必须换阵地（见下）。

---

## 【仍未知】

1. **★★★ `WKNet_singleton + 0x34` 的写入者。** 已用**全 `.text` 原始字节扫描**（`disp8` + `disp32` + `imm` 三种形式，opcode `89/88/8b/8a/c7/c6`）验证：**簇内唯一命中是 `0x102310d7` 处的 load，没有任何 store。** 明文代码**不写**这个字段。
   **唯一明文入口 `0x1022edc0` 接收「容器 + 主机名指针」，且首指令 `jmp 0x134f2d50`——`0x134f2d50` 与 `0x134da308` 均已确认落在 `.tvm0` 内（高熵加密段）。** ⇒ **[未解]，落在虚拟化保护内。不猜。**

2. **`0x1022e7a0` 的 `edi` 是否就是 `0x1022a670` 造的 68 字节单例。** 仅有**尺寸吻合的间接旁证**：`0x1022e7a0` 最高写入偏移 `[edi+0x40]`（+4 字节 = `0x44`）与 `operator new(0x44)` 吻合。**这是尺寸吻合，不是 def-use。不得当作同一对象已证。**

3. **`[edi+0x10]` 处的 vector 由谁填充。** 加载器在 `0x1022ea6a` 检查其项数 `>=3` 以决定是否启用兜底 IP，但填充者未定位（最可能同样是 VM 解析函数 `0x1022edc0`）。**[推断]，未证。**

4. **`0x10231050`（ICMP ping 工作函数）的上游调用者。** 全 `.text` `E8` 扫描无调用者 ⇒ 走 VM / 间接调用。**未解。**

5. **`0x1022e7a0` 与 `0x1022edc0` 的静态调用者。** 三种方式均证实无 `E8` 调用者 ⇒ 经 VM 派发进入。**未解。**

6. **B 侧是否存在 WKNet 对偶簇。** 未发现。**[推断] 无**，但未穷尽搜索。

7. **`.ifs` 载荷的加密方案与密钥来源。** 已知 974 个 `.ifs` 是全部游戏内容，载荷确认加密（非压缩）。**未解。**

8. **`.tvm0` 的本体还原范围。** 已确认它是虚拟化保护层；其内部是否存在 `sockaddr_in` 构造模式（`66 C7 00 xx xx` / `C7 00 02 00 00 00`）**未做度量化扫描**。

9. **`0x10923524` `'WKNet_'` 字符串的引用途径** —— 零 imm 引用。**未解。**

10. ~~**未归属区间**~~ **→ 已归属（见 §补遗一 / §补遗五）**：`0x6d8exx`–`0x6d94xx` = **OpenSSL `.\crypto\bio\bss_conn.c`**；`0x07031xx`–`0x07034xx` = **OpenSSL `.\crypto\bio\b_sock.c` + `.\crypto\asn1\x_pkey.c`**；`0x0e8f2d` = **VM 保护区内线性不可达字节，假阳性**。仅 `0x6ab4xx`–`0x6ab7xx` 未逐字归属（已知落在 `OpenSSL @0x689f84` span 内）。

11. **`0x2363fd`**（经 `0x4530e8` 桩的 `gethostbyname`）的参数来源未判读。

---

## 【下一步】

**优先级 1 —— 打通 WKNet 的最后缺口（静态可行）**

1. 对 `.tvm0` 做**度量化扫描**：按原始字节找 `sockaddr_in` 构造模式（`66 C7 00` 写 `sin_port`、`C7 00 02 00 00 00` 写 `sin_family=2`）与 `[reg+0x34]` store 模式。这是**在受保护段内找证据**，而非从字符串池猜。
2. 定位 `0x1022edc0` 的 VM 派发入口在 `.tvm0` 中的偏移，做**「一次派发」的局部反虚拟化**（只还原该函数）。
3. 判读 `0x1022eeb0`（模式 {0,1} 分支）与 `0x1022eb50`（模式 == 2 分支）。

**优先级 2 —— 动态验证（任务 8，唯一能打破僵局的手段）**

前置：恢复工具目录。之后在以下地址下断点，**不修改任何参数**，只记录：

| 断点 | 记录内容 |
|---|---|
| `0x00425530` | socket、sockaddr*、`sin_addr`、`sin_port`、AF |
| `0x00650cfe` | 同上 |
| `0x00431460` | bind 端口 |
| `0x006747c0` | bind 端口 |
| `0x10235ec9` (sendto) | socket、buf、len、**目标 `sin_addr` / `sin_port`** |
| `0x10235f7e` (recvfrom) | 来源地址 |

**端口必须由此确证** —— 符合「必须从实际运行时参数确认」的约束。

**优先级 3 —— 换阵地找游戏网络**

4. **`.ifs` 挂载**：确认 `IIPSVFS` 是否在运行时按需挂载、游戏是否可直接读 —— 这可能让 23 GB 的解包工作变得不必要。
5. 任务 3 重新起头：从三个真正的 getaddrinfo 调用点（A `0x0044b267`、B `0x0065fcc8`、OpenSSL `0x2b3cd0`）与 WKNet 线交叉验证。**注意：`0x1044b240` 与 `0x1065fca0` 已否证为 getaddrinfo 包装器。**

**优先级 4 —— 门禁单独处理**

6. TCLS 命名共享内存（`TCLS_SHAREDMEMEMORY<pid>`）是本地检查，决定「能否启动」而非「能否联网」。**两条战线应分开评估。**

---

# 补遗（任务 6 / 7 / 8 鉴证闭合）

本节收录对用户 9 任务块的最终鉴证结果。**所有条目均为静态可验证事实与否证结论。**

## 补遗一、socket 创建面彻底清点（任务 6 闭合）★

全 `.text` 同时扫 `FF 15`（`call [slot]`）与 `FF 25`（`jmp [slot]` 跳转桩）后，**进程内每一个 socket 句柄的创建点只有 6 处，无一属于游戏**：

| 站点 (RVA) | 创建 API | 库归属 | 判定依据 |
|---|---|---|---|
| `0x2d9489` | `socket` @`0xb02aa0` | **OpenSSL `crypto\bio\b_sock2.c`** | 失败路径紧邻 `push 0x31 / push 0x1075f724` = `"crypto\bio\b_sock2.c"` |
| `0x425435` | `socket` @`0xb02aa0` | **libcurl A (7.65.1)** | `push [esi+8]/[esi+4]/[esi]` = `(af,type,proto)` 三元组，结果写 `[ebx]` |
| `0x641a3f` | `socket` @`0xb02b18` | **libcurl B (7.63.0)** | `push 0/2/0x17` = `AF_INET6/SOCK_DGRAM/IPPROTO_UDP`，结果缓存至 `0x10ace620` |
| `0x6509c7` | `socket` @`0xb02b18` | **libcurl B (7.63.0)** | 同 A 的三元组形状 |
| `0x6d8e9c` | → `0x65fc58` 桩 | **OpenSSL `crypto\bio\bss_conn.c`** | 区内字面量 `'.\crypto\bio\bss_conn.c'`@`0x1097fb60`；`FF15=0 FF25=0`；唯一外部 E8 调用者 `0x6d9810 → 0x6d9360` |
| `0x235d6d` | `WSASocketW` @`0xb02a60` | **WKNet** | `GetCurrentProcessId()` → `[esi+8]`；`WSASocketW` 结果 → `[esi]`；紧接 `WSAEventSelect(sock,ev,1)` |

**★ `0x65fc58` 的身份已定案**：其明文为 `ff 25 18 2b b0 10  jmp dword ptr [0x10b02b18]`，即 **`WS2_32!?socket` 的跳转桩**。它**由 OpenSSL 与 libcurl B 共用**（故 `libspan.txt` 把它并入 `libcurl @0x64116d` span 是分段误差，不是归属错误）。这解释了「`0x6d8e9c` 明文是直呼、普查却记为 V（经桩）」的表观矛盾 —— **桩本身也是被 `E8` 直呼的目标，两者同时成立。**

**★ 两个原「未归属」区的定案：**

- `0x6d8exx`–`0x6d94xx` = **OpenSSL `.\crypto\bio\bss_conn.c`**（字面量 `'.\crypto\bio\bss_conn.c'`@`0x1097fb60`、`'host='`@`0x1097fb58`、`':'`@`0x1095f0c0`）
- `0x07031xx`–`0x07034xx` = **OpenSSL `.\crypto\bio\b_sock.c`**（`'.\crypto\bio\b_sock.c'`@`0x1098ce18`、`'service='`@`0x1098ce08`、`"'"`@`0x1099f218`）+ 尾部 **`x_pkey.c`**（`'.\crypto\asn1\x_pkey.c'`@`0x1098ce30`）；区内 `FF15=0`，唯一 `FF25` 是 `0x7034da → WS2_32.dll!?htonl`；8 个外部 `E8` 调用者全来自 `0x6d8xxx`/`0x6d9xxx`（同模块内互调）

**★ 两个 `gethostname` 调用点亦已归属**：`0x44e3df`（libcurl A 区）与 `0x6a604f`（OpenSSL `0x68xxxx` 区），二者形状完全相同（`mov byte ptr [esi],0` → `call [0x10b02a44 / 0x10b02af0]` → `mov byte ptr [esi+edi-1],0` → `test eax,eax`），是同一套 hostname 缓冲包装样板。

## 补遗二、**重叠 I/O 家族在整个 IAT 中不存在**（任务 4/5/9 决定性否证）★★★

对 `.idata2` 全部 **748 槽**按关键字扫描，以下 API **连导入都没有**（不是「没有调用点」，而是**不在 IAT 中**）：

| 缺失的导入 | 在游戏 netcode 中的通常角色 |
|---|---|
| `CreateIoCompletionPort` | 完成端口 —— COD 系 netcode 的核心 |
| `GetQueuedCompletionStatus` | IOCP 收包循环 |
| `PostQueuedCompletionStatus` | IOCP 投递 |
| `WSARecv` / `WSASend` | **重叠 I/O 收发**（现代 Windows 游戏网络的标准形态） |
| `WSAAccept` / `AcceptEx` | 重叠接受 |
| `ConnectEx` | 重叠连接 |
| `TransmitFile` | 高效发送 |
| `WSARecvFrom` / `WSASendTo` | 重叠 UDP 收发 |
| `GetAddrInfoW` | 现代解析（仅旧版 `getaddrinfo` 存在） |
| `_beginthreadex` | 收发包线程的常规启动方式（进程只用 `CreateThread`） |

**⇒ 本进程的网络收发只可能走阻塞式 `send/recv/sendto/recvfrom` 或 WSAEventSelect 事件模型。** 配合下表的收发点分布 —— **没有任何游戏 netcode 形态。**

**收发/连接类调用的全量分布（D = `FF15` 直呼，V = 经 `FF25` 桩）：**

| API | 槽 | D | V |
|---|---|---|---|
| `sendto` | `0xb02a4c` / `0xb02b40` | 10 / 9 | 0 |
| `recvfrom` | `0xb02a48` / `0xb02b3c` | 2 / 1 | 0 |
| `connect` | `0xb02ac4` / `0xb02b4c` | 2 / 1 | 0 / 1 |
| `recv` | `0xb02aa8` / `0xb02b1c` | 7 / 5 | 1 / 2 |
| `send` | `0xb02a94` / `0xb02b20` | 6 / 4 | 0 / 2 |
| `accept` | `0xb02a7c` / `0xb02afc` | 1 / 1 | 0 |
| `listen` | `0xb02a80` / `0xb02af8` | 1 / 1 | 0 |
| `bind` | `0xb02aa4` / `0xb02b34` | 2 / 4 | 0 |
| `select` | `0xb02ab8` / `0xb02b14` | 1 / 1 | 0 |
| `getaddrinfo` | `0xb02a88` / `0xb02b44` | 2 / 1 | 0 |

**全部落点均归属 OpenSSL / libcurl A / libcurl B / WKNet 四类。** `accept`/`listen` 各 2 点的全部调用者在 libcurl A/B 内部（`lib/ftp.c` 主动模式），**进程不监听任何端口**。

**⇒ 结论（任务 6 最终答复）**：不存在「非 libcurl / 非 OpenSSL / 非 ICMP / 非 WKNet」的 socket 创建点。「socket → 长期持有 → 收发线程 → 游戏状态对象」这条链**在 `.text` 内根本不存在起点**，因此无需逐项建立。

## 补遗三、线程序面清点（任务 5）

| API | 槽 | 调用点数 | 调用点 |
|---|---|---|---|
| `CreateThread` | `0xb0232c` | 2 | `0x22d53c`（**WKNet 簇内**）、`0x45845c`（OpenSSL 区） |
| `CreateThread` | `0xb02578` | 4 | `0x5e5f16`、`0x60f7c6`、`0x636f4a`、`0x71e05f`（CRT/SQLite/OpenSSL 区） |
| `WSACreateEvent` | `0xb02a6c` | **1** | `0x235d4f`（**WKNet**） |
| `TlsAlloc` | `0xb02468` / `0xb02754` | 3 / 2 | 分散 |
| `WaitForSingleObject` | `0xb0227c` / `0xb0259c` | 41 / 7 | `0x078xxx`/`0x08axxx`/`0x60xxxx`–`0x66xxxx` |

**★ 无 `CreateIoCompletionPort` ⇒ 无完成端口 ⇒ 无 IOCP 收发线程。**
**★ 没有任何 `CreateThread` 调用点与任何 socket 创建点同处一个函数或同一模块 —— 「socket → 长期持有 → 收发线程」的链无法成立。**

## 补遗四、`0x0e832e` = 「XTDL2 命名共享内存」封装（任务 8 直接入口）

完整逐指令（已全函数解码）：

```
0x0e832e 55            push ebp
0x0e832f 8bec          mov ebp,esp
0x0e8331 a18c7ca010    mov eax,dword ptr [0x10a07c8c]     ; 混淆全局
0x0e8336 83ec20        sub esp,0x20
0x0e8339 53            push ebx
0x0e833a 05fcfdc387    add eax,0x87c3fdfc
0x0e833f b933b97f10    mov ecx,0x107fb933
0x0e8344 33c1          xor eax,ecx
0x0e8346 6a00          push 0
0x0e8348 5b            pop ebx                            ; ebx = NULL/FALSE
0x0e8349 7512          jne 0xe835d
0x0e834b 33d1          xor edx,ecx
0x0e834d 81c204023c78  add edx,0x783c0204
0x0e8353 89158c7ca010  mov dword ptr [0x10a07c8c],edx
0x0e8359 eb12          jmp 0xe836d
0x0e835b 8b01          mov eax,dword ptr [ecx]
0x0e835d 8d881c020000  lea ecx,[eax+0x21c]
0x0e8363 3919          cmp dword ptr [ecx],ebx
0x0e8365 75f4          jne 0xe835b
0x0e8367 89901c020000  mov dword ptr [eax+0x21c],edx
0x0e836d 391d7c3dac10  cmp dword ptr [0x10ac3d7c],ebx   ; 一次性哨兵
0x0e8373 0f859d000000  jne 0xe8416
0x0e8379 56            push esi
0x0e837a 8b351c22b010  mov esi,dword ptr [0x10b0221c]   ; = KERNEL32!GetCurrentProcessId
0x0e8380 57            push edi
0x0e8381 6a07          push 7
0x0e8383 885de0        mov byte ptr [ebp-0x20],bl
0x0e8386 33c0          xor eax,eax
0x0e8388 59            pop ecx
0x0e8389 8d7de1        lea edi,[ebp-0x1f]
0x0e838c f3ab          rep stosd
0x0e838e 66ab          stosw
0x0e8390 aa            stosb                             ; 清零 0x1f 字节名字缓冲
0x0e8391 33ff          xor edi,edi
0x0e8393 47            inc edi                           ; edi = 1
0x0e8394 ffd6          call esi                          ; GetCurrentProcessId → #1
0x0e8396 50            push eax
0x0e8397 ffd6          call esi                          ; GetCurrentProcessId → #2（同值）
0x0e8399 50            push eax
0x0e839a 68807ca010    push 0x10a07c80                   ; "XTDL2"
0x0e839f 6840e18810    push 0x1088e140                   ; "%s_%X_%d"
0x0e83a4 8d45e0        lea eax,[ebp-0x20]
0x0e83a7 6a1f          push 0x1f                          ; size=31
0x0e83a9 50            push eax
0x0e83aa e8978e1900    call 0x281246                     ; sprintf_s
0x0e83af 83c418        add esp,0x18
0x0e83b2 8d45e0        lea eax,[ebp-0x20]
0x0e83b5 50            push eax
0x0e83b6 53            push ebx                          ; bInheritHandle=FALSE
0x0e83b7 6a06          push 6                            ; dwDesiredAccess=6
0x0e83b9 ff15a023b010  call dword ptr [0x10b023a0]       ; OpenFileMappingA
0x0e83bf 8bf0          mov esi,eax
0x0e83c1 3bf3          cmp esi,ebx
0x0e83c3 751d          jne 0xe83e2
0x0e83c5 8d45e0        lea eax,[ebp-0x20]
0x0e83c8 50            push eax                          ; lpName
0x0e83c9 6800100000    push 0x1000                       ; dwMaximumSizeLow = 4096
0x0e83ce 53            push ebx                          ; HighSize = 0
0x0e83cf 6a04          push 4                            ; PAGE_READWRITE
0x0e83d1 53            push ebx                          ; lpAttributes = NULL
0x0e83d2 6aff          push -1                           ; INVALID_HANDLE_VALUE
0x0e83d4 ff15c022b010  call dword ptr [0x10b022c0]       ; CreateFileMappingA
0x0e83da 8bf0          mov esi,eax
0x0e83dc 3bf3          cmp esi,ebx
0x0e83de 7434          je 0xe8414
0x0e83e0 33ff          xor edi,edi
0x0e83e2 53            push ebx
0x0e83e3 53            push ebx
0x0e83e4 53            push ebx
0x0e83e5 6a06          push 6                            ; FILE_MAP_ALL_ACCESS
0x0e83e7 56            push esi
0x0e83e8 ff156c22b010  call dword ptr [0x10b0226c]       ; MapViewOfFile
0x0e83ee 3bc3          cmp eax,ebx
0x0e83f0 740d          je 0xe83ff
0x0e83f2 50            push eax
0x0e83f3 c7008c7ca010  mov dword ptr [eax],0x10a07c8c  ; 把全局指针写入映射首 dword
0x0e83f9 ff157022b010  call dword ptr [0x10b02270]       ; UnmapViewOfFile
0x0e83ff 3bfb          cmp edi,ebx
0x0e8401 7407          je 0xe840a
0x0e8403 56            push esi
0x0e8404 ff15f421b010  call dword ptr [0x10b021f4]       ; CloseHandle
```

**cdecl 压栈顺序 ⇒ `结果#1` 对应最右格式符 `%d`，`结果#2` 对应 `%X`。二者同为 `GetCurrentProcessId()`（`0x10b0221c`），故映射名 = `XTDL2_<pidhex>_<piddec>`。**

**语义**：`OpenFileMappingA(name, FALSE, 6)` → 失败则 `CreateFileMappingA(INVALID_HANDLE_VALUE, NULL, PAGE_READWRITE, 0, 0x1000, name)` → `MapViewOfFile(h, FILE_MAP_ALL_ACCESS, 0,0,0)` → 成功时**把全局指针 `0x10a07c8c` 写入映射首 dword** → **立即 `UnmapViewOfFile`** → `CloseHandle`。**短命映射** ⇒ 疑似**单实例门锁 / 握手令牌**，不是数据通道。

**★ `0x0e832e` 在全 `.text` 中零 `E8` 调用者** ⇒ 经 VM 派发进入（与 `.text` 其余 VM 入口一致）。

## 补遗五、`0x0e8f2d`（唯一非库 `recv` 站点）的最终定性

`0x0e8f2d` 经 A 家族桩表 `0x453100`（= `recv`）调用，是整个 socket 普查里**唯一不属于四类的站点**。定性依据（三重）：

1. **所在区 `RVA 0x0d0000–0x100000`（192 KB）是 VM/TVM 虚拟化保护代码区。** 定量：该区 `E9`(jmp) 共 1564 条，其中 **1114 条 (71%)** 目标落在 `.tvm0`；`E8`(call) 共 2718 条，**373 条 (14%)** 落在 `.tvm0`。对照正常代码区 `0x410000–0x420000`：`E8`=916 条仅 **6 条 (1%)**、`E9`=105 条仅 **2 条 (2%)**。
2. **该区 `FF15` 命中 22 槽全为 KERNEL32，`FF25` 命中 0** ⇒ 不直接使用任何网络 API。
3. **该区唯一被外部调用的入口是 `0x0e8f00`**（唯一外部调用者 `0x005a67 → 0x0e8f00`），其**首指令即 `jmp <.tvm0>`**；且**区内零 `E9` 目标落在 `0x0e8d00–0x0e8f00`**（该段 `E8` 目标仅 2 条：`0x005a67 → 0x0e8f00` 与内部 `0x0e8d19 → 0x0e8d1f`）。

**⇒ `0x0e8f2d` 位于线性不可达的 VM 覆盖字节中，是原字节扫描的假阳性，不是真实调用点。** 即便按明文解读，该区也**无 socket 创建、无长期持有、无收发线程**。

**附带实证的 `.tvm0` 边界**（回应「E9 目标看似越界」的疑虑）：`.tvm0` 的 **RVA 范围是 `0x19dd000–0x393b000`**（节表 `va=0x19dd000 vsize=0x1f5e000`）⇒ 形如 `jmp 0x25eb887` / `call 0x2625ea7` / `lea edx,[edx+0x2547e8b]` 的目标**全部在 `.tvm0` 之内，不是越界垃圾**，是 TVM 派发桩。

## 补遗六、任务 8 —— `Base.dll` 不消费任何配置文件名（双重否证）

**否证 1：`Base.dll` 对工作目录内的配置文件零引用。**

| 字面量 | 全文件引用数 |
|---|---|
| `iips` / `enable_iips` / `iips_url` | 0 / 0 / 0 |
| `stun` / `stun.ini` / `stun1` | 0 / 0 / 0 |
| `codol.qq.com` | 0 |
| `BugTrace.ini` / `Game.dat` / `Tenparty` | 0 / 0 / 0 |
| `GameBabyConfig` / `localization.txt` | 0 / 0 |
| `wukong` | 0（与「主机名在栈上构造」一致） |
| **`.ini`（任意上下文）** | **0** |

⇒ **`Base.dll` 不消费任何 `.ini`**；`iips.ini` / `stun.ini` 由别的模块（launcher / tenproxy / WKNet 宿主）消费。

**否证 2：TCLS / TAS 相关字面量在 `Base.dll` 内是「死字面量」。**

| 字面量 | 地址 | 全文件引用数 |
|---|---|---|
| `TCLS_SHAREDMEMEMORY` | `0x88fffc` | **0** |
| `TCLS_TASMEMORY_` | `0x89015c` | **0** |
| `\tencent\tas\TASData.dat` | `0x88fff5` | **0** |
| `tenslx.dll` | `0xa03bb0` | **0** |
| `gamesafe v2.0` | `0x88b430` | **1**（唯一引用在 **`.tvm0:0x26d43f6`**） |
| `XTDL2` | `0xa07c80` | 1（`0x0e839b`，VM 保护区内） |
| `%s_%X_%d` | `0x88e140` | 1（`0x0e83a0`，同上） |

**nuance（必须同时记下）**：`gamesafe v2.0` 的唯一引用是**明文形式**，说明 **`.tvm0` 可以明文引用 `.rdata` 字面量** ⇒ `TCLS_*` 的**零引用是更强的证据**：它们要么经计算/加密寻址，要么根本不由本模块使用；**静态不可解，不得据此猜测其用途。**

**⇒ 唯一在 `Base.dll` 内被实际使用的共享内存名是 `XTDL2_<pidhex>_<piddec>`**（补遗四），不是 TCLS。

## 补遗七、任务 7 —— 524 / 615 的真实载体：**否定**

不再搜 `RseAuthState` / `RseCountryOpen`（`Base.dll` 已证无这些字符串），改为搜**数值 524 / 615**：

| 搜索 | 结果 |
|---|---|
| 十进制字面串 `"524\0"` / `"615\0"` / `"524"` / `"524 "` / `"615 "` | **全文件 0 命中** |
| `.rdata` 含 `524`/`615` 子串 | 4 处，全为十六进制乱码子串：`0x97a19a` `'0BDECF8A22E6524775F98CDEBDCB'`、`0x97a3de` `'F432C89435DE5242'`、`0x978da0` `'957F6C6FEACD615468DF104DE296CD8F'` |
| `0x20c`(524) 的 imm32 | **6 处，全为栈帧或步长** |
| `0x267`(615) 的 imm32（`.text` 内） | **0 命中** |

`0x20c` 的 6 处逐条：

| 站点 | 指令 | 性质 |
|---|---|---|
| `0x3887d3` | `81 ec 0c 02 00 00` = `sub esp,0x20c` | 栈帧（带 SEH / cookie `0x109b2afc`） |
| `0x51ad6d` | `sub esp,0x20c` | 栈帧 |
| `0x5ec065` | `sub esp,0x20c` | 栈帧 |
| `0x73db52` | `sub esp,0x20c` | 栈帧 |
| `0x450d7c` | `add eax,0x20c` | libcurl A 区，后接 `push 0x2711; call 0x10414c10` |
| `0x536c84` | `add eax,0x20c` | **全局表清零的 524 字节步长**：`xor eax,eax / and dword ptr [eax+0x10aae7b0],0 / add eax,0x20c / cmp eax,0x8300 / jb` |

**⇒ 524 / 615 在 `Base.dll` 内没有协议载体。** 用户要求的 `packet parser / switch / opcode / message dispatch` **亦未发现**（与补遗二的 IAT 缺席互为印证）。**不得因为看到数值就直接命名。**

---

## 【GAME_NET_EXCLUDED】★ 任务 9 的最终答复

**结论（限定于 `.text` 与 IAT 面）：`GAME_NET_EXCLUDED` —— 本 DLL 内不存在非 libcurl、非 WKNet、非安全探针的长期网络对象。**

支撑链条（每一环均已独立验证）：

| # | 事实 | 强度 |
|---|---|---|
| 1 | 全 `.text` 的 socket 创建点仅 6 处，**全部**归属 OpenSSL(2) / libcurl A(1) / libcurl B(2) / WKNet(1) | 已证 |
| 2 | **重叠 I/O 家族（`WSARecv`/`WSASend`/`WSAAccept`/`AcceptEx`/`ConnectEx`/`CreateIoCompletionPort` 等）根本不在 IAT 中** | 已证（决定性的缺席） |
| 3 | `accept`/`listen` 各 2 点全在 libcurl A/B 内 ⇒ **进程不监听端口** | 已证 |
| 4 | `CreateThread` 6 点无一与 socket 创建点同模块；`WSACreateEvent` 唯一调用点在 WKNet | 已证 |
| 5 | 唯一「非四类」的 `recv` 站点 `0x0e8f2d` 落在 VM 保护区线性不可达字节中 | 已证 |
| 6 | `.text` 无 packet dispatcher / opcode switch / sequence / ack / channel 任何形态 | 已证（多次独立扫描） |
| 7 | 524 / 615 无载体（补遗七） | 已证 |
| 8 | `Base.dll` 零 `.ini` 引用（补遗六）⇒ 网络地址不由本模块从配置文件读取 | 已证 |

**⇒ 任务 9 目标（「找到一个非 libcurl、非 WKNet、非安全探针的长期网络对象」）在本 DLL 内不可达。** 目标对象若存在，位于 **`Base.dll` 之外**（其余模块 / 974 个加密 `.ifs` 载荷 / `TenProtect` 的 VM 层）。

**⚠️ 与早前 `GAME_NETWORK_CANDIDATE` 节的关系**：该节曾把 WKNet 列为唯一候选。**本节的 `GAME_NET_EXCLUDED` 不推翻它，而是收敛它** —— 用户任务 2 明文要求「**不得因此直接判定其为 game netcode**」，故 WKNet 的最终分类是 **「选路 / 接入基础设施，非 game netcode」**，二者一致。

---

## 附：本报告依据的、须随结论一起传递的元判断

- **本 DLL 里那张 IAT 不是游戏的网络层。** 任何基于「从 IAT 找游戏 socket」的后续推断都会失败。
- **「明文函数体零静态调用者」是虚拟化调用图的结构性属性**（`0x22e610` / `0x22e740` 等 TVM 派发器入口），不是死代码判据。必须停止对 `0x1022exxx` 簇使用「无调用者 = 未使用」。
- **IAT 槽内容高位若为 1（`0x80000000` 置位），即为序号导入**，必须走「导出表 ordinal → 名字」反查，不能 `cstr`。本报告中的 `sendto` / `WSASetLastError` / `__WSAFDIsSet` 即由此确认。
- **在反汇编文本里 grep `+0x34` 会命中栈操作数**（如 `mov byte ptr [ebp-0x34], 0x73` 是主机名字符串的一个字节）。本次主机名构造段中就存在这种命中 —— **不得当作对象字段写入的证据。**

---

*本文只记录可验证事实与否证结论，不含任何绕过 / 会话伪造实现。*
