# 学习报告 119（重开）— `Profiles2Service.cpp`（32,616 B / 669 行）

**学习范围**：`backend\Demonware\Profiles2Service.cpp` 全文（**669 行逐行读完**）
**性质**：全实测
**★★★★★ 本报告收录七个重大发现**：①**背包重置的自维持死循环与 `A=0` 判据** ②**档案规范形态 33,428 字节的精确算式** ③**`8/1` 的四种 framing 与 `OLMOD_PUBLIC_PROFILE_MODE`** ④**两个 ID 的精确值（平台 vs Demonware）** ⑤**`8/2` 的"非空即致命"** ⑥**`OLMOD_SERVE_PRIVATE_PROFILE` 的 opt-in** ⑦**rank/prestige/XP 的精确偏移**

---

## 一、★★★★★ **背包重置的自维持死循环**

### 1.1 ★★★★★ 完整注释（第 23–47 行，逐字）

```cpp
// ★ 2026-10-05 19:45 -- 断掉"背包每次登录都被重置"的自维持死循环。
//
// 现场与全部证据：`1A-DSH\01-findings\定因-背包重置是自维持死循环-20261005-1945.md`
//
// CODOL 一旦判「您的帐户检测到数据异常，现已修复，但是您需要重新配置您的背包」，
// 就会把公开档案重置成**第一个 typed u32 = 0** 的形态，并通过 Profiles2 `8/3` 回传：
//
//     `08 00 00 00 00 | 08 01 00 00 00 | 08 01 00 00 00 | 08 <crc> | 13 08 <len> | <zlib blob>`
//       ^^^^ **A = 0**
//
// 盘上实测三份（`02-证据\profile-reset-20261005-1945\`）：**1405 B / 1404 B / 1404 B**，
// 首个 u32 全 = 0，而且**客户端自己下一轮也解析不出块**（声明块数 = 0）。
//
// 对照甲方 18:47 配好的完好档案（`Publicprofile.configured`，**1511 B**）：
//     `08 04 00 00 00 | ...`   **A = 4 = 军牌四项齐**
//     解压后 `0x1126` bit0 `onboard_complete` = 1、`0x111D` bit0 `un_marketplace` = 1、
//     军牌 = **16646 / 16639 / 15961 / 26236**
//
// `A` 的取值分布（**六份档案实测**）：**完好 4 / 出厂 2 / 2019 原版 1 / 重置产物 0**。
//
// 从前是「客户端吐 0 -> 服务端照存 0 -> 下次 `8/1` 原样发回 0 -> 客户端又判异常」，
// 每登一次转一圈，配置永远留不住。**存这份 0 没有任何价值**，所以默认拒收，
// 保住上一份好档案；`OLMOD_SAVE_RESET_PROFILE=1` 可恢复旧行为（纯开关，无需重编）。
```

### ★★★★★ 完整的死循环

```
客户端判"数据异常" ⇒ **把公开档案重置成 `A = 0`** ⇒ 通过 `8/3` 回传
        ↓
服务端**照存 0**
        ↓
下次 `8/1` **原样发回 0**
        ↓
★★★ 客户端**又判异常**
        ↓
★★★★★ ⇒ **每登一次转一圈,配置永远留不住**
```

### ★★★★★ `A` 的完整取值分布（六份档案实测）

| `A` 值 | 含义 |
|---|---|
| **`4`** | ★★★ **完好**（**军牌四项齐**） |
| **`2`** | **出厂** |
| **`1`** | **2019 原版** |
| **`0`** | ★★★ **重置产物** |

★★★ **⇒ 四个精确值对应四种档案状态。**

### ★★★★★ 两份档案的字节对照

| 档案 | 大小 | 首字段 |
|---|---|---|
| **重置产物**（三份） | **1405 / 1404 / 1404 B** | ★★ **`A = 0`** |
| **完好档案**（`Publicprofile.configured`） | ★ **1511 B** | ★★ **`A = 4`** |

★★ **⇒ 且完好档案解压后的三个精确事实：**
```
`0x1126` bit0 `onboard_complete` = **1**
`0x111D` bit0 `un_marketplace` = **1**
军牌 = **16646 / 16639 / 15961 / 26236**
```

★★ **⇒ 军牌四项与报告 114 的"档案被重置"记录**完全吻合** ✓**
（那里 card 从 `16646/16639/15961/26236` 变成 `30059/30060/30061`）

### ★★★★★ `looksLikeResetArtifact` 的精确判据（第 60–75 行）

