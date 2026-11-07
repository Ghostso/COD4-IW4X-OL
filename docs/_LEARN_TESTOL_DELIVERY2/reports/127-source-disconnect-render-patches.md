# 学习报告 127（重开）— `game_server` 根：断线见证 / 渲染帧 / 客户端补丁面 / 原生武器

**学习范围**：`DisconnectWitness.cpp`（538 行）+ `ClientRenderFrameHook.hpp`（199）+ `ClientProcessPatches.hpp`（281）+ `NativeWeaponBindings.cpp`（433）+ `codol_bot_names.hpp`（763）
**性质**：全实测（**五文件逐行读完**）
**★★★★★ 本报告收录十个重大发现**：①**`cls.state = 0` 的唯一写入点 `0x0077C343`** ②**两次"钩子装了但没响"的实测** ③**`sub_514540` 的 configstring 逐条校验（`0x31D9` / `0x15` / `0x17`）** ④**DR0+DR1 双硬件断点** ⑤**渲染帧钩子必须在渲染线程（无 `D3DCREATE_MULTITHREADED`）** ⑥**`AnglesToQuaternion` vs `AngleVectors` 的寄存器反向错误** ⑦**`Bullet_Endpos` 从 7 参数变 10 参数** ⑧**`com_maxfps` 上限补丁只改 MAX 不改 DEFAULT** ⑨**`TCLS_SHAREDMEMEMORY<pid>` 命名空间边界** ⑩**738 个官方 bot 名字的实测来源**

---

## 一、★★★★★ **`DisconnectWitness` —— `cls.state = 0` 的唯一写入点**

### 1.1 ★★★★★ 核心事实（第 15–28 行，逐字）

```
"On **mp_battlecity** the client now reaches **cls.state 10 (ACTIVE)**, acks reliable
 commands, sends button input -- and then **zeroes cls.state about a second later**.
 **Not a Com_Error** (`com_errorMessage` stays empty), **not a fault** (no ClientException),
 and **nothing the server sends accounts for it**. **Six server-side theories died
 against that one second.**"
```

★★★★★ **⇒ 四个排除 + 六个理论死亡：**
```
`cls.state = 10`（ACTIVE）✓
ack 可靠命令 ✓
发送按钮输入 ✓
        ↓
★★★ **约 1 秒后 `cls.state` 归零**
        ↓
★★★ 不是 Com_Error（`com_errorMessage` 空）
★★★ 不是 fault（无 ClientException）
★★★ 服务端发的任何东西都解释不了
        ↓
★★★★★ **"Six server-side theories died against that one second."**
```

### 1.2 ★★★★★ 唯一写入点（第 21–25 行，逐字）

```
"Scanning .text for **every write to cls.state (0x076446B0)** finds **exactly five**,
 and **only ONE stores 0**: the `mov dword ptr [0x076446B0], 0` at **0x0077C343**,
 inside **sub_77C290**. Its **three callers fan out to 97 call sites**, far too many
 to narrow by reading, so **the caller's return address is the answer** and
 **a hook is the only way to read it**."
```

★★★★★ **⇒ 五个精确值：**
```
`cls.state` 绝对地址 = **`0x076446B0`**
对它的写入共 **5 处**,其中**只有 1 处写 0**
写 0 的指令：`mov dword ptr [0x076446B0], 0` @ **`0x0077C343`**
所在函数：**`sub_77C290`**
        ↓
★★★ 它的 **3 个调用者扇出到 97 个调用点** ⇒ 读代码无法收窄
★★★ ⇒ **只有钩子能拿到调用者返回地址**
```

### 1.3 ★★★★★ **为什么钩"写入"而不是"函数入口"**（第 32–44 行，逐字）

```
// **THE WRITE ITSELF, NOT THE FUNCTION ENTRY.** Two reasons, both measured:
//
//  1. Hooking sub_77C290's entry was armed (log: "disconnect witness installed" at
//     **21:09:50**) and the client still went **cls.state 10 -> 0 at 21:12:08**
//     **without the hook firing**. Whatever reaches the write **does not come through
//     the prologue**.
//  2. That prologue is `**55 8B EC 83 E4 F8**` -- push ebp / mov ebp,esp / **AND ESP,-8**.
//     A **five-byte steal cuts `and esp,-8` in half**, so the trampoline would have
//     executed a **truncated instruction**. It was **wrong even where it did fire**.
```

★★★★★ **⇒ 两个独立的实测理由：**
```
① 钩入口已装（**21:09:50**）但**没响**,客户端仍在 **21:12:08** 归零
   ⇒ **到写入的路径不经过函数序言**
② 序言 `55 8B EC 83 E4 F8`（5 字节）⇒ **5 字节窃取会把 `and esp,-8` 切成两半**
   ⇒ 蹦床执行**截断的指令** ⇒ **即使响了也是错的**
```

### 1.4 ★★★★★ 十字节写入的完整编码（第 41–49 行，逐字）

```
// The write is `**C7 05 B0 46 64 07 00 00 00 00**` at 0x0077C343 -- **ten bytes**,
// so a **five-byte jump plus five NOPs** fits with room to spare and **nothing is split**.
// (**My earlier scan printed 0x0077C345 because it reported where the ADDRESS OPERAND
// sits, not where the instruction starts.**)
```

★★★★★ **⇒ 十字节分解：**
```
`C7 05`              ⇒ `mov dword ptr [imm32], imm32`
`B0 46 64 07`        ⇒ 地址 **`0x076446B0`**（小端）
`00 00 00 00`        ⇒ 值 **0**
        ↓
★★★ 总 **10 字节** ⇒ `E9` + rel32（5）+ **5 个 `0x90`**
```

★★★ **⇒ 一个真实的自纠错：早先扫描报 `0x0077C345` 是因为**报了地址操作数的位置**,不是指令起点**。**

### 1.5 ★★★★★ **`Com_Error` 的"空消息"是假读**（第 51–61 行，逐字）

```
// **AND Com_Error, BECAUSE "NO ERROR" MAY HAVE BEEN A FALSE READ.**
//
// `com_errorMessage` was **empty every time** the client left, and that was taken as
// **proof Com_Error never ran**. **It only proves the MESSAGE was empty** -- a Com_Error
// raised with an **empty or unresolved string** reads **exactly the same from outside**,
// and that would **also explain the blank dialog body** seen all evening.
```

★★★★★ **⇒ 一个精确的逻辑陷阱：**
```
`com_errorMessage` 空
        ↓
★★★ 被当成 "Com_Error 从未运行" 的**证明**
        ↓
★★★ 实际只证明**消息是空的**
   ⇒ 用空/未解析字符串 raise 的 Com_Error **从外面看一模一样**
        ↓
★★★ 而且这还能解释**整晚看到的空白对话框**
```

### ★★★ `Com_Error` 的地址与字节（第 62–65 行）

```cpp
ComErrorRva     = **0x000F8350**;    // ⇒ 0x004F8350
ComErrorStolen  = **5**;
ExpectedComError = { **0xE8, 0x7B, 0xF9, 0xFF, 0xFF** };   // ★ E8 rel32 → sub_4F7CD0
```

★★★ **⇒ `E8 7B F9 FF FF` = `call sub_4F7CD0`（rel32 = `0xFFFFF97B` = -1669）。**

### ★★★★★ **相对 call 不能直接复制**（第 59–61 行，逐字）

```
"Five bytes is a clean steal, but **a relative call CANNOT simply be copied to a
 trampoline at a different address: its target is encoded as a delta**. The installer
 **rewrites that delta below**."
```

★★★ **⇒ 蹦床构造（第 430–439 行）：**
```cpp
const auto originalDelta = *(int32_t*)(comError + 1);
auto *destination = comError + ComErrorStolen + originalDelta;   // ★ 先解出目标
tramp[0] = 0xE8;
*(int32_t*)(tramp + 1) = destination - (tramp + 5);              // ★ 再重编码 delta
```

### 1.6 ★★★★★ **configstring 校验器 `sub_514540`（第 125–150 行，逐字）**

```
// sub_514540 is what raises **XBOXLIVE_CANTJOINSESSION as ERR_SERVERDISCONNECT**
// (measured: **com_errorCode = 2** written from **sub_4F82E0+0x11F**, caller frame
// **sub_514540+0xA5**). Decoded, it is a **per-configstring check**:
//
//     mov  ebx, [ebp+8]            <- a **CONFIGSTRING INDEX**
//     cmp  ebx, **0x31D9**         range check, else a different raise at +0x76
//     mov  al, [ebx + **0x77D8250**]   its **TYPE byte**, in the **CCS block**
//     cmp  al, **0x17** / jae ok
//     cmp  al, **0x15** / je  ok
//     call sub_661610              the **CCS clear**
//     push XBOXLIVE_CANTJOINSESSION / push 2 / raise
```

★★★★★ **⇒ 五个精确值：**
```
`com_errorCode = 2` 由 **`sub_4F82E0+0x11F`** 写入,调用帧 **`sub_514540+0xA5`**
        ↓
★★★ 配置串索引上界 **`0x31D9`**（= **12,761**）
★★★ 类型字节表基址 **`0x77D8250`**（**CCS 块**）
★★★ 接受：**`type == 0x15`** 或 **`type >= 0x17`**
★★★ 拒绝 ⇒ `call sub_661610`（**CCS 清除**）⇒ raise
```

★★★ **⇒ 判定逻辑：**
```
`0x15` ⇒ 通过
`>= 0x17` ⇒ 通过
`0x16` ⇒ **拒绝**
`< 0x15` ⇒ **拒绝**
```

### ★★★★★ **dmz loot band 已被排除**（第 140–142 行，逐字）

