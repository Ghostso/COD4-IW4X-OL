# 学习报告 130（重开）— `ClientCommandTrace.cpp`（749 行）：三个测量仪器

**学习范围**：`ClientCommandTrace.cpp`（27,720 B / 749 行）
**性质**：全实测（**逐行读完**）
**★★★★★ 本报告收录九个重大发现**：①**`sub_614C00` 的 6 字节序言（不是 5）** ②**命令环的完整寻址公式（512 × 1024）** ③**`'!'` 子帧的 4+len 帧格式** ④**CSV 转义与十六进制双路径** ⑤**`_fsopen` + `_SH_DENYWR` 的共享读** ⑥**`cg = table[selector] ^ 0xFBB2C97A` 的三指令解析** ⑦**三个镜像区域的精确偏移** ⑧**`.data` 的 229.8 MB vs 10.5 MB** ⑨**`com_maxfps` 探针的三个 RVA**

---

## 一、★★★★★ **`sub_614C00` 的 6 字节序言**

### 1.1 ★★★★★ 完整注释（第 25–34 行，逐字）

```cpp
// sub_614C00, **verified against C:\Games\OLfinal\out.exe rather than taken from a note**:
//
//     RVA **0x214C00**   **55 8b ec 83 ec 08**  53 56 57  8b f8  a1 ...
//                    push ebp / mov ebp,esp / sub esp,8 / push ebx / push esi / push edi
//                    **mov edi, eax**          <- **EAX is the sequence number on entry**
//
// **SIX BYTES, NOT FIVE.** The first three instructions occupy **1 + 2 + 3 bytes**, so a
// five-byte steal would **cut `sub esp, 8` in half** and **the client would die on the first
// command**. **FrameHook's HookSize of 5 is correct only because Com_Frame's prologue happens
// to land on a boundary at five (55 8b ec 56 57)**. **The size is a property of the TARGET,
// not the hook.**
```

★★★★★ **⇒ 六个精确值：**
```
RVA = **`0x214C00`**
字节 = **`55 8B EC 83 EC 08`**
        ↓
★★★ `55`     ⇒ `push ebp`（**1 字节**）
★★★ `8B EC`  ⇒ `mov ebp, esp`（**2 字节**）
★★★ `83 EC 08` ⇒ `sub esp, 8`（**3 字节**）
        ↓
★★★ 合计 **1 + 2 + 3 = 6 字节**
        ↓
★★★★★ ⇒ **5 字节会把 `sub esp, 8` 切成两半** ⇒ **客户端在第一条命令上就死**
```

### ★★★★★ **"size 是目标的属性,不是钩子的"**

```
`FrameHook.cpp` 的 `HookSize = 5` **只因为** `Com_Frame` 的序言恰好落在 5 字节边界
（**`55 8B EC 56 57`**）
        ↓
★★★ ⇒ 而 `sub_614C00` 需要 **6 字节**
★★★ ⇒ **"The size is a property of the TARGET, not the hook."**
```

### ★★★ `EAX` 是入口时的序号

```
`8B F8` ⇒ `mov edi, eax`  ⇒ **EAX 在入口就是 sequence number**
        ↓
★★★ ⇒ 所以钩子可以直接 `push eax` 作为 `record()` 的参数
```

---

## 二、★★★★★ **命令环的完整寻址公式**

### 2.1 ★★★★★ 完整注释（第 38–49 行，逐字）

```cpp
// **The command text is NOT an argument.** sub_614C00 reads it out of a **512-slot ring**:
//
//     base = **dword_331C0C8 ^ 0xD362501F**        (RVA **0x2F1C0C8**, obfuscated pointer)
//     cmd  = base + **524628** + ((seq & **0x1FF**) << **10**)
//
// **512 slots of 1024 bytes**. **`(seq & 0x1FF)` is where the ring size is stated by the
// image itself**, independently of the wire measurement that first established it.
```

★★★★★ **⇒ 五个精确常量：**

| 常量 | 值 |
|---|---|
| `CommandRingBaseRva` | **`0x2F1C0C8`**（`dword_331C0C8`） |
| `CommandRingBaseKey` | ★ **`0xD362501F`** |
| `CommandRingOffset` | ★ **`524628`** |
| `CommandRingSlots` | ★ **`512`**（`0x1FF` 掩码） |
| `CommandRingStride` | ★ **`1024`**（`<< 10`） |

### ★★★★★ **公式分解**

```
base = *(u32*)(module + 0x2F1C0C8) ^ 0xD362501F
        ↓
cmd  = base + 524628 + ((seq & 0x1FF) << 10)
        ↓
★★★ `seq & 0x1FF`     ⇒ **512 个槽位**（环大小由**镜像自己**说明）
★★★ `<< 10`           ⇒ **× 1024 字节/槽**
★★★ `+ 524628`        ⇒ 环在结构体里的偏移
        ↓
★★★ 总环大小 = **512 × 1024 = 524,288 字节**（512 KB）
★★★ 且 **524628** 略大于 **524,288** ⇒ **环前面还有 340 字节的头**
```

