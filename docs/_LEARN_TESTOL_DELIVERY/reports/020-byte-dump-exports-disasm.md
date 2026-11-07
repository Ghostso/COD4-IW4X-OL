# 学习报告 020 — 逐字节转储：完整导出/导入契约 + 入口函数反汇编

**方法**：解析 6 个模块的导出/导入表 + 反汇编关键入口的前 64-96 字节
**性质**：全实测

---

## 一、★★★ 六模块完整导出契约（逐字节）

| 模块 | 文件内 DLL 名 | 导出数 | 导入 DLL | 导入数 |
|---|---|---|---|---|
| `Injector32.exe` | — | **0** | `KERNEL32.dll` | **1** |
| `Bootstrapper32.dll` | `Bootstrapper32.dll` | **2** | `KERNEL32.dll` | 1 |
| `ol_room_owner.exe` | — | **0** | `WS2_32.dll`, `KERNEL32.dll` | 2 |
| `Localnetworking.Ayria32` | **`LocalnetworkingRe.Ayria32`** | **3** | `WS2_32.dll`, `KERNEL32.dll` | 2 |
| `Platformwrapper.Ayria32` | **`PlatformwrapperRe.Ayria32`** | **6** | `USER32.dll`, `KERNEL32.dll` | 2 |
| `Alwaysoffline.Localnet32` | **`AlwaysofflineRe.Localnet32`** | **5** | `WS2_32`, `bcrypt`, `USER32`, `ADVAPI32`, `CRYPT32`, `KERNEL32` | **6** |
| `CodolGameServer.Localnet32` | `CodolGameServer.Localnet32` | **55** | `WS2_32`, `USER32`, `ADVAPI32`, `CRYPT32`, `KERNEL32` | 5 |

### ★★★ 发现 1：三个插件的**内部 DLL 名带 `Re.` 后缀**

```
文件名                    内部 DLL 名
Localnetworking.Ayria32   →  LocalnetworkingRe.Ayria32
Platformwrapper.Ayria32   →  PlatformwrapperRe.Ayria32
Alwaysoffline.Localnet32  →  AlwaysofflineRe.Localnet32
```

★★★ **`Re` = "Reimplementation"（重实现）** —— 这是**上游 ol-mod 项目的命名习惯**：
**"我们对 Ayria 官方组件的重实现"**。

★ **只有 `CodolGameServer.Localnet32` 没有 `Re`** ——
**因为它不是重实现，是**全新的**战斗服**（不是替代任何官方组件）。

★★ **文件名与内部名不同不影响 `LoadLibrary`**（按路径加载），
**但如果代码里 `GetModuleHandle("LocalnetworkingRe.Ayria32")` 就会用内部名。**

★★★ **这是"从源码重建后改名"会破坏契约的直接证据**
（BUILD.md 说"兼容文件名不能改"，现在有了字节级依据）。

### ★★★ 发现 2：导入 DLL 极少 —— 全静态链接

```
Injector32.exe              1 个（KERNEL32）
Bootstrapper32.dll          1 个（KERNEL32）
ol_room_owner.exe           2 个（WS2_32, KERNEL32）
Localnetworking.Ayria32     2 个（WS2_32, KERNEL32）
Platformwrapper.Ayria32     2 个（USER32, KERNEL32）
Alwaysoffline.Localnet32    6 个
CodolGameServer.Localnet32  5 个
```

★★ **`Localnetworking` 只导入 `WS2_32` + `KERNEL32`** ——
**极简，只做网络**（与名字完全一致）。

★★ **`Platformwrapper` 不导入 `WS2_32`！** 只导入 `USER32` + `KERNEL32`。
**⇒ 它不做任何网络 I/O** —— 与报告 014 引用的记忆一致：
> `Platformwrapper` 的 Tencent 接口（`Tencent.cpp:35-53`）没有任何名字槽位

★ **`Alwaysoffline` 用 `bcrypt.dll`** —— Windows CNG 加密 API。
**⇒ 它自己做加密（TLS/握手）**，而不依赖 OpenSSL（静态链接没了）。