```cpp
bool looksLikeResetArtifact(const std::span<const std::uint8_t> profile)
{
    // 骨架（本机实测）：`08 <u32 A=0> | 08 01 | 08 01 | 08 <crc> | 13 08 <len>`
    if (profile.size() < **26** || profile[0] != **0x08**)
        return false;
    const auto first = readLeU32(profile, 1);       // ★ 偏移 1（跳过 tag 0x08）
    if (first != **0**)
        return false;
    // 后续必须仍是合法骨架，免得把别的 0 开头形态误判成重置产物。
    static constexpr std::array<std::uint8_t, **11**> skeleton{
        0x08, 0x01, 0x00, 0x00, 0x00, 0x08, 0x01, 0x00, 0x00, 0x00, 0x08 };
    return std::equal(skeleton.begin(), skeleton.end(), profile.begin() + **5**);
}
```

★★★ **⇒ 三重判据：**
```
① `size >= 26` 且 `profile[0] == 0x08`
② **偏移 1 处的 u32 == 0**（即 `A = 0`）
③ ★★★ **偏移 5 起的 11 字节必须匹配骨架** `08 01 00 00 00 08 01 00 00 00 08`
        ↓
★★★ 理由（逐字）："免得把别的 0 开头形态误判成重置产物"
```

### ★★★ 拒收的处理（第 525–534 行）

```cpp
// ★ 2026-10-05 19:45 -- 拒收客户端的"重置产物"，见文件顶部那段说明。
// **照常回成功（客户端不会重传）**，只是**不覆盖**已存的好档案。
if (!saveResetArtifact() && looksLikeResetArtifact(*profile))
{
    AlwaysofflineRe::log("Profiles2 8/3: refused to overwrite Publicprofile with the client's reset artifact ...");
    return ServiceResponse{ .task = request.task };      // ★ 成功（非错误）
}
```

★★★ **⇒ 关键设计：**照常回成功**（否则客户端会重传）。**

---

## 二、★★★★★ **档案规范形态 33,428 字节的精确算式**

### 2.1 ★★★★★ 完整注释（第 89–91 行，逐字）

```cpp
// 规范形态（**33428 B = 9 + 5*4 + 6 + 32768 + 625**）：
//   `0A <u64 owner> | 08 <A> | 08 <0=未压缩> | 08 <1=formatVersion> |
//    08 <crc32(raw[4:])> | 13 08 <32768> | <raw 32768> | <tail 625>`
```

### ★★★★★ 完整的字节分解

| 部分 | 大小 | 内容 |
|---|---|---|
| **`0A <u64 owner>`** | **9** | tag `0x0A` + **8 字节 owner** |
| **`08 <A>`** | **5** | tag + u32 |
| **`08 <0=未压缩>`** | **5** | tag + u32 |
| **`08 <1=formatVersion>`** | **5** | tag + u32 |
| **`08 <crc32(raw[4:])>`** | **5** | tag + u32 |
| **`13 08 <32768>`** | **6** | tag `0x13` + `0x08` + u32 长度 |
| **`<raw 32768>`** | **32,768** | 原始数据 |
| **`<tail 625>`** | **625** | 尾部 |
| **合计** | ★★★ **33,428** | — |

★★★ **⇒ 算式验证：**
```
`9 + 5×4 + 6 + 32768 + 625`
= 9 + 20 + 6 + 32768 + 625
= **33,428** ✓
```

### ★★★ 三个精确常量（第 111–113 行）

```cpp
constexpr std::size_t CanonicalSize = **33428**;
constexpr std::size_t RawSize       = **32768**;   // = 32 KB
constexpr std::size_t TailSize      = **625**;
```

### ★★★★★ 上传形态的对照（第 87 行，逐字）

```cpp
//   * 客户端上传形态（本机实测 2026-10-07 10:42:16，**1774 B**）：
//       `08 <A> | 08 <1=zlib> | 08 <1=formatVersion> | 08 <crc> | 13 08 <len> | <zlib> | <tail 626>`
```

★★★★★ **⇒ 上传形态**没有 `0A <owner>` 前导,且 **`tail = 626`**（规范件是 **625**）。**

★★★ **⇒ 两个形态的差异：**
```
上传形态：`08 <A> | 08 <1=zlib> | 08 <1> | 08 <crc> | 13 08 <len> | <zlib> | <tail **626**>`
规范形态：`0A <owner> | 08 <A> | 08 <**0**=未压缩> | 08 <1> | 08 <crc> | 13 08 <**32768**> | <raw **32768**> | <tail **625**>`
        ↓