★★★ **⇒ `524,628 - 524,288 = 340` ⇒ 头部 **340 字节**。**
**⇒ 第 486–488 行注释确认："its **ring sits at +524628**, so its **header holds the sequence counters**"。**

---

## 三、★★★★★ **`'!'` 子帧的 4+len 帧格式**

### 3.1 ★★★★★ 完整注释（第 114–123 行，逐字）

```cpp
// **A '!' RECORD IS BINARY AND MUST NOT BE NUL-TERMINATED.**
//
// Measured on the first live run: **all 85 '!' records came out as ONE BYTE, "!"**, because
// **the sub-frame carries a NUL at offset 1 and a NUL-bounded read stops there**. **Half the
// traffic -- the live configstring updates and BOTH scoreboard records -- collapsed into one
// indistinguishable row.** The comment in record() warned about exactly that, and **the bug
// was upstream of the code it warned about**.
//
// The framing is **'!' at 0, a uint16 LENGTH at +2, payload from +4**. So the record is
// **4 + length bytes** and **the payload's first byte is the inner verb sub_614AC0 switches on**.
```

★★★★★ **⇒ 五个精确值：**
```
`[0]`    = **`'!'`**
`[1]`    = ★ **NUL**（`0x00`）—— 这就是 NUL 截断的元凶
`[2..3]` = **`uint16 length`**
`[4..]`  = **payload**
        ↓
★★★ 总长 = **4 + length**
★★★ **payload 的第一个字节 = 内层 verb**（`sub_614AC0` 的 switch 值）
        ↓
★★★ 实测：**85 条 `'!'` 记录全部被截成 1 字节 `"!"`**
★★★ ⇒ **一半的流量**（实时 configstring 更新 + **两条**计分板记录）塌成一行
```

### ★★★ 钳制到槽位（第 129–133 行）

```cpp
// CLAMPED TO THE SLOT. A length read out of a slot that was not written this cycle
// is whatever was there before, and trusting it would walk off the ring.
return std::string(text, std::min<std::size_t>(
    4u + static_cast<std::size_t>(length), CommandRingStride));   // ★ min(4+len, 1024)
```

### ★★★ 文本记录的两个边界（第 135–140 行）

```cpp
// BOUNDED BY THE SLOT, NOT BY THE NUL. A slot that has never been written holds
// whatever was there before, and strlen on it would run off the end of the ring.
const auto *end = (const char*)std::memchr(text, '\0', **CommandRingStride**);
return std::string(text, end ? (size_t)(end - text) : **CommandRingStride**);
```

★★★ **⇒ 用 `memchr` 限长 **1024**,而不是 `strlen`（无界）。**

---

## 四、★★★★★ **CSV 转义与十六进制双路径**

### 4.1 ★★★ `escape()` 的两条规则（第 143–161 行）

```cpp
// A reliable command carries quotes and commas routinely --
// `s ui_DMKillScore "50"` has both -- and **a trace that cannot be parsed is not a trace**.
for (const auto c : value)
{
    if (c == '"') out += "\"\"";                        // ★ 双引号翻倍（CSV 标准）
    else if ((unsigned char)c < 0x20) out += ' ';       // ★ 控制字符 ⇒ 空格
    else out += c;
}
```

★★★ **⇒ 一个真实例子：`s ui_DMKillScore "50"` 同时含引号和（可能的）逗号。**

### ★★★★★ **二进制走十六进制**（第 196–213 行，逐字）

```cpp
// **HEX FOR A BINARY RECORD, TEXT FOR A TEXT ONE.** `escape()` turns **every byte below
// 0x20 into a space**, which is **right for a stray control character in a command string
// and destroys a binary payload** -- and **the binary ones are the records we cannot decode
// offline, so they are the whole reason this exists**.
if (verb == '!')
{
    static constexpr char Digits[] = "0123456789abcdef";
    rendered.reserve(text.size() * 2);
    for (const auto c : text) { rendered += Digits[byte >> 4]; rendered += Digits[byte & 0x0F]; }
}
```

★★★ **⇒ 一个精确的取舍：**
```
`escape()` 把 **< 0x20 的字节变成空格**
   ⇒ 对**文本命令里的杂散控制符**正确
   ⇒ 但**毁掉二进制载荷**
        ↓
★★★ 而**二进制记录正是无法离线解码的那些** ⇒ **是这个工具存在的全部理由**
        ↓
★★★ ⇒ `'!'` 记录走**小写十六进制**（`0123456789abcdef`）
```

### ★★★★★ **三个 dispatch 站点的分派**（第 176–194 行）

```cpp
const auto verb = text.front();
char inner = 0;
const char* dispatch = "**sub_613A40**";          // ★ 默认

if (verb == '!')
{
    if (text.size() > 4) inner = text[4];         // ★ payload 第一字节
    dispatch = "**sub_614AC0**";
}
else if (verb == 'd' || verb == 'k' || verb == 'x' || verb == 't')
{
    dispatch = "**sub_614C00**";
}
```

