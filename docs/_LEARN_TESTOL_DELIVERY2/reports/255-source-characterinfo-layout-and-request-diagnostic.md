# 255 · `ProfileManagerRva` **不是指针**、`chunkMask` 必须相等、`characterInfo` 的 1104 步长与七个偏移

## 一、范围

本报告学习 `EngineBindings.cpp` 15045–15260 行。

## 二、`profileSlotProbeEnabled`：**三个事故与一个"不能用"的判定**

```cpp
// OFF BY DEFAULT, and this is a calibration decision rather than caution.
//
// Reading the roster is a bounded memory read behind readableSpan and is
// demonstrably safe -- it ran on a live client and produced the 686 measurement.
// CALLING sub_50FF30 is a native call on the bridge thread, and its safety is NOT
// established: it walks the public profile, formats two strings and reads through
// a manager the game thread also owns.
//
// Six ClientException reports exist on this build with the same innermost frame,
// sub_779510 +0x230, and THREE OF THEM PREDATE THIS BATCH. Today's three share a
// different caller frame from the older three, which is suggestive and is not a
// demonstration -- the probe ran twice with no crash, and did not run at all in
// two runs that crashed. Nothing isolates a cause either way.
```

### 2.1 三次崩溃的**六份报告**

```text
6 份 ClientException，最内层帧都是 sub_779510 +0x230
其中 3 份【先于本批次】
今天的 3 份与更早的 3 份【调用者帧不同】
```

### 2.2 那个**诚实的结论**

```text
"which is suggestive and is not a demonstration"
"... the probe ran twice with no crash, and did not run at all in two runs that crashed."
"Nothing isolates a cause either way."
```

### 2.3 四个观测的**四种组合**

```text
探针跑 2 次 ⇒ 没崩
崩溃的 2 次 ⇒ 探针没跑
```

**⇒ 两个方向的证据都不成立。**

**"暗示而不是证明"** —— 这是本文件里**最克制**的一段表述。

### 2.4 结论

```cpp
// So the unvalidated call stays off the path everyone else runs, and turns on for
// whoever is deliberately measuring: OLMOD_PROBE_PROFILE_SLOTS=1.
```

**"未验证的调用留在其他人跑的那条路之外，只对有意测量的人打开。"**

## 三、`currentCharacterIndex` 的**四项前置**

```cpp
if (!currentCharacterGet_ || !publicProfileReady() || !profileSlotProbeEnabled())
    return nullopt;
const auto characterIndex = currentCharacterGet_();
if (characterIndex < 0 || characterIndex >= 12) { ...report...; return nullopt; }
```

### 3.1 那句因果

```cpp
// publicProfileReady() FIRST. sub_6B87C0 resolves "currentCharacterIndex"
// through the profile on its first call, so it has the same precondition as
// sub_50FF30 -- see the CODDIFF on CharacterSlotGetRva.
```

**"`sub_6B87C0` 在第一次调用时通过 profile 解析 `currentCharacterIndex`，所以它与 `sub_50FF30` 有相同的前置条件。"**

**⇒ 所以 `publicProfileReady()` 必须在调用前检查。**

## 四、**`12 IS OUR BOUND, NOT THE ENGINE'S`**（本组最重要的一段）

```cpp
// 12 IS OUR BOUND, NOT THE ENGINE'S. out.exe's own consumers -- sub_6B87C0 and
// sub_7C5BA0, which is the function that actually indexes the table -- do only
// `if (index < 0) index = 0` and then scale by 156 with no upper check. So this
// is stricter than the code it is modelling, and may simply be wrong here.
// Widening it on that reasoning alone would be inventing a bound; report the
// value and let a measurement decide.
```

### 4.1 三个事实

```text
sub_6B87C0 与 sub_7C5BA0 只做 `if (index < 0) index = 0`
然后【乘 156】而【没有上界检查】
⇒ 我们的 12 比建模的代码更严格，可能在这里就是错的
```