```
"So it rejects **ONE configstring by index**. Logging that index **names it outright** --
 far better than guessing which band is at fault. The **dmz loot band** was the obvious
 suspect and has **already been RULED OUT** by running with `OLMOD_DMZ_LOOT_BAND=0`:
 **the kick happened anyway, at 02:50:12**."
```

### ★★★ 序言是 6 字节（第 144–150 行）

```cpp
ValidatorRva    = **0x00114540**;
ValidatorStolen = **6**;
ExpectedValidator = { **0x55, 0x8B, 0xEC, 0x83, 0xEC, 0x10** };   // push ebp / mov ebp,esp / sub esp,0x10
```
★★★ **⇒ "**Five would cut `sub esp,0x10` in half, the same mistake made on sub_77C290 earlier tonight.**"**

### 1.7 ★★★★★ **硬件断点：两次软件钩子都空**（第 200–213 行，逐字）

```
// **A HARDWARE WATCHPOINT, BECAUSE BOTH SOFTWARE HOOKS CAME BACK EMPTY.**
//
// Measured **2026-09-04**: the hook on **the only `mov dword [cls.state], 0`** in the
// image was armed and **never fired**; the hook on **Com_Error** was armed and **never
// fired**; there is **no ClientException and no match end** -- and cls.state **still goes
// 10 -> 0** about a second after the client enters.
// **A value that changes with no instruction touching its address is a value being
// wiped as part of something larger: a memset over the whole `cls` struct, which
// references no address a scanner can find.**
//
// **The CPU does not care how the write happens.** DR0 + DR7 make it trap on the
// **ADDRESS**, so a **`rep stosd` inside memset is caught exactly like a `mov`.**
```

★★★★★ **⇒ 一个关键的推理跳跃：**
```
唯一写 0 的指令被钩了但**没响**
Com_Error 被钩了但**没响**
无 ClientException、无比赛结束
        ↓
★★★ 而 `cls.state` 仍然 10 → 0
        ↓
★★★★★ ⇒ **"一个值在没有任何指令触碰它地址的情况下改变,
   只能是它作为更大对象的一部分被擦除：`memset` 整个 `cls` 结构体"**
   ⇒ **`memset` 不引用任何扫描器能找到的地址**
        ↓
★★★ ⇒ **CPU 不在乎写入怎么发生** ⇒ 硬件断点按**地址**陷阱
   ⇒ **`rep stosd` 和 `mov` 一样被捕获**
```

### ★★★★★ **DR0 + DR1 双断点**（第 252–265 行，逐字）

```cpp
context.Dr0 = target;                                       // ★ cls.state 0x076446B0
context.Dr1 = module + (0x033E7904 - 0x00400000);           // ★ com_errorCode 0x033E7904
context.Dr7 = (context.Dr7 & ~0xFF000F) | 0x1 | 0x4 |
              (0x1 << 16) | (0x3 << 18) |                   // ★ DR0: rw=01, len=11
              (0x1 << 20) | (0x3 << 22);                    // ★ DR1: rw=01, len=11
```

★★★ **⇒ DR7 位域：**
```
`bit0`  = **L0**（DR0 本地启用）
`bit2`  = **L2**（DR1 本地启用）
`bit16-17` = DR0 **rw = 01**（写）
`bit18-19` = DR0 **len = 11**（4 字节）
`bit20-21` = DR1 **rw = 01**
`bit22-23` = DR1 **len = 11**
        ↓
★★★ 掩码 `~0xFF000F` ⇒ 清 `bit0-3` + `bit16-23`
```

### ★★★★★ `com_errorCode` 的第二断点理由（第 253–258 行，逐字）

```
// AND **DR1 on com_errorCode**. **Only one instruction in the image writes it**
// (**sub_4F7DA0+0x21E, `= ecx`**) and that is the **drop handler storing the code it was
// already given** -- so **whoever SETS it to 2 does so through a pointer**, exactly as
// cls.state was wiped through one. The same hardware trap answers the same shape of question.
```

★★★ **⇒ `com_errorCode` 绝对地址 = **`0x033E7904`**。**
**⇒ 唯一写入者 `sub_4F7DA0+0x21E`（`= ecx`）只是**存储已给的值** ⇒ 设成 2 的另有其人（经指针）。**

### ★★★★★ **不是一次性断点**（第 296–303 行，逐字）

```
// **NOT ONE-SHOT.** The first attempt logged **once** and spent itself on a **routine
// write at 23:01:29** -- **ninety seconds BEFORE the client entered the match at
// 23:02:57** -- so **the transition that matters was never seen**. cls.state is written
// **on every rung of the connect ladder**; the interesting one is **late and writes 0**.
```

★★★★★ **⇒ 三个精确时刻：**
```
**23:01:29** ⇒ 一次例行写入（**一次性的钩子在这里用掉了**）
**23:02:57** ⇒ 客户端真正进入比赛
        ↓
★★★ 差 **90 秒** ⇒ **真正要看的转换从未被看到**
```

★★★ **⇒ 修复：**
```cpp
static volatile long reported = 0;
if (InterlockedIncrement(&reported) <= **24**) { ... }     // ★ 上限 24 次
```
★★★ **⇒ 且**打印新值**（第 302–303 行逐字）："a debug write breakpoint traps **AFTER**
the store, so **the value at the address is what was just written**. **`= 0` after the
client has entered is the one to read**."**

### ★★★ 两个断点的 Dr6 分派（第 289–294 行）

```cpp
const auto which = pointers->ContextRecord->Dr6 & 0x3;   // ★ bit0=DR0, bit1=DR1
if (which == 0) return EXCEPTION_CONTINUE_SEARCH;
const auto isErrorCode = (which & 0x2) != 0;
pointers->ContextRecord->Dr6 = 0;                        // ★ 清 Dr6
```

### ★★★ 日志格式（第 316–327 行）

```
"%s = %u WRITTEN by the instruction before 0x%08X (module+0x%X)
 -- resolve with Tools/olfinal/xrefs.py; caller frame [ebp+4]=0x%08X"
```

### ★★★★★ **一次真实的地址手写错误**（第 218–221 行，逐字）

```
// cls.state is 0x076446B0 absolute against a 0x400000 image base, so **0x072446B0** from
// the module. **Derived from the constant rather than typed as a second literal**: the
// first attempt **hand-wrote 0x036446B0**, armed on **the wrong address entirely**, and
// duly caught **an unrelated write (0x03A446B0 in the log)**.
```

★★★ **⇒ 三个值：**
```
正确：`0x076446B0 - 0x400000` = **`0x072446B0`**
手写错误：**`0x036446B0`**
实际捕获的无关写入：**`0x03A446B0`**
```

### ★★★ **先装软件钩子再装硬件断点**（第 517–520 行，逐字）

```
"**The watchpoint last**: it is **the one that cannot be evaded**, and it is armed
 **after the software hooks so their own writes cannot trip it**."
```

### ★★★ `installDisconnectWitness` 的六个步骤

```
① 检查 `OLMOD_DISCONNECT_WITNESS == '1'`（**必须首字符 '1'**）
② 已装 ⇒ `AlreadyInstalled`
③ PE 校验（DOS/NT 签名 + `ClsStateWriteRva + StolenSize < SizeOfImage`）
④ **字节校验**（`std::equal` 10 字节）
⑤ 装 `cls.state` 钩子 + `Com_Error` 钩子（独立校验）+ validator 钩子（独立校验）
⑥ 最后装 VEH + 硬件断点
```

### ★★★ `UnexpectedBytes` 的完整错误消息（第 531–533 行）

```cpp
case DisconnectWitnessResult::UnexpectedBytes:
    return "UNEXPECTED BYTES -- 0x0077C343 is not this build's cls.state=0 "
           "write, nothing was written";
```

---

## 二、★★★★★ **`ClientRenderFrameHook` —— 为什么必须是渲染线程**

### 2.1 ★★★★★ 完整的线程测量（第 3–18 行，逐字）

```
// **WHY A SECOND FRAME HOOK.** ol-mod already hooks **Com_Frame** (`FrameHook.cpp`), and
// that is **the right place for game-server work**. It is **the WRONG place for a
// Direct3D call**, and the client says so outright:
//
//     device **BehaviorFlags   0x42**   **FPU_PRESERVE | HARDWARE_VERTEXPROCESSING**
//                                   - **no D3DCREATE_MULTITHREADED**
//     thread **16016**           Com_Frame **0x4FEA20**               **923 calls / 5s**
//     thread **43208**           sub_BE21F0 **0xBE21F0**              **923 calls / 5s**
//                            and every BeginScene, Clear and SetRenderTarget
//
// Measured **2026-09-09**. The two run in **exact lockstep**, **one render frame per
// Com_Frame**, on **DIFFERENT threads**. **Without D3DCREATE_MULTITHREADED every call on
// the device has to come from the thread that made it**, so an upload driven from the
// Com_Frame callback would be **calling the device off-thread**.
```

★★★★★ **⇒ 六个精确值：**
```
`BehaviorFlags = **0x42**` = **`FPU_PRESERVE`(0x02) | `HARDWARE_VERTEXPROCESSING`(0x40)**
        ↓
★★★ **无 `D3DCREATE_MULTITHREADED`（0x04）**
        ↓
★★★ 线程 **16016**：`Com_Frame` @ **`0x4FEA20`** ⇒ **923 次 / 5 秒**
★★★ 线程 **43208**：`sub_BE21F0` @ **`0xBE21F0`** ⇒ **923 次 / 5 秒**
        ↓
★★★★★ ⇒ **完全同步（一次 Com_Frame 对应一帧渲染）,但在不同线程上**
```

### 2.2 ★★★★★ 钩子站点（第 20–33 行，逐字）

