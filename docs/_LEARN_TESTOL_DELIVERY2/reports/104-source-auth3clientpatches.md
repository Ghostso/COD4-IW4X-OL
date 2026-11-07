# 学习报告 104（重开）— `backend\Demonware\Auth3ClientPatches.cpp`（10,785 B / 260 行）

**学习范围**：`backend\Demonware\Auth3ClientPatches.cpp` 全文
**性质**：全实测（**逐行读完**）
**★★★★★ 本报告收录五个重大发现**：①**三个补丁的完整字节签名** ②**`0x1430` 的固定间距** ③**四态判据（`located`/`absent`/`ambiguous`/`unusable`）** ④**"absent 与 ambiguous 不是同一答案"的两周教训** ⑤**借用进程名门控导致远端玩家登录失败**

---

## 一、★★★★★ **三个补丁的完整字节签名**

### 1.1 ★★★★★ 三个模式（第 21–30 行，逐字）

```cpp
constexpr std::array<int, **11**> CertificateCall{
    0x68, -1, -1, -1, -1, 0x0F, 0x95, 0xC2, 0x52, 0x50, 0xE8,
};
constexpr std::array<int, **10**> CertificateBranch{
    0x74, -1, 0x83, 0xBE, 0x78, 0x02, 0x00, 0x00, 0x00, 0x74,
};
constexpr std::array<int, **18**> AuthenticationBranch{
    0x8B, 0x86, -1, -1, -1, -1, 0x83, -1, -1, 0x85, 0xC0, 0x0F,
    0x84, -1, -1, -1, -1, 0x68,
};
```

★★★ **⇒ `-1` 是**通配符**（`if (pattern[index] >= 0 && ...)`）。**

### ★★★★★ 三个签名的完整解读

#### ① `CertificateCall`（11 字节）

```
`68 ?? ?? ?? ??`  ⇒ **PUSH imm32**（压入一个地址）
`0F 95 C2`        ⇒ **SETNE DL**（条件置字节）
`52`              ⇒ **PUSH EDX**
`50`              ⇒ **PUSH EAX**
`E8`              ⇒ **CALL rel32**
        ↓
★★★ ⇒ 一个"**根据条件 push 参数后调用**"的序列
```

#### ② `CertificateBranch`（10 字节）

```
`74 ??`           ⇒ **JE rel8**（短跳转）
`83 BE 78 02 00 00 00`  ⇒ **CMP DWORD PTR [ESI+0x00000278], 0**
`74`              ⇒ **JE rel8**
        ↓
★★★ ⇒ **比较 `[ESI+0x278]` 是否为 0,然后两次条件跳转**
   ⇒ ★★ **`0x278` 是一个精确的结构偏移**
```

#### ③ `AuthenticationBranch`（18 字节）

```
`8B 86 ?? ?? ?? ??`  ⇒ **MOV EAX, [ESI+imm32]**
`83 ?? ??`           ⇒ **CMP r/m32, imm8**
`85 C0`              ⇒ **TEST EAX, EAX**
`0F 84 ?? ?? ?? ??`  ⇒ **JE rel32**
`68`                 ⇒ **PUSH imm32**
        ↓
★★★ ⇒ 一个"**读字段 → 比较 → 测试 → 条件跳转 → push**"的序列
```

### ★★★★★ 三个补丁的实际修改（第 96–101 行）

```cpp
void patch(const std::span<std::uint8_t> image, const std::array<std::size_t, 3> &sites)
{
    std::memset(image.data() + sites[0] + **10**, **0x90**, **5**);   // ★ 5 个 NOP
    image[sites[1]] = **0x71**;                                        // ★ 0x74 → 0x71
    image[sites[2] + **12**] = **0x81**;                               // ★ 0x84 → 0x81
}
```

### ★★★★★ 三个补丁的精确语义

| # | 位置 | 原字节 | 改为 | 含义 |
|---|---|---|---|---|
| **1** | `sites[0] + **10**` | （`E8` 后的 5 字节 = `CALL rel32` 的操作数） | ★★ **`0x90 × 5`** | ★★★ **NOP 掉 CALL 的目标地址** |
| **2** | `sites[1]` | **`0x74`**（`JE`） | ★★ **`0x71`**（`JNO`） | ★★★ **把"相等则跳"改成"不溢出则跳"** |
| **3** | `sites[2] + **12**` | **`0x84`**（`JE rel32` 的 opcode） | ★★ **`0x81`**（`JNO rel32`） | ★★★ **同上** |

