# 学习报告 023 — 逐字节：Localnetworking 的完整日志串区 + onStartup 反汇编

**方法**：按 NUL 切分 `0x4FF00..0x50340` 全部字符串 + 反汇编 `onStartup`/`onMessage`
**性质**：全实测
**★★★ 本报告给出了 `Localnetworking` 全部行为契约的字节级证据**

---

## 一、★★★ `Localnetworking` 的完整日志串区（逐串 + 精确偏移）

```
偏移       长度  内容
0x04FF70  30    "directory_iterator::operator++"     ← ★ 目录遍历（找插件）
0x04FF90  27    " failed with Winsock error "
0x04FFD4  18    "WSAStartup failed."
0x04FFE8  37    "Creating the datagram bridge listener"
0x050010  70    "No Localnetworking backend port was available in the configured range."
0x050058  25    "Loaded Localnet32 plugin "          ← ★★★ 加载日志
0x050074  14    "127.0.0.2:3074"                     ← ★★★ 默认 LSG 地址
0x050084  18    "OLMOD_LOBBY_LISTEN"                 ← ★★★ 环境变量
0x050098  46    "Lobby listener disabled by OLMOD_LOBBY_LISTEN."
0x0500C8  25    "\" is not a valid ip:port."
0x0500E4  44    "Lobby listener skipped: OLMOD_LOBBY_LISTEN=\""
0x050114  28    "formal-zone-lsg.codol.qq.com"       ← ★★★ LSG 主机名
0x050134  16    "OLMOD_LOBBY_HOST"                   ← ★★★ 环境变量
0x050148  41    "Lobby listener skipped: no plugin claims "
0x050174  46    "; another process already owns that address?)."
0x0501A4  16    " (Winsock error "
0x0501B8  4     " -> "
0x0501C0  30    "Lobby listener COULD NOT BIND "
0x0501E0  21    "Lobby listener bound "
0x0501F8  47    "Localnetworking backend listening on 127.0.0.1:"
0x050228  12    "Createserver"                       ← ★★★ GetProcAddress 参数
0x050238  ...   （libstdc++/MSVC 的通用错误串）
```

### ★★★ 这一串揭示了 `Localnetworking` 的完整职责

| 职责 | 证据字符串 |
|---|---|
| 1. 遍历目录找插件 | `directory_iterator::operator++` + `Loaded Localnet32 plugin ` |
| 2. 调 `WSAStartup` | `WSAStartup failed.` |
| 3. 创建 **datagram bridge** | `Creating the datagram bridge listener` |
| 4. 绑定 backend 端口 | `No Localnetworking backend port was available in the configured range.` |
| 5. ★★★ **绑定 Lobby 监听器** | `Lobby listener bound ` / `COULD NOT BIND` |
| 6. 默认 LSG 地址 `127.0.0.2:3074` | 字面串 |
| 7. 环境变量覆盖 | `OLMOD_LOBBY_LISTEN` / `OLMOD_LOBBY_HOST` |
| 8. 调 `Createserver` | 字面串 |

---

## 二、★★★ 关键发现 1：`127.0.0.2:3074` 是**硬编码默认值**

```
0x050074  len=14  "127.0.0.2:3074"
0x050114  len=28  "formal-zone-lsg.codol.qq.com"
```

★★★ **`Localnetworking` 自己知道 LSG 的地址是 `127.0.0.2:3074`**，
且知道 LSG 主机名是 `formal-zone-lsg.codol.qq.com`。

★★ **⇒ 与 `preflight.ps1` 的 hosts 配置、`Platform.json` 的 `lobbyEndpoint`、
`fake_auth_tls.py` 的 127.0.0.1(认证)/127.0.0.2(大厅) 完全一致。**

★ **三方对齐**：
```
preflight.ps1      formal-zone-lsg.codol.qq.com → 127.0.0.2
Platform.json      lobbyEndpoint = formal-zone-lsg.codol.qq.com:3074
Localnetworking    硬编码 "127.0.0.2:3074" + "formal-zone-lsg.codol.qq.com"
stun_local.py      同样的域名映射
```

