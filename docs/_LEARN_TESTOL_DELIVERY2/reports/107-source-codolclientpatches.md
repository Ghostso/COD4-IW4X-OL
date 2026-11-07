# 学习报告 107（重开）— `CodolClientPatches.cpp`（43,329 B / 951 行）

**学习范围**：`backend\Demonware\CodolClientPatches.cpp` 全文（**951 行逐行读完**）
**性质**：全实测
**★★★★★ 本报告收录六个重大发现**：①**八个 3.3.3.3 专用 RVA 与四个钩子** ②**七个稳定补丁站点（`0x75`→`0xEB`）** ③**`.tp3` 解包时机（~3400 ms）** ④**`sub_7FADC0` 门的反汇编与三处补丁** ⑤**两次实测纠偏（getter 方案无效 / 跳过解析器导致死循环）** ⑥**`CODOL_FORCE_RECORD_VALIDATOR` 探针的完整设计**

---

## 一、★★★★★ **本文件是 3.3.3.3-only,且自我门禁**

### 1.1 ★★★★★ 完整注释（第 20–45 行，逐字）

```cpp
// THIS FILE IS STILL 3.3.3.3-ONLY, DELIBERATELY, AND IT GATES ITSELF.
//
// These two constants are a SEPARATE copy of the host gate from
// EngineBindings::ExpectedTimestamp/ExpectedImageSize, which now name
// out.exe (1649370). That divergence is intentional rather than an
// oversight: every RVA below is a 3.3.3.3 address, so the honest gate for
// this patch set is the build those addresses describe. On an OLfinal host
// the check fails, nothing is written, and backend/Appmain.cpp logs
// "Refused to apply CODOL startup patches to an unknown executable image."
// once -- which is accurate, not a fault to chase.
//
// WHAT IT COSTS ON OLfinal: the client-side profile completion, profile
// reload, public-profile request and inventory refresh hooks do not
// install. The Demonware SERVER side is unaffected and build-independent.
//
// TODO(CODOL): port the eight RVAs below to 1649370 if the OLfinal client
// turns out to need these hooks. ...
// Exit condition is a live client reaching its loadout with these absent;
// if it does, delete this note instead of porting.
// Tools/olfinal/import-signature.py is the method that worked for the four
// constants in game_server/ClientProcessPatches.cpp, ...
```

### ★★★★★ 三个关键事实

```
① ★★★ **两个门控常量**（第 46–47 行）：
   `CodolTimestamp = 0x57611E31`
   `CodolImageSize = 0x0C72A000`
        ↓
★★★ 与 `EngineBindings::ExpectedTimestamp/ExpectedImageSize`（现在指向
   **`out.exe` 1649370**）是**分开的副本** ⇒ **刻意的分歧**
        ↓
② ★★★★ **在 OLfinal 上失败的后果**（逐字）：
   "the client-side **profile completion, profile reload,
    public-profile request and inventory refresh hooks** **do not install**.
    The **Demonware SERVER side is unaffected** and build-independent."
        ↓
③ ★★★ **退出条件（逐字）**："**a live client reaching its loadout with these absent;
   if it does, delete this note instead of porting.**"
```

★★ **⇒ 第 ③ 条是**"用实测决定要不要移植"的明确判据**。**

### ★★★ `isCodolHost` 的进程名门控（第 590–600 行）

```cpp
bool isCodolHost()
{
    std::array<wchar_t, 32768> path{};
    const auto size = GetModuleFileNameW(nullptr, path.data(), static_cast<DWORD>(path.size()));
    ...
    return _wcsicmp(std::wstring(name).c_str(), L"**codoMP_client_shipRetail.exe**") == 0;
}
```

★★ **⇒ 与报告 104 的 `isKnownClientImage`（`out.exe` + `codoMP_client_shipRetail.exe`）**不同**：**
```
报告 104（Auth3 补丁）⇒ **两个名字都接受**（`out.exe` + `codoMP_client_shipRetail.exe`）
本文件（启动补丁）⇒ ★ **只接受 `codoMP_client_shipRetail.exe`**
        ↓
★★★ ⇒ 这印证了报告 104 的注释："**There it is CORRECT and documented:
   every RVA in that file is a 3.3.3.3 address, so the build IS the precondition**"
```

---

## 二、★★★★★ **八个 3.3.3.3 专用 RVA**

### 2.1 ★★★★★ 完整列表（第 48–59 行）

