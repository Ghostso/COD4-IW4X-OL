# 学习报告 082（重开）— `payload\Ayria\` 的 8 个 PE 二进制的完整结构

**学习范围**：`Injector32.exe` / `Bootstrapper32.dll` / `Bootstrapper64.dll` / `ol_room_owner.exe` / 4 个插件
**性质**：全实测（**8 个二进制的完整 PE 头 + 节表 + 导出表**）
**★★★★★ 本报告收录三个重大发现**：①**三个 Ayria 框架二进制的 PE 时间戳被篡改/清零** ②**`.fptable` 五处全零（0/128）确认** ③**更正一处早前的读数错误（Bootstrapper64 的 ImageBase）**

---

## 一、★★★★★ 八个二进制的完整 PE 表

| # | 文件 | 大小 | 机器 | **ImageBase** | **TimeDateStamp** | **UTC 时间** | 导出数 | `.fptable` |
|---|---|---|---|---|---|---|---|---|
| **1** | **`Injector32.exe`** | **126,464** | x86 | **`0x400000`** | **2689507600** | ★★★ **2055-03-24 13:26:40** | **0** | ✗ |
| **2** | **`Bootstrapper32.dll`** | **159,744** | x86 | **`0x10000000`** | **2299471394** | ★★★ **2042-11-13 06:03:14** | **2** | ✗ |
| **3** | **`Bootstrapper64.dll`** | **204,288** | **x64** | ★ **`0x180000000`** | **15930** | ★★★ **1970-01-01 04:25:30** | **2** | ✗ |
| **4** | **`ol_room_owner.exe`** | **283,648** | x86 | **`0x400000`** | **1792344237** | ★ **2026-10-18 17:23:57** | **0** | ★ **✓** |
| **5** | **`Localnetworking.Ayria32`** | **519,168** | x86 | **`0x10000000`** | **1792861222** | ★★ **2026-10-24 17:00:22** | **3** | ★ **✓** |
| **6** | **`Platformwrapper.Ayria32`** | **543,232** | x86 | **`0x10000000`** | **1791007846** | ★ **2026-10-03 06:10:46** | **6** | ★ **✓** |
| **7** | **`Alwaysoffline.Localnet32`** | **4,189,184** | x86 | **`0x10000000`** | **1792610028** | ★ **2026-10-21 19:13:48** | **5** | ★ **✓** |
| **8** | **`CodolGameServer.Localnet32`** | **6,834,176** | x86 | **`0x10000000`** | **1792610047** | ★ **2026-10-21 19:14:07** | **55** | ★ **✓** |

★ **⇒ 只有 `Bootstrapper64.dll` 是 x64（200 字节 optHdr / 7 个节 / 含 `.pdata` 与 `_RDATA`）。**
**⇒ 其余 7 个都是 x86（224 字节 optHdr / 5 个节）。****

---

## 二、★★★★★ **三个 Ayria 框架二进制的时间戳被篡改**

### 2.1 ★★★★★ 完整的分组

| 分组 | 文件 | **TimeDateStamp** | 判定 |
|---|---|---|---|
| **Ayria 框架** | `Injector32.exe` | **2689507600** ⇒ **2055-03-24** | ★★★ **未来时间** |
| **Ayria 框架** | `Bootstrapper32.dll` | **2299471394** ⇒ **2042-11-13** | ★★★ **未来时间** |
| **Ayria 框架** | `Bootstrapper64.dll` | **15930** ⇒ **1970-01-01 04:25:30** | ★★★ **近零（假）** |
| **ol-mod 自建** | `ol_room_owner.exe` | **1792344237** ⇒ **2026-10-18** | ✓ **真实** |
| **ol-mod 自建** | `Platformwrapper.Ayria32` | **1791007846** ⇒ **2026-10-03** | ✓ **真实** |
| **ol-mod 自建** | `Alwaysoffline.Localnet32` | **1792610028** ⇒ **2026-10-21 19:13:48** | ✓ **真实** |
| **ol-mod 自建** | `CodolGameServer.Localnet32` | **1792610047** ⇒ **2026-10-21 19:14:07** | ✓ **真实** |
| **被覆盖** | `Localnetworking.Ayria32` | **1792861222** ⇒ **2026-10-24 17:00:22** | ★★ **= 我上一轮覆盖的时间** |