★★★ 三处差异：① 有无 owner 前导 ② 压缩标志（1 vs 0）③ tail 长度（626 vs 625）
```

### ★★★★★ 三条逐字节对照（第 80–96 行，逐字）

```
① 老外 C# 参考 `00-reference\third-party\reference\CodolLocalLobbyServer.cs`：
     `SavePublicProfile()` 上传 -> 解压 -> 规范入库；
     `ReadProfileResult()` 下发前把对象里的 u64 owner 补丁成**请求者 id**（`:653`）。
        ↓
② 归档规范件 `03-live\server\archive\05-baselines\WORKING-20261005-1421\
   baseline\player_profiles\public.result`：**33428 B**,owner = **0xE7C8A98A6B4C2D0E**。
        ↓
③ 客户端上传形态（本机实测 2026-10-07 10:42:16,**1774 B**）
```

★★ **⇒ 第 ② 条给出**归档规范件的 owner 值 = `0xE7C8A98A6B4C2D0E`**（= Demonware 账号 id）。**

### ★★★★★ 两条不完整的旧方案（第 93–96 行，逐字）

```
`body`     —— **裸上传件、无 owner 前导** => 客户端弹「数据异常」并重置；
`prefixed` —— **0A + 会话平台 id（不是客户端请求的 DW id）** => **无弹窗、也不生效**。
        ↓
★★★ 本转换把两条各自缺的东西补齐：**正确 owner + 规范体**。
```

★★★★★ **⇒ 两个失败模式**精确互补**：**
```
`body`      ⇒ 缺 owner ⇒ **弹「数据异常」并重置**
`prefixed`  ⇒ owner 错（用了平台 id）⇒ **无弹窗但不生效**
        ↓
★★★ 正解 = **正确 owner（DW id）+ 规范体**
```

---

## 三、★★★★★ **`8/1` 的四种 framing**

### 3.1 ★★★★★ 完整枚举（第 236–256 行，逐字）

```cpp
//   **`OLMOD_PUBLIC_PROFILE_MODE=canonical`** (default since 2026-10-07)
//                                       `0A <u64 owner>` + canonical storage body.
//                                       owner = **the id THIS request asked for**（客户端的
//                                       Demonware account id）；body = **33428 B** 形态。
//   **`OLMOD_PUBLIC_PROFILE_MODE=body`** 裸 `Publicprofile` 字节,无前缀。
//                                       Same shape as `getPrivateInfo()` (task 2, rank/level survives)
//   **`OLMOD_PUBLIC_PROFILE_MODE=prefixed`** `u64 session userId` 然后裸字节。这是上游
//                                       `getPublicInfos` 的做法,也是本文件 18:35 之前的做法。
//                                       **It produced NO anomaly warning, and also no persistence
//                                       -- the client appears to discard it.**
//   **`OLMOD_PUBLIC_PROFILE_MODE=off`** 回 **ZERO objects**。客户端然后没有档案可加载,
//                                       自己建一份并通过 `8/3` 上传（实测 17:25 与 17:31）
```

### ★★★★★ 四种模式的完整表

| 模式 | 形态 | 效果 |
|---|---|---|
| **`canonical`**（默认） | ★ `0A <u64 owner>` + **33,428 B 规范体** | ★★★ **正解** |
| **`body`** | 裸 `Publicprofile` 字节 | 与 task 2 同形,**rank/level 存活** |
| **`prefixed`** | `u64 session userId` + 裸字节 | ★★ **无弹窗但也无持久化**（客户端丢弃） |
| **`off`** | **零对象** | ★ 客户端**自己建一份并上传** |

★★★ **⇒ 第 3 条是关键：**"no anomaly warning, and also no persistence -- the client appears to discard it"**
**⇒ 即：**不报错 ≠ 生效**。**

### ★★★★★ 为什么需要这个开关（第 229–234 行，逐字）

```cpp
// WHY A KNOB. **Four framings were defensible while the right one was unknown, and each test
// costs a client restart.** Operator report 2026-10-05 18:4x:
//   「您的帐户检测到数据异常，现已修复，但是您需要重新配置您的背包」 + 新手引导又出现
// appeared **immediately after the reply switched from `prefixed` to `body`**, so the client is
// now actually **PARSING the profile and rejecting its content**.
// Being able to flip the framing from `nt10.py` (no rebuild) is what makes the next few rounds cheap.
```

★★★ **⇒ 三条精确事实：**
```
① ★★ **四种 framing 都曾合理**（因为不知道哪个对）,且**每次测试要重启客户端**
        ↓