★★★★★ **⇒ 三个站点与四个字母的精确映射：**
```
默认（其他字母）        ⇒ **`sub_613A40`**（126-case switch）
`'!'`                  ⇒ **`sub_614AC0`**（子帧）
`'d'` / `'k'` / `'x'` / `'t'` ⇒ **`sub_614C00`**（断线路径）
        ↓
★★★ ⇒ 与报告 126 的三个 dispatch 站点**完全对应** ✓
```

### ★★★ 理由（第 178–180 行，逐字）

```
"Logging only the `'!'` would **collapse `% @ J K`** -- **four different handlers, one of them
 the scoreboard** -- into one indistinguishable row, which is **the shape of a finding being
 deleted by its own instrument**."
```

★★★ **⇒ 四个内层 verb：`%` / `@` / `J` / `K`（**`K` 是计分板**）。**

### ★★★★★ **CSV 的七列格式**（第 224–231 行）

```cpp
std::fprintf(Output, "%lu,%u,%c,%s,%s,%zu,\"%s\"\n",
             GetTickCount() - StartedAt,     // ★ ms
             sequence,                        // ★ 序号
             verb,                            // ★ 外层 verb（char）
             inner ? std::string(1, inner).c_str() : "",   // ★ 内层 verb
             dispatch,                        // ★ 站点名
             text.size(),                     // ★ 字节数
             rendered.c_str());               // ★ 内容（转义/十六进制）
```

★★★ **⇒ 表头（第 307 行）：**`ms,sequence,verb,inner,dispatch,bytes,text`** ✓**

### ★★★★★ **每行都 flush**（第 233–237 行，逐字）

```cpp
// **FLUSHED EVERY ROW, DELIBERATELY.** At **~2.4 commands a second** the cost is nothing,
// and **the alternative has already cost this project a session**: a watcher's output **sat
// in a block buffer and its log read 0 bytes through the whole run it was watching**.
// **A trace that is only readable after a clean exit is no use for a client that crashes.**
```

★★★ **⇒ 三个精确值：**
```
速率 **~2.4 命令/秒** ⇒ flush 成本可忽略
        ↓
★★★ 反例：某个 watcher 的输出**卡在块缓冲里**,**整轮日志读到 0 字节**
        ↓
★★★ ⇒ **只有干净退出后才可读的 trace,对会崩的客户端毫无用处**
```

---

## 五、★★★★★ **`_fsopen` + `_SH_DENYWR` 的共享读**

### 5.1 ★★★★★ 完整注释（第 294–302 行，逐字）

```cpp
// **ABSOLUTE PATH**, and the caller is responsible for making it one. **A diagnostic that
// wrote to a relative path once produced nothing at all and looked like a hook that never
// fired** -- **the client's working directory is not where anybody looks.**
// **`_fsopen` WITH `_SH_DENYWR`, NOT fopen.** The CRT's **fopen denies sharing outright**:
// measured, **neither PowerShell nor python could open the file while the client held it**,
// so **the trace was only readable after the client stopped recording** -- **useless for
// watching a ten-minute demo go past, and worse than useless if the client crashes**,
// which is one of the things worth tracing.
```

★★★★★ **⇒ 两个精确教训：**
```
① **相对路径** ⇒ **什么也没写**,看起来像"钩子从没响"
   ⇒ **客户端的工作目录不是任何人会去看的地方**
        ↓
② **`fopen` 拒绝共享** ⇒ **PowerShell 和 python 都打不开**
   ⇒ trace **只在停止录制后才可读**
   ⇒ **对看十分钟 demo 无用,对崩溃更无用**
        ↓
★★★ ⇒ 改用 **`_fsopen(path, "w", `_SH_DENYWR`)**（只拒写,允许读）
```

### ★★★ 路径推导（第 268–278 行）

```cpp
std::wstring buffer(MAX_PATH, L'\0');
const auto size = GetModuleFileNameW(nullptr, buffer.data(), (DWORD)buffer.size());
buffer.resize(size);
const auto file = std::filesystem::path(buffer).parent_path() / L"Ayria" / L"Logs" / L"client-commands.csv";
```

★★★ **⇒ 路径 = `<exe 目录>/Ayria/Logs/client-commands.csv`。**

### ★★★★★ **"已安装不是错误"**（第 316–324 行，逐字）

```cpp
// **ALREADY INSTALLED IS NOT AN ERROR.** Re-running the diagnostic should **start a new file
// against the hook that is already there**, not patch the prologue a second time -- **the
// second patch would copy the JMP as its own "original" and the client would recurse into
// itself on the next command.**
if (Trampoline) { Recording.store(true); return true; }
```

★★★★★ **⇒ 一个精确的递归故障：**
```
第二次打补丁 ⇒ 蹦床里复制的是**第一条 `E9`**
        ↓
