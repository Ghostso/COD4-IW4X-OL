# COMBAT_P1_B1_SOURCE_DIFF — B-1 只读采样代码差异

**任务**：COMBAT-P1-B1（**仅授权 B-1**）
**日期**：2026-10-11
**授权范围**：仅新增 `EngineBindings::bind()` 门禁前的**可选只读采样代码**。未构建、未部署、未启动/附加/注入任何进程。
**修改对象**：**F**（活动基准）`F:\桌面\ol\ol-mod-olfinal\src\game_server\EngineBindings.cpp`
**未触碰**：D（冻结副本）、`EngineBindings.hpp`、任何 RVA/ABI/守卫/协议常量/网络逻辑、任何导出、`GOLDEN-LOBBY-001`、`REF_LOBBY_KIT`、既有日志与历史证据。

---

## 0. 步骤 1 结论：B-1 在本次实施前**不存在**

| 检查项 | 结果 |
|---|---|
| `COMBAT_P1_B1_SOURCE_DIFF.md` / `_SAFETY_REVIEW.md` / `_TEST_PLAN.md` / `_SHA256_MANIFEST.txt` | **均不存在**（工作区根、F、D 三处递归检索 0 命中） |
| 源码中是否已有采样代码（`OLMOD_COMBAT_P0_SAMPLE` / `image-sample` / `SampleHostImageIdentity` / `HostImageSample`） | **0 命中**（F 与 D 均查） |
| `EngineBindings.cpp` 实施前工作区状态 | 工作区 blob == HEAD blob（`cc679b5db6635f975f8f7861e63547413a2a2002`），**未修改** |
⇒ 未发现既有 B-1 交付物或源码差异，因此在**本轮**实施。

---

## 1. 差异总览

```
$ git -C F diff --stat -- src/game_server/EngineBindings.cpp
 src/game_server/EngineBindings.cpp | 297 +++++++++++++++++++++++++++++++++++++
 1 file changed, 297 insertions(+)

hunk 1: @@ -3645,4 +3645,295 @@ namespace CodolGameServer
hunk 2: @@ -3653,4 +3944,10 @@ namespace CodolGameServer
```

**结构性核对（对 git diff 的 `+` 行统计）**

| 指标 | 值 | 说明 |
|---|---|---|
| 新增行 | **297** | 全部为插入 |
| 删除/修改行 | **0** | **既有代码一行未改**（纯追加） |
| `{` / `}` | 34 / 34 | 括号平衡 |
| `(` / `)` | 133 / 133 | 括号平衡 |
| 新增匿名命名空间块 | 1 | 与文件既有 `namespace { }` 用法一致 |
| 新增导出（`dllexport`） | **0** | 约束 5 |
| 触碰既有守卫（`std::equal(..., module_ + …)`） | **0** | 约束 4 |
| 内存写/改页保护/发布绑定（`VirtualProtect` / `WriteProcessMemory` / `bindingCommitted_.store(true)`） | **0** | 约束 3 |

---

## 2. 修改点一：门禁前的唯一调用（hunk 2，新行 3944..3953）

```
        bindingCommitted_.store(false, std::memory_order_release);
        module_ = reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));

        // AUTHORISED COMBAT-P1 B-1 DIAGNOSTIC. Read-only and opt-in: returns immediately
        // unless OLMOD_COMBAT_P0_SAMPLE == "1". Its output goes to the log only and is NOT
        // consulted by any condition below; the gate and every guard are unchanged.
        SampleHostImageIdentity(module_);

        if (!module_)
            return false;
```

**关键性质**
- 调用位于 `module_` 赋值之后、**任何 `return false` 之前** ⇒ 无论门禁通过与否都可达（这正是 COMBAT-P0 的缺口）。
- 调用的**返回值被忽略**（函数返回 `void`）⇒ **不可能参与判定**（约束 3）。
- 紧随其后的 `if (!module_) return false;` 及其后所有代码**逐字未改**（约束 2）。

---

## 3. 修改点二：新增的只读采样辅助块（hunk 1，新行 3646..3939）

> 下列为**文件中的实际内容**（行号 = 修改后的最终行号，格式 `行号| 原文`）。

