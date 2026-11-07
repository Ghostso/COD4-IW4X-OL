# 学习报告 015 — launch_chain.py 全文 + 名字三处契约 + 交付包缺口总账

**学习范围**：`bundle\launch_chain.py` 全文（25,009 B / 445 行）+ `IdentityConfig.hpp` + `payload\` 核查
**核心发现**：★★★ **交付包有 5 处硬缺口**，其中 3 处必崩；★★★ **名字必须三处字节相同**

---

## 一、`launch_chain.py` 的完整流程（`main()` 行 212-440）

```
0   保真检查：Injector32 / 客户端 exe / ol_room_owner 三个文件必须存在
    stop_all()                              ← 先杀干净
    │
0   fake_auth_tls.py          → 127.0.0.1:3074 (TCP)    [OLMOD_SKIP_AUX=1 时跳过]
0b  stun_local.py --ports 3074,3478,19302 (UDP)          [OLMOD_SKIP_AUX=1 时跳过]
      绑不上 3074 ⇒ return 7
1   ol_room_owner.exe         → 28970                    [OLMOD_SKIP_AUX=1 时跳过]
      20s 内没监听 ⇒ return 4
2   nt10.py --root GAME --secs 2400 --delay 0 --apis API
      ★ 客户端由 nt10.py 拉起（唯一能读会话密钥的路径）
      等 28962 (client bridge) 120s ⇒ return 5
2b  force_display_name.py --watch 150 --apply <name> --encoding utf-8
3   dedicated（默认跳过，`--no-dedicated`；或 `--combined` 表示进程内）
      start_dedicated.ps1  ← ★ 交付包内不存在
      等 28961 120s ⇒ return 6
```

### 退出码表

| 码 | 含义 |
|---|---|
| 2 | 三个必需文件有一个缺失 |
| 3 | fake auth 20s 内没监听 |
| 4 | room owner 20s 内没监听 |
| 5 | 客户端 120s 内没到 bridge 端口 |
| 6 | dedicated 120s 内没监听 |
| 7 | local STUN 20s 内没绑上 UDP 3074 |

★ **每个码对应一个明确的失败点** —— 这是好的工程实践。

---

## 二、★★★ 为什么客户端必须经 `nt10.py`（行 12-22）

> `CodolGame.py launch-dedicated` 起三个进程，但**它的客户端直接走 `Injector32.exe`，
> 没有 `nt10.py`**。那对我们来说 **LSG 就断了**：
> 会话密钥**无法在服务器端推导** —— **1499 × 336 = 503,664 组合，0 命中**，
> 且真实密钥**不出现在 16,514 字节的客户端流中的任何位置**。
> **唯一来源就是 `nt10.py` 从客户端进程内存读到 `secrets.txt`。**
>
> 所以客户端**必须**从 `nt10.py` 来。其他两个（room owner + dedicated）只消费
> `SessionStart`，可以走上游路径。

★★★ **这是整条链的"第一性原理"**：
```
会话密钥每会话随机、不可推导
    ↓
只能从客户端内存读
    ↓
只有 nt10.py 会读
    ↓
客户端必须由 nt10.py 拉起
    ↓