```cpp
constexpr std::size_t MaximumPatchSize = 8;
constexpr std::size_t ProfileCompletionRva       = **0x2D83E0**;
constexpr std::size_t ProfileStartOperationRva   = **0x2D84D0**;
constexpr std::size_t ProfileManagerFrameRva     = **0x2D9FE0**;
constexpr std::size_t PublicProfileRequestCallRva= **0x2D866A**;
constexpr std::size_t GetPublicProfilesRva       = **0x65A890**;
constexpr std::size_t InventoryRequestRva        = **0x0A6B10**;
constexpr std::size_t InventoryFinalizeRva       = **0x0A6CC0**;
constexpr std::size_t CurrentCharacterCacheRva   = **0x8D7E3C**;
```

### ★★★★★ 八个 RVA 的完整表

| # | RVA | 名称 | 用途 |
|---|---|---|---|
| **1** | **`0x2D83E0`** | `ProfileCompletionRva` | ★ **档案完成** |
| **2** | **`0x2D84D0`** | `ProfileStartOperationRva` | ★ 启动档案操作 |
| **3** | **`0x2D9FE0`** | `ProfileManagerFrameRva` | ★★ **档案管理器帧** |
| **4** | **`0x2D866A`** | `PublicProfileRequestCallRva` | ★ 公开档案请求调用 |
| **5** | **`0x65A890`** | `GetPublicProfilesRva` | 取公开档案 |
| **6** | **`0x0A6B10`** | `InventoryRequestRva` | ★ **库存请求** |
| **7** | **`0x0A6CC0`** | `InventoryFinalizeRva` | ★ 库存完成 |
| **8** | **`0x8D7E3C`** | `CurrentCharacterCacheRva` | ★★ **当前角色缓存（数据,不是代码）** |

★★ **⇒ 第 8 个是**数据地址**（`volatile LONG *`）,其余 7 个是**代码地址**。**

### ★★★ 四个序言签名（第 61–70 行）

```cpp
ProfileCompletionPrefix     { 0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8 }   // 6 字节
ProfileManagerFramePrefix   { 0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x14 }   // 6 字节
InventoryRequestPrefix      { 0x55, 0x8B, 0xEC, 0x51, 0x80, 0x3D }   // 6 字节
InventoryFinalizePrefix     { 0x55, 0x8B, 0xEC, 0x83, 0xE4, 0xF8 }   // 6 字节
PublicProfileRequestCall    { 0xE8, 0x21, 0x22, 0x38, 0x00 }         // 5 字节
```

### ★★★★★ 三个序言的解读

```
`55`           ⇒ **PUSH EBP**
`8B EC`        ⇒ **MOV EBP, ESP**
`83 E4 F8`     ⇒ **AND ESP, -8**      （**8 字节对齐**）
`83 EC 14`     ⇒ **SUB ESP, 0x14**    （20 字节局部）
`51`           ⇒ **PUSH ECX**
`80 3D ...`    ⇒ **CMP BYTE PTR [...], imm8**
`E8 rel32`     ⇒ **CALL**
        ↓
★★★ ⇒ 四个函数序言中**三个以 `55 8B EC` 开头**（标准帧）
   ⇒ 而 `InventoryRequest` 是 `55 8B EC 51 80 3D`（**无栈对齐**）
        ↓
★★★ ⇒ `ProfileCompletion` 与 `InventoryFinalize` 的序言**完全相同**（`55 8B EC 83 E4 F8`）
   ⇒ 所以必须**同时校验两者**才能区分（第 510–513 行）
```

### ★★★ 五个结构偏移（第 72–82 行）

```cpp
constexpr std::size_t RemoteTaskProfileOffset        = **56**;
constexpr std::size_t TaskRemoteTaskOffset           = **40**;
constexpr std::size_t RemoteTaskErrorOffset          = **56**;
constexpr std::size_t ProfileKindOffset              = **108**;
constexpr std::size_t ProfileOperationOffset         = **116**;
constexpr std::size_t ProfileDeferredOperationOffset = **120**;
constexpr std::size_t ProfileDownloadAttemptOffset   = **37132**;
constexpr std::uint32_t PublicProfileKind  = **1**;
constexpr std::uint32_t PrivateProfileKind = **2**;
constexpr std::uint32_t DownloadOperation  = **1**;
constexpr std::uint32_t MissingProfileError= **800**;
```