★★★ **⇒ 补丁 2 和 3 是**同一个技巧**：**
```
`0x74` = **JE**  (Jump if Equal,       ZF=1)
`0x71` = **JNO** (Jump if Not Overflow, OF=0)
        ↓
`0x84` = **JE rel32**
`0x81` = **JNO rel32**
        ↓
★★★★★ ⇒ **把"相等就跳"改成"不溢出就跳"** ⇒ **条件几乎总成立** ⇒ **跳过校验**
```

★★ **⇒ 这是一个**经典的二进制补丁技巧**（把条件跳转改成"永不成立"或"总成立"）。**
**⇒ 而 `0x71`（JNO）在正常情况下**几乎总成立**（溢出罕见）⇒ **等效于无条件跳转**。**

★★ **⇒ 补丁 1 是**NOP 掉 5 字节**（`E8 rel32` 的操作数部分）⇒ **但 `E8` 本身还在!**
**⇒ 若 NOP 掉的是 `E8` 后的 4 字节 + 1 字节 ⇒ `E8 90 90 90 90` ⇒ **CALL 到一个无效地址**。**
**⇒ 更可能：`sites[0] + 10` 正好是**下一个指令的起始**,NOP 掉 5 字节的**条件调用**。**
**⇒ 记录为**待精确核对项**（需看反汇编）。**

---

## 二、★★★★★ **`0x1430` 的固定间距**

### 2.1 ★★★★★ 完整注释（第 103–119 行，逐字）

```cpp
// WHY THERE IS NO PROCESS-NAME GATE HERE ANY MORE -- handoff §§191g.
//
// This used to refuse any image not named codoMP_client_shipRetail.exe, copied from the
// sibling gate in CodolClientPatches.cpp. There it is CORRECT and documented: every RVA in
// that file is a 3.3.3.3 address, so the build IS the precondition. Here it was never the
// precondition -- the three sites below are found by BYTE SIGNATURE, and they locate
// uniquely in OLfinal's out.exe (1649370) at the same **0x1430 spacing** they have in 3.3.3.3.
// See Tools/olfinal/check-auth3-patches.py, which measures that offline against either.
```

★★★★★ **⇒ 三个关键事实：**
```
① ★★★ **旧实现借用了 `CodolClientPatches.cpp` 的进程名门控**
   （拒绝非 `codoMP_client_shipRetail.exe` 的镜像）
        ↓
② ★★★ **在 `CodolClientPatches.cpp` 里那个门控是**正确的**：
   "every RVA in that file is a **3.3.3.3 address**, so **the build IS the precondition**"
        ↓
③ ★★★★★ **但在这里（Auth3 补丁）**从不需要**那个门控：
   "the three sites below are found **BY BYTE SIGNATURE**, and they locate
    uniquely in OLfinal's `out.exe` (**1649370**) at the **same `0x1430` spacing**
    they have in 3.3.3.3"
        ↓
★★★ ⇒ **`0x1430` = 三个站点之间的固定间距**
   ⇒ 这是**跨 build 不变的**（而绝对偏移会变）
```

★★ **⇒ 又一次见到 `1649370`（与报告 077 的 `build_number` 吻合）。**

### ★★★★★ 借用门控的**实际代价**（第 112–117 行，逐字）

```cpp
// The cost of the borrowed gate was a remote player's login. installAuth3ClientPatches()
// returned TRUE WITHOUT PATCHING on out.exe, ServerFactory::create read that as success,
// and the client validated the self-signed certificate Auth3TlsTransport mints at runtime
// for real -- `tlsv1 alert unknown ca`, then a 40 second stall and a hang up. It never
// showed on this machine because this machine's client does not take the Auth3 path.
```

### ★★★★★ 完整的故障链

```
① ★★★ `installAuth3ClientPatches()` 在 `out.exe` 上**返回 TRUE 但没有打补丁**
        ↓
② `ServerFactory::create` **把它读成成功**
        ↓
③ ★★★ 客户端**真的去校验** `Auth3TlsTransport` 运行期生成的自签证书
        ↓
④ ★★★★★ **`tlsv1 alert unknown ca`** ⇒ **40 秒卡顿** ⇒ **挂断**
        ↓
★★★ ⑤ "It never showed on this machine because **this machine's client
    does not take the Auth3 path**."
```