```
// `sub_BE21F0` is the render backend's per-frame function; at **+0x1E** it calls
// `sub_BE2150`, which is what calls **BeginScene**:
//
//     00BE220B  50              push eax
//     00BE220C  8B D8           mov  ebx, eax
//     00BE220E  **E8 3D FF FF FF**  call sub_BE2150     ; <- the five bytes replaced
//     00BE2213  83 C4 04        add  esp, 4         ; **CALLER cleanup, cdecl**
```

★★★ **⇒ 三个精确值：**
```
调用点 RVA = **`0x7E220E`**（绝对 **`0x00BE220E`**）
目标 RVA   = **`0x7E2150`**（绝对 **`0x00BE2150`**）
原始字节   = **`E8 3D FF FF FF`**（rel32 = `0xFFFFFF3D` = **-195**）
```

### ★★★★★ **尾部跳转 ⇒ 约定无关**（第 31–33 行，逐字）

```
"The replacement **runs the pump and then TAIL-JUMPS to sub_BE2150 with the stack
 untouched**, so the original's own `retn` returns straight to the call site. **That makes
 the hook convention-agnostic - it never has to know how many arguments sub_BE2150 takes.**"
```

★★★★★ **⇒ 一个精妙的设计：**
```
替换体：**跑泵** ⇒ **尾跳**到 `sub_BE2150`（**栈不动**）
        ↓
★★★ ⇒ 原函数的 `retn` **直接返回到调用点**
★★★ ⇒ **钩子不需要知道 `sub_BE2150` 有几个参数**
```

### ★★★★★ **Fiber 上下文**（第 37–43 行，逐字）

```
// **THE FIBER CONTEXT.** `sub_BE7470` opens with `**sub_67C170(1, sub_BE0900)**`, a
// **fiber switch rather than a thread hop**. It **returns immediately when the caller is
// already on context 1**, and otherwise **yields until `sub_BE0900` is true**.
// Measured from the render frame, `**sub_67C080()`** - the same slot computation
// sub_67C170 uses - **returns 1**, and `sub_BE0900` is `**sub_67CCE0() || sub_67C080() == 1**`,
// so the predicate is **ALREADY satisfied** there. The pump reads the slot anyway and
// **refuses if it is not 1**, because **the failure mode of guessing is `Error("1190")`**.
```

★★★★★ **⇒ 四个精确值：**
```
`sub_BE7470` 开头：**`sub_67C170(1, sub_BE0900)`** ⇒ **fiber 切换,不是线程跳转**
槽位计算：**`sub_67C080()`** ⇒ 渲染帧里返回 **1**
谓词：`sub_BE0900 = **`sub_67CCE0() || sub_67C080() == 1`**
        ↓
★★★ ⇒ **在渲染帧里谓词已满足**
★★★ 但泵仍**读槽位并在不是 1 时拒绝** ⇒ **猜错的失败模式是 `Error("1190")`**
```

### ★★★★★ **已证明的完整链**（第 45–53 行，逐字）

```
// **PROVEN.** On **2026-09-09** this exact sequence -- **staged blob, sub_BE7470 from
// inside a render-frame callback, then DB_LinkXAssetEntry(10)** -- published **seven PPSh
// images** into a live client. `image+0` went from the **load-def pointer** to a real
// **IDirect3DTexture9 whose vtable (0x6c6f1438)** is **byte-identical** to the one every
// shipped image carries, the **load def relocated to +0x2C**, **category went 3 -> 11**
// (the **+8** the staging path adds), all **52 header bytes** survived the link, and the
// **XAsset entry table found each name afterwards**. That run was driven through
// **Frida** (`tools/runtime/CodolForgeImageProbe.py`) because it needed no rebuild;
// **THIS code is the same sequence in the DLL and has not itself been run yet.**
```

★★★★★ **⇒ 七个精确事实：**
```
① 顺序：**staged blob ⇒ `sub_BE7470`（渲染帧回调内）⇒ `DB_LinkXAssetEntry(10)`**
② 发布 **7 个 PPSh 图像**
③ `image+0`：**load-def 指针** → **真正的 `IDirect3DTexture9`**
④ 纹理 vtable = **`0x6c6f1438`**（**与所有出厂图像逐字节相同**）
⑤ load def 重定位到 **`+0x2C`**
⑥ category **3 → 11**（**+8** 是 staging 路径加的）
⑦ **52 字节头全部存活**,XAsset 条目表事后能找到每个名字
        ↓
★★★ 通过 **Frida**（`tools/runtime/CodolForgeImageProbe.py`）驱动
★★★ **"THIS code is the same sequence in the DLL and has not itself been run yet."**
```

### ★★★ 五个 RVA（第 192–198 行）

```cpp
RenderFrameCallSiteRva  = **0x7E220E**;   // 0x00BE220E
RenderFrameTargetRva    = **0x7E2150**;   // 0x00BE2150
ImageUploadRva          = **0x7E7470**;   // 0x00BE7470  (sub_BE7470)
FiberSlotRva            = **0x27C080**;   // 0x0067C080  (sub_67C080)
LoadForRendererDvarRva  = **0xA899CC**;   // 0x00E899CC
```
★★★ **⇒ 第 5 条的注释（第 197 行）："`sub_BE7470` **does nothing at all unless `*(dvar + 12)` is non-zero**."**

### ★★★ 八个 `ForgeImageUploadStatus`

```cpp
Queued / WrongFiberSlot / RendererClosed / UploadFaulted /
NoTexture / LinkFaulted / LinkRefused / Published
```
★★★ **⇒ 四个注释：**
```
`WrongFiberSlot`  ⇒ "the render frame was **not on slot 1 after all**"
`RendererClosed`  ⇒ "the **dvar sub_BE7470 gates on reads zero**"
`NoTexture`       ⇒ "sub_BE7470 returned but **image+0 is still null**"
```

### ★★★★★ **为什么必须从进程内发布**（第 137–150 行，逐字）

```
// **WHY THIS EXISTS.** Publishing from an injected thread **works and was proven asset
// type by asset type**, but **it does not SURVIVE**: **a zone transition removes Material,
// GfxImage and XAnimParts entries and rewrites XModels as the missing-model default**,
// and **a name that already exists cannot be re-pointed by linking**. **Every run from
// outside therefore races the next map load.**
//
// Publishing from in here does not have that problem, because it can happen **AFTER the
// zone the client is about to run** -- **the render-frame hook is the first thing that
// runs every frame**, and by the time it does, **the map's own assets are already loaded**.
//
// **ORDER MATTERS** and is enforced by phase: **images have to exist before a material
// can bind them, and materials before a model can name them**. The pump does **one image
// per frame**, then the materials, then the models.
```

★★★★★ **⇒ 三个精确约束：**
```
① zone 转换会**移除 Material / GfxImage / XAnimParts**,并把 XModels **重写成缺失模型默认值**
② **已存在的名字无法通过链接重新指向**
③ 所以从外部发布**每轮都在和下一次地图加载赛跑**
        ↓
★★★ ⇒ 从**渲染帧钩子**发布 ⇒ 时机在 **zone 加载之后**
        ↓
★★★ 阶段顺序：**Images ⇒ Materials ⇒ Models**（**每帧一个图像**）
```

### ★★★ 六个 `ForgeChainPhase`

```cpp
Idle / Images / Materials / Models / Done / Failed
```

### ★★★ 纹理语义按名字后缀（第 121–123 行，逐字）

```
"The semantic is taken from the name's suffix - **`_c` colour 2, `_n` normal 5, `_s` specular 8** -
 which is what the **shipped MaterialTextureDefs** carry, and what the **PPSh's own materials**
 expect of these six names."
```
★★★ **⇒ 三个精确值：`_c` ⇒ **2** / `_n` ⇒ **5** / `_s` ⇒ **8**。**

### ★★★ 克隆源（第 155–158 行）

```
"`mc/mtl_t6_wpn_pda` carries **colorMap, normalMap and specularMap**, which is what
 the **PPSh's two weapon materials** need."
```

### ★★★ 内存所有权（第 105–107 行，逐字）

```
"The image is **MOVED and kept alive for the life of the process**: the engine copies
 the **52-byte header** but **keeps the pointers inside it**, so **the storage can never
 be released**."
```

### ★★★ 拒绝而非静默挂起（第 109–110 行）

```
"Returns **false** when the hook is **not installed** -- **queueing against a hook that
 will never run is a silent hang, not a deferral**."
```

### ★★ 默认关

```cpp
// DEFAULT OFF, set **CODOL_IMAGE_UPLOAD_HOOK=1** to enable.
```
★ **⇒ 第 5 个 `CODOL_*` 变量。**

---

## 三、★★★★★ **`ClientProcessPatches.hpp` —— 十六个补丁面**

### 3.1 ★★★★★ **`config_mp.cfg` 的明文补丁**（第 51–74 行，逐字）

```
// **WRITE AND READ players/config_mp.cfg AS PLAIN TEXT.**
//
// The game **ALREADY writes it as text and then re-encrypts it in a second pass**.
// **Com_WriteConfigToFile 0x004FDAF0** prints the header, unbindall, the binds and the
// dvars into the file, closes it, and **only then** does
//
//     if (!strcmp(name, "config_mp.cfg")) { read back; **sub_7BC570(name, len, size)**;
//                                           write back; }
//
// and the read path **0x004F30C0** is the mirror -- **the SAME sub_7BC570**, so
// **the cipher is symmetric**, and it is **keyed on the FILE NAME**, which is why
// `settings_c.zip.iw4` needs its **own key**. Both gates are the identical inlined strcmp
// ending in **one conditional jump**, so turning "jump when the name is NOT config_mp.cfg"
// into an **unconditional jump** skips the second pass on write and the decrypt on read:
//
//     **0x004FDBCC   75 6E  jnz  ->  EB 6E**     never re-encrypt what was just written
//     **0x004F3119   75 34  jnz  ->  EB 34**     never decrypt what is about to be run
```

★★★★★ **⇒ 六个精确值：**
```
写：**`Com_WriteConfigToFile 0x004FDAF0`**（先写明文,再加密）
加密：**`sub_7BC570(name, len, size)`**
读：**`0x004F30C0`**（**同一个 `sub_7BC570`** ⇒ **对称密码**）
        ↓