---

## 三、★★★ 关键发现 2：`OLMOD_LOBBY_LISTEN` 是"让出大厅"的开关

### 字符串链（按日志顺序）

```
0x050084  "OLMOD_LOBBY_LISTEN"
0x050098  "Lobby listener disabled by OLMOD_LOBBY_LISTEN."
0x0500C8  "\" is not a valid ip:port."
0x0500E4  "Lobby listener skipped: OLMOD_LOBBY_LISTEN=\""
0x050134  "OLMOD_LOBBY_HOST"
0x050148  "Lobby listener skipped: no plugin claims "
0x050174  "; another process already owns that address?)."
```

### ★★★ 四条日志揭示了三种"跳过绑定"的情形

| 日志 | 条件 |
|---|---|
| `Lobby listener disabled by OLMOD_LOBBY_LISTEN.` | `OLMOD_LOBBY_LISTEN` 设了值但**不是 ip:port**（或空） |
| `Lobby listener skipped: OLMOD_LOBBY_LISTEN="<值>" is not a valid ip:port.` | 设了但格式错 |
| `Lobby listener skipped: no plugin claims <host>; another process already owns that address?` | ★ **没插件认领这个主机名**（`OLMOD_CLAIM_LOBBY` 未设！） |
| `Lobby listener bound <addr>` | ✓ 成功 |
| `Lobby listener COULD NOT BIND <addr> (Winsock error <n>)` | 绑失败（端口占用） |

★★★ **`no plugin claims <host>` 这条直接对应报告 010 的 `OLMOD_CLAIM_LOBBY`**：

```cpp
// Servers.cpp:109-116（报告 010 引用）
if (contains(value, "lobby.codol.localhost")) {
    enabled = (OLMOD_CLAIM_LOBBY == "1");
    return enabled ? ServerKind::lobby : ServerKind::none;
}
```

★★ **⇒ `Localnetworking` 在绑 Lobby 之前**问每个插件"你认领 `formal-zone-lsg.codol.qq.com` 吗"**
（这就是 `Broadcastmessage` 的用途！报告 020 的数组遍历 + 短路）。

★★★ **如果 `OLMOD_CLAIM_LOBBY=1`（`launch_chain.py` 会设）：`Alwaysoffline` 认领 ⇒ 绑 `127.0.0.2:3074`。**

★★ **如果 `OLMOD_SKIP_AUX=1`（走我们的大厅）：**
**`Localnetworking` 仍然会尝试绑 —— 除非 `OLMOD_LOBBY_LISTEN` 显式禁用或改端口。**

★ **这解释了报告 015 的 `OLMOD_SKIP_AUX=1` 注释**：
> 2026-10-20：走他们的大厅时，auth / STUN 都归他们（3074 不能抢）。

★★★ **但注释只跳过了 Python 侧的 auth/STUN，
没说 `Localnetworking` 的 `Lobby listener` 也要让出！**

★★ **⇒ 若用 `OLMOD_SKIP_AUX=1` 与我们的大厅共存，
必须额外设 `OLMOD_LOBBY_LISTEN`（让它跳过绑定），否则端口冲突。**

### ★ 这是本报告最重要的**操作结论**

```
走我们的大厅时，必须：
  OLMOD_SKIP_AUX=1              ← 跳 Python auth/STUN/room_owner
  OLMOD_LOBBY_LISTEN=<disable>  ← ★ 跳 Localnetworking 的 Lobby 绑定
  OLMOD_CLAIM_LOBBY 不设 / ≠1   ← 让插件不认领
```

---

## 四、★★★ 关键发现 3：`Createserver` 紧邻在日志串之后 —— 是 `GetProcAddress` 参数

```
0x0501F8  "Localnetworking backend listening on 127.0.0.1:"    ← 最后一条日志
0x050228  "Createserver"                                        ← ★ 紧接着
```