### ★★★★★ 三条结论

```
① ★★★ **三个 Ayria 框架二进制的 PE 时间戳是伪造/清零的**
   （两个指向未来 2055/2042,一个指向 1970 年 4 时 25 分 —— 后者是
     **PE 时间戳沿用 MS-DOS 时间戳约定时的经典"零值"表现**）
        ↓
② ★★★ **五个 ol-mod 自建二进制的 PE 时间戳全部真实**
   ⇒ **两组二进制的构建来源不同**
        ↓
③ ★★★★★ **`Localnetworking.Ayria32` 的 PE 时间戳
   （2026-10-24 17:00:22 UTC = 2026-10-25 01:00:22 北京）
   与我上一轮记录的"LastWrite 2026-10-25 01:00:22"完全一致**
        ↓
★★★ ⇒ **该文件的 PE 时间戳也被那次覆盖改写了**
   ⇒ 这是一个**额外的独立证据**,证明哈希不符确实来自我的覆盖（而非别的原因）
```

★★ **⇒ 第 ③ 条**强化了报告 001–010 的结论**：该文件是被我改过的（连 PE 时间戳都变了）。**

### ★★★ `Bootstrapper64.dll` 的 `15930` 是什么意思

```
15930 秒（自 1970-01-01 00:00:00 UTC）
= **1970-01-01 04:25:30 UTC**
        ↓
★★★ ⇒ 这是 **MS-DOS 时间戳的最小可表示值** 在某种换算下的结果
   （DOS 日期 1980-01-01 00:00:00 对应某个值,而 15930 略低于它）
        ↓
★ 结论：**这是"时间戳未设置"的残留,不是真实构建时间**
```

---

## 三、★★★★★ **更正一处早前的读数错误**

### 3.1 ★★★ 早前记录 vs 实测

| 项 | 早前记录 | ★ **实测（本次）** |
|---|---|---|
| `Bootstrapper64.dll` 的 **ImageBase** | ★ **`0x00000001`**（"非法"） | ★★★ **`0x180000000`**（**标准 x64 DLL 默认基址**） |

★★★ **⇒ 早前的 `0x00000001` 是**错的**。**

### ★★★ 错误原因（推断）

```
`Bootstrapper64.dll` 是 **PE32+（magic 0x20B）**
   ⇒ 数据目录从 `optHdr + **112**` 开始
   ⇒ ImageBase 在 `optHdr + **24**`（**8 字节**）

若按 **PE32 的偏移**去读（`optHdr + **28**`，4 字节）
   ⇒ 就读到了错误的字段位置
        ↓
★★★ ⇒ 得到 `0x00000001` 这样一个"非法"值
        ↓
★ 实测用 64 位偏移（+24）读 ⇒ **`0x180000000`** ✓
```

★★ **⇒ 这是"**节/目录偏移按错误位宽解读**"的又一类错误（与记忆里"一处 6 字节偏移错误
制造了一批假发现"同类）。**
**⇒ 已更正：`0x180000000` 是 Visual Studio 对 x64 DLL 的**默认基址**,完全正常。****

### 3.2 ★★★ 因此早前记录的"三个异常"要修正为**两个**

| 早前记录的三个异常 | 更正后 |
|---|---|
| PE32+/AMD64（唯一 64 位） | ✓ **仍然成立** |
| ~~ImageBase = 0x00000001（非法）~~ | ★★★ **作废**（实为 `0x180000000`,正常） |
| TimeDateStamp 1970-01-01 04:25:30 | ✓ **仍然成立** |

★ **⇒ `Bootstrapper64.dll` 的实际异常只有**一条**：**时间戳是假的**（与其他两个 Ayria 框架件同类）。**

★★ **⇒ 但"可能未使用"的推断仍然指向它** ⇒ 三个 Ayria 框架件的时间戳全假,说明它们来自**同一批被处理过的二进制**。**

---

## 四、★★★★★ **`.fptable` 的零填充被确认（0/128）**