★★★ **⇒ 第 ⑤ 条是**"本机不复现"的精确原因**：**
```
本机的客户端**不走 Auth3 路径** ⇒ 补丁缺失无影响
        ↓
★★★ ⇒ 远端玩家走 Auth3 路径 ⇒ **暴露**
```

★ **⇒ 这是**"返回 true 但没做事"的经典危害**（与报告 099 的 `readDelta` 返回 false 但调用方忽略同类）。**

---

## 三、★★★★★ **四态判据（本报告的核心设计）**

### 3.1 ★★★★★ 完整枚举（第 32–48 行，逐字）

```cpp
// ABSENT AND AMBIGUOUS ARE NOT THE SAME ANSWER, and the old findUnique() returned
// std::nullopt for both. That single word is why this file could be wrong for a fortnight:
// "no sites" reads as "not the game, carry on" and "two sites" reads as "the game, but do
// not touch it", and only one of those is safe to treat as success.
enum class SiteSearch
{
    located,    // all three, exactly once each -- safe to patch
    absent,     // none of the three appear; this image does not contain the code
    ambiguous,  // present but not uniquely, or only partly present -- NOT safe to patch
    unusable,   // not a mappable i386 image, or its pages would not unprotect
};

struct SiteLookup
{
    SiteSearch result{ SiteSearch::absent };
    std::array<std::size_t, 3> sites{};
};
```

### ★★★★★ 四态的完整语义

| 状态 | 条件 | 安全性 |
|---|---|---|
| **`located`** | 三个签名**各恰好出现一次** | ★ **可以打补丁** |
| **`absent`** | 三个签名**一个都没有** | ★★ **镜像不含该代码** |
| **`ambiguous`** | 出现但**不唯一**,或**只有部分出现** | ★★★ **不可打补丁** |
| **`unusable`** | 不是可映射的 i386 镜像,或页无法解锁 | ★★ **不可打补丁** |

### ★★★★★ 两周错误的完整复盘（逐字）

```
"ABSENT AND AMBIGUOUS ARE NOT THE SAME ANSWER, and the old `findUnique()`
 returned **`std::nullopt` for both**.
 That **single word** is why this file could be **wrong for a fortnight**:
  · "**no sites**" reads as "**not the game, carry on**"
  · "**two sites**" reads as "**the game, but do not touch it**"
 and **only one of those is safe to treat as success**."
        ↓
★★★★★ ⇒ **一个 `nullopt` 混同了两种语义完全不同的情况**
   ⇒ "没有"（正常,非游戏镜像）vs "有多个"（异常,必须拒绝）
   ⇒ **只有前者可以当成功**
```

★★ **⇒ 这与报告 099 的"两种拒绝共用一个消息 cost a cycle"、报告 101 的
"descriptor 形状不参与"是**同一类"语义混同"问题**（第三次出现）。**

### ★★★ 计数提前终止（第 50–79 行）

```cpp
// Counting stops at two: nothing downstream can act on a third.
if (++count > 1) break;
```

★★ **⇒ 数到 2 就停 ⇒ **不需要知道精确数量**（>1 都是 ambiguous）。**

### ★★★ `locate` 的判定逻辑（第 81–94 行）

```cpp
if (call.first == 1 && certificate.first == 1 && authentication.first == 1)
    return SiteLookup{ SiteSearch::located, { call.second, certificate.second, authentication.second } };
if (!call.first && !certificate.first && !authentication.first)
    return SiteLookup{ SiteSearch::absent, {} };
return SiteLookup{ SiteSearch::ambiguous, {} };
```

★★★ **⇒ 三条规则：**
```
① 三者都恰好 1 次 ⇒ **located**
② 三者都 0 次     ⇒ **absent**
③ 其余            ⇒ **ambiguous**
```

★★ **⇒ 注意：**"只有部分出现"（如 call=1, certificate=0）⇒ **ambiguous**（不是 absent）。**
**⇒ 这是**严格的三者齐备要求**。**

---

## 四、★★★★★ **`isKnownClientImage` 的精确用途**

### 4.1 ★★★★★ 完整注释（第 131–135 行，逐字）

