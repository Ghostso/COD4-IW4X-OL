# 学习报告 114（重开）— `MarketplaceService.cpp` 前半（1–659 行 / 共 1,099 行）

**学习范围**：`backend\Demonware\MarketplaceService.cpp` 第 1–659 行
**性质**：全实测
**★★★★★ 本报告收录七个重大发现**：①**43 个默认权益的完整清单** ②**8,460 记录上限与 512 KB 的双重天花板** ③**`80/230` 的五次复现与"权威源码不能覆盖实测"铁律** ④**`80/70` 的 48 字节请求逐字节** ⑤**"回答错会整服务变灰"的代价** ⑥**服务 93 的双钱包机制** ⑦**`80/203` 的 12 字段物品记录**

---

## 一、★★★★★ **43 个默认权益的完整清单**

### 1.1 ★★★★★ 完整数组（第 29–40 行）

```cpp
// Recovered from **CODOL_DefaultAvailableItems_Init (0x7052F0)**.
constexpr std::array<std::uint32_t, **43**> DefaultEntitlements{
    10001, 10010, 10015, 10049,
    20379, 20782, 20416, 21037, 20394, 25075, 25684,
    60043, 60040, 60137,
    60076, 60080, 60083,
    60000, 60005, 60003, 60128, 60144, 60162, 12243,
    545, 789, 792, 686, 1945, 612, 592,
    60178, 60179, 60180, 60181, 60182, 60183, 60184, 60185,
    30059, 30060, 30061,
    50000,
};
```

### ★★★★★ 完整的 43 个 item id（分组）

| 组 | id | 数量 |
|---|---|---|
| **1xxxx** | `10001` / `10010` / `10015` / `10049` | **4** |
| **2xxxx** | `20379` / `20782` / `20416` / `21037` / `20394` / `25075` / `25684` | **7** |
| **60043 组** | `60043` / `60040` / `60137` | **3** |
| **6007x/6008x** | `60076` / `60080` / `60083` | **3** |
| **6000x 组** | `60000` / `60005` / `60003` / `60128` / `60144` / `60162` / `12243` | **7** |
| **5xx–1xxx** | `545` / `789` / `792` / `686` / `1945` / `612` / `592` | **7** |
| **6017x–6018x** | `60178`–`60185`（**连续 8 个**） | **8** |
| **3005x–3006x** | `30059` / `30060` / `30061` | **3** |
| **50000** | `50000` | **1** |
| **合计** | — | ★ **43** ✓ |

★★★ **⇒ 出处：**`CODOL_DefaultAvailableItems_Init` @ **`0x7052F0`**。**

★★ **⇒ 与报告 089 的 `MarketplaceSkus.json` 的 `items` 表**对应**（那些 id 范围一致：`10001` / `60000` / `60076` / `30059` / `50000`）。**

★ **⇒ 且 `60178`–`60185` 是**连续 8 个** ⇒ 可能是一组相关的解锁项。**

---

## 二、★★★★★ **8,460 记录与 512 KB 的双重天花板**

### 2.1 ★★★★★ 完整引用（第 64–101 行，逐字）

```cpp
// LOCAL OVERRIDE (DSH, 2026-10-05) -- THE REPLY CAP IS THE LAOWAI'S OWN NUMBER: **8460 RECORDS**.
//
// This is NOT our old baseline's page clamp. It is the figure the laowai documented in their
// own game-server code, `src\game_server\ClientProcessPatches.hpp:250-255`, verbatim:
//
//     // OWN EVERY ITEM, without sending a single extra inventory byte.
//     //
//     // The inventory reply is capped at **8,460 records** by a **512 KB buffer** the client passes
//     // per task, the catalogue is **21,753 ids**, and the client does **NOT page** -- told 19,900
//     // existed while receiving 8,460 it **never asked for the rest** (measured 2026-09-03). So
//     // **no amount of work on the wire can deliver the catalogue**.
//
// and the same file (`:257-268`) states the consequence and the real answer:
// the store list is **not built FROM the inventory array** -- the client walks its own item table
// and asks an ownership resolver (**`sub_5E3760`, 94 call sites**) per entry, whose "owned without
// being in the inventory" branch is guarded by a predicate with **exactly one caller**. Forcing
// that predicate true is `installUnlockAllPatch()` (`ClientProcessPatches.cpp:1347-1393`),
// enabled with **`OLMOD_UNLOCK_ALL=1`** (`:1349`, consumed in `Appmain.cpp:1122-1129`).
```

### ★★★★★ 四个精确数字

| # | 项 | 值 |
|---|---|---|
| **1** | ★★★ **库存应答上限** | **8,460 记录** |
| **2** | ★★★ **客户端每任务缓冲区** | **512 KB** |
| **3** | ★★★ **完整目录** | **21,753 个 id** |
| **4** | ★★ **所有权解析器的调用点** | **`sub_5E3760`，94 处** |

