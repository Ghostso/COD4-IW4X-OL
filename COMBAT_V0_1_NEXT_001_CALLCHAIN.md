# COMBAT_V0_1_NEXT_001_CALLCHAIN.md

> 任务：COMBAT-V0.1-NEXT-001 —— 纯静态定位"客户端为什么没有向本地第一版战斗服务器发起连接"
> 镜像：`CODOLServer/_mainline/_dyn100_run_20260925_182324/live/image_best.bin`（10,899,456 B）
> 基址：**0x400000**（PE32，`magic=0x10B`，`e_lfanew=0x128`，无 TLS/重定位修正）
> 本次分析**未启动、未注入、未附加客户端进程；未读取外部进程内存**。
> 分析基座与全部脚本：[`_combat_next001/`](_combat_next001/)（`peimg.py` + `a1..j1_*.py`）

---

## 0. 结论先行：完整链条已闭合

```
21/5 findSessions 响应
  -> session 对象 (67B 地址块 @+0)
  -> [0x6294A3/0x6294AF] 桥接(Bridge) 把地址块送进 battle-connect
  -> [0x470360] battle-connect：拷贝地址块 69B、构造地址对象、写入 netchan +0x14..+0x28
  -> [0x470467] 置全局网络状态 [0x76446B0] = 3
  -> [0x5C05F0] 每帧战斗状态机：switch(state-3) -> case0
  -> [0x5C0729] 组装 "getchallenge 0 \"%s\""（20B 摘要）+ 把 netchan +0x14..+0x28 压栈
  -> [0x675260] -> [0x6751F0] -> [0x6750A0] -> call [0xCA8128]（网络消息投递）
  -> 首个战斗数据包（NAT 遍历 29B -> DTLS init 16B ...）
```

**但这条链在最前面还有一个更早的闸门，而且它正是客户端从未发起连接的原因**（详见
[COMBAT_V0_1_NEXT_001_BLOCKER.md](COMBAT_V0_1_NEXT_001_BLOCKER.md)）：

```
0x632680 mmbook-accepted handler
  0x63268D cmp byte [esi+0x278], 0      ; 闸门 1
  0x63269B cmp [0x76446b0], 3           ; 闸门 2（>=3 即退出）
  0x6326AA cmp [esi+0xe360], edi        ; 闸门 3（预约索引 <0 即退出）
  0x6326B9 cmp [ebp+8],  [esi+0x3a048]  ; 闸门 4  ← ★ A（客户端预约 u64 低半）
  0x6326C8 cmp [ebp+0xc],[esi+0x3a04c]  ; 闸门 5  ← ★ B（高半）
         jne 0x632916  -> ret 0x14      ; ★ 任一不等 = 整个 handler 立刻返回
  0x6326DF call 0xC3C678 (strncmp "mmbook accepted", 0xf)
```

**闸门 4/5 比较的是"mmbook accepted 这条消息自带的 u64"与"客户端为本次预约记下的 u64"。**
只有它俩相等，才会继续走到 0x63280B 置 accepted 闩锁、0x632824 通知 listener、
0x63285A 调用桥接 0x6293B0 —— 也就是**才会去连战斗服**。

---

## 1. 证据等级约定

| 等级 | 含义 |
|---|---|
| **CONFIRMED** | 反汇编逐指令可复核；数据流两端都在同一函数内可见 |
| **HIGH** | 反汇编可复核，但一端跨越未解出的运行时对象/未命名的动态解析函数 |
| **INFERRED** | 由指令形态与相邻常量推断，缺一个直接证据 |
| **UNKNOWN** | 本次镜像内**未找到**证据；明确指出缺什么 |

> 本镜像的 PE **导入目录被剥离**（`DataDirectory[1].RVA=0x0E5DC635, Size=0`），
> 且镜像内**不存在** `ws2_32` / `sendto` / `recvfrom` / `GetProcAddress` / `LoadLibrary` 字符串。
> 因此**任何"导入函数 → 调用者"的推断都无法在本镜像内建立**。
> 下文所有函数级结论一律走**控制流交叉引用**（`E8 rel32` 直接 call 目标 + 数据段函数指针表），
> 不靠导入表或字符串命中认定调用关系。