★★★ ⇒ 蹦床跳到**自己的钩子** ⇒ **客户端在下一条命令上无限递归**
```

### ★★★ 序言校验失败写一行 CSV（第 336–345 行）

```cpp
if (!std::equal(std::begin(Expected), std::end(Expected), target))
{
    std::fprintf(Output,
        "0,0,?,,REFUSED,0,\"prologue at RVA 0x%zX is not 55 8B EC 83 EC 08 -- "
        "this build moved sub_614C00; nothing was patched\"\n", ClientCommandDispatchRva);
    return false;
}
```

★★★ **⇒ 拒绝也写进 CSV（第 3 列 = `?`,第 5 列 = `REFUSED`）⇒ 可在同一份文件里看到。**

### ★★★ 第 6 字节补 `0x90`（第 371 行）

```cpp
target[5] = 0x90;   // the sixth stolen byte, padded
```

### ★★★★★ **钩子故意不卸**（第 385–389 行，逐字）

```cpp
// **THE HOOK IS LEFT IN PLACE ON PURPOSE.** Unpatching means **writing six bytes back into a
// function another thread may be executing at that instant**, for no gain -- **the hook costs
// a predictable branch and a flag test once every few hundred milliseconds**. **Only the
// RECORDING stops.**
```

★★★ **⇒ 两个理由：**
```
① 卸补丁 = **往另一个线程可能正在执行的函数里写 6 字节**
② 成本 = **每几百毫秒一次可预测分支 + 一次标志测试**
```

### ★★★ 钩子的完整序列（第 242–255 行）

```cpp
__declspec(naked) void dispatchHook()
{
    __asm
    {
        pushfd
        pushad                  // ★ EAX survives; PUSHAD stores, it does not clobber
        push eax                // ★ 序号 = __cdecl 参数
        call record
        add esp, 4
        popad
        popfd
        jmp [Trampoline]        // ★ 蹦床（被偷的 6 字节 + 跳回 target+6）
    }
}
```

★★★ **⇒ 注释（第 247 行）："EAX survives; **PUSHAD stores, it does not clobber**"**
**⇒ 这是一个精确的细节：`pushad` 把 EAX 存进栈,**不改 EAX 的值** ⇒ 可以 `push eax`。**

---

## 六、★★★★★ **`cg = table[selector] ^ 0xFBB2C97A` 的三指令解析**

### 6.1 ★★★★★ 完整注释（第 426–437 行，逐字）

```cpp
// **cgBase = dword_1C1D188[dword_82C3B58] ^ 0xFBB2C97A**, and **the playerState is at cg + 0**.
//
// Read straight off **sub_613A40's own prologue**, which resolves it in **three instructions**
// before switching on the verb character:
//     **mov edx, dword_82C3B58**
//     **mov esi, dword_1C1D188[edx*4]**
//     **xor esi, 0FBB2C97Ah**
// **All three globals live in .data, whose virtual size is 229.8 MB against 10.5 MB on disk.**
```

★★★★★ **⇒ 四个精确值：**
```
`cgIndexRva` = **`0x7EC3B58`**（`dword_82C3B58`）
`cgArrayRva` = **`0x181D188`**（`dword_1C1D188`）
`cgKey`      = ★ **`0xFBB2C97A`**
        ↓
★★★ 三条指令：`mov edx, [0x82C3B58]` / `mov esi, [0x1C1D188 + edx*4]` / `xor esi, 0xFBB2C97A`
        ↓
★★★ **`.data` 的虚拟大小 = 229.8 MB,virtual 10.5 MB on disk**
   ⇒ **219 MB 的 BSS 式未初始化区**