② ★★★ 从 `prefixed` 切到 `body` **立即**出现「数据异常 + 新手引导」
   ⇒ 说明客户端**真的在解析档案内容并拒绝它**
        ↓
③ ★ **能从 `nt10.py` 翻转（无需重编）** ⇒ 让后续几轮变便宜
```

★ **⇒ 第 ③ 条是**"开关即实验"的设计哲学**（与报告 114 的 `OLMOD_MARKETPLACE_ANSWER_230` 同）。**

---

## 四、★★★★★ **两个 ID 的精确值**

### 4.1 ★★★★★ 完整注释（第 281–295 行，逐字）

```cpp
// `AuthSession::userId` is the **PLATFORM/OpenID** id (**0x01100001DEADC0DE = 76561201696194782**),
// but this client asks Profiles2 for its **Demonware account id**
// **0xE7C8A98A6B4C2D0E = 16701785630074219790**. Measured 2026-10-05 17:30:45 from the wire:
//
//     `LSG_REQUEST sequence=7 service=8 task=1 payload=0A0E2D4C6B8AA9C8E700`
//                                          ^^ tag 0x0A
//                                            ^^^^^^^^^^^^^^^^^^ **u64 LE = E7C8A98A6B4C2D0E**
//                                                              ^^ trailing zero
//
// The same value is this client's **`${CODOID(...)}`** in its login telemetry and the **`Owner`**
// of the marketplace inventory it writes, so it is **a property of the install, not of a session**.
```

### ★★★★★ 两个 ID 的完整对照

| ID | 值 | 十进制 | 来源 |
|---|---|---|---|
| **平台/OpenID** | ★ **`0x01100001DEADC0DE`** | **76,561,201,696,194,782** | `AuthSession::userId` |
| **Demonware 账号** | ★★ **`0xE7C8A98A6B4C2D0E`** | **16,701,785,630,074,219,790** | ★ 客户端请求里用的 |

★★★★★ **⇒ 这解决了报告 083/105 的"两个命名空间"问题：**
```
**平台 ID** = `0x01100001DEADC0DE`（我们的 `AuthSession`）
**Demonware 账号 ID** = `0xE7C8A98A6B4C2D0E`（客户端实际请求用的）
        ↓
★★★ 且明确"**the same value is this client's `${CODOID(...)}` in its login telemetry and
   the `Owner` of the marketplace inventory it writes**"
   ⇒ **是安装的属性,不是会话的属性**
```

### ★★★ 请求的精确字节（逐字）

```
`0A 0E 2D 4C 6B 8A A9 C8 E7 00`
 ^^ tag 0x0A
    ^^^^^^^^^^^^^^^^^^ u64 LE = `E7C8A98A6B4C2D0E`
                      ^^ trailing zero
```

★★ **⇒ 注意字节序：**`0E 2D 4C 6B 8A A9 C8 E7` 是 `0xE7C8A98A6B4C2D0E` 的**小端**。**

### ★★★ 为什么会有这个差异（第 441–445 行，逐字）

```cpp
// But `AuthSession::userId` here is the **platform/OpenID** id 0x01100001DEADC0DE,
// because our auth is the Python TLS shim (`fake_auth_tls.py`) and the laowai's
// `Auth3Protocol`, which recovers the Demonware account id from the client's own auth ticket
// (`Auth3Protocol.cpp:206 identity.userId = readU64(decoded, 6);`), **never runs**.
// **The laowai never hits this because for them the two ids are the same value.**
```

★★★★★ **⇒ 完整的因果：**
```
我们的 auth 走 `fake_auth_tls.py` ⇒ `Auth3Protocol` **不跑**
        ↓
★★★ ⇒ `identity.userId` 停在**平台 id** `0x01100001DEADC0DE`
   ⇒ 而客户端请求的是 **DW 账号 id** `0xE7C8A98A6B4C2D0E`
        ↓
★★★ ⇒ **两个 id 不匹配**
        ↓
