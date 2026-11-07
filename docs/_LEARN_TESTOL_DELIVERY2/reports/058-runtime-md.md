# 学习报告 058（重开）— `source\.agents\modules\runtime.md`（48,090 B）

**学习范围**：`.agents\modules\runtime.md` 第 1–120 行（分发/启动 + 双进程）
**性质**：全实测（**ol-mod 的权威技术规范**）
**★★★ 本报告收录**标准启动的精确约束**、**六个 Winsock hook**、**mutex 改名机制**

---

## 一、★★★★★ `source\.agents\` 的完整规模

| 文件 | 字节 |
|---|---|
| **`AGENTS.md`** | **118,015** |
| **`modules\game_server.md`** | ★★★ **223,587** |
| `modules\reverse_engineering.md` | 89,517 |
| **`modules\runtime.md`** | **48,090** |
| `modules\game_server_coverage.md` | 21,180 |
| `modules\gsc.md` | 21,617 |
| `modules\backend.md` | 19,203 |
| `pipelines\codol.dot` | 14,587 |
| **50 个 `research\*.md`** | （6 个最大的：special-rewards 27 KB / interactables 24 KB / publicprofile_ddl 23 KB / dw3_feasibility 32 KB / teleporter-links 18 KB / entry 16 KB） |

★★★ **⇒ `.agents\` 总计 **59 个文件 / 0.92 MB**，是**整个项目最密集的文档区**。**

★ **⇒ `game_server.md`（223 KB）是**单一最大的文档**。**

---

## 二、★★★★★ 标准启动的精确约束（第 7 行，逐字）

```markdown
标准启动使用原版 `Injector32.exe`，工作目录为游戏根目录，只传
`codoMP_client_shipRetail.exe` 路径，不添加参数。`CODOLBackend.Ayria32` 和旧的
运行时 hotload 不是当前链路；`CodolGame.py launch-inventory` 只是 `launch` 的兼容别名。
```

### ★★★★★ 四条精确约束

| # | 约束 | 内容 |
|---|---|---|
| **1** | 用**原版** `Injector32.exe` | 不用自研替代 |
| **2** | **工作目录 = 游戏根目录** | `cwd=GAME` |
| **3** | **只传客户端路径** | `Injector32.exe "<client>"` |
| **4** | ★★★ **不添加参数** | **`不添加参数`** |

★★★ **⇒ 第 4 条与 `nt10.py:1416-1426` 的注释**完全一致**：**
> **"Do NOT add more arguments: Injector32 fails with ERROR_FILE_NOT_FOUND
> on the argument COUNT"**

★ **⇒ 这是**第三次独立确认**"不能给注入器加参数"。**

### ★★ 两个已废弃的组件（第 7 行）

```
CODOLBackend.Ayria32         ← ★ 不是当前链路
旧的运行时 hotload            ← ★ 不是当前链路
```

★★ **⇒ `CODOLBackend.Ayria32` 是一个**历史上存在但现在不用**的插件名。**

### ★ `launch-inventory` 是别名

```
CodolGame.py launch-inventory  只是  launch 的兼容别名
```

---

## 三、★★★★★ `Localnetworking` 的完整实现约束（第 9–18 行）

```markdown
`Localnetworking.Ayria32` 已由 xmake target `ol_localnetworking` 源码化，构建物为
`LocalnetworkingRe.Ayria32`，stage 时覆盖到兼容文件名。实现保持归档二进制的
`onStartup/onInitialized/onMessage`、六个 Winsock hook、`.Localnet32/Createserver`
发现链和无 virtual destructor 的 2019 `IServer::Endpoints` ABI；`IServer` 的唯一共享
定义在 `src/shared/LocalnetServer.hpp`。运行根、Plugins、Logs 和 Assets 均从当前 DLL
路径推导，不再写死 `./Ayria`。自动化 fixture 已验证构建物为 PE32、三个 export、
Localnet32 枚举、hostname claim、240/8 synthetic DNS、六个真实 Mhook hook、同-server
fan-out，以及 TCP 和非阻塞 UDP 的 `ping/pong` 往返与来源 endpoint 回填；尚未用该重建 DLL 完成 CODOL 自然链路
实跑，因此不能把归档组件的运行证据直接转移给重建物。归档 DLL 仍保留在
`distribution/legacy` 作为哈希固定的对照证据，但不再进入 stage。
```

### ★★★★★ 六项实现约束

| # | 约束 | 内容 |
|---|---|---|
| **1** | **三个导出** | `onStartup` / `onInitialized` / `onMessage` |
| **2** | ★★★ **六个 Winsock hook** | （未在此列出具体名字） |
| **3** | **发现链** | `.Localnet32` / `Createserver` |
| **4** | ★★★ **2019 `IServer::Endpoints` ABI** | **无 virtual destructor** |
| **5** | `IServer` 唯一定义 | **`src/shared/LocalnetServer.hpp`** |
| **6** | ★ 路径推导 | 运行根/Plugins/Logs/Assets **从 DLL 路径推导**，不写死 `./Ayria` |

### ★★★★★ 自动化 fixture 的八项验证（逐字）

```
① PE32
② 三个 export
③ Localnet32 枚举
④ hostname claim
⑤ 240/8 synthetic DNS
⑥ 六个真实 Mhook hook
⑦ 同-server fan-out
⑧ TCP 和非阻塞 UDP 的 ping/pong 往返与来源 endpoint 回填
```

★★★ **⇒ 第 ⑤ 条"**240/8 synthetic DNS**"是一个精确的网络常量：**
```
240.0.0.0/8   ← 这是 OLDMOD_SYNTHETIC_DNS=1 时的"黑洞"网段
```

★ **⇒ 与上一轮报告 026 的 `OLMOD_SYNTHETIC_DNS` 语义**完全一致**（1 = 黑洞 240.0.0.0/4... 实际是 /8）。**

### ★★★★★ 关键的诚实声明（第 16–18 行）

```
尚未用该重建 DLL 完成 CODOL 自然链路实跑，因此不能把归档组件的运行证据
直接转移给重建物。归档 DLL 仍保留在 `distribution/legacy` 作为哈希固定的
对照证据，但不再进入 stage。
```

★★★ **⇒ 三条重要信息：**
```
① ★★★ **尚未用重建 DLL 完成 CODOL 自然链路实跑**
② ★★ **不能把归档组件的运行证据直接转移给重建物**
③ `distribution/legacy` 保留归档 DLL 作**哈希固定的对照证据**，但**不进入 stage**
```

★★ **⇒ 第 ① 条解释了为什么交付包的 `Localnetworking.Ayria32` 可能"缺 bind 代码"（上一轮记忆）：**
**⇒ 重建物**还没实跑验证过**。**

---

## 四、★★★★ `Platformwrapper` 的实现约束（第 20–39 行）

### 4.1 ★★★ 保留的符号（第 22–24 行）

```
只保留 CODOL EXE 已确认动态消费的
  Invoke / CreateObj / InitCrossContextByOpenID
  onStartup / onInitialized / onMessage