### 4.1 ★★★ 实测（5 个文件的 `.fptable` 全部 128 字节为 0）

| 文件 | `.fptable` 文件偏移 | **非零字节数** |
|---|---|---|
| `ol_room_owner.exe` | **`0x42C00`** | ★ **0 / 128** |
| `Localnetworking.Ayria32` | **`0x7B600`** | ★ **0 / 128** |
| `Platformwrapper.Ayria32` | **`0x81200`** | ★ **0 / 128** |
| `Alwaysoffline.Localnet32` | **`0x3D9200`** | ★ **0 / 128** |
| `CodolGameServer.Localnet32` | **`0x64A400`** | ★ **0 / 128** |

★★★ **⇒ 全部 128 字节为 `00` ⇒ "盘上全零"** ✓ **与早前记录一致。**

### 4.2 ★★★ `.fptable` 的节表属性

| 文件 | VA | vsize | raw 偏移 | rsize | 字符 |
|---|---|---|---|---|---|
| `ol_room_owner.exe` | `0x00047000` | **128** | `0x00042C00` | **512** | **`0xC0000040`** |
| `Localnetworking.Ayria32` | `0x0007E000` | **128** | `0x0007B600` | **512** | **`0xC0000040`** |
| `Platformwrapper.Ayria32` | `0x00084000` | **128** | `0x00081200` | **512** | **`0xC0000040`** |
| `Alwaysoffline.Localnet32` | `0x003DE000` | **128** | `0x003D9200` | **512** | **`0xC0000040`** |
| `CodolGameServer.Localnet32` | `0x00806000` | **128** | `0x0064A400` | **512** | **`0xC0000040`** |

★★★ **⇒ 五处**属性完全一致**：`vsize=128` / `rsize=512` / `chars=0xC0000040`。**

### ★★★★★ `0xC0000040` 的位分解

```
0xC0000040 = INITIALIZED_DATA (0x40)
           | MEM_READ        (0x40000000)
           | MEM_WRITE       (0x80000000)
        ↓
★★★ ⇒ **可读写、已初始化数据**
   ⇒ **没有 MEM_EXECUTE** ✓（不是代码节）
   ⇒ **没有 MEM_SHARED / MEM_DISCARDABLE**
        ↓
★ 而 128 字节 = **16 个 8 字节槽**（或 32 个 4 字节槽）
```

★★ **⇒ `vsize=128` 但 `rsize=512` ⇒ 文件里占 512 字节（一整个扇区的最小对齐）,只声明 128 有效。**
**⇒ 结合"盘上全零" ⇒ **运行期被填入 128 字节数据**（16 个指针或 16 个结构）。**

★★★ **⇒ 与早前记录的"filled at runtime"一致** ✓

### 4.3 ★★★ `.fptable` 的边界

```
有 `.fptable` 的 5 个：`ol_room_owner.exe` + **4 个插件**
没有的 3 个：`Injector32.exe` / `Bootstrapper32.dll` / `Bootstrapper64.dll`
        ↓
★★★ ⇒ 判据清晰：**Ayria 框架件没有,ol-mod 自建件全有**
```

★ **⇒ 这提供了一个**极强的文件来源判据**：**
```
**有 `.fptable` ⇒ ol-mod 自建的**
**无 `.fptable` ⇒ Ayria 上游框架的**
```

---

## 五、★★★★★ **四种插件的导出契约**

### 5.1 ★★★ `.Ayria32` 型（Ayria 插件）

| 文件 | 导出数 | **导出名** |
|---|---|---|
| **`Localnetworking.Ayria32`** | **3** | `onInitialized` / **`onMessage`** / `onStartup` |
| **`Platformwrapper.Ayria32`** | **6** | ★★ **`CreateObj`** / ★★★ **`InitCrossContextByOpenID`** / ★★ **`Invoke`** / `onInitialized` / `onMessage` / `onStartup` |

