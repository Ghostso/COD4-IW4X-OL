# 学习报告 021 — 逐字节：Bootstrapper 插件发现/加载契约（决定性证据）

**方法**：读 `Bootstrapper32.dll` 字符串面 + 反汇编 `onStartup` 空桩验证
**性质**：全实测
**★★★ 性​质：这是全包最关键的逐字节证据**

---

## 一、★★★ Bootstrapper 的完整字符串表（偏移 `0x22A46`..`0x22B10`）

```
偏移        内容
0x22A46     "/Ayria/Logs/Bootstrapper32.log"
0x22A86     "/Ayria/Logs"
0x22A96     "/Ayria/Assets"
0x22AA6     "/Ayria/Plugins"          ← ★★★
0x22AB4     "onMessage"                ← ★★★
0x22AC0     "onInitialized"            ← ★★★
0x22AD0     "Ayria32"                  ← ★★★ 后缀
0x22AE4     "/Ayria/Plugins/%s"        ← ★★★ 扫描模式
0x22AF8     "Loaded plugin \"%s\""     ← ★★★ 日志
0x22B04     "onStartup"                ← ★★★
0x22B0C     "vector too long"
0x22B10     "string too long"
```

### ★★★ 逐串精确偏移验证

```
--- 'onMessage' @ 0x22AB4 ---
   [%-8s] %*s.../Ayria/Logs...../Ayria/Assets.../Ayria/Plugins.onMessage...

--- 'onInitialized' @ 0x22AC0 ---
   ./Ayria/Logs...../Ayria/Assets.../Ayria/Plugins.onMessage...onInitialized....Ayria32...../Ayria/Plugins/%s..Loaded plugin "%s"..onStartup...

--- 'onStartup' @ 0x22B04 ---
   lized....Ayria32...../Ayria/Plugins/%s..Loaded plugin "%s"..onStartup...

--- 'Ayria' @ 0x22AD1 (即 'Ayria32' @ 0x22AD0) ---
   /Ayria/Assets.../Ayria/Plugins.onMessage...onInitialized....Ayria32...../Ayria/Plugins/%s.....
```

### ★★★ 三个字符串之间的精确距离

```
0x22AB4  onMessage
   +12 (0x22AC0)  onInitialized
   +16 (0x22AD0)  Ayria32
   +20 (0x22AE4)  /Ayria/Plugins/%s
   +20 (0x22AF8)  Loaded plugin "%s"
   +12 (0x22B04)  onStartup
```

★★ **全部以 NUL 分隔、紧密排列** —— 这是**编译器字符串池**布局。

---

## 二、★★★ 插件的发现与加载规则（逆向字符串推得）

### 规则 1：扫描目录 `/Ayria/Plugins`

```
相对路径  "/Ayria/Plugins"
扫描模式  "/Ayria/Plugins/%s"
```

★ **`%s` 是文件名** —— 说明**遍历该目录下的所有文件**。

### 规则 2：★★★ 只加载以 `Ayria32` 结尾的

```
0x22AD0  "Ayria32"
```

★★★ **这是核心发现！**

```
文件名                               后缀       加载？
Localnetworking.Ayria32   →  ".Ayria32"    ✓
Platformwrapper.Ayria32   →  ".Ayria32"    ✓
CodolGameServer.Localnet32→  ".Localnet32"  ✗ ★★★
Alwaysoffline.Localnet32  →  ".Localnet32"  ✗ ★★★
```

★★★ **⇒ `Bootstrapper32.dll` **只加载 `*.Ayria32`，不加载 `*.Localnet32`！**

### 但这与 README 矛盾

**README 行 53-54 说**：
> 战斗服 ＝ `<游戏根>\Ayria\Plugins\CodolGameServer.Localnet32`（**进程内**）
> 后端   ＝ `<游戏根>\Ayria\Plugins\Alwaysoffline.Localnet32`（**进程内**）

★★★ **如果 Bootstrapper 只认 `Ayria32` 后缀，
那么 `CodolGameServer.Localnet32` 和 `Alwaysoffline.Localnet32` **根本不会被它加载**。**