★★★ **⇒ 七个偏移 + 四个常量值。**
**⇒ `ProfileDownloadAttemptOffset = **37132**`（`0x9104`）⇒ 一个**很大的结构偏移**。**
**⇒ 且第 388 行的 `ProfileStride = **0x9128**`（= 37160）⇒ 与 37132 接近（差 28）。**

---

## 三、★★★★★ **七个稳定补丁站点（`0x75`→`0xEB`）**

### 3.1 ★★★★★ 完整表（第 155–182 行）

```cpp
// These are the only seven differences between the archived original and
// the stable patched executable. IDA confirms that the final five suppress
// error reporting without manufacturing a successful DW state transition.
constexpr std::array<PatchSite, 7> PatchSites{
    PatchSite{**0x2422C1**, 2,
        {0x75, 0x27, 0x68, 0xDC, 0x6E, 0xC7, 0x00, 0x68},
        {**0xEB**, 0x27, 0x68, 0xDC, 0x6E, 0xC7, 0x00, 0x68}},
    PatchSite{**0x24283D**, 8,
        {0x0F, 0x85, 0x11, 0xFD, 0xFF, 0xFF, 0x68, 0x2C},
        {**0xE9**, 0x12, 0xFD, 0xFF, 0xFF, 0xFF, 0x68, 0x2C}},
    PatchSite{**0x2D2AD1**, 4, {0x75, 0x12, 0x68, 0x88}, {**0xEB**, 0x12, 0x68, 0x88}},
    PatchSite{**0x2D2B07**, 4, {0x75, 0x12, 0x68, 0xA8}, {**0xEB**, 0x12, 0x68, 0xA8}},
    PatchSite{**0x2D2B42**, 4, {0x75, 0x12, 0x68, 0xD8}, {**0xEB**, 0x12, 0x68, 0xD8}},
    PatchSite{**0x2D2B8D**, 4, {0x75, 0x4B, 0x68, 0xFC}, {**0xEB**, 0x4B, 0x68, 0xFC}},
    PatchSite{**0x2D2C18**, 4, {**0x7D**, 0x0F, 0x68, 0x3C}, {**0xEB**, 0x0F, 0x68, 0x3C}},
};
```

### ★★★★★ 七个站点的完整表

| # | RVA | 大小 | 原字节 | 补丁后 | 语义 |
|---|---|---|---|---|---|
| **1** | **`0x2422C1`** | 2 | `**75** 27` | `**EB** 27` | **JNE → JMP** |
| **2** | **`0x24283D`** | 8 | `**0F 85** 11 FD FF FF` | `**E9** 12 FD FF FF` | ★★ **JNE rel32 → JMP rel32**（**并修正了相对偏移！**） |
| **3** | **`0x2D2AD1`** | 4 | `**75** 12` | `**EB** 12` | JNE → JMP |
| **4** | **`0x2D2B07`** | 4 | `**75** 12` | `**EB** 12` | JNE → JMP |
| **5** | **`0x2D2B42`** | 4 | `**75** 12` | `**EB** 12` | JNE → JMP |
| **6** | `0x2D2B8D` | 4 | `**75** 4B` | `**EB** 4B` | JNE → JMP |
| **7** | **`0x2D2C18`** | 4 | `**7D** 0F` | `**EB** 0F` | ★★ **JGE → JMP** |

### ★★★★★ 两个操作码对照

```
`75` = **JNE rel8**  (Jump if Not Equal)
`EB` = **JMP rel8**  (无条件)
        ↓
★★★ ⇒ 补丁 1/3/4/5/6 都是 **JNE → JMP**（**条件跳转改成无条件**）

`7D` = **JGE rel8**  (Jump if Greater or Equal)
`EB` = **JMP rel8**
        ↓
★★★ ⇒ 补丁 7 是 **JGE → JMP**（**有符号比较后跳转 → 无条件**）

`0F 85` = **JNE rel32**
`E9`    = **JMP rel32**
        ↓
★★★ ⇒ 补丁 2 是 **JNE rel32 → JMP rel32**
```

### ★★★★★ 补丁 2 的**相对偏移修正**

```
原：`0F 85 11 FD FF FF`  ⇒ JNE, 偏移 = **0xFFFFFD11**（= −751）
改：`E9    12 FD FF FF`  ⇒ JMP, 偏移 = **0xFFFFFD12**（= −750）
        ↓
★★★ **偏移从 −751 改成 −750（+1）**
        ↓
★★★★★ 原因：`0F 85 rel32` 是 **6 字节指令**,而 `E9 rel32` 是 **5 字节**
   ⇒ 若偏移不变,跳转目标会**偏移 1 字节**
   ⇒ **必须 +1 修正** ✓
```

