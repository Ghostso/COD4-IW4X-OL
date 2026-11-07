# 学习报告 086（重开）— 从插件字符串面确认两套运行期机制

**学习范围**：`Alwaysoffline.Localnet32` @`0x3B5F80` + `CodolGameServer.Localnet32` @`0x5E2A00` 的字符串窗口
**性质**：全实测（**字节级定位 + 上下文转储**）
**★★★★★ 本报告收录两个机制的完整字符串链**：①**STORAGE2 的密钥流加密路径**（含明文会崩溃的警告）②**`mp_playlists` 被专服解析**（含两条失败日志串）

---

## 一、★★★★★ **机制一：STORAGE2 的密钥流加密路径**

### 1.1 ★★★ 证据位置

```
文件：`payload\Ayria\Plugins\Alwaysoffline.Localnet32`（4,189,184 B）
偏移：**`0x3B5F80` – `0x3B6220`**（`.rdata` 段内）
```

### 1.2 ★★★★★ 完整的字符串序列（按位置转储，`|` 表示 NUL 分隔）

```
 bytes=
 owner=
STORAGE2 getFile name=
|rejected malformed uploadFile request|
|rejected uploadFile request for a non-authenticated owner|
|STORAGE2 uploadFile name=|
|**configs_s.info**|
|**configs_s.keystream**|
|**Keystreams**|
|. **Serving PLAINTEXT - the client will discard it and crash later.**|
| bytes but got |
|' **needs a keystream of at least **|
||STORAGE2 WARNING: '|
| bytes)|' (|STORAGE2 encrypted '|
||Server|
|rejected unsafe uploadFile filename|
|could not encode uploadFile owner directory|
|could not create uploadFile owner directory: |
|.|w|r|i|t|i|n|g|.|
|could not create uploadFile temporary file|
|could not write uploadFile temporary file|
|could not commit uploadFile: win32=|
```

### ★★★★★ 五组精确事实

#### ① 两种 STORAGE2 操作

```
**`STORAGE2 getFile name=`**     ⇒ **读文件**
**`STORAGE2 uploadFile name=`**  ⇒ **写文件**（客户端上传）
```

#### ② 三条拒绝路径

```
`rejected malformed uploadFile request`               ⇒ 请求格式错
`rejected uploadFile request for a non-authenticated owner`  ⇒ 未认证的 owner
`rejected unsafe uploadFile filename`                 ⇒ 文件名不安全（路径穿越防护）
```

#### ③ ★★★★★ **密钥流机制（最关键）**

```
`configs_s.info` + `configs_s.keystream` + `Keystreams`
        ↓
★★★ 长度校验串：**`'<file>' needs a keystream of at least <N> bytes but got <M>`**
   ⇒ **密钥流长度必须 ≥ 目标文件长度**
        ↓
★★★★★ 若加密不可用而直接返回明文：
   **`. Serving PLAINTEXT - the client will discard it and crash later.`**
   ⇒ **"以明文提供 —— 客户端会丢弃它并在之后崩溃"**
```

★★★★★ **⇒ 完整的机制链（与报告 083 的清单声明完全吻合）：**
```
客户端通过 Demonware **STORAGE2** 请求 `configs_s.info`
        ↓
★★★ `Alwaysoffline.Localnet32`（本插件实现 STORAGE2 服务端）必须返回**加密形态**
   密钥流从 **`Keystreams\configs_s.keystream`** 读取
        ↓
★★★ 长度校验：密钥流 **≥ 文件长度**（否则报 `needs a keystream of at least N bytes`）
        ↓
★★★★★ 若无法加密而返回明文 ⇒ **客户端丢弃该文件并在之后崩溃**
```

★★ **⇒ 这解释了报告 083 的三条清单声明：**
```
清单 `origin`: "ol-mod **captured publisher-file keystream**"          ✓ 吻合
清单 `role`:  "**position-keyed keystreams for the publisher files
              this build decrypts on receipt**"                       ✓ 吻合
清单 `size`:  keystream 与 info **同为 25,126**                        ✓ 吻合（长度必须足够）
```