```
3645|     }
3646| 
3647|     // ============================================================================
3648|     // OLMOD(combat-p1-b1-readonly-image-sample): AUTHORISED DIAGNOSTIC; OFF BY DEFAULT.
3649|     //
3650|     // Why it exists: on the 2026-10-10 runs, EngineBindings::bind() returned false at one
3651|     // of three SILENT early returns (module / DOS magic / the single NT "if"), so the log
3652|     // could not say WHICH condition failed, and nothing could say whether the running
3653|     // image's bytes match the binding catalog. This sampler reads ONLY the host module's
3654|     // own PE headers and two RVA byte ranges, then writes one log line per item.
3655|     //
3656|     // It is deliberately NOT part of the binding decision:
3657|     //   * gated on the environment variable OLMOD_COMBAT_P0_SAMPLE == "1";
3658|     //   * when that variable is absent or not exactly "1", it returns BEFORE reading or
3659|     //     logging anything, so bind() behaviour is unchanged;
3660|     //   * it never writes memory, never changes page protection, never publishes a
3661|     //     pointer, never calls a guarded function, never touches bindingCommitted_;
3662|     //   * it cannot make the gate pass: it neither relaxes SizeOfImage nor skips a guard.
3663|     // The expected bytes below are PROBE EXPECTATIONS for offline comparison only. They are
3664|     // never consumed by bind() and must not be mistaken for binding data.
3665|     // ============================================================================
3666|     namespace
3667|     {
3668|         constexpr const char *HostImageSampleSwitch = "OLMOD_COMBAT_P0_SAMPLE";
3669|         constexpr std::uint32_t HostImageSampleComFrameRva = 0x000FEA20;
3670|         constexpr std::uint32_t HostImageSampleClientPatchRva = 0x0008371A;
3671|         // Probe expectation copied from ClientProcessPatches.cpp:207-211
3672|         // (UnsignedFastfileVerificationRva). Reported as expected= only; never enforced here.
3673|         constexpr std::array<std::uint8_t, 8> HostImageSampleClientPatchBytes{
3674|             0x83, 0x7C, 0x24, 0x08, 0x01, 0x0F, 0x94, 0xC0};
3675| 
3676|         std::string HostImageHex32(const std::uint32_t value)
3677|         {
3678|             char buffer[16]{};
3679|             std::snprintf(buffer, sizeof(buffer), "0x%08X", value);
3680|             return std::string(buffer);
3681|         }
3682| 
3683|         std::string HostImageHex16(const std::uint16_t value)
3684|         {
3685|             char buffer[16]{};
3686|             std::snprintf(buffer, sizeof(buffer), "0x%04X", value);
3687|             return std::string(buffer);
3688|         }
3689| 
3690|         void HostImageAppendBytes(
3691|             std::string &out,
3692|             const std::uint8_t *const bytes,
3693|             const std::size_t size)
3694|         {
3695|             constexpr char Hex[] = "0123456789ABCDEF";
3696|             for (std::size_t index = 0; index < size; ++index)
3697|             {
3698|                 if (index != 0)
3699|                     out.push_back(' ');
3700|                 out.push_back(Hex[(bytes[index] >> 4) & 0x0F]);
3701|                 out.push_back(Hex[bytes[index] & 0x0F]);
3702|             }
3703|         }
3704| 
3705|         void HostImageSampleLog(const std::string &message)
3706|         {
3707|             OlMod::RuntimeLog::write(OlMod::RuntimeLog::Channel::GameServer, message);
3708|         }
3709| 
3710|         // SEH-guarded byte copy. No object with a destructor may live inside __try
3711|         // (MSVC C2712), so the destination is a caller-owned POD buffer and the caller
3712|         // formats the log line afterwards.
3713|         bool ReadHostBytesSafely(
3714|             const std::uint8_t *const address,
3715|             void *const destination,
3716|             const std::size_t size)
3717|         {
3718|             __try
3719|             {
3720|                 auto *const target = static_cast<std::uint8_t *>(destination);
3721|                 for (std::size_t index = 0; index < size; ++index)
3722|                     target[index] = address[index];
3723|                 return true;
3724|             }
3725|             __except (EXCEPTION_EXECUTE_HANDLER)
3726|             {
3727|                 return false;
3728|             }
3729|         }
3730| 
3731|         bool HostRangeIsReadable(
3732|             const std::uint8_t *const module,
3733|             const std::uint32_t rva,
3734|             const std::size_t size)
3735|         {
3736|             const auto *const address = module + rva;
3737|             MEMORY_BASIC_INFORMATION information{};
3738|             if (VirtualQuery(address, &information, sizeof(information)) != sizeof(information))
3739|                 return false;
3740|             if (information.State != MEM_COMMIT)
3741|                 return false;
3742|             constexpr DWORD ReadableMask =
3743|                 PAGE_READONLY | PAGE_READWRITE | PAGE_WRITECOPY |
3744|                 PAGE_EXECUTE_READ | PAGE_EXECUTE_READWRITE | PAGE_EXECUTE_WRITECOPY;
3745|             if ((information.Protect & ReadableMask) == 0)
3746|                 return false;
3747|             const auto *const regionBegin =
3748|                 static_cast<const std::uint8_t *>(information.BaseAddress);
3749|             const auto *const regionEnd = regionBegin + information.RegionSize;
3750|             return address >= regionBegin && address + size <= regionEnd;
3751|         }
3752| 
3753|         // Reads one RVA into a fixed buffer after an explicit size and readability check.
3754|         // Returns false and leaves the buffer untouched when any check fails.
3755|         bool HostImageReadRva(
3756|             const std::uint8_t *const module,
3757|             const std::uint32_t rva,
3758|             const std::uint32_t sizeOfImage,
3759|             std::uint8_t *const destination,
3760|             const std::size_t size,
3761|             const char *&failure)
3762|         {
3763|             failure = nullptr;
3764|             if (rva > sizeOfImage || size > static_cast<std::size_t>(sizeOfImage) - rva)
3765|             {
3766|                 failure = "out_of_sizeofimage";
3767|                 return false;
3768|             }
3769|             if (!HostRangeIsReadable(module, rva, size))
3770|             {
3771|                 failure = "not_readable";
3772|                 return false;
3773|             }
3774|             if (!ReadHostBytesSafely(module + rva, destination, size))
3775|             {
3776|                 failure = "read_faulted";
3777|                 return false;
3778|             }
3779|             return true;
3780|         }
3781| 
3782|         void SampleHostImageIdentity(std::uint8_t *const module)
3783|         {
3784|             char enabled[8]{};
3785|             const auto enabledLength = GetEnvironmentVariableA(
3786|                 HostImageSampleSwitch,
3787|                 enabled,
3788|                 static_cast<DWORD>(sizeof(enabled)));
3789|             if (enabledLength != 1 || enabled[0] != '1')
3790|                 return;
3791| 
3792|             const auto processId = GetCurrentProcessId();
3793|             std::string prefix = "image-sample v=1 sampler=combat-p1-b1 pid=";
3794|             prefix += std::to_string(static_cast<unsigned long long>(processId));
3795|             prefix += " switch=";
3796|             prefix += HostImageSampleSwitch;
3797|             prefix += "=1";
3798| 
3799|             if (!module)
3800|             {
3801|                 HostImageSampleLog(prefix + " stage=module_missing");
3802|                 return;
3803|             }
3804| 
3805|             char imagePath[520]{};
3806|             const auto pathLength = GetModuleFileNameA(
3807|                 nullptr, imagePath, static_cast<DWORD>(sizeof(imagePath)));
3808|             std::string identity = prefix;
3809|             identity += " base=";
3810|             identity += HostImageHex32(static_cast<std::uint32_t>(
3811|                 reinterpret_cast<std::uintptr_t>(module)));
3812|             identity += " path=\"";
3813|             if (pathLength > 0 && static_cast<std::size_t>(pathLength) < sizeof(imagePath))
3814|                 identity.append(imagePath, static_cast<std::size_t>(pathLength));
3815|             else
3816|                 identity += "<unavailable>";
3817|             identity += '"';
3818| 
3819|             std::uint32_t eLfanew = 0;
3820|             if (!HostRangeIsReadable(module, 0x3C, sizeof(eLfanew)) ||
3821|                 !ReadHostBytesSafely(module + 0x3C, &eLfanew, sizeof(eLfanew)))
3822|             {
3823|                 HostImageSampleLog(identity + " stage=e_lfanew_unreadable");
3824|                 return;
3825|             }
3826|             if (eLfanew < 0x40 || eLfanew > 0x1000)
3827|             {
3828|                 HostImageSampleLog(
3829|                     identity + " stage=e_lfanew_out_of_range value=" + HostImageHex32(eLfanew));
3830|                 return;
3831|             }
3832| 
3833|             IMAGE_NT_HEADERS nt{};
3834|             if (!HostRangeIsReadable(module, eLfanew, sizeof(nt)) ||
3835|                 !ReadHostBytesSafely(module + eLfanew, &nt, sizeof(nt)))
3836|             {
3837|                 HostImageSampleLog(identity + " stage=nt_headers_unreadable");
3838|                 return;
3839|             }
3840| 
3841|             const auto sizeOfImage = static_cast<std::uint32_t>(nt.OptionalHeader.SizeOfImage);
3842|             std::string pe = prefix;
3843|             pe += " pe signature=";
3844|             pe += HostImageHex32(static_cast<std::uint32_t>(nt.Signature));
3845|             pe += " machine=";
3846|             pe += HostImageHex16(nt.FileHeader.Machine);
3847|             pe += " sections=";
3848|             pe += std::to_string(static_cast<unsigned long long>(nt.FileHeader.NumberOfSections));
3849|             pe += " timestamp=";
3850|             pe += HostImageHex32(nt.FileHeader.TimeDateStamp);
3851|             pe += " sizeofimage=";
3852|             pe += HostImageHex32(sizeOfImage);
3853|             pe += " gate_expected_timestamp=";
3854|             pe += HostImageHex32(EngineBindings::ExpectedTimestamp);
3855|             pe += " gate_expected_sizeofimage=";
3856|             pe += HostImageHex32(static_cast<std::uint32_t>(EngineBindings::ExpectedImageSize));
3857|             pe += " gate_timestamp_equal=";
3858|             pe += nt.FileHeader.TimeDateStamp == EngineBindings::ExpectedTimestamp ? "1" : "0";
3859|             pe += " gate_sizeofimage_equal=";
3860|             pe += sizeOfImage == static_cast<std::uint32_t>(EngineBindings::ExpectedImageSize)
3861|                 ? "1" : "0";
3862|             HostImageSampleLog(identity);
3863|             HostImageSampleLog(pe);
3864| 
3865|             // RVA 0x0FEA20 -- Com_Frame. Expected bytes are taken from the REAL guard
3866|             // array (ComFramePrefix, EngineBindings.cpp:755-757); nothing is duplicated.
3867|             {
3868|                 constexpr std::uint32_t Rva = HostImageSampleComFrameRva;
3869|                 constexpr std::size_t Size = 5;
3870|                 std::array<std::uint8_t, Size> bytes{};
3871|                 const char *failure = nullptr;
3872|                 std::string line = prefix;
3873|                 line += " rva=";
3874|                 line += HostImageHex32(Rva);
3875|                 line += " len=";
3876|                 line += std::to_string(static_cast<unsigned long long>(Size));
3877|                 if (!HostImageReadRva(module, Rva, sizeOfImage, bytes.data(), Size, failure))
3878|                 {
3879|                     line += " stage=";
3880|                     line += failure;
3881|                     HostImageSampleLog(line);
3882|                 }
3883|                 else
3884|                 {
3885|                     const bool match = std::equal(
3886|                         ComFramePrefix.begin(), ComFramePrefix.end(), bytes.begin());
3887|                     line += " expected=";
3888|                     HostImageAppendBytes(line, ComFramePrefix.data(), ComFramePrefix.size());
3889|                     line += " effective=";
3890|                     HostImageAppendBytes(line, bytes.data(), bytes.size());
3891|                     line += " match=";
3892|                     line += match ? "1" : "0";
3893|                     line += " source=EngineBindings.cpp:755-757";
3894|                     HostImageSampleLog(line);
3895|                 }
3896|             }
3897| 
3898|             // RVA 0x8371A -- unsigned-fastfile verification. Expected bytes are a probe-only
3899|             // copy of ClientProcessPatches.cpp:207-211; that TU is not linked here.
3900|             {
3901|                 constexpr std::uint32_t Rva = HostImageSampleClientPatchRva;
3902|                 constexpr std::size_t Size = HostImageSampleClientPatchBytes.size();
3903|                 std::array<std::uint8_t, Size> bytes{};
3904|                 const char *failure = nullptr;
3905|                 std::string line = prefix;
3906|                 line += " rva=";
3907|                 line += HostImageHex32(Rva);
3908|                 line += " len=";
3909|                 line += std::to_string(static_cast<unsigned long long>(Size));
3910|                 if (!HostImageReadRva(module, Rva, sizeOfImage, bytes.data(), Size, failure))
3911|                 {
3912|                     line += " stage=";
3913|                     line += failure;
3914|                     HostImageSampleLog(line);
3915|                 }
3916|                 else
3917|                 {
3918|                     const bool match = std::equal(
3919|                         HostImageSampleClientPatchBytes.begin(),
3920|                         HostImageSampleClientPatchBytes.end(),
3921|                         bytes.begin());
3922|                     line += " expected=";
3923|                     HostImageAppendBytes(
3924|                         line,
3925|                         HostImageSampleClientPatchBytes.data(),
3926|                         HostImageSampleClientPatchBytes.size());
3927|                     line += " effective=";
3928|                     HostImageAppendBytes(line, bytes.data(), bytes.size());
3929|                     line += " match=";
3930|                     line += match ? "1" : "0";
3931|                     line += " source=ClientProcessPatches.cpp:207-211";
3932|                     HostImageSampleLog(line);
3933|                 }
3934|             }
3935|         }
3936|     }
3937| 
3938|     bool EngineBindings::bind()
3939|     {
3940|         // OLMOD(engine-binding-transaction): resolved pointers are staged in
3941|         // this long-lived adapter, but validity is published only after build,
3942|         // prefix, runtime-slot, message, and glass-bridge checks all succeed.
3943|         // A failed rebind must also revoke a previously committed publication.
3944|         bindingCommitted_.store(false, std::memory_order_release);
3945|         module_ = reinterpret_cast<std::uint8_t *>(GetModuleHandleW(nullptr));
3946| 
3947|         // AUTHORISED COMBAT-P1 B-1 DIAGNOSTIC. Read-only and opt-in: returns immediately
3948|         // unless OLMOD_COMBAT_P0_SAMPLE == "1". Its output goes to the log only and is NOT
3949|         // consulted by any condition below; the gate and every guard are unchanged.
3950|         SampleHostImageIdentity(module_);
3951| 
3952|         if (!module_)
3953|             return false;
3954| 
```