★ **⇒ 这是一个**极其细致的补丁**（注意到指令长度差并修正了相对偏移）。**

### ★★★★★ 七个站点的分布

```
`0x2422C1` / `0x24283D`  ⇒ **0x24 段**（2 个）
`0x2D2AD1` – `0x2D2C18`  ⇒ **0x2D2 段**（5 个,**连续密集**）
        ↓
★★★ ⇒ 5 个密集站点跨 `0x2D2AD1` – `0x2D2C18` = **0x147 字节**（327 字节）
   ⇒ 平均每 **65 字节**一个 ⇒ **同一个函数里的连续错误检查**
```

### ★★★ 注释的关键声明（逐字）

```
"**IDA confirms that the final five suppress error reporting
 without manufacturing a successful DW state transition.**"
        ↓
★★★ ⇒ 最后 5 个补丁（`0x2D2AD1` – `0x2D2C18`）**只抑制错误上报**,
   **不伪造成功的 DW 状态转换**
```

---

## 四、★★★★★ **`.tp3` 解包时机（~3400 ms）**

### 4.1 ★★★★★ 完整注释（第 836–840 行，逐字）

```cpp
// ★★★ 2026-10-07 05:0x -- **必须等镜像解包**（实测踩到并修正）：
// 插件 DllMain 跑在客户端 `.tp3` 段**解包之前**，那一刻 `0x806F20` 还是密文
// ⇒ 首次实测直接 `unexpected bytes at RVA 0x406F20 -- refused`（03:31:30 日志）。
// 游戏服插件的日志给了正确时机：`deferred startup: .tp3 image unpacked and stable after ~3400 ms`。
// 所以这里起一个**后台轮询线程**：每秒看一次，字节对上就打，最多等 120 秒。
```

### ★★★★★ 三个精确事实

```
① ★★★ **插件 DllMain 跑在客户端 `.tp3` 段解包之前**
        ↓
② ★★★ 那一刻 `0x806F20` **还是密文** ⇒ 首次实测报
   **`unexpected bytes at RVA 0x406F20 -- refused`**（日志时间 **03:31:30**）
        ↓
③ ★★★★★ **游戏服插件的日志给出了正确时机**：
   **`deferred startup: .tp3 image unpacked and stable after ~3400 ms`**
        ↓
★★★ ⇒ 所以起**后台轮询线程**：每秒看一次,最多等 **120 秒**
```

★★★★★ **⇒ 第 ③ 条是**跨插件的知识传递**：**
```
`CodolGameServer.Localnet32` 的日志揭示了 `.tp3` 解包耗时 **~3400 ms**
        ↓
★★★ 而 `Alwaysoffline.Localnet32`（本文件所在）**借用这个知识**
   ⇒ 起轮询线程等解包完成
        ↓
★★★ ⇒ 与 memory 的「`.tp3` 加密节：客户端代码加密在盘上,运行期解密」**完全吻合**
```

★★ **⇒ 且给出了**精确的等待时长 `~3400 ms`**（之前只知道"运行期解密",不知多久）。**

---

## 五、★★★★★ **`sub_7FADC0` 门的反汇编与三处补丁**

### 5.1 ★★★★★ 门判定区的现场反汇编（第 866–877 行，逐字）

```
门判定区反汇编（现场 capstone，`0x7FAF19`-`0x7FAF38`）：
    007faf19  cmp dword [ebp-0x48], 2      ; **status==2 ?**
    007faf1d  jne 0x7faf38                 ; ★ 不等则跳走
    007faf1f  test ebx, ebx                ; **error==0 ?**
    007faf21  jne 0x7faf38                 ; ★ 非零则跳走
    007faf2c  lea edi, [ebx+1]             ; → **1（成功路径参数）**
    007faf2f  call 0x7fb380
    007faf34  mov byte [esi+4], 1          ; ★★ **ctx+4 = 1（唯一写入者）**
```

### ★★★★★ 完整的三处补丁（第 885–889 行）