★★★★★ **⇒ 完整的因果：**
```
客户端每任务给 **512 KB** 缓冲区 ⇒ 只装得下 **8,460 条**记录
        ↓
而目录有 **21,753** 个 id
        ↓
★★★ 且客户端**不分页**（"told 19,900 existed while receiving 8,460 it **never asked for
   the rest**",measured **2026-09-03**）
        ↓
★★★★★ ⇒ **"no amount of work on the wire can deliver the catalogue"**
   ⇒ 线上传输**无论如何都送不全**目录
```

### ★★★★★ 真正的解法（逐字）

```
"the store list is **not built FROM the inventory array** --
 the client **walks its own item table** and asks an **ownership resolver**
 (**`sub_5E3760`, 94 call sites**) per entry,
 whose **'owned without being in the inventory'** branch is guarded by a
 **predicate with exactly one caller**."
        ↓
★★★ 强制该谓词为真 = **`installUnlockAllPatch()`**（`ClientProcessPatches.cpp:1347-1393`）
   ⇒ 用 **`OLMOD_UNLOCK_ALL=1`** 启用（`:1349`，在 `Appmain.cpp:1122-1129` 消费）
        ↓
★★★★★ ⇒ **"OWNING EVERYTHING is the unlock-all patch's job -- not this handler's"**
```

★★ **⇒ 这是**"用补丁改所有权判断"而不是"用线上数据送全"的正确解法**。**

### ★★★★★ 一次实测失败（第 92–98 行，逐字）

```cpp
// ★ MEASURED 2026-10-05 17:16: sending the full 8460 records (the reply measured 512 KB after
// the byte ceiling clamped it) **killed the client again** -- 512 KB is the client buffer's
// **CAPACITY**, and the **LSG frame plus the TLV envelope have to fit inside it too**, so the
// usable payload is **smaller**. The default therefore stays at **400 records**, which is the
// configuration measured working at **17:05** (full login, level applied, warehouse populated).
// With `OLMOD_UNLOCK_ALL=1` the wire size no longer decides ownership at all -- see the citation
// above -- so **there is no reason to push it**.
```

★★★★★ **⇒ 三个精确事实：**
```
① ★★★ **512 KB 是**容量上限**,而 **LSG 帧 + TLV 信封也要装进去**
   ⇒ **实际可用载荷更小**
        ↓
② ★★ **默认值保持 400 条**（"measured working at **17:05**：full login, level applied,
   warehouse populated"）
        ↓
③ ★★★ **`OLMOD_UNLOCK_ALL=1` 后线上大小不再决定所有权** ⇒ "**there is no reason to push it**"
```

### ★★★ 三个环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| **`OLMOD_MARKETPLACE_MAX_ITEMS`** | ★ **`400`** | 记录数上限（**0 = 不封顶**） |
| **`OLMOD_MARKETPLACE_MAX_REPLY_BYTES`** | ★ **`512 × 1024`** | 字节上限（**0 = 禁用**） |
| **`OLMOD_MARKETPLACE_ANSWER_230`** | **`0`** | 是否用真实库存回答 task 230 |

★★ **⇒ `OLMOD_*` 累计 **21 个**。**

---

## 三、★★★★★ **`80/230` 的五次复现与"权威源码不能覆盖实测"铁律**

### 3.1 ★★★★★ 四次观察（第 339–345 行，逐字）

```cpp
// `1A-DSH\01-findings\定因-卡在连接中-第3轮-道具集决定任务序列-20261005-0130.md:144-185`
// (`confirmed`, **four independent observations** -- the object COUNT alone decides the outcome):
//
//     `80/230` answered  **0 objects (66 B)**   ->  **reached the lobby**
//     `80/230` answered  **7 objects**          ->  stuck on 「连接中」
//     `80/230` answered **10 objects (690 B)**  ->  stuck on 「连接中」
//     `80/230` answered **43 objects (2738 B)** ->  stuck on 「连接中」
```

### ★★★★★ 四次观察的完整表

| 应答 | 字节 | 结果 |
|---|---|---|
| ★ **0 个对象** | **66 B** | ★★★ **到达大厅** |
| **7 个对象** | — | ★ **卡在「连接中」** |
| **10 个对象** | **690 B** | **卡在「连接中」** |
| **43 个对象** | **2,738 B** | **卡在「连接中」** |

★★★★★ **⇒ **仅对象数量就决定结果**（"the object COUNT alone decides the outcome"）。**

★★ **⇒ 且**0 个对象是 66 B**（空应答的精确大小）。**

### ★★★★★ 后续影响（第 347–352 行，逐字）

```cpp
// Same document, §1: after a non-empty `80/230` the client **stops the startup task sequence
// ~7 steps later** and **NEVER sends** `80/173`, `8/3`, `80/203`, `71/15`, `80/154`, `71/20`, `21/5`.
//
// MEASURED 2026-10-05 17:19 (this file with the early return removed, cap 400):
// `80/230` replied **24,826 B** of objects; the client went silent after **seq 34**
// (`71/3 ClientLoadTimes`) and every tail task listed above was missing. **Fifth reproduction.**
```

★★★ **⇒ 非空 `80/230` 后客户端**停止启动序列**,**永不发送 7 个后续任务**：**
```
`80/173` / `8/3` / `80/203` / `71/15` / `80/154` / `71/20` / `21/5`
        ↓
★★★ 注意：**`80/203` 也在其中** ⇒ 真实库存的通道被切断了
```