★★★★★ ⇒ "**The laowai never hits this because for them the two ids are the same value.**"
```

★ **⇒ 第 ④ 条与报告 106 的"`DefaultUsername` 才是生效值"**同一根因**（`Auth3Protocol` 不跑）。**

### ★★★ `OLMOD_DW_ACCOUNT_ID`（第 296–316 行）

```cpp
// `OLMOD_DW_ACCOUNT_ID` overrides (hex, with or without `0x`, or decimal).
// **0 disables the self-lookup alias entirely**, which restores the exact pre-change behaviour
// (an unmatched `8/1` returns zero objects).
```

★★ **⇒ `OLMOD_*` 累计 **24 个**。**

### ★★★★★ `getPublicInfos` 的自查找回退（第 429–462 行，逐字）

```
"Consequence before this change: the client uploads its public profile on a timer
 (`8/3` -- observed 17:31:04 and 17:31:09, and `1004/1100001DEADC0DE/Publicprofile` was
 rewritten at 17:31:09) but its startup read (`8/1`) came back EMPTY, so **every relaunch
 started from defaults**. The class/loadout setup and everything else staged in the public
 profile therefore **did not survive a restart even though the file was on disk**."
        ↓
★★★ ⇒ 完整的症状：**文件在盘上,但每次重启都从默认开始**
```

★ **⇒ 且给出**边界（逐字）：**
```
"this emulator serves **one player**, so an unmatched id can only be the session user;
 when real multi-client rosters land this must become a **real per-user lookup**."
```

---

## 五、★★★★★ **`8/2` 的"非空即致命"**

### 5.1 ★★★★★ 完整注释（第 468–470 行，逐字）

```cpp
// CODREF: the current out.exe startup path treats **both error 800 and a non-empty task-2
// private profile as fatal**.  The captured live contract is an **empty successful reply**;
// task 7 remains the explicit by-user read.
if (!servePrivateProfile())
    return ServiceResponse{ .task = request.task };      // ★ 空成功
```

★★★★★ **⇒ 两种都是致命：**
```
`error 800` ⇒ **致命**
**非空**的 task-2 私密档案 ⇒ **致命**
        ↓
★★★ ⇒ 所以默认**回空成功**
```

### ★★★★★ 一次实测（第 501–503 行，逐字）

```
"MEASURED 2026-10-05 16:26: with the `writeU64(userId) + writeRaw(profile)` framing that
 getPublicInfos() uses, a **non-empty task-2 reply made the client exit during startup**
 (backend log stopped at `service=80 task=119`, **client process gone, no ComError line**)."
        ↓
★★★ ⇒ 精确症状：日志停在 **`service=80 task=119`**,**客户端进程消失,无 ComError**
```

### ★★★★★ 但 rank/prestige/XP **只在私密档案里**（第 195–205 行，逐字）

```cpp
// WHY THIS EXISTS. The player's rank / prestige / XP are **NOT in the public profile**.
// Measured 2026-10-05 by byte-comparing the live client blob against the reference profiles:
//   * live `Ayria\Assets\Alwaysoffline\1004\1100001DEADC0DE\Publicprofile` (**1918 B**, 4 typed u32
//     header) and the older `player_profiles\public.result` (**33428 B**) are **byte-identical across
//     `0x1200..0x1400`**; at the rank offsets **both read garbage** (`0x890000EA` / `0xEA0000EA`).
//   * `player_profiles\secure.result` (**32983 B**) carries clean values at the **SAME offsets**:
//         **`0x12EC` = `0x00A8B63C` = 11,056,700**   experience
//         **`0x1313` = 4**                          prestige
//         **`0x1317` = `0x46` = 70**                rank
//         **`0x131B` = 4**                          rankVersion
```

### ★★★★★ 四个精确的偏移与值

| 偏移 | 值 | 含义 |
|---|---|---|
| **`0x12EC`** | ★ **`0x00A8B63C` = 11,056,700** | **经验值** |
| **`0x1313`** | ★ **`4`** | **转生** |
| **`0x1317`** | ★ **`0x46` = 70** | **等级** |
| **`0x131B`** | ★ **`4`** | **rankVersion**（== `CodolProfile.RANK_VERSION`） |

★★★★★ **⇒ 且明确"公档在这四个偏移上读的是**垃圾**（`0x890000EA` / `0xEA0000EA`）"。**

★★ **⇒ 这解释了报告 118 的 `StatsService` 为什么需要 `lb 1000` 单独发等级/转生/战神分：**
```
公档里**没有** rank/prestige/XP
        ↓