```

★★ **⇒ 与报告 127 的 `cg = table[selector] ^ 0xFBB2C97A`**完全一致** ✓**
**⇒ 且本报告给出了 `selector` 的**来源**：`dword_82C3B58`（`cgIndexRva`）。**

### ★★★ `resolveCg()` 的三步（第 450–477 行）

```cpp
① `index = *(u32*)(ModuleBase + 0x7EC3B58)` ⇒ readable 检查
② `slot = *(u32*)(ModuleBase + 0x181D188 + index*4)` ⇒ readable 检查
③ `if (!obfuscated) return nullptr;`          // ★ 0 ^ key = key 本身
④ `cg = obfuscated ^ 0xFBB2C97A`
⑤ `readable(cg, PlayerStateBytes) ? cg : nullptr`
```

### ★★★★★ **"未设槽位 XOR 出密钥本身"**（第 468–471 行，逐字）

```
// **AN UNSET SLOT XORS TO THE KEY ITSELF.** **Zero ^ key is a 4 GB-ish pointer** that
// VirtualQuery would reject anyway, but **saying it here makes the "not in a match yet" case
// explicit rather than a mystery in the unresolved counter.**
```

★★★ **⇒ `0 ^ 0xFBB2C97A = 0xFBB2C97A`** ⇒ 一个 **~4 GB 的指针**（实际 **4,220,766,586**）**
**⇒ `VirtualQuery` 会拒绝,但显式返回 `nullptr` 让"还没进比赛"成为一个**明确状态**。**

---

## 七、★★★★★ **三个镜像区域的精确偏移**

### 7.1 ★★★★★ 完整注释（第 479–488 行，逐字）

```
// ps    **cg + 0**          the **246-field playerState**, already **116/120 verified**
// ci    **cg + 0x180C50**   clientInfo, **stride 0x450** -- names, models, ranks. Read off
//                       **CG_DrawCompassBlip**: `clientInfo = cg + 0x180C50 + 0x450*clientNum`
// clc   **the command-ring base, which IS clientConnection**: its **ring sits at +524628**, so
//                       its **header holds the sequence counters**. Sampled to find the snapshot
//                       boundary **EMPIRICALLY** -- the only callers of the command dispatcher
//                       are **five sites inside one 158 KB function**, which is **not something to
//                       hook**, and **a counter ticking ~20/s is the boundary either way**.
```

### ★★★★★ 三个区域的完整表

| 名 | 偏移 | 字节 | 来源 |
|---|---|---|---|
| **`ps`** | ★ **`cg + 0x000000`** | **`0x3B78`**（15,224） | `cg` |
| **`ci`** | ★ **`cg + 0x180C50`** | ★ **`0x450 × 18 = 19,440`** | `cg` |
| **`clc`** | **`base + 0`** | **`0x400`**（1,024） | 命令环基址 |

★★★ **⇒ 三个精确事实：**
```
① `ps` = **246 个 netfield,偏移 `0x0 .. 0x3B74`** ⇒ 大小 **`0x3B78`**（**最后一个字之后**）
② `ci` = **`cg + 0x180C50 + 0x450 * clientNum`**,**18 个 client** ⇒ **`0x450 × 18`**
③ `clc` = **命令环基址 = `clientConnection`**,环在 **`+524628`**
        ↓
★★★ `clc` 的理由：命令 dispatcher 的调用者**是一个 158 KB 函数里的五个点**
   ⇒ **不是能钩的东西**
   ⇒ 而**一个 ~20/s 的计数器就是边界**
```

★★ **⇒ `0x450` 与报告 128 的 `characterInfo 0x3B8 → 0x450`**完全一致** ✓**
**⇒ `18` 与 `MaximumSessionMembers` / `capacity` / `client >= 18` **第四次一致** ✓**

### ★★★ `PlayerStateBytes = 0x3B78` 的推导

```cpp
// playerstate-0x00DA8540.tsv: **246 netfields, offsets 0x0 .. 0x3B74**. **One word past the last.**
constexpr std::size_t PlayerStateBytes = 0x3B78;
```
★★★ **⇒ `0x3B74 + 4 = 0x3B78` ✓**

### ★★★★★ **按 4 字节字变化检测**（第 568–581 行）

```cpp
for (std::size_t offset = 0; offset + 4 <= Regions[r].bytes; offset += 4)
{
    std::uint32_t was{}, now{};
    std::memcpy(&was, previous[r].data() + offset, 4);
    std::memcpy(&now, current[r].data() + offset, 4);
    if (was == now) continue;
    std::fprintf(PsOutput, "%lu,%u,%s,0x%05zX,%u,%u\n",
                 GetTickCount() - StartedAt, commandTime, Regions[r].name, offset, was, now);
}
```

★★★ **⇒ CSV 六列：`ms,commandTime,region,offset,was,now`（第 632 行表头）**
**⇒ `commandTime` 是 `ps` 的**第 0 个字**（`cg + 0`）⇒ **join key**（第 541–545 行逐字）：**
```
"**commandTime is playerState index 0 at offset 0** -- the field demoq.py prints first on
 every change. **It is the join key**: both sides can quote it, and **neither has to guess at
 the other's clock**."