★ **⇒ **第五次复现**：24,826 B 的应答 ⇒ 客户端在 **seq 34**（`71/3 ClientLoadTimes`）后静默。**

### ★★★★★ **铁律**（第 354–357 行，逐字）

```cpp
// The governing rule, from that document §7.2, verbatim:
//   「**权威源码可以否证"语义猜测"，但不能覆盖我方客户端的实测行为。两者冲突时，以我方实测为准。**」
//   (Authoritative source may refute a semantic guess, but it must not override our client's
//    measured behaviour. When the two conflict, our measurement wins.)
```

★★★★★ **⇒ 这是整个项目最重要的一条方法论：**
```
**权威源码可以否证"语义猜测"**
        ↓
★★★ 但**不能覆盖我方客户端的实测行为**
        ↓
★★★★★ **两者冲突时,以我方实测为准**
```

### ★★★★★ 一次"又犯了同样的错"（第 331–337 行，逐字）

```cpp
// I deleted this early return at 17:17 on the strength of the laowai's own source
// (`registerTask(0x50, 230, …)` -> this same `getInventory()`, plus
// `.agents\research\dw3_feasibility.md:156-167` describing 230 as a legitimate
// clear-and-replace pass). **That was wrong. It is the exact mistake already recorded once
// today, and it cost a second client session.**
```

★★★ **⇒ 作者自己承认："**That was wrong. It is the exact mistake already recorded once today,
 and it cost a second client session.**"**

★★ **⇒ 即：**同一天犯了两次同样的错**（用权威源码推翻实测）。**

### ★★★★★ `80/230` 的真实机制（第 380–390 行，逐字）

```cpp
// The laowai documented what an empty 230 does, `.agents\research\dw3_feasibility.md:156-167`:
//   "The later `CODOL_Marketplace_RequestStartupInventory` (**`0x4A5120`**) independently
//    constructs service `80`, task `230` through `bdMarketplace_StartGetInventoryPaged`
//    (**`0xA472B0`**). Its completion callback, `CODOL_Marketplace_OnPagedInventoryComplete`
//    (**`0x4A5680`**), **CLEARS the 20,000-entry native inventory**, copies the returned 168-byte
//    inventory objects, and finalizes the replacement. ... Mapping task `230` to the same
//    persistent inventory store **prevents this legitimate late replacement from erasing the
//    pre-profile cache**."
```

★★★★★ **⇒ 完整的机制 + 四个精确地址：**
```
**`CODOL_Marketplace_RequestStartupInventory = 0x4A5120`**
**`bdMarketplace_StartGetInventoryPaged = 0xA472B0`**
**`CODOL_Marketplace_OnPagedInventoryComplete = 0x4A5680`**
        ↓
★★★ 完成回调**清空 20,000 项的原生库存**,拷贝返回的 **168 字节**库存对象,然后完成替换
        ↓
★★★★★ ⇒ **空 230 ⇒ 清空库存 ⇒ 档案按"你什么都没有"校验 ⇒ 正是"数据异常 → 重新配置背包"**
```

### ★★★★★ 一次**档案被重置**的实测（第 367–378 行，逐字）

```cpp
// Operator report 2026-10-05 18:5x:
//   「**存档数据异常，已经被重置了**」-- the client REPLACED its own public profile with defaults
//   (card **16646/16639/15961/26236 -> 30059/30060/30061**, onboardCharacterID **612 -> 0**) with
//   **NO server query in between**. From `n10run-20261005-184057.txt`, the whole window between
//   the profile download and the reset was:
//       seq=7  8/1    -> **1537 B** (the profile)
//       seq=8  8/2    -> **33009 B**
//       seq=27 80/230 -> **21 B**   <-- **ZERO objects**
//       seq=28 93/1   -> 21 B
//       seq=51 8/3    -> **1405 B** (the reset profile)
//   There is no `80/203` in that window and `80/70` is deliberately empty, so the client had
//   **NOTHING from the server to validate against**.
```

★★★★★ **⇒ 一条完整的实测时间线：**
```
seq=7  `8/1`    ⇒ **1,537 B**（档案）
seq=8  `8/2`    ⇒ **33,009 B**
seq=27 `80/230` ⇒ **21 B**  ← ★★★ **零对象**
seq=28 `93/1`   ⇒ 21 B
seq=51 `8/3`    ⇒ **1,405 B**（**重置后的档案**）
        ↓
★★★ 且**该窗口内没有 `80/203`**,而 `80/70` 故意为空
   ⇒ 客户端**没有任何服务端数据可用于校验**
        ↓
★★★★★ ⇒ **档案被替换成默认值**（card 4 个 → 3 个,onboardCharacterID 612 → 0）
```

★★ **⇒ 这是**"空 230 导致档案重置"的完整证据链**。**

### ★★★ 判断标准（第 397–398 行，逐字）

```cpp
// JUDGEMENT: with this ON, the login chain must still complete AND the class/loadout and
// player card must survive a restart. If the client sticks on 连接中, turn it back off.
```