★★★ 所以 `StatsService` 的 `lb 1000` 必须**独立提供**这些值
```

### ★★★ `OLMOD_SERVE_PRIVATE_PROFILE=1` 的 opt-in（第 210–214 行，逐字）

```cpp
// `getPrivateInfo` is task 2, and upstream deliberately answers it with an EMPTY reply, on the
// recorded basis that "out.exe startup treats both error 800 and a non-empty task-2 private
// profile as fatal". **That measurement is for out.exe / build 1649370, NOT for this
// 3.19.26.13 client**, so it is kept as the default and the feature is **opt-in** via
// `OLMOD_SERVE_PRIVATE_PROFILE=1`.
```

★★★★★ **⇒ 一个极其精确的**适用性判断**：**
```
那条实测是 **out.exe / build 1649370** 的
        ↓
★★★ **不是这个 3.19.26.13 客户端** 的
        ↓
⇒ 所以保持默认（空）,但**提供 opt-in 开关**
```

★ **⇒ 这是**"测量的适用范围"的明确区分**（与报告 114 的"权威源码 vs 实测"同类）。**

---

## 六、★★★★ **八个任务与文件操作**

### 6.1 ★★★ 8 个任务（第 328–359 行）

| task | 名称 |
|---|---|
| **1** | `getPublicInfos` |
| **2** | `getPrivateInfo` |
| **3** | `setPublicInfo` |
| **4** | `setPrivateInfo` |
| **5** | `deleteProfile` |
| **6** | `setPrivateInfoByUserID` |
| **7** | `getPrivateInfoByUserID` |
| **8** | `setPublicInfoByUserID` |

★★ **⇒ 4 个"无 ByUserID" + 3 个"ByUserID" + 1 个 delete。**

### ★★★ `profilePath`（第 598–603 行）

```cpp
return assetRoot_ / std::to_string(identity.titleId) / userIdDirectory(userId) / filename;
```

★★ **⇒ `<assetRoot>/<titleId>/<USERID大写>/<filename>`**
**⇒ 第三次出现相同的 `userIdDirectory`（前两次：报告 106、115）。**

### ★★★ `saveProfile` 的原子写（第 621–653 行）

```cpp
auto temporary = path;
temporary += L"**.writing**";
...
if (!MoveFileExW(temporary.c_str(), path.c_str(),
    **MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH**))
```

★★★ **⇒ **第四次出现**同一原子写约定**（前三次：报告 096、106、115）。**

### ★★★ `stripOptionalUserId`（第 655–667 行）

```cpp
if (payload.empty() || payload.front() != 0x0A)
    return std::vector<std::uint8_t>(payload.begin(), payload.end());    // ★ 无前导 ⇒ 原样

ByteBuffer input(payload);
std::uint64_t ignoredUserId{};
if (!input.readU64(ignoredUserId)) return std::nullopt;
const auto remaining = input.remaining();
return std::vector<std::uint8_t>(remaining.begin(), remaining.end());    // ★ 剥掉前导
```

★★ **⇒ 有 `0x0A` 前导 ⇒ 剥掉 `u64`；无 ⇒ 原样。**

### ★★★ `getPrivateInfoByUserId` 的**保留前导**（第 580–582 行）

```cpp
ByteBuffer object;
object.writeU64(userId);        // ★ 有前导
object.writeRaw(*profile);
```

★★★ **⇒ 与 `getPrivateInfo`（task 2）**相反**：**
```
`getPrivateInfo`（task 2）     ⇒ **裸档案,无 userId 前导**（因为非空会致命）
`getPrivateInfoByUserId`（task 7）⇒ **有 userId 前导**
```

★ **⇒ 理由（第 494–496 行）："That is what the reference lobby actually sent and what the
client accepted -- `lobby_server.py:246-252` reads the file and returns `[d]` verbatim"。**

### ★★★ `deleteProfile`（第 588–596 行）

```cpp
const auto userId = session_.snapshot().userId;
std::filesystem::remove(profilePath(userId, "Publicprofile"), error);
error.clear();
std::filesystem::remove(profilePath(userId, "Privateprofile"), error);
```

★★ **⇒ 删两个文件,恒回成功（不检查删除结果）。**

### ★★★ `crc32` 的计算（第 157–161 行）

```cpp
const auto crc = static_cast<std::uint32_t>(crc32(0,
    reinterpret_cast<const Bytef *>(raw.data()) + **4**,
    static_cast<uInt>(**RawSize - 4**)));
for (unsigned int index = 0; index != 4; ++index)
    raw[index] = static_cast<std::uint8_t>(crc >> (index * 8));
```

★★★★★ **⇒ 两个精确细节：**
```
① CRC 只算 `raw[**4**..]`（**跳过前 4 字节**）
② ★★★ **算完后把 CRC 写回 `raw[0..3]`**
        ↓