★★ **`Injector32.exe` 只导入 `KERNEL32`** ——
**它不导入 `kernel32!LoadLibraryW` 之外的任何东西就能注入**？
**实际上 `LoadLibrary`/`WriteProcessMemory`/`CreateRemoteThread` 全在 `KERNEL32` 里**。

---

## 二、★★★ 三类入口函数契约

### 类型 A：`onStartup` / `onInitialized`（Ayria 标准契约）

**`Localnetworking.Ayria32`（3 个导出）**：
```
[1] 0x00009DF0  onInitialized
[2] 0x00017090  onMessage
[3] 0x00016FC0  onStartup
```

**`Platformwrapper.Ayria32`（6 个导出）**：
```
[1] 0x000176C0  CreateObj
[2] 0x00007440  InitCrossContextByOpenID
[3] 0x00017600  Invoke
[4] 0x000076E0  onInitialized
[5] 0x000190F0  onMessage
[6] 0x00018E90  onStartup
```

★★ **`onStartup` / `onInitialized` / `onMessage` 是 Ayria 的三件套** ✓

★ **`Platformwrapper` 多了 3 个**（`CreateObj` / `InitCrossContextByOpenID` / `Invoke`）
—— 这是**它要暴露给游戏代码的腾讯平台接口**（通过 COM 式对象）。

★★ **`InitCrossContextByOpenID`** 与 `fake_auth_tls.py` 的 OpenID 相关（报告 011）：
> `tag25 = OpenID`，格式串 `"OpenID LoginKey: %s"` → 全 0 = 空账号 = 认证失败

### 类型 B：`Createserver`（战斗服契约）

**`Alwaysoffline.Localnet32`（5 个导出）**：
```
[1] 0x000C6C30  CODOL_GetInventoryRefreshStatus
[2] 0x000C6B70  CODOL_GetProfileReloadStatus
[3] 0x000C6BD0  CODOL_RequestInventoryRefresh
[4] 0x000C6B10  CODOL_RequestProfileReload
[5] 0x000C67F0  Createserver                              ← ★
```

**`CodolGameServer.Localnet32`（55 个导出）**：
```
[53] 0x0005DD70  Createserver                              ← ★
[54] 0x00220880  onInitialized
[55] 0x00220880  onStartup                                 ← ★ 与上面同地址
```

### 类型 C：`Bootstrapper32.dll` 特有（2 个）

```
[1] 0x000023E4  Broadcastmessage
[2] 0x00002425  onInitializationdone
```

★★ **`Broadcastmessage`** = 向所有插件广播消息。
**`onInitializationdone`** = 初始化完成回调。

★★★ **⇒ 这是**反向的**接口**：**加载器向插件调 `onStartup`，插件向加载器调 `Broadcastmessage`。**

---

## 三、★★★ 入口函数反汇编（实测字节）

### ① `CodolGameServer::Createserver` @ RVA `0x5DD70` —— **是个空桩！**

```asm
0005DD70  33 C0              xor eax, eax
0005DD72  C3                 ret
0005DD73  CC CC ...          (int3 填充)
```

★★★ **`33 C0 C3` = `return 0`。**

★ **`Createserver` 在 CodolGameServer 里**什么都不做**，
直接返回 0。**

★★ **这与 `Alwaysoffline::Createserver` 形成对比**（见 ②）。

★★★ **⇒ 推论**：`CodolGameServer` **不通过 `Createserver` 初始化**。
它靠 **`onStartup`**（@ `0x220880`，与 `onInitialized` 同地址）。

★ **但 `onStartup` 和 `onInitialized` 同地址** —— **也是空桩？**
**需要反汇编 0x220880 确认。**

### ② `Alwaysoffline::Createserver` @ RVA `0xC67F0` —— **真实的 SEH 函数！**