---

## 4. 默认关闭路径（约束 1 与 2）

`SampleHostImageIdentity()` 的**第一段代码**即为开关检查：

```
            char enabled[8]{};
            const auto enabledLength = GetEnvironmentVariableA(
                HostImageSampleSwitch,
                enabled,
                static_cast<DWORD>(sizeof(enabled)));
            if (enabledLength != 1 || enabled[0] != '1')
                return;
```

| 情形 | 行为 |
|---|---|
| `OLMOD_COMBAT_P0_SAMPLE` **不存在** | `GetEnvironmentVariableA` 返回 0 ⇒ **立即 return**：不读内存、不写日志、不建字符串、不调用任何 Win32 查询 API |
| 设为 `"0"` / `""` / `"true"` / `"1 "` / 长度 ≠ 1 | **立即 return**（只接受**恰好**一个字符 `'1'`） |
| 设为 `"1"` | 进入采样；仍**只读**、只写日志、返回值忽略 |

⇒ **默认路径与改动前逐位相同**：唯一新增的行为是一次 `GetEnvironmentVariableA` 调用（无副作用）。`bind()` 的返回判定、日志文本、守卫顺序、控制流**均未改变**。

---

## 5. 异常处理（约束 3 与"只读"）

三层保护，任一层失败都**只记录**、不影响 `bind()`：