★★ **⇒ 两条判据：①登录链仍完成 ②class/loadout 与 player card 在重启后存活。**

---

## 四、★★★★★ **`80/70` 的 48 字节请求逐字节**

### 4.1 ★★★★★ 完整字节（第 512–525 行，逐字）

```
    25000000 86 50 03 46          size, 0x86, service 80, proto 3, task 70
    10 00                         string  context      ""
    08 01000000                   u32     pageNum      1
    08 D0070000                   u32     itemsPerPage 2000
    01 01                         bool    showAll      true
    08 00000000                   u32     numSkuIds    0
    08 00000000                   u32     numSkuTypes  0
    10 "1625160"                  string  storeVersion

The 7 trailing zero bytes of that 48-byte frame are **padding, not a field**:
the length prefix says **0x25** and **4 + 0x25 = 41**.
```

### ★★★★★ 完整的请求帧解析

| 偏移 | 字节 | 字段 | 值 |
|---|---|---|---|
| **0** | `25 00 00 00` | ★ **size = 0x25 = 37** | 载荷长度 |
| **4** | `86` | ★ 标志 | — |
| **5** | `50` | ★ **服务 = 80** | — |
| **6** | `03` | ★ **协议版本 3** | — |
| **7** | `46` | ★ **任务 = 70** | — |
| **8** | `10 00` | **string** | `""`（context） |
| **10** | `08 01 00 00 00` | **u32** | **1**（pageNum） |
| **15** | `08 D0 07 00 00` | **u32** | ★ **2000**（itemsPerPage） |
| **20** | `01 01` | **bool** | **true**（showAll） |
| **22** | `08 00 00 00 00` | **u32** | **0**（numSkuIds） |
| **27** | `08 00 00 00 00` | **u32** | **0**（numSkuTypes） |
| **32** | `10 "1625160"` | **string** | ★★ **`"1625160"`**（storeVersion） |
| **41** | — | — | **载荷结束**（`4 + 0x25 = 41`） |
| **41–47** | `00 × 7` | ★★★ **填充** | **不是字段** |

★★★★★ **⇒ 两个精确的算术：**
```
`size = 0x25 = 37`
`4 + 0x25 = **41**` ⇒ 帧头 4 字节 + 载荷 37 字节 = 41
        ↓
★★★ 而总帧是 **48 字节** ⇒ **48 − 41 = 7 字节填充** ✓
```

★★ **⇒ 且 `storeVersion = "1625160"`** ⇒ 一个**7 位数字的版本号**（可能是时间戳 `16-25-160` 或纯编号）。**

### ★★★★★ `80/70` 的"整服务变灰"警告（第 527–533 行，逐字）

```cpp
// The EMPTY page is what the C# OLfinal server ships by default, for a reason worth
// carrying over verbatim: a well-formed empty reply leaves the store browsable, but
// **a reply the client cannot deserialize marks the WHOLE marketplace service dead** --
// **STORE and INVENTORY grey out with a warning triangle** and the client **does not recover
// in session**. CODOL's SKU record is **not MW19's bdMarketplaceSku**; it carries **two extra
// fields** (a **u8 after rentalDuration**, a **u32 after couponEnabled**), and writing the
// sibling title's order is exactly how that failure was produced **once already**.
```

★★★★★ **⇒ 三条精确事实：**
```
① ★★★ **格式良好的空应答** ⇒ 商店仍可浏览
   **客户端无法反序列化的应答** ⇒ **整个市场服务死掉**
   ⇒ **STORE 与 INVENTORY 变灰 + 警告三角**,且**会话内不恢复**
        ↓
② ★★★ **CODOL 的 SKU 记录不是 MW19 的 `bdMarketplaceSku`**
   ⇒ 它有**两个额外字段**：**`rentalDuration` 之后的 u8** + **`couponEnabled` 之后的 u32**
        ↓
③ ★★★ "**writing the sibling title's order is exactly how that failure was produced
   once already**"
```

★★ **⇒ 第 ② 条是**两个精确的额外字段**（`u8` 与 `u32`）。**

### ★★★ 两个精确地址（第 535–538 行）

```cpp
// TODO(CODOL): emit real SKUs once the record is written in the order CODOL's own
// deserializer reads it -- **sub_A497F0** in codoMP_client_shipRetail.exe, reached from
// getSkusPaginated at **sub_A462A0**.
```

★★ **⇒ `sub_A497F0`（反序列化器）/ `sub_A462A0`（`getSkusPaginated`）。**

---

## 五、★★★★★ **服务 93 的双钱包机制**

### 5.1 ★★★★★ 完整注释（第 581–607 行，逐字）