### 4.2 **`156` 这个乘数**

**`156` 是角色记录的元素尺寸** —— 而 §238 的 `characterStride = 14`（位移）与 §239 的 `characterSlots = 610` 是**序号**。

**`156` 是**字节**尺寸** —— 所以一个角色记录是 156 字节。

**§252 里"`sub_7C5BA0`，是真正索引这个表的函数"** ✓ 同一函数。

### 4.3 那句"仅凭这个理由就放宽就是在发明一个界"

**"仅凭这个理由就放宽就是在发明一个界；报告值让测量来决定。"**

**这是一个"已知过严但拒绝凭推理放宽"的立场** —— 与本文件里"不猜偏移"（§252 的转储全部候选）同族。

### 4.4 而它**拒绝每一次 loadout 捕获**

```cpp
// SAY WHAT THE VALUE WAS. "currentCharacterIndex unavailable" is the answer this
// gave for a number that is sitting right there, and it refused every loadout
// capture on this build.
```

**"『currentCharacterIndex unavailable』是它给一个就在那里的数字的答案，而它在这个 build 上拒绝了每一次 loadout 捕获。"**

**⇒ 所以这个过严的界**确实**在生效**并**造成了实际功能损失**。

### 4.5 那次修复只加了日志

```cpp
if (lastCharacterIndexRefusal_ != characterIndex)
{
    lastCharacterIndexRefusal_ = characterIndex;
    write("currentCharacterIndex out of our 0..11 range: N (out.exe itself only clamps negatives)");
}
```

**日志明确写出"out.exe 本身只夹负数"** —— 所以读日志的人立刻知道这是我们的界。

**而 `lastCharacterIndexRefusal_ = -2` 在成功时复位** —— 一个"上次拒绝值"的缓存（-2 是不可能的值，因为合法值是 0..11 或负数）。

## 五、`publicProfileReady` 的**四项**（本组第二重要）

### 5.1 **`ProfileManagerRva` 是管理器本身，不是指向它的指针**

```cpp
// ProfileManagerRva IS THE MANAGER, not a pointer to it. CodolMatchFlow.py's
// readPublicProfileState does `profileManager.add(PUBLIC_PROFILE_OFFSET)` on
// `module.base.add(PROFILE_MANAGER_RVA)` -- no dereference anywhere, and the
// arithmetic checks out against what it printed live this session:
// 0x400000 + 0xE14BC48 + 0x10 = 0xE54BC58, which is the address it reported.
//
// The first version of this dereferenced twice and returned false forever, which
// read as "the profile is never ready" on a run where it demonstrably was.
const auto *profile = module_ + ProfileManagerRva + PublicProfileOffset;
```

### 5.2 三个地址

```text
module_                0x400000
ProfileManagerRva      0xE14BC48
PublicProfileOffset    0x10
⇒ 0xE54BC58
```

**"与它本次会话实时打印的地址一致"** —— 一次实测核对。

### 5.3 那次错误

**"第一版两次解引用并永远返回 false，在一个它显然已经就绪的运行里读成了『profile 从未就绪』。"**

**⇒ 这就是 §225/§234/§235/§239/§243 那条"沉默读起来像健康"的**反面**：这次是"沉默读起来像故障"，而实际是探针错了。**

**两个方向都有** —— 这是本项目的第 N 次。

### 5.4 **`chunkMask` 必须**相等**而不是子集**

```cpp
// EQUALITY, not a mask test. `chunkMask === PROFILE_REQUIRED_CHUNK_MASK` is what
// the tool checks, so extra bits set is NOT ready, and a subset test would call
// a half-loaded profile ready.
if (*(const uint32*)(profile + ProfileChunkMaskOffset) != ProfileRequiredChunkMask)
    return false;
```

### 5.5 两个方向的错误

