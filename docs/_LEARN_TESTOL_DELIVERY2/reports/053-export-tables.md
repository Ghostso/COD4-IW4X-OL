# 学习报告 053（重开）— 六个 DLL 的完整导出契约

**学习范围**：`Bootstrapper32/64.dll` + 四个插件的**全部导出符号**
**方法**：手工解析 Export Directory（含 Ordinal/Name 双表）
**性质**：全实测
**★★★ 本报告给出**三类插件契约**的完整符号清单**

---

## 一、★★★★★ 六个 DLL 的导出总表

| DLL | 文件内 DLL 名 | 导出数 |
|---|---|---|
| `Bootstrapper32.dll` | **`Bootstrapper32.dll`** | **2** |
| `Bootstrapper64.dll` | **`Bootstrapper64.dll`** | **2** |
| `Alwaysoffline.Localnet32` | **`AlwaysofflineRe.Localnet32`** | **5** |
| `CodolGameServer.Localnet32` | **`CodolGameServer.Localnet32`** | **55** |
| `Localnetworking.Ayria32` | **`LocalnetworkingRe.Ayria32`** | **3** |
| `Platformwrapper.Ayria32` | **`PlatformwrapperRe.Ayria32`** | **6** |

★★★ **⇒ 三个插件的内部 DLL 名带 `Re.` 后缀：**
```
Localnetworking.Ayria32   →  LocalnetworkingRe.Ayria32
Platformwrapper.Ayria32   →  PlatformwrapperRe.Ayria32
Alwaysoffline.Localnet32  →  AlwaysofflineRe.Localnet32
        ↓
★ 而 CodolGameServer 和两个 Bootstrapper **不带 Re**
```

★★ **⇒ `Re` = "Reimplementation"（重实现）—— 上游 ol-mod 的命名习惯。**

---

## 二、★★★★ `Bootstrapper32.dll` / `Bootstrapper64.dll`（各 2 个）

### 2.1 ★★★ 32 位版

```
DLL Name: Bootstrapper32.dll
NumFunc=2 NumNames=2
  [  1] 0x000023E4  Broadcastmessage
  [  2] 0x00002425  onInitializationdone
```

### 2.2 ★★★ 64 位版

```
DLL Name: Bootstrapper64.dll
NumFunc=2 NumNames=2
  [  1] 0x00002D8C  Broadcastmessage
  [  2] 0x00002DFC  onInitializationdone
```

★★★ **⇒ 两版**导出名完全相同**，只是 RVA 不同（32 位 `0x23E4`/`0x2425` vs 64 位 `0x2D8C`/`0x2DFC`）。**

★★ **⇒ 两个函数：**
```
Broadcastmessage      （★ 向插件广播）
onInitializationdone  （★ 初始化完成回调）
```

★★★ **⇒ 这是**反向接口**：加载器向插件提供这两个函数。**

★ **⇒ 与报告 020 的反汇编分析**完全吻合**（`Broadcastmessage` 遍历插件数组 + 短路）。**

---

## 三、★★★★ `Alwaysoffline.Localnet32`（5 个）

```
DLL Name: AlwaysofflineRe.Localnet32
NumFunc=5 NumNames=5
  [  1] 0x000C6C30  CODOL_GetInventoryRefreshStatus
  [  2] 0x000C6B70  CODOL_GetProfileReloadStatus
  [  3] 0x000C6BD0  CODOL_RequestInventoryRefresh
  [  4] 0x000C6B10  CODOL_RequestProfileReload
  [  5] 0x000C67F0  Createserver
```

### ★★★★★ 五个导出的语义

| # | 符号 | 作用 |
|---|---|---|
| 1 | `CODOL_GetInventoryRefreshStatus` | 查询**库存刷新**状态 |
| 2 | `CODOL_GetProfileReloadStatus` | 查询**档案重载**状态 |
| 3 | `CODOL_RequestInventoryRefresh` | ★ **请求**库存刷新 |
| 4 | `CODOL_RequestProfileReload` | ★ **请求**档案重载 |
| 5 | **`Createserver`** | ★★★ **真正的入口**（带 SEH + /GS） |

★★★ **⇒ 两对 Request/GetStatus + 一个 Createserver。**

★★ **⇒ 这是**最小的后端契约**：只有 5 个符号。**

★ **⇒ 与 `CodolGameServer` 的 55 个形成鲜明对比。**

---

## 四、★★★★★ `CodolGameServer.Localnet32`（55 个）

### 4.1 ★★★ 完整的 55 个导出（按序号）

**配置入口（3 个）**
```
[ 1] 0x00222B30  CODOL_GameServerConfigureBooking
[ 2] 0x00221AF0  CODOL_GameServerConfigureGameState
[ 3] 0x002215B0  CODOL_GameServerConfigureSession       ← ★★★ 最重要
```

