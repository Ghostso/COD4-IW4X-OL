# 245 · `volatile` 是载荷、`stage` 与 `faultStage` 的两条记录、两次遍历的顺序

## 一、范围

本报告学习 `EngineBindings.cpp` 11285–11695 行（`ensureWeaponRegistryInitialized` 全部）。

## 二、**`volatile` 是载荷**（本组最重要的一段）

```cpp
// VOLATILE IS LOAD-BEARING. MSVC gives a non-volatile local that is
// modified inside __try an INDETERMINATE value once an exception
// unwinds, so every counter here read as garbage on exactly the path
// worth measuring: one run reported stage=5 with walked=1 and
// mismatches=0 while also naming a mismatch at index 1, which cannot
// all be true at once. The char buffers were always fine - they are
// memory writes - and it was the register-cached scalars that lied.
volatile bool initialized{};
volatile std::uint32_t failedIndex{};
...
```

### 2.1 那次不可能的日志

```text
stage=5  walked=1  mismatches=0  但同时又命名了 index 1 的一处 mismatch
```

**"这不可能同时为真"** —— 而这正是**信号**。

### 2.2 机理

```text
MSVC 对在 __try 内被修改的【非 volatile 局部变量】在异常展开后给出【不确定值】
→ 因为这些标量被缓存在寄存器里，而展开路径不恢复寄存器
```

**"字符缓冲区一直是好的 —— 它们是内存写 —— 而撒谎的是寄存器缓存的标量。"**

### 2.3 那句反面证据

```cpp
// Not volatile, and it does not need to be: its address is taken, so
// MSVC keeps it in memory and the __try rule about register-cached
// locals does not reach it. Same reason the char buffers always read
// back correctly while every scalar counter here did not.
NativeFault fault{};
```

**"不 volatile，也不需要：它的地址被取用，所以 MSVC 把它留在内存里"**

**这是一条可复用的判据**：**取地址 ⇒ 强制落内存 ⇒ 免于 C2712 的值不确定问题。**

### 2.4 与 §242 的 C2712 连起来

```text
§242  __try 必须住在没有析构函数的函数里（C2712）
§245  __try 内修改的标量必须是 volatile（否则展开后值不确定）
```

**两条 MSVC 约束，一个方向相反**（一个是"不能有对象"，一个是"必须有 volatile"）。

## 三、**`stage` 与 `faultStage` 的两条记录**

```cpp
// `stage` records PROGRESS and is overwritten as the function walks on
// past a break; `faultStage` records where a fault actually happened
// and is written once. Reading progress as the fault site said stage=5
// for three runs while the real fault was the resolver at stage 22.
volatile std::uint32_t stage{1};
volatile std::uint32_t faultStage{};
```

### 3.1 两个变量的职责

```text
stage       进度（会被覆盖）
faultStage  故障点（只写一次）
```

### 3.2 那次误读

**"把进度读作故障点，连续三次运行都说 `stage=5`，而真正的故障是 22 号阶段的解析器。"**

### 3.3 两张表的阶段号

```text
注释给出的表：
  1 reset  2 configstring walk  3 default resolve  4 initialize  5 verify
实际代码用的：
  1 reset
  2 configstring walk
  3 default resolve
  4 initialize
  5 verify
  20 + pass    （解析器 fault，pass 0/1 ⇒ 20/21）
  51           （lookup verify fault）
  90 + stage   （外层 __except 兜底）
```

### 3.4 **两套阶段号并不同域**

```text
1..5        正常路径的阶段
20,21       解析器 fault（与 2 重叠！）
51          verify lookup fault
90+stage    外层兜底
```

**`20` 与 `2` 是不同的数**，所以不冲突。**但注释里的"真实的故障是 22 号阶段的解析器"** —— 而代码里 `20 + pass` 只产生 20 与 21。

**所以那次观测到 22 是另一个版本/另一处写入** —— 这是注释与代码的**一处时间差**。

## 四、`registerGameplayDvars` 的必要性（那段 dvar 因果链）

```cpp
// THE GAMEPLAY DVARS FIRST, because registering a weapon reads one.
// sub_432130 loads mp/gametypeWeaponCustomTable.csv and asks, per weapon,
// whether the current gametype is in that row's '|'-separated list - and
// sub_432000 does it with `mov ecx, [edx+0Ch]` on the g_gametype dvar,
// unguarded. In a dedicated process that dvar has never been registered,
// because the only thing that registers it is CG_Init, so edx was 0 and the
// read of 0xC was the whole fault.
```