```

### ★★★ 首帧播种（第 561–566 行）

```cpp
if (!seeded[r]) { previous[r] = current[r]; seeded[r] = true; continue; }   // ★ 第一帧不报
```

### ★★★ `Sleep(PsInterval)` 默认 **50 ms**（第 448/601 行）

```cpp
unsigned PsInterval = 50;
PsInterval = intervalMs ? intervalMs : 50;
```

### ★★★★★ **为什么是线程而不是钩子**（第 415–422 行，逐字）

```
// **A READER ON A THREAD, NOT A HOOK.** We already run inside out.exe, so the client's decoded
// playerState is **simply memory we can read**. **A trampoline would put our code on the
// engine's own execution path for no gain** -- and **that path is the one that killed three
// clients at once when it was per-frame**. **Reading cannot.**
```

★★★ **⇒ 与报告 126 的 "Frida hook on the PER-FRAME sub_54FDA0 crashed all three running
clients at once"**同一事件** ✓**

### ★★★ `stopPlayerStateTrace` 的 `Sleep(120)`（第 656 行）

```cpp
Sleep(120);   // let the sampler notice before the file closes
```
★★ **⇒ 120 ms = 2.4 个 50 ms 周期 ⇒ 足够采样线程看到 `PsRecording == false`。**

---

## 八、★★★★★ **`com_maxfps` 探针的三个 RVA**

### 8.1 ★★★★★ 完整常量（第 688–692 行）

```cpp
constexpr std::size_t MaxFpsDvarPointerRva = **0x7258770**;   // dword_7658770
constexpr std::size_t FrameCounterRva      = **0x2F3A08C**;   // dword_333A08C, ++ per Com_Frame
constexpr std::size_t ConnectionStateRva   = **0x72446B0**;   // dword_76446B0
constexpr std::size_t DvarIntValueOffset   = **12**;
```

★★★★★ **⇒ 四个精确值：**
```
`com_maxfps` dvar 指针 ⇒ **`0x7258770`**
帧计数器（每次 Com_Frame ++） ⇒ **`0x2F3A08C`**
`cls.state` ⇒ ★ **`0x72446B0`**
dvar 整数值偏移 ⇒ ★ **`+12`**（`0x0C`）
```

★★★ **⇒ 第 3 条与报告 127 的 `cls.state = 0x076446B0`**完全一致** ✓**（RVA = `0x076446B0 - 0x400000` = `0x36446B0`？）
**★★ 待核对：** 报告 127 说 `cls.state` 绝对 **`0x076446B0`**,RVA 应为 **`0x36446B0`**；
本文件写 **`0x72446B0`**。差 **`0x3C00000`**。

★★★ **⇒ 这是一个**必须标注的差异**：**
```
报告 127（`DisconnectWitness.cpp`）：`ClsStateAbsolute = **0x076446B0**`,
   `AssumedImageBase = 0x00400000` ⇒ RVA = **`0x036446B0`**
        ↓
本报告（`ClientCommandTrace.cpp`）：`ConnectionStateRva = **0x72446B0**`
        ↓
★★★ 差 **`0x3C00000`**（62,914,560）
```

★★ **⇒ 两者不可能同时对同一地址。`0x076446B0` 作为绝对地址,
   RVA 必是 `0x036446B0`。而本文件写 `0x72446B0` ⇒ 若按 `base + 0x72446B0` 计算,
   绝对地址是 `0x076446B0`（`0x400000 + 0x72446B0 = 0x76446B0`）。
   **★★★ 但 `0x400000 + 0x72446B0 = 0x76446B0`,而报告 127 的绝对地址是 `0x76446B0`（写作 `0x076446B0`）⇒ 一致！**
   ⇒ **两边其实一致**,只是报告 127 把 `0x76446B0` 写成 `0x076446B0`（补了一个前导零）。
   **⇒ 结论：RVA = `0x72446B0`,绝对 = `0x76446B0`。**
   ⇒ 而报告 127 里 `0x076446B0 - 0x400000 = 0x72446B0` **也是对的**（我之前算 `0x036446B0` 算错了）。
   ⇒ **无差异 ✓**（我在报告 127 里写的 `0x072446B0` 是错的,正确是 `0x072446B0`？）
   `0x76446B0 - 0x400000 = 0x36446B0`... 

**★★ 精确重算：**
```
`0x076446B0` 去掉前导零 = **`0x76446B0`**
`0x76446B0 - 0x400000` = **`0x72446B0`** ✓ 与本文件 `ConnectionStateRva = 0x72446B0` **完全一致**
```
★★★ **⇒ 一致 ✓。我在报告 127 里写的 `0x072446B0` 是正确的。**
**⇒ 本条澄清完毕。**

### ★★★★★ **`fps-probe` 的完整日志格式**（第 735–742 行）

```cpp
"fps-probe com_maxfps before=%u now=%u minMsec=%u | frames=%u over %llu ms = %.1f fps
 | connectionState=%u (Com_Frame clamps to 30 when this is neither 0 nor 10)"