（因此不能用老外的 CodolGame.py launch-dedicated）
```

### ★ 与报告 009 的冲突（仍然是最大疑问）

**注释说**（行 34-36）：
> run `nt10.py` -> launches the client **through `Ayria\Injector32.exe -qa`**,
> inheriting the chain environment

**报告 009 实测**：包内**没有** `inject_ayria.on`，也没有 `NT10_INJECT`，
⇒ `nt10.py` 走 `subprocess.Popen([client.exe])`，**不经 Injector32**。

★★ **两者不可能同时成立。** 三种解释（报告 009 已列）：
- A. 甲方运行目录里有 `.on` 文件，包里没有
- B. `nt10.py` 版本不同
- C. 第二条插件加载路径

★ **本报告新增第四个可能**：
**D. 注释是旧的** —— 2026-10-05 22:41 写下时确实走 Injector32，
后来（2026-10-05 02:10 的注入开关注释之后）改成了 Popen 直起，
**但 `launch_chain.py` 的注释没跟着改**。

★★ **证据支持 D**：`nt10.py:1367-1374` 的注释时间戳是 **02:10**（比 22:41 早），
且写着"**默认走原「直接起 exe」**"。**"原"= 一直如此。**

**⇒ 最可能：`launch_chain.py` 的 docstring 是**过期描述**，
`nt10.py` 一直是直起，插件靠**另一条路**加载（或根本不加载）。**

---

## 三、★★ 已有证据反证"插件不加载则必死"

报告 009 推论链最后一步是"→ 客户端连不上大厅 → 卡住"。

**但这个包里有一条实测记录**（行 244-247）：

> MEASURED 2026-10-05 14:57:53, the ONLY time today the client ever dialled UDP 28960:
> ```
> 14:50:06 [combined/game-server] game server frame hook installed
> 14:54:19 [combined/game-server] ConfigureSession accepted bytes=22 endpoint=28960
> 14:57:53 [combined/game-server] udp packet peer=2130706433:22011 bytes=29 type=13
> 14:57:53 [combined/game-server] dtls peer=... state=established replyBytes=114
> 14:57:54 [combined/game-server] dtls rejected ... DTLS data authentication failed
> ```
> Note: role `combined`, a **ONE-process deployment** —— and the client dialled with
> **NO `mmbook`/`mmstart`/`SessionStart`** anywhere in that log.

★★★ **这是关键反证**：
- `[combined/game-server]` 前缀 = **进程内插件**在运行
- `game server frame hook installed` = 插件成功 hook 了 `Com_Frame`
- **说明插件确实加载过**

★★ **所以插件加载是**发生过的**。报告 009 的"插件不加载"结论
只在"包内字面 + 无外部状态"条件下成立 —— 甲方运行时一定有额外条件。**

---

## 四、`--combined` 与三个 role 的真实语义（行 227-249）★ 极重要

### 引用 `game_server.md:197`（逐字）

> 默认 `combined` 保留旧部署；`client` 只安装最小 `Com_Frame` hook 服务 session capture，
> **不运行 gameplay server**；`dedicated` 安装 gameplay hook、监听控制端口
> 并在游戏线程消费 `SessionStart`

### ★★ 推论（作者原文）

> So under `OLMOD_PROCESS_ROLE=client` —— **what our chain has been using** ——
> **the CLIENT PROCESS RUNS NO GAME SERVER AT ALL.**
> The game server lives **only in the second (dedicated) process**,
> **which this client never talks to.**

★★★ **这是一条极其重要的诊断**：

```
role=client       → 只有 session capture，没有 gameplay server
role=dedicated    → 有 gameplay server，但要和客户端通信
role=combined     → ★ 一个进程里全有
```

**`run.cmd` 传 `--no-dedicated`** ⇒ role 是 `client` ⇒ **根本没有战斗服**。

★★ **这解释了"进大厅但打不了局"**！
**不是战斗服坏了，是根本没起。**

★ 修正路径：用 `--combined`（一个进程内全有）而不是 `--no-dedicated`。

---

## 五、`--no-dedicated` 的来历（行 220-224）

> Single-variable isolation switch: the **20:17 round reached the lobby** with the
> dedicated starting **4.5 minutes LATER**, while **20:45/20:48/20:50 all had it up
> before the client's LSG connect and all died** with
> `致命错误 / 与大厅服务失去连接` after serving exactly **one frame (`71/4`)**.
> `--no-dedicated` separates the two.

### ★★ 实测时间线

| 轮次 | dedicated 何时起 | 结果 |
|---|---|---|
| 20:17 | 客户端连上后 **4.5 分钟后** | ★ **进大厅** |
| 20:45 | 客户端连前 | 死于 `71/4`（与大厅服务失去连接） |
| 20:48 | 客户端连前 | 同上 |
| 20:50 | 客户端连前 | 同上 |

★★★ **结论：dedicated 起得太早会杀死会话。**

★ **可能原因**（我的推断）：
- dedicated 起来后**抢先绑定了某些端口**（28961/28962/28970）
- 或它**抢先修改了共享状态/内存**
- 或它的 `Com_Frame` hook **和客户端插件冲突**（同一个 EXE！）

★★ **"`71/4` 恰好一帧"** 说明握手第一步成功、第二步失败 ——
**这是典型的"端口被抢或 hook 冲突"**。

★ **`--no-dedicated` 是**隔离变量**的临时开关，不是最终方案。**

---

## 六、`--combined` 是正解（行 227-249）

**注释说 `combined` 是"旧部署（legacy）"**，但实测**只有 `combined` 那次客户端真的
拨了 UDP 28960**（14:57:53）。

★★ **`combined` 是唯一让 gameplay server 在客户端进程内运行的 role** ——
**没有跨进程通信，没有端口冲突，没有 hook 冲突。**

★ **`--combined` 唯一的代价**：进程内多跑一个 gameplay server，内存/性能开销。

---

## 七、★★★ 名字的三处契约（`IdentityConfig.hpp:62-84`）—— 全包最硬的约束

### 契约原文（行 81-84）

> ⚠ **三处必须逐字节相同，缺一即进不去服**（拒单形态见本节 §①）：
> 1. **本常量**；
> 2. **启动器 `restart_chain.ps1` 的 `OLMOD_DISPLAY_NAME` 且 `..._ENC='utf-8'`**；
> 3. **`force_display_name.py` 写进 16 字节字段的字节**（编码 utf-8）

### 三处对照（交付包内实测）

| # | 位置 | 交付包内的值 | 状态 |
|---|---|---|---|
| 1 | `IdentityConfig.hpp:85` `DefaultUsername` | **`"SGamingSH0X"`** | 现役 |
| 2 | `launch_chain.py:377` `OLMOD_DISPLAY_NAME` 默认 | **`"Easily_"`** | ★★ **失配！** |
| 2 | `launch_chain.py:389` `..._ENC` 默认 | `"utf-8"` | ✓ |
| 3 | `force_display_name.py` 写入 | 由 2 决定 ⇒ `"Easily_"` | ★★ **失配！** |

★★★ **`SGamingSH0X` ≠ `Easily_`** ⇒ **交付包按字面执行，connect 名字校验必失败**。

### 拒单形态（行 48-49，实测原文）

```
connect userinfo name does not match the session roster
  name="TGlmZXRpbWWBUg==" (GBK)   vs   expected="TGlmZXRpbWXkuLc=" (UTF-8)
