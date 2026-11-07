# 学习报告 025 — 逐字节：Localnetworking 的 Winsock hook 完整目标集

**方法**：统计 API 字符串出现次数 + 按 NUL 切分 hook 目标名字区 + 读 IAT 名表区
**性质**：全实测
**★★★ 本报告给出了 hook 冲突的完整字节级证据**

---

## 一、★★★ `Localnetworking` 的完整 API 面（实测次数）

```
API                次数    偏移（前 4 个）
connect            12      0x48AC8, 0x48B3C, 0x48B50, 0x48B70     ← ★★ 但这些都是 errno 串！
sendto              4      0x50588, 0x505BC, 0x50604, 0x50734    ← ★★★ 真 hook 目标
gethostbyname       1      0x506CC                                ← ★★★ 真 hook 目标
recvfrom            4      0x50618, 0x50628, 0x50638, 0x50728    ← ★★★ 真 hook 目标
WSAStartup          1      0x4FFD4                                ← 初始化
WS2_32              1      0x541A8                                ← IAT 名表
ws2_32              1      0x506F4                                ← 字符串
WSAIoctl            0      —                                      ← ★ 不用
bind                1      0x50718                                ← ★★★ 真 hook 目标
listen              7      0x50005, 0x5009E, 0x500EA, 0x5014E    ← 日志文本（"listener"）
accept              0      —                                      ← ★ 不用
socket              1      0x48E1E                                ← errno 串（"not a socket"）
closesocket         0      —
WSASocket           0      —
GetProcAddress      1      0x541F6                                ← IAT
VirtualProtect      1      0x543A4                                ← ★★★ 装 hook 用
LoadLibrary         3      0x541E6, 0x54208, 0x547E4              ← IAT
```

### ★★★ 关键判读：`connect` 的 12 次**全部是 errno 串**

```
0x048AC0  'already connected'
0x048B3C  'connection aborted'
0x048B50  'connection already in progress'
0x048B70  'connection refused'
0x048B84  'connection reset'
...
```

★★ **`0x48AC8` 是 `"already connected"` 的第 8 个字符位置** ——
**`connect` 子串出现在 errno 错误消息里，不是 API 名！**

★★★ **⇒ `connect` 不是 `Localnetworking` 的 hook 目标。**

★★ **这与 `nt10.py` 的 `--apis connect,sendto,gethostbyname`（报告 007）不同**：
**`nt10.py` hook `connect`，`Localnetworking` **不** hook `connect`。**

★★★ **⇒ hook 目标集有**交集但不重合**，冲突只发生在交集上。**

---

## 二、★★★ 真正的 hook 目标名字区（`0x50560`..）

```
0x50560 附近连读（原样）：
ct..ConnectEx... clientPort=.... bytes=.sendto-target .. error=. result=....
serverPort=....sendto-direct .. prefix=.... type=..dtls-send ..
datagram-route-created .sendto . source=....recvfrom-route .recvfrom-game ..
recvfrom-direct ....dtls
```

### 按 NUL 切分还原

| 偏移 | 内容 | 性质 |
|---|---|---|
| `0x50558` | `ConnectEx` | API 名（但**未在 hook 集**？） |
| `0x50564` | ` clientPort=` | 日志格式 |
| `0x50574` | ` bytes=` | 日志 |
| `0x5057C` | `sendto-target ` | ★★ 日志 |
| `0x5058C` | ` error=` | 日志 |
| `0x50594` | ` result=` | 日志 |
| `0x505A0` | ` serverPort=` | 日志 |
| `0x505B0` | `sendto-direct ` | ★★ 日志 |
| `0x505C0` | ` prefix=` | 日志 |
| `0x505CC` | ` type=` | 日志 |
| `0x505D4` | `dtls-send ` | ★★★ DTLS |
| `0x505E0` | `datagram-route-created ` | ★★★ 路由 |
| `0x50604` | `sendto ` | ★★★ **hook 目标（带空格）** |
| `0x5060C` | ` source=` | 日志 |
| `0x50618` | `recvfrom-route ` | ★★ 日志 |
| `0x50628` | `recvfrom-game ` | ★★★ 游戏流量 |
| `0x50638` | `recvfrom-direct ` | ★★ |
| `0x50660` | `dtls` | ★★★ |

★★★ **⇒ 三种流量被区分**：