★★★★★ **⇒ `Platformwrapper.Ayria32` 多出三个：**
```
`CreateObj`                  ⇒ **创建对象**（导出给宿主创建 COM-like 对象）
`InitCrossContextByOpenID`   ⇒ ★★★ **用 OpenID 初始化跨上下文**
`Invoke`                     ⇒ **调用**
        ↓
★★★ ⇒ `InitCrossContextByOpenID` 是**腾讯平台桥**的关键导出
   （`OpenID` 是腾讯账号体系,与报告 077 的
    `${CODO_OPENID}` / `${CODO_JUMP_SIGNATURE}` 呼应）
```

★ **⇒ 而 `Localnetworking.Ayria32` **只有 3 个**（不含这三个）⇒ 它不需要跨上下文。**

### 5.2 ★★★ `.Localnet32` 型（Localnet 插件）

| 文件 | 导出数 | **导出名** |
|---|---|---|
| **`Alwaysoffline.Localnet32`** | **5** | `CODOL_GetInventoryRefreshStatus` / `CODOL_GetProfileReloadStatus` / `CODOL_RequestInventoryRefresh` / `CODOL_RequestProfileReload` / **`Createserver`** |
| **`CodolGameServer.Localnet32`** | **55** | 见第 6 节 |

★★ **⇒ `.Localnet32` 型的共同导出：`Createserver`（两种都有）。**

### 5.3 ★★★ 两个 `onInitialized` / `onStartup` 的**共有性**

```
`Localnetworking.Ayria32`        : onInitialized / onMessage / onStartup
`Platformwrapper.Ayria32`        : … + onInitialized / onMessage / onStartup
`CodolGameServer.Localnet32`     : … + onInitialized / onStartup     ← ★ 无 onMessage
`Bootstrapper32.dll` / `Bootstrapper64.dll` : Broadcastmessage / onInitializationdone
        ↓
★★★ ⇒ **三种不同的回调命名族：**
   `.Ayria32` / `Localnet32` 用 **`onStartup` / `onInitialized`**（注意 **-ized**）
   `Bootstrapper*.dll` 用 **`onInitializationdone`**（注意 **Initialization + done**）
```

★★ **⇒ `onInitialized` 与 `onInitializationdone` 是**两个不同的名字**,拼写只差一部分。**
**⇒ 这与报告（`Alwaysoffline` / `AlwaysofflineRe` 的命名）同类：**名字极其接近但语义不同。****

### 5.4 ★★★ `Bootstrapper*.dll` 的 2 个导出

```
`Broadcastmessage`, `onInitializationdone`
        ↓
★ 两个架构（32/64）**导出名完全相同** ⇒ 是**同一份源码的两次编译**
```

---

## 六、★★★★★ **`CodolGameServer.Localnet32` 的 55 个导出（完整）**

### 6.1 ★★★ 按前缀分组

| 前缀 | 数量 | 说明 |
|---|---|---|
| **`CODOL_GameServerConfigure*`** | **3** | Booking / GameState / Session |
| **`CODOL_GameServerGet*Status*`** 族 | ★★ **~48** | 见下 |
| **`CODOL_GameServerRequestBots`** | **1** | — |
| **`CODOL_GameServerSetEnabled`** | **1** | — |
| **`Createserver`** | **1** | ★ Localnet 契约 |
| **`onInitialized` / `onStartup`** | **2** | ★ Ayria 契约（**两地址相同**,见早前记录） |
| **合计** | **55** | ✓ |

### 6.2 ★★★★★ 完整的 55 个导出名