```cpp
// The name is used for exactly one judgement, and it is not "may I patch this". It is
// "should I be alarmed that there was nothing here to patch": in a test binary or a tool
// that happens to load this plugin, absent signatures are the expected, healthy answer.
// In an image we ship the game as, absent signatures mean they MOVED WITH THE BUILD, and
// that must be loud -- the failure it causes is a remote player who cannot log in.
bool isKnownClientImage(const std::string &name)
{
    return _stricmp(name.c_str(), "**out.exe**") == 0 ||
        _stricmp(name.c_str(), "**codoMP_client_shipRetail.exe**") == 0;
}
```

### ★★★★★ 两个已知的客户端镜像名

| # | 文件名 | 说明 |
|---|---|---|
| **1** | ★★★ **`out.exe`** | ★ 即 **OLfinal 1649370**（报告 090 的 `Auth3ClientPatches` 也提到 `out.exe`） |
| **2** | **`codoMP_client_shipRetail.exe`** | 交付包 `gameExecutable` 的名字 |

★★★ **⇒ 第 1 条很重要：**`out.exe` 就是那个"OLfinal 1649370"的实际文件名**。**
**⇒ 与报告 087 的 `zm_factory_sh.lua` 里"`out.exe` 的唯一 `compass_map_*` 串"**完全对应** ✓**

### ★★★★★ 名字的**唯一用途**：决定"absent 是否该报警"

```
**不是**"我能不能打补丁"（那由字节签名决定）
        ↓
★★★ 而是"**我该不该为'这里没东西可打'而惊慌**"：
  · **测试二进制或工具**（碰巧加载本插件）⇒ **absent 是预期的健康答案** ⇒ **静默**
  · **我们发布的游戏镜像** ⇒ **absent 意味着签名随 build 移动了** ⇒ **必须大声**
        ↓
★★★ 理由（逐字）："the failure it causes is **a remote player who cannot log in**"
```

★ **⇒ 这是**"用进程名决定日志级别,而不是决定行为"**的精确设计。**

### ★★★ 四态的四条日志串（第 219–254 行）

| 状态 | 日志 |
|---|---|
| **`located`** | `Applied the three Auth3 client patches to <name> at +0x<s0>, +0x<s1>, +0x<s2>.` |
| **`absent` + 已知客户端** | `The three Auth3 client patch signatures are ABSENT from <name>, which IS a known CODOL client image -- they have moved with the build. Re-derive them with Tools/olfinal/check-auth3-patches.py; until then Auth3 cannot serve a client that needs it.` |
| **`absent` + 非客户端** | ★ **静默**（`result = true; return;` 无日志） |
| **`ambiguous`** | `The Auth3 client patch signatures do not resolve to one site each in <name>. **Refusing to patch a guess.**` |
| **`unusable`** | `Could not map <name> as a patchable i386 image for the Auth3 client patches.` |

★★★ **⇒ `ambiguous` 的措辞值得注意："**Refusing to patch a guess.**"**

---

## 五、★★★★★ **`install` 的完整实现**

### 5.1 ★★★ 五步（第 142–196 行）

```
① **取当前模块基址**（`GetModuleHandleW(nullptr)`）
        ↓
② ★ **校验 PE**：`e_magic == IMAGE_DOS_SIGNATURE` + `Signature == IMAGE_NT_SIGNATURE`
   + ★★★ **`Machine == IMAGE_FILE_MACHINE_I386`**
        ↓
③ `locate(image)` ⇒ 若非 `located` ⇒ 返回该状态
        ↓
④ ★★★ **三段 `VirtualProtect`**（`PAGE_EXECUTE_READWRITE`）
   ⇒ **失败则回滚已保护的范围**（`while (protectedCount)` 逆序恢复）
        ↓
⑤ `patch(image, sites)` ⇒ **`FlushInstructionCache`** ⇒ 逆序恢复保护
```

### ★★★★★ 三个受保护的精确范围

```cpp
std::array<ProtectedRange, 3> ranges{
    ProtectedRange{module + sites[0] + **10**, **5**},
    ProtectedRange{module + sites[1],          **1**},
    ProtectedRange{module + sites[2] + **12**, **1**},
};
```

★★★ **⇒ 与 `patch()` 的三个修改位置**完全对应** ✓**

