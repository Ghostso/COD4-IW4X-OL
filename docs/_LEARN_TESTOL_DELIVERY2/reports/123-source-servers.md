# 学习报告 123（重开）— `backend\Appmain.cpp`（90 行）+ `Servers.hpp`（127）+ `Servers.cpp`（671）

**学习范围**：`Appmain.cpp`（3,184 B / 90 行）+ `Servers.hpp`（4,781 B / 127）+ `Servers.cpp`（30,698 B / 671）
**性质**：全实测（**三文件逐行读完**）
**★★★★★ 本报告收录七个重大发现**：①**`Createserver` 的唯一入口与五个环境变量开关** ②**`classifyHostname` 的完整判定链** ③**STUN 的两种应答（15/9 字节）** ④**`LobbyServer` 的 13 服务 + 2 辅助组成** ⑤**`submitBooking` 的"软失败"放宽** ⑥**`Auth3` 补丁只在 auth3 分支安装** ⑦**`DllMain` 的两个补丁**

---

## 一、★★★★★ **`Createserver` 的唯一入口**

### 1.1 ★★★★★ 完整实现（`Appmain.cpp:19-48`）

```cpp
extern "C" __declspec(dllexport) IServer *__cdecl **Createserver**(const char *hostname)
{
    if (!hostname || !OlMod::runsBackend(OlMod::processRole()))
        return nullptr;                                        // ★ 角色门控

    if (!StartupPatchesInstalled)
    {
        static std::once_flag warning;
        std::call_once(warning, [] {
            AlwaysofflineRe::log("**Refused to apply CODOL startup patches to an unknown
                executable image.**");
        });
    }

    try
    {
        auto *server = Factory.create(hostname);
        if (server)
            AlwaysofflineRe::log(std::string("**Claimed** ") + hostname + " as " +
                serverKindName(classifyHostname(hostname)) + '.');
        return server;
    }
    catch (const std::exception &error)
    {
        AlwaysofflineRe::log(std::string("Createserver failed: ") + error.what());
        return nullptr;
    }
}
```

### ★★★★★ 三个关键点

```
① ★★★ **角色门控**：`OlMod::runsBackend(processRole())`
   ⇒ 与报告 095 的 `ProcessRole` 三值矩阵**直接对应**
   ⇒ **`Dedicated` 角色下 `runsBackend` 为 false** ⇒ 不创建任何服务
        ↓
② ★★★ **`Refused to apply CODOL startup patches...` 只打一次**（`std::call_once`）
   ⇒ 与报告 107 的"在 OLfinal 上必然拒绝,这是准确的"**完全对应** ✓
        ↓
③ ★★ **`Claimed <hostname> as <kind>`** ⇒ 每次创建都记日志
```

### ★★★ 四个 `CODOL_*` 导出（第 50–82 行）

```cpp
CODOL_RequestProfileReload(profileKind)
CODOL_GetProfileReloadStatus(profileKind, &generation, &state, &errorCode)
CODOL_RequestInventoryRefresh()
CODOL_GetInventoryRefreshStatus(&generation, &state, &errorCode)
```

★★★ **⇒ 与报告 082 的 `Alwaysoffline.Localnet32` 的 4 个导出**完全一致** ✓**
**⇒ 且与报告 108 的 `CodolClientPatches.hpp` 的 API **完全对应** ✓**

### ★★★★★ `DllMain` 的两个补丁（第 84–101 行）

```cpp
BOOL WINAPI DllMain(const HINSTANCE module, const DWORD reason, LPVOID)
{
    if (reason == DLL_PROCESS_ATTACH)
    {
        DisableThreadLibraryCalls(module);
        if (OlMod::runsBackend(OlMod::processRole()))
        {
            StartupPatchesInstalled = Demonware::installCodolStartupPatches();
            // ★★★ 2026-10-07 04:5x -- 探针（`CODOL_FORCE_RECORD_VALIDATOR=1` 时才动手）：
            // 强制放行候选记录校验器...**与 3.3.3.3 门无关**：
            // 它自己做字节校验（`55 8B EC 51 53` → `B0 01 C2 04 00`），失败就拒绝并写日志。
            static_cast<void>(Demonware::installForcedRecordValidatorPatch());
        }
    }
    return TRUE;
}
```