```cpp
constexpr std::array<GateSite, 3> gateSites{ {
    { **0x3FAF1D**, { 0x75, 0x19, 0x00 }, { **0x72, 0x19, 0x00** }, 2 },   // JNE → JB
    { **0x3FAF21**, { 0x75, 0x15, 0x00 }, { **0x90, 0x90, 0x00** }, 2 },   // JNE → NOP NOP
    { **0x3FAF2C**, { 0x8D, 0x7B, 0x01 }, { **0x6A, 0x01, 0x5F** }, 3 },   // LEA EDI,[EBX+1] → PUSH 1; POP EDI
} };
```

### ★★★★★ 三个补丁的精确语义

| # | RVA | 原 | 改 | 语义 |
|---|---|---|---|---|
| **1** | **`0x3FAF1D`** | `75 19`（**JNE**） | ★ **`72 19`（JB）** | ★★★ **"不等则跳" → "小于则跳"** ⇒ **status 3 也走成功路径** |
| **2** | **`0x3FAF21`** | `75 15`（**JNE**） | ★★ **`90 90`（NOP NOP）** | ★★★ **不再要求 `error == 0`** |
| **3** | **`0x3FAF2C`** | `8D 7B 01`（**LEA EDI,[EBX+1]**） | ★★ **`6A 01 5F`（PUSH 1; POP EDI）** | ★★★ **强制 `edi = 1`**（与成功路径同参） |

★★★ **⇒ 三个补丁合起来：**
```
① 把 `status == 2` 放宽为 `status >= 2`（`JB` = 无符号小于）
② 去掉 `error == 0` 的要求
③ 强制成功路径的参数 `edi = 1`
        ↓
★★★★★ ⇒ **门 `sub_7FADC0` 无条件走成功路径**
   ⇒ 写 `ctx+4 = 1` ⇒ `AllocResultHandler(ok=1)` ⇒ 链条继续
```

★★ **⇒ 且明确"**直接补门本体**（等价 frida d12 的强制点；**不再触碰任何共享 getter**）"。**

---

## 六、★★★★★ **两次实测纠偏（极有价值的教训）**

### 6.1 ★★★★★ 纠偏一：**跳过解析器导致死循环**（第 849–855 行，逐字）

```cpp
// 上一版把**校验器** `sub_806F20` 改成 `mov al,1; ret 4`，虽然门过了、`server_index` 也到 0，
// 但客户端随后**永远不发 `mmstart`** —— 原因：`sub_806F20` **同时是解析器**
// （记录字段是它一个个读进去的），跳过它 ⇒ 记录 `+0x168/+0x16C` 全是 0
// ⇒ `HandleMMBookReply` 门3 拿推送 ID（`RoomHostUid = 1000001`）与 0 比 ⇒ 不等
// ⇒ 清零 + `sub_6292B0` 重发分配请求 ⇒ 5 秒循环（d17 实测）。
```

★★★★★ **⇒ 完整的死循环链：**
```
① 把校验器 `sub_806F20` 改成 `mov al,1; ret 4`
        ↓
② 门过了、`server_index` 也到 0（**看起来成功**）
        ↓
★★★ ③ 但客户端**永远不发 `mmstart`**
        ↓
★★★ ④ 原因：**`sub_806F20` 同时是解析器**（记录字段是它逐个读进去的）
   ⇒ 跳过它 ⇒ 记录 `+0x168/+0x16C` **全是 0**
        ↓
★★★ ⑤ `HandleMMBookReply` 门3 拿推送 ID（**`RoomHostUid = 1000001`**）与 **0** 比
   ⇒ **不等**
        ↓
★★★ ⑥ 清零 + `sub_6292B0` 重发分配请求 ⇒ **5 秒循环**（d17 实测）
```

★ **⇒ 第 ④ 条是**关键洞察：一个函数**同时承担校验和解析两个职责** ⇒ 跳过它就连解析也没了。**

### ★★★★★ 纠偏二：**getter 方案无效且连坐 UI/启动**（第 857–865 行，逐字）

```cpp
// ⚠ 下列 getter 方案 **d23 实测无效且连坐 UI/启动**（更正见下方 04:4x 段）：
//     状态 getter `sub_B83EF0`（RVA 0x783EF0）：`55 8B EC 51 56 8B` → `B8 02 00 00 00 C3`（mov eax,2; ret）
//     错误 getter `sub_927100`（RVA 0x527100）：`8B 41 38`            → `33 C0 C3`（xor eax,eax; ret）
// ★★★ 2026-10-07 04:4x -- **改正目标（d23 实测，单变量）**：
//   arm 门控生效、两处 getter 补丁**现场字节回读确认已写入**，但门仍未放行
//   ⇒ `sub_B83EF0`/`sub_927100` **不是门 `sub_7FADC0` 的输入**（属另一类；改写连坐启动/UI 文本）。
```