**客户端状态查询（10 个）**
```
[ 5] 0x00220E70  GetClientGameStateStage
[ 6] 0x002214D0  GetClientGameplayStatus
[ 7] 0x00220CC0  GetClientIngressStatus
[ 8] 0x00220EE0  GetClientLoadingStatus
[ 9] 0x00221370  GetClientMenuResponseStatus
[10] 0x00221120  GetClientRejectStatus
[11] 0x00221290  GetClientReliableCommandStatus
[12] 0x00220FD0  GetClientUserCmdStatus
```

**通用状态（10 个）**
```
[ 4] GetBotStatus        [13] GetConnectionlessDiagnosticsV1
[14] GetConstantConfigStringStatus
[15] GetDedicatedSessionConsumptionStatus
[17] GetGameStateConfigurationStatus
[18] GetGameStateReadinessStatus
[19] GetGameStateStatus  [20] GetLoadingStatus
[21] GetLoadoutPreparationStatus
[22] GetLoadoutResolveFailure
```

**网络/传输（5 个）**
```
[23] GetNetchanStatus   [24] GetNetworkStatus
[31] GetStatus          [32] GetTransportStatus
[33] GetTransportTimingStatus
```

**快照/实体（3 个）**
```
[16] 0x00222E30  GetEntityDamageStatusV1     ← ★★★
[29] 0x00222D80  GetSnapshotDeltaStatus
[30] 0x00222D40  GetSnapshotStatus
```

**角色/会话（5 个）**
```
[25] GetRegisteredCharacterPresentation
[26] GetRegisteredCharacterStatus
[27] GetSdStatusV1
[28] GetSessionStatus
```

**★ World 层（17 个）**
```
[34] 0x002236E0  GetWorldBulletExecutionStatusV1
[35] 0x00223820  GetWorldBulletExecutionStatusV2
[36] 0x00223520  GetWorldClientThinkStatus
[37] 0x00224060  GetWorldEventStatus
[38] 0x00224130  GetWorldEventWeaponStatus
[39] 0x00223410  GetWorldObjectiveStatusV1
[40] 0x00223E80  GetWorldPlayerFlagsStatus
[41] 0x00223FA0  GetWorldPlayerHealthStatus
[42] 0x00223DF0  GetWorldPlayerPmoveStatus
[43] 0x00223990  GetWorldPlayerSampleV1
[44] 0x00223A30  GetWorldPlayerSampleV2
[45] 0x00223D10  GetWorldPlayerStatus
[46] 0x00223EF0  GetWorldPlayerViewHeightStatus
[47] 0x00224220  GetWorldPlayerWeaponStatus
[48] 0x002235A0  GetWorldPredictableEventStatusV1
[49] 0x00224360  GetWorldResolvedLoadoutStatus
[50] 0x00222DF0  GetWorldStatus
```

**机器人 + 启用（2 个）**
```
[51] 0x002209D0  CODOL_GameServerRequestBots
[52] 0x00220890  CODOL_GameServerSetEnabled
```

**非 `CODOL_` 前缀的三个（3 个）**
```
[53] 0x0005DD70  Createserver        ← ★★★ 空桩（`33 C0 C3`）
[54] 0x00220880  onInitialized       ← ★ 与 onStartup 同址
[55] 0x00220880  onStartup
```

★★★ **⇒ 三个非 `CODOL_` 前缀：`Createserver` / `onInitialized` / `onStartup`。**

★★ **⇒ 52 + 3 = 55 ✓**

### 4.2 ★★★★★ 两个关键发现

**① `onInitialized` 与 `onStartup` **同地址**（`0x00220880`）**

★★★ **⇒ 编译器把两个空函数**合并**了（tail merge / ICF），**
**或其中一个是 `ret` 桩。**

**② `Createserver` 的 RVA `0x0005DD70` **明显低于**其他所有导出**

```
Createserver      0x0005DD70   ← 在 .text 前段（1/8 处）
其他所有导出      0x0022xxxx   ← 在 .text 中后段
        ↓
★ 相差约 0x1C2B60（1.8 MB）
```

★★★ **⇒ 链接顺序的结果：`Createserver` 定义在**早期编译单元**，**
**而 `CODOL_GameServer*` 导出集中在**最后编译的单元**。**

---

## 五、★★★★ `Localnetworking.Ayria32`（3 个）

```
DLL Name: LocalnetworkingRe.Ayria32
NumFunc=3 NumNames=3
  [  1] 0x00009DF0  onInitialized
  [  2] 0x00017090  onMessage
  [  3] 0x00016FC0  onStartup
```

★★★ **⇒ 这是**最标准的 Ayria 三件套**：**
```
onInitialized  0x00009DF0
onMessage      0x00017090
onStartup      0x00016FC0
```

★ **⇒ 三个地址**各不相同**（不像 `CodolGameServer` 的 `onStartup`/`onInitialized` 同址）。**

★★ **⇒ 上一轮（报告 053）已实测 `onMessage` 是 `32 C0 C3`（`xor al,al; ret`）—— 空桩。**

---

## 六、★★★★ `Platformwrapper.Ayria32`（6 个）