★★★ 密钥是 **FILE NAME** ⇒ `settings_c.zip.iw4` **需要自己的密钥**
        ↓
★★★ 两个补丁点：
   **`0x004FDBCC`**：`75 6E`（`jnz`）→ **`EB 6E`**（`jmp`）⇒ **写时不重加密**
   **`0x004F3119`**：`75 34`（`jnz`）→ **`EB 34`**（`jmp`）⇒ **读时不解密**
```

### ★★★★★ **迁移是优雅的**（第 69–72 行，逐字）

```
// **MIGRATION IS GRACEFUL AND NEEDS NO FILE DELETED.** An existing ENCRYPTED config,
// read without decryption, **fails the "starts with //" validation at 0x004F3144** and
// **is ignored**; the game then **writes a fresh plaintext one on exit**.
```

★★★ **⇒ 第三个地址：**`0x004F3144` = "starts with `//`" 校验点。**

### ★★★★★ **`com_maxfps` 上限补丁**（第 88–111 行，逐字）

```
// **Com_InitDvars registers it at 0x004FC400 as**
//     Dvar_RegisterInt("com_maxfps", value=**200**, min=**0**, MAX=**200**,
//                      flags=**ARCHIVE**, desc)
// so **200 is not a default a player can raise -- it is the dvar's own upper bound**,
// and any higher value **clamps back down on set AND on config load**. That is why the
// graphics menu's "uncapped" writes **200** and why **~186-190 is where everyone lands**:
// the limiter is **1000/maxfps in INTEGER milliseconds**, so **200 asks for 5 ms** and
// **Sleep(1) rounding makes it about 5.3**.
//
// This rewrites the imm32 of the **`push 0C8h` that supplies MAX (0x004FC408)**, leaving
// the **DEFAULT push at 0x004FC40F alone** -- so **nothing changes for anyone who never
// sets the dvar**, and **a value that is set now survives a config round-trip** instead
// of clamping.
```

★★★★★ **⇒ 六个精确值：**
```
注册：`Dvar_RegisterInt("com_maxfps", value=**200**, min=**0**, MAX=**200**, flags=**ARCHIVE**)`
        ↓
★★★ **200 是 dvar 自己的上界**,不是玩家能提高的默认值
★★★ 更高值在 **set 时和 config 加载时**都会钳回
        ↓
★★★ 补丁只改 **MAX 的 `push 0C8h`（`0x004FC408`）**
★★★ **保留 DEFAULT 的 `push`（`0x004FC40F`）**
        ↓
★★★ ⇒ **从未设过 dvar 的人毫无变化**；设过的值**能挺过 config 往返**
```

### ★★★★★ **天花板不是免费的**（第 106–110 行，逐字）

```
// **AND THE CEILING IS NOT FREE ABOVE ~320.** The client makes **one usercmd per rendered
// frame**, so **fps/10 of them arrive per 100 ms server frame** against a queue of
// **PendingUserCmdCapacity**: measured **2026-09-06**, **com_maxfps 0 gave 490 fps**,
// **pending sat at 32** and **cmdAge reached 268 ms**, and **the player called it
// unbelievably laggy**.
```

★★★★★ **⇒ 四个精确值：**
```
`com_maxfps 0` ⇒ **490 fps**
`pending` 卡在 **32**
`cmdAge` 达到 **268 ms**
        ↓
★★★ ⇒ 玩家评价："**unbelievably laggy**"
★★★ ⇒ 阈值："**above ~320**" 不免费
```

### ★★★★★ **`TCLS_SHAREDMEMEMORY<pid>` 的命名空间边界**（第 126–146 行，逐字）

```
// **TenProxy opens that name during this process's own startup and dies at [100] if it
// cannot.** **SampleLauncher creates it from ANOTHER process**, which **works on Windows
// and was measured NOT to work under Wine on 2026-09-05**: the mapping existed **twice
// over** -- pre-published **across a window of pids** AND published again on discovery,
// **pid 352 inside the window 276..2320** -- and **TenProxy still got
// `OpenFileMapping ... fail! Error code = 2`**.
// **A name that exists and cannot be opened from the target process is a namespace
// boundary, and no amount of publishing from outside crosses one.**
```

★★★★★ **⇒ 四个精确值：**
```
TenProxy 打不开就**死在 `[100]`**
Wine 实测：映射**存在两次**（预发布 pid 窗口 + 发现时再发布）
**pid 352** 在窗口 **276..2320** 内
        ↓
★★★ 仍然 **`OpenFileMapping ... fail! Error code = 2`**（`ERROR_FILE_NOT_FOUND`）
        ↓
★★★★★ ⇒ **"一个存在但从目标进程打不开的名字是命名空间边界,
   从外部发布多少都跨不过去。"**
```

### ★★★ 六个 `TclsMappingResult`

```cpp
NotRequested    // OLMOD_TCLS_BLOB 未设 -- Windows 保留 SampleLauncher 的路径
AlreadyVisible  // 另一个进程已有；我们现在**持有句柄**使它不能消失
Published       // 我们在**本进程**创建并从 blob 文件填充
BlobUnreadable  // 文件读不了
CreateFailed    // CreateFileMapping 拒绝
MapFailed       // MapViewOfFile 拒绝
```

### ★★★ 时机论证（第 137–139 行）

```
"The timing is settled too -- this runs where **'client process patch patched' is logged**,
 measured **~30 s before TenProxy asked** on the failing machine."
```

### ★★★ 为什么用文件而非重建（第 141–142 行）

```
"The BLOB comes from a **file** rather than being rebuilt here, because **SampleLauncher
 already knows how to compose it** and **a file crosses any namespace a mapping cannot**."
```

### ★★★★★ **`UnlockAll` 的完整论证**（第 257–274 行，逐字）

```
// **OWN EVERY ITEM, without sending a single extra inventory byte.**
//
// The inventory reply is **capped at 8,460 records by a 512 KB buffer** the client passes
// per task, the catalogue is **21,753 ids**, and **the client does NOT page** -- told
// **19,900 existed while receiving 8,460 it never asked for the rest** (measured
// **2026-09-03**). So **no amount of work on the wire can deliver the catalogue**.
//
// It does not have to. **The store list is not built FROM the inventory array**: the
// client walks **its own item table** and asks an **ownership resolver per entry
// (sub_5E3760, 94 call sites)**. That resolver **already has an "owned without being in
// the inventory" branch**, and the branch is **guarded by a predicate with exactly ONE
// caller -- itself**. **Forcing that predicate true fills the out-record as owned with
// quantity -1**, for every item the inventory did not carry.
//
// **ONE CALLER is why this is the safe place to cut.** The **hash lookup underneath it
// has six callers and returns a RECORD POINTER**, so forcing that would hand callers a
// **wild pointer**; the **list-walk beside it has twenty-three callers** and gates things
// this has no business changing. **This predicate is a bool used in one branch of one
// function.**
```

★★★★★ **⇒ 七个精确值：**
```
inventory 回复上限：**8,460 条**（**512 KB** 缓冲）
目录总量：**21,753 个 id**
        ↓
★★★ **客户端不分页**：告诉它 **19,900** 存在而只收到 **8,460**,它**从不请求其余**
        ↓
★★★ ⇒ **线上再怎么努力也送不完目录**
        ↓
★★★ 解法：商店列表**不是**从 inventory 数组构建的
   ⇒ 客户端走**自己的物品表**,对每项问**所有权解析器 `sub_5E3760`（94 个调用点）**
   ⇒ 该解析器**已有"拥有但不在 inventory 里"的分支**
   ⇒ 该分支由**恰好一个调用者（自己）**守护的谓词控制
   ⇒ **强制该谓词为真 ⇒ out-record 填成 owned + quantity `-1`**
        ↓
★★★★★ **"ONE CALLER is why this is the safe place to cut."**
   ⇒ 下面的 hash 查找有 **6 个调用者且返回记录指针** ⇒ 强制会给出**野指针**
   ⇒ 旁边的 list-walk 有 **23 个调用者** ⇒ 会改到不该改的东西
```

### ★★★ 六个 `MaxFpsCeilingPatchResult` / 七个 `ClientProcessPatchResult`

```cpp
ClientProcessPatchResult: NotRequested / Patched / AlreadyPatched /
                          UnsupportedHost / UnexpectedBytes /
                          UnexpectedTarget / ProtectionFailed   // ★ 7 个
MaxFpsCeilingPatchResult: NotRequested / Patched / AlreadyPatched /
                          UnsupportedHost / UnexpectedBytes / ProtectionFailed  // ★ 6 个
ClientRawInputPatchResult: Patched / AlreadyPatched / UnsupportedHost /
                          UnexpectedBytes / ProtectionFailed   // ★ 5 个（无 NotRequested）
```

### ★★★ 七个"防御性"补丁（第 171–221 行）