---

## 2. 镜像布局与地址换算

| section | VA | VSize | RawPtr | RawSize |
|---|---|---|---|---|
| `.tp3` | 0x001000 | 0x8A689A | 0x001000 | 0x8A7000 |
| `.tp3\0a` | 0x8A8000 | 0x16DA70 | 0x8A8000 | 0x16E000 |
| `.tp3` | 0xA16000 | 0x0DBB1CC0 | 0xA16000 | 0x62000 |
| `.tp3` | 0x0E5C8000 | 0x31 | 0xA78000 | 0x1000 |
| `.tp3` | 0x0E5C9000 | 0x9228 | 0xA79000 | 0xA000 |
| `.tp3` | 0x0E5D3000 | 0x4000 | 0xA83000 | 0x4000 |
| `.tp3` | 0x0E5D7000 | 0x82000 | 0x771000 | 0x6000 |

该文件是**连续 VA 区间 0x401000..0xCA8000 的内存转储**：section[0] 的
`vaddr == rawptr == 0x1000`，故 **file offset == VA − 0x400000**。后续 4 个 section
则是追加的独立区段（各自 rawptr 声明）。

---

## 3. 完整调用链（按执行顺序）

### 3.1 【A】listener 注册/触发的定位

**监听链表头 = 匹配对象 `+0x4`**（`[esi+4]`），节点结构：
`+0x0`=对象指针、`+0x4`=next。

| RVA | 指令 | 说明 |
|---|---|---|
| `0x632824` | `mov edi, [esi+4]` | 取链表头 |
| `0x63282E` | `test edi, edi` / `je 0x632846` | 空链表跳过 |
| `0x632832` | `mov ecx, [edi]` | 节点 → 对象 |
| `0x632834` | `mov eax, [ecx]` | 对象 → vtable |
| `0x632836` | `mov edx, [eax+0x24]` | **通知槽 = vtable+0x24** |
| `0x632839` | `mov edi, [edi+4]` | next |
| `0x63283C/3E` | `push 0` / `push 1` | 参数 (1, 0) |
| `0x632840` | `call edx` | **触发通知** |

**同一函数内第二处广播**（参数不同：`push 2` / `push 0`，槽 = `vtable+0x24`）：
`0x6328A5` — `mov ecx,[edi]` … `0x6328A9 mov edx,[eax+0x24]` … `0x6328B3 call edx`。

**注册源**：本镜像内**未找到**把节点写进 `[esi+4]` 的注册函数。
已确认的是**两个 listener 对象的 vtable 地址**（由 data 段引用 `0x632680` 的位置给出）：

| vtable VA | 文件偏移 | 前 8 个槽 |
|---|---|---|
| `0xDC73B0` | 0x9C73B0 | `632680` `62E9F0` `62CA60` `62C580` `629730` `6297A0` `8435D0` `850A40` |
| `0xDC7850` | 0x9C7850 | `632680` `62E9F0` `62CA60` `62C580` `629730` `6297A0` `8435D0` `9DDFF0` |

两个 vtable 的**槽 0 都是 0x632680**（即 accepted handler 本身被注册为回调），
前 6 槽完全相同，只有第 7/8 槽不同 → 它们是**同一个类族的两个实例**。
**未命名（UNKNOWN）**：这两个 vtable 属于哪个类、在何处被 new 出来并挂到 `[esi+4]`。

### 3.2 【B】battle UDP socket 创建与地址写入

**镜像内找不到直接调用 `socket()/connect()/sendto()/recvfrom()` 的代码**，因为导入被剥离
（§1）。但找到了一条**完整的 UDP socket 创建链**，以及**地址写入 netchan 的确切位置**。

**(B-1) 地址写入 netchan（本任务的关键 step）**