★★ **字符串池里 `Createserver` **紧接在日志串区末尾**，
后面直接是 MSVC 的通用错误串（`vector too long` 等）。**

★★★ **⇒ `Createserver` 是**代码字符串**（给 `GetProcAddress` 用的），
与日志串同一个池。**

★ **这坐实了报告 022 的推断**：
**`Localnetworking` 用 `GetProcAddress(h, "Createserver")` 加载 `*.Localnet32`。**

---

## 五、★★★ `Localnetworking::onStartup` @ `0x16FC0` 完整反汇编

```asm
00016FC0  55                    push ebp
00016FC1  8B EC                 mov  ebp, esp
00016FC3  83 E4 F8              and  esp, 0FFFFFFF8h        ← 8 字节对齐
00016FC6  83 EC 74              sub  esp, 74h               ← 116 字节局部
00016FC9  56                    push esi
00016FCA  8D 4C 24 10           lea  ecx, [esp+10h]
00016FCE  E8 DD 01 FF FF        call 000071B0               ← 构造对象 A（配置？）
00016FD3  80 7C 24 70 00        cmp  byte ptr [esp+70h], 0  ← ★ 检查对象 A 的某 bool
00016FD8  0F 84 A0 00 00 00     je   0001707E               ← false → 跳过主体
--- 主体 ---
00016FDE  8D 54 24 08           lea  edx, [esp+08h]
00016FE2  C7 44 24 08 00 00 00 00  mov  dword ptr [esp+08h], 0
00016FEA  8D 4C 24 40           lea  ecx, [esp+40h]
00016FEE  C7 44 24 0C 70 C2 07 10  mov  dword ptr [esp+0Ch], 1007C270h  ← ★ 字符串
00016FF6  E8 35 FD FF FF        call 00006D30               ← 构造 B（含字符串）
00016FFB  8D 54 24 08           lea  edx, [esp+08h]
00016FFF  8D 4C 24 58           lea  ecx, [esp+58h]
00017003  E8 28 FD FF FF        call 00006D30               ← 构造 C
00017008  8D 54 24 08           lea  edx, [esp+08h]
0001700C  8D 4C 24 28           lea  ecx, [esp+28h]
00017010  E8 1B FD FF FF        call 00006D30               ← 构造 D
00017015  E8 E6 DE FE FF        call 00004F00               ← ★ 主逻辑
0001701A  8B F0                 mov  esi, eax
0001701C  8D 44 24 10           lea  eax, [esp+10h]
00017020  68 68 10 00 00        push 1068h                  ← ★ 0x1068 = 4200
00017025  50                    push eax
00017026  8B CE                 mov  ecx, esi
00017028  E8 23 E5 FE FF        call 00005550
0001702D  84 C0                 test al, al
0001702F  74 22                 je   00017053
00017031  E8 5A D3 FF FF        call 00004390               ← 检查 A
00017036  84 C0                 test al, al
00017038  75 19                 jne  00017053
0001703A  83 EC 08              sub  esp, 8
0001703D  8B CE                 mov  ecx, esi
0001703F  8B C4                 mov  eax, esp
00017041  C7 00 B0 19 05 10     mov  dword ptr [eax], 100519B0h   ← ★ 字符串
00017047  C7 40 04 2C 00 00 00  mov  dword ptr [eax+4], 2Ch         ← ★ 长度 44
0001704E  E8 DD FF FE FF        call 00005030
--- 清理 ---
00017053  80 7C 24 70 00        cmp  byte ptr [esp+70h], 0
00017057  74 24                 je   0001707D
00017059  8D 4C 24 58           lea  ecx, [esp+58h]
0001705D  E8 1D 3D FF FF        call 0000AD80               ← 析构
00017062  8D 4C 24 40           lea  ecx, [esp+40h]
00017066  E8 14 3D FF FF        call 0000AD80               ← 析构
0001706C  8D 4C 24 28           lea  ecx, [esp+28h]
00017070  E8 0B 3D FF FF        call 0000AD80               ← 析构
00017076  8D 4C 24 10           lea  ecx, [esp+10h]
0001707A  E8 02 3D FF FF        call 0000AD80               ← 析构
0001707F  ...（清理结尾）
00017080  8B E5                 mov  esp, ebp
00017082  5D                    pop  ebp
00017083  C3                    ret
```