和对应三处 Mhook
        ↓
★ **52 个通用 Steam exports 没有进入实现**
```

★★★ **⇒ 六个导出 + 三处 Mhook，**砍掉了 52 个 Steam 导出**。**

★ **⇒ 这与报告 053 的 6 个导出**完全吻合**。**

### 4.2 ★★★★★ 归档 DLL 的四个精确发现（第 24–27 行，逐字）

```
归档 DLL i64 进一步确认 Tencent 对象只有 15-slot vtable、
byte/wide string 均先按 caller capacity 截断复制再回写完整长度，
TerSafe `CreateObj(0)` 分配 `0x858` bytes，
`setInitInfo` 分别写 `uin +0x0C`、`gameVersion +0x10` 和 64-bit sink `+0x18`。
```

### ★★★★★ 四个精确的技术事实

| # | 事实 | 值 |
|---|---|---|
| **1** | Tencent 对象 vtable | ★ **15-slot** |
| **2** | 字符串处理 | **先按 caller capacity 截断复制，再回写完整长度** |
| **3** | `CreateObj(0)` 分配 | **`0x858`（2,136）字节** |
| **4** | `setInitInfo` 写入三个字段 | **`uin +0x0C`** / **`gameVersion +0x10`** / **64-bit sink `+0x18`** |

★★★ **⇒ 第 2 条是一个**经典的 API 契约**：**
```
先按调用方声明的 capacity 截断复制
        ↓
再回写**完整长度**（不是截断后的长度）
        ↓