| RVA | 指令 | 说明 |
|---|---|---|
| `0x470471` | `mov edx,[eax+0x47]` + `rep movsd`(16 dwords) + `movsw` + `movsb` | 从 `[esi]` 拷贝 **69 B**（64+4+1）到 `[ebp-0xb8]` |
| `0x470481` | `mov ecx,[eax+0x43]` | 读源 **+0x43** |
| `0x47048A` | `mov ecx,[eax+0x4b]` | 读源 **+0x4b** |
| `0x470492` | `mov edx,[eax+0x4f]` | 读源 **+0x4f** |
| `0x470498` | `mov ecx,[eax+0x53]` | 读源 **+0x53** |
| `0x4704A0` | `mov edx,[eax+0x57]` | 读源 **+0x57** ← 需要 ≥ 0x5B 字节 |
| `0x4704AD/0x4704B3/0x4704BE` | `call 0x7BFD70` | 地址/端点对象构造；成功后 `al=1` |
| `0x4704CA` | `push 0xDB45C4` = `"EXE_HOSTUNREACH"` | **失败分支**：主机不可达 |
| `0x470510` | `mov [ebx+0x14], edx` | 写 netchan **+0x14** |
| `0x470516` | `mov [ebx+0x18], eax` | netchan **+0x18** |
| `0x47051C` | `mov [ebx+0x1c], ecx` | netchan **+0x1c** |
| `0x470522` | `mov [ebx+0x20], edx` | netchan **+0x20** |
| `0x47052D` | `mov [ebx+0x24], eax` | netchan **+0x24** |

其中 `ebx = [0x331C0C8] ^ 0xD362501F`（0x47040E/0x470421），即 **netchan 对象指针**，
槽位在 `[0x331C0C8]`。

**(B-2) 每帧状态机读取同一组 netchan 偏移**

| RVA | 指令 |
|---|---|
| `0x5C072E` | `mov edx,[ebx+0x14]` |
| `0x5C0731` | `mov ecx,[ebx+0x18]` |
| `0x5C073B` | `mov edx,[ebx+0x1c]` |
| `0x5C0741` | `mov ecx,[ebx+0x20]` |
| `0x5C0747` | `mov edx,[ebx+0x24]` |
| `0x5C074A` | `mov ecx,[ebx+0x28]` |
| `0x5C0734-0757` | 把 6 个 dword（24B）压栈 → `0x5C075A call 0x675260` |

**这就是"endpoint → 首个战斗包"的合流点**：地址由 0x470510 写进 netchan，
同一帧稍后被 0x5C072E 读出并送进发包路径。**CONFIRMED**。

**(B-3) UDP socket 创建（独立 UDP/URI 子系统）**

| RVA | 说明 |
|---|---|
| `0xC7B8F0` | socket 创建函数入口；`call 0xC7B810` 解析协议 → `cmp eax,-1` |
| `0xC7B966` | `mov eax,[edi+4]` / `dec eax` / `cmp eax,6` / `jmp [eax*4+0xC7BA1C]` → **按协议类型的 7 路分派** |
| `0xC7B97B/0xC7B982/0xC7B989` | 三个协议分支，各自 `call 0xC7BB00 / 0xC7BAF0 / 0xC7BB10`（`0xC7BB10(1)` 疑似 SOCK_DGRAM 类参数） |
| `0xC7B99A` | `push 1` / `push esi` / `call 0xC7BB20` → 对 fd 设置选项（FD_CLOEXEC 形态） |
| `0xC7B9AE` | `call 0xC7B510` → 解析目标地址 |
| `0xC5D7CA` / `0xC5D899` | 引用 `"udp://%s:%d"`；`0xC5D7CA call 0xC3F57E`（sprintf）；`0xC5D7EF call 0xC7B8F0` |

⇒ **HIGH**：这是一条 POSIX 风格的 UDP socket 创建 + 地址解析链，但
①它的两个调用点都在 `0xC5D7xx` 的**连接表枚举**里，与战斗 netchan 的关系未建立；
②`0xC7BB00/0xC7BAF0/0xC7BB10/0xC7B510` 的具体系统调用无法在剥离导入的镜像内命名。

### 3.3 【C】endpoint 数据流（21/5 → netchan）

**(C-1) 桥接函数 `0x6293B0`**（被 accepted handler 在 `0x63285A` 调用）