★★★★★ **⇒ 一个"补丁写进去了但没效果"的精确诊断：**
```
① 两处 getter 补丁**现场字节回读确认已写入**
        ↓
★★★ ② 但门**仍未放行**
        ↓
★★★★★ ③ 结论：**`sub_B83EF0` / `sub_927100` 不是门 `sub_7FADC0` 的输入**
   ⇒ 它们**属于另一类**（改写会**连坐启动/UI 文本**）
        ↓
★ ④ 正确做法：**直接补门本体**
```

★★ **⇒ 第 ③ 条是**"字节回读确认 ≠ 逻辑正确"的范例**（补丁生效了,但改错了对象）。**

### ★★★ 两个 getter 的完整字节

| getter | RVA | 原字节 | 改为 | 语义 |
|---|---|---|---|---|
| **状态 getter `sub_B83EF0`** | **`0x783EF0`** | `55 8B EC 51 56 8B` | `B8 02 00 00 00 C3` | **`mov eax, 2; ret`**（恒返回 2） |
| **错误 getter `sub_927100`** | **`0x527100`** | `8B 41 38` | `33 C0 C3` | **`xor eax, eax; ret`**（恒返回 0） |

★★ **⇒ 两者都是**6 字节 → 6 字节** / **3 字节 → 3 字节**（长度不变,不破坏后续指令）。**

---

## 七、★★★★★ **`CODOL_FORCE_RECORD_VALIDATOR` 探针的完整设计**

### 7.1 ★★★★★ 三个设计要素

```
① ★★★ **默认关闭**：`getenv("CODOL_FORCE_RECORD_VALIDATOR") != "1"` ⇒ 直接返回
        ↓
② ★★★★ **必须"武装"后才动手**（`armForcedAllocationPatch`）：
   "getter 补丁**不能在启动期生效**。实测（d18–d21，**四连坏启动**）：
    启动期 t≈8 s 就把两个 getter 改成撒谎，客户端的下载链路（同一个容器类）
    在 t≈36–39 s 误判 ⇒ 弹「**致命错误 / EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE**」后退出；
    回退 validator 版即恢复好启动（d22）。
    ⇒ 正解：**武装后才动手** —— `armForcedAllocationPatch()` 在
    「**kind-3 应答真的带上 server 候选**」时置位（= 用户点第二次匹配，
    离客户端发 43 B op-27 分配请求约 10 s；启动早已结束）。"
        ↓
③ ★★★ **后台轮询线程**：每秒看一次,最多 **2400 次**（= 2400 秒）
```

### ★★★★★ 第 ② 条的完整因果

```
启动期 t≈**8 s** 就打 getter 补丁
        ↓
★★★ 客户端下载链路（**同一个容器类**）在 t≈**36–39 s** 误判
        ↓
★★★ 弹「**致命错误 / EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE**」后退出
        ↓
★★★ 回退 validator 版 ⇒ 恢复好启动（d22）
        ↓
★★★★★ ⇒ **正解：武装后才动手**
   ⇒ 武装时机 = "kind-3 应答真的带上 server 候选"（用户点第二次匹配）
   ⇒ 离客户端发 **43 B op-27 分配请求**约 **10 s**
```

### ★★★ 四连坏启动（d18–d21）

★★ **⇒ 连续四次坏启动 ⇒ 才定位到"启动期不能动手"。**

### ★★★ 证据分级（第 783–788 行，逐字）

```
"⚠ 证据分级：**客户端原生强制**（`rope.md` §5.3 **第二级**）。
  它**只证明"门之后的链条能不能通"**,
  **不证明我们的记录形状已经正确**；正路仍是按 §5.2.1 把**类型标签流**做对。"
        ↓
★★★ ⇒ **明确承认这是探针,不是修复**
```

★★ **⇒ 且注释两次重复了这段（04:5x 与 06:0x 各一次）⇒ 强调。**

### ★★★ 两份副本的问题（第 786–788 行，逐字）

```cpp
// ⚠ 同一只补丁在 `src/game_server/ClientProcessPatches.cpp` 另有一份**未部署**的副本
//   （客户端里的 `CodolGameServer.Localnet32` 还是 **2026-10-03** 的构建，源码树这份不会生效）；
//   **生效的是本处**，因为 `Alwaysoffline.Localnet32` 每轮都从源码树部署。
```