★ 这与 Windows 的 `strcpy_s` / `StringCchCopy` 语义**不同**
```

### 4.3 ★★★ `Platform.json` 的职责（第 29–31 行）

```
新 `Ayria/Assets/Platformwrapper/Platform.json` 集中持有
title、game/zone/server tags、认证 endpoint 和稳定 platform user ID；
旧 `UserID.txt` 只作为迁移输入，`Username.txt` 不再进入 CODOL-only 插件。
platform ID 是客户端 room/OpenID 兼容身份，backend profile 继续唯一持有显示名。
```

★★★ **⇒ 三条重要信息：**
```
① `Platform.json` 集中持有 5 类信息
② ★ 旧 `UserID.txt` 只作**迁移输入**，`Username.txt` **不再使用**
③ ★★★ **platform ID = room/OpenID 兼容身份；backend profile 唯一持有显示名**
```

★★ **⇒ 第 ③ 条与 `fake_auth_tls.py` 的 `display_name()` 逻辑**完全一致**（报告 045）。**

### 4.4 ★★★★★ 一次**完整的自然运行验证**（第 33–38 行，逐字）

```
clean 自然运行 `.runtime/natural-match/20260809_rebuilt_platformwrapper_v1/` 中
client/dedicated 均加载重建 DLL，Auth/frontend、QuickMatch、ready、client-native
allocation、`mmbook/mmstart`、`SessionStart`、`mp_crash_tropical/sd` world 和
snapshot 全部成功。随后对同一 client 的只读内存核验确认 room member identity
`+0x10/+0x14` 与内嵌 `MatchMakingInfo +0x208/+0x20C` 均为
`0x00000000DEADC0DE`，修复了旧失败样本中的零 internal ID。
该证据只覆盖 CODOL-only 表面，不提高 52 个未迁移 Steam exports 的完成度。
```

★★★ **⇒ 八项全部成功的验证：**
```
① Auth/frontend
② QuickMatch
③ ready
④ client-native allocation
⑤ mmbook/mmstart
⑥ SessionStart
⑦ mp_crash_tropical/sd world
⑧ snapshot
```

★★★ **⇒ 且内存核验了**四个精确偏移**：**
```
room member identity  : +0x10 / +0x14
MatchMakingInfo       : +0x208 / +0x20C
        ↓
★ 四个值都是 **`0x00000000DEADC0DE`**
```

★★ **⇒ `0xDEADC0DE` 与报告 017 的 `platformUserId = "01100001DEADC0DE"` **低 32 位一致**。**

★★★ **⇒ 这修复了"旧失败样本中的零 internal ID"。**

---

## 五、★★★★★ 双进程启动的 mutex 机制（第 48–58 行）

### 5.1 ★★★ 启动顺序（第 48–50 行）

```
CodolGame.py launch-dedicated 是当前 shared room owner + client + dedicated 生命周期入口。
launcher 先启动独立 `ol_room_owner.exe` 并确认 loopback IPC 端口就绪，
再启动 client，最后以 `OLMOD_PROCESS_ROLE=dedicated` 启动游戏服务进程。
```

★★★ **⇒ 三步顺序：**
```
① ol_room_owner.exe（等 loopback IPC 端口就绪）
② client
③ dedicated（OLMOD_PROCESS_ROLE=dedicated）
```

### 5.2 ★★★★★ mutex 改名的完整机制（第 50–58 行，逐字）

```
CODOL 的 CRT initializer `CODOL_SingleInstance_Init 0x00B49820` 原本让所有进程创建
同一个全局 mutex；dedicated 的 `ol_game_server` 只在该角色下校验 CODOL PE timestamp、
image size、mutex 名称和 `WinMain 0x641E2A` guard bytes，然后把 dedicated 的 mutex
名称末位改为独立固定值，同时保持原生 `75 2D` 条件分支。client 与 `combined` 仍使用
原名称和原生单实例保护。旧版 `EB 2D` bypass 会被原子升级为独立 mutex 并恢复为 `75 2D`。
真实回归已验证结束 client 后 dedicated 保持存活，`CodolGame.py launch-client` 可只恢复
client 和 process state，不重启 authoritative world。
```

### ★★★★★ 六个精确的地址/字节

| # | 项 | 值 |
|---|---|---|
| **1** | CRT 初始化函数 | **`CODOL_SingleInstance_Init 0x00B49820`** |
| **2** | WinMain 地址 | **`0x641E2A`** |
| **3** | ★★★ **原生条件分支** | **`75 2D`**（`jne +0x2D`） |
| **4** | ★ 旧版 bypass | **`EB 2D`**（`jmp +0x2D`） |
| **5** | 校验项 | **PE timestamp / image size / mutex 名称 / guard bytes** |
| **6** | 改法 | **mutex 名称末位改为独立固定值** |

★★★ **⇒ 完整的 mutex 机制：**
```
CODOL_SingleInstance_Init 0x00B49820
        ↓
所有进程创建**同一个全局 mutex**
        ↓
dedicated 的 ol_game_server 校验四项
（PE timestamp / image size / mutex 名 / guard bytes）
        ↓
★★★ 把 dedicated 的 **mutex 名称末位改为独立固定值**
        ↓
★ 同时保持原生 `75 2D` 条件分支（不改成 EB）
```

★★★ **⇒ 且明确："旧版 `EB 2D` bypass 会被**原子升级**为独立 mutex 并**恢复为 `75 2D`**"。**

★ **⇒ 这是一个**关键的兼容性修复**：**
```
旧做法：把 `75 2D`（jne）改成 `EB 2D`（jmp）—— 硬绕过单实例检查
        ↓