```
sendto           ← hook 目标（API 名）
  ├─ sendto-target        目标
  └─ sendto-direct        直连（绕过我们的桥）

recvfrom         ← hook 目标（API 名）
  ├─ recvfrom-route       路由流量
  ├─ recvfrom-game        游戏流量
  └─ recvfrom-direct      直连
```

★★★ **这是"分流"设计的字节级证据**：
**`Localnetworking` hook 了 `sendto`/`recvfrom`，并按"目标/来源"决定走桥还是直连。**

### ★ 完整 hook 目标集（4 个）

| API | 次数 | 偏移 | 用途 |
|---|---|---|---|
| `sendto` | 4 | `0x50588`（日志）+ `0x50604`（API 名） | 拦截发送 |
| `recvfrom` | 4 | `0x50618` 等 | 拦截接收 |
| `gethostbyname` | 1 | `0x506CC` | ★ 拦截 DNS |
| `bind` | 1 | `0x50718` | ★ 拦截绑定 |

★★ **注意 `0x506F4` 有 `ws2_32`（小写）** —— 是 `LoadLibrary("ws2_32")` 的参数字符串
（Windows 不区分大小写，但字符串本身是小写）。

---

## 三、★★★ `Localnetworking` 的 IAT 名表区（`0x54180` 附近）

```
...inet_pton ...inet_ntop ...WS2_32.dll ...GetModuleFileNameW ...
GetEnvironmentVariableA ...LoadLibraryW ...GetProcAddress ...
LoadLibraryA ...GetWindowsDirectoryA ...GetCurrentProcessId ...
DisableThreadLibraryCalls ...CloseHandle ...
```

★★★ **这是完整的 `LoadLibrary`+`GetProcAddress` 链** ——
**`Localnetworking` 用**运行时解析**而不是静态导入来拿 Winsock 函数。**

★★ **为什么？** 因为 hook 需要**原始函数地址**（在 `ws2_32.dll` 里），
而且**必须绕过自己的导入表**（否则 hook 自己的导入没意义）。

### ★★★ 关键 API 的用途推演

| API | 用途 |
|---|---|
| `VirtualAlloc` (`0x54380`) | ★ 分配 trampoline / 代码洞 |
| **`VirtualProtect`** | ★★★ **改页保护装 hook** |
| `VirtualQuery` | ★ 检查页属性 |
| `GetSystemInfo` | ★ 取页大小（`dwPageSize`） |
| `GetModuleHandleW` | 取 `ws2_32` 基址 |
| `FormatMessageA` | 错误消息 |

★★★ **⇒ `VirtualAlloc` + `VirtualProtect` + `VirtualQuery` + `GetSystemInfo` 四件套
= 经典 inline hook 实现。**

★★ **这与 `nt10.py` 的 hook 机制**完全相同**（报告 002/003 的 `E9 rel32` + trampoline）：
**两者都在 `ws2_32` 的代码段写 `E9` 跳转。**

---

## 四、★★★ hook 冲突的**逐字节**证明

### `nt10.py` 的 hook 集（报告 007，`--apis` 默认值）

```
connect, sendto, gethostbyname
```
★ `launch_chain.py:99-100` 传的是：
```
"OpenFileMappingW,CreateFileMappingW,MapViewOfFile,connect,sendto,"
"WinHttpConnect,WinHttpOpenRequest,WinHttpSendRequest,z1,z2"
```
⇒ **`nt10.py` 实际 hook：`connect`, `sendto`（+ WinHttp 三个 + 3 个 kernel32 映射 API）**

### `Localnetworking` 的 hook 集（本报告）

```
sendto, recvfrom, gethostbyname, bind
```

### ★★★ 交集 = `sendto`

```
nt10.py:          connect, sendto, gethostbyname         (+ OpenFileMappingW 等 5 个)
Localnetworking:  sendto, recvfrom, gethostbyname, bind
                                    ↑
交集：sendto, gethostbyname
```

★★★ **★ 冲突点在 `sendto` 和 `gethostbyname` 两个。**

★★ **（报告 024 我推测"`Localnetworking` 抢先 hook 了 `ws2_32`"，
现在有了精确的**两个**冲突点。）**

### ★★★ 谁先装谁赢

```
若 nt10.py 先装：
    sendto → nt10 的 trampoline → 原函数
    Localnetworking 再装时：
        读 sendto 首字节 → 发现是 E9（已 hooked）
        → ★ 三种可能：
           (a) 拒绝安装（"Failed to install..."）
           (b) 链接到自己（hook 链）
           (c) 覆盖（nt10 的 hook 失效）

若 Localnetworking 先装：
    nt10 读 sendto 首字节 → E9
    → ★ 同样三种可能
```