| RVA | 指令 | 说明 |
|---|---|---|
| `0x6293D0` | `push 1` / `call 0x63AD20` | 入口副作用 |
| `0x6293DC/0x6293E6` | `mov ecx,0xC9113A8 / 0xC9113B0` + `call 0xB75D90` | 两个维护调用 |
| `0x62942B` | `call 0xB95C50` （ecx=匹配对象, 参数=esp+0x14） | ★ 解析地址块 |
| `0x629434/0x62943D` | `call 0xB74140` / `call 0xB74060` | 初始化两个局部对象 |
| `0x629442` | `push 0x150` / `push 0` / `push esp+0x18` / `call 0xC42DE0` | ★ 把 **esp+0x18 起 0x150 B 清零** |
| `0x62945F` | `call 0xB74BC0` | 对 esp+0x18 做初始化 |
| `0x629464-0x6294A3` | 从 `[esi+0x10]/[esi+0x14]`、`[esi+0x1cc..0x1d8]`、`[0x849B87C]` 取值写入 `esp+0x5b/0x5f/0x6b/0x6f` | 组装局部地址块 |
| `0x6294AF` | `mov ecx, esp+0x18` / `call 0x470360` | ★ **调用 battle-connect**（`E8 rel32` 直接调用；全镜像内 `0x470360` **只有这一个** `E8` 调用者） |

**★ 关键尺寸结论**：battle-connect 在 `0x470471` 读取源对象偏移到 **+0x57**，
而桥接只清零了 **0x150 B** —— 0x5B < 0x150，**尺寸自洽**。
结合 `codol_crypto.py` 内已冻结的注释
"*`0xB95C50` 要求地址块长度 0x43(=67)*"，**在本镜像内独立证实：战斗地址块是 67 字节**，
且它来自 `0xB95C50` 的输出缓冲 / 桥接构造的 0x150 缓冲区，**不是** `[ebp+0x10]` 处的原始消息。

**(C-2) `0x6293B0` 的两个调用者**

| 调用点 | 上下文 | 含义 |
|---|---|---|
| `0x63285A` | accepted handler PASS 路径，前一条为 `0x632852 lea ecx,[eax+esi+0x7470]`，`0x632859 push esi` | **mmbook accepted → 战斗** |
| `0x62CD8B` | 函数 `0x62CD2F`：`mov [edi+0x7230],1`、`mov [edi+0xe360],0`、清 0x238 字节、`lea esi,[edi+0x7238]`、`push edi` | **预约/会话槽初始化 → 战斗**（非 accepted 路径） |

**(C-3) 两个分支的地址/传输差异**

| 分支 | 地址来源 | 传输 |
|---|---|---|
| accepted 路径（`0x63285A`） | 桥接内 0xB95C50 解析结果 + `[esi+0x1cc..]` | 同一 netchan，后续帧进入 `0x5C05F0` case0（getchallenge） |
| 槽初始化路径（`0x62CD8B`） | 同一桥接函数 | 同上 |

两者**共用同一个桥接与同一个 netchan**，未发现"不同分支用不同地址或不同协议"的证据 →
该问题**UNKNOWN**（未否证，也未证实）。

**(C-4) `mmbook accepted` 是否参与 socket 创建**

**不参与。** accepted handler 的作用是**触发桥接**（`0x63285A`）；
真正把地址写进 netchan 的是桥接调用的 `0x470360`。
accepted 消息**只影响会话状态并触发**（`[esi+0x288]=1`、`[0x849B61C]=1`），
但它**同时携带一个必须匹配的 u64**（见 §0 闸门 4/5）—— 这是本任务的**首要阻断点**。

### 3.4 【D】首个战斗数据包的发送路径

**(D-1) 发送前的闸门（每帧）**