★★★ ⇒ 即：**`raw` 的前 4 字节是 CRC,但它本身不参与 CRC 计算**
```

★ **⇒ 这是一个**自包含的校验和**设计（前 4 字节存校验值）。**

### ★★★ 用 zlib（第 19 行 + 第 138–155 行）

```cpp
#include <zlib.h>
...
if (compression == **1**) {
    uLongf outSize = RawSize;
    if (uncompress(raw.data(), &outSize, ..., packed) != Z_OK || outSize != RawSize)
        return false;
}
else if (compression == **0**) {
    if (packed != RawSize) return false;
    std::copy_n(stored.begin() + 26, RawSize, raw.begin());
}
else return false;
```

★★ **⇒ `compression` 只有 **0（未压缩）与 1（zlib）** 两个值。**

---

## 七、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **背包重置死循环** | 客户端判异常 ⇒ 重置成 **`A=0`** ⇒ `8/3` 回传 ⇒ 服务端照存 ⇒ 下次 `8/1` 发回 ⇒ **又判异常** |
| 2 | ★★★★★ **`A` 四值** | **`4`=完好**（军牌四项齐）/ **`2`=出厂** / **`1`=2019 原版** / **`0`=重置产物** |
| 3 | ★★★ 两份档案大小 | 重置产物 **1405/1404/1404 B**；完好档案 **1511 B** |
| 4 | ★★★ 完好档案的三事实 | `0x1126` bit0 `onboard_complete`=**1** / `0x111D` bit0 `un_marketplace`=**1** / 军牌 **16646/16639/15961/26236** ✓ 与报告 114 吻合 |
| 5 | ★★★★ **`looksLikeResetArtifact` 三重判据** | `size ≥ **26**` + `profile[0]==**0x08**` + **偏移 1 的 u32 == 0** + **偏移 5 起 11 字节骨架** `08 01 00 00 00 08 01 00 00 00 08` |
| 6 | ★★★ 拒收仍回成功 | "**照常回成功（客户端不会重传）**,只是**不覆盖**已存的好档案" |
| 7 | ★★★★★ **规范形态 33,428 字节** | **`9 + 5×4 + 6 + 32768 + 625`** ✓ |
| 8 | ★★★ 三段结构 | `0A <u64 owner>`(9) + 4×(tag+u32)(20) + `13 08 <32768>`(6) + raw(32768) + tail(625) |
| 9 | ★★★★★ **上传形态对照** | **1774 B**,`08 <A> | 08 <**1=zlib**> | 08 <1> | 08 <crc> | 13 08 <len> | <zlib> | <tail **626**>` |
| 10 | ★★★ 三处差异 | 有无 owner 前导 / 压缩标志(**1 vs 0**) / tail(**626 vs 625**) |
| 11 | ★★★★★ **两个旧方案互补的失败** | `body` ⇒ **缺 owner ⇒ 弹「数据异常」并重置**；`prefixed` ⇒ **owner 错 ⇒ 无弹窗但不生效** |
| 12 | ★★★★ **四种 framing** | **`canonical`**(默认,正解) / `body` / `prefixed` / **`off`**（零对象 ⇒ 客户端自己建并上传） |
| 13 | ★★★★★ **`prefixed` 的精确症状** | "**no anomaly warning, and also no persistence -- the client appears to discard it**" |
| 14 | ★★★ 开关的理由 | 四种都曾合理,每次测试要重启客户端；从 `prefixed`→`body` **立即**出现「数据异常」⇒ **客户端真的在解析内容** |
| 15 | ★★★★★ **两个 ID 的精确值** | **平台/OpenID `0x01100001DEADC0DE` = 76,561,201,696,194,782**；**DW 账号 `0xE7C8A98A6B4C2D0E` = 16,701,785,630,074,219,790** |
| 16 | ★★★ 请求字节 | `0A 0E 2D 4C 6B 8A A9 C8 E7 00` ⇒ tag `0x0A` + **u64 LE** + trailing 0 |
| 17 | ★★★★★ **为什么两 id 不同** | 我们走 `fake_auth_tls.py` ⇒ `Auth3Protocol` **不跑** ⇒ `identity.userId` 停在平台 id ⇒ "**the laowai never hits this because for them the two ids are the same value**" |
| 18 | ★★ `OLMOD_DW_ACCOUNT_ID` | 可覆盖；**0 禁用自查找** ⇒ `OLMOD_*` 累计 **24 个** |
| 19 | ★★★★ **自查找回退的后果** | 文件在盘上但 `8/1` 回空 ⇒ **每次重启从默认开始** ⇒ class/loadout **不存活** |
| 20 | ★★ 边界声明 | "this emulator serves **one player**" ⇒ 多客户端时必须变**真正的按用户查找** |
| 21 | ★★★★★ **`8/2` 两种致命** | **`error 800`** 与 **非空 task-2 档案** ⇒ 所以默认**回空成功** |
| 22 | ★★★ 实测症状 | 2026-10-05 16:26 非空 task-2 ⇒ 客户端**启动中退出**（日志停在 **`service=80 task=119`**,**进程消失,无 ComError**） |
| 23 | ★★★★★ **rank/prestige/XP 只在私档** | 公档在四个偏移上读**垃圾**（`0x890000EA` / `0xEA0000EA`） |
| 24 | ★★★★★ **四个精确偏移** | **`0x12EC` = 11,056,700**(经验) / **`0x1313` = 4**(转生) / **`0x1317` = 70**(等级) / **`0x131B` = 4**(rankVersion) |
| 25 | ★★★★ **`OLMOD_SERVE_PRIVATE_PROFILE=1`** | 理由："**That measurement is for out.exe / build 1649370, NOT for this 3.19.26.13 client**" |
| 26 | ★★ 8 个任务 | `1` getPublic / `2` getPrivate / `3` setPublic / `4` setPrivate / `5` delete / `6` setPrivateByUID / `7` getPrivateByUID / `8` setPublicByUID |
| 27 | ★★ `profilePath` | `<assetRoot>/<titleId>/<USERID大写>/<filename>` ⇒ **第三次出现相同 `userIdDirectory`** |
| 28 | ★★★ `saveProfile` 原子写 | **第四次出现**（`.writing` + `MOVEFILE_REPLACE_EXISTING \| MOVEFILE_WRITE_THROUGH`） |
| 29 | ★★★★ **两个任务的 framing 相反** | `getPrivateInfo`(task 2) ⇒ **裸档案无前导**；`getPrivateInfoByUserId`(task 7) ⇒ **有 userId 前导** |
| 30 | ★★★★★ **CRC 的自包含设计** | 只算 **`raw[4..]`**,算完**写回 `raw[0..3]`** ⇒ **前 4 字节是校验值但不参与计算** |
| 31 | ★★ `compression` 两值 | **0 = 未压缩** / **1 = zlib** |

---

## 八、结论

### 1. ★★★★★ **背包重置是一个自维持死循环,`A=0` 是精确判据**

```
客户端判异常 ⇒ 重置成 `A=0` ⇒ `8/3` 回传 ⇒ 服务端照存 ⇒ `8/1` 发回 ⇒ 又判异常
        ↓