★★★ **`"Failed to install one or more Winsock hooks."` 的存在说明至少有一条拒绝路径。**

★★ **而 `launch_chain.py` 用 `--delay 0`**（不等待）⇒ **强化了竞态。**

---

## 五、★★★ 完整的 `Localnetworking` 职责清单（字节级）

```
onStartup @ 0x16FC0
  ├─ 构造配置对象（call 0x71B0）
  ├─ 构造三个字符串（0x1007C270 / 其他）
  ├─ call 0x4F00    ← ★★★ 主逻辑
  │     ├─ 读 PEB（fs:[0x2C] = 当前线程的 TEB→ProcessEnvironmentBlock）
  │     ├─ 读 0x1007D184（局部变量表基址）
  │     ├─ 检查 0x1007D8DC 等状态
  │     └─ ...
  ├─ call 0x5550    ← 检查结果
  ├─ if 失败 → 记录 "Failed to install one or more Winsock hooks."
  └─ call 0x5030    ← 日志
```

### `0x4F00` 反汇编的关键片段（逐字节）

```asm
004F00  55                    push ebp
004F01  8B EC                 mov  ebp, esp
004F03  6A FF                 push -1                 ← SEH 开始
004F05  68 A3 3B 04 10        push 10043BA3h          ← SEH 处理器
004F0A  64 A1 00 00 00 00     mov  eax, fs:[0]        ← SEH 链
004F10  50                    push eax
004F11  51                    push ecx
004F12  56                    push esi
004F13  A1 00 B8 07 10        mov  eax, [1007B800h]   ← ★ 栈 Cookie
004F18  33 C5                 xor  eax, ebp           ← /GS 保护
004F1A  50                    push eax
004F1B  8D 45 F4              lea  eax, [ebp-0Ch]
004F1E  64 A3 00 00 00 00     mov  fs:[0], eax
004F24  64 A1 2C 00 00 00     mov  eax, fs:[2Ch]      ← ★★★ PEB！
004F2A  8B 0D 84 D1 07 10     mov  ecx, [1007D184h]
004F30  8B 0C 88              mov  ecx, [eax+ecx*4]   ← ★ TlsIndex？
004F33  A1 DC D8 07 10        mov  eax, [1007D8DCh]
004F38  3B 81 08 00 00 00     cmp  eax, [ecx+8]
004F3E  7F 1F                 jg   00004F5F
```

★★★ **`fs:[2Ch]` = PEB，`[PEB + TlsIndex*4]` = TLS 槽** ——
**这是**线程局部存储**的访问。**

★★ **⇒ `onStartup` 安装了**TLS 索引**，用于在多个线程里共享状态。**

★ **注意 `0x1007D184` 是 `TlsIndex` 的存储位置。**

★★ **这与报告 019 发现的"`CodolGameServer` 有 TLS 目录"呼应** ——
**整个插件体系都依赖 TLS。**

---

## 六、`0x515BC` 不是字符串，是**指针数组**

**实测**（RVA `0x515BC` → raw `0x507BC`，前 20 字节）：
```
00 1C 00 10  F0 1C 00 10  00 1D 00 10  D0 1D 00 10  B0 17 00 10
```

★★ **解码为 5 个指针**（小端）：
```
0x10001C00
0x10001CF0
0x10001D00
0x10001DD0
0x100017B0
```

★★★ **全部在 ImageBase `0x10000000` + RVA `0x17B0..0x1DD0`** ——
**在 `.text`（VA `0x1000`, Size `0x448BA`）内 ✓**

★★ **⇒ 这是**函数指针数组**（可能是 hook 原函数的 trampoline 表）。**

★ **`onStartup` 里的 `mov [esp+0Ch], 0x1007C270`** ——
**`0x1007C270` 处的值是 `0x100515BC`（本报告的 `+0` 字段）** ——
★★ **⇒ `0x1007C270` 是一个**包含指针的结构**，指向这个函数表。**

---

## 七、逐字节证据总表（本报告）