### ★★★ 失败回滚（第 176–183 行）

```cpp
if (!VirtualProtect(range.address, range.size, PAGE_EXECUTE_READWRITE, &range.previous))
{
    while (protectedCount)
    {
        auto &previous = ranges[--protectedCount];
        DWORD ignored{};
        VirtualProtect(previous.address, previous.size, previous.previous, &ignored);
    }
    return SiteSearch::unusable;
}
```

★★★ **⇒ 若第 N 段保护失败 ⇒ **逆序恢复前 N−1 段** ⇒ **不留半保护状态**。**

★ **⇒ 这是**资源获取失败时的干净回滚**（RAII 的手写版）。**

### ★★★ `FlushInstructionCache`（第 188 行）

```cpp
FlushInstructionCache(GetCurrentProcess(), module, size);
```

★★ **⇒ 必须刷新指令缓存,否则 CPU 可能执行**旧的已缓存指令**。**

### ★★★ `std::call_once` 保证只打一次（第 212–214 行）

```cpp
static std::once_flag once;
static bool result{};
std::call_once(once, [] { ... });
return result;
```

★★ **⇒ 幂等：多次调用只执行一次。**

### ★★★ 一个公开的纯函数接口（第 201–208 行）

```cpp
bool patchAuth3ValidationBuffer(const std::span<std::uint8_t> image)
{
    const auto found = locate(image);
    if (found.result != SiteSearch::located) return false;
    patch(image, found.sites);
    return true;
}
```

★★ **⇒ 这个版本**不涉及进程内存**,只对传入的镜像字节打补丁 ⇒ **可离线测试**。**

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **三个签名的长度** | `CertificateCall` **11** / `CertificateBranch` **10** / `AuthenticationBranch` **18** |
| 2 | ★★ `-1` 是通配符 | `if (pattern[index] >= 0 && image[offset+index] != pattern[index])` |
| 3 | ★★★★ **签名 1（`CertificateCall`）** | `68 ?? ?? ?? ??`（**PUSH imm32**）+ `0F 95 C2`（**SETNE DL**）+ `52`（PUSH EDX）+ `50`（PUSH EAX）+ `E8`（**CALL**） |
| 4 | ★★★★★ **签名 2（`CertificateBranch`）** | `74 ??`（**JE rel8**）+ `83 BE 78 02 00 00 00`（**CMP [ESI+0x278], 0**）+ `74`（JE rel8）⇒ ★★ **`0x278` 是精确结构偏移** |
| 5 | ★★★ **签名 3（`AuthenticationBranch`）** | `8B 86 ?? ?? ?? ??`（MOV EAX,[ESI+imm32]）+ `83 ?? ??`（CMP）+ `85 C0`（TEST）+ `0F 84 ?? ?? ?? ??`（**JE rel32**）+ `68`（PUSH） |
| 6 | ★★★★★ **三个修改** | ①`sites[0]+**10**` 写 **5 × `0x90`** ②`sites[1]` 改 **`0x74`→`0x71`** ③`sites[2]+**12**` 改 **`0x84`→`0x81`** |
| 7 | ★★★★★ **`0x74`→`0x71` 的语义** | **JE**（相等则跳）→ **JNO**（不溢出则跳）⇒ **条件几乎总成立** ⇒ **跳过校验** |
| 8 | ★★★ 同理 | **`0x84`（JE rel32）→ `0x81`（JNO rel32）** |
| 9 | ★★★★★ **`0x1430` 固定间距** | 三个站点在 **OLfinal `out.exe`（1649370）** 与 **3.3.3.3** 中**间距相同**（绝对偏移不同） |
| 10 | ★★★★ **旧门控是借来的** | 从 `CodolClientPatches.cpp` 复制；那里**正确**（"every RVA is a 3.3.3.3 address, so **the build IS the precondition**"） |
| 11 | ★★★★★ **借用门控的代价** | 在 `out.exe` 上**返回 TRUE 但没打补丁** ⇒ `ServerFactory::create` 当成功 ⇒ 客户端**真的校验自签证书** ⇒ **`tlsv1 alert unknown ca`** ⇒ **40 秒卡顿 + 挂断** |
| 12 | ★★★ "本机不复现"的原因 | "**this machine's client does not take the Auth3 path**" |
| 13 | ★★★★★ **四态判据** | **`located`**（三者各 1 次,可打）/ **`absent`**（三者都 0）/ **`ambiguous`**（不唯一或部分）/ **`unusable`**（非 i386 或页不可解锁） |
| 14 | ★★★★★ **两周教训** | 旧 `findUnique()` 对 **absent 与 ambiguous 都返回 `std::nullopt`** ⇒ "**no sites**"= "不是游戏,继续" vs "**two sites**"= "是游戏但别碰" ⇒ **只有前者可当成功** |
| 15 | ★★ 计数提前终止 | `if (++count > 1) break;` ⇒ **数到 2 就停** |
| 16 | ★★ `locate` 三规则 | 三者都 1 ⇒ located；三者都 0 ⇒ absent；**其余 ⇒ ambiguous**（含"部分出现"） |
| 17 | ★★★★★ **`isKnownClientImage` 的两个名字** | ★★★ **`out.exe`**（= OLfinal 1649370）/ `codoMP_client_shipRetail.exe` |
| 18 | ★★★★ **名字的唯一用途** | **不是**"能否打补丁",而是"**absent 是否该报警**"（测试二进制静默 / 发布镜像大声） |
| 19 | ★★★ 四条日志 | located 带三个偏移；absent+已知 带 "moved with the build"；absent+非客户端 **静默**；ambiguous **"Refusing to patch a guess."** |
| 20 | ★★★ `install` 的 PE 校验 | `IMAGE_FILE_MACHINE_I386` **强制 32 位** |
| 21 | ★★★ 三个保护范围 | `sites[0]+10`（**5**）/ `sites[1]`（**1**）/ `sites[2]+12`（**1**） |
| 22 | ★★ 失败回滚 | 第 N 段失败 ⇒ **逆序恢复前 N−1 段** |
| 23 | ★★ `FlushInstructionCache` | 必须刷新（否则执行旧缓存指令） |
| 24 | ★★ `std::call_once` | 幂等 |
| 25 | ★★ `patchAuth3ValidationBuffer` | 纯函数版（对传入镜像打补丁,**可离线测试**） |