```cpp
/// Service 93 task 1 -- the SECOND wallet, which is a **different currency** and not a second
/// copy of the first.
///
/// That 93/1 is a balance poll at all: **sub_B49160** constructs **TWO objects at unk_BA0B2B8
/// with a 32-byte stride**, and **sub_4A71B0** -- the only balance poller -- passes both to
/// **sub_4A4930**, which issues **Marketplace/130** for the first and **93/1** for the second.
/// One poll, two services, one array. In the measured menu session the client sent **15 of these
/// against 12 task 130s**.
///
/// THE CURRENCY ID IS A **SELECTOR, NOT A VERSION**. **sub_6AF970** and **sub_6AF9E0** are twin
/// getters that walk that same two-element array for a specific id and return **ZERO** when
/// they do not find it:
///
///     v2 = &byte_BA0B2C8;                 // wallet[0].currencyId
///     while (*v2 != 2) {                  // ...and != 1 in the other one
///         v2 += 32;
///         if (v2 >= &byte_BA0B308) { v3 = 0; goto done; }
///     }
///     v3 = dword_BA0B2CC[8 * v1];         // that wallet's amount
///
/// So answering this with the id-1 record leaves the **id-2 readout at zero** however large
/// its amount is. That is what the **"Top Up" button covering the second balance** was:
/// a zero, correctly displayed.
```

### ★★★★★ 完整的双钱包机制

```
**`sub_B49160`** 在 **`unk_BA0B2B8`** 构造**两个对象**,步长 **32 字节**
        ↓
**`sub_4A71B0`**（唯一的余额轮询器）把两者传给 **`sub_4A4930`**
        ↓
★★★ `sub_4A4930` 为**第一个**发 **`Marketplace/130`**,为**第二个**发 **`93/1`**
   ⇒ "**One poll, two services, one array**"
        ↓
★★★ 实测：客户端发了 **15 个 93/1** vs **12 个 task 130**
```

### ★★★★★ 货币 ID 是**选择器,不是版本**（逐字代码）

```cpp
v2 = &byte_BA0B2C8;                 // wallet[0].currencyId
while (*v2 != 2) {                  // ...and != 1 in the other one
    v2 += 32;
    if (v2 >= &byte_BA0B308) { v3 = 0; goto done; }
}
v3 = dword_BA0B2CC[8 * v1];         // that wallet's amount
```

★★★ **⇒ 三个精确的地址/常量：**
```
**`byte_BA0B2C8`** ⇒ `wallet[0].currencyId`
**`byte_BA0B308`** ⇒ 数组末尾（`(0xBA0B308 - 0xBA0B2C8) / 32 = **2**` 个元素 ✓）
**`dword_BA0B2CC`** ⇒ 该钱包的金额
        ↓
★★★ 步长 **32 字节**,数组 **2 个元素**
```

### ★★★★★ "Top Up 按钮盖住第二个余额"的精确解释

```
若用 **id-1 的记录**回答 93/1
        ↓
★★★ 则 **id-2 的读数恒为 0**,无论其金额多大
        ↓
★★★★★ ⇒ 这就是 **"Top Up 按钮盖住第二个余额"**：
   **一个零,被正确地显示出来**
```

★★ **⇒ 这是一个**"数据错配导致 UI 显示 0"的精确案例**（不是 UI bug）。**

### ★★★ `SecondaryCurrencyId` 的数据驱动（第 605–607 行）

```cpp
// Which wallet is served stays data-driven -- whichever entry of the Marketplace asset
// carries **SecondaryCurrencyId** -- so a title that numbers its currencies differently is a
// **data change rather than a code change**.
```

★ **⇒ 服务哪个钱包由 **`SecondaryCurrencyId`** 数据决定（不是硬编码）。**

---

## 六、★★★★★ **`80/203` 的 12 字段物品记录**

### 6.1 ★★★★★ 完整构造（第 409–430 行）

```cpp
for (std::size_t index = 0; index != count; ++index)
{
    const auto &item = inventory[index];
    ByteBuffer object;
    object.writeU64(identity.userId);       // ① userId
    object.writeString("**steam**");         // ② 固定字符串
    object.writeU32(item.id);                // ③ 物品 id
    object.writeU32(item.quantity);          // ④ 数量
    object.writeU32(0);                      // ⑤ 恒 0
    object.writeBlob(ItemData);              // ⑥ blob { 2 }
    object.writeU32(item.expireDateTime);    // ⑦ 过期时间
    object.writeI64(item.expiryDuration);    // ⑧ 过期时长
    object.writeU16(**2**);                  // ⑨ 恒 2
    object.writeU32(item.modifiedTime);      // ⑩ 修改时间
    object.writeU8(item.customSourceType);   // ⑪ 来源类型
    ...
}
```

### ★★★★★ 完整的 11 个字段

| # | 类型 | 值 | 说明 |
|---|---|---|---|
| **①** | **u64** | `identity.userId` | 用户 ID |
| **②** | **string** | ★★ **`"steam"`** | 固定平台名 |
| **③** | **u32** | `item.id` | 物品 ID |
| **④** | **u32** | `item.quantity` | 数量 |
| **⑤** | **u32** | **`0`** | 恒 0 |
| **⑥** | **blob** | ★ `{ 2 }` | 单字节 **2** |
| **⑦** | **u32** | `item.expireDateTime` | 过期时间 |
| **⑧** | **i64** | `item.expiryDuration` | 过期时长 |
| **⑨** | **u16** | ★ **`2`** | 恒 2 |
| **⑩** | **u32** | `item.modifiedTime` | 修改时间 |
| **⑪** | **u8** | `item.customSourceType` | 来源类型 |

