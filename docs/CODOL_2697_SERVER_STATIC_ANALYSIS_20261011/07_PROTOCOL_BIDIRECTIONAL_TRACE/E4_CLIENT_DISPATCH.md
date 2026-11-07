# E4 — 客户端侧静态协议分派分析

> 阶段 E · CODOL 2697 · client-side static only  
> 分析日期：2026-10-12  
> 边界：仅静态 PE 解析、反汇编、字符串/常量/调用点交叉检查。未启动客户端或服务端，未注入，未打补丁，未编译，未安装工具，未修改任何样本。  
> 等级：`VERIFIED`（具体指令或调用链直接支持）、`STATIC-INFERENCE`（有依据的语义解释）、`NOT-OBSERVED`（无运行时或互通证据）、`BLOCKED`（样本、恢复方式或工具条件不足）。  
> **互通结论：NOT-OBSERVED。本报告不能证明新客户端与服务端已经能够互通。**

## 0. 结论速览

| 主题 | 本次静态结论 | 等级 |
|---|---|---|
| 打包客户端身份 | 实际文件 SHA-256 与 manifest 声明一致 | `VERIFIED` |
| 主静态镜像身份 | `codol2697-static-candidate.bin` SHA-256、ImageBase、EP、时间戳与交接值一致 | `VERIFIED` |
| 主静态镜像性质 | 它是 **aplib 恢复的静态镜像**，不是运行时解包观测，也不是对 TenProtect 运行时内存的直接 dump | `VERIFIED`（文件与 PE 结构）；运行时等价性 `NOT-OBSERVED` / `BLOCKED` |
| Msg 字节读取核心 | `RVA 0x1AC1D0` 的分段/环形缓冲区复制逻辑可由指令直接确认；语义名称“Msg_ReadData”是推断 | 指令 `VERIFIED`；名称 `STATIC-INFERENCE` |
| `0xA2D90` | 存在 4 字节读取、游标推进和全局槽更新；不能确认它是 reliable command 读取器 | 指令 `VERIFIED`；语义 `BLOCKED/UNKNOWN` |
| `0xA2E50` | 客户端读取 `long(4) + short(2) + payload` 的格式与服务端 E3 的 `0x02` 负载高度匹配 | 格式 `VERIFIED`；与 `0x02` 的关系 `STATIC-INFERENCE`；实际分派 `BLOCKED/UNKNOWN` |
| `0x01 serverCommand` | 未定位可复现的客户端 opcode switch 或读取分支 | 搜索范围未命中，`BLOCKED/UNKNOWN` |
| `0x02 reliable command` | 找到高匹配格式读取函数，但未找到 `cmp/switch` 形式的 `0x02` 分派 | `STATIC-INFERENCE` / `BLOCKED/UNKNOWN` |
| `0x03 gamestate` | 找到 `gamestateupdate %d` 的真实字符串引用和状态/表更新候选，但未确认网络读取分支 | `STATIC-INFERENCE` / `BLOCKED/UNKNOWN` |
| `0x04 configstring` | 未定位可复现的网络读取/分派分支 | 搜索范围未命中，`BLOCKED/UNKNOWN` |
| `0x05/0x06` EOF/EOS | 未找到可复现的客户端 `0x06` 读取、终止判断或循环退出指令 | 搜索范围未命中，`NOT-OBSERVED` / `BLOCKED` |

## 1. 样本身份、来源与限制

### 1.1 manifest 声明的打包客户端

| 项目 | 值 |
|---|---|
| 绝对路径 | `D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetail.exe` |
| 大小 | `9,964,656` 字节 |
| SHA-256 | `353754047dbbfe3afbf6c7d97de3faca785b3d5d5e34a9053c820ee78814d6e1` |
| PE Machine | `0x14C` |
| PE Subsystem | `2` |
| PE ImageBase | `0x400000` |
| PE Timestamp | `0x554898DC` |
| 文件系统 LastWriteTime | `2015-05-07 03:53:54` |
| 打包特征 | 原始 `.text`/`.rdata`/`.data` 等区段被 TenProtect 包装；直接完整反汇编不可行 |
| 导入 | 仅导入 `codoMP_client_shipRetailBase.dll` 的 ordinal `#1` |