★★★★★ **⇒ 两个补丁 + 一个精确的字节对照：**
```
① `installCodolStartupPatches()` ⇒ 报告 107 的**七个站点**
② `installForcedRecordValidatorPatch()` ⇒ 报告 107 的**门强制探针**
        ↓
★★★ 且给出**门补丁的精确字节**：
   `55 8B EC 51 53` → `B0 01 C2 04 00`
   ⇒ **`mov al,1; ret 4`**（5 字节）
        ↓
★★★ 注意：报告 107 记的是 `mov al,1; ret 4` 但**未给原始字节**
   ⇒ 本报告补上：**原 `55 8B EC 51 53`**（`push ebp; mov ebp,esp; push ecx; push ebx`）
```

---

## 二、★★★★★ **`classifyHostname` 的完整判定链**

### 2.1 ★★★★★ 五级判定（`Servers.cpp:88-216`）

```cpp
if (contains(value, "**lobby.codol.localhost**"))     ⇒ lobby（需 OLMOD_CLAIM_LOBBY=1）
if (!contains(value, "**demonware.net**") && !contains(value, "**qq.com**"))
    return none;                                       // ★★ 域名白名单
if (contains(value, "**stun.**") || "**stun1-**" || "**stun2-**")  ⇒ stun
if (contains(value, "**umbrella.**") || "**auth3.**" || "**uno.**") ⇒ auth3
if (contains(value, "**auth.**"))                     ⇒ legacyAuth（需 OLMOD_CLAIM_LEGACY_AUTH=1）
if (contains(value, "**cs.**"))                       ⇒ content
if (contains(value, "**lsg.**") || "**lobby.**")      ⇒ lobby
return none;
```

### ★★★★★ 完整的判定表

| 优先级 | 匹配 | 结果 | 环境变量开关 |
|---|---|---|---|
| **1** | ★ **`lobby.codol.localhost`** | **lobby** | ★ **`OLMOD_CLAIM_LOBBY=1`** |
| **2** | **非 `demonware.net` 且非 `qq.com`** | ★★ **none**（白名单） | — |
| **3** | **`stun.` / `stun1-` / `stun2-`** | **stun** | ★ **`OLMOD_EXTERNAL_STUN=1`** ⇒ 放弃 |
| **4** | **`umbrella.` / `auth3.` / `uno.`** | **auth3** | ★ **`OLMOD_EXTERNAL_AUTH3=1`** ⇒ 放弃 |
| **5** | **`auth.`** | **legacyAuth** | ★★ **`OLMOD_CLAIM_LEGACY_AUTH=1`**（**默认不认领**） |
| **6** | **`cs.`** | **content** | — |
| **7** | **`lsg.` / `lobby.`** | **lobby** | ★ **`OLMOD_EXTERNAL_AUTH3=1`** ⇒ 放弃 |

★★★ **⇒ **五个环境变量开关**（`OLMOD_CLAIM_LOBBY` / `EXTERNAL_STUN` / `EXTERNAL_AUTH3` / `CLAIM_LEGACY_AUTH` / …）**
**⇒ `OLMOD_*` 累计 **29 个**。**

### ★★★★★ 第 1 条的完整理由（第 92–108 行，逐字）

```cpp
// OLMOD(claim-lobby): the OLfinal bring-up stack points the client at
// `lobby.codol.localhost`, which the hosts file resolves to 127.0.0.1 and the C# LobbyServer
// answers. **That is why this backend's matchmaking and room services -- 21/1..21/16 and
// 11/1..11/13, all registered -- never see a request**: the gate below requires
// demonware.net or qq.com, so Createserver **refuses the name** and Localnetworking lets the
// connection through to the real socket instead of routing it in-process.
//
// It matters because **ConfigureSession is sent from MatchmakingService**. With the lobby
// served elsewhere **nothing ever tells the game server to host**, and QueryEndpoint on a live
// client reports **sessionConfigured=false, bound=false, port=0** -- which is exactly what a
// two-client match is blocked on, and **no amount of address work reaches it**.
```

★★★★★ **⇒ 一个精确的"为什么所有服务都没被调用"的解释：**
```
客户端拨 `lobby.codol.localhost`
        ↓
★★★ 但门控要求 `demonware.net` 或 `qq.com`
   ⇒ **`Createserver` 拒绝这个名字**
   ⇒ `Localnetworking` 让连接**穿过到真 socket**
        ↓
★★★ ⇒ `21/1..21/16` 与 `11/1..11/13` **全部注册了但从未收到请求**
        ↓
★★★ ⇒ `ConfigureSession` **从不发送** ⇒ 没人告诉战斗服去 host
   ⇒ `QueryEndpoint` 报 **`sessionConfigured=false, bound=false, port=0`**
        ↓
★★★★★ ⇒ **"no amount of address work reaches it"**
```