★★ **⇒ 实际是 **11 个字段**（不是 12）。**

★★★ **⇒ 第 ② 条是 `"steam"`** ⇒ 说明**平台标识是 Steam**（与报告 109 的 `SteamTicketAuth` 呼应）。**

### ★★★★★ 字节封顶的精确逻辑（第 425–429 行）

```cpp
// ★ 字节封顶：**至少发一件**（否则空回复会把仓库清空），超过就停在这里。
if (byteCap && !response.objects.empty() && replyBytes + objectBytes > byteCap)
    break;
```

★★★★★ **⇒ 三个条件：**
```
① `byteCap` 非零（启用封顶）
② ★★★ **`!response.objects.empty()`** ⇒ **至少已发一件**
③ `replyBytes + objectBytes > byteCap` ⇒ 超限
        ↓
★★★ ⇒ 目的（逐字）："**至少发一件**（否则**空回复会把仓库清空**）"
```

★ **⇒ 第 ② 条是**关键的防护**：即使第一件就超限,也**必须发出去**,否则空回复清空仓库。**

### ★★★★★ `80/230` 与 `80/203` 的 `maximumResults` 差异（第 292–302 行）

```cpp
if (request.task == 230 && contextual.valid())
{
    maximumResults = (std::numeric_limits<std::size_t>::max)();      // ★ 230 ⇒ 无上限
}
else
{
    std::uint16_t contextualMaximum{};
    if (!contextual.readU16(contextualMaximum) || !contextual.valid())
        return ServiceResponse{ .error = InvalidRequestError, .task = request.task };
    maximumResults = contextualMaximum;                              // ★ 203 ⇒ 从请求读 u16
}
```

★★★ **⇒ 两个任务的 `maximumResults` 来源**不同**：**
```
**task 230** ⇒ **`SIZE_MAX`**（无上限）
**task 203** ⇒ **从请求读 `u16`**（客户端指定）
```

★ **⇒ 注释解释（第 361 行）："the real inventory is delivered by **`80/203`** --
 which is why `maximumResults` is parsed for **203 only**"。**

---

## 七、★★★★ **`purchaseSkus` 的严格校验**

### 7.1 ★★★★★ 七步校验（第 434–505 行）

```cpp
if (!input.readString(context) || !input.readU32(skuCount) || skuCount == 0 || skuCount > **255**)
    return error;                                              // ① skuCount 1..255
for (index < skuCount)
    if (!input.readU32(sku) || sku == 0) return error;         // ② 每个 sku 非零
if (!input.readU32(quantityCount) || quantityCount != skuCount)
    return error;                                              // ③ 数量数 == sku 数
for (index < quantityCount)
    if (!input.readU32(quantity) || quantity == 0) return error;  // ④ 每个数量非零
if (!input.readBool(gift) || !input.readU32(accountCount) || accountCount != skuCount)
    return error;                                              // ⑤ 账户数 == sku 数
for (index < accountCount)
    if (!input.readU64(accountId) || !input.readString(accountType)) return error;  // ⑥
if ((request.service != 0x50 && request.service != 0x5D) ||
    !input.readU32(couponCount) || couponCount != 0 ||
    !input.readU32(metadataCount) || metadataCount != 0 ||
    !input.readU8(sourceType) || sourceType != 0 ||
    !input.readU32(resultCount) || resultCount != expectedResultCount)
    return error;                                              // ⑦ 四个零字段
```

### ★★★★★ 七条精确校验

| # | 校验 |
|---|---|
| **①** | **`skuCount` 在 1..255** |
| **②** | 每个 `sku` **非零** |
| **③** | **`quantityCount == skuCount`** |
| **④** | 每个 `quantity` **非零** |
| **⑤** | **`accountCount == skuCount`** |
| **⑥** | 每个 `accountId` + `accountType` 可读 |
| **⑦** | ★★★ **`couponCount == 0` / `metadataCount == 0` / `sourceType == 0` / `resultCount == expectedResultCount`** |

★★★ **⇒ 第 ⑦ 条的关键：**
```cpp
const auto expectedResultCount = request.service == **0x50** ? skuCount : **0**;
        ↓
★★★ **服务 `0x50`** ⇒ `resultCount == skuCount`
   **服务 `0x5D`** ⇒ `resultCount == 0`
```

★★ **⇒ 即：**两个服务的 `resultCount` 语义不同**（0x50 要等于 sku 数,0x5D 要等于 0）。**

### ★★★ 服务 93 的完整说明（第 239–248 行，逐字）

```cpp
// Service 93 is the second half of the wallet-and-purchase pair. It stays Unknown93
// here on purpose: **93 is absent from MW19** (which has 91/92/95/96), so it is a **Tencent
// addition** that no source we have names, and the C# server's "Commerce" is labelled a
// **HYPOTHESIS** in its own enum. What is measured is what it DOES. CODOL builds **ONE cart in
// `sub_4A6550`** and splits it by whether **`sub_707480`** prices the sku, then hands both halves
// the same argument list -- so **93/4 and 93/131 carry Marketplace 154's request byte for byte**
// and take the same path. 93/4 was answered by the C# OLfinal server and was missing here,
// which is **not harmless**: an unregistered purchase is **dropped on the floor and still looks
// like a success**, because the client's UI **only needs the empty reply to advance**.
```