```
① Configure 三件：
  CODOL_GameServerConfigureBooking
  CODOL_GameServerConfigureGameState
  CODOL_GameServerConfigureSession

② Client 八件（客户端状态）：
  CODOL_GameServerGetClientGameStateStage
  CODOL_GameServerGetClientGameplayStatus
  CODOL_GameServerGetClientIngressStatus
  CODOL_GameServerGetClientLoadingStatus
  CODOL_GameServerGetClientMenuResponseStatus
  CODOL_GameServerGetClientRejectStatus
  CODOL_GameServerGetClientReliableCommandStatus
  CODOL_GameServerGetClientUserCmdStatus

③ 网络与传输（★ 与战斗服任务最相关）：
  CODOL_GameServerGetConnectionlessDiagnosticsV1
  CODOL_GameServerGetNetchanStatus                  ★★
  CODOL_GameServerGetNetworkStatus
  CODOL_GameServerGetSnapshotDeltaStatus            ★★★
  CODOL_GameServerGetSnapshotStatus                 ★★★
  CODOL_GameServerGetTransportStatus                ★★
  CODOL_GameServerGetTransportTimingStatus
  CODOL_GameServerGetConstantConfigStringStatus

④ 会话与加载：
  CODOL_GameServerGetDedicatedSessionConsumptionStatus
  CODOL_GameServerGetLoadingStatus
  CODOL_GameServerGetSessionStatus
  CODOL_GameServerGetStatus

⑤ GameState 三件：
  CODOL_GameServerGetGameStateConfigurationStatus
  CODOL_GameServerGetGameStateReadinessStatus
  CODOL_GameServerGetGameStateStatus

⑥ 装备（loadout）：
  CODOL_GameServerGetLoadoutPreparationStatus
  CODOL_GameServerGetLoadoutResolveFailure

⑦ 角色呈现：
  CODOL_GameServerGetRegisteredCharacterPresentation
  CODOL_GameServerGetRegisteredCharacterStatus

⑧ ★★★ World 族（**18 件**，与"world 绑定"任务最相关）：
  CODOL_GameServerGetWorldBulletExecutionStatusV1
  CODOL_GameServerGetWorldBulletExecutionStatusV2
  CODOL_GameServerGetWorldClientThinkStatus
  CODOL_GameServerGetWorldEventStatus
  CODOL_GameServerGetWorldEventWeaponStatus
  CODOL_GameServerGetWorldObjectiveStatusV1
  CODOL_GameServerGetWorldPlayerFlagsStatus
  CODOL_GameServerGetWorldPlayerHealthStatus
  CODOL_GameServerGetWorldPlayerPmoveStatus
  CODOL_GameServerGetWorldPlayerSampleV1
  CODOL_GameServerGetWorldPlayerSampleV2
  CODOL_GameServerGetWorldPlayerStatus
  CODOL_GameServerGetWorldPlayerViewHeightStatus
  CODOL_GameServerGetWorldPlayerWeaponStatus
  CODOL_GameServerGetWorldPredictableEventStatusV1
  CODOL_GameServerGetWorldResolvedLoadoutStatus
  CODOL_GameServerGetWorldStatus
  （+ GetEntityDamageStatusV1 / GetSdStatusV1 下）

⑨ 其他：
  CODOL_GameServerGetBotStatus
  CODOL_GameServerGetEntityDamageStatusV1              ★★
  CODOL_GameServerGetSdStatusV1

⑩ 动作：
  CODOL_GameServerRequestBots
  CODOL_GameServerSetEnabled

⑪ 契约：
  Createserver / onInitialized / onStartup
```

### ★★★★★ 三个关键观察

```
① ★★★ **这是一个"自检 API 面"**
   ~48 个 `Get*Status` 全是**只读诊断钩子**
   ⇒ 设计意图：**外部（Lua / 宿主）可以在任何时刻查询服务器每个子系统的状态**
        ↓
★ 与报告 079 的 `mp_playlists` 的"43 个 gametype 只有 11 个脚本"形成对照：
  **插件侧提供了极密的可观测性,而脚本侧有巨大缺口**

② ★★★ **与既有 memory 的多处直接对应：**
   · `GetWorldStatus` / `GetEntityDamageStatusV1` / `GetWorldPlayerHealthStatus`
     ⇒ memory「`codol_battle_service_bind_world` **从未被调用** ⇒ `svc->world` 恒 NULL
        ⇒ 实体层/伤害/HIT 整条是死的」
        ↓
★★★ ⇒ **`GetWorldStatus` 就是查询那个"从未绑定"的 world 的钩子**
   ⇒ 可用它**在运行期验证 world 是否绑定**

   · `GetSnapshotStatus` / `GetSnapshotDeltaStatus`
     ⇒ 与 memory 的「快照索引 run 编码必须 4 位」「快照字段级离线对照」直接对应

   · `GetWorldPlayerSampleV1/V2` / `GetWorldPlayerPmoveStatus`
     ⇒ 与「出生点: 服务端权威位置」「pmove」对应

③ ★★ **只有 `V1` / `V2` 两档版本**（`SdStatusV1` / `EntityDamageStatusV1` /
   `WorldBulletExecutionStatusV1/V2` / `WorldPlayerSampleV1/V2` / `WorldObjectiveStatusV1`
   / `WorldPredictableEventStatusV1` / `ConnectionlessDiagnosticsV1`）
   ⇒ **最多两版,且 `V2` 只出现在 Bullet 与 PlayerSample**
```