★★ **⇒ 这与 memory 的「外部方案验证已结项」**完全吻合**：**
```
memory："**混合方案架构成立但解决不了**（外部让出3074+我们的lobby接管，客户端仍不connect）"
        ↓
★★★ 本报告：给出**精确的机制**（名字门控）
```

### ★★★★★ 第 5 条的完整理由（第 172–191 行，逐字）

```cpp
// LOCAL OVERRIDE (DSH, 2026-10-05) -- **DO NOT CLAIM LEGACY AUTH BY DEFAULT.**
//
// WHY: on this workspace the client dials `formal-zone-auth.codol.qq.com`, which the
// hosts file maps to 127.0.0.1, and a Python TLS auth server (`fake_auth_tls.py`) owns
// that socket. `contains(value, "auth.")` matches that name, and `ServerFactory::create`
// returns a PendingStreamServer for legacyAuth **UNCONDITIONALLY** -- a **PLAINTEXT stream
// server, while this client's auth is TLS**. Claiming the name therefore takes login
// away from the working TLS server, and **login is the one link that currently works**.
```

★★★★★ **⇒ 一个精确的"认领即破坏"：**
```
客户端拨 `formal-zone-auth.codol.qq.com`
        ↓
★★★ 而 `ServerFactory::create` 对 legacyAuth **无条件**返回
   **`PendingStreamServer`（纯文本流服务器）**
        ↓
★★★ 但**这个客户端的 auth 是 TLS**
        ↓
★★★★★ ⇒ **认领即把登录从能工作的 TLS 服务器抢走**
   ⇒ "**login is the one link that currently works**"
```

### ★★★★★ 第 4 条的完整理由（第 142–162 行，逐字）

```cpp
// OLMOD_EXTERNAL_AUTH3: HAND AUTH3 BACK TO A REAL SERVER.
//
// Handoff section 191i. Claiming this name is what forces the whole opaque path:
// the connection never reaches a socket, an in-process TLS server answers it with a
// certificate it **MINTS AT RUNTIME AND SIGNS ITSELF**, and the only way a client accepts
// that is if **three of its validation sites are patched out first**. On 2026-09-03 that
// chain cost a remote player **his evening** -- the patches were gated on a **3.3.3.3
// filename**, OLfinal runs **out.exe**, so they never applied and his client correctly said
// **`tlsv1 alert unknown ca`**.
```

★★★★★ **⇒ 与报告 104 的"两周错误"**完全同一事件**：**
```
报告 104（`Auth3ClientPatches.cpp`）：
  借用 `CodolClientPatches.cpp` 的进程名门控
  ⇒ 在 `out.exe` 上返回 TRUE 但没打补丁
  ⇒ 客户端真的校验自签证书 ⇒ **`tlsv1 alert unknown ca`**
  ⇒ **40 秒卡顿 + 挂断**
        ↓
★★★ 本报告：同一事件的另一侧描述
   ⇒ "**cost a remote player his evening**"
   ⇒ 且明确"**the patches were gated on a 3.3.3.3 filename, OLfinal runs out.exe**"
```

---

## 三、★★★★★ **STUN 的两种应答（15/9 字节）**

### 3.1 ★★★★★ 完整实现（第 259–323 行）

```cpp
if (request[0] == **0x14** || request[0] == **0x1E**)
{
    std::vector<std::uint8_t> response;
    response.reserve(request[0] == 0x14 ? **15** : **9**);              // ★ 15 / 9 字节
    response.push_back(static_cast<std::uint8_t>(request[0] + **1**));   // ★ 类型 +1
    appendLeU16(response, **AF_INET**);                                  // = 2
    response.insert(response.end(), { **0xF0, 0x00, 0x00, 0x01** });      // ★ 4 字节
    appendLeU16(response, ntohs(endpoints->client.port));                // ★ 客户端端口
    if (request[0] == **0x14**)
    {
        const auto *address = reinterpret_cast<const std::uint8_t *>(&endpoints->server.ipv4);
        response.insert(response.end(), address, address + 4);            // ★ 服务端 IP
        appendLeU16(response, ntohs(endpoints->server.port));             // ★ 服务端端口
    }
    ...
}
```