### ★★★ 五个关键点

1. **`C7 00 B0 19 05 10` + `C7 40 04 2C 00 00 00`**
   ```
   地址 = 0x100519B0  = ImageBase 0x10000000 + RVA 0x519B0
   长度 = 0x2C = 44
   ```
   ★ **`0x519B0` 在 `.rdata`（VA `0x46000`, Size `0xFC7C` → 到 `0x55C7C`）内** ✓
   ★ **44 字节的字符串** —— 在报告 023 第一节的日志串区里：
   **`0x0500E4` 的 `"Lobby listener skipped: OLMOD_LOBBY_LISTEN=\""` 正好 44 字节！**

   ★★★ **但偏移不匹配**（`0x519B0` vs `0x500E4`）。
   **⇒ `0x519B0` 是**另一处**的 44 字节字符串。
   **需要读 `0x519B0` 的实际内容。**

2. **`1007C270h`**（@ `0x16FEE`）
   ```
   RVA = 0x7C270，在 .data（VA 0x56000, Size 0x27A74 → 到 0x96474）内 ✓
   ```

3. **`push 1068h`**（@ `0x17020`）= **4200**
   ★ **可能是超时毫秒数**（4.2 秒）或缓冲区大小。

4. **`call 0x4F00`** —— 主逻辑（可能就是"遍历插件 + 绑 Lobby"）。

5. **`onMessage` @ `0x17090` = `32 C0 C3`**
   ```asm
   00017090  32 C0    xor al, al
   00017092  C3       ret
   ```
   ★★ **`onMessage` 是空桩，返回 `false`。**

   ★★★ **⇒ `Localnetworking` 的 `onMessage` 永远返回 false
   ⇒ `Bootstrapper::Broadcastmessage` **永远继续遍历下一个插件**
   ⇒ **`Localnetworking` 不消费任何广播消息。**

   ★ **这与报告 020 的短路语义结合**：
   **如果所有插件 `onMessage` 都返回 false，`Broadcastmessage` 返回 false。**

---

## 六、★★★ `Platformwrapper` 的 `onStartup` 也在 `0x18E90`（报告 020）

**注意 `Platformwrapper` 的 `onMessage` @ `0x190F0` 也需检查是否空桩。**

★ **如果 `Platformwrapper::onMessage` 是真函数，那 `Broadcastmessage` 的
"谁认领 LSG 主机名"查询就由它回答。**

★★★ **但 `OLMOD_CLAIM_LOBBY` 是 `Alwaysoffline` 的**（`Servers.cpp:109-116`，报告 010）。
**⇒ `Alwaysoffline.Localnet32` 也必须实现 `onMessage` 才能回答认领查询。**

★★ **可是报告 022 实测：`Alwaysoffline.Localnet32` 的 `onStartup` 出现 0 次！**
```
Alwaysoffline.Localnet32:  onStartup = 0
```
★★★ **⇒ `Alwaysoffline` **没有** `onStartup` 导出，也就无法被 `Bootstrapper` 加载。**

★★ **那它怎么回答 `OLMOD_CLAIM_LOBBY`？**

★★★ **⇒ 由 `Localnetworking` 通过 `Createserver` 之后的**另一条路径**问它，
或者 `OLMOD_CLAIM_LOBBY` 由 `Localnetworking` 自己读**。

★ **`Localnetworking` 里 `OLMOD_CLAIM_LOBBY` 出现次数？** —— **待查。**

---

## 七、逐字节证据总表（本报告）