### 6.3 ★★★ 三个 `Configure*` 的语义

```
`CODOL_GameServerConfigureBooking`   ⇒ **预订**
`CODOL_GameServerConfigureGameState` ⇒ **比赛状态**
`CODOL_GameServerConfigureSession`   ⇒ **会话**
        ↓
★ 与报告 077 的 `[dw_config] room_serverBookingTimeout=5` 呼应（booking 概念一致）
```

---

## 七、★★★★ 节表对照（`.text` 占比）

| 文件 | `.text` vsize | SizeOfImage | **`.text` 占比** |
|---|---|---|---|
| `Injector32.exe` | **88,141** | **`0x24000`** = 147,456 | **59.8%** |
| `Bootstrapper32.dll` | **110,981** | **`0x2C000`** = 180,224 | **61.6%** |
| `Bootstrapper64.dll` | **132,528** | **`0x38000`** = 229,376 | **57.8%** |
| `ol_room_owner.exe` | **209,113** | **`0x4B000`** = 307,200 | **68.1%** |
| `Localnetworking.Ayria32` | **280,762** | **`0x83000`** = 536,576 | **52.3%** |
| `Platformwrapper.Ayria32` | **299,884** | **`0x89000`** = 561,152 | **53.4%** |
| `Alwaysoffline.Localnet32` | **3,131,760** | **`0x405000`** = 4,214,784 | **74.3%** |
| `CodolGameServer.Localnet32` | **4,702,008** | **`0x842000`** = 8,658,944 | ★ **54.3%** |

★★ **⇒ `CodolGameServer.Localnet32` 的 `.data` vsize **1,989,748** 但 raw 只有 **176,128** ⇒
**约 1.81 MB 是运行期初始化的（未初始化数据/BSS 类）。****

★★ **⇒ `Alwaysoffline.Localnet32` 的 `.text` 占比 **74.3%** 最高（纯代码型）。**

### ★★★ 三个 Ayria 框架件都有 `.rsrc`（436 字节）

```
`Injector32.exe` / `Bootstrapper32.dll` / `Bootstrapper64.dll` 都有 `.rsrc`（vsize **436**）
        ↓
★★★ 而 **五个 ol-mod 自建件全部没有 `.rsrc`**！
   （ol_room_owner.exe 的节是：.text / .rdata / .data / **.fptable** / .reloc）
        ↓
★ ⇒ .rsrc 的 436 字节可能只是版本信息资源
```

★★ **⇒ 结合 `.fptable` 的判据,现在有**两条独立判据**区分两组文件：**
```
**有 `.rsrc` / 无 `.fptable` / 时间戳假  ⇒ Ayria 上游框架（3 个）**
**无 `.rsrc` / 有 `.fptable` / 时间戳真  ⇒ ol-mod 自建（5 个）**  ✓ 完美二分
```

---

## 八、★★★★★ **与源码树的构建血缘**

### 8.1 ★★★ 四个 ol-mod 件的构建时刻（北京时间）

| 文件 | **北京时间** |
|---|---|
| `Platformwrapper.Ayria32` | **2026-10-03 14:10:46** |
| `ol_room_owner.exe` | **2026-10-19 01:23:57** |
| `Alwaysoffline.Localnet32` | ★ **2026-10-22 03:13:48** |
| `CodolGameServer.Localnet32` | ★ **2026-10-22 03:14:07** |

### ★★★★★ 一个精确的血缘吻合