★★★ 四个 `A` 值：**4=完好 / 2=出厂 / 1=2019 原版 / 0=重置产物**
        ↓
★★★★★ 修复：**拒收 `A=0` 但仍回成功**（否则客户端重传）
```

### 2. ★★★★★ **档案规范形态是 33,428 字节**（`9 + 20 + 6 + 32768 + 625`）

### 3. ★★★★★ **两个旧方案**互补地失败**（`body` 缺 owner ⇒ 弹窗；`prefixed` owner 错 ⇒ 不生效）

### 4. ★★★★★ **两个 ID 的精确值被确认**（平台 `0x01100001DEADC0DE` vs DW `0xE7C8A98A6B4C2D0E`）

★ **⇒ 根因是 `Auth3Protocol` 不跑,而"laowai 从没撞上因为他们的两个 id 是同一个值"。**

### 5. ★★★★★ **`8/2` 的两种致命**（`error 800` 与非空档案）

### 6. ★★★★★ **rank/prestige/XP 只在私档,有四个精确偏移**（`0x12EC`/`0x1313`/`0x1317`/`0x131B`）

★ **⇒ 这解释了报告 118 的 `lb 1000` 为什么要独立提供这些值。**

### 7. ★★★★ **`OLMOD_SERVE_PRIVATE_PROFILE` 的适用范围判断**（"那是 out.exe 1649370 的实测,不是本客户端的"）

### 8. ★★★★ **CRC 的自包含设计**（只算 `raw[4..]`,写回 `raw[0..3]`）

---

## 九、下一步

- `Profiles2Service.hpp`（39 行）
- `ClanService`（623 行）/ `Storage2Service`（450 行）/ `Friends2Service`（325 行）
- `SharedRoom*`（4 文件）/ `Servers.cpp`（624 行）/ `DedicatedBookingDispatcher`（926 行）