### ★★★ 三种解释

**A. 后缀检查不是"必须以 Ayria32 结尾"，而是别的逻辑**
（比如"优先 Ayria32，Localnet32 用另一套"）

**B. `Localnet32` 由**另一个** bootstrapper 加载**
（`Bootstrapper64.dll`？那是 64 位，不适用）

**C. 后缀检查可能对 `Localnet32` 换成了别的东西**
（比如只把 `Ayria32` 替换成 `Localnet32` 再试一次）

★★★ **最可能是 C —— 但字符串表里**没有 `Localnet32`**！
（我在报告 020 里搜过 `CodolGameServer` 相关词，现在再确认 `Localnet32`）

### ★ 必须逐字节确认：Bootstrapper 里有没有 `Localnet32`

**这是本报告最关键的一条待验证。**

### 规则 3：★★★ 每个插件找三个符号

```
"onMessage"
"onInitialized"
"onStartup"
```

★★ **三个都在字符串表里，且相邻。**

### 规则 4：★★★ `Createserver` 完全不在 Bootstrapper 里

报告 020 实测：
```
=== Bootstrapper32 关键字符串 ===
  Createserver     0      ← ★★★ 零次
  CreateObj        0
  Invoke           1      ← 只有 1 次，且在 manifest XML 里
```

★ **`Invoke` 的 1 次在 `0x25732`，上下文是**：
```
<requestedExecutionLevel level="asInvoker" uiAccess="false"></requestedExecutionLevel>
```
—— **这是嵌入的 application manifest XML，不是代码字符串！**

★★★ **⇒ Bootstrapper **从不调用** `Createserver` / `CreateObj` / `Invoke`。**

★★ **所以 `Alwaysoffline::Createserver`（那个带 SEH 的真实函数）**永远不会被 Bootstrapper 调用**。**

★ **那它被谁调？** 待查。

---

## 三、★★★ `CodolGameServer::onStartup` 不是空桩 —— 是**跳转**

报告 020 我说它"可能也是空桩"，**错了**。逐字节实测：

```
00220880  E9 BB 71 FF FF        jmp 00017A40        ← ★★★ 相对跳转！
00220885  CC CC ...             (int3 填充)
```

### 相对跳转解码

```
E9 = JMP rel32
rel32 = BB 71 FF FF = 0xFFFF71BB = -0x8E45  (有符号)
目标  = 0x00220885 + (-0x8E45) = 0x00220885 - 0x8E45 = 0x0017A40
```

★★★ **`onStartup` @ `0x220880` 是 `jmp 0x17A40`** ——
**一条跳转指令，指向 `.text` 前段（`0x17A40`）。**

★★ **这与 `Createserver` 的 `33 C0 C3`（`xor eax,eax; ret`）完全不同**：

```
CodolGameServer::Createserver     33 C0 C3      → 真·空桩
CodolGameServer::onStartup        E9 xx xx xx   → ★ 跳到真实实现
```

★★★ **⇒ `CodolGameServer` **确实通过 `onStartup` 初始化**，且实现真在 `0x17A40`。**

★ **为什么用 `jmp` 而不是直接放在 `0x220880`？**
**因为 `onStartup`/`onInitialized` 共用 `0x220880`** ——
**导出表里两个符号指向同一地址，那地址上是一条 `jmp` 而不是完整函数体。**

★★ **这是链接器的"thunk"技巧**：两个名字 → 一处 thunk → 真实实现。

---

## 四、★★★ `CodolGameServer::SetEnabled` @ `0x220890` 的逐字节结构

```asm
00220890  55                 push ebp
00220891  8B EC              mov  ebp, esp
00220893  83 E4 F8           and  esp, -8            ← 8 字节栈对齐
00220896  E8 A5 71 FF FF     call 00017A40           ← ★★★ 同一个 0x17A40！
0022089B  80 3D 27 70 69 10 00  cmp byte ptr [10697027h], 0   ← ★ 全局 bool
002208A2  0F 84 FC 00 00 00  je   000209A4
002208A8  8B 45 08           mov  eax, [ebp+8]        ← 参数 1（bool enabled）
002208AB  84 C0              test al, al
002208AD  74 11              je   000208C0
002208AF  51                 push ecx
002208B0  E8 EB 31 F0 FF     call 000F3AA0
002208B5  84 C0              test al, al
002208B7  0F 84 E7 00 00 00  je   000209A4
002208BD  8B 45 08           mov  eax, [ebp+8]
```