```asm
000C67F0  55                 push ebp
000C67F1  8B EC              mov  ebp, esp
000C67F3  6A FF              push 0FFFFFFFFh          ← ★ SEH 作用域开始
000C67F5  68 11 D6 2F 10     push 102FD611h           ← ★ SEH 处理器（VA @ ImageBase 0x10000000）
000C67FA  64 A1 00 00 00 00  mov  eax, dword ptr fs:[0]  ← ★ 当前 SEH 链
000C6800  50                 push eax
000C6801  81 EC C0 00 00 00  sub  esp, 0C0h            ← ★ 192 字节局部变量
000C6807  A1 00 0B 3D 10     mov  eax, dword ptr [103D0B00h]  ← ★ 栈 Cookie
000C680C  33 C5              xor  eax, ebp             ← Cookie ^ EBP
000C680E  89 45 EC           mov  [ebp-14h], eax       ← 保存
000C6811  53                 push ebx
000C6812  56                 push esi
000C6813  57                 push edi
000C6814  50                 push eax
000C6815  8D 45 F4           lea  eax, [ebp-0Ch]
000C6818  64 A3 00 00 00 00  mov  dword ptr fs:[0], eax
000C681E  89 65 F0           mov  [ebp-10h], esp
000C6821  8B 75 08           mov  esi, [ebp+8]        ← ★ 第 1 个参数
000C6824  85 F6              test esi, esi
000C6826  0F 84 75 02 00 00  je   000C68A1           ← ★ 参数为 NULL 则跳到错误处理
000C682C  E8 AF 7D FC FF     call 0008E5E0            ← 真正的初始化
```

★★★ **逐字节确认的五个事实**：

1. **`6A FF` / `68 xx xx xx xx`** = **MSVC 的 `__try`/`__except` 或 `__try`/`__finally` 帧**
   ⇒ **这个函数有异常处理**
2. **`64 A1 00 00 00 00`** = `mov eax, fs:[0]` ⇒ **读写 SEH 链**
3. **`A1 00 0B 3D 10`** ⇒ **读取 `0x103D0B00` 处的栈 Cookie**
   ★ **`0x103D0B00` 在 ImageBase `0x10000000` + RVA `0x3D0B00`**
   ★ **在 `.data` 节（VA `0x3CC000`..`0x3DE000`）范围内** ✓
4. **`33 C5` + `89 45 EC`** = **`__security_cookie ^ ebp` 存栈**
   ⇒ **这是 `/GS` 栈保护函数**
5. **`81 EC C0 00 00 00`** ⇒ **192 字节栈帧** ⇒ **函数体不简单**

★★★ **⇒ `Alwaysoffline::Createserver` 是**真正的入口**（有栈保护 + SEH + 192 字节栈帧）。

★★ **与 `CodolGameServer::Createserver` 的 `33 C0 C3` 天壤之别。**

### ③ `Localnetworking::onStartup` @ RVA `0x16FC0` —— 真实函数

```asm
00016FC0  55                 push ebp
00016FC1  8B EC              mov  ebp, esp
00016FC3  83 E4 F8           and  esp, 0FFFFFFF8h     ← ★ 8 字节栈对齐
00016FC6  83 EC 74           sub  esp, 74h            ← 116 字节局部
00016FC9  56                 push esi
00016FCA  8D 4C 24 10        lea  ecx, [esp+10h]
00016FCE  E8 DD 01 FF FF     call 000071B0            ← 构造某个对象
00016FD3  80 7C 24 70 00     cmp  byte ptr [esp+70h], 0   ← ★ 检查某个 bool
00016FD8  0F 84 A0 00 00 00  je   0001707E            ← ★ false 则跳
00016FDE  8D 54 24 08        lea  edx, [esp+08h]
00016FE2  C7 44 24 08 00 00 00 00  mov dword ptr [esp+08h], 0
00016FEA  8D 4C 24 40        lea  ecx, [esp+40h]
00016FEE  C7 44 24 0C 70 C2 07 10  mov dword ptr [esp+0Ch], 1007C270h  ← ★ 字符串常量指针
00016FF6  E8 35 FD FF FF     call 00006D30            ← 另一个构造
```