上述路径、大小、SHA-256 和时间戳已完成只读复核。manifest 的 `original_exe_sha256` 与该 SHA-256 一致：`VERIFIED`。

### 1.2 主静态镜像

| 项目 | 值 |
|---|---|
| 绝对路径 | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin` |
| 大小 | `12,571,648` 字节 |
| SHA-256 | `24b4ef2502d3661df178f557192534098c714353cf8c2a00a2ffb26af2bb97e4` |
| PE Machine | `0x14C` |
| PE Subsystem | `2` |
| ImageBase | `0x400000` |
| EntryPoint RVA | `0x74FF4F` |
| PE Timestamp | `0x554898DC` |
| 关键区段 | `.text` RVA `0x1000`；`.rdata` RVA `0x7AE000`；`.data` RVA `0x8F1000`；`.tvm0` RVA `0xD958000`；`.rimp` RVA `0xDC11000` |

**来源限制（必须保留）：** 该文件是已恢复的静态镜像。它可以提供 PE 结构和静态机器码，但没有证明这些静态字节与 TenProtect 在每个运行阶段解密/映射后的真实内存完全一致；也没有运行时断点、内存 dump 或初始化后 dump 作为对照。因此：

- 镜像本身的哈希和 PE 元数据：`VERIFIED`；
- 静态指令的字节级存在：`VERIFIED`；
- 该指令在运行时确实被加载并执行：`NOT-OBSERVED`；
- 静态镜像与实际运行时映射的完全等价性：`BLOCKED`。

### 1.3 manifest 与辅助 DLL

| 文件 | 绝对路径 | SHA-256 | 大小 | 证据 |
|---|---|---|---|---|
| manifest | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\manifest.json` | `34017bf787800678a66d277520869873c3352c713da883e9dce2d348f669da00` | 未在本报告重新展开 | `VERIFIED`；version=`2.6.9.7`，`original_exe_sha256` 与客户端一致 |
| client_room DLL | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\client_room2697.dll` | `120c4cfdd79a9a38d992598c30af3c5cabe754e7b3d17614074b4b8026ffc3a7` | `184,832` | manifest 组件哈希匹配，`VERIFIED` |
| loopback DLL | `D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\client_native_loopback.dll` | `53c6fbe264defc06629fef06f43a1ddd82fda716439432c354b5eb2ee4074829` | `125,440` | manifest 组件哈希匹配，`VERIFIED` |
| Base DLL | `D:\BaiduNetdiskDownload\CODOL.NET\Game\CODOL_2.6.9.7\codoMP_client_shipRetailBase.dll` | `b3f840927eba5ed7448fe6f92130d2450c9981a818696ab7f57cb48025ce609a` | 本次未作为主镜像完整分析 | `VERIFIED`（哈希复核） |

辅助 DLL 的导入表确认它们都导入 `WS2_32.dll` 的网络函数（例如 `WS2_32.WSAStartup`、`socket`、`connect`、`send`、`recv`、`htons`、`htonl`）。这只证明它们包含网络/传输代码，不证明它们实现 2697 客户端消息 opcode 分派：`STATIC-INFERENCE`，协议对应关系 `BLOCKED`。

## 2. 地址校验与可复现性

本轮不接受旧 `c_xref.va_refs` 的节相对伪 RVA。所有报告地址均由“文件偏移 → PE 区段 → RVA → VA”重新校验：

- `.text` 文件偏移：`fileoff = RVA - 0x1000 + 0x400 = RVA - 0xC00`
- `.rdata` 文件偏移：`fileoff = RVA - 0x7AE000 + 0x7ACE00 = RVA - 0x1200`
- `.data` 文件偏移：`fileoff = RVA - 0x8F1000 + 0x8EF800 = RVA - 0x1800`
- 本镜像 VA：`VA = ImageBase + RVA = 0x400000 + RVA`

因此报告中的 VA 只在明确写出时使用。像 `0x5AC1D0` 这样的值是 ImageBase 为 `0x400000` 时的 VA；其 RVA 为 `0x1AC1D0`，文件偏移为 `0x1AB5D0`。

### 2.1 搜索范围

已执行并在 `_data\e4_*` 中留下派生素材的范围：

1. 主镜像 PE 头部、区段表、ImageBase、EP、时间戳。
2. `.text` 内原始 `E8 rel32` 调用目标和直接调用点扫描，重点目标：
   - `RVA 0x1AC1D0`（Msg 字节复制核心）
   - `RVA 0x1ACB00`（数据/缓冲复制候选）
   - `RVA 0xA2D90`
   - `RVA 0xA2E50`
3. 全文件绝对 VA/指针引用扫描，重点协议字符串和候选函数地址。
4. 字符串扫描：`gamestateupdate`、`gamestateupdate %d`、`serverCommand`、`reliable`、`snapshot`、`configstring`、`EOF`、`UNEXPECTED_EOF`、`CG_ServerCommand`、`EXE_ERR_RELIABLE_CYCLED_OUT`、`EXE_ERR_NOT_RECEIVED`。
5. 简单 32 位缩放间接跳转表模式扫描，`jmp dword ptr [reg*4 + base]` 当前只列出 18 个命中；没有一个落在本次重点函数 `0xA2xxx`、`0x6Dxxx`、`0x6Exxx` 附近。
6. 关键函数的直接 `E8` 调用者和 `.rdata/.data` 函数指针引用搜索。
7. 辅助 DLL 的导入表与哈希身份；未把辅助 DLL 的网络导入提升为协议 opcode 证据。

**搜索未命中的限制：** 以上结果表示“在本恢复镜像、当前区段映射、当前线性反汇编和直接调用/指针搜索范围内未命中”。它不等于“客户端不存在该 opcode、分支或函数”。可能的遗漏来源包括：

- TenProtect 运行时解密/重定位；
- `.tvm0` 虚拟化/间接分派；
- 间接调用、vtable、注册表、对象方法；
- 跳转粘连、编译器内联、跳转表和未线性解码区域；
- 恢复镜像与运行时映射的差异。

## 3. Msg 游标与读取函数候选

### 3.1 Msg 字节复制核心：RVA `0x1AC1D0`

| 项目 | 值 |
|---|---|
| RVA | `0x1AC1D0` |
| VA | `0x5AC1D0` |
| 文件偏移 | `0x1AB5D0` |
| 等级 | 分段缓冲复制 `VERIFIED`；命名 `STATIC-INFERENCE` |

已确认的静态行为：

- 以 `ESI` 指向 Msg/缓冲区对象；
- 读取 `[msg+0x08]`、`[msg+0x0C]`、`[msg+0x10]`、`[msg+0x14]`、`[msg+0x18]`；
- 当读取偏移落在第一段时，从 `[msg+0x08] + offset` 复制；
- 落在第二段时，以 `[msg+0x18]`、`[msg+0x0C]` 进行第二段映射；
- 越界时不复制并返回失败/零长度候选。

其中“Msg_ReadData”是语义命名，不是符号表或导出名：`STATIC-INFERENCE`。

### 3.2 `RVA 0xA2D90`：4 字节读取和全局槽更新候选

| 项目 | 值 |
|---|---|
| RVA 边界 | `0xA2D90..0xA2E42` |
| VA | `0x4A2D90..0x4A2E42` |
| 文件偏移 | `0xA2190..0xA2242` |
| 等级 | 指令和读取调用 `VERIFIED`；可靠命令语义 `BLOCKED/UNKNOWN` |

关键可复现指令：

```asm
004a2da7  mov  ecx,[esi+0x18]
004a2daa  mov  eax,[esi+0x1c]
004a2dad  add  ecx,[esi+0x14]
004a2db1  lea  edi,[eax+4]
004a2db4  cmp  edi,ecx
004a2db6  jg   0x4a2dd4
004a2dbe  push 4
004a2dc0  push edx
004a2dc1  call 0x5ac1d0      ; RVA 0x1AC1D0；读取 4 字节
004a2dc6  mov  ebx,[ebp-0x408]
004a2dcf  mov  [esi+0x1c],edi ; cursor += 4
...
004a2dd4  mov  dword ptr [esi],1
004a2dda  or   ebx,0xffffffff
```

说明：

- `0xA2DA7..0xA2DB6` 计算并检查 `cursor + 4 <= [msg+0x18] + [msg+0x14]`；
- `0xA2DC1` 的真实目标为 `RVA 0x1AC1D0`；
- 成功时把 `[esi+0x1C]` 推进 4 字节；
- 失败时把 `[esi+0]` 置 1，并把读取值置为 `-1`；
- 之后访问 `[0x1A89500] xor 0x2B90AC87`，比较/更新 `+0x4014C`，并清空 `+0x40154 + ((value & 0xFF) << 10)` 槽。

**不能升级的结论：** 该函数确实包含一个 4 字节读取和全局槽清零，但未见足够的命令长度、字符串、序列号或命令执行证据。不能仅凭形状称其为 reliable command 读取器。该语义为 `BLOCKED/UNKNOWN`。

### 3.3 其他读取包装候选

| RVA | VA | 文件偏移 | 观察 | 等级 |
|---|---:|---:|---|---|
| `0x1AC800` | `0x5AC800` | `0x1ABC00`（`RVA-0xC00`） | 有符号 16 位读取包装候选 | 指令候选 `VERIFIED`；语义 `STATIC-INFERENCE` |
| `0x1AC850` | `0x5AC850` | `0x1ABC50` | 32 位读取包装候选 | 指令候选 `VERIFIED`；语义 `STATIC-INFERENCE` |
| `0x1AC8A0` | `0x5AC8A0` | `0x1ABCA0` | 32 位/浮点读取及默认/错误路径候选 | `STATIC-INFERENCE` |
| `0x1ACAA0` | `0x5ACAA0` | `0x1ABEA0` | 16 位读取候选；ABI 调用者仍需确认 | `STATIC-INFERENCE` |
| `0x1ACA10` | `0x5ACA10` | `0x1ABE10` | 字符串读取候选；逐字节、上限约 `0x400`、NUL/newline/`-1` 结束和替换逻辑候选 | 指令 `VERIFIED`；语义 `STATIC-INFERENCE` |
| `0x1ACB00` | `0x5ACB00` | `0x1ABF00` | 数据/缓冲区复制候选；检查 `cursor + length <= [msg+0x14]`，失败置 `[msg]=1` | 指令 `VERIFIED`；语义 `STATIC-INFERENCE` |

上表不是导出表或符号确认表，而是反汇编得到的读取函数候选集合。`0xA2E50` 内部的确切调用目标 `0x1AC1D0` 和 `0x1ACB00` 已完成映射复核。

## 4. 服务端消息 opcode 分派搜索

### 4.1 核对表

| 目标 | 客户端静态命中 | 结论 |
|---|---|---|
| `0x01 serverCommand` | 未找到可复现的 `0x01` reader/switch；未找到 `CG_ServerCommand:` 的直接代码引用 | 搜索范围未命中，`BLOCKED/UNKNOWN` |
| `0x02 reliable command` | 未找到 `cmp ...,2` 后直达 `0xA2E50` 的 switch；仅找到 `0xA2E50` 的 `long + short + payload` 格式匹配 | 分派 `BLOCKED/UNKNOWN`；格式关系 `STATIC-INFERENCE` |
| `0x03 gamestate` | 未找到可确认的读取/switch；仅找到 `gamestateupdate %d` 字符串引用和 `0xA2660` 状态表更新候选 | `STATIC-INFERENCE` / `BLOCKED/UNKNOWN` |
| `0x04 configstring` | 未定位协议读取或字符串消费分支 | 搜索范围未命中，`BLOCKED/UNKNOWN` |
| `0x05 EOF/EOS` | 未定位 `0x05` 的读取、终止或循环退出判断 | 搜索范围未命中，`BLOCKED/UNKNOWN` |
| `0x06 EOF/EOS` | 未定位 `0x06` 的读取、终止或长度边界判断；服务端写入 0x06 只能作为服务端事实 | `NOT-OBSERVED` / `BLOCKED` |

### 4.2 未命中细节

- 简单缩放跳转表扫描只找到 18 处，均不在 `0xA2xxx`、`0x6Dxxx`、`0x6Exxx` 的重点区域附近。
- 对 `0xA2D90`、`0xA2E50` 做直接 `E8` 调用点和 `.rdata/.data` 绝对函数指针搜索：在当前范围内均未命中直接调用者。
- 这不等于“无调用者”或“客户端未使用”。它只表示直接 `E8`/绝对指针路径未闭合；vtable、对象方法、虚拟化或间接分派仍可形成调用：`BLOCKED`。
- 服务端 E2 的证据是 `_SV_EndClientSnapshot RVA 0x87104` 根据 `_CODOL_Target2697ArchivesActive` 选择 `0x05/0x06`；服务端 gamestate/configstrings 新通道也以 `0x06` 结束。该事实**不能**推导出客户端支持 `0x06`。

## 5. Gamestate、configstring 和初始化状态候选

### 5.1 已校验字符串引用

| 字符串 | 字符串 RVA / VA | 文件偏移 | 真实代码引用 | 结论 |
|---|---|---:|---|---|
| `gamestateupdate %d` | RVA `0x8B8378` / VA `0xCB8378` | `0x8B7178` | `0x56893`，文件偏移 `0x55C93`；`0xA2994`，文件偏移 `0xA1D94` | 引用本身 `VERIFIED`；是否为协议 parser `BLOCKED` |
| `gamestateupdate` | RVA `0x8C6334` / VA `0xCC6334` | `0x8C5134` | `0x1F14F7`，文件偏移 `0x1F08F7` | 真实代码引用 `VERIFIED`；更像命令/字符串处理上下文，不能升格为网络分派 |
| `EXE_CONFIGSTRINGMISMATCH` | RVA `0x8B835C` / VA `0xCB835C` | `0x8B715C` | `0x18BEBB`，文件偏移 `0x18B2BB` | 位于诊断字符串比较链，非已确认 configstring reader |
| `UNEXPECTED_EOF` | RVA `0x8B3270` / VA `0xCB3270` | `0x8B2070` | 仅发现 `.data` 指针 `RVA 0x932584`，未发现直接代码引用 | 不支持客户端读取/判断 `0x06` |
| `CG_ServerCommand:` | RVA `0x8B5EC9` | `0x8B4CC9` | 未发现直接 VA 代码引用 | `BLOCKED/UNKNOWN` |
| `EXE_ERR_RELIABLE_CYCLED_OUT` | RVA `0x8B5EDC` | `0x8B4CDC` | 未发现直接 VA 代码引用 | `BLOCKED/UNKNOWN` |
| `EXE_ERR_NOT_RECEIVED` | RVA `0x8B5F0C` | `0x8B4D0C` | 未发现直接 VA 代码引用 | `BLOCKED/UNKNOWN` |

### 5.2 `RVA 0xA2660` 状态/表更新候选

| 项目 | 值 |
|---|---|
| RVA 范围候选 | `0xA2660..A2D90` 邻近区域 |
| VA | `0x4A2660` |
| 文件偏移 | `0xA1A60` |
| 关键证据 | 读 signed short 计数；循环调用 `0x1AC1D0`；维护 `0x1B47EE4 + 0x775C`、`0x1B6F640`、`0x2BD0A40` 表和 `0x1DD7` 上限 |
| `gamestateupdate %d` 引用 | `0xA2994`（文件偏移 `0xA1D94`） |
| 等级 | 函数调用/内存操作 `VERIFIED`；gamestate 初始化语义 `STATIC-INFERENCE`；网络 opcode 分派 `BLOCKED/UNKNOWN` |

可复现的早期指令：

```asm
004a2676  push 0x775c
004a267b  push 0
004a267d  push 0x1b47ee4
004a2684  call 0xb50900
004a2689  mov  dword ptr [0x1b6f640],1
...
004a26b2  call 0x5ac1d0       ; RVA 0x1AC1D0，读取 2 字节计数
004a26e0  mov edx,esi
004a26e2  call 0x44c8c0
...
004a2702  cmp edi,0x1dd7
...
004a2728  mov cl,byte ptr [edi+0x2bd0a40]
```

该函数可以作为“gamestate 相关初始化/记录处理候选”，但不能说它已经证明：

- 客户端从网络消息读取 `0x03`；
- `gamestateupdate %d` 是协议分派日志；
- 配置字符串已经进入可用的客户端初始化状态机。

因此 gamestate 的网络进入路径仍为 `BLOCKED/UNKNOWN`。

## 6. Snapshot、delta 和 EOF 候选

### 6.1 `RVA 0x6E060`：短计数循环候选

| 项目 | 值 |
|---|---|
| RVA | `0x6E060` |
| VA | `0x46E060` |
| 文件偏移 | `0x6D460` |
| 观察 | 先读取 short 参数/计数，循环内多次通过 `0x1AC1D0` 读取 short/long 组合；维护 `0x2CFCC68` 每项 `0x20` 字节的表和全局 `0x74549A4` |
| 等级 | 读取/循环指令 `VERIFIED`；snapshot/delta 语义 `STATIC-INFERENCE`；`0x06` 或 EOF 分支 `BLOCKED/UNKNOWN` |

### 6.2 `RVA 0x6D340`：复杂消息解析候选

| 项目 | 值 |
|---|---|
| RVA | `0x6D340` |
| VA | `0x46D340` |
| 文件偏移 | `0x6C740` |
| 观察 | 手工读字节、使用 `0x1AC1D0`、使用 `0x1ACB00` 边界复制路径、检查 `0x7FFC` 边界；附近可观察到 `cmp eax,5` 和 `cmp eax,6` |
| 等级 | 代码模式 `VERIFIED`；把 `5/6` 解释为协议 `0x05/0x06` `BLOCKED/UNKNOWN` |

**重要限制：** 上述 `cmp eax,5/6` 在当前线性上下文中不能证明是网络 opcode switch。没有发现从读取字节到该比较、再到明确 snapshot/gamestate 状态转换的闭合链，所以不能把该函数写成已验证的 `0x05/0x06` 分派器。

### 6.3 EOF/EOS 结论

已检查的服务端 `0x06` 语义是：

- `_SV_EndClientSnapshot RVA 0x87104` 分支在 `_CODOL_Target2697ArchivesActive` 条件下选择 `0x05` 或 `0x06`；
- gamestate/configstrings 的新通道写入函数也以 `0x06` 结束。

客户端侧目前：

- 未找到真实文件偏移校验过的 `0x06` 读取点；
- 未找到 `0x06` 后终止循环、结束快照、切换状态或长度校验的闭合链；
- `UNEXPECTED_EOF` 只有 `.data` 指针引用，没有直接代码引用证据。

因此客户端对 `0x06` 的读取/终止判断：`NOT-OBSERVED`、`BLOCKED`。不能写成“客户端不支持”，也不能写成“客户端支持”。

## 7. Reliable command 格式匹配

### 7.1 服务端 E3 对照格式

服务端 E3 已确认的新格式为：

```text
0x02 | long(sequence/参数) | short(length) | profile_buf[length]
```

旧格式回退为：

```text
0x01 | long(sequence/参数) | NUL-terminated command string
```

这些结论来自服务端 E3 报告，本次没有重扫服务端。

### 7.2 客户端 `RVA 0xA2E50` 强候选

| 项目 | 值 |
|---|---|
| RVA 边界 | `0xA2E50..0xA2FDE` |
| VA | `0x4A2E50..0x4A2FDE` |
| 文件偏移 | `0xA2250..0xA23DE` |
| 等级 | 读取格式 `VERIFIED`；与服务端 `0x02` 的绑定 `STATIC-INFERENCE`；实际 opcode 分派 `BLOCKED/UNKNOWN` |

关键可复现指令：

```asm
004a2e71  lea edi,[eax+4]
004a2e74  mov [ebp-0x410],ecx
004a2e7a  cmp edi,ecx
004a2e7c  jg  0x4a2ea0
004a2e84  push 4
004a2e86  push ecx
004a2e87  call 0x5ac1d0      ; 读取 4 字节，结果最终进入 EBX
004a2e8c  mov ebx,[ebp-0x40c]
...
004a2eac  lea edi,[eax+2]
004a2eaf  cmp edi,ecx
004a2eb1  jg  0x4a2fdf
004a2ebd  push 2
004a2ebf  push edx
004a2ec0  call 0x5ac1d0      ; 读取 2 字节 length
004a2ec8  movsx edi,word ptr [ebp-0x40c]
004a2ecf  mov eax,0x3fc
004a2edd  cmp di,ax
004a2ee0  jbe 0x4a2ef1
...
004a2f02  call 0x5acb00      ; 复制 payload
...
004a2f7a  cmp eax,0x400
004a2fc6  call 0x631ce0      ; payload 复制完成路径
```

函数内部可确认的顺序：

1. 读取 4 字节，保存到 `EBX`；
2. 检查游标后读取 2 字节，按 `signed short` 处理 length；
3. 上限常量为 `0x3FC`；
4. 调用 `RVA 0x1ACB00` 复制 payload；
5. 在 `[0x1A89500] xor 0x2B90AC87` 所指全局结构中，按 `EBX & 0xFF` 选取 `+0x40154 + (index << 10)` 的约 `0x400` 字节槽；
6. 槽内写入 `0x21`、NUL、short length、payload，并受 `0x400` 边界检查。

与服务端 E3 的关系：

- 服务端新格式的“`long + short + data`”负载与客户端 `0xA2E50` 的读取顺序高度一致；
- 客户端函数本身未见 `0x02` opcode 的读取，也未见直接调用者；
- 因此只能写成“客户端存在与服务端 `0x02` 负载格式匹配的读取函数候选”，不能写成“客户端已验证处理 `0x02` reliable command”。

**冲突处理：** 当前未发现客户端对 `0x02` 的语义反证；但也没有发现 `0x02` 分派点。任何“客户端已支持 `0x02`”的说法必须保持 `STATIC-INFERENCE`，运行互通保持 `NOT-OBSERVED`。

## 8. 辅助网络 DLL 的边界

`client_room2697.dll` 和 `client_native_loopback.dll` 的哈希、PE ImageBase、导入表已复核：

- 两者 ImageBase 均为 `0x10000000`；
- 两者均导入 `WS2_32.dll` 的 socket 收发函数；
- 这说明它们是传输/房间/loopback 相关模块的静态候选；
- 目前没有完成其函数级消息 opcode 或 Msg 游标对应链；
- 因此不能把 `WS2_32` 导入、DLL 名或 loopback 名升级为“2697 协议分派已实现”的证据：`STATIC-INFERENCE`；具体协议绑定 `BLOCKED`。

## 9. E4 兼容性矩阵

| 主题 | 服务端写入证据 | 客户端读取证据 | 当前结论 |
|---|---|---|---|
| Gamestate 注册门控 | E1：`0xA3DAB` 双门控；`0xA3E00` 放行；`0xA21B8` 编码 `03...06`；E1 已定位 `0xA3EA0` | 未定位 `0x03` 网络读取/switch；仅发现 `gamestateupdate %d` 引用 `0xA2994` 和 `0xA2660` 状态/表更新候选 | `STATIC-INFERENCE`；网络接收与初始化状态机 `BLOCKED/UNKNOWN` |
| EOF `0x06` | E2：`_SV_EndClientSnapshot 0x87104` 选择 `0x05/0x06`；gamestate/configstrings 新通道写 `0x06` | 未找到真实指令级 `0x06` 读取、长度检查或终止判断 | `NOT-OBSERVED` / `BLOCKED` |
| Reliable `0x02` | E3：`0x02 + long + short + data`，有 `0x01` 回退 | `0xA2E50` 读取 `long + short + payload`；未找到 `0x02` opcode switch | 格式匹配 `VERIFIED`；opcode 分派 `STATIC-INFERENCE`；互通 `NOT-OBSERVED` |
| Snapshot | E2：`0xA4860`、`0xA4FA0` 服务端写入链；旧 legacy 见 `0x00/0x05` | `0x6E060` 短计数循环、`0x6D340` 复杂解析候选；未闭合 delta 解码和 `0x06` | `STATIC-INFERENCE` / `BLOCKED` |
| Configstring | E1：`0xA0468` 写 `0x04`，终止 `0x06` | 未定位读取/消费分支；`EXE_CONFIGSTRINGMISMATCH` 无直接 reader 证据 | 搜索范围未命中，`BLOCKED/UNKNOWN` |
| ServerCommand `0x01` | 旧版研究记录与 legacy 函数存在，但不作为本次客户端匹配前提 | 未定位 `0x01` reader/switch 或 `CG_ServerCommand` 调用链 | 搜索范围未命中，`BLOCKED/UNKNOWN` |

## 10. 最终回答

### 10.1 哪条协议路径形成了最完整的客户端静态双向证据链？

**Reliable command 路径相对最完整，但仍不是完整双向证据链。**

- 服务端 E3 有 `0x02` 写入格式和 `0x01` 回退分支；
- 客户端 `0xA2E50` 有高度匹配的 `long + short + payload` 读取和槽更新；
- 但客户端没有找到 `0x02` opcode switch，也没有直接调用者，实际运行时执行链未闭合；
- 因此结论最多为格式匹配 `VERIFIED` + 语义绑定 `STATIC-INFERENCE`；互通为 `NOT-OBSERVED`。

### 10.2 哪些字段或 opcode 已确认两端一致？

在当前 E4 证据范围内：

- **字段序列**：客户端 `0xA2E50` 读取 `long + short + payload`，与服务端 E3 新 reliable 格式的负载序列一致：`VERIFIED`；
- **opcode `0x02`**：客户端没有找到读取/分派 `0x02` 的确切指令：`BLOCKED/UNKNOWN`；
- **`0x01 serverCommand`**：未确认；
- **`0x03 gamestate`**：未确认协议接收分支；
- **`0x04 configstring`**：未确认；
- **`0x05/0x06` EOF/EOS**：未确认客户端读取或终止逻辑；
- 因此目前能确认的是“负载字段形状匹配”，不能确认“两端 opcode 分派和状态机一致”。

### 10.3 当前最主要的兼容性障碍是什么？

1. 打包客户端被 TenProtect 包装，不能直接完整反汇编；
2. 主样本是恢复静态镜像，不是运行时解包观测，静态字节与运行时映射的等价性未证明；
3. 客户端 opcode switch 没有线性定位，虚拟化/间接分派使直接 `E8` 调用图不完整；
4. 客户端 `0x06` 的读取和终止判断完全未闭合；
5. 所有互通结论都缺少运行时/抓包/内存观测，必须保持 `NOT-OBSERVED`。

### 10.4 下一步最小、最有价值的静态验证任务

优先级从高到低：

1. 追查 `0xA2E50` 的间接调用者、vtable/对象方法引用，确认是否存在读取 `0x02` 后的调用链；
2. 在第 1 项未闭合前，继续以 `.tvm0` 和间接跳转表为中心，寻找客户端服务端消息 `switch`，而不是重复全文件字符串扫描；
3. 对 `0xA2660` 和 `0x6E060` 的上层调用者建立最小对象/状态图，分别确认 gamestate 初始化入口和 snapshot delta 循环入口。

这仍是静态任务；在得到运行时或互通观测之前，不得把上述路径写成已实操可用。