### 4.1 五层

```text
1. sub_432130 载入 mp/gametypeWeaponCustomTable.csv
2. 逐武器问：当前 gametype 是否在该行的 '|' 分隔列表里
3. sub_432000 用 `mov ecx, [edx+0Ch]` 读 g_gametype 的 dvar —— 【无保护】
4. 专用服里 g_gametype 从未注册（唯一注册它的是 CG_Init）
5. ⇒ edx = 0 ⇒ 读 0xC 就是整个 fault
```

### 4.2 那句"这不是 workaround"

```cpp
// Nothing here is a workaround: it calls the game's own registration
// blocks, and it does so ONCE, gated on the dvar the fault named.
```

**"调用游戏自己的注册块"** —— 而不是手写 dvar。

### 4.3 修复的判据是"dvar 指针是否为空"

```cpp
if (!before) registered = registerGameplayDvars();
```

**"未注册" = 指针为 null** —— 而注册后 `after` 应该非空。

**而日志同时记录 `before` 与 `after` 与 `value`** —— 所以一次日志就能判断注册是否生效。

## 五、`g_gametype` dvar 的 `+0xC` 是**值指针**

```cpp
const auto *const value = after && readableSpan((const char*)after + 0xC, 4)
    ? *(const char *const *)((const char*)after + 0xC)
    : nullptr;
```

**不是 `+0xC` 的 uint32 而是 `+0xC` 处的指针再解引用** —— 所以 `dvar_t` 的 `+0xC` 是一个 **`char*`**。

**这与记忆里的"dvar 对象 +0xC 是值"一致**，但**这里是二次解引用**（指针指向字符串）。

**注意 `readableSpan(..., 4)` 后再解引用** —— 但**没有对 `value` 本身做 `readableSpan`，只在 `snprintf` 的 `readableSpan(value, 1)` 处才检查** ✓

## 六、**reset 的条件性**

```cpp
if (registryWord(WeaponRegistryCountRva) == 0)
{
    *registryMode = 2;
    weaponRegistryReset_();
}
initialized = true;
```

### 6.1 两个修正（注释明说）

```text
Three things this used to get wrong, all of them measurable:
the reset was UNCONDITIONAL, the mode word was never set, and
initialize() was called with no argument at all.
```

```text
① reset 原来是无条件的
② 模式字（=2）从来没设过
③ initialize() 原来不传参数
```

### 6.2 而"把 count 与 memo 清零不是我们的事"

```cpp
// THE COUNT AND THE MEMO ARE NOT OURS TO ZERO. That was written on
// the theory that a stale count would make WeaponLookup walk the
// table the reset had just emptied. The game never touches them
// here, and it does not have to: it only resets when the count is
// already 0, so the reset and the count agree by construction.
```

**"游戏在这里从不碰它们，而且不需要：它只在 count 已经是 0 时才 reset，所以 reset 与 count 由构造一致。"**

### 6.3 那句实测反证

```text
Live logs then measured `before reset count=0` and the zeroing
changed nothing, which is the same answer from the other side.
```

**"实测 `before reset count=0`，而清零什么都没改变 —— 从另一侧得到同一个答案。"**

**这是"删掉一个多余操作并用实测证明它多余"** —— 一个干净的负结果。

### 6.4 `initialized = true` 在 reset 之后立刻置

**注意位置**：`initialized = true;` 在 reset 之后、walk 之前。

**所以 `initialized` 是一个"走出 reset 阶段"的标志，而不是"全部成功"。**

**而 walk 循环里 `if (!initialized) break;`** —— 这个判据用的是同一个变量。

**这是一个变量两种用途** —— 而在 §2 里 `initialized` 还是最终返回值的一部分：

```cpp
return initialized && weaponRegistryInitialized() ? Ready : InitializationFailed;
```

**三种用途**：阶段标志、循环中断标志、最终成败。

## 七、**两次遍历的顺序**（本组核心）

```cpp
for (pass = 0; pass < 2; ++pass)
{
    const bool skipModular = pass == 0;
    for (index = 1; index < WeaponConfigStringCount; ++index)
    {
        if (skipModular ? *name == '*' : *name != '*') continue;
        ...
    }
    if (pass == 0) { /* default weapon / initialize(1) / knife stats */ }
}
```