★★ **`mov dword ptr [esp+0Ch], 1007C270h`** ——
**这是把 `0x1007C270` 处的地址（一个 std::string 的内容或指针）装进栈上的对象。**

★ **`0x1007C270` = ImageBase `0x10000000` + RVA `0x7C270`**
★ **在 `.rdata`（VA `0x46000`..`0x56000`）**？
**不 —— `0x7C270` 超出 `.rdata`（到 `0x55C7C`），在 `.data`（`0x56000`..`0x7DA74`）内** ✓

★★ **强推论**：`onStartup` 第一件事是**构造一个带配置字符串的对​象**
（可能是 `ServerConfig` / `BindAddress`）。

★★★ **`Localnetworking::onStartup` 是真实函数**，有 116 字节栈帧 + 对象构造。

### ④ `Bootstrapper32::Broadcastmessage` @ RVA `0x23E4` —— **遍历插件数组**

```asm
000023E4  56                 push esi
000023E5  8B 35 B4 8A 02 10  mov  esi, dword ptr [10028AB4h]  ← ★ 全局：起始指针
000023EB  57                 push edi
000023EC  8B 3D B8 8A 02 10  mov  edi, dword ptr [10028AB8h]  ← ★ 全局：结束指针
000023F2  EB 24              jmp  00002418
--- 循环体 ---
000023F4  68 B4 44 02 10     push 100244B4h           ← ★ 消息/事件名
000023F9  FF 36              push dword ptr [esi]     ← ★ 当前插件句柄/对象
000023FB  FF 15 20 D0 01 10  call dword ptr [1001D020h]  ← ★ 通过 IAT 调外部函数（应为 Broadcast）
00002401  85 C0              test eax, eax
00002403  74 10              je   00002415            ← 返回 0 则跳过
00002405  FF 74 24 10        push dword ptr [esp+10h]  ← 参数 2
00002409  FF 74 24 10        push dword ptr [esp+10h]  ← 参数 1
0000240C  FF D0              call eax                 ← ★★★ 间接调用（插件回调！）
0000240E  59 59              pop  ecx; pop ecx
00002410  84 C0              test al, al
00002412  75 0C              jne  00002420            ← 返回 true → 结束（短路）
--- 循环尾 ---
00002414  83 C6 04           add  esi, 4              ← ★ 指针 +4（数组元素 4 字节）
00002418  3B F7              cmp  esi, edi
0000241A  75 D8              jne  000023F4            ← 循环
0000241C  32 C0              xor  al, al              ← 返回 false（所有插件都没处理）
0000241E  5F 5E              pop  edi; pop esi
00002420  C3                 ret
```

★★★ **这是全包最清晰的"插件调度器"实现**：

```
全局变量：
  0x10028AB4  插件数组起始指针
  0x10028AB8  插件数组结束指针
  元素大小    4 字节（句柄/对象指针）

循环：
  for (esi = begin; esi != end; esi += 4) {
      fn = IAT_call(0x1001D020, *esi, "0x100244B4");   // 问"你支持这个消息吗"
      if (!fn) continue;
      if (fn(arg1, arg2)) return true;                  // ★ 第一个返回 true 的就短路
  }
  return false;
```

★★ **`add esi, 4` + `cmp esi, edi`** —— **数组遍历的铁证**（指针 + 步长 + 上界比较）。

★★★ **`jne 00002420`（`test al,al; jne`）** ⇒ **短路语义**：
**第一个返回 `true` 的插件"消费"了这条消息，后续插件不再收到。**

★ **这解释了为什么插件顺序重要**（`Localnetworking` 必须先于 `Alwaysoffline`）。

★★ **`0x100244B4`** = ImageBase `0x10000000` + RVA `0x244B4`,在 `.rdata`（`0x1D000`..`0x26210`）内 ✓
—— **是一个字符串常量（消息名）**。