```text
子集测试（`(mask & required) == required`）  ⇒ 半加载的 profile 被当成就绪
相等（`mask == required`）                    ⇒ 额外的位让"就绪"被当成"未就绪"
```

**代码选了**相等** —— 与工具一致。**

**而"额外的位 ⇒ 未就绪"是一个保守的错误方向**（宁可等）。

### 5.6 四项判据

```text
① profile 可读（到 ProfileParsedOffset + 1）
② profile[ProfileParsedOffset] 非零
③ chunkMask == required
④ operation == 0
```

## 六、`reportClientCharacterInfo`：**1104 步长与七个偏移**（本组第三重要）

### 6.1 那段反汇编

```cpp
// sub_53DF40 picks the block with
//     (char *)dword_827F730 + 1104 * entityState.clientNum + 717648
// for ET_PLAYER, and passes it as BG_UpdatePlayerDObj's third argument.
```

```text
dword_827F730                基址指针（全局）
+ 1104 * clientNum          步长 1104
+ 717648                    数组偏移
```

### 6.2 两个常量

```cpp
constexpr std::size_t ClientCharacterInfoBasePointerRva = 0x7E7F730;   // ← VA 0x827F730 - 0x400000
constexpr std::size_t ClientCharacterInfoArrayOffset   = 717648;
constexpr std::size_t ClientCharacterInfoStride        = 1104;
constexpr std::uint32_t ReportedClients                = 4;
```

**`0x7E7F730 + 0x400000 = 0x827F730`** ✓

**而 §235 里 `0x827F730` 是"characterInfo"的全局基址** ✓ —— 完全一致。

### 6.3 七个偏移（从代码可推出）

```text
+0       infoValid            (uint32)
+0x18    base model name       (char*)
+0x20    十个附件名（数组）
+660     rebuild flag          (uint32)
+900     DObj handle           (uint32)
+1024    resolver request      (16 × uint32)
```

**而 §255 开头说 "infoValid at +0x00, the base model name at +0x18, ten attachment names at +0x20"** ✓

### 6.4 **`CharacterInfoAttachmentNamesOffset` 必然是 `0x20`**

```cpp
if (!readableSpan(info, CharacterInfoAttachmentNamesOffset)) { ...UNREADABLE... }
```

**这个 `readableSpan(info, 0x20)` 是"结构性守卫"** —— 只覆盖前 32 字节。

**而 §255 后半段明确批评了这一点**：

```cpp
// the loop's only structural guard covers the first 32
// bytes (CharacterInfoAttachmentNamesOffset). A read 164 bytes in, across
// four slots including ones no client occupies, is a check-then-use race
```

**⇒ `CharacterInfoAttachmentNamesOffset = 0x20 = 32`** ✓

### 6.5 而 §184 里是 `0xAF350 + 18*0x450`

**那是**服务端**的 characterInfo 数组（18 槽、0x450 = 1104 步长）。**

**`0x450 = 1104`** ✓ —— **同一个步长，两个数组**：

```text
服务端   dword_827F730 + 18*0x450 + 0xAF350     （18 槽）
客户端   dword_827F730 + 1104*clientNum + 717648  （? 槽）
```

**两个不同的基址（`0xAF350` vs `717648 = 0xAF350`?）**

**`717648 = 0xAFA50`** —— 不是 `0xAF350`。

**差 `0x700`** —— 所以是**两个不同的数组**在同一个全局基址上。

**这是一处重要的区分** —— 而两者步长相同（1104）。

### 6.6 `ReportedClients = 4` 与"19 + 18 块"

**§255 后面说**：

```cpp
// cgame hands every one of these slots a PERMANENT 64-byte buffer out of one pool at
// init (0x0044B310 and 0x004555D0 walk 19 + 18 blocks of stride 1104 and
// deal out 25 buffers each; the pool is memset 0xE740 = 37 * 1600)
```

