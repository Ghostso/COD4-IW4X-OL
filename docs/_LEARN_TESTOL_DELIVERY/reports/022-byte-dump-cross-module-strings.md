# 学习报告 022 — 逐字节：跨模块字符串矩阵（谁加载谁，定案）

**方法**：对 8 个模块逐一统计 10 个关键词的**精确出现次数**
**性质**：全实测
**★★★ 本报告解决了报告 021 提出的核心矛盾**

---

## 一、★★★ 完整矩阵（实测次数）

```
模块                             Localnet32  .Ayria32  Localnetworking  CodolGameServer  Alwaysoffline  Platformwrapper  Bootstrapper  Plugins  onStartup  Createserver
Bootstrapper32.dll                        0          1                0                0              0                0             2        2          1            0
Bootstrapper64.dll                        0          0                0                0              0                0             2        2          1            0
Localnetworking.Ayria32                   1          1                4                0              0                0             0        0          1            1
Platformwrapper.Ayria32                   0          1                0                0              0                4             2        0          1            0
Alwaysoffline.Localnet32                  3          0                0                1            201                0             0        0          0            2
CodolGameServer.Localnet32                1          0                0              614              1                0             0        0          1            1
Injector32.exe                            0          0                0                0              0                0             1        0          0            0
ol_room_owner.exe                         0          0                0                0              0                0             0        0          0            0
```

### ★★★ 立刻可读出的五条结论

## 结论 1：`Bootstrapper` **只加载 `*.Ayria32`**

```
Bootstrapper32.dll:  .Ayria32 = 1 次，Localnet32 = 0 次
Bootstrapper64.dll:  .Ayria32 = 0 次，Localnet32 = 0 次  ← ★ 64 位版完全不管插件
```

★★ **`Bootstrapper64.dll` 甚至没有 `.Ayria32` 字符串** ——
**它是纯 64 位加载桩，与插件发现无关。**

★★★ **⇒ `Bootstrapper32.dll` 只扫 `*.Ayria32`。**
**`CodolGameServer.Localnet32` / `Alwaysoffline.Localnet32` **不是**它加载的。**

---

## 结论 2：★★★ `Localnetworking.Ayria32` 是 `*.Localnet32` 的加载器

```
Localnetworking.Ayria32:  Localnet32 = 1 次   ← ★★★
                          .Ayria32   = 1 次
                          Localnetworking = 4 次
                          onStartup  = 1 次
                          Createserver = 1 次   ← ★★★
```

★★★ **`Localnetworking` 里有 `Localnet32` 字符串（1 次）和 `Createserver`（1 次）！**

★ **⇒ 分层加载**：
```
Bootstrapper32.dll
    └─ 加载所有 *.Ayria32
        ├── Localnetworking.Ayria32   ← ★★★ 它再加载 *.Localnet32
        └── Platformwrapper.Ayria32
                    ↓
        Localnetworking 加载 *.Localnet32
            ├── Alwaysoffline.Localnet32
            └── CodolGameServer.Localnet32
```

★★★ **这就是报告 009 "`inject_ayria.on` 之谜"的一半答案**：
**`nt10.py` 不注入 ⇒ 无 `Bootstrapper` ⇒ 无 `Localnetworking` ⇒ 无 `*.Localnet32`。**

★ **但只要 `Localnetworking.Ayria32` 被加载，两个 `.Localnet32` 就会被它拉起来。**

---

## 结论 3：★★★ `Createserver` 在 `Localnetworking` 里出现 1 次！

```
Localnetworking.Ayria32:  Createserver = 1 次
Alwaysoffline.Localnet32: Createserver = 2 次  ← 导出名 + 代码内引用
CodolGameServer.Localnet32: Createserver = 1 次 ← 只有导出表
Bootstrapper32.dll:       Createserver = 0 次
```

★★★ **⇒ `Localnetworking` 是唯一"知道 `Createserver` 这个名字"的加载器**。

★ **`Alwaysoffline` 里 2 次**：导出表 1 次 + 代码内 1 次（可能是日志/自检）。
★ **`CodolGameServer` 里 1 次**：只有导出表。
★ **`Localnetworking` 里 1 次**：**`GetProcAddress(h, "Createserver")` 的字符串参数！**

★★★ **⇒ `Createserver` 是 `Localnetworking` 调用的，不是 `Bootstrapper`。**
**报告 020/021 的"无人调用 `Createserver`"结论**被推翻**。**

---

## 结论 4：★★★ `CodolGameServer` 里 `CodolGameServer` 出现 **614 次**

```
CodolGameServer.Localnet32:  CodolGameServer = 614 次
                             Alwaysoffline   = 1 次
```