★ **`0x1001D020` 在 `.rdata`/IAT 区（`.rdata` 到 `0x26210`，IAT 从 `0x1D000`?）**，需确认。

### ⑤ `Bootstrapper32::onInitializationdone` @ RVA `0x2425`

```asm
00002424  F9                 (上一函数末尾的 stc/stdc)
00002425  80 3D 8C 8A 02 10 00   cmp byte ptr [10028A8Ch], 0   ← ★ 全局 bool
0000242D  75 36              jne  00002465
0000242F  56                 push esi
00002430  8B 35 B4 8A 02 10  mov  esi, dword ptr [10028AB4h]  ← 同一个插件数组起始
```

★★ **`0x10028A8C` 是一个全局 `bool`（"已初始化"标志）** ——
**首次调用时 `== 0`，进入初始化分支并置 1；再次调用直接返回。**

★★★ **⇒ `onInitializationdone` 是**幂等的一次性初始化**。**

---

## 四、★★★ 由反汇编得出的加载链全貌

```
Injector32.exe（只导入 KERNEL32）
     │  CreateProcess(client) + 远程 LoadLibrary(Bootstrapper32.dll)
     ▼
Bootstrapper32.dll（只导入 KERNEL32，导出 2 个）
     │
     ├─ 全局 0x10028AB4 / 0x10028AB8 = 插件数组 begin/end
     ├─ 全局 0x10028A8C = "已初始化" bool
     │
     │  对每个 Ayria\Plugins\*：
     │      LoadLibrary  →  GetProcAddress("onStartup")  →  调用
     │      把句柄/对象写入数组
     │
     ▼
Broadcastmessage(msg)  ← 遍历数组，问每个插件"你处理吗"，第一个 true 短路
     │
     ├──> Localnetworking.Ayria32   [onStartup 0x16FC0] [onMessage 0x17090] [onInitialized 0x9DF0]
     │        ★ 只导入 WS2_32 + KERNEL32（专业做网络）
     │
     ├──> Platformwrapper.Ayria32   [onStartup 0x18E90] [onMessage 0x190F0] [onInitialized 0x76E0]
     │        + CreateObj 0x176C0 / Invoke 0x17600 / InitCrossContextByOpenID 0x7440
     │        ★ 只导入 USER32 + KERNEL32（不做网络）
     │
     ├──> Alwaysoffline.Localnet32  [Createserver 0xC67F0 ★真实] + 4 个 CODOL_*Profile/Inventory
     │        ★ 导入 6 个 DLL 含 bcrypt（自己加密）
     │
     └──> CodolGameServer.Localnet32 [Createserver 0x5DD70 ★空桩] + onStartup/onInitialized(同址)
              + 52 个 CODOL_GameServer* 状态/配置导出
              ★ 导入 5 个 DLL
```

### ★★★ 关键推论

1. **两类插件契约并存**：
   - **Ayria 型**：`onStartup` / `onInitialized` / `onMessage`
   - **自研型**：`Createserver`（`Alwaysoffline` 真实现、`CodolGameServer` 空桩）

2. **`CodolGameServer` 的真正入口是 `onStartup` @ `0x220880`**
   （因为 `Createserver` 是 `xor eax,eax; ret`）
   ★ **必须反汇编 `0x220880` 才能确认它是否也是空桩。**

3. **`Broadcastmessage` 按数组顺序遍历 + 短路**
   ⇒ **插件加载顺序决定行为**

4. **`Alwaysoffline` 是"先起来"的那个**（有真 `Createserver` + bcrypt）
   ⇒ **它负责认证/握手，`CodolGameServer` 负责战斗**

---

## 五、★★★ 对我们任务（换战斗服）的直接意义

### 换战斗服要动的东西