```
DLL Name: PlatformwrapperRe.Ayria32
NumFunc=6 NumNames=6
  [  1] 0x000176C0  CreateObj
  [  2] 0x00007440  InitCrossContextByOpenID
  [  3] 0x00017600  Invoke
  [  4] 0x000076E0  onInitialized
  [  5] 0x000190F0  onMessage
  [  6] 0x00018E90  onStartup
```

### ★★★ 六个导出的分类

**Ayria 三件套（3 个）**
```
onInitialized  0x000076E0
onMessage      0x000190F0
onStartup      0x00018E90
```

**★ 腾讯平台接口（3 个）**
```
CreateObj                  0x000176C0   ← ★ COM 式对象创建
Invoke                     0x00017600   ← ★ COM 式方法调用
InitCrossContextByOpenID   0x00007440   ← ★★ 跨上下文初始化
```

★★★ **⇒ `InitCrossContextByOpenID` 与报告 046 的 `OpenID`**直接相关**：**
```
fake_auth_tls.py 的 tag25 = OpenID = "10001"
        ↓
Platformwrapper 的 InitCrossContextByOpenID
        ↓
★ 用 OpenID 初始化跨上下文
```

★★ **⇒ `CreateObj` + `Invoke` 是**COM 式的对象接口**（不是纯 C 函数）。**

---

## 七、★★★★★ 三类插件契约的完整对照

| 类型 | 代表 | 契约符号 | 加载器 |
|---|---|---|---|
| **A. Ayria 型** | `Localnetworking.Ayria32`<br>`Platformwrapper.Ayria32` | **`onStartup` / `onInitialized` / `onMessage`** | **`Bootstrapper32.dll`**（扫 `*.Ayria32`） |
| **B. Localnet 型** | `Alwaysoffline.Localnet32`<br>`CodolGameServer.Localnet32` | **`Createserver`**（+ 各自的 `CODOL_*`） | **`Localnetworking.Ayria32`**（扫 `*.Localnet32`） |
| **C. 加载器自身** | `Bootstrapper32/64.dll` | **`Broadcastmessage` / `onInitializationdone`** | （被 `Injector32.exe` 加载） |

★★★ **⇒ 两类插件契约 + 一个加载器接口，全部由导出符号定义。**

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★ 三个 `Re` 后缀 | `LocalnetworkingRe` / `PlatformwrapperRe` / `AlwaysofflineRe` |
| 2 | ★ 无 `Re` | `CodolGameServer` / `Bootstrapper32` / `Bootstrapper64` |
| 3 | ★★ `Bootstrapper32` 导出 | `Broadcastmessage` 0x23E4 / `onInitializationdone` 0x2425 |
| 4 | ★★ `Bootstrapper64` 导出 | 同名，RVA **0x2D8C / 0x2DFC** |
| 5 | ★★★ `Alwaysoffline` 5 个 | 2 对 Request/GetStatus + **`Createserver`** 0xC67F0 |
| 6 | ★★★★★ `CodolGameServer` 55 个 | 3 Configure + 47 Get* + RequestBots + SetEnabled + **3 非前缀** |
| 7 | ★★★ **`onInitialized` == `onStartup`** | **同址 `0x00220880`** |
| 8 | ★★★ `Createserver` RVA | **`0x0005DD70`**（比其余低 **1.8 MB**） |
| 9 | ★ `Localnetworking` 3 个 | `onInitialized` 0x9DF0 / `onMessage` 0x17090 / `onStartup` 0x16FC0 |
| 10 | ★★ `Platformwrapper` 6 个 | 三件套 + **`CreateObj` / `Invoke` / `InitCrossContextByOpenID`** |
| 11 | ★★ `InitCrossContextByOpenID` | 与 `fake_auth_tls` 的 **OpenID（tag25）** 相关 |
| 12 | ★★★ 三类契约 | **Ayria 型（3 件套）/ Localnet 型（Createserver）/ 加载器（2 个）** |

---

## 九、结论

### 1. ★★★★★ **`Re` 后缀是"重实现"标记**，只用于三个插件

★ **⇒ `CodolGameServer` 没有 `Re`，因为它是**全新实现**（不是替代官方组件）。**

### 2. ★★★★★ **`CodolGameServer` 的 55 个导出**构成完整的能力清单

★ **⇒ 其中 **17 个 `GetWorld*` + `GetEntityDamageStatusV1`** 是战斗服的核心探针。**

### 3. ★★★ **`onInitialized` 与 `onStartup` 同址**（编译器合并）

### 4. ★★★ **`Createserver` 的 RVA 比其余低 1.8 MB**（链接顺序）

### 5. ★★★ **`Platformwrapper` 的 `CreateObj`/`Invoke`** 是 COM 式接口

### 6. ★★ **`Alwaysoffline` 只有 5 个导出**（最小后端契约）

---

## 十、下一步

- `payload\` **18 个小 map lua** + `cha.lua`/`zm.lua` 剩余
- `payload\` **`MarketplaceSkus.json` 结构**（2.5 MB）
- `source\` 结构与关键文档