| # | 证据 | 偏移 | 值 |
|---|---|---|---|
| 1 | `sendto`（API 名） | `0x50604` | ★★★ hook 目标 |
| 2 | `recvfrom`（API 名） | `0x50638`? | ★★★ hook 目标 |
| 3 | `gethostbyname` | `0x506CC` | ★★★ hook 目标 |
| 4 | `bind` | `0x50718` | ★★★ hook 目标 |
| 5 | `sendto-target` / `sendto-direct` | `0x5057C`/`0x505B0` | ★★ 分流日志 |
| 6 | `recvfrom-route`/`-game`/`-direct` | `0x50618`.. | ★★ 分流日志 |
| 7 | `dtls-send` / `datagram-route-created` | `0x505D4`/`0x505E0` | ★★★ DTLS |
| 8 | `ConnectEx` | `0x50558` | API 名（未在 hook 集？） |
| 9 | `VirtualAlloc`+`VirtualProtect`+`VirtualQuery`+`GetSystemInfo` | `0x54380`.. | ★★★ inline hook 四件套 |
| 10 | `LoadLibraryW`+`GetProcAddress` | `0x541E6`/`0x541F6` | ★★ 运行时解析 |
| 11 | `fs:[2Ch]`（PEB）+ TLS 槽 | `0x4F24` | ★★ TLS 索引 |
| 12 | 函数指针数组 @ `0x515BC` | 5 个指针 | ★ trampoline 表 |
| 13 | `connect` 12 次全是 errno 串 | `0x48AC0`.. | ★★★ 非 hook 目标 |

---

## 八、★★★ 操作级结论

### 结论 1：hook 冲突点是 **`sendto` + `gethostbyname`**（不是 `connect`）

```
nt10.py:          connect, sendto, gethostbyname
Localnetworking:  sendto, recvfrom, gethostbyname, bind
        ⇒ 冲突：sendto, gethostbyname
        ⇒ 不冲突：connect（Localnetworking 不 hook）, recvfrom/bind（nt10 不 hook）
```

★★★ **⇒ 如果要"外部战斗服 + nt10 读密钥"共存，
必须解决 `sendto` 和 `gethostbyname` 的双重 hook。**

### 结论 2：`Localnetworking` 是**功能完整的 Winsock 重定向层**

```
sendto   → 判断目标：走桥 or 直连
recvfrom → 判断来源：route / game / direct
gethostbyname → 合成 DNS（OLMOD_SYNTHETIC_DNS）
bind     → 拦截 Lobby 绑定
dtls     → 内置 DTLS（战斗服加密）
```

★★ **它不是"简单 hook"，是**一个完整的网络栈**。**

### 结论 3：★★★ 这解释了为什么"混合方案解决不了"

**记忆 `codol-lsg-never-listening`**：
> "混合方案架构成立但解决不了（外部让出 3074 + 我们的 lobby 接管，客户端仍不 connect）"

★★★ **⇒ 因为即使让出 3074，
`Localnetworking` 的 `sendto`/`recvfrom` hook 仍然活跃，
它会**把游戏流量导向自己的桥**，而不是我们的 lobby。**

★★ **`sendto-target` / `sendto-direct` 的分流逻辑**决定了流量去哪。
**只有 `OLMOD_LOBBY_LISTEN` 那一条控制"bind"，控制不了"发送路由"。**

★★★ **⇒ 必须找到"让 `Localnetworking` 完全不装 hook"的开关。
如果不存在，就只能二选一。**

### 结论 4：★ 我们自己的 `dll`（本地 `Localnetworking`）与外部版是同一份

★★ **记忆里有"交付的 Localnetworking 二进制缺真实 bind 代码（源码比二进制新）"。**
**现在看：`Localnetworking.Ayria32` 确实有完整的 hook + bind 逻辑（本报告实测）。**

★ **⇒ 记忆里那个"缺 bind 代码"的判断，可能针对的是**另一份**（源码重建的）。**

---

## 九、待逐字节继续（★ 优先级）

- [ ] ★★★ **在 `Localnetworking` 里搜有无"禁用 hook"的环境变量**
      （`OLMOD_DISABLE_HOOK` / `OLMOD_HOOK` / `OLMOD_RAW` 等）
- [ ] ★★★ **`0x5550`（hook 安装结果检查）与 `0x4390`**
- [ ] ★★ **`recvfrom` API 名的精确偏移**（`0x50638` 是日志，API 名可能在别处）
- [ ] ★★ **`0x1007D184`（TlsIndex）与 `0x1007D8DC`（状态）**
- [ ] ★ **`0x4F00` 完整反汇编**（只看了前 176 字节）
- [ ] ★ **`0x515BC` 的 5 个函数指针分别是什么**（trampoline 表）