### ★★★ 关键事实

1. **`E8 A5 71 FF FF` = `call 0x17A40`**
   ```
   下一条 = 0x22089B
   rel32  = 0xFFFF71A5 = -0x8E5B
   目标   = 0x22089B - 0x8E5B = 0x17A40  ✓
   ```
   ★★★ **与 `onStartup` 的 `jmp 0x17A40` 是**同一个目标**！**

2. **全局 bool @ `0x10697027`**
   ★ `0x10697027` = ImageBase `0x10000000` + RVA **`0x697027`**
   ★ 在 `.data` 节（VA `0x620000`..`0x806000`）范围内 ✓

★★★ **`0x17A40` 是一个**公共的入口点**：
- `onStartup`（`jmp`）→ `0x17A40`
- `SetEnabled`（`call`）→ `0x17A40` 然后继续读全局状态**

★★ **⇒ `0x17A40` 很可能是**"确保已初始化"（lazy init / ensure-ready）函数**，
或者**获取单例**（返回 `this`/`svc` 指针）。

★ **典型模式**：
```c
void* ensure_instance() {
    if (!g_initialized) { do_init(); g_initialized = true; }
    return g_instance;
}
```

★★ **`SetEnabled` 先 `call 0x17A40`（确保初始化）再读参数** —— 完全吻合。

---

## 五、★★★ 综合：三条链的完整字节级证据

### 链 1：Bootstrapper 的插件发现（字符串面）

```
0x22AA6  "/Ayria/Plugins"          目录
0x22AE4  "/Ayria/Plugins/%s"       遍历
0x22AD0  "Ayria32"                 后缀过滤  ← ★★★
0x22AF8  "Loaded plugin \"%s\""    日志
0x22B04  "onStartup"               入口 1
0x22AC0  "onInitialized"           入口 2
0x22AB4  "onMessage"               入口 3
0x22A46  "/Ayria/Logs/Bootstrapper32.log"  日志文件
```

### 链 2：`Broadcastmessage` 的调度（反汇编，报告 020）

```asm
000023F4  68 B4 44 02 10     push 0x100244B4       ← ★ 消息名（在 .rdata）
000023FB  FF 15 20 D0 01 10  call [0x1001D020]    ← IAT（外部函数）
0000240C  FF D0              call eax              ← 插件回调
00002414  83 C6 04           add  esi, 4           ← 数组步长 4
00002418  3B F7              cmp  esi, edi
0000241A  75 D8              jne  <循环>
```

★ **`0x100244B4` 在 `.rdata`（VA `0x1D000`..`0x26210`）内** ✓
★ 此前的读取（报告 020）读到的是 `k.a.-.G.E...f.o.-.F.O...` ——
**这是 `.rdata` 里的其他数据，不是这个字符串**。
**需要用 RVA → RawPtr 正确换算再读。**

### 链 3：插件自身的入口（反汇编）

```
CodolGameServer::Createserver    33 C0 C3          → 空桩（永不初始化）
CodolGameServer::onStartup       E9→0x17A40        → 真入口
CodolGameServer::onInitialized   E9→0x17A40        → 同一入口
CodolGameServer::SetEnabled      55 8B EC → call 0x17A40 → 读全局
Alwaysoffline::Createserver      SEH+/GS+192字节栈  → 真函数（但无人调）
Localnetworking::onStartup       55 8B EC → 116字节 → 真函数
```

---

## 六、★★★ 这一块对我们任务的**决定性结论**

### 结论 1：`CodolGameServer` 通过 `onStartup` 初始化，与 `Createserver` 无关