| RVA | 指令 | 说明 |
|---|---|---|
| `0x5C2A80` | 每帧驱动函数；`0x5C2A9B cmp byte [0x76446A1], 0` / `je 0x5C2BB6` | 网络总开关 |
| `0x5C2A80` 体内依次调用 `0x5B7170`、`0x516310`、`0x5C2680`、**`0x5C05F0`**、`0x5C2200`、`0x768FD0`、`0x5C25A0`、`0x46F1A0`、`0x5C2920` | 组帧顺序 |
| `0x5C068D` | `cmp byte [esi+0x278], 0` / `je 0x6328EB`（退出） | **闸门 A** |
| `0x5C069B` | `cmp [0x76446B0], 3` / `jge 0x6328EB`（退出） | **闸门 B**：状态 < 3 才继续 |
| `0x5C0620/0x5C0635-0647` | `eax=[0x76446B0]`；必须 ∈ {3,4,5,6} | 取状态 |
| `0x5C0707` | `jmp [eax*4+0x5C0F3C]`（表：`0x5C070E`/`0x5C0776`/`0x5C0E07`/`0x5C0EBB`） | `switch(eax-3)` |

**调度表语义（由各 case 内字符串确定）**

| case | 目标 | 字符串证据 | 阶段 |
|---|---|---|---|
| 0 | `0x5C070E` | `"getchallenge 0 \"%s\""`、`"EXE_CLIENTFAILEDTOCHALLENGE"` | **getchallenge** |
| 1 | `0x5C0776` | `"name"`、`"clantag"`、`"xuid"`、`"natType"`、`"rank"`、`"clan"`、`"901"`、`"2490"`、`"checksum"`、`"challenge"`、`"statver"` | **connect** |
| 2 | `0x5C0E07` | `"stats"`、`"heartbeat"` | stats/heartbeat |
| 3 | `0x5C0EBB` | `"EXE_ERR_CLIENT_CMD_OVERFLOW"`、`"EXE_MATCHENDED"` | 结束 |

⇒ **`[0x76446B0]==3` 是唯一会产出 getchallenge 的取值。** 写入点只有 `0x470467`（置 3）。
（另四处写入：`0x470467=3`、`0x5BE90A=7`、`0x5BEA8B=4`、`0x77C343=0`、`0x813D34=7`。）

**(D-2) 组装与投递**

| RVA | 指令/字符串 |
|---|---|
| `0x5C070E` | `lea edx,[ebp-0x18]` / `call 0x5BF860`（取 20B 摘要） |
| `0x5C071E` | `push 0xDBFD04` = `"getchallenge 0 \"%s\""` |
| `0x5C0729` | `call 0x774900`（snprintf） |
| `0x5C072E-0757` | 读 netchan `+0x14..+0x28` 共 24B 压栈（§3.2 B-2） |
| `0x5C075A` | `call 0x675260` |
| `0x5C0762` | `test al,al` / `jne 0x5C0F1B`（成功即离开本 case） |
| `0x5C076A` | `push 0xDBB708` = `"EXE_CLIENTFAILEDTOCHALLENGE"`（**失败分支**） |

投递链：`0x675260` → `0x6751F0` → `0x6750A0` → `0x67512B call dword ptr [0xCA8128]`

- `0x675260`：`mov eax,edx` / 自身 strlen 循环 / `cmp esi,0x800`（**上限 2048**，
  超出则 `xor al,al` 返回失败）/ `call 0xC427F0`（memcpy）到 `[ebp-0x800]`
- `0x6751F0`：`[ebp+0xc]` ∈ {0,1} → 返回 0；`==2` → `call 0x6750A0`；
  其余 → `call 0x77FB80`（错误分支）
- `0x6750A0`：`[ebp+8]<1` 走 `0x6750A0+0x3E`（`0x7872C08` 环槽，索引 `[0x788680C]&0x3F`，
  槽宽 `0x4F0`）；否则用 `[ebp+0x18]` 索引 `0x7867768` 表（表项 `0x62C8`）→
  `mov [esi+0x4E8],edi` / `mov [esi+0x4EC],ebx` / `call [0xCA8128]`

⇒ **投递边界是"网络消息入队"**（写标志 `+0x4E8/+0x4EC` 后调用统一网络动作）。
**`[0xCA8128]` 的真实身份 UNKNOWN**（导入被剥离，该槽在镜像内无法命名）。
因此"首个战斗数据包真正落到 UDP socket 的那一条指令"**在本镜像内无法命名** —— 见 §4 缺口。

### 3.5 【E】每帧驱动与状态机被调用的证据