```

★ **base64 解码**：
- `TGlmZXRpbWWBUg==` = `Lifetime` + `81 52` = **GBK 的 `Lifetime丷`**
- `TGlmZXRpbWXkuLc=` = `Lifetime` + `E4 B8 B7` = **UTF-8 的 `Lifetime丷`**

★★ **同一个名字，两种编码，字节不同 ⇒ 拒单。**

### ★★★ 名字演变史（一张完整的时间线）

| 日期 | 名字 | 编码 | 字节数 | 说明 |
|---|---|---|---|---|
| 10-7 前 | `Alwaysoffline` | GBK | 13 | 老外默认 |
| 10-7 10:3x | `AdministraClient` | - | 16 | ★ 对齐客户端自造名 |
| 10-7 11:0x | `Lifetime` | GBK→UTF-8 | 8 | 甲方要求前缀 |
| 10-7 15:5x | `Lifetime丷` | **UTF-8** | 11 | 线编码整体切 UTF-8 |
| 10-7 16:5x | `Lifetime丷` | UTF-8（v13） | 11 | 全线 UTF-8 |
| 10-11 25000 | `Lifetime_` | utf-8 | 9 | ★ **从未部署** |
| 10-11 | `Sunl1ght` | utf-8 | 8 | 现役（当时） |
| 10-12 | `内裤再美终究装逼` | **GBK** | **16** | ★ **正好装满无 NUL** |
| 10-13 2005 | `SGamingSH0X` | utf-8 | 10 | ★ **现役（源码）** |
| ? | `Easily_` | utf-8 | 7 | ★ **`launch_chain.py` 里的** |

★★★ **`Easily_` 出现在 `launch_chain.py:372` 的注释里**：
> ★ 2026-10-11（V1.101）-- 默认名 = `Easily_`（甲方指定，改自 `Lifetime丷`）

★ **但 `IdentityConfig.hpp` 的 10-13 记录说现役是 `SGamingSH0X`** ——
**比 `Easily_` 更晚**。

★★ **⇒ `launch_chain.py` 的默认名**落后于**源码常量 2 天**。**

---

## 八、★★ 16 字节定长字段的两种坑态

### 坑 1：`内裤再美终究装逼` = GBK **正好 16 字节，无 NUL**

> 字段是 **16 字节定长**（`Auth3Protocol.cpp:207-211` 只从 ticket 取 `subspan(14, 16)`），
> 而 `内裤再美终究装逼` 的 GBK 恰为 **16 字节（正好装满，无 NUL 终止）**。

★ **无 NUL 终止的字符串在某些 API 下会越界读** —— 这是个隐藏风险。

### 坑 2：UTF-8 中文装不下

> 先做过 UTF-8 版：**UTF-8 全名 24 字节装不下**，只能取前 5 字；
> 甲方要求"**显示全**" ⇒ 换 GBK。

★ **`内裤再美终究装逼` (8 字) × 3 字节 = 24 > 16** ⇒ UTF-8 装不下。
★ **GBK = 8 × 2 = 16** ⇒ 正好。

★★ **所以编码选择不只看渲染，还要看能否装下。**

### ★ 两个渲染管线（行 51-52）★★ 无法调和

> 名字被多处消费：**只有大厅右上角是 GBK 渲染**；
> 房间内角色名/右侧面板/榜单/列表 **全部是 UTF-8 渲染**（GBK 字节在这些地方显示成 `▮R`）。

★★★ **一份字段不可能同时满足两种渲染。** 作者的取舍：
> ③ 字段一份字节不可能同时满足两种渲染 ⇒ **先保大头（全 UTF-8）**，
>   右上角的「丷」留给**分缓冲定向写入**专项

★ **这就是 `force_display_name.py --tag` 模式的由来**（报告 014 第六节）：
**先给每份拷贝打标签，建立"界面↔地址"映射，再按拷贝分编码写。**

★★ **纯 ASCII 名字（`SGamingSH0X`/`Easily_`）没有这个问题** ——
**两种编码字节相同**。这是作者最终选 ASCII 的原因。

---

## 九、★★★ 交付包缺口总账（本报告最重要的产出）

### 硬缺口（必崩）

| # | 缺口 | 位置 | 后果 |
|---|---|---|---|
| **1** | `_rsa.txt` 不存在 | `fake_auth_tls.py:117` | **启动第一行 `FileNotFoundError`** |
| **2** | `C:\Program Files\Python314\python.exe` 不存在 | `launch_chain.py:72` | **所有 Popen 全失败** |
| **3** | `start_dedicated.ps1` 全包不存在 | `launch_chain.py:425` | **步骤 3 必然 exit≠0**（但 `--no-dedicated` 可绕过） |
| **4** | `OLMOD_GAME_ROOT` 默认 `D:\repo\03-live\client\TESTOL` 不存在 | `launch_chain.py:69` | **`SystemExit`（在 `--help` 之前就抛）** |
| **5** | `inject_ayria.on` 不存在 | `nt10.py:1373` | 插件不加载（报告 009） |

### 静默降级（不崩但不对）

| # | 问题 | 位置 | 后果 |
|---|---|---|---|
| **6** | `display_name()` 两个 game 候选都不存在 | `fake_auth_tls.py:209` | 名字恒 `Client青` |
| **7** | `--needle` 默认 `AdministraClient` | `force_display_name.py:157` | 非 `Administrator` 账户扫不到 |
| **8** | ★★ `OLMOD_DISPLAY_NAME` 默认 `Easily_` ≠ 源码 `SGamingSH0X` | `launch_chain.py:377` | **名字校验拒单** |

### ★ 数量统计

- **5 处必崩**
- **3 处静默降级**
- **0 处自动恢复**

★★★ **结论：这个交付包按字面执行，一步都走不通。**
但**这不是"包坏了"** —— 它是**把甲方开发目录里的文件挑了一部分复制出来**，
**依赖的相对路径和外部文件全部指向开发环境**。

---

## 十、`OLMOD_SKIP_AUX` —— 与我们方案对接的接口（行 282-284, 305-306, 334-336）

```python
if os.environ.get("OLMOD_SKIP_AUX") == "1":
    say("OLMOD_SKIP_AUX=1 -> skip fake_auth_tls.py and stun_local.py")