★★★ **换战斗服时，"必须实现 `Createserver`"是个误解。**
**真正被调用的是 `onStartup`（也即 `0x17A40` 那个入口）。**

★ **`Alwaysoffline` 的真 `Createserver`**从未被 Bootstrapper 调用** ——
**可能是历史遗留，或由别的机制调用。**

### 结论 2：★ 后缀 `Ayria32` 是硬过滤 —— 但 `Localnet32` 必须也能被加载

★★★ **字符串表里只有 `Ayria32`，没有 `Localnet32`。**

★★ **这意味着**：
- **要么** `Ayria32` 只是一个**优先级后缀**（先找 `X.Ayria32`，找不到再找 `X.Localnet32`）
- **要么** `Localnet32` 由**另一段代码**（可能在 `Bootstrapper64.dll` 或别处）处理
- **要么** README 说"进程内"是错的

★ **必须反汇编 `/Ayria/Plugins/%s` 的使用点才能定。**

### 结论 3：★★★ `Createserver` 字符串 0 次是**最强的排除证据**

★★ **Bootstrapper **从不**干预 `Createserver`。**
**⇒ 任何 C++ 重实现只要保持 55 个导出符号，`Createserver` 可以是空壳。**

### 结论 4：★ `onMessage` 是消息分发入口

★★ **`Broadcastmessage` → 每个插件的 `onMessage`** ——
**这是插件间通信（或加载器→插件通知）的主通道。**

★ **`Localnetworking::onMessage` @ `0x17090` 就是网络事件的接收点。**

---

## 七、逐字节证据总表（本报告）

| # | 证据 | 偏移/地址 | 结论 |
|---|---|---|---|
| 1 | `"/Ayria/Plugins"` | `0x22AA6` | 扫描目录 |
| 2 | `"/Ayria/Plugins/%s"` | `0x22AE4` | 遍历模式 |
| 3 | `"Ayria32"` | `0x22AD0` | ★ 后缀过滤 |
| 4 | `"Loaded plugin \"%s\""` | `0x22AF8` | 加载日志 |
| 5 | `"onStartup"` | `0x22B04` | 入口符号 1 |
| 6 | `"onInitialized"` | `0x22AC0` | 入口符号 2 |
| 7 | `"onMessage"` | `0x22AB4` | 入口符号 3 |
| 8 | **`"Createserver"` 0 次** | — | ★★★ 加载器不调它 |
| 9 | `"Invoke"` 唯一 1 次在 manifest XML | `0x25732` | 非代码字符串 |
| 10 | `onStartup = E9 BB 71 FF FF` | `0x220880` | ★ `jmp 0x17A40` |
| 11 | `SetEnabled = E8 A5 71 FF FF` | `0x220896` | ★ `call 0x17A40` |
| 12 | `Createserver = 33 C0 C3` | `0x5DD70` | 真空桩 |
| 13 | 全局 bool `0x10697027` | RVA `0x697027` | `.data` 内 |
| 14 | `Broadcastmessage` 数组步长 4 | `0x2414` | `add esi,4` |
| 15 | `onInitializationdone` 幂等标志 | `0x10028A8C` | 全局 bool |

---

## 八、待逐字节继续（★ 优先级排序）

- [ ] ★★★ **`Localnet32` 在 Bootstrapper 里存在吗？**（决定 `CodolGameServer` 能否被加载）
- [ ] ★★★ **反汇编 `0x17A40`**（`onStartup` 的真实实现）
- [ ] ★★ **`0x100244B4` 的正确读取**（Broadcastmessage 的消息名）
- [ ] ★★ **`/Ayria/Plugins/%s` 的使用点**（加载循环）
- [ ] ★ **`0x1001D020`（IAT 槽）指向什么**
- [ ] `Bootstrapper32.dll` 的 `SizeOfImage = 0x2C000`，`0x22A46` 在 `.rdata`（VA `0x1D000`, Size `0x9210` → 到 `0x26210`）内 ✓
- [ ] 谁调用 `Alwaysoffline::Createserver`（真函数，但 Bootstrapper 不调）