### 7.1 pass 0 = **普通武器**（跳过 `*`），pass 1 = **模块化武器**（只要 `*`）

**注意注释说 "Pass 1 first, exactly as CL_ParseGamestate orders them"** —— 而代码 `pass == 0` 先跑。

**这看起来矛盾** —— 除非"Pass 1"是 `CL_ParseGamestate` 自己的编号（它把普通武器叫 pass 1）。

**而从 `skipModular = pass == 0` 与 `*name == '*' → continue` 可知：pass 0 处理非 `*`。**

**所以"Pass 1 first" = "普通武器先"，而本代码的 pass 0 = 普通武器** ✓ 两个编号系统。

### 7.2 那个反汇编前缀

```asm
lea esi, [edi+1748h]      ; base 5960 + index        (1748h = 5960)
call CL_GetConfigString   ; index in ESI
test al, al / jz          ; empty -> skip
cmp [ebp+arg_0], 0 / jz   ; pass 0 does NOT skip modular
cmp al, '*'    / jz       ; pass 1 skips modular names
push 0 / push esi / call WeaponResolver
cmp eax, edi              ; resolved index must BE the index
```

### 7.3 **六个断言**

```text
1. 0x1748 = 5960 = WeaponConfigStringBase
2. CL_GetConfigString 的 index 在 ESI
3. 空串跳过
4. arg_0 == 0 ⇒ 【不】跳过模块化
5. arg_0 != 0 ⇒ 跳过模块化（即跳过 '*'）
6. 解析出的 index 必须【等于】传入的 index
```

**第 6 项是最强的** —— 它要求解析是**恒等**的，而不只是"非零"。

### 7.4 `static_assert` 的两条

```cpp
static_assert(WeaponConfigStringBase == WeaponWalkConfigStringBase,
    "the walk base has to be the one sub_59B560 adds to the index");
static_assert(WeaponConfigStringCount == WeaponWalkEntryCount,
    "the walk bound has to be CL_ParseGamestate's `cmp edi, 6A4h`");
```

**`0x6A4 = 1700` = `WeaponConfigStringCount`** ✓

### 7.5 为什么不直接调 `sub_59B560`

```cpp
// THE WALK IS sub_59B560, ONE INDEX AT A TIME. Its whole prefix is
// reproduced here rather than called, because on a mismatch it ends
// in Com_Error("181 %s %d %d") and Com_Error LONGJMPS - through
// this __try, and through a jmp_buf this thread may never have set.
```

**"在 mismatch 时它以 `Com_Error("181 %s %d %d")` 结束，而 `Com_Error` **LONGJMP** —— 穿过这个 `__try`，穿过一个这个线程可能从未设置过的 `jmp_buf`。"**

**这是一个非常好的理由**：`__try` 捕不到 `longjmp`（`longjmp` 不触发 SEH）。

**所以把前缀复制出来逐个 index 做，就能用 SEH 安全地捕到 fault。**

### 7.6 首个名字记录在**解析之前**

```cpp
if (named < 6) std::snprintf(firstNames[named], ..., "%u:%s", index, name);
++named;
```

**"记录在问它们解析之前"** —— 因为：

```text
A stage-2 fault says the resolver died on a name; only the name itself says
whether the accessor handed it a weapon or rubbish, and that distinction was
the whole of the __fastcall/ESI bug.
```

**"访问器给它的是一把武器还是垃圾 —— 这个区分就是整个 `__fastcall`/ESI bug 的全部。"**

**这与 §242 里 `__usercall`（EAX + EDI）是同一类问题** —— 调用约定错 ⇒ 参数是垃圾。

## 八、**mismatch 记录 6 个而不是停在第 1 个**

```cpp
if (mismatches < 6) { ... firstMismatch[mismatches] = "%u->%u:%s" ... }
++mismatches;
...
if (mismatches >= 6) break;
```

### 8.1 理由

```text
Record the first handful rather than stopping at one: whether the whole
table is shifted or only index 1 disagrees is the difference between an
off-by-one and an expectation that was never true for the default weapon,
and one sample cannot tell them apart.
```

**"整张表位移 vs 只有 index 1 不一致 —— 这是『差一』与『对默认武器从未成立过的期望』之间的区别，一个样本分不开。"**