```text
19 + 18 = 37 块，步长 1104
每块 25 个缓冲区
池 memset 0xE740 = 37 * 1600
```

**`37 * 1600 = 59200`** —— 而 `0xE740 = 59200` ✓

**所以池是 37 块 × 1600 字节** —— 而每块的 characterInfo 是 1104 字节，剩下的 496 是别的东西。

**这解释了 `37`** —— 与记忆里"18 槽"相关但不同（19 + 18 = 37）。

## 七、**`EMPTY` 与 `UNREADABLE` 的分离**（本组第四重要）

```cpp
// A NULL MODEL POINTER AND AN EMPTY STRING ARE DIFFERENT ANSWERS and the
// difference is the whole point: one says the client never resolved a
// character, the other says it resolved one and got nothing.
// AN EMPTY NAME MUST READ AS EMPTY. readCString returns nullopt for a
// zero-length string as well as for an unreadable one, and this probe
// printed both as UNREADABLE -- so section 165c wrote the empty-name case
// off as instrument noise while it was sitting in the log as the invisible
// player itself, `valid=1 model=UNREADABLE`, run after run. Check the first
// byte here rather than change readCString, whose other callers rely on
// "non-empty or nothing".
const auto model = !name
    ? std::string{ "NULL" }
    : (!readableSpan(name, 1) ? std::string{ "UNREADABLE" }
        : (!*name ? std::string{ "EMPTY" }
            : readCString(name, 128).value_or(std::string{ "UNREADABLE" })));
```

### 7.1 **四态**

```text
NULL         指针为空
UNREADABLE   指针不可读
EMPTY        字符串为空
<name>       正常
```

### 7.2 **那个被当成"仪器噪声"的真实信号**

```text
`valid=1 model=UNREADABLE` 连续多次运行
⇒ 而它实际是"玩家不可见"的那个 case
⇒ §165c 把它写成仪器噪声
```

**这是"沉默/噪声读起来像健康"的**第六次**（§225/§234/§235/§239/§243/§255）。**

**而这次的形式是**"把有效信号分类成噪声"** —— 一个新的变体。

### 7.3 而修法**不改 `readCString`**

**"检查这里的首字节而不是改 `readCString`，它的其他调用者依赖『非空或什么都没有』。"**

**这是一个正确的"不改共享工具"决策** —— 与 §244 里"在不能造出错枪的方向上判断"同族。

### 7.4 `NULL` vs `EMPTY` 的语义

```text
NULL         客户端从未解析出一个角色
EMPTY        它解析了但什么也没得到
```

**两个完全不同的缺陷。**

## 八、"指针本身也要打印"的那段论证

```cpp
// AND THE POINTER ITSELF, because UNREADABLE has been read as instrument
// noise for a whole session and section 166 says it cannot be. cgame hands
// every one of these slots a PERMANENT 64-byte buffer out of one pool at
// init ... Nothing writes the POINTER afterwards -- CG_SetupClientCharacterInfo
// 0x00541800 strncpy's INTO it. So a slot whose pointer cannot be read is not
// a race: it says this probe is not looking at that process's characterInfo at all.
```

### 8.1 三层论证

```text
1. cgame 在 init 时给每个槽一个【永久的】64 字节缓冲区
2. 之后没有东西写【指针】—— `0x00541800` 是 `strncpy`【进去】
3. ⇒ 一个指针读不出的槽【不是竞态】：它说明这个探针根本没看着那个进程的 characterInfo
```

### 8.2 这是一个**排除竞态**的论证

**"不是竞态"** 的理由是"指针只写一次" ⇒ **读不到就是看错了地方**。

**这比"可能有时序问题"强得多。**

## 九、**`tag_` 的识别**（本组第五重要）

```cpp
// BG_UpdatePlayerDObj 0x0040AB30
// walks the ten names at +0x20 and STOPS AT THE FIRST EMPTY ONE, registering
// every non-empty one as an XModel. When the character resolver returns no
// names at all, 0x00541800's second loop is off by one slot and writes a TAG
// STRING into an attachment MODEL slot -- which is what "tag index 0 kills
// the whole player's DObj" was. A `tag_` here names that defect on sight.
```