★★★★★ **⇒ 五个精确事实：**
```
① ★★★ **服务 93 在 MW19 里不存在**（MW19 有 91/92/95/96）
   ⇒ **腾讯新增**,无源可命名,C# 的 "Commerce" 在其枚举里标为 **HYPOTHESIS**
        ↓
② ★★★ CODOL 在 **`sub_4A6550`** 建**一个购物车**
   ⇒ 由 **`sub_707480`** 是否为该 sku 定价来**分成两半**
   ⇒ 两半**参数列表完全相同**
        ↓
③ ★★★ ⇒ **`93/4` 与 `93/131` 逐字节携带 `Marketplace 154` 的请求**
        ↓
④ ★★★ **未注册的购买会被丢弃但仍看起来像成功**
   ⇒ 因为客户端 UI **只需要空应答就能前进**
```

★ **⇒ 第 ④ 条是**"静默丢弃"的危险**（与报告 109 的"沉默导致重试"**相反**：这里静默反而看起来成功）。**

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★ **43 个默认权益** | 来自 **`CODOL_DefaultAvailableItems_Init` @ `0x7052F0`**；含 **`60178`–`60185` 连续 8 个** |
| 2 | ★★★★★ **8,460 记录上限** | 客户端每任务 **512 KB** 缓冲区；目录 **21,753 个 id**；**客户端不分页**（"never asked for the rest",measured 2026-09-03） |
| 3 | ★★★★★ **"线上送不全"** | "**no amount of work on the wire can deliver the catalogue**" |
| 4 | ★★★★ **真正解法** | 客户端**自己走物品表** + **`sub_5E3760`（94 个调用点）** 所有权解析器 ⇒ **`installUnlockAllPatch()`** + **`OLMOD_UNLOCK_ALL=1`** |
| 5 | ★★★ 一次实测失败 | 2026-10-05 17:16 发全 8,460 ⇒ **又杀客户端**（512 KB 是**容量**,LSG 帧 + TLV 信封也要装进去） |
| 6 | ★★ 默认值 | **400 条**（"measured working at **17:05**：full login, level applied, warehouse populated"） |
| 7 | ★★ 三个环境变量 | `OLMOD_MARKETPLACE_MAX_ITEMS`(**400**) / `OLMOD_MARKETPLACE_MAX_REPLY_BYTES`(**512 KB**) / `OLMOD_MARKETPLACE_ANSWER_230`(**0**) |
| 8 | ★★★★★ **`80/230` 四次观察** | **0 对象(66 B) ⇒ 到达大厅** / 7 对象 / 10 对象(690 B) / 43 对象(2,738 B) ⇒ **全卡「连接中」** |
| 9 | ★★★ 后续 | 非空 230 ⇒ **停启动序列 ~7 步**,**永不发 `80/173` `8/3` `80/203` `71/15` `80/154` `71/20` `21/5`** |
| 10 | ★★ 第五次复现 | 2026-10-05 17:19 回 **24,826 B** ⇒ seq 34 后静默 |
| 11 | ★★★★★ **铁律** | 「**权威源码可以否证"语义猜测"，但不能覆盖我方客户端的实测行为。两者冲突时，以我方实测为准。**」 |
| 12 | ★★★ 同一天两次同样错误 | "**That was wrong. It is the exact mistake already recorded once today, and it cost a second client session.**" |
| 13 | ★★★★ **`80/230` 的真实机制** | **`0x4A5120`** → **`0xA472B0`** → **`0x4A5680`** ⇒ **清空 20,000 项原生库存** + 拷贝 **168 字节**对象 |
| 14 | ★★★★★ **档案被重置的实测** | seq=7 `8/1`(1,537 B) / seq=8 `8/2`(33,009 B) / **seq=27 `80/230`(21 B,零对象)** / seq=28 `93/1`(21 B) / **seq=51 `8/3`(1,405 B,重置后)**；card **16646/16639/15961/26236 → 30059/30060/30061**、**onboardCharacterID 612 → 0** |
| 15 | ★★ 判据 | 登录链完成 **且** class/loadout 与 player card 重启后存活 |
| 16 | ★★★★★ **`80/70` 的 48 字节** | `25000000 86 50 03 46` + `10 00` + `08 01000000`(pageNum 1) + `08 D0070000`(**2000**) + `01 01` + `08 00000000`×2 + `10 "**1625160**"`；**`4 + 0x25 = 41`**,后 **7 字节填充** |
| 17 | ★★★★★ **"整服务变灰"** | 格式良好的空应答 ⇒ 商店可浏览；**无法反序列化 ⇒ STORE+INVENTORY 变灰 + 警告三角,会话内不恢复** |
| 18 | ★★★ **CODOL SKU 的两个额外字段** | **`rentalDuration` 之后的 `u8`** + **`couponEnabled` 之后的 `u32`**（不是 MW19 的 `bdMarketplaceSku`） |
| 19 | ★★ 两个地址 | **`sub_A497F0`**（反序列化器）/ **`sub_A462A0`**（`getSkusPaginated`） |
| 20 | ★★★★★ **双钱包机制** | `sub_B49160` 在 **`unk_BA0B2B8`** 构造**两个 32 字节对象**；`sub_4A71B0` → `sub_4A4930` ⇒ 第一个发 **`Marketplace/130`**,第二个发 **`93/1`**；实测 **15 个 93/1 vs 12 个 130** |
| 21 | ★★★ 货币 ID 是**选择器** | `byte_BA0B2C8`（`wallet[0].currencyId`）→ `byte_BA0B308`（末尾,`(0xBA0B308-0xBA0B2C8)/32 = 2` 个元素）；`dword_BA0B2CC` = 金额 |
| 22 | ★★★★★ **"Top Up 按钮"的真相** | 用 id-1 记录回答 93/1 ⇒ **id-2 读数恒 0** ⇒ "**一个零,被正确地显示出来**" |
| 23 | ★★ 数据驱动 | `SecondaryCurrencyId`（数据改动而非代码改动） |
| 24 | ★★★★ **`80/203` 的 11 字段** | `u64 userId` / **`string "steam"`** / `u32 id` / `u32 quantity` / `u32 0` / **`blob{2}`** / `u32 expireDateTime` / `i64 expiryDuration` / **`u16 2`** / `u32 modifiedTime` / `u8 customSourceType` |
| 25 | ★★★★★ **字节封顶三条件** | `byteCap` 非零 + ★ **`!objects.empty()`**（**至少发一件**）+ 超限 ⇒ 目的："否则**空回复会把仓库清空**" |
| 26 | ★★★ **230 vs 203 的 maximumResults** | **230 ⇒ `SIZE_MAX`**（无上限）；**203 ⇒ 从请求读 `u16`** |
| 27 | ★★★★★ **`purchaseSkus` 七条校验** | skuCount **1..255** / 每个 sku 非零 / 数量数==sku 数 / 每个数量非零 / 账户数==sku 数 / 账户对可读 / **四个零字段** |
| 28 | ★★★ `resultCount` 的差异 | **服务 `0x50` ⇒ == skuCount**；**服务 `0x5D` ⇒ == 0** |
| 29 | ★★★★★ **服务 93 的身份** | **MW19 里不存在**（MW19 有 91/92/95/96）⇒ **腾讯新增**；C# 的 "Commerce" 标为 **HYPOTHESIS** |
| 30 | ★★★ 一个购物车 | `sub_4A6550` 建**一个**购物车,`sub_707480` 定价与否**分成两半** ⇒ **`93/4`/`93/131` 逐字节携带 `Marketplace 154` 的请求** |
| 31 | ★★★★ **静默丢弃** | 未注册的购买**被丢弃但仍看起来像成功**（UI 只需空应答前进） |
| 32 | ★★ `OLMOD_*` 累计 | **21 个** |