---

## 七、结论

### 1. ★★★★★ **三个补丁的字节签名与修改全部还原**

```
补丁 2/3 都是 **JE → JNO**（`0x74→0x71` / `0x84→0x81`）⇒ 条件几乎总成立 ⇒ 跳过证书校验
补丁 1 是 **NOP 5 字节**
        ↓
★ 签名 2 里 **`CMP [ESI+0x278], 0`** 给出一个精确结构偏移
```

### 2. ★★★★★ **`0x1430` 是跨 build 不变的固定间距**

★ **⇒ 这是"字节签名定位"能跨 3.3.3.3 与 OLfinal 通用的关键。**

### 3. ★★★★★ **四态判据源于一个"两周错误"**

```
旧 `findUnique()` 对 **absent** 与 **ambiguous** 都返回 `nullopt`
        ↓
★★★ 但两者语义完全相反：
  absent    ⇒ "不是游戏,继续"（**可当成功**）
  ambiguous ⇒ "是游戏,但别碰"（**必须拒绝**）
        ↓
★★★★★ ⇒ **一个 `nullopt` 混同了两种语义 ⇒ 错了两个星期**
```

### 4. ★★★★★ **借用进程名门控导致远端玩家无法登录**

```
在 `out.exe` 上**返回 TRUE 但没打补丁** ⇒ 被当成功
        ↓
客户端真的校验自签证书 ⇒ **`tlsv1 alert unknown ca`** ⇒ 40 秒卡顿 + 挂断
        ↓
★★★ **本机不复现**（本机客户端不走 Auth3 路径）
```

### 5. ★★★★ **`out.exe` 就是 OLfinal 1649370 的实际文件名**（与报告 087 呼应）

### 6. ★★★ **进程名的唯一用途是决定日志级别,不是决定行为**

### 7. ★★★ **`install` 有干净的失败回滚 + `FlushInstructionCache` + `call_once` 幂等**

---

## 八、下一步

- `Auth3Protocol.hpp`（29 行）+ `Auth3TlsTransport.cpp`（311 行）+ `.hpp`（31 行）
- `AuthSession` / `ByteBuffer` / `Crypto` / `IdentityConfig` / `CodolClientPatches`（882 行）
- 然后 12 个 Service 实现