### ★★★★★ 完整的两种应答

#### `0x14` → `0x15`（15 字节）

| 偏移 | 大小 | 内容 |
|---|---|---|
| **0** | 1 | ★ **`0x15`**（`0x14 + 1`） |
| **1–2** | 2 | **`AF_INET` = 2**（LE） |
| **3–6** | 4 | ★ **`F0 00 00 01`** |
| **7–8** | 2 | **客户端端口**（LE） |
| **9–12** | 4 | ★ **服务端 IP** |
| **13–14** | 2 | ★ **服务端端口**（LE） |
| **合计** | **15** | — |

#### `0x1E` → `0x1F`（9 字节）

| 偏移 | 大小 | 内容 |
|---|---|---|
| **0** | 1 | ★ **`0x1F`**（`0x1E + 1`） |
| **1–2** | 2 | **`AF_INET` = 2** |
| **3–6** | 4 | **`F0 00 00 01`** |
| **7–8** | 2 | **客户端端口** |
| **合计** | **9** | — |

★★★ **⇒ 与报告 110 的注释**完全吻合** ✓**
```
报告 110（`Servers.cpp` 的引用）：
  "应答规格 **15|u16 2|addr|addr / 1f|u16 3|addr|addr**"
        ↓
★★★ 本报告：**`0x15` 15 字节** / **`0x1F` 9 字节** ✓
   ⇒ 但报告 110 记的是 "`1f|u16 **3**`" 而代码是 `AF_INET = **2**`
   ⇒ ★ **记录为差异**（可能报告 110 的 "3" 是别的意思）
```

### ★★★ 标准的 STUN binding 应答（第 297–322 行）

```cpp
if (size < 20 || request[0] != 0 || request[1] != 1) return true;      // ★ 非 0x0001 ⇒ 忽略

std::vector<std::uint8_t> response;
appendU16(response, **0x0101**);                                       // ★ 类型
appendU16(response, **12**);                                           // ★ 长度 12
response.insert(response.end(), request + 4, request + 20);            // ★ 复制 transaction id（16 字节）
appendU16(response, **0x0001**);                                       // 属性：MAPPED-ADDRESS
appendU16(response, **8**);                                            // 属性长度 8
response.push_back(**0**);                                             // 保留
response.push_back(**1**);                                             // 族 = IPv4
appendU16(response, ntohs(endpoints->client.port));                    // ★ 端口（**大端**）
appendU32(response, ntohl(endpoints->client.ipv4));                    // ★ IP（**大端**）
```

★★★ **⇒ 标准 STUN（RFC 5389）的 `MAPPED-ADDRESS` 应答，**32 字节**：**
```
`0x0101`(2) + `12`(2) + transaction id(16) + `0x0001`(2) + `8`(2)
+ `0`(1) + `1`(1) + port(2) + ip(4) = **32** ✓
```

★★ **⇒ 注意：**这里用**大端**（`appendU16`/`appendU32`）,而 DW STUN 用**小端**（`appendLeU16`）。**

---

## 四、★★★★★ **`LobbyServer` 的 13 服务 + 2 辅助组成**

### 4.1 ★★★★★ 完整成员表（`Servers.hpp:88-108`）

```cpp
Demonware::ServiceRegistry registry_;
Demonware::LobbyProtocol protocol_;
Demonware::ContentUnlock2Service contentUnlock2_;      // 0x1C
Demonware::Friends2Service friends2_;                  // 0x09 + 0x44
Demonware::MatchmakingService matchmaking_;            // 0x15 + 0x8A
Demonware::InstantMessageService instantMessage_;      // 0x06
Demonware::MarketplaceService marketplace_;            // 0x50 + 0x5D
Demonware::Profiles2Service profiles2_;                // 0x08
Demonware::StatsService stats_;                        // 0x04
Demonware::Storage2Service storage2_;                  // 0x0A
Demonware::TencentService tencent_;                    // 0x47
Demonware::TitleUtilitiesService titleUtilities_;      // 0x0C
SharedRoomClient sharedRoomClient_;                    // ★ 共享房间客户端
DedicatedBookingDispatcher bookingDispatcher_;         // ★ 预订分发器
Demonware::Unknown0BService unknown0B_;                // 0x0B
Demonware::AckOnlyServices ackOnly_;                   // ★ 空 ack 兜底
```