★★★ 新做法：保留 `75 2D`，改 **mutex 名称末位** —— 让检查自然通过
```

★★ **⇒ 这与上一轮报告 044 的 P4 补丁（`75`→`90 90`）是**不同思路**：**
```
P4 补丁     →  NOP 掉跳转（硬绕过）
mutex 改名  →  改数据让检查通过（软绕过）
```

### 5.3 ★★★ `-qa` 的再次确认（第 57–58 行，逐字）

```
第二进程还使用 CODOL `WinMain` 原生支持的 `-qa` 参数越过 TCLS-only 启动门槛，
不另行 patch `WIN_NO_TCLS` 分支。
```

★★★ **⇒ 这是**第四次独立确认** `-qa` 的作用（前三次：报告 032/033、上一轮记忆）。**

★ **⇒ 且明确："**不另行 patch `WIN_NO_TCLS` 分支**"** —— 用原生参数而非打补丁。

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ `.agents\` 规模 | **59 文件 / 0.92 MB** |
| 2 | ★★ 最大文档 | **`game_server.md` 223,587 B** |
| 3 | ★★★★★ **标准启动四约束** | 原版 Injector / **cwd=GAME** / 只传客户端路径 / **不加参数** |
| 4 | ★ 已废弃组件 | `CODOLBackend.Ayria32` / 旧运行时 hotload |
| 5 | ★★★ `Localnetworking` 六约束 | 三导出 / **六个 Winsock hook** / `.Localnet32+Createserver` / **2019 IServer ABI（无虚析构）** / `LocalServer.hpp` / 路径从 DLL 推导 |
| 6 | ★★★ **synthetic DNS 网段** | **240/8** |
| 7 | ★★★★ **诚实声明** | **"尚未用重建 DLL 完成自然链路实跑"** |
| 8 | ★★ 归档保留 | `distribution/legacy`（哈希固定对照，**不进 stage**） |
| 9 | ★★★ `Platformwrapper` 六导出 | `Invoke`/`CreateObj`/`InitCrossContextByOpenID` + 三件套 |
| 10 | ★ 砍掉 | **52 个 Steam exports** |
| 11 | ★★★★ **Tencent 对象** | **15-slot vtable** |
| 12 | ★★★ 字符串契约 | **先按 capacity 截断复制，再回写完整长度** |
| 13 | ★★ `CreateObj(0)` 分配 | **`0x858`（2,136）字节** |
| 14 | ★★ `setInitInfo` 三字段 | **`uin +0x0C` / `gameVersion +0x10` / sink `+0x18`** |
| 15 | ★★★ 身份分工 | **platform ID = room/OpenID；backend profile = 显示名** |
| 16 | ★★★★★ **八项自然运行验证** | Auth/QuickMatch/ready/allocation/mmbook+mmstart/SessionStart/world/snapshot |
| 17 | ★★★ 内存核验四偏移 | **`+0x10`/`+0x14`** 和 **`+0x208`/`+0x20C`**，值全为 **`0x00000000DEADC0DE`** |
| 18 | ★★★ **mutex 机制** | `CODOL_SingleInstance_Init` **`0x00B49820`**，改 **名称末位** |
| 19 | ★★★ **原生分支 `75 2D`** | 旧版 `EB 2D` bypass 被**原子升级并恢复** |
| 20 | ★ WinMain | **`0x641E2A`** |
| 21 | ★★★ `-qa` 第四次确认 | **"不另行 patch `WIN_NO_TCLS` 分支"** |

---

## 七、结论

### 1. ★★★★★ **"标准启动不加参数"是第三次独立确认**

### 2. ★★★★ **`Localnetworking` 重建物"尚未完成自然链路实跑"**

★ **⇒ 这解释了为什么交付包的 `Localnetworking.Ayria32` 可能有问题。**

### 3. ★★★★★ **mutex 改名（而非 NOP 跳转）是更优雅的绕过方式**

```
保留 75 2D，改 mutex 名称末位 ⇒ 让检查自然通过
```

### 4. ★★★★ **`Platformwrapper` 的 Tencent 对象是 15-slot vtable**

### 5. ★★★ **字符串契约：先按 capacity 截断，再回写完整长度**

### 6. ★★★ **`0x00000000DEADC0DE` 在四个内存偏移验证通过**

---

## 八、下一步

- `runtime.md` 剩余（第 120 行起，约 900 行）
- `source\.agents\modules\game_server.md`（223 KB，最大）
- `source\.agents\modules\backend.md`（19 KB）
- `source\docs\devlog\`（中文开发历程）