```

★★★★★ **⇒ 一个精确的**新事实**：**
```
**`Com_Frame` 在 `connectionState` 既不是 0 也不是 10 时,把帧率钳到 30**
```

### ★★★ 直接写 dvar 值而非 `Dvar_SetInt`（第 714–718 行，逐字）

```cpp
// **WRITE THE VALUE DIRECTLY RATHER THAN THROUGH Dvar_SetInt**, because **the question is
// what the LIMITER does with it, not whether the dvar setter clamps**. **Zero is inside the
// registered range either way.**
if (set && maxfps) *maxfps = value;
```

### ★★★ 测量逻辑（第 720–733 行）

```cpp
const auto window = sampleMs ? sampleMs : **3000u**;
const auto startFrames = *counter;
const auto startTicks = GetTickCount64();
Sleep(window);
const auto endFrames = *counter;
const auto elapsed = GetTickCount64() - startTicks;
const auto frames = endFrames - startFrames;
const auto fps = elapsed ? (frames * 1000.0 / elapsed) : 0.0;
const auto minMsec = now ? (**1000u / now**) : **1u**;      // ★ 整数除法
```

★★★ **⇒ `minMsec = 1000 / maxfps`（**整数除法**）与报告 126 的推导**完全一致** ✓**
**⇒ 且 `maxfps == 0` ⇒ `minMsec = **1**`（跳过限速器）✓**

### ★★★ 三级解引用（第 699–705 行）

```cpp
const auto pointer = *(const uintptr_t*)(base + MaxFpsDvarPointerRva);
return pointer ? (uint32_t*)(pointer + **DvarIntValueOffset**) : nullptr;   // ★ +12
```
★★★ **⇒ dvar 结构体里整数值在 **`+12`**（与报告 129 的 `dvar[3]` / `[ecx+0Ch]`**完全一致** ✓）。**

---

## 九、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **`sub_614C00`** | RVA **`0x214C00`**,字节 **`55 8B EC 83 EC 08`**（**6 字节**） |
| 2 | ★★★★★ **为什么 6 不是 5** | `push ebp`(1) + `mov ebp,esp`(2) + `sub esp,8`(3) ⇒ 5 会**切半 `sub esp,8`** |
| 3 | ★★★★★ **"size 是目标的属性"** | `FrameHook` 的 5 只因 `Com_Frame` 序言 **`55 8B EC 56 57`** 恰好 5 字节边界 |
| 4 | ★★★ EAX 语义 | `8B F8` = `mov edi, eax` ⇒ **EAX 入口即序号** |
| 5 | ★★★★★ **命令环 RVA** | **`0x2F1C0C8`**（`dword_331C0C8`） |
| 6 | ★★★★★ **命令环密钥** | ★ **`0xD362501F`** |
| 7 | ★★★★★ **完整公式** | `base = *(u32*)(mod+0x2F1C0C8) ^ 0xD362501F`；`cmd = base + **524628** + ((seq & **0x1FF**) << **10**)` |
| 8 | ★★★★★ **环参数** | **512 槽 × 1024 字节 = 524,288**；偏移 **524,628** ⇒ 头 **340 字节** |
| 9 | ★★★★★ **`'!'` 帧格式** | `[0]`=`'!'` / **`[1]`=NUL** / `[2..3]`=**uint16 len** / `[4..]`=payload；总长 **4+len** |
| 10 | ★★★★★ **NUL 截断的实测** | **85 条 `'!'` 全部塌成 1 字节 `"!"`** ⇒ **一半流量**（configstring + **两条**计分板）丢失 |
| 11 | ★★★ 内层 verb 位置 | **payload 第一字节**（`text[4]`） |
| 12 | ★★★ 长度钳制 | `min(4 + len, **1024**)` |
| 13 | ★★★ 文本边界 | **`memchr(text, '\0', 1024)`**,不用 `strlen` |
| 14 | ★★★ CSV 转义 | `"` ⇒ `""`；**`< 0x20` ⇒ 空格** |
| 15 | ★★★★★ **二进制走十六进制** | `'!'` 记录用**小写十六进制**（`escape` 会毁掉二进制） |
| 16 | ★★★★★ **三个 dispatch 站点** | 默认 **`sub_613A40`** / `'!'` ⇒ **`sub_614AC0`** / **`'d' 'k' 'x' 't'`** ⇒ **`sub_614C00`** |
| 17 | ★★★ 四个内层 verb | **`%` / `@` / `J` / `K`**（**`K` 是计分板**） |
| 18 | ★★★ CSV 七列 | `ms,sequence,verb,inner,dispatch,bytes,text` |
| 19 | ★★★★★ **每行 flush** | 速率 **~2.4/s**；反例：块缓冲导致**整轮 0 字节** |
| 20 | ★★★★★ **`_fsopen` + `_SH_DENYWR`** | `fopen` 拒绝共享 ⇒ **PowerShell/python 都打不开** |
| 21 | ★★★ 路径 | `<exe 目录>/Ayria/Logs/client-commands.csv`（**绝对路径**） |
| 22 | ★★★★★ **二次打补丁会递归** | 蹦床里复制的是**第一条 `E9`** ⇒ **跳到自己的钩子** |
| 23 | ★★★ 序言失败写 CSV | 第 3 列 `?`、第 5 列 `REFUSED` |
| 24 | ★★★ 第 6 字节 | `target[5] = 0x90` |
| 25 | ★★★★★ **钩子故意不卸** | 卸 = 往另一线程可能正在执行的函数写 6 字节；成本 = **每几百毫秒一次分支** |
| 26 | ★★★ `pushad` 细节 | "**PUSHAD stores, it does not clobber**" ⇒ EAX 可继续用 |
| 27 | ★★★★★ **`cg` 三指令** | `mov edx,[0x82C3B58]` / `mov esi,[0x1C1D188+edx*4]` / **`xor esi, 0xFBB2C97A`** |
| 28 | ★★★★★ **三个 RVA** | `cgIndexRva = **0x7EC3B58**` / `cgArrayRva = **0x181D188**` / `cgKey = **0xFBB2C97A**` |
| 29 | ★★★★★ **`.data` 尺寸** | **虚拟 229.8 MB vs 磁盘 10.5 MB** ⇒ **~219 MB 未初始化** |
| 30 | ★★★★★ **未设槽位 = 密钥本身** | `0 ^ 0xFBB2C97A = **0xFBB2C97A**`（~4 GB 指针）⇒ **显式返回 `nullptr`** |
| 31 | ★★★★★ **三个镜像区域** | `ps` **`cg+0`** / `0x3B78`；`ci` **`cg+0x180C50`** / **`0x450 × 18 = 19,440`**；`clc` **环基址** / `0x400` |
| 32 | ★★★ `ci` 公式 | **`cg + 0x180C50 + 0x450*clientNum`**（从 `CG_DrawCompassBlip` 读出） |
| 33 | ★★★★★ `clc` 的理由 | 命令 dispatcher 的调用者是**一个 158 KB 函数里的五个点** ⇒ **不能钩**；**~20/s 计数器就是边界** |
| 34 | ★★★ `ps` 的 246 netfield | 偏移 **`0x0 .. 0x3B74`** ⇒ 大小 **`0x3B78`**（最后一字之后） |
| 35 | ★★★ 4 字节字检测 | `offset + 4 <= bytes`,步长 **4** |
| 36 | ★★★ `commandTime` | `ps` **第 0 字（`cg+0`）** ⇒ **join key** |
| 37 | ★★★ 首帧播种 | `!seeded` ⇒ 只存不报 |
| 38 | ★★★ 采样周期 | 默认 **50 ms** |
| 39 | ★★★★★ **线程而非钩子** | "**that path is the one that killed three clients at once when it was per-frame**" |
| 40 | ★★★ 停止等待 | **`Sleep(120)`**（2.4 个周期） |
| 41 | ★★★★★ **`com_maxfps` 探针三 RVA** | dvar 指针 **`0x7258770`** / 帧计数 **`0x2F3A08C`** / `cls.state` **`0x72446B0`** |
| 42 | ★★★ dvar 值偏移 | ★ **`+12`**（与报告 129 的 `[ecx+0Ch]` **一致** ✓） |
| 43 | ★★★★★ **新事实：Com_Frame 钳 30** | "**Com_Frame clamps to 30 when connectionState is neither 0 nor 10**" |
| 44 | ★★★ 直接写值 | 不走 `Dvar_SetInt`（问的是**限速器**行为,不是 setter 是否钳制） |
| 45 | ★★★ `minMsec` | **`1000 / maxfps`（整数除法）**；`maxfps == 0` ⇒ **1** |
| 46 | ★★★ 默认窗口 | **3000 ms** |
| 47 | ★★★ 地址一致性核对 | `0x076446B0`（报告 127）− `0x400000` = **`0x72446B0`** = 本文件 `ConnectionStateRva` ✓ **无差异** |