### 8.2 两个判据

```text
每个 index 都 mismatch 且差恒为 k  ⇒ 【整表位移 k】
只有少数 mismatch                ⇒ 【个别期望错误】
```

**这与 §240 的"同一 id 是否跨 class"、§241 的"两 class fixture"、§243 的"686 对照"是同一族的第 N 次。**

### 8.3 而 `failedIndex` 只记第一个

```cpp
if (!failedIndex) { failedIndex = index; failedResolvedIndex = resolvedIndex; ... }
```

**`failedIndex` 记第一个**（用于最终报告），**`firstMismatch[6]` 记前六个**（用于模式分析）。

## 九、`stage` 在两次遍历之间的中间段

```cpp
if (pass == 0)
{
    stage = 3;
    defaultWeapon = weaponResolver_("defaultweapon_mp", nullptr);
    stage = 4;
    static_cast<void>(weaponRegistryInitialize_(1));
    if (weaponKnifeStatsLoad_) weaponKnifeStatsLoad_();
    stage = 5;
}
```

### 9.1 四步

```text
3  resolve("defaultweapon_mp", nullptr)
4  initialize(1)                    ← 参数 1 是必需的
   knife stats load（可选）
5  verify
```

### 9.2 那句"参数不是可选的"

```cpp
// `push 1; call sub_42FE80` at 0x454B41 and 0x4FE1AC. The parameter is
// not optional and was never being passed.
```

**两个调用点都用 `push 1`** —— 所以 `initialize(1)` 是必须的。

### 9.3 刀块被跳过

```cpp
// The knife block at 0x454A98 is skipped - it is guarded on an obfuscated
// mode word (`[eax+0x180C1C] == 2` read through dword_1C1D188 ^ 0xFBB2C97A)
// and it only populates a deferred-reload list.
```

**两个理由**：

```text
1. 它被一个【混淆过的模式字】守护（`dword_1C1D188 ^ 0xFBB2C97A`）
2. 它只填充一个【延迟重载列表】
```

**所以跳过它是安全的** —— 而备注承认了它。

**`0xFBB2C97A` 与记忆里的 `cg = table[selector] ^ 0xFBB2C97A` 是同一个 XOR 常量** ✓

## 十、`pass 0` 的已知缺口

```cpp
// Pass 0's modular tail (sub_431F30, sub_80C220, sub_660C90 and the
// deferred list at 0x82CA590) is not ported, so pass 0 here stops
// after the resolve. That is a KNOWN GAP, not an equivalence claim:
// it registers the '*' names but does not queue their reload.
```

**"那是一个【已知缺口】，不是等价性声明：它注册 `*` 名字但不排队它们的重载。"**

**四个未移植的东西**：

```text
sub_431F30
sub_80C220
sub_660C90
0x82CA590 处的延迟列表
```

**"KNOWN GAP, not an equivalence claim"** —— 这是"承认不完整"的正确写法。

## 十一、最终 verify 的 51 阶段的两次尝试

```cpp
std::uint32_t verifyLookup{};
if (!tryWeaponLookup(weaponLookup_, "defaultweapon_mp", verifyLookup, fault))
{
    exceptionCode = fault.code;
    faultStage = 51;
    initialized = false;
}
else
{
    initialized = initialized && defaultWeapon != 0 && verifyLookup == defaultWeapon;
}
```

### 11.1 两项校验外加上一项

```text
1. lookup 不 fault
2. defaultWeapon != 0（之前 resolve 成功）
3. verifyLookup == defaultWeapon   ← 【反查得到同一个号】
```

**第 3 项与 §236 里 `weaponLookup_(nativeName) != weaponAssetIndex` 是同一手法** —— **resolver 与 lookup 两个不同函数的一致性检查**。

### 11.2 而 `initialized` 被**再次**赋值

```cpp
initialized = initialized && defaultWeapon != 0 && verifyLookup == defaultWeapon;
```

**所以最终的 `initialized` 是"前面都没失败 且 这三项"。**

## 十二、失败时的**六段日志**

```text
details    stage/fault/index/resolved/name/default/count/walked/named/faults/exception
seen       weapon registry first names  [6 个]
globals    count= next=
preReset   before reset count= cache= counter= initialized=
beforeAfter after reset count= cache= counter= attachModels= map0=
where      fault at rva= op= target= code=
reported   com_error depth= level= text=
mism       mismatches= [6 个]
```