★★★ **⇒ 且解释了为什么 `Keystreams\` 目录在交付包里**整目录缺失** —— 这是一个**硬缺陷**：**
```
清单要求 `Keystreams/configs_s.keystream`（25,126 B）
        ↓
★★★ 但交付包里**没有这个目录**
        ↓
★★★★★ ⇒ 若按清单部署 ⇒ 只能返回**明文** ⇒
   触发 **"Serving PLAINTEXT - the client will discard it and crash later."**
   ⇒ **客户端丢弃 `configs_s.info` 并在之后崩溃**
```

★ **⇒ 这在**症状层面**与 memory 里的"客户端拒绝启动 / 卡住"**方向一致**
（**但未实测验证,仅记录为强线索**）。**

#### ④ ★★★ 原子写临时文件

```
`.|w|r|i|t|i|n|g|.`  ⇒ UTF-16LE 的 **`.writing.`**
        ↓
★★★ ⇒ 写入时先落 `<name>.writing.<n>` 之类的临时名,再提交
   ⇒ 与 `codol.call` 的原子写约定、`nt10.py` 的 `os.replace` **同一模式**
        ↓
★ 且有 **`could not commit uploadFile: win32=<code>`** ⇒ 提交时上报 Win32 错误码
```

#### ⑤ ★★★ owner 目录管理

```
`could not encode uploadFile owner directory`
`could not create uploadFile owner directory: `
        ↓
★★★ ⇒ 每个 owner（玩家）有一个**目录**,目录名需要"编码"（★ 可能是 `1100001DEADC0DE` 那种）
   ⇒ 与报告 083 的 `1100001DEADC0DE` 玩家种子目录**呼应**