| # | 补丁 | 缺陷 |
|---|---|---|
| **1** | `LoopFxNullGuard` | 零售 effect runner **对 FxEffectDef 无空检查就解引用** |
| **2** | `EntityEventWeaponGuard` | **`CG_EntityEvent` 在后来的空检查之前就读 WeaponDef 标志** |
| **3** | `EntityEventRangeGuard` | 默认分支 raise **ERR_DROP** 并用**无效值**索引名字表；表范围 **0..184** |
| **4** | `AmmoLookupWeaponGuard` | 死亡/重生转换时 **weapon 0** ⇒ 返回零弹药 |
| **5** | `WeaponInventoryGuard` | 非零 weapon 索引但 **WeaponDef 不可用** |
| **6** | `UiOperatorResolverGuard` | **20 × 3 × 3** 函数指针表 |
| **7** | `AlphaWeaponGamestate` | **`CL_ParseGamestate` 一次调用清空并重建武器注册表** |

★★★ **⇒ 第 3 条给出精确上界：entity-event id 表 **`0..184`**（185 个）。**
★★★ **⇒ 第 6 条给出精确维度：**`20 × 3 × 3`**。**
★★★ **⇒ 第 7 条的注释（第 158–163 行，逐字）：**
```
"**CL_ParseGamestate clears and rebuilds the client's native weapon registry in one call.**
 Alpha WeaponDefs linked while the player is in the frontend therefore **disappear after
 the last ordinary-weapon pass but before the modular pass resolves strings that refer to
 them**. Redirect **only that second pass's call** so the callback can **restore the
 ordinary alpha definitions at their server-assigned indices first**."
```

### ★★★ 三个 `ClientProcessPatches` 的补丁点

```cpp
patchClientExecutionStateBuffer(image)                    // 执行状态
patchClientRawMouseCallBuffer(image, imageBase, replacement)  // 原始鼠标
patchClientBatteryDisplayBuffer(image, imageBase, replacement) // 电池显示
```

### ★★★ `clientBatteryDisplayDivisor(double multiplier)`

```cpp
int clientBatteryDisplayDivisor(double multiplier);
```
★ **⇒ "Native battery HUD units, with a **safe default before replicated dvars arrive**."**

### ★★★ `UnsignedFastfile` 的边界（第 233–239 行，逐字）

```
"Permit locally repacked OLFinal fastfiles while **retaining the native header, version,
 SHA-256 block checks, zone-name binding and inflate path**. **Only the RSA signature
 verdict is accepted.** Off unless `OLMOD_ALLOW_UNSIGNED_FASTFILES=1` and **pinned to the
 verified 1649370 bytes**."
```
★★★ **⇒ 五项保留 + 一项放开（**仅 RSA 签名判定**）。**

### ★★★ `ForceRecordValidator` 的出处（第 23–25 行，逐字）

```
"`01-docs\30-topics\findings\成果-A生效kind3带候选与D2首次触发及房间不再10秒被踢-20261007-0255.md`
 **§5.2/§9/§11**"
```
★ **⇒ 探针,需 `CODOL_FORCE_RECORD_VALIDATOR=1`。**

---

## 四、★★★★★ **`NativeWeaponBindings.cpp` —— 三个 ABI 错误**

### 4.1 ★★★★★ **`playerState_s` 的 5 个偏移**（第 26–32 行）

```cpp
EFlagsOffset                    = **0x104**;
ViewAnglesOffset                = **0x160**;
LinkEntityOffset                = **0x248**;
CurrentWeaponOffset             = **0x3F8**;
WeaponPositionFractionOffset    = **0x404**;
UnlinkedEntityNum               = **2047**;
TurretViewFlags                 = **0x0C00**;
```

★★★ **⇒ 5 个偏移 + 2 个常量,与报告 126 的 `EFlagsOffset = 0x104`**一致** ✓**

### ★★★★★ **"THIRD file holding playerState_s offsets"**（第 22–25 行，逐字）

```
// CODDIFF(1649370): **THE SAME UNPORTED BLOCK AS NativeWeaponMovementBindings.cpp**
// -- a **THIRD file holding playerState_s offsets**, and **byte-identical to the
// 3.3.3.3 tree's copy of this file**. Same struct, **three files, one of them ported**.
// Values and evidence are stated once, in NativeWeaponMovementBindings.cpp.
```

★★★★★ **⇒ 一个精确的代码卫生问题：**
```
`playerState_s` 的偏移出现在 **3 个文件**里
其中**只有 1 个**移植了（`NativeWeaponMovementBindings.cpp`）
        ↓
★★★ 本文件（`NativeWeaponBindings.cpp`）**与 3.3.3.3 树的副本逐字节相同** ⇒ **未移植**
```

### 4.2 ★★★★★ **`AnglesToQuaternion` vs `AngleVectors`（第 77–90 行，逐字）**

```
// CODDIFF(1649370): **THIS WAS THE WRONG FUNCTION, AND ITS ARGUMENTS WERE BACKWARDS.**
// `AnglesToQuaternionRva` **0x3853E0** is **sub_7853E0**, which **reads its angles
// through ESI and writes FOUR floats through EDX** -- an **angles-to-QUATERNION**,
// **not 3.3.3.3's nine-float AnglesToAxis 0x0062C1A0, which does not exist on this build
// at all**. **With the registers the other way round this read a zeroed axis buffer AS
// the angles and stamped a quaternion over the caller's `fireAngles`**, so **every basis
// it produced was three zero vectors** and **SV_IsWeaponFireBasisValid refused it**.
// Section **73f**.
//
// What 1649370 has is **AngleVectors, sub_767890**: four STACK arguments, **__cdecl**,
// three separate destinations. **Quake-derived engines define AnglesToAxis as AngleVectors
// with the SECOND row inverted**, so this returns the same **(forward, LEFT, up)** the
// callers below already expect.
```

★★★★★ **⇒ 六个精确值：**
```
错误：`AnglesToQuaternionRva` = **`0x3853E0`** = `sub_7853E0`
     ⇒ **ESI 读角度、EDX 写 4 个 float** ⇒ **角度→四元数**
     ⇒ **不是** 3.3.3.3 的九 float `AnglesToAxis` **`0x0062C1A0`**
     ⇒ **该函数在本 build 上根本不存在**
        ↓
★★★ 寄存器反了 ⇒ 把**清零的轴缓冲当成角度**读,把**四元数盖到 `fireAngles` 上**
★★★ ⇒ **每个基向量都是三个零向量** ⇒ `SV_IsWeaponFireBasisValid` **拒绝**
        ↓
★★★ 正解：**`AngleVectors` = `sub_767890`**（**4 个栈参数,`__cdecl`,3 个独立目标**）
★★★ Quake 系引擎：`AnglesToAxis` = `AngleVectors` **第二行取反**
```

### ★★★ 第二行取反的实现（第 122–126 行）

```cpp
for (std::size_t component{3}; component != 6; ++component)
    axis[component] = -axis[component];     // ★ 只取反 [3..5]（第二行 = right）
```

### 4.3 ★★★★★ **`Bullet_Endpos` 从 7 参数变 10 参数**（第 142–170 行，逐字）

```
// CODREF(fire_weapon): 3.3.3.3's **Bullet_Endpos 0x0055AEB0** uses the custom ABI
// **EDI=muzzleTrace, ESI=end**, followed by **seed, spread, dir, forward, right, up and
// maxRange on the stack -- SEVEN**.
//
// CODDIFF(1649370): **sub_592230 READS TEN**, and **the three new ones are all floats
// INSERTED into the middle**. Section **75**.
//
//   **[ebp+08] uint32*  randomSeed**     unchanged
//   **[ebp+0C] float    spread**         unchanged slot
//   **[ebp+10] float    spread**         <- **NEW, a SECOND cone radius**
//   **[ebp+14] float*   direction**      was [ebp+10]
//   **[ebp+18] float    randomMinimum**  <- **NEW**
//   **[ebp+1C] float    randomMaximum**  <- **NEW**
//   **[ebp+20] float*   forward**        was [ebp+14]
//   **[ebp+24] float*   right**          was [ebp+18]
//   **[ebp+28] float*   up**             was [ebp+1C]
//   **[ebp+2C] float    maxRange**       was [ebp+20]
//
// **EDI and ESI are unchanged** -- sub_592230 still does `fld [edi]` into `fstp [esi]`.
// **Carrying the seven-argument form left the callee reading forward, right, up and
// maxRange out of the caller's own frame, and three uninitialised dwords as floats.**
```

★★★★★ **⇒ 完整的栈布局对照表：**

| 偏移 | 1649370 | 3.3.3.3 |
|---|---|---|
| `[ebp+08]` | **`uint32* randomSeed`** | 同 |
| `[ebp+0C]` | **`float spread`** | 同 |
| `[ebp+10]` | ★ **`float spread`（第二个锥半径）** | `float* direction` |
| `[ebp+14]` | **`float* direction`** | `float randomMinimum`？ |
| `[ebp+18]` | ★ **`float randomMinimum`** | `float* forward` |
| `[ebp+1C]` | ★ **`float randomMaximum`** | `float* right` |
| `[ebp+20]` | **`float* forward`** | `float* up` |
| `[ebp+24]` | **`float* right`** | `float maxRange` |
| `[ebp+28]` | **`float* up`** | — |
| `[ebp+2C]` | **`float maxRange`** | — |

★★★ **⇒ 三个新 float **插在中间**,且 `EDI`/`ESI` **不变**（`fld [edi]` → `fstp [esi]`）。**
★★★ **⇒ 用旧的 7 参数形式 ⇒ callee 从**调用者自己的栈帧**里读 forward/right/up/maxRange,**
**并把三个未初始化的 dword 当 float 读。**

### ★★★★★ 恢复的语义（第 165–176 行，逐字）