### ★★★★★ 完整的 15 个成员

| # | 成员 | 服务 ID | 报告 |
|---|---|---|---|
| **1** | `registry_` | — | 109 |
| **2** | `protocol_` | — | 116 |
| **3** | `contentUnlock2_` | **`0x1C`** | 117 |
| **4** | `friends2_` | **`0x09` + `0x44`** | 121 |
| **5** | `matchmaking_` | **`0x15` + `0x8A`** | 110 |
| **6** | `instantMessage_` | **`0x06`** | 112 |
| **7** | `marketplace_` | **`0x50` + `0x5D`** | 114–115 |
| **8** | `profiles2_` | **`0x08`** | 119 |
| **9** | `stats_` | **`0x04`** | 118 |
| **10** | `storage2_` | **`0x0A`** | 121 |
| **11** | `tencent_` | **`0x47`** | 117 |
| **12** | `titleUtilities_` | **`0x0C`** | 117 |
| **13** | `unknown0B_` | **`0x0B`** | 112–113 |
| **14** | `sharedRoomClient_` | — | 待读 |
| **15** | `bookingDispatcher_` | — | 待读 |
| **16** | `ackOnly_` | 多个 | 109 |

★★★ **⇒ 实际是 **16 个成员**（含 `registry_` 与 `protocol_`）。**
**⇒ 其中 **12 个是 Demonware 服务**（`0x1C` `0x09` `0x44` `0x15` `0x8A` `0x06` `0x50` `0x5D` `0x08` `0x04` `0x0A` `0x47` `0x0C` `0x0B` = **14 个服务 ID**）。**

★★ **⇒ 与报告 122 的"15 个服务有完整实现"**吻合**（这里是 14 个 + `ClanService` 在 `Servers.cpp` 里 `static` 创建 = **15**）。**

### ★★★★★ `ClanService` 的 `static` 创建（第 430–434 行）

```cpp
{
    static const auto clanService = std::make_shared<Demonware::ClanService>(session_);
    clanService->registerTasks(registry_);
}
```

★★★ **⇒ **`static`** ⇒ **只创建一次**（跨多个 `LobbyServer` 实例共享）。**
**⇒ 这是一个**刻意的单例**（因为战队数据要跨连接保持）。**

---

## 五、★★★★★ **`submitBooking` 的"软失败"放宽**

### 5.1 ★★★★★ 完整实现（第 487–507 行）

```cpp
void LobbyServer::submitBooking(const std::string_view command)
{
    log("CODOL_GAME_BOOKING command=" + std::string(command));
    if (OlMod::processRole() == OlMod::ProcessRole::Client)
    {
        const auto userId = session_.snapshot().userId;
        if (!sharedRoomClient_.setReady(userId, true))
        {
            // ★★ 2026-10-07 17:1x -- **不再当死路**：靶场（solo coop）实测走到这里时
            //   `setReady` 失败（该流程不经过"进房→房主 ready"两步），booking 被直接
            //   return 掉 ⇒ SessionStart/map-load 全没跑 ⇒ 客户端随后报
            //   「**你的关卡文件与服务器的不同！退出连接**」（战斗服还在等一张从未加载的图）。
            //   改动（唯一）：失败只记日志、**继续 submit**
            log("CODOL_GAME_SESSION booking_ready_soft_failed (continuing) user=" +
                std::to_string(userId));
        }
    }
    static_cast<void>(bookingDispatcher_.submit(std::string(command)));
}
```

### ★★★★★ 完整的因果链

```
靶场（solo coop）流程**不经过"进房→房主 ready"两步**
        ↓
★★★ `setReady` 失败 ⇒ 旧实现**直接 return**
        ↓
★★★ `SessionStart` / map-load **全没跑**
        ↓
★★★★★ 客户端报 **「你的关卡文件与服务器的不同！退出连接」**
   （战斗服还在等一张**从未加载的图**）
        ↓
★★★ 修复：失败只记日志、**继续 submit**
        ↓
★★★ 判据（逐字）："靶场 mmstart 后出现 **`CODOL_GAME_SESSION accepted=true`**
   + 战斗服 **`map asset load requested map=coop_train_mp_firingrange`**"
```