**八段**（我把它们数一遍）。

### 12.1 那句"没有 `std::string`，因为 C2712"

```cpp
// No std::string in this function: it carries a __try, and MSVC
// refuses object unwinding alongside it (C2712).
```

**这是 §242 同一条约束的第二次出现** —— 而这次是**主动避免**（用 `char[]` + `snprintf`）。

### 12.2 `snprintf` 的边界处理

```cpp
const auto added = std::snprintf(seen + written, sizeof(seen) - written, " [%s]", entry);
if (added > 0) written += added;
```

**注意 `added > 0` 才累加** —— 而 `snprintf` 返回的是"**本应写入**的长度"（可能大于可用空间）。

**所以 `written` 可能超过 `sizeof(seen)`** —— 而循环开头的 `(size_t)written >= sizeof(seen)` 检查会拦住下一次写入 ✓

**这是一个正确的、但需要两步才看懂的写法。**

### 12.3 那个"rva 直接贴进 IDA"的说明

```text
// WHERE it faulted, as an RVA that pastes straight into IDA, and WHAT it
// touched. 0x02F060 reading address 0 is a null WeaponDef string; anything
// inside 0x0F82E0 is Com_Error, which means the engine RAISED this rather
// than tripping over it.
```

**两个可判读的值**：

```text
rva = 0x02F060 且 target = 0   ⇒ WeaponDef 的名字指针是 null
rva 在 0x0F82E0 内              ⇒ 【引擎主动报错】而不是意外触到
```

**`0x0F82E0` 是 `Com_Error` 的地址** —— 而后面读的 `ComErrorDepthRva`/`ComErrorLevelRva`/`ComErrorTextRva` 就是它的状态。

### 12.4 那句"引擎报了真错误"

```text
// Com_Error's own state. sub_4F82E0 bumps the depth, keeps the
// level, formats the message, and THEN longjmps - so a non-zero
// depth here says the engine reported a real error and the text is
// its own words, not our guess about them.
```

**"非零的 depth 说明引擎报告了一个真错误，而文本是它自己的话，不是我们关于它的话的猜测。"**

### 12.5 `%.240s` 与 `readableSpan(errorText, 241)`

```cpp
readableSpan(errorText, 241) ? errorText : "<unreadable>"
```

**检查 241 字节而用 `%.240s`** —— 因为 `%.Ns` 会读最多 N 个字符**再加一个 NUL 终止符**，所以需要 N+1 字节可读 ✓

## 十三、关键结论

1. **`volatile` 是载荷** —— `__try` 内修改的非 volatile 标量在展开后值不确定。
2. **取地址 ⇒ 强制落内存 ⇒ 免于此问题**（`NativeFault fault{}`）。
3. **`stage` 记进度、`faultStage` 记故障点** —— 分开是因为把进度当故障点误读了三次。
4. **注释里的阶段表与代码的阶段号不同域**（`20+pass` 只产生 20/21，而注释提到 22）。
5. **`g_gametype` 未注册 ⇒ `sub_432000` 的 `[edx+0Ch]` 是整个 fault** —— 修法是调用游戏自己的注册块。
6. **reset 必须条件化**（`count == 0`），且模式字必须置 2，`initialize` 必须传 1。
7. **"把 count 清零"是多余的** —— 实测证明。
8. **两次遍历：普通武器先，模块化后**，中间插入 default/initialize/knife。
9. **不能直接调 `sub_59B560`** —— 它的 `Com_Error` 会 `longjmp` 穿过 `__try`。
10. **解析出的 index 必须【等于】传入的 index** —— 比"非零"强。
11. **记 6 个 mismatch 而不是 1 个** —— 整表位移 vs 个别错误需要模式。
12. **final verify 的双向一致性**（lookup 与 resolve 同一个号）。
13. **"KNOWN GAP, not an equivalence claim"** —— 承认未移植的四项。

## 十四、未闭合点

- `stage` 注释表（1..5）与实际写入（20/21/51/90+）不同域，注释里提到的 22 在代码中不产生。
- pass 0 的模块化尾部（`sub_431F30`/`sub_80C220`/`sub_660C90`/`0x82CA590`）未移植。
- `EngineBindings.cpp` 11695 行之后未读取（本批已续读到 11850）。