---

## 十、结论

### 1. ★★★★★ **`sub_614C00` 必须偷 6 字节,不是 5**

★ **⇒ `1 + 2 + 3` 的指令边界 ⇒ 5 会切半 `sub esp, 8` ⇒ 第一条命令就死。**
**⇒ 且确立了原则："size 是**目标**的属性,不是钩子的。"**

### 2. ★★★★★ **命令环的完整公式与参数**（512 × 1024，密钥 `0xD362501F`，偏移 524,628）

### 3. ★★★★★ **`'!'` 帧的 `4 + len` 格式与 NUL 截断的实测**（85 条全塌成 1 字节）

### 4. ★★★★★ **CSV 的二进制/文本双路径**（`escape` 会毁掉二进制 ⇒ `'!'` 走十六进制）

### 5. ★★★★★ **`_fsopen` + `_SH_DENYWR`**：`fopen` 拒绝共享是一个真实的观测障碍

### 6. ★★★★★ **`cg = table[selector] ^ 0xFBB2C97A` 的三条指令**（含 `cgIndexRva` 这个此前未记录的来源）

### 7. ★★★★★ **三个镜像区域的精确偏移**（`ps` / `ci` `0x450×18` / `clc`）

### 8. ★★★★★ **`.data` 的 229.8 MB vs 10.5 MB**（~219 MB 未初始化）

### 9. ★★★★★ **`Com_Frame` 在 `connectionState ∉ {0, 10}` 时把帧率钳到 30**（新事实）

### 10. ★★★ **地址一致性核对通过**：`cls.state` 的绝对 `0x076446B0` 与 RVA `0x72446B0` 互证

---

## 十一、下一步

`game_server` 根剩余：

1. ★ **`EngineBindings.cpp`（917,344 B）** + `EngineBindings.hpp`（133,088 B）
2. ★ **`Appmain.cpp`（565,999 B）**
3. `NativePmoveBindings.cpp`（113,000 / **2,090 行**）
4. `ClientProcessPatches.cpp`（82,545 / **1,815 行**）
5. 然后 `server_mp` 154 文件（12,604,630 B）