### 9.1 五层

```text
1. `BG_UpdatePlayerDObj` 走 10 个名字（`+0x20`），【遇到第一个空就停】
2. 每个非空的名字注册为一个 XModel
3. 当角色解析器一个名字都不返回时
4. `0x00541800` 的第二个循环【差一个槽】
5. ⇒ 把一个【TAG 字符串】写进一个附件【模型槽】
```

### 9.2 而"tag index 0 杀掉整个玩家的 DObj"

**这是那个缺陷的名字。**

**⇒ 在日志里看到 `tag_` 就立刻命名了这个缺陷。**

**这是一个"可观测的指纹"** —— 不需要理解整个链条就能识别。

### 9.3 `BK` 与 `strncpy` 的对比

```text
`0x00541800` 是 `strncpy` 进去（不换指针）
而它有两个循环，第二个【差一个槽】
```

## 十、`req` 与 `cs` 的**两个证据源**

### 10.1 `req` = `info + 1024`（我方发出的请求）

```cpp
constexpr std::size_t CharacterInfoResolverRequestOffset = 1024;
const auto word = [requestBytes](index) { return *(const uint32*)(requestBytes + index*4); };
// word(0)=model, word(1)=variant, word(2)=female, word(3)=item
// word(4..15) = overrides 位集
```

### 10.2 那个**决定性的诊断**

```cpp
// Section 166b: 0x00541800 fills it from the clientState this server sends
// and MEMSETS IT TO ZERO on its one early return
// (`if (*(int *)(clientState + 0x150) <= 0)`). So this one field separates
// the only two ways a name can come back empty, with no inference left:
//
//   request all zero      -> the modelIndex gate fired. ... a WIRE fault, ours, on the way in.
//   request populated     -> the gate passed and the resolver 0x0080E600
//                            returned NO NAMES ... an ITEM-TABLE fault, not a wire one.
```

### 10.3 一个字段分开两类缺陷

```text
request 全零  ⇒ modelIndex 闸门触发 ⇒ 【线上故障，我们的，在入口路上】
request 有值  ⇒ 闸门通过而解析器没返回名字 ⇒ 【物品表故障，不是线上的】
```

**"没有推理余地了"** —— 因为 `0x00541800` 在唯一一个提前返回里把它 memset 成零。

**这是本文件里最干净的一个判据。**

### 10.4 `cs` = `base - 503016`（客户端收到的 clientState）

```cpp
// The clientinfo loop inside sub_54B3F0 walks it:
//     mov ebx, [esp+0x24]      ; the CG object
//     add ebx, 0x56C1C         ; clientState = ebx - 4  ->  CG + 0x56C18
//     ...
//     add ebx, 0x160           ; and the stride is 0x160
// and dword_827F730 is CG + 858368 (0x4557FE), so the array sits at
// dword_827F730 - 503016.
constexpr std::ptrdiff_t ClientStateArrayFromCharacterInfoBase = -503016;
constexpr std::size_t ClientStateStride = 0x160;
```

### 10.5 三个数字的算术

```text
dword_827F730 = CG + 858368
clientState   = CG + 0x56C18
差            = 858368 - 0x56C18 = 858368 - 355352 = 503016
```

**`0x56C18 = 355352`** ✓

**而 `503016 = 0x7ACA8`。**

**⇒ `clientState = base - 503016`** ✓ 算术闭合。

### 10.6 三个字段

```text
+0x150   model index
+0x7C   character item（低 16 位）
+0x14   纯 body model index（回退 0x00541BD0 用它变名字）
```

### 10.7 而 `<= 0` 的闸门

```cpp
// `if (*(int *)(clientState + 0x150) <= 0)`
```