| RVA | 指令 | 说明 |
|---|---|---|
| `0x5C2A80` | 函数入口，`mov eax,[0x82C3B58]` / `mov esi,[eax*4+0x1C1D188]` / `xor esi,0xFBB2C97A` | 取当前连接对象（混淆存储） |
| `0x5C2AB7` | `mov ecx, edi` | 为 0x5C05F0 准备 ecx |
| `0x5C2AB9` | `call 0x5C05F0` | **每帧调用战斗状态机** |
| `0x5BE6FF`(函数内 `0x5BEAEA`) | `mov dword [0x76446B0],4` / `call 0x5C05F0` | 另一处调用（状态先置 4） |

---

## 3.6 ★ 追加：闸门 4/5 那对 u64 的来源已闭合

在完成 §3.1-§3.5 后，本次继续追到 A/B 的写入点，**闭合了原有的 A/B 来源与 accepted 比较值来源两个缺口**：

| RVA | 指令 | 说明 |
|---|---|---|
| `0x62F6EF` | 函数入口（**mmbook 请求构造器**） | 先清零 A/B：`0x62F717`/`0x62F71D` |
| `0x62F736` | `mov ecx,[edi+0x168]` | 读**预约项 +0x168** |
| `0x62F73C` | `mov [esi+0x3a048],ecx` | 写 A |
| `0x62F742` | `mov edx,[edi+0x16c]` | 读**预约项 +0x16c** |
| `0x62F748` | `mov [esi+0x3a04c],edx` | 写 B |
| `0x62F7C1-0x62F7C7` | `push 8` / `push [edi+0x10]` / `call 0xB74410` | base64 编码 |
| `0x62F7E0`/`0x62F7E5` | `push 0xDC6724`(`"mmbook"`) / `push 0xDC672C`(`"%s %d %s %d"`) | 组装命令 |
| `0x62F7EA` | `call 0x774980` (snprintf) | → `"mmbook <A> <base64> <B>"` |
| `0x62F7F9`/`0x62F809` | 再取 `[esi+0x3a04c]` / `[esi+0x3a048]` | 压参 |
| `0x62F801`/`0x62F819` | `mov edx,[edx+0x150]` / `call edx` | **发送 mmbook 请求** |

⇒ **客户端在 mmbook 里送出 (A,B)，并在 accepted handler 里要求服务端把 (A,B) 原样回传。**
与既有抓包 `"mmbook 796 AQAAAAAAAAA= 0"` 完全吻合（`796`=A、`0`=B）。
这解释了为什么"固定内容的 `"mmbook accepted"`（0xDC69B0）"无论怎样调
`replyId`/`seq`/`senderId` 都过不了闸门 —— **它不携带那对动态 (A,B)**。

---

## 4. 未闭合项与所需证据（不猜测填补）

| # | 未闭合项 | 现状 | 需要什么证据 |
|---|---|---|---|
| # | 未闭合项 | 现状 | 需要什么证据 |
|---|---|---|---|
| U1 | `[src+0x278]`（accepted handler 第一道闸门）的写入点与取值语义 | 可执行段内 `+0x278` 写点共 **35 处**，其中 `0x62C04E`/`0x62DF08`/`0x62F474` 落在匹配模块内；**本次未筛选确认** | 按匹配状态机筛选这三处，确认"开始匹配后是否置非 0" |
| U2 | 预约项 `+0x168/+0x16c` 由谁填充（↔ 21/5 session 字段） | 成对写入点共 **21 个候选**（`_combat_next001/k4_pairs.py`），未筛选 | 21/5 响应解析链的字段落位 |
| U3 | accepted handler 的上游传参（`0x7F1540 → [0x82E13FC] → vtable+0x13C`） | 用于二次确认 (A,B) 取自消息载荷这两个 dword | 该 vtable 槽的调用约定与参数装配 |
| U4 | `[0xCA8128]` 的真实系统调用身份（发包/入队边界） | 投递路径的**最后一条指令**；**UNKNOWN** | 带**未剥离导入目录**的镜像，或该模块的原始 PE / 映射文件 |
| U5 | listener 节点 `[esi+4]` 的**注册函数** | 链表遍历与触发已定位（`0x632824`/`0x6328A5`）；**注册未找到** | 对匹配对象 `+4` 的赋值点；本镜像该区间的写点未命中目标对象 |
| U6 | `0xC7B8F0`（UDP socket 创建链）与战斗 netchan 的关系 | 找到了 UDP socket 创建链，但两个调用者都在 `0xC5D7xx` 连接表枚举里 | `0xC5D7xx` 调用者链，或 `0xC7BB00/0xC7BAF0/0xC7BB10/0xC7B510` 的真实身份 |
| U7 | 桥接 `0xB95C50` 的具体解析语义 | 由 `codol_crypto.py` 冻结注释 + 本镜像 0x43 读数交叉支持"67B" | `0xB95C50` 完整反汇编 |
| U8 | 客户端 ECDH/DTLS 调用点与 16B 的实际消费者 | `secp224r1`/`DTLS1_*` 字符串的**立即数交叉引用 = 0 命中**（经运行时基址+偏移寻址） | 动态基址映射，或未剥离的导入表 |
| U9 | `0xC3C678`（`strncmp` 形态）的语义边界 | 用于确认 accepted 消息栈上 (A,B) 的精确来源与长度约定 | 该函数完整反汇编 |
| ~~U10~~ | ~~预约 A/B 从哪写入 / accepted 比较的是什么~~ | **已闭合**（§3.6）：来自**预约项 `+0x168/+0x16c`**，由 mmbook 构造器 `0x62F6EF` 读入并格式化成 `"mmbook %d %s %d"` | — |