| 层 | 机制 | 位置（新行号） | 失败时的输出 |
|---|---|---|---|
| 1 | **显式边界检查**：`rva > sizeOfImage \|\| size > sizeOfImage - rva` | `HostImageReadRva`，约 3755-3775 | `stage=out_of_sizeofimage` |
| 2 | **页可读性检查**：`VirtualQuery` 要求 `State == MEM_COMMIT` 且保护位含可读掩码，且整段落在同一 region 内 | `HostRangeIsReadable`，约 3728-3753 | `stage=not_readable` |
| 3 | **SEH 守卫的实际读取**：`__try { 逐字节复制 } __except (EXCEPTION_EXECUTE_HANDLER) { return false; }` | `ReadHostBytesSafely`，约 3700-3726 | `stage=read_faulted` |

另外的早退与对应的日志阶段名：`stage=module_missing`、`stage=e_lfanew_unreadable`、`stage=e_lfanew_out_of_range`、`stage=nt_headers_unreadable`。

**C2712 规避**：`ReadHostBytesSafely` 内**不含任何带析构函数的对象**（目标缓冲由调用方以 POD 提供），日志字符串的构造全部发生在 `__try` **之外**。这也是为什么采样被拆成「读取」与「格式化」两步。

---

## 6. 明确未改动的内容（逐项核对）