**`modelIndex <= 0` ⇒ 提前返回 ⇒ memset request 为零。**

**⇒ 所以 `request` 全零等价于 `clientState + 0x150 <= 0`。**

## 十一、**"不要在这里读 battery"** —— 一次用崩溃换来的教训

```cpp
// NO BATTERY READ HERE. `+0x0A4` was read from this struct for one run, to
// settle whether the zm meter's numerator is ever non-zero -- it is not,
// measured `battery=0` with `valid=1` -- and the client CRASHED while
// firing shortly after, 0xC0000005 on a corrupted pointer. Isolated by
// reverting to the last commit and firing again: no fault, so the read is
// the prime suspect and it is gone.
```

### 11.1 四个事实

```text
+0x0A4 读一跑 ⇒ 测得 battery=0 而 valid=1
随后开火时客户端崩溃 0xC0000005 于一个损坏的指针
回退到上一个 commit 再开火 ⇒ 无故障
⇒ 那个读是主要嫌疑，已删除
```

### 11.2 而**不安全的原因**

```cpp
// Why it was unsafe: this function RUNS OFF THE GAME THREAD, as the comment
// above says, and the loop's only structural guard covers the first 32
// bytes (CharacterInfoAttachmentNamesOffset). A read 164 bytes in, across
// four slots including ones no client occupies, is a check-then-use race
// against a struct the engine is rebuilding. A local readableSpan does not
// close that.
```

### 11.3 三层

```text
1. 这个函数【不在游戏线程】上跑
2. 循环的结构性守卫只覆盖前 32 字节
3. 一个 164 字节处的读，跨四个槽（包括没有客户端占用的）⇒ 【check-then-use 竞态】
```

**"一个局部的 `readableSpan` 不闭合这个。"**

**⇒ 这是一个 **TOCTOU** 的明确定义** —— 而 `readableSpan` 只保证"检查那一刻可读"。

### 11.4 那句"答案已经记录了"

```cpp
// The answer it produced is recorded in re/demo-re/17-zm-hud-and-battery.md,
// so re-adding it buys nothing.
```

**"它产生的答案已记录在 `re/demo-re/17-zm-hud-and-battery.md` 里，所以重新加回来买不到任何东西。"**

**⇒ 一个用崩溃换来的一次性测量，而结果已归档。**

## 十二、`reportSessionMemberItemHandles` 的**decodeKey 对比**

### 12.1 那段核心问题

```cpp
// THE CHARACTER-ITEM DECODE KEY, FROM WHICHEVER PROCESS THIS IS.
//
// The record entries the engine wants are `rotr(itemId, 8) ^ decodeKey`
// (encodeCharacterItemId), and this server puts RAW ids on the wire -- which is
// why the client renders items unrelated to the loadout (section 182c). Whether
// the server can encode FOR the client turns on one fact and nothing else:
//
//   same value in both processes -> the key is global, the server can encode.
//   different values             -> it is per-profile, the server CANNOT, and
//                                   the wire must carry something the client
//                                   encodes with its own key.
```

### 12.2 一个二分

```text
两个进程的 key 相同   ⇒ key 是【全局】的 ⇒ 服务器可以编码
两个进程的 key 不同   ⇒ key 是【每 profile】的 ⇒ 服务器不能编码
```

### 12.3 而"打印它就能比较"

```cpp
// This reporter already runs in BOTH processes -- the log carries its output as
// "session member roster" from the dedicated and "client-side session member
// roster" from the client -- so printing the key here compares them with no new
// plumbing and no guess about which side is which.
```

**"没有新的管道，也不猜哪边是哪边。"**

### 12.4 而编码式是 **`rotr(itemId, 8) ^ decodeKey`**

**而 §239 里 `readIndex` 是 `std::rotl(raw ^ key, 8)`** —— **方向相反**！