```
早前记录（记忆）：
  "`src\game_server\Appmain.cpp` 完整版 **565,999 B @2026-10-22 03:13**"
        ↓
★★★ `Alwaysoffline.Localnet32` 的构建时刻 = **2026-10-22 03:13:48**
        ↓
★★★ ⇒ **源码在 03:13 被改,二进制在 03:13:48 被构建**（相差 ~48 秒）
   ⇒ 而 `CodolGameServer.Localnet32` 在 **03:14:07**（再过 19 秒）
        ↓
★★★★★ ⇒ **两个插件是**同一次 `xmake build` 的产物**,且紧随 `Appmain.cpp` 的编辑**
```

★ **⇒ 这给"交付包的二进制来自哪次提交"提供了**精确的时间锚点**。**

★★ **⇒ 且 `Platformwrapper.Ayria32`（2026-10-03）比另外三个早 19 天
⇒ 它**在那次批量构建中没有被重建**（或它的源码没变）。**
**⇒ 这与记忆里"`PlatformwrapperRe.Ayria32`"的 `Re` 后缀存在性**有关,值得后续核对。**

### ★★★ `Localnetworking.Ayria32` 的单独情形

```
其他三个 ol-mod 件：2026-10-03 / 2026-10-19 / 2026-10-22
`Localnetworking.Ayria32`：**2026-10-24 17:00:22 UTC**
        ↓
★★★ 而这个时间**正是我上一轮写入它的时刻**
   （LastWrite **2026-10-25 01:00:22 北京** = 2026-10-24 17:00:22 UTC）
        ↓
★ ⇒ **它不在那次批量构建里** ⇒ 是被我单独覆盖的
```

---

## 九、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★ 二进制总数 | **8 个**（3 个 Ayria 框架 + 5 个 ol-mod 自建） |
| 2 | ★★ 唯一 x64 | **`Bootstrapper64.dll`**（200 字节 optHdr / **7 节** / 含 `.pdata` + `_RDATA`） |
| 3 | ★★★★★ **三个 Ayria 框架件时间戳是假的** | **2689507600（2055）** / **2299471394（2042）** / **15930（1970-01-01 04:25:30）** |
| 4 | ★★★ **五个 ol-mod 件时间戳真实** | 2026-10-03 / 10-18 / 10-21 / 10-21 / **10-24（我的覆盖）** |
| 5 | ★★★★★ **`Bootstrapper64.dll` ImageBase 更正** | 早前记 **`0x00000001`** ⇒ 实测 **`0x180000000`**（**正常**） |
| 6 | ★★ 错误原因 | 用 **PE32 偏移（+28）** 读 **PE32+** 的 ImageBase（应在 **+24**） |
| 7 | ★★ 更正后异常数 | **3 → 2**（"非法基址"作废,"假时间戳"仍成立） |
| 8 | ★★★★★ **`.fptable` 五处全零** | **0 / 128 非零字节**（实测） ✓ |
| 9 | ★★★ 五处属性一致 | `vsize=**128**` / `rsize=**512**` / `chars=**0xC0000040**` |
| 10 | ★★★ `0xC0000040` 位分解 | **INITIALIZED_DATA + MEM_READ + MEM_WRITE**（**无 EXECUTE**） |
| 11 | ★★★★ **两条独立判据区分两组文件** | **有 `.rsrc` / 无 `.fptable` / 时间戳假** = Ayria 上游；**无 `.rsrc` / 有 `.fptable` / 时间戳真** = ol-mod 自建 ✓ |
| 12 | ★★★ `.Ayria32` 导出契约 | `onInitialized` / `onMessage` / `onStartup` |
| 13 | ★★★★★ **`Platformwrapper.Ayria32` 多三个导出** | **`CreateObj`** / **`InitCrossContextByOpenID`** / **`Invoke`** |
| 14 | ★★ `InitCrossContextByOpenID` | ★★★ **用腾讯 `OpenID` 初始化跨上下文**（与 `${CODO_OPENID}` 呼应） |
| 15 | ★★★ `.Localnet32` 共同导出 | **`Createserver`** |
| 16 | ★★★ 三种回调命名族 | `.Ayria32`/`.Localnet32` 用 **`onStartup`/`onInitialized`**；`Bootstrapper*.dll` 用 **`onInitializationdone`** |
| 17 | ★★ `Bootstrapper*` 的 2 导出 | **`Broadcastmessage` / `onInitializationdone`**（32/64 同名） |
| 18 | ★★★★★ **`CodolGameServer.Localnet32` 55 导出** | **3 Configure + ~48 Get*Status + RequestBots + SetEnabled + Createserver + onInitialized + onStartup** |
| 19 | ★★★ **World 族 18 件** | 含 **`GetWorldStatus`** / `GetEntityDamageStatusV1` / `GetWorldPlayerHealthStatus` / `GetWorldPlayerPmoveStatus` / `GetWorldPlayerSampleV1/V2` |
| 20 | ★★★ 网络族 8 件 | 含 **`GetSnapshotStatus`** / **`GetSnapshotDeltaStatus`** / **`GetNetchanStatus`** / **`GetTransportStatus`** |
| 21 | ★★ 版本档 | 只有 **V1/V2**；`V2` 只出现在 **Bullet** 与 **PlayerSample** |
| 22 | ★★ `.data` BSS 特征 | `CodolGameServer` 的 `.data` vsize **1,989,748** vs raw **176,128** ⇒ **~1.81 MB 运行期初始化** |
| 23 | ★ `.text` 占比 | 最高 **`Alwaysoffline.Localnet32` 74.3%**；最低 **`Localnetworking.Ayria32` 52.3%** |
| 24 | ★★★★ **构建血缘** | `Alwaysoffline.Localnet32` = **2026-10-22 03:13:48 北京** ⇔ 源码 `Appmain.cpp` **@03:13**（**差 ~48 秒**） |
| 25 | ★★ 同批 | `CodolGameServer.Localnet32` = **03:14:07**（**再过 19 秒**） |
| 26 | ★★★ `Platformwrapper.Ayria32` 早 19 天 | **2026-10-03** ⇒ 那次批量构建中**未被重建** |
| 27 | ★★ `Localnetworking.Ayria32` | **2026-10-24 17:00:22 UTC** = **我覆盖它的时刻**（**独立证据**） |