| 项 | 状态 | 核对方式 |
|---|---|---|
| `EngineBindings.hpp` | **未修改** | `git status` 仅 `EngineBindings.cpp` 为 M |
| `ExpectedTimestamp` / `ExpectedImageSize` / `ComFrameRva` | **未修改**（仅被**读取**用于打印 `gate_expected_*` 与 `gate_*_equal`） | 常量值仍为 `0x6096930A` / `0x0E5D6000` / `0x0FEA20` |
| 75 条既有守卫（9 具名 + 66 链） | **未修改、未重排、未增删** | 新增行中无 `std::equal(..., module_ + …)` 模式 |
| 门禁判定 `if (nt->Signature … TimeDateStamp … SizeOfImage)` | **未修改**（仍为同一个 `if`，仍静默返回 false） | 该 `if` 不在 diff 中 |
| RVA / 结构偏移 / ABI / 协议常量 / 网络逻辑 | **未修改** | diff 为纯追加，且新增块不含此类定义 |
| 导出表 | **未新增任何导出** | 新增行 `dllexport` 计数 = 0 |
| `bindingCommitted_` | **未被写入**（新增块不触碰它） | 新增行中 `bindingCommitted_.store(true)` 计数 = 0 |
| D 冻结副本 | **未触碰** | D 的 `git status` 仍为 6 条 |
| `GOLDEN-LOBBY-001` / `REF_LOBBY_KIT` / 既有日志 | **未触碰** | 本轮全部写入仅限交付物与 F 的单一源文件 |