★★★ **⇒ 一个**部署差异**：**
```
`CodolGameServer.Localnet32` ⇒ 客户端里的是 **2026-10-03** 构建 ⇒ 源码树改动**不生效**
`Alwaysoffline.Localnet32`   ⇒ **每轮都从源码树部署** ⇒ 改动**生效**
        ↓
★★★ ⇒ 与报告 082 的 PE 时间戳**完全吻合**：
   `Platformwrapper.Ayria32` = **2026-10-03 06:10:46**（未被重建）
   `Alwaysoffline.Localnet32` = **2026-10-21 19:13:48**（重建过）
```

---

## 八、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **3.3.3.3 门控** | `CodolTimestamp = **0x57611E31**` / `CodolImageSize = **0x0C72A000**`（与 `EngineBindings` 的 out.exe 门控**分开的副本**） |
| 2 | ★★★★ OLfinal 的代价 | **profile completion / profile reload / public-profile request / inventory refresh** 四个钩子**不安装**；**Demonware 服务端不受影响** |
| 3 | ★★★ 退出条件 | "**a live client reaching its loadout with these absent; if it does, delete this note instead of porting**" |
| 4 | ★★ `isCodolHost` | **只接受 `codoMP_client_shipRetail.exe`**（与报告 104 接受两个名字**不同**） |
| 5 | ★★★★★ **八个 RVA** | `0x2D83E0` / `0x2D84D0` / `0x2D9FE0` / `0x2D866A` / `0x65A890` / `0x0A6B10` / `0x0A6CC0` / ★ `0x8D7E3C`（**数据地址**） |
| 6 | ★★★ 四个序言 | `55 8B EC 83 E4 F8`（×2）/ `55 8B EC 83 EC 14` / `55 8B EC 51 80 3D` / `E8 21 22 38 00` |
| 7 | ★★ 序言冲突 | `ProfileCompletion` 与 `InventoryFinalize` 序言**完全相同** ⇒ 必须同时校验两者 |
| 8 | ★★★ 七个偏移 + 四常量 | `56`/`40`/`56`/`108`/`116`/`120`/**`37132`**；`PublicProfileKind=1`/`PrivateProfileKind=2`/`DownloadOperation=1`/**`MissingProfileError=800`** |
| 9 | ★★★ `ProfileStride` | **`0x9128`** = 37160（与 `37132` 差 28） |
| 10 | ★★★★★ **七个补丁站点** | `0x2422C1` `0x24283D` `0x2D2AD1` `0x2D2B07` `0x2D2B42` `0x2D2B8D` `0x2D2C18` |
| 11 | ★★★ 操作码 | 5 个 **`75`(JNE) → `EB`(JMP)** / 1 个 **`7D`(JGE) → `EB`** / 1 个 **`0F 85`(JNE rel32) → `E9`(JMP rel32)** |
| 12 | ★★★★★ **补丁 2 的相对偏移修正** | `11 FD FF FF`(−751) → **`12 FD FF FF`(−750)** ⇒ **因 `0F 85`(6 字节) 变 `E9`(5 字节),偏移必须 +1** |
| 13 | ★★ 站点分布 | `0x24` 段 **2 个** + `0x2D2` 段 **5 个**（跨 327 字节,平均每 **65** 字节一个） |
| 14 | ★★★ IDA 结论 | "the **final five suppress error reporting without manufacturing a successful DW state transition**" |
| 15 | ★★★★★ **`.tp3` 解包时机** | 插件 DllMain 跑在**解包之前** ⇒ `0x806F20` 还是密文 ⇒ 首次实测报 **`unexpected bytes at RVA 0x406F20 -- refused`**（03:31:30） |
| 16 | ★★★★★ **精确时长** | 游戏服插件日志：**`deferred startup: .tp3 image unpacked and stable after ~3400 ms`** |
| 17 | ★★ 轮询设计 | 每秒一次,最多 **120 秒**（注释）/ 代码里 **2400 次**（2400 秒） |
| 18 | ★★★★★ **`sub_7FADC0` 门反汇编** | `cmp [ebp-0x48],2` / `jne` / `test ebx,ebx` / `jne` / `lea edi,[ebx+1]` / `call 0x7fb380` / **`mov byte [esi+4],1`**（**`ctx+4` 的唯一写入者**） |
| 19 | ★★★★★ **三处门补丁** | `0x3FAF1D` **`75 19`→`72 19`**（JNE→**JB**,status 3 也成功）/ `0x3FAF21` **`75 15`→`90 90`**（去掉 error==0）/ `0x3FAF2C` **`8D 7B 01`→`6A 01 5F`**（**`push 1; pop edi`**） |
| 20 | ★★★★★ **纠偏一：跳过解析器** | `sub_806F20` **同时是校验器和解析器** ⇒ 改成 `mov al,1; ret 4` ⇒ 记录 `+0x168/+0x16C` **全 0** ⇒ 推送 ID(`RoomHostUid=1000001`) 与 0 不等 ⇒ **5 秒循环**（d17） |
| 21 | ★★★★★ **纠偏二：getter 方案无效** | 两处 getter **字节回读确认已写入**但门**仍未放行** ⇒ **它们不是门的输入** ⇒ 改写**连坐启动/UI 文本**（d23） |
| 22 | ★★★ 两个 getter 字节 | `sub_B83EF0`@`0x783EF0`：`55 8B EC 51 56 8B`→`B8 02 00 00 00 C3`；`sub_927100`@`0x527100`：`8B 41 38`→`33 C0 C3` |
| 23 | ★★★★★ **武装时机** | 启动期 t≈**8 s** 打补丁 ⇒ 下载链路在 t≈**36–39 s** 误判 ⇒ **`EXE_DOWNLOAD_PUBLISHER_FILE_FAILURE`** 退出（**d18–d21 四连坏启动**） |
| 24 | ★★★ 武装条件 | "**kind-3 应答真的带上 server 候选**"（用户点第二次匹配，离发 **43 B op-27 分配请求**约 **10 s**） |
| 25 | ★★★ 证据分级 | "**客户端原生强制**（`rope.md` §5.3 **第二级**）" ⇒ **只证明"门之后的链条能不能通",不证明记录形状正确** |
| 26 | ★★★ 两份副本 | `ClientProcessPatches.cpp` 那份**未部署**（客户端里是 **2026-10-03** 构建）；**生效的是本处**（`Alwaysoffline` 每轮部署） |
| 27 | ★★ 与报告 082 吻合 | `Platformwrapper.Ayria32` = **2026-10-03 06:10:46**（未重建）/ `Alwaysoffline.Localnet32` = **2026-10-21 19:13:48**（重建过） |

---

## 九、结论

### 1. ★★★★★ **本文件是 3.3.3.3-only 并自我门禁,且有明确的退出条件**

```
`CodolTimestamp = 0x57611E31` / `CodolImageSize = 0x0C72A000`
        ↓
★★★ OLfinal 上 ⇒ 四个钩子不安装 ⇒ 日志 "Refused to apply … unknown executable image"（**准确,不是故障**）
        ↓
★★★★★ 退出条件：**"a live client reaching its loadout with these absent"** ⇒ 满足就删注释不移植
```

### 2. ★★★★★ **七个补丁站点全是"条件跳转 → 无条件跳转"**

★ **⇒ 且补丁 2 注意到 **`0F 85`(6 字节) → `E9`(5 字节)** 的长度差,**把相对偏移 +1 修正**。**

### 3. ★★★★★ **`.tp3` 解包耗时 ~3400 ms**（从游戏服插件的日志获得）

★ **⇒ 插件 DllMain 跑在解包之前 ⇒ 必须起轮询线程等。**

### 4. ★★★★★ **两次实测纠偏,各有精确诊断**

```
纠偏一：`sub_806F20` **同时是校验器和解析器** ⇒ 跳过它 ⇒ 记录全 0 ⇒ **5 秒循环**
纠偏二：两处 getter **不是门的输入** ⇒ 字节回写成功但**门不放行** ⇒ 还连坐 UI
        ↓
★★★ ⇒ 最终正解：**直接补门本体三处**
```

### 5. ★★★★ **`CODOL_FORCE_RECORD_VALIDATOR` 探针有"武装"机制**

★ **⇒ 因为启动期打补丁会让下载链路误判（**四连坏启动** d18–d21）。**

### 6. ★★★ **明确承认这是探针不是修复**（`rope.md` §5.3 第二级证据）

---

## 十、下一步

- `CodolClientPatches.hpp`（41 行）
- `Auth3TlsTransport.cpp`（311 行）
- 然后 12 个 Service 实现