★★ **⇒ 关键：**`coop_train_mp_firingrange`** ⇒ 与报告 079 的 `[map_loads_ratio]` 的
`mp_firingrange` **相关**（但这里是 `coop_train_` 前缀）。**

---

## 六、★★★★★ **`Auth3` 补丁只在 auth3 分支安装**

### 6.1 ★★★★★ 完整注释（第 649–658 行，逐字）

```cpp
// Installed **HERE** rather than for every claimed name: these three patches **blind the
// client's certificate and authentication checks**, and **Auth3 is the only path that needs
// them**. Claiming STUN used to drag them in too, which is **a lot of blast radius for a UDP
// echo**. Still early enough -- the client cannot validate anything until it talks to the
// server this branch is about to return.
if (!Demonware::installAuth3ClientPatches())
{
    log("**Could not install the three recovered CODOL Auth3 client patches.**");
    return nullptr;
}
```

★★★★★ **⇒ 三个精确的设计理由：**
```
① ★★★ 这三个补丁**致盲客户端的证书与身份验证检查**
   ⇒ **只有 Auth3 路径需要它们**
        ↓
② ★★ 以前**认领 STUN 时也会装** ⇒ "**a lot of blast radius for a UDP echo**"
        ↓
③ ★ 但**仍然足够早**（客户端在跟这个服务器说话之前无法验证任何东西）
```

★ **⇒ 第 ② 条是**"最小爆炸半径"的明确表述**。**

★★ **⇒ 且失败时**返回 `nullptr`**（不认领）⇒ 客户端走真 socket。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★ **`Createserver` 入口** | 角色门控（`runsBackend`）+ `Claimed <host> as <kind>` 日志 |
| 2 | ★★★ **"Refused to apply..." 只打一次** | `std::call_once` ⇒ ✓ 与报告 107 对应 |
| 3 | ★★★ 四个 `CODOL_*` 导出 | `RequestProfileReload` / `GetProfileReloadStatus` / `RequestInventoryRefresh` / `GetInventoryRefreshStatus` ⇒ ✓ 与报告 082/108 **一致** |
| 4 | ★★★★★ **`DllMain` 两个补丁** | `installCodolStartupPatches()` + `installForcedRecordValidatorPatch()` |
| 5 | ★★★★★ **门补丁的原始字节** | **`55 8B EC 51 53` → `B0 01 C2 04 00`**（= `mov al,1; ret 4`）⇒ 补报告 107 未给的原始字节 |
| 6 | ★★★★★ **`classifyHostname` 七级** | `lobby.codol.localhost` / 域名白名单 / `stun.*` / `auth3.*` / `auth.*` / `cs.*` / `lsg.*`+`lobby.*` |
| 7 | ★★ 域名白名单 | **必须含 `demonware.net` 或 `qq.com`**，否则 `none` |
| 8 | ★★★★★ **五个环境变量开关** | `OLMOD_CLAIM_LOBBY` / `EXTERNAL_STUN` / `EXTERNAL_AUTH3` / `CLAIM_LEGACY_AUTH`（+ `OLMOD_*` 累计 **29 个**） |
| 9 | ★★★★★ **第 1 条的完整理由** | 客户端拨 `lobby.codol.localhost`，但门控要 `demonware.net`/`qq.com` ⇒ **`Createserver` 拒绝** ⇒ `Localnetworking` 穿透 ⇒ **`21/*` 与 `11/*` 全注册但从未收到请求** ⇒ `ConfigureSession` 从不发送 ⇒ `sessionConfigured=false, bound=false, port=0` ⇒ **"no amount of address work reaches it"** |
| 10 | ★★★★★ **第 5 条（legacyAuth）的理由** | `ServerFactory` 对 legacyAuth **无条件**返回 **`PendingStreamServer`（纯文本）**，而本客户端 auth 是 **TLS** ⇒ **认领即抢走登录** ⇒ "**login is the one link that currently works**" |
| 11 | ★★★★★ **第 4 条（auth3）的理由** | 认领即强制整条不透明路径（运行期自签证书 + **三个验证点补丁**）⇒ 2026-09-03 **"cost a remote player his evening"** ⇒ 因补丁**门控在 3.3.3.3 文件名**而 OLfinal 跑 `out.exe` ⇒ **`tlsv1 alert unknown ca`** ✓ 与报告 104 同一事件 |
| 12 | ★★★★★ **DW STUN `0x14` → `0x15`** | **15 字节**：`0x15` + `AF_INET(2)` + **`F0 00 00 01`** + 客户端端口 + **服务端 IP** + **服务端端口** |
| 13 | ★★★★★ **DW STUN `0x1E` → `0x1F`** | **9 字节**：`0x1F` + `AF_INET(2)` + `F0 00 00 01` + 客户端端口 |
| 14 | ★★★ 与报告 110 的差异 | 报告 110 记 "`1f\|u16 **3**`"，代码是 `AF_INET = **2**` ⇒ **记录为差异** |
| 15 | ★★★★ **标准 STUN binding** | **32 字节**：`0x0101` + `12` + transaction id(16) + `0x0001` + `8` + `0` + `1` + port(2) + ip(4)，**大端** |
| 16 | ★★★ 端序对比 | DW STUN 用**小端**（`appendLeU16`），标准 STUN 用**大端**（`appendU16`/`appendU32`） |
| 17 | ★★★★★ **`LobbyServer` 16 成员** | 12 个 Demonware 服务 + `registry_` + `protocol_` + `sharedRoomClient_` + `bookingDispatcher_` + `ackOnly_` |
| 18 | ★★ **14 个服务 ID** | `0x1C` `0x09` `0x44` `0x15` `0x8A` `0x06` `0x50` `0x5D` `0x08` `0x04` `0x0A` `0x47` `0x0C` `0x0B`（+ `ClanService` 的 `0x03` = **15**） |
| 19 | ★★★ **`ClanService` 是 `static`** | 只创建一次（跨 `LobbyServer` 实例共享）⇒ 战队数据跨连接保持 |
| 20 | ★★★★★ **`submitBooking` 软失败** | 靶场流程**不经过"进房→房主 ready"** ⇒ `setReady` 失败 ⇒ 旧实现 `return` ⇒ **SessionStart 没跑** ⇒ **「你的关卡文件与服务器的不同！退出连接」** ⇒ 改为**继续 submit** |
| 21 | ★★ 判据 | **`CODOL_GAME_SESSION accepted=true`** + 战斗服 **`map asset load requested map=coop_train_mp_firingrange`** |
| 22 | ★★★★★ **Auth3 补丁只在此分支** | "these three patches **blind the client's certificate and authentication checks**" ⇒ **只有 Auth3 需要**；以前 STUN 也装 ⇒ "**a lot of blast radius for a UDP echo**" |