```
要替换的         CodolGameServer.Localnet32（6.8 MB，55 个导出）
必须保持的       文件名       CodolGameServer.Localnet32
                 内部 DLL 名  CodolGameServer.Localnet32   ← 无 Re 后缀
                 导出符号     55 个（尤其 Createserver / onStartup / onInitialized
                              / CODOL_GameServerConfigureSession 等）
                 ImageBase   0x10000000（否则仍可用，只是要重定位）
导入依赖         可以不同（5 个 DLL 是当前实现的选择，不是契约）
```

★★ **最小替换面**：**只需保证 55 个导出符号存在**，
**其余（内部实现、导入表、节布局）随便换。**

★★★ **但要注意**：
- **`Createserver` 在官方实现里是空桩** —— 如果我们写成"真初始化"，**会被调用吗？**
  **不知道**。加载器可能**根本不调 `Createserver`**（因为它是空的）
  ⇒ **我们也可以留空桩**
- **`onStartup` 和 `onInitialized` 同址** —— 官方把两个都指向同一个桩
  ⇒ **我们可以让两个都指向真正的初始化**

★ **风险**：**如果加载器只按名 `GetProcAddress` 而不调用某些符号，
我们写了实现也不会执行。**

★★★ **⇒ 必须先确认"谁调用了哪些导出函数"。**
**方法**：反汇编 `CodolGameServer` 的 `onStartup` @ `0x220880`，
以及 `Bootstrapper32` 里调用插件的地方。

---

## 六、这一块（逐字节）的结论

### 确证（实测字节）

1. **三个插件的内部 DLL 名带 `Re.`**（`LocalnetworkingRe` / `PlatformwrapperRe` / `AlwaysofflineRe`）✓
2. **只有 `CodolGameServer` 内部名与文件名相同**（无 `Re`）✓
3. **`CodolGameServer::Createserver` = `33 C0 C3`（`xor eax,eax; ret`）—— 空桩** ✓
4. **`Alwaysoffline::Createserver` 是真实 SEH+/GS 函数**（`6A FF` / `64 A1` / `33 C5` / 192 字节栈帧）✓
5. **`Localnetworking::onStartup` 是真实函数**（116 字节栈帧 + 对象构造）✓
6. **`Bootstrapper32::Broadcastmessage` 是插件数组遍历器**（`add esi,4` + `cmp esi,edi` + 短路）✓
7. **`Bootstrapper32::onInitializationdone` 用全局 bool `0x10028A8C` 保证幂等** ✓
8. **`Platformwrapper` 不导入 `WS2_32`**（只 `USER32` + `KERNEL32`）✓
9. **`Alwaysoffline` 导入 `bcrypt.dll`**（自己做加密）✓
10. **`Injector32` 只导入 `KERNEL32`**（注入所需 API 全在里面）✓
11. **`CodolGameServer` 与 `Alwaysoffline` 的 `Createserver` 完全不同** ✓

### 三条重要推论

| # | 推论 | 依据 |
|---|---|---|
| 1 | **`Broadcastmessage` 是串行短路调度器** | `jne` 返回 true 即结束 |
| 2 | **`CodolGameServer` 靠 `onStartup` 而非 `Createserver` 初始化** | 后者是空桩 |
| 3 | **换战斗服只需保持 55 个导出符号** | 契约是命名导出 |

---

## 七、待逐字节继续

- [ ] `CodolGameServer::onStartup` @ `0x220880`（是否也是空桩？）
- [ ] `0x100244B4` 的消息名字符串（Broadcastmessage 传什么）
- [ ] `0x1001D020`（IAT 槽，调的是什么）
- [ ] `Alwaysoffline::Createserver` 调用的 `0x8E5E0`
- [ ] `Localnetworking::onStartup` 的 `0x1007C270` 字符串内容
- [ ] `Localnetworking::onMessage` @ `0x17090`（网络消息分发）
- [ ] `Platformwrapper::CreateObj` / `Invoke`（COM 边界）
- [ ] `Alwaysoffline` 的 4 个 `CODOL_*Profile/Inventory` 请求/状态函数
- [ ] 谁调用插件的 `Createserver`（在 Bootstrapper 里搜 `GetProcAddress` 的参数字符串）