---

## 九、结论

### 1. ★★★★★ **8,460 / 512 KB / 21,753 三个数字构成一个硬上限**

```
客户端每任务 512 KB ⇒ 只装 8,460 条；目录 21,753 ⇒ **线上送不全**
        ↓
★★★ 正确解法：**`OLMOD_UNLOCK_ALL=1` 改所有权判断**（`sub_5E3760` 的谓词）
```

### 2. ★★★★★ **`80/230` 的四次观察 + 第五次复现,以及一条方法论铁律**

```
**0 对象(66 B) ⇒ 到达大厅**；7/10/43 对象 ⇒ **全卡「连接中」**
        ↓
★★★ 且非空 230 ⇒ **永不发 `80/203`** ⇒ 真实库存通道被切断
        ↓
★★★★★ 铁律：**"权威源码可以否证语义猜测,但不能覆盖我方实测"**
```

### 3. ★★★★★ **一次"档案被重置"的完整实测链**（`80/230` 零对象 ⇒ 清空 20,000 项 ⇒ 档案按"什么都没有"校验）

### 4. ★★★★★ **`80/70` 的 48 字节逐字节还原**（含 `4 + 0x25 = 41` 与 7 字节填充）

### 5. ★★★★★ **"格式错的应答会让整个市场服务变灰且会话内不恢复"**

### 6. ★★★★★ **服务 93 的双钱包机制与"Top Up 按钮显示 0"的真相**

### 7. ★★★★★ **`80/203` 的 11 字段（含固定 `"steam"`）与"至少发一件"的防护**

### 8. ★★★★ **服务 93 的"静默丢弃但看起来成功"**

---

## 十、下一步

- `MarketplaceService.cpp` 后半（660–1,099 行，约 440 行）
- `StatsService`（875 行）/ `LobbyProtocol`（807 行）/ `Profiles2Service`（630 行）
- `ClanService`（623 行）/ `Storage2Service`（450 行）/ `Friends2Service`（325 行）