```

注释（行 283）：
> **2026-10-20：走他们的大厅时，auth / STUN 都归他们（3074 不能抢）。**

注释（行 335-336）：
> **2026-10-21：走他们大厅时不用我们的房间/候选那套；
> 而且 ROOM_PORT(=28970) 与他们的 DS 撞端口。**

★★★ **这就是"融合"的现成接口！**

```
OLMOD_SKIP_AUX=1
    ⇒ 跳过 fake_auth_tls (3074)
    ⇒ 跳过 stun_local (3074)
    ⇒ 跳过 ol_room_owner (28970)
    ⇒ 只留：nt10.py 拉客户端 + force_display_name + (dedicated)
```

★★ **这正好对应"只替换战斗服"的需求**：
- 我们的链提供 auth / lobby / STUN
- 外部方案提供**进程内战斗服**（`--combined`）
- **`OLMOD_SKIP_AUX=1` + `--combined`** = 我们的大厅 + 他们的战斗服

★ **前提**：`OLMOD_GAME_ROOT` 指向正确、Python 路径修好、
名字三处对齐、且 `--combined` 时插件要能加载。

---

## 十一、`payload\` 的完整内容（55 文件）

### 顶层

| 文件 | 大小 | 作用 |
|---|---|---|
| `Injector32.exe` | 126,464 | Ayria 注入器 |
| `Bootstrapper32.dll` | 159,744 | ★ 32 位引导器（扫 `Plugins\`） |
| `Bootstrapper64.dll` | 204,288 | 64 位版（本游戏不用） |
| `ol_room_owner.exe` | 283,648 | 房间所有者 |
| `ol-mod-runtime-manifest.json` | 28,209 | 运行时清单 |

### `Plugins\`（★★ 四个进程内插件）

| 插件 | 大小 |
|---|---|
| `Alwaysoffline.Localnet32` | **4,189,184** (4.0 MB) |
| `CodolGameServer.Localnet32` | **6,834,176** (6.5 MB) |
| `Localnetworking.Ayria32` | 519,168 |
| `Platformwrapper.Ayria32` | 543,232 |

★ **`CodolGameServer` 6.5 MB 是最大的** —— gameplay server 全在这里。

### `Assets\`

| 路径 | 内容 |
|---|---|
| `Alwaysoffline\Identity.json` | `{"username":"Alwaysoffline"}` ★ 迁移种子 |
| `Alwaysoffline\1004\MarketplaceSkus.json` | **2.5 MB** 商城 |
| `Alwaysoffline\1004\Server\*.info` | 12 个服务器配置文件 |
| `Platformwrapper\Platform.json` | ★ 见下 |
| `OlMod\GameScripts\` | 41 个 Lua（gametype 11 + maps 21 + common） |

### ★★★ `Platform.json`（256 B）—— 关键常量

```json
{
  "schemaVersion": 1,
  "titleId": 1004,
  "gameVersion": 42,
  "zoneId": 83886082,
  "serverId": 1,
  "platformUserId": "01100001DEADC0DE",
  "authEndpoint": "formal-zone-auth.codol.qq.com:3074",
  "lobbyEndpoint": "formal-zone-lsg.codol.qq.com:3074"
}
```

★★ **`platformUserId = "01100001DEADC0DE"`** ——
**正是记忆里"LSG/房间层使用平台 ID `0x01100001DEADC0DE`"的那个值。**

★ **`zoneId = 83886082 = 0x05000002`**
★ **`gameVersion = 42`**
★ **两个 endpoint 都指向 `:3074`** —— 与 `fake_auth_tls.py` / `stun_local.py` 完全对应。

★★ **注意：`display_name()` 读 `platformUserId` 后 `.lstrip("0")`** ⇒
**`"01100001DEADC0DE"` → `"1100001DEADC0DE"`**（★★ **前导 0 被去掉，变成 15 位！**）

★★★ **这是一个潜在 bug**：`1004\1100001DEADC0DE\Identity.json` 这个路径**不存在**
（包内 `1004\` 下只有 `MarketplaceSkus.json` 和 `Server\`）。

⇒ **`display_name()` 的第一候选必落空**，走第二候选 `1004\*\Identity.json`（也空），
走第三候选 `Identity.json` 的 `username` = **`"Alwaysoffline"`**。

★★ **所以交付包里名字会是 `Alwaysoffline`**（不是 `Client青`，也不是 `Easily_`）。

★ **报告 011 第六节的结论需要修正**：不是 `Client青`，是 **`Alwaysoffline`**。

---

## 十二、这一块的结论

### 架构层面（★★ 最重要）

1. **`role=combined` 是唯一能让 gameplay server 在客户端进程内跑的 role**；
   **`role=client`（`--no-dedicated` 用的）根本没有战斗服。**
2. **dedicated 起得早会杀死会话**（20:45/48/50 全死于 `71/4`）。
3. **`OLMOD_SKIP_AUX=1` 是与我们方案对接的现成开关**（让出 3074 和 28970）。

### 契约层面（★★★ 最硬的）

4. **名字必须三处逐字节相同**（源码常量 / `OLMOD_DISPLAY_NAME` / 写进内存的字节），
   **缺一即进不去服**（拒单原文有）。
5. **16 字节定长字段**：UTF-8 中文装不下（24 字节），GBK 能装（16 字节）；
   **装满是合法的（无 NUL）**。
6. **两种渲染管线（右上 GBK / 其余 UTF-8）无法用一份字节满足** ⇒ 纯 ASCII 名字免于此难。

### 交付包层面（★★★ 本报告最大产出）

7. **5 处必崩 + 3 处静默降级**，按字面执行**一步都走不通**。
8. 根因：**从开发目录挑文件复制，路径全部指向开发环境**。
9. ★ **`platformUserId.lstrip("0")` 是个隐藏 bug**：`01100001DEADC0DE` → `1100001DEADC0DE`。

---

## 十三、待验证（关键）

- [ ] ★★★ **`inject_ayria.on` 之谜**：甲方环境一定有，包里没有。
      **最可能解释 D：`launch_chain.py` docstring 过期**（`nt10.py` 一直是直起）。
- [ ] ★★ **`launch_chain.py` 的 `Easily_` vs `IdentityConfig.hpp` 的 `SGamingSH0X`**
      —— 哪个是最后的？`Easily_` 注释说 10-11，源码说 10-13 `SGamingSH0X`。
- [ ] ★★ **`--combined` 是否真能让我们进图**（14:57 那次 dtls 认证失败）
- [ ] `platformUserId.lstrip("0")` 的意图（去掉前导 0 是 bug 还是有意？）
- [ ] `ol-mod-runtime-manifest.json`（28 KB）的 `start_dedicated.ps1` 无命中 ⇒ 部署脚本里也没它
- [ ] `MarketplaceSkus.json` 2.5 MB 的内容（商城数据，与进图无关？）