---

## 八、结论

### 1. ★★★★★ **`classifyHostname` 的门控解释了"所有服务都没被调用"**

```
客户端拨 `lobby.codol.localhost`
        ↓
★★★ 但门控要求 `demonware.net` 或 `qq.com` ⇒ **拒绝**
        ↓
★★★★★ ⇒ `21/1..21/16` 与 `11/1..11/13` **全注册但从未收到请求**
   ⇒ `ConfigureSession` 从不发送 ⇒ **"no amount of address work reaches it"**
```

★ **⇒ 这与 memory 的「外部方案验证已结项」的结论**完全吻合**，且给出了精确机制。**

### 2. ★★★★★ **五个环境变量开关控制认领行为**（默认全部"不认领"）

### 3. ★★★★★ **legacyAuth 认领即破坏**（纯文本服务器 vs TLS 客户端）

### 4. ★★★★★ **auth3 认领强制整条不透明路径**（自签证书 + 三补丁）

★ **⇒ 且 2026-09-03 那次"cost a remote player his evening"与报告 104 是同一事件。**

### 5. ★★★★★ **DW STUN 的两种应答（15 / 9 字节）与标准 STUN 的 32 字节**

### 6. ★★★★ **`LobbyServer` 有 15 个服务 + 2 个辅助**

### 7. ★★★★ **`submitBooking` 的软失败放宽**（靶场流程不经过进房）

### 8. ★★★ **Auth3 补丁的"最小爆炸半径"**（只在此分支安装）

---

## 九、下一步

- `DedicatedBookingDispatcher.cpp`（926 行）+ `.hpp`（62 行）
- `SharedRoomClient.cpp`（180）/ `.hpp`（41）/ `SharedRoomControl.cpp`（426）/ `.hpp`（76）/ `SharedRoomHost.cpp`（49）/ `SharedRoomSessionOwner.cpp`（163）/ `.hpp`（66）
- `IServer.hpp`（2 行）