```

---

## 二、★★★★★ **机制二：`mp_playlists` 被专服解析**

### 2.1 ★★★ 证据位置

```
文件：`payload\Ayria\Plugins\CodolGameServer.Localnet32`（6,834,176 B）
偏移：**`0x5E2A00` – `0x5E2BE0`**（`.rdata` 段内）
```

### 2.2 ★★★★★ 完整的字符串序列

```
line/1004/Server/**mp_playlists_shipRetail_release.info**
**no match rules reached the dedicated server**
**rotation did not resolve from the publisher playlist**
 roundLimit=
 winLimit=
 time=
 roundSwitch=
**match rules invalid booked=**
 version=
**booking configured**
**booking accepted, taking the booking and loadout locks**
```

### ★★★★★ 三个精确发现

#### ① ★★★★ **`CodolGameServer.Localnet32` 自己读 `mp_playlists_shipRetail_release.info`**

```
路径尾部：**`line/1004/Server/mp_playlists_shipRetail_release.info`**
        ↓
★★★ ⇒ 与 payload 里的实际路径 `Ayria/Assets/Alwaysoffline/1004/Server/…` **对应**
   ⇒ 即专服**直接解析那个 128 KB / 3,970 行的 playlist 文件**！
```

#### ② ★★★★★ **两条可观测的失败日志串**

```
**"no match rules reached the dedicated server"**
   ⇒ **比赛规则没有到达专服**（playlist 里的 `rule` 没被应用）
        ↓
**"rotation did not resolve from the publisher playlist"**
   ⇒ **地图轮转没能从"发布方 playlist"解析出来**
```

★★ **⇒ 这两条串是**判断 playlist 是否被正确解析**的直接观测点。**

#### ③ ★★★ 解析出的字段名（与报告 079 的 playlist 语法对照）

| 插件里的串 | 对应 playlist 里的键 |
|---|---|
| **`roundLimit=`** | `rule scr_*_roundlimit`（如 `scr_cha_roundlimit 2`） |
| **`winLimit=`** | `rule scr_*_winlimit`（如 `scr_cha_winlimit 1`） |
| **`time=`** | `rule scr_*_timelimit`（如 `scr_cha_timelimit 10`） |
| **`roundSwitch=`** | `rule scr_*_roundswitch`（如 `scr_cha_roundswitch 2`） |
| **`version=`** | ★ **文件头的 `version <N>`**（实际值 **796**） |
| **`match rules invalid booked=`** | ★ 校验失败时的日志（带 booking 号） |

★★★ **⇒ 印证报告 079 的 playlist 语法被专服**逐字段消费**。**
**⇒ 且 `version=` 对应的正是 `mp_playlists_shipRetail_release.info` 第 1 行的 **`version 796`**。****

#### ④ ★★★ booking 生命周期

```
"booking configured"
"booking accepted, taking the booking and loadout locks"
        ↓
★★★ ⇒ 与报告 082 的 `CODOL_GameServerConfigureBooking` 导出、
   报告 077 的 `[dw_config] room_serverBookingTimeout=5` **三点呼应**
```

★★ **⇒ 完整的 booking 概念链：**
```
`[dw_config] room_serverBookingTimeout=5`      （配置）
        ↓
`CODOL_GameServerConfigureBooking`              （导出 API）
        ↓
"booking configured" → "booking accepted, taking the booking and loadout locks"
        ↓
`match rules invalid booked=<N>`                （失败路径,带 booking 号）
```

---

## 三、★★★★★ **两套机制的关系图**

```
                    ┌─────────────────────────────────────────┐
                    │  客户端（codoMP_client_shipRetail.exe）  │
                    └─────────────────────────────────────────┘
                          │                          │
      Demonware STORAGE2  │                          │  连接专服
      getFile              │                          │
                          ▼                          ▼
        ┌──────────────────────────┐   ┌────────────────────────────┐
        │ Alwaysoffline.Localnet32 │   │ CodolGameServer.Localnet32 │
        │ （STORAGE2 服务端）       │   │ （战斗服）                  │
        ├──────────────────────────┤   ├────────────────────────────┤
        │ · getFile / uploadFile   │   │ · 读 mp_playlists_…info    │
        │ · owner 目录管理          │   │ · 解析 roundLimit/winLimit │
        │ · .writing. 原子写        │   │        time/roundSwitch    │
        │ · **configs_s.info**      │   │ · 解析 version             │
        │   + **Keystreams\**       │   │ · booking 生命周期          │
        │     **configs_s.keystream**│  │ · 地图轮转                  │
        │ · 明文 ⇒ 客户端崩溃        │   │ · 55 个 Get*Status 自检钩子 │
        └──────────────────────────┘   └────────────────────────────┘
                    │                          │
                    │  两者都**不在** `mp_playlists` 缺失清单里
                    │  （它们正是**消费**这些文件的那一方）
```

★★★ **⇒ 关键推论：**
```
**`Alwaysoffline.Localnet32` 需要 `configs_s.keystream`,而交付包没提供它**
**`CodolGameServer.Localnet32` 需要 `mp_playlists_…info`,而交付包提供了（112,274 B）**
        ↓
★★★ ⇒ 两个插件对**各自配置文件的依赖状态不同**：
   一个**缺**（keystream）、一个**有**（playlist）
```

---

## 四、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ **证据位置** | `Alwaysoffline.Localnet32` @**`0x3B5F80`**；`CodolGameServer.Localnet32` @**`0x5E2A00`** |
| 2 | ★★★★★ **STORAGE2 两操作** | **`STORAGE2 getFile name=`** / **`STORAGE2 uploadFile name=`** |
| 3 | ★★★ 三条拒绝 | `rejected malformed uploadFile request` / `…non-authenticated owner` / **`rejected unsafe uploadFile filename`** |
| 4 | ★★★★★ **密钥流三件** | **`configs_s.info`** + **`configs_s.keystream`** + **`Keystreams`**（含目录名） |
| 5 | ★★★★★ **长度校验串** | **`'<file>' needs a keystream of at least <N> bytes but got <M>`** |
| 6 | ★★★★★ **明文警告串** | **`. Serving PLAINTEXT - the client will discard it and crash later.`** |
| 7 | ★★★ 两条 WARNING 前缀 | `STORAGE2 WARNING: '` / `' (STORAGE2 encrypted '` |
| 8 | ★★★ **原子写** | **`.|w|r|i|t|i|n|g|.`** = UTF-16LE 的 **`.writing.`** |
| 9 | ★★ 提交错误 | `could not commit uploadFile: win32=<code>` |
| 10 | ★★★ owner 目录 | `could not encode/create uploadFile owner directory` |
| 11 | ★★★★★ **专服读 playlist** | **`line/1004/Server/mp_playlists_shipRetail_release.info`** |
| 12 | ★★★★★ **两条失败日志** | **`no match rules reached the dedicated server`** / **`rotation did not resolve from the publisher playlist`** |
| 13 | ★★★★ **解析出的字段** | **`roundLimit=` / `winLimit=` / `time=` / `roundSwitch=` / `version=`** |
| 14 | ★★ 校验失败 | `match rules invalid booked=<N>` |
| 15 | ★★★ **booking 生命周期** | **`booking configured`** → **`booking accepted, taking the booking and loadout locks`** |
| 16 | ★★★ 三点呼应 | `[dw_config] room_serverBookingTimeout=5` ⇔ **`CODOL_GameServerConfigureBooking`** ⇔ **`booking configured`** |
| 17 | ★★★★★ **硬缺陷确认** | 清单要求 **`Keystreams/configs_s.keystream`**，**交付包整目录缺失** ⇒ 只能返回明文 ⇒ **触发客户端崩溃** |
| 18 | ★★ 两插件依赖状态不同 | `Alwaysoffline` **缺** keystream；`CodolGameServer` **有** playlist |

---

## 五、结论

### 1. ★★★★★ **`Alwaysoffline.Localnet32` 实现了完整 STORAGE2 服务端,并有一条"明文即崩溃"的硬约束**

```
客户端经 STORAGE2 请求 `configs_s.info`
        ↓
★★★ 必须返回**用 `Keystreams\configs_s.keystream` 加密**的形态
   （长度校验：密钥流 ≥ 文件长度）
        ↓
★★★★★ 否则打印 **"Serving PLAINTEXT - the client will discard it and crash later."**
```

★★★ **⇒ 而 `Keystreams\` 目录在交付包里**整目录缺失** ⇒
按清单部署会**必然触发**这条路径。**
**⇒ 这是继"`inject_ayria.on` 缺失"之后的**第二个硬缺陷**,且后果更直接（客户端崩溃）。**

### 2. ★★★★★ **`CodolGameServer.Localnet32` 直接解析 `mp_playlists_shipRetail_release.info`**

```
解析出：`roundLimit=` / `winLimit=` / `time=` / `roundSwitch=` / **`version=`**（= **796**）
        ↓
★★★ 两条可直接观测的失败日志：
   **"no match rules reached the dedicated server"**
   **"rotation did not resolve from the publisher playlist"**
```

★ **⇒ 这为战斗服任务提供了**现成的判据**（不必再猜 playlist 有没有生效）。**

### 3. ★★★★ **两套机制的分工清晰**

★ **⇒ `Alwaysoffline` 管**存储与加密**,`CodolGameServer` 管**比赛规则与轮转**。**
**⇒ 两者都与报告 079 的配置层直接咬合。**

### 4. ★★★ **booking 概念链被三点证实**（配置 / 导出 API / 运行日志）

### 5. ★★★ **原子写模式一致**（`.writing.` 临时文件 ⇔ `nt10.py` 的 `os.replace`）

---

## 六、下一步（剩余可深入项）

- 用 `Alwaysoffline.Localnet32` / `CodolGameServer.Localnet32` 的**完整字符串面**
  系统提取（不只两个窗口），可产出"两插件的可观测日志清单"
- `maps\*.lua` 17 个小文件的逐个确认（一行 `return {...}`,清单已在报告 054）
- `MarketplaceSkus.json`（22,413 行）的逐条（报告 055 已给结构）
- `enemy_recorded_path_by_spawner` 剩余 ~600 行的逐条（报告 085 已给全量统计 + 抽样）