```text
§239  decodeCharacterItemId   : ROL32(key ^ low ^ high, 8)      三个操作数
§239  readIndex               : ROTL(raw ^ key, 8)              两个操作数
§255  encodeCharacterItemId   : ROTR(itemId, 8) ^ decodeKey     【先旋转后异或】
```

**三种不同的组合** —— 而 `rotr(x,8) ^ k` 与 `rotl(x^k, 8)` **不是互逆的**：

```text
encode:  y = rotr(x, 8) ^ k
decode:  x = rotl(y ^ k, 8)
⇒ rotl((rotr(x,8) ^ k) ^ k, 8) = rotl(rotr(x,8), 8) = x   ✓ 互逆
```

**✓ 实际上**是互逆的** —— 因为 `rotr` 与 `rotl` 是逆运算，而两次异或相消。**

**所以 §255 的 `encodeCharacterItemId` 与 §239 的 `readIndex` 解码式是**同一对**。**

**这是一处重要的确认。**

## 十三、`characterInfo` 的**前 32 字节守卫**

```cpp
if (!readableSpan(info, CharacterInfoAttachmentNamesOffset))   // 0x20 = 32
{ report += " [N]=UNREADABLE"; continue; }
```

### 13.1 而后续读了 `+0x18`（名字指针）、`+0x20`（附件）、`+660`、`+900`、`+1024`

**全部超过了 32 字节。**

**⇒ 每一处都有自己的 `readableSpan`（对 `+660`/`+900`），但 `+0x18`/`+0x20` 依赖那 32 字节的守卫。**

**而 §255 的批评正是针对这一点**（"只覆盖前 32 字节"）。

## 十四、关键结论

1. **`profileSlotProbeEnabled` 的六个崩溃报告"暗示而不是证明"** —— 两个方向的证据都不成立。
2. **`12` 是我们的界而非引擎的**（引擎只夹负数、乘 156、无上界）—— 而它**确实拒绝了每一次 loadout 捕获**。
3. **`ProfileManagerRva` 是管理器本身不是指针** —— 第一版两次解引用导致"永远未就绪"。
4. **`chunkMask` 必须**相等**而不是子集** —— 半加载 vs 额外位，代码选保守。
5. **`0x400000 + 0xE14BC48 + 0x10 = 0xE54BC58`** —— 实测核对。
6. **客户端 characterInfo 步长 1104（= 0x450）与服务端相同，但基址不同**（`0xAFA50` vs `0xAF350`）。
7. **池是 37 块 × 1600 字节**（`0xE740`），19 + 18 块，每块给 25 个缓冲区。
8. **`NULL` / `EMPTY` / `UNREADABLE` 三态必须分开** —— 而 `EMPTY` 曾被当成仪器噪声（第 N 次"信号被分类成噪声"）。
9. **不改 `readCString`** —— 因为其它调用者依赖"非空或什么都没有"。
10. **"指针只写一次 ⇒ 读不到不是竞态"** —— 一个排除竞态的论证。
11. **`tag_` 是"差一个槽"缺陷的可观测指纹**。
12. **`request` 全零 vs 有值分开"线上故障"与"物品表故障"** —— 本文件最干净的判据。
13. **`clientState = base - 503016`** 算术闭合。
14. **`+0x0A4` battery 读导致崩溃**（0xC0000005），回退后无故障 ⇒ 已移除；而 `readableSpan` 不闭合 TOCTOU。
15. **`rotr(x,8) ^ k` 与 `rotl(x^k,8)` 是互逆对** —— §255 与 §239 的两种表达一致。

## 十五、未闭合点

- `156`（角色记录字节尺寸）与 §238 的 `14`（位移序号）的关系未直接核对。
- `0xAFA50` vs `0xAF350` 两个数组的用途区分只在代码注释里。
- `12` 这个界是否真的过严（代码明确拒绝凭推理放宽）。
- `EngineBindings.cpp` 15260 行之后未读取。