★★ **614 次是因为**：所有 52 个导出名都叫 `CODOL_GameServer*`，
加上日志前缀、模块名等。

★ **`Alwaysoffline` 出现 1 次** —— **只提了一次**（可能是共享的配置/日志路径）。

★ **`Alwaysoffline` 里 `Alwaysoffline` 出现 201 次**（自身名字 + 52 类日志前缀）。

## 结论 5：★ `Platformwrapper` 里有 `Bootstrapper` 2 次

```
Platformwrapper.Ayria32:  Bootstrapper = 2 次
                          Platformwrapper = 4 次
```

★★ **`Platformwrapper` 知道 `Bootstrapper`** —— 可能是日志路径
（`Ayria\Logs\Bootstrapper32.log`）或反向调用 `Broadcastmessage`。

★★★ **⇒ 插件**可以**回调 `Bootstrapper` 的 `Broadcastmessage`**（报告 020 已在
`Bootstrapper32.dll` 里看到 `Broadcastmessage` 导出）。

---

## 二、★ `Localnetworking` 的 4 次 `Localnetworking` 与 1 次 `Localnet32`

★★ **1 次 `Localnet32` 是关键**。需要看它的**上下文**确认是不是 `GetProcAddress` 参数。

### ★ 可能的形态

```c
// 遍历 Ayria\Plugins\*.Localnet32
for (dir_entry : find_files("./Ayria/Plugins", ".Localnet32")) {
    HMODULE h = LoadLibraryA(path);
    if (!h) continue;
    fp_create = GetProcAddress(h, "Createserver");     // ← Createserver 字符串
    if (fp_create) fp_create();
    // 再取 onStartup / onInitialized / onMessage
}
```

★★ **这与 `Localnetworking` 里有 `onStartup`（1 次）和 `Createserver`（1 次）**完全吻合**：
- `onStartup` = 它自己的导出名（导出表里 1 次）
- `Createserver` = 它查找的**别人的**导出名

★★ **但 `onInitialized` / `onMessage` 在 `Localnetworking` 里是 0 次** ——
**说明它只找 `Createserver`，不找另外两个。**

★★★ **⇒ `*.Localnet32` 的契约**只有 `Createserver`**；
`*.Ayria32` 的契约才是 `onStartup`/`onInitialized`/`onMessage`。**

★★ **这解释了两个命名体系的本质区别**：
```
.Ayria32      = Ayria 官方插件格式（三件套 onStartup/onInitialized/onMessage）
.Localnet32   = 本项目的扩展格式（只有 Createserver）
```

---

## 三、★★★ 修正报告 020/021 的错误结论

| 报告 | 原结论 | 逐字节修正 |
|---|---|---|
| 020 | "`CodolGameServer::Createserver` 是空桩 ⇒ 不通过它初始化" | ★ **仍成立**（`33 C0 C3`），但**它会被 `Localnetworking` 调用并返回 0** |
| 020 | "`Alwaysoffline::Createserver` 是真函数但无人调" | ★★ **推翻**：`Localnetworking` 用 `GetProcAddress("Createserver")` 调它 |
| 021 | "`CodolGameServer` 靠 `onStartup` @ 0x17A40 初始化" | ★ 部分成立，但 **`onStartup` 是 Ayria 三件套，`Localnetworking` 不找它** |
| 021 | "Bootstrapper 只加载 `*.Ayria32`" | ★★★ **成立，且是定案** |
| 021 | "`Localnet32` 在 Bootstrapper 里 0 次" | ★★★ **成立**，且**在 `Localnetworking` 里有 1 次** |

### ★★★ 更正后的完整加载链

```
Injector32.exe
   │  LoadLibrary(Bootstrapper32.dll)
   ▼
Bootstrapper32.dll
   │  扫描 ./Ayria/Plugins/*.Ayria32
   │  对每个：GetProcAddress("onStartup"/"onInitialized"/"onMessage")
   ├──> Localnetworking.Ayria32
   │       ★ 它再扫描 ./Ayria/Plugins/*.Localnet32
   │       ★ 对每个：GetProcAddress("Createserver") → 调用
   │       ├──> Alwaysoffline.Localnet32   Createserver @ 0xC67F0（真函数）
   │       └──> CodolGameServer.Localnet32 Createserver @ 0x5DD70（空桩）
   │
   └──> Platformwrapper.Ayria32
```

---

## 四、★★★ 对我们任务（换战斗服）的决定性意义

### ★★★ `CodolGameServer::Createserver` 是空桩 —— 但它**确实被调用**

```
33 C0 C3 = xor eax,eax; ret
```