```
// Recovered from **sub_592230** and its ordinary **CG_FireWeapon call at 0x595DF0**:
// **[0x0C,0x10] are radial angle bounds** and **[0x18,0x1C] are azimuth bounds**.
// The plain-bullet call passes **[0,spread]** and **[0,360]**.
// The helper consumes them as **lo+(hi-lo)*random**. Both **DEG2RAD (0x00DE7FA0)** and
// **LCG scale 1/32768 (0x00DE7BD8)** are **bit-identical to 3.3.3.3's**.
```

★★★★★ **⇒ 六个精确值：**
```
`[0x0C, 0x10]` = **径向角上下界**
`[0x18, 0x1C]` = **方位角上下界**
普通子弹：**`[0, spread]`** 和 **`[0, 360]`**
消费公式：**`lo + (hi - lo) * random`**
`DEG2RAD` = **`0x00DE7FA0`**（与 3.3.3.3 逐位相同）
`LCG scale 1/32768` = **`0x00DE7BD8`**（逐位相同）
```

### ★★★★★ **为什么 `spreadMinimum = 0`**（第 173–176 行，逐字）

```
// **Passing spread for both values collapses the disc to its outer rim and makes hip
// fire avoid the crosshair centre.**
```
★★★★★ **⇒ 一个精确的游戏手感缺陷：**
```
`radiusAngleMin = radiusAngleMax = spread`
        ↓
★★★ ⇒ **圆盘塌缩成外环** ⇒ **腰射避开准星中心**
```

### ★★★ 十参数的实际汇编（第 182–202 行）

```cpp
__asm
{
    push edi
    push esi
    push maxRange          // [esp+2C]
    push up                // [esp+28]
    push right             // [esp+24]
    push forward           // [esp+20]
    push randomMaximum     // [esp+1C]
    push randomMinimum     // [esp+18]
    push direction         // [esp+14]
    push spread            // [esp+10]
    push spreadMinimum     // [esp+0C]
    push randomSeed        // [esp+08]
    mov edi, muzzleTrace
    mov esi, end
    call function
    add esp, 40            // ★ 10 个参数 × 4 = 40
    pop esi
    pop edi
}
```

★★★ **⇒ `add esp, 40`（`0x28`）⇒ **10 个栈参数** ⇒ 与 `[ebp+08]`..`[ebp+2C]` **完全对应** ✓**

### ★★★ `getPlayerEyePosition` 的两个前置拒绝（第 254–258 行）

```cpp
// TODO(CODOL): Add server-owned tag/link entity resolution before accepting
// viewlocked or linked player states.
if ((eFlags & TurretViewFlags) != 0 || linkEntity != UnlinkedEntityNum)
    return std::nullopt;
```
★★★ **⇒ 两个拒绝条件：`eFlags & 0x0C00`（炮塔视角）/ `linkEntity != 2047`（已链接）。**

### ★★★ `BG_GetPlayerEyePosition` 的出处（第 241–243 行）

```
"CODOL **BG_GetPlayerEyePosition 0x00414150** owns **origin, view height, bob, lean and
 minimum-height clamping**. Its **-1 linkedEntityContext** is valid **only for the
 unlinked player path**."
```
★★★ **⇒ 五个职责 + `-1` 作为 `linkedEntityContext`。**

### ★★★ `BG_GetSurfacePenetrationDepth`（第 384–421 行）

```cpp
constexpr std::size_t functionRva = **0x02EC00**;      // sub_42EC00
...
const auto penetrationScale = *(const float*)(definition + **3704**);   // 0xE78
auto lossScale = *(const float*)(definition + **3708**);                // 0xE7C
if (lossScale == 0.0f) lossScale = 1.0f;
depth = (float)surfaceFactor * penetrationScale / lossScale;
```

★★★★★ **⇒ 四个精确值：**
```
`BG_GetSurfacePenetrationDepth` = **`sub_42EC00`**
`WeaponDef + 3704`（**`0xE78`**）= **穿透系数**
`WeaponDef + 3708`（**`0xE7C`**）= **厚度损失系数**（**0 表示 1.0**）
公式：**`depth = surfaceFactor * penetrationScale / lossScale`**
```

★★★ **⇒ 且注释（第 409–412 行）：**
```
"**OLFinal sub_5923C0 multiplies the material table by WeaponDef+0xE78, then scales
 thickness loss by +0xE7C (zero means 1.0).** Return the equivalent effective depth so
 the source loop can retain **`damage -= thickness / depth`**."
```

### ★★★ `WeaponDefinitionsRva` 的槽查找（第 400–403 行）

```cpp
const auto *slot = reinterpret_cast<const uint8_t *const *>(module_ + WeaponDefinitionsRva) + weaponAssetIndex;
const auto *definition = *slot;
if (definition) { ... }
```

### ★★★ 上界校验（第 388–391 行）

```cpp
if (!valid() || !weaponAssetIndex ||
    weaponAssetIndex > MaximumWeaponAssetIndex ||
    !surfaceType || surfaceType >= BulletSurfaceTypeCount ||
    gameThreadId_ != GetCurrentThreadId())
    return std::nullopt;
```

### ★★★ 结果校验（第 428–431 行）

```cpp
return completed && std::isfinite(depth) && depth >= 0.0f &&
        depth <= MaximumWeaponDamageRange
    ? std::optional{ depth } : std::nullopt;
```

### ★★★ 副手武器的两个偏移

```cpp
const auto currentWeapon = readNativeValue<std::uint32_t>(
    playerState, offhand ? **0x3E4** : CurrentWeaponOffset);
```
★★★ **⇒ 注释（第 291–292 行，逐字）：**
```
"CODREF(1649370): **offhand admission 429E10 requires WeaponDef type1**.
 **A grenade is selected at +3E4 while +3F8 still names the held gun.**"
```
★★★★★ **⇒ 两个精确值：**
```
`ps + 0x3E4` = **选中的手雷**（副手）
`ps + 0x3F8` = **仍在手里的枪**（主手）
```

### ★★★ `right` 取反（第 348–351 行）

```cpp
// CODDIFF(fire_weapon): CODOL **AnglesToAxis 0x0062C1A0 stores the left axis in row one**,
// while **weaponParms/Bullet_Endpos owns right**.
.right = { -axis[3], -axis[4], -axis[5] },
```

---

## 五、★★★★★ **`codol_bot_names.hpp` —— 738 个名字的实测来源**

### 5.1 ★★★★★ 完整来源（第 5–20 行，逐字）

```
// `codol_bot_names.hpp` -- the **21-generation client's own bot display-name pool**.
//
// Read out of the **LIVE client process** (read-only: **OpenProcess + ReadProcessMemory**),
// ticket **20261011-27000**. The pool is **one NUL-separated UTF-8 table** in the client's
// asset heap at **0x4A2E7A78..0x4A2EA1F5** (**9853 bytes**) and holds **738 names**.
// **Nothing here is invented and nothing is translated**: the bytes below are the
// **client's own shipping strings, in the client's own order**.
//
// **Cross-check that fixed the origin**: the **2697/Antia roster (bot_roster.json, 10000
// entries) does NOT contain these names** -- **that pool belongs to another generation**.
// The **seven names the operator read off the running 21-generation game**
// (**山枫恋人 / 电侠伟 / 无极剑士 / 红莲之焰 / 飘渺纹龙 / GIR魔法 / 红玻璃戒指**)
// are all present here, **at indices 22/29/234/251/279/717/729**.
//
// **Consumers**: `Appmain.cpp`'s **botDisplayName()** cycles this pool by **slot index**;
// `OLMOD_BOT_NAMES="A,B,C"` overrides the whole pool at runtime.
```

★★★★★ **⇒ 六个精确值：**
```
来源：**活客户端进程**（`OpenProcess` + `ReadProcessMemory`,只读）
ticket：**20261011-27000**
地址范围：**`0x4A2E7A78 .. 0x4A2EA1F5`**
大小：**9853 字节**
名字数：**738**
格式：**NUL 分隔的 UTF-8 表**
```

### ★★★★★ **七个验证索引**

| 名字 | 索引 |
|---|---|
| **山枫恋人** | **22** |
| **电侠伟** | **29** |
| **无极剑士** | **234** |
| **红莲之焰** | **251** |
| **飘渺纹龙** | **279** |
| **GIR魔法** | **717** |
| **红玻璃戒指** | **729** |

★★★ **⇒ 七个名字全部在表里,且索引精确。**
**⇒ 我已在读到的文件里核对：`山枫恋人` 在第 738 行（1-based）= 索引 737？**

**★★ 待核对：** 文件内 `山枫恋人` 出现在列表第 **718** 项（1-based 行 738 减去 20 行头）。
按 0-based 索引应为 **717**。而文档说 **22**。

★★★ **⇒ 这是一个**需要标注的差异**：注释里的索引 22/29/234/251/279/717/729 与我在
文件里看到的位置不一致 ⇒ **可能注释用的是另一套编号,或注释有误** ⇒ **记录为待核对项。**

（实际核对：文件第 43 行是 `"无极剑士"`，列表从第 22 行开始 ⇒ 1-based 列表索引 = 43-22+1 = **22**；
文档说 `无极剑士` 在 **234**。第 300 行 `"电侠伟"` ⇒ 索引 = 300-22+1 = **279**；文档说 **29**。
第 255 行 `"飘渺纹龙"` ⇒ 索引 = 255-22+1 = **234**；文档说 **279**。
⇒ **三个值互换了位置** ⇒ 文档索引与文件顺序**不对应** ⇒ 明确记录。）

### ★★★ 三个消费者

```cpp
Appmain.cpp 的 botDisplayName()  ⇒ 按 **slot index** 循环
OLMOD_BOT_NAMES="A,B,C"          ⇒ **运行时覆盖整个池**
```

### ★★★ 名字的构成特征（实测观察）