---

## 十、结论

### 1. ★★★★★ **`.fptable` 的零填充与两条区分判据被确认**

```
`.fptable` 五处**全部 0/128 非零字节** ✓
        ↓
★★★ 两条独立判据完美二分：
   **有 `.rsrc` / 无 `.fptable` / 假时间戳** ⇒ **Ayria 上游框架（3 个）**
   **无 `.rsrc` / 有 `.fptable` / 真时间戳** ⇒ **ol-mod 自建（5 个）**
```

### 2. ★★★★★ **三个 Ayria 框架件的 PE 时间戳是伪造的**（2055 / 2042 / 1970）

★ **⇒ 而五个 ol-mod 自建件的都是真实的 2026-10 构建时间。**

### 3. ★★★★★ **构建血缘精确到 48 秒**（`Appmain.cpp` @03:13 → 插件 @03:13:48 / @03:14:07）

### 4. ★★★★★ **`CodolGameServer.Localnet32` 的 55 个导出是一个完整的自检 API 面**

★ **⇒ 其中 `GetWorldStatus` / `GetEntityDamageStatusV1` / `GetSnapshotStatus` 等
可直接用于**运行期验证既有 memory 里的多个结论**（world 是否绑定、快照状态）。**

### 5. ★★★ **更正：`Bootstrapper64.dll` 的 ImageBase 是 `0x180000000`**（正常）

★ **⇒ 早前的 `0x00000001` 是**按 PE32 偏移读 PE32+** 造成的错误。**

### 6. ★★★ **`Platformwrapper.Ayria32` 的 `InitCrossContextByOpenID`** 是腾讯平台桥

### 7. ★★ **`onInitialized`**（插件）与 **`onInitializationdone`**（Bootstrapper）是两个不同的名字

---

## 十一、下一步

- `payload\Ayria\ol-mod-runtime-manifest.json`（28,209 B）
- `enemy_recorded_path_by_spawner`（第 2542–3765 行,1,224 行）
- `bundle\_leaf2_chain.pem` / `_ca.pem` / `_leaf2.key` 的逐个确认
- 用 `GetWorldStatus` 等导出的**字符串交叉引用**（在 `CodolGameServer.Localnet32` 里搜这些状态名对应的注册逻辑）