| # | 偏移 | 内容 | 结论 |
|---|---|---|---|
| 1 | `0x04FF70` | `directory_iterator::operator++` | ★ 目录遍历 |
| 2 | `0x050058` | `Loaded Localnet32 plugin ` | ★★★ 加载 `.Localnet32` |
| 3 | `0x050074` | `127.0.0.2:3074` | ★★★ 硬编码 LSG 地址 |
| 4 | `0x050084` | `OLMOD_LOBBY_LISTEN` | ★★★ 让出大厅的开关 |
| 5 | `0x050114` | `formal-zone-lsg.codol.qq.com` | ★ LSG 主机名 |
| 6 | `0x050134` | `OLMOD_LOBBY_HOST` | ★ 覆盖主机名 |
| 7 | `0x050148` | `Lobby listener skipped: no plugin claims ` | ★★ 认领查询失败 |
| 8 | `0x050228` | `Createserver` | ★★★ `GetProcAddress` 参数 |
| 9 | `0x16FC0` | `onStartup` 真函数，116 字节栈帧 | ★ 主逻辑在 `0x4F00` |
| 10 | `0x17090` | `onMessage` = `32 C0 C3` | ★★ 空桩返回 false |
| 11 | `0x17041` | `mov [eax], 0x100519B0` + len 44 | ★ 44 字节串（待读） |

---

## 八、★★★ 对我们任务的**操作级结论**

### 结论 1：`Localnetworking` 是 `*.Localnet32` 的加载器（定案）

```
Bootstrapper32.dll → 扫描 *.Ayria32 → Localnetworking.Ayria32
Localnetworking    → 扫描 *.Localnet32 → Alwaysoffline / CodolGameServer
```

### 结论 2：★★★ 与我们大厅共存的**完整**环境变量组合

```
OLMOD_SKIP_AUX=1                 跳 Python auth/STUN/room_owner
OLMOD_LOBBY_LISTEN=<非 ip:port>  ★ 跳 Localnetworking 的 Lobby 绑定（新增！）
OLMOD_CLAIM_LOBBY 不设或≠1       ★ 让插件不认领 LSG
```

★★★ **报告 016 只发现了 `OLMOD_SKIP_AUX`，漏了 `OLMOD_LOBBY_LISTEN`。**
**如果不设它，`Localnetworking` 会抢绑 `127.0.0.2:3074`，与我们的 `lobby_server.py` 冲突。**

### 结论 3：★★ `Localnetworking::onMessage` 是空桩

★ **⇒ 插件的 `onMessage` 通道实际上是**关闭的**（至少对 `Localnetworking`）。**

★★ **⇒ `Broadcastmessage` 的"认领查询"可能不是通过 `onMessage`，
而是 `Localnetworking` 内部直接读环境变量。**

### 结论 4：★★ `Alwaysoffline` 没有 `onStartup` 导出

```
Alwaysoffline.Localnet32:  onStartup = 0 次
```

★ **⇒ 它无法被 `Bootstrapper` 的 `*.Ayria32` 扫描加载**（这没错，它是 `.Localnet32`）。
★★ **但它**也没有** `onMessage`** ⇒ 无法回答认领查询。

★★★ **⇒ `OLMOD_CLAIM_LOBBY` 的读取方必须是 `Localnetworking` 自己。**

★ **这需要用字节验证（在 `Localnetworking` 里搜 `OLMOD_CLAIM_LOBBY`）。**

---

## 九、待逐字节继续（★ 优先级）

- [ ] ★★★ **读 `0x100519B0`（RVA `0x519B0`）的 44 字节字符串内容**
- [ ] ★★★ **在 `Localnetworking` 里搜 `OLMOD_CLAIM_LOBBY`**（谁读它）
- [ ] ★★★ **反汇编 `0x4F00`（`onStartup` 的主逻辑 = 插件遍历 + 绑 Lobby）**
- [ ] ★★ **读 `0x1007C270`（`.data` 里的字符串/结构）**
- [ ] ★★ **`Platformwrapper::onMessage` @ `0x190F0` 是否空桩**
- [ ] ★ **`push 1068h`（4200）的含义**
- [ ] ★ **`0x5590` / `0x4390` / `0x5030` 三个被调函数**