★★★ **⇒ 738 个名字全部是 **2003–2010 年代中国网游风格**的昵称：**
```
高频前缀：冒险(×11)、天使(×9)、孤独(×9)、爱(×40+)、龙(×20+)、魔法(×15+)、
        冰(×20+)、帅(×12)、狂(×12)、霸(×6)
高频后缀：宝贝、乖乖、宝宝、公主、法师、侠客、战神
        ↓
★★★ 含数字的：**`孙悟空2003`** / **`覆雨长空1`** / **`刀嘣战士3`**
含拉丁字母的：**`Jo0乖乖猪`** / **`ICE红茶`** / **`GIR魔法`** / **`best直觉`** /
             **`Like睡觉`** / **`天梦BOY`** / **`九江Feel`** / **`冒险ADM`** /
             **`布宝VS大头`** / **`风Vs云`** / **`思觉失调A`** / **`无与伦比之JA`**
含繁体/异体字的：**`名门緈諨`** / **`訫鎻已开`** / **`溡尙颖儿`** / **`霸气十足`** /
                **`悃了冰`** / **`飘摇的枼子`** / **`莣誋濄佉`** / **`咾癙嫒汏洣`** /
                **`栤鱩法师`** / **`瞀熃膴`** / **`龟趺身功`** / **`灭ㄝ战鈫`** /
                **`风情ㄉ万种`** / **`幻影の降龙`** / **`真心爱谁ぃ`** / **`沩你垨銗`**
```

★★★ **⇒ 三个特殊字符类别：**
```
注音符号：**`ㄉ`**（`风情ㄉ万种`）、**`ㄝ`**（`灭ㄝ战鈫`）
日文假名：**`の`**（`幻影の降龙`）
平假名小字：**`ぃ`**（`真心爱谁ぃ`）
        ↓
★★★ ⇒ **这些字符在 GBK 编码里占双字节** ⇒ 与报告 125 的
   `validDisplayName`（允许 `>= 0x20 && != 0x7F`）**兼容** ✓
```

★★ **⇒ 且名字里**没有**任何控制字符、没有超长项（最长 **`小小老鼠爱牙牙`** = 7 字）。**

---

## 六、逐字节证据总表

| # | 项 | 值 |
|---|---|---|
| 1 | ★★★★★ **`cls.state` 绝对地址** | **`0x076446B0`**（模块内 `0x072446B0`） |
| 2 | ★★★★★ **唯一写 0 的指令** | `mov dword ptr [0x076446B0], 0` @ **`0x0077C343`**，在 **`sub_77C290`** 内 |
| 3 | ★★★ 写入总数 | 对 `cls.state` 的写入共 **5 处**,只有 **1 处写 0** |
| 4 | ★★★ 调用扇出 | `sub_77C290` 的 **3 个调用者**扇出到 **97 个调用点** |
| 5 | ★★★★★ **十字节编码** | **`C7 05 B0 46 64 07 00 00 00 00`** |
| 6 | ★★★ 自纠错 | 早先扫描报 `0x0077C345` 是**报了地址操作数位置**,不是指令起点 |
| 7 | ★★★★★ **钩入口失败的实测** | 装于 **21:09:50**,客户端仍在 **21:12:08** 归零,**钩子没响** |
| 8 | ★★★★★ **序言陷阱** | `55 8B EC 83 E4 F8`（**`and esp,-8`**）⇒ 5 字节窃取**切半条指令** |
| 9 | ★★★ **`Com_Error`** | **`0x004F8350`**,字节 **`E8 7B F9 FF FF`**（→ `sub_4F7CD0`） |
| 10 | ★★★★★ **空消息 ≠ 未运行** | `com_errorMessage` 空**只证明消息空**;空字符串 raise 的 Com_Error **从外面一模一样** |
| 11 | ★★★ 相对 call 不能直拷 | 蹦床必须**解出目标再重编码 delta** |
| 12 | ★★★★★ **configstring 校验器** | **`sub_514540`**，`com_errorCode = 2` 由 **`sub_4F82E0+0x11F`** 写,调用帧 **`sub_514540+0xA5`** |
| 13 | ★★★★★ **校验逻辑** | 索引 `< 0x31D9`；类型字节 @ **`0x77D8250`**；**接受 `0x15` 或 `>= 0x17`** |
| 14 | ★★★ 拒绝动作 | `call sub_661610`（**CCS 清除**）⇒ `push XBOXLIVE_CANTJOINSESSION` / `push 2` / raise |
| 15 | ★★★ **dmz loot band 已排除** | `OLMOD_DMZ_LOOT_BAND=0` 后**仍在 02:50:12 被踢** |
| 16 | ★★★ validator 序言 | `55 8B EC 83 EC 10`（**6 字节**）⇒ 5 字节会切半 `sub esp,0x10` |
| 17 | ★★★★★ **两次软件钩子都空** | 2026-09-04：唯一写 0 的钩子**没响**、Com_Error 钩子**没响**、无 ClientException、无比赛结束 |
| 18 | ★★★★★ **硬件断点的推理** | "**值在无指令触碰地址时改变 ⇒ 是作为更大对象一部分被 memset 擦除**" |
| 19 | ★★★★★ **DR0 + DR1** | DR0 = `cls.state`；DR1 = **`com_errorCode 0x033E7904`** |
| 20 | ★★★ DR7 位域 | `bit0`=L0 / `bit2`=L2 / `bit16-17`+`bit20-21`=**01 写** / `bit18-19`+`bit22-23`=**11 4字节** |
| 21 | ★★★ `com_errorCode` 唯一写入者 | **`sub_4F7DA0+0x21E`**（`= ecx`）⇒ 只是存储已给值 ⇒ 设 2 的经指针 |
| 22 | ★★★★★ **不是一次性** | 首次在 **23:01:29** 用掉,而客户端 **23:02:57** 才进图（**差 90 秒**）⇒ 上限 **24 次** |
| 23 | ★★★ 打印新值 | 写断点在**存储之后**陷阱 ⇒ 地址上的值就是刚写的值 ⇒ **`= 0` 是答案** |
| 24 | ★★★ 手写地址错误 | 正确 `0x072446B0`；手写 `0x036446B0`；实际捕获 `0x03A446B0` |
| 25 | ★★★ 顺序 | **先软件钩子,后硬件断点**（避免自己的写触发断点） |
| 26 | ★★★★★ **`BehaviorFlags = 0x42`** | **`FPU_PRESERVE`(0x02) \| `HARDWARE_VERTEXPROCESSING`(0x40)** ⇒ **无 `D3DCREATE_MULTITHREADED`** |
| 27 | ★★★★★ **两个线程** | **16016**：`Com_Frame 0x4FEA20` **923/5s**；**43208**：`sub_BE21F0 0xBE21F0` **923/5s** |
| 28 | ★★★★★ 渲染钩子站点 | 调用点 **`0x7E220E`**、目标 **`0x7E2150`**、字节 **`E8 3D FF FF FF`** |
| 29 | ★★★★★ **尾跳设计** | 跑泵后**尾跳**、**栈不动** ⇒ **约定无关**,不必知道参数个数 |
| 30 | ★★★★★ **Fiber 谓词** | `sub_BE7470` 开头 **`sub_67C170(1, sub_BE0900)`**；槽位 **`sub_67C080()`** 返回 **1**；`sub_BE0900 = sub_67CCE0() \|\| sub_67C080()==1` |
| 31 | ★★★ 猜错的代价 | **`Error("1190")`** |
| 32 | ★★★★★ **已证明的链** | staged blob ⇒ `sub_BE7470` ⇒ `DB_LinkXAssetEntry(10)` ⇒ **7 个 PPSh 图像** |
| 33 | ★★★★ 纹理 vtable | **`0x6c6f1438`**（与所有出厂图像**逐字节相同**） |
| 34 | ★★★ 其它已验证项 | load def → **`+0x2C`**；category **3 → 11**（**+8**）；**52 字节头**全存活 |
| 35 | ★★★ 五个 RVA | `0x7E220E` / `0x7E2150` / `0x7E7470` / `0x27C080` / **`0xA899CC`**（dvar） |
| 36 | ★★★ dvar 门 | "`sub_BE7470` **does nothing at all unless `*(dvar + 12)` is non-zero**" |
| 37 | ★★★★★ **为什么从进程内发布** | zone 转换**移除 Material/GfxImage/XAnimParts**、把 XModels **重写成缺失模型默认值**；**已存在的名字无法重新指向** |
| 38 | ★★★ 阶段顺序 | **Images ⇒ Materials ⇒ Models**（**每帧一个图像**） |
| 39 | ★★★ 纹理语义 | **`_c` ⇒ 2 / `_n` ⇒ 5 / `_s` ⇒ 8** |
| 40 | ★★★ 克隆源 | **`mc/mtl_t6_wpn_pda`**（colorMap + normalMap + specularMap） |
| 41 | ★★★ 内存所有权 | 图像**MOVED 并存活整个进程**（引擎复制 52 字节头但**保留内部指针**） |
| 42 | ★★★★★ **`config_mp.cfg` 明文补丁** | 写 **`0x004FDBCC`** `75 6E`→**`EB 6E`**；读 **`0x004F3119`** `75 34`→**`EB 34`** |
| 43 | ★★★ 三个函数地址 | 写 **`Com_WriteConfigToFile 0x004FDAF0`** / 密码 **`sub_7BC570`** / 读 **`0x004F30C0`** |
| 44 | ★★★ 密码对称且按名 | **同一个 `sub_7BC570`**,**密钥 = FILE NAME** ⇒ `settings_c.zip.iw4` 需自己的密钥 |
| 45 | ★★★ 迁移点 | "starts with `//`" 校验 @ **`0x004F3144`** ⇒ 旧的加密配置**被忽略** ⇒ 退出时写新的明文 |
| 46 | ★★★★★ **`com_maxfps` 注册** | **`0x004FC400`**：default **200** / min **0** / max **200** / flags **ARCHIVE** |
| 47 | ★★★★★ **补丁点** | MAX 的 `push 0C8h` @ **`0x004FC408`**；**保留 DEFAULT 的 push @ `0x004FC40F`** |
| 48 | ★★★★★ **`~320` 的代价** | `com_maxfps 0` ⇒ **490 fps**、**pending 32**、**cmdAge 268 ms** ⇒ **"unbelievably laggy"** |
| 49 | ★★★★★ **TCLS 命名空间边界** | Wine 实测映射存在**两次**（**pid 352 在窗口 276..2320 内**）仍 **`OpenFileMapping ... fail! Error code = 2`** |
| 50 | ★★★ TenProxy 失败点 | 死在 **`[100]`** |
| 51 | ★★★ 时机 | 补丁日志 "client process patch patched" **比 TenProxy 询问早约 30 秒** |
| 52 | ★★★★★ **UnlockAll 的边界** | inventory 上限 **8,460 条**（**512 KB**）/ 目录 **21,753** / 客户端**不分页**（告诉它 **19,900** 也不追问） |
| 53 | ★★★★★ **为什么切在那里** | 谓词**只有一个调用者（自己）**；下面的 hash 查找有 **6 个调用者**且返回**记录指针**；旁边 list-walk 有 **23 个调用者** |
| 54 | ★★★ 强制后的效果 | out-record 填成 **owned + quantity `-1`** |
| 55 | ★★★ entity-event 表范围 | **`0..184`**（185 项） |
| 56 | ★★★ UI 运算符表维度 | **`20 × 3 × 3`** |
| 57 | ★★★ `CL_ParseGamestate` 的时序 | 一次调用**清空并重建**武器注册表 ⇒ alpha WeaponDefs **在普通武器 pass 之后、模块化 pass 之前消失** |
| 58 | ★★★ `UnsignedFastfile` 的五项保留 | header / version / **SHA-256 块校验** / zone-name 绑定 / inflate 路径；**只放开 RSA 签名判定** |
| 59 | ★★★★★ **三个文件持有 `playerState_s` 偏移** | 只有 `NativeWeaponMovementBindings.cpp` **移植了**；本文件**与 3.3.3.3 树副本逐字节相同** |
| 60 | ★★★★★ **`AnglesToQuaternion` 错误** | `0x3853E0` = `sub_7853E0`（**ESI 读角度、EDX 写 4 float**）⇒ **不是** `AnglesToAxis 0x0062C1A0`（**本 build 不存在**） |
| 61 | ★★★★★ **寄存器反了的后果** | 把**清零的轴缓冲当角度**读,把**四元数盖到 `fireAngles`** ⇒ **三个零向量** ⇒ `SV_IsWeaponFireBasisValid` 拒绝 |
| 62 | ★★★ 正解 | **`AngleVectors` = `sub_767890`**（4 个栈参数、`__cdecl`、3 个独立目标）；**第二行取反** ⇒ `(forward, LEFT, up)` |
| 63 | ★★★★★ **`Bullet_Endpos` 7 → 10** | `sub_592230` **读 10 个**；三个新 float **插在中间**；`EDI`/`ESI` **不变** |
| 64 | ★★★★★ 完整栈布局 | `+08` seed / `+0C` spread / **`+10` spread2（新）** / `+14` direction / **`+18` randomMin（新）** / **`+1C` randomMax（新）** / `+20` forward / `+24` right / `+28` up / `+2C` maxRange |
| 65 | ★★★★★ 用旧形式的后果 | callee 从**调用者自己的帧**读 forward/right/up/maxRange，并把**三个未初始化 dword 当 float** |
| 66 | ★★★★★ **角界语义** | `[0x0C,0x10]` = **径向**；`[0x18,0x1C]` = **方位**；普通子弹 **`[0,spread]`** 和 **`[0,360]`** |
| 67 | ★★★ 消费公式 | **`lo + (hi - lo) * random`** |
| 68 | ★★★ 逐位相同的两个 | `DEG2RAD` **`0x00DE7FA0`** / LCG scale **`0x00DE7BD8`** |
| 69 | ★★★★★ **`spreadMinimum = 0` 的理由** | 两个都传 `spread` ⇒ **圆盘塌缩成外环** ⇒ **腰射避开准星中心** |
| 70 | ★★★ `BG_GetPlayerEyePosition` | **`0x00414150`**（origin / view height / bob / lean / 最低高度钳制）；`-1` 只对**未链接**路径有效 |
| 71 | ★★★ 两个拒绝 | `eFlags & 0x0C00`（炮塔）/ `linkEntity != 2047`（已链接） |
| 72 | ★★★★★ **穿透公式** | `sub_42EC00`；`WeaponDef+3704`(**0xE78**) 穿透系数；`+3708`(**0xE7C**) 损失系数（**0⇒1.0**）；`depth = surfaceFactor * pen / loss` |
| 73 | ★★★ 副手两个偏移 | **`ps+0x3E4`** = 选中的手雷；**`ps+0x3F8`** = 仍在手里的枪；`offhand admission 429E10` **要求 WeaponDef type 1** |
| 74 | ★★★ `right` 取反 | CODOL `AnglesToAxis 0x0062C1A0` **把 left 轴存第一行** ⇒ `right = -axis[3..5]` |
| 75 | ★★★★★ **738 个 bot 名字** | 活进程 `OpenProcess`+`ReadProcessMemory`；**`0x4A2E7A78..0x4A2EA1F5`**、**9853 字节**、**738 个**、NUL 分隔 UTF-8 |
| 76 | ★★★★★ **来源交叉验证** | **2697/Antia 名册（10000 条）不含这些名字** ⇒ **属于另一代** |
| 77 | ★★★★ 七个验证索引 | 山枫恋人/电侠伟/无极剑士/红莲之焰/飘渺纹龙/GIR魔法/红玻璃戒指 ⇒ 注释称 **22/29/234/251/279/717/729** |
| 78 | ★★★ **索引待核对** | 我按文件顺序核对：`无极剑士`=**22**、`飘渺纹龙`=**234**、`电侠伟`=**279** ⇒ 注释的三个值**互换了位置** |
| 79 | ★★★ 两个消费者 | `Appmain.cpp` 的 `botDisplayName()`（按 slot index 循环）/ **`OLMOD_BOT_NAMES="A,B,C"`** |
| 80 | ★★★ 字符类别 | 注音 **`ㄉ`/`ㄝ`**、假名 **`の`/`ぃ`** ⇒ **GBK 双字节** ⇒ 与 `validDisplayName` 兼容 |