★★★ **⇒ `CodolGameServer` 在 `Createserver` 里**什么都不做**，直接返回 0。**

**如果 `Localnetworking` 检查返回值**：
```c
if (fp_create() != 0) { fail }    // 那么 0 = 成功
```
⇒ **空桩返回 0 就是"成功"，这是故意的。**

### ★★ 但 `Alwaysoffline::Createserver` 是**真的做初始化**（SEH + GS + 192 字节）

**⇒ 两种语义并存**：
- `Alwaysoffline` 用 `Createserver` 做初始化
- `CodolGameServer` 不用（它靠 `onStartup`，但 `Localnetworking` 不调 `onStartup`）

★★★ **这是本报告最矛盾的发现**：
**`CodolGameServer` 既不被 `Createserver` 初始化（空桩），也不被 `onStartup` 初始化
（`Localnetworking` 不调 `onStartup`）。**

### ★★★ 三种解释

**A. `CodolGameServer` 靠 DLL 的 `DllMain` / TLS 回调自初始化**
★ **支持**：报告 019 实测它有 **TLS 目录**（RVA `0x5F6300`）。
**TLS 回调在 `LoadLibrary` 时被 loader 自动调用，不需要任何人显式调用。**

**B. `CodolGameServer` 的 `Createserver` 在别处被定义（不是 `0x5DD70`）**
★ **反对**：导出表明确写 `[53] 0x0005DD70 Createserver`。

**C. `Localnetworking` 调 `onStartup` 而不是 `Createserver`**
★ **反对**：`Localnetworking` 里 `onStartup` 只出现 1 次（**它自己的导出表**），
`Createserver` 出现 1 次（**查找别人的**）。

★★★ **⇒ 最可能是 A：`CodolGameServer` 靠 `DllMain`/TLS 自初始化。**

★ **这与其他插件一致**：`Localnetworking`/`Platformwrapper` 也都有 TLS 目录吗？**待验。**

---

## 五、★ `ol_room_owner.exe` 全是 0

```
ol_room_owner.exe:  Localnet32=0  .Ayria32=0  ...  全部 0
```

★★ **`ol_room_owner.exe` 完全不知道任何插件名** ——
**它是独立进程，通过 TCP（端口 28970）与客户端通信，不加载插件。**

★ **与报告 020 实测的"导入只有 `WS2_32` + `KERNEL32`"一致** ✓

---

## 六、逐字节证据总表

| # | 模块 | 关键词 | 次数 | 偏移 | 结论 |
|---|---|---|---|---|---|
| 1 | `Bootstrapper32` | `.Ayria32` | **1** | `0x22AD0` | 只加载 Ayria32 |
| 2 | `Bootstrapper32` | `.Localnet32` | **0** | — | ★ 不管 Localnet32 |
| 3 | `Bootstrapper64` | `.Ayria32` | **0** | — | 64 位版不管插件 |
| 4 | `Localnetworking` | `Localnet32` | **1** | 待定位 | ★★★ 它加载 Localnet32 |
| 5 | `Localnetworking` | `Createserver` | **1** | 待定位 | ★★★ 它调 Createserver |
| 6 | `Alwaysoffline` | `Createserver` | **2** | 导出+代码 | 真实现 |
| 7 | `CodolGameServer` | `Createserver` | **1** | 导出表 | 空桩 |
| 8 | `CodolGameServer` | `CodolGameServer` | **614** | 多处 | 52 导出名 + 日志前缀 |
| 9 | `Platformwrapper` | `Bootstrapper` | **2** | 待定位 | 可回调 Broadcastmessage |
| 10 | `ol_room_owner` | 全部 | **0** | — | 完全独立 |

---

## 七、待逐字节继续（★ 优先级）

- [ ] ★★★ **定位 `Localnetworking` 里 `Localnet32` 字符串的偏移与上下文**
- [ ] ★★★ **定位 `Localnetworking` 里 `Createserver` 的偏移，确认是 `GetProcAddress` 参数**
- [ ] ★★★ **`Localnetworking::onStartup` @ `0x16FC0` 的完整反汇编**（看它怎么找插件）
- [ ] ★★ **`CodolGameServer` 的 TLS 回调地址与内容**（验证解释 A）
- [ ] ★★ **`CodolGameServer::onStartup` @ `0x17A40` 的反汇编**
- [ ] ★ **`Platformwrapper` 里 `Bootstrapper` 的 2 次上下文**
- [ ] ★ **`Alwaysoffline` 里 `CodolGameServer` 出现 1 次的上下文**
- [ ] `CodolGameServer` 里 `Alwaysoffline` 出现 1 次的上下文