---

## 5. 最简调用链摘要（一屏）

```
[服务端 21/5] session 记录 258B (含 SessionId)
        |
        v  预约项 +0x168/+0x16c --(0x62F6EF)--> 预约对象 +0x3a048/+0x3a04c (A/B)
        |     同时被 mmbook 请求格式化带走: "mmbook <A> <base64> <B>"   [已闭合 §3.6]
        v  预约槽 +0xe360 = index
[服务端 6/14] mmbook accepted (service 21 push)
        |
        v  0x7F1540 -> [0x82E13FC] -> vtable+0x13C
[0x632680] accepted handler
        |-- 0x63268D [esi+0x278]==0 ?              -> 退出
        |-- 0x63269B [0x76446b0]>=3 ?              -> 退出
        |-- 0x6326AA [esi+0xe360]<0 ?              -> 退出
        |-- 0x6326B9 [ebp+8]  != [esi+0x3a048] ?   -> 0x632916 ret 0x14   ★ 首要阻断
        |-- 0x6326C8 [ebp+0xc]!= [esi+0x3a04c] ?   -> 0x632916 ret 0x14   ★ 首要阻断
        |-- 0x6326DF strncmp "mmbook accepted"
        v
   0x63280B [esi+0x288]=1 ; 0x632827 [0x849b61c]=1
   0x632824 listener loop -> vtable+0x24(1,0)
   0x63285A call 0x6293B0 (bridge, arg = 匹配对象)
        v
[0x6293B0] bridge: 0xB95C50 解析地址块(67B) ; 清 0x150B 局部块 ; 填充
   0x6294AF call 0x470360  (ecx = 局部地址块)
        v
[0x470360] battle-connect: 拷 69B ; 读 +0x43/0x47/0x4B/0x4F/0x53/0x57
   0x4704BE call 0x7BFD70 (地址对象)  失败 -> "EXE_HOSTUNREACH"
   0x470510-0x47052D 写 netchan +0x14/+0x18/+0x1c/+0x20/+0x24
   0x470467 [0x76446B0] = 3
        v
[0x5C2A80] 每帧驱动 (guard [0x76446a1]) -> 0x5C2AB9 call [0x5C05F0]
        v
[0x5C05F0] gate A [esi+0x278] ; gate B [0x76446b0]<3 ; switch(state-3)
   case0 @0x5C070E: "getchallenge 0 \"%s\"" + netchan[+0x14..+0x28](24B)
   0x5C075A call 0x675260
        v
[0x675260]->[0x6751F0]->[0x6750A0]-> 0x67512B call [0xCA8128]   [U4 未闭合]
        v
   首个战斗数据包 (NAT 29B -> init 16B -> ...)
```