---

## 七、结论

### 1. ★★★★★ **`cls.state = 0` 的追查经过两次失败才到硬件断点**

```
① 钩唯一写 0 的指令 ⇒ **装了但没响**
② 钩 Com_Error      ⇒ **装了但没响**
        ↓
★★★ 硬件断点（DR0 + DR1）⇒ 按**地址**陷阱 ⇒ `memset`/`rep stosd` 也抓得住
```

### 2. ★★★★★ **"空消息"不等于"没运行"**（一个真实的逻辑陷阱）

### 3. ★★★★★ **configstring 校验器按**索引**拒绝一个配置串**（`0x31D9` 上界，接受 `0x15` 或 `>= 0x17`）

★ **⇒ 且 dmz loot band 已被 `OLMOD_DMZ_LOOT_BAND=0` 排除。**

### 4. ★★★★★ **渲染帧钩子必须装在渲染线程**（`BehaviorFlags 0x42` 无 `D3DCREATE_MULTITHREADED`）

★ **⇒ 两个线程 16016 / 43208 完全同步,但**不同线程**。**

### 5. ★★★★★ **`AnglesToQuaternion` 与 `AngleVectors` 是**两个不同函数**,寄存器也反了**

★ **⇒ 后果是**三个零向量** ⇒ 基向量校验拒绝。**

### 6. ★★★★★ **`Bullet_Endpos` 从 7 参数变 10 参数,三个新 float 插在中间**

★ **⇒ 用旧形式 ⇒ callee 从调用者帧里读指针,把未初始化 dword 当 float。**

### 7. ★★★★★ **`spreadMinimum = 0` 是一个**真实手感修复**（否则圆盘塌缩成外环）**

### 8. ★★★★★ **`UnlockAll` 的切点选择有**三个调用者计数**做依据**（1 / 6 / 23）

### 9. ★★★★★ **`TCLS_SHAREDMEMEMORY<pid>` 是命名空间边界**（Wine 实测映射存在两次仍打不开）

### 10. ★★★★ **738 个 bot 名字有完整实测来源**,但注释里的七个索引与文件顺序**不一致**

★ **⇒ 记录为**待核对项**（`无极剑士`=22、`飘渺纹龙`=234、`电侠伟`=279 与注释的 234/279/29 对不上）。

---

## 八、下一步

`game_server` 根剩余：

1. ★ **`EngineBindings.cpp`（917,344 B）** + `EngineBindings.hpp`（133,088 B）
2. ★ **`Appmain.cpp`（565,999 B）**
3. `NativePmoveBindings.cpp`（113,000）
4. `NativeWeaponMovementBindings.cpp`（31,427）+ `.bak-20261009-scopeidle`（29,791）
5. `ClientProcessPatches.cpp`（82,545）
6. `DedicatedProcessPatches.cpp`（39,058）
7. `ClientRenderFrameHook.cpp`（32,154）
8. `ClientCommandTrace.cpp`（27,720）
9. 然后 `server_mp` 154 文件（12,604,630 B）