---

## 7. 制品哈希（改动前后）

| 项 | 值 |
|---|---|
| 改动前 SHA-256（= HEAD 内容） | 见 `COMBAT_P1_B1_SHA256_MANIFEST.txt` §A |
| 改动前 git blob | `cc679b5db6635f975f8f7861e63547413a2a2002` |
| **改动后 SHA-256** | `5B3794254DB79CEF1E74AA94E2ABBC4E0C41EC0F0CB0597C70C5970FD753BB6F` |
| **改动后 git blob** | `5894e06bb5d1bf6cfb7896600b17ef8ea53b48b6` |
| 改动后字节数 | **885,136**（改动前 871,806；+13,330） |
| F `git status --porcelain` | 实施前 17 条 → 实施后 **18 条**（新增 `M src/game_server/EngineBindings.cpp`） |

**完整差异可复现命令（只读）**

```
git -C "F:\桌面\ol\ol-mod-olfinal" diff -U3 -- src/game_server/EngineBindings.cpp
git -C "F:\桌面\ol\ol-mod-olfinal" hash-object src/game_server/EngineBindings.cpp
```

---

## 8. 本轮未做

未构建、未编译、未部署、未调用 `ol_deploy`、未启动/附加/注入/终止任何进程、未调用 `CODOL_GameServerSetEnabled`、未执行 Stage D/E/F/T、未读任何进程内存、未改动 D 与冻结基线。**静态期望字节仍未验证**（见 `COMBAT_P1_B1_TEST_PLAN.md` §6）。
