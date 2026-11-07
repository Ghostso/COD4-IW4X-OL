# 130 · UIPage 页号定性 + UI 遥测派发器四分支 —— 页名不存在于协议面，以及 129 卷两处归属的更正

> 项目：使命召唤OL 大厅（build 1649370 / 3.19）
> 前卷：`124`（UIPage 样本 505 次 / 28 种页号 2..154）、`127`（信封）、`129`（四入口 + 65 日志点）
> 本卷：**闭合 129 §7 的 ⚠️「UIPage 页号 → 页名」**，并**更正 129 §1/case 归属**、**复核 116 卷服务开关表布局（结论：116 正确）**
> 证据：`tools/callsite_finder.py`、`tools/page_table_hunt.py`、`tools/dispatch_table_scan.py`、`tools/ptrref_scan.py`、`tools/rawdump.py`

---

## §0 结论（八句）

1. **★★ `UIPage` 的页号没有静态名字表。** 全镜像 `{id,name}` 表普查只找到 **12 段**，全部是 IME 名 / 数学函数名 / OpenSSL 库名 / BD 通知枚举 / AI 节点名 / 键码名 —— **没有一段是 UI 页名**。
2. **★★ 页号不是枚举常量，是运行时「属性值」。** 它由一条**虚拟属性 getter 链**从 UI 元素对象上读出来：`[[obj+0x10]+0x28] → [0] → [+0x30]`，调用参数 `(this=[P+0x30], index, out)`。
3. **★★ UI 遥测派发器 `0x1D39E0` 是一个 4 分支 switch**，switch 键 = `[[msgobj+0x10]+0x10]` 的 UI **元素类型码**：**0=UIClick / 1=UIPage / 2=UIKeySetting / 3=通用 5 属性采样器**。
4. **★ 129 卷的 case 归属是错的**（它写「case3 → UIPage，case0/1 → UIClick」）。本卷按**调用目标**复核：`0x641180`(UIClick) 有 **2 个**调用点，**都在 case0 体内**；`0x6411E0`(UIPage) 唯一调用点在 **case1 体内**（`0x5D3B07`）；`0x641340`(UIKeySetting) 唯一调用点在 **case2 体内**（`0x5D3B34`）。
5. **★★ `0xDAE091` = 空字符串哨兵**（`d[0x9AE091]==0`，落在 `0x9AE090..0x9AE093` 的连续四个零字节里；4 处调用点把它当"无字符串"占位传入）。**★ 本卷自我更正一次**：第一版我判它是"指向数据中部的不透明指针"，方向反了。
6. **★★ `0x477910` 不是遥测入口（撤回"第五入口"猜测）**：全镜像 10 个调用点，但**体内 rel32 扫描不调用任何四入口**（`0x640190/0x6404B0/0x640FD0/0x63FC60` 各 7/56/2/7 处，区间内 NONE）⇒ **129 卷"四入口"模型成立**。它是大厅作用域的 5 参动作记录器 `(flag, v1, v2, str, str)`。
7. **★★ `UIInitialGameMode`（`0x641420`）的载荷语义闭合**：全镜像 3 个调用点，`0x2B0230` 内依次压 **`'un_sp_onboard'` / `'un_mp_onboard'` / `'un_zm_onboard'`** ⇒ **载荷 = 新手引导所属模式（单机/多人/僵尸）**。
8. **★ 116 卷「服务开关表 `0xA4E8F8`」布局复核通过**：116 卷原文写的是 `[ptr][flag]` ×20，**这是对的**（本卷原始字节复核：`0xA4E8F8` 起每 8 字节 `[DWORD 指向服务名][DWORD 0/1]`，`0xA4E9F8` 后接另一张表）。**我自己此前把它记成了“反序读法”，那是记忆偏差不是 116 卷的错** —— 本卷更正的是**我的记忆**，不是 116 卷。启用 5 个：`matchmaking` / `messaging` / `profiles` / `storage` / `stats`。

---

## §1 页名到底在哪：先证伪，再定性

### 1.1 全镜像 `{id,name}` 表普查（`tools/page_table_hunt.py`）

判据：连续 ≥8 项、每项 8 字节 = `[u32 id ≤ 210][u32 ptr → .rdata ASCII]`（以及反向顺序）。

命中 **12 段**：

| # | 位置 | 项数 | id 范围 | 内容 | 与 UI 有关？ |
|---|---|---|---|---|---|
| 1 | `0xA1F45C` | 11 | 1..12 | `GFxIME_Ch_Trad_*` | ❌ 输入法 |
| 2 | `0xA3FF70` | 29 | 5..38 | `exp/pow/log/sinh/sqrt…` | ❌ 数学函数 |
| 3 | `0xA4C440` | 35 | 2..69 | `system lib / BN lib / RSA lib…` | ❌ OpenSSL |
| 4 | `0xA4E750` | 48 | 1..58 | `BD_NEW_NOTIFICATION / BD_FRIENDSHIP_PROPOSAL…` | ❌ 通知枚举 |
| 5 | **`0xA4E8F8`** | **20** | **0..1** | **服务名（`all/critical/messaging/matchmaking…`）** | ❌ 服务开关 |
| 6 | `0xA4EC78` | 9 | 2..18 | `NODE_TURRET / NODE_COVER_STAND…` | ❌ AI 节点 |
| 7-11 | `0xA57C5C` 等 5 段 | 12..39 | 9..210 | `ENTER/ESCAPE/F1/MOUSE1/KP_*…`（含 `KEY_*` 同族） | ❌ 键码 |
| 12 | `0xA57F64` | 39 | 0..206 | `KEY_TAB/KEY_ENTER…` | ❌ 键码 |

★★ **⇒ 不存在 UI 页名表。** 页号 `2..154` 不是某个 `{id,name}` 数组的索引。

### 1.2 页号的真实来源（代码证据）

派发器 `0x1D39E0` 的 case 1（UIPage）体内：

```
0x5D3AD1  mov ecx,[eax+0x28]        ; eax = [msgobj+0x10] = 属性桶 P
0x5D3AD4  mov edx,[ecx]             ; edx = Q[0] = 方法表
0x5D3AD6  mov eax,[eax+0x30]        ; eax = P+0x30 = 传给方法的 this
0x5D3AD9  mov edx,[edx+0x30]        ; edx = 方法表[+0x30] = get()
0x5D3ADC  lea esi,[esp+0x20]        ; 出参缓冲
0x5D3AE0  push esi
0x5D3AE1  push ebx                  ; ebx = 0  ⇒ **属性索引 0**
0x5D3AE2  push eax                  ; this
0x5D3AE3  call edx                  ; ★ get(this, 0, out)
0x5D3AE5  test al,al / je 0x5d3c40  ; 取失败 ⇒ 不记
0x5D3AFB  mov esi,[esp+0x30]        ; ★ 页号 = get 写回 out 缓冲的值
```

⇒ **页号 = UI 元素属性索引 0 的取值**。这是**运行时数据**，不是编译期枚举。

同一条链在 case 3 被用于 **索引 0..4 共 5 个属性**，在 case 0 用于 **索引 0,1,2**，并且有一处额外的 `[edx+0x28]`（**属性个数 getter**，返回值在 case 0 里被 `cmp eax,2` 判定）。

### 1.3 三层对象模型（本卷新定）

```
UI 消息对象 obj
  obj+0x10 ──► 属性桶 P
                 P+0x10 = 元素类型码 (0..3)   ← switch 键
                 P+0x28 ──► Q ;  Q[0] = 方法表 V
                 P+0x30 = 传给 V 的 this
                 V+0x28 = count()      → 属性个数
                 V+0x30 = get(idx,out) → 属性值
```

★★ **⇒ 页号、UIClick 坐标、UIKeySetting 的 64 位 ID，全部是通过同一个 `get(idx,out)` 从 UI 元素读出来的运行时值。** 这解释了为什么语料里页号是 28 种散值而**没有一个能对上任何常量表**。

### 1.4 页名在哪 —— 诚实结论

页名只可能存在于**两个地方**：
1. **UI 资产**（`.ifs`，974 个，载荷加密，见 `codol-ifs-container-format`）—— 客户端内部 UI 元素自带的名字；
2. **服务端 playlist 明文**（大厅模式/公告/商城走这条，见 `codol-lobby-ifs-and-aes-chain`）。

**两者都不在当前可读面内。** ⇒ **本卷把 129 §7 的「页号→页名」定性为「协议面不存在该映射」，不是「还没找到」。** 这与 `8/3` 32 KB 字段映射是同一道边界。

---

## §2 派发器 `0x1D39E0` 的四分支全解剖

入口：

```
0x5D39E0  ... mov esi,[ebp+8]        ; esi = UI 消息对象
0x5D3A0C  mov ecx,[eax+0x10]         ; eax = [esi+0x10] = P
0x5D3A0F  cmp ecx,3
0x5D3A18  jmp dword ptr [ecx*4 + 0x5d3c6c]
```

跳转表 @VA `0x5D3C6C`（file `0x1D3C6C`）：`0→0x5D3A1F / 1→0x5D3AD1 / 2→0x5D3B11 / 3→0x5D3B4B`。

| 分支 | 体地址 | 调用 | 事件 | 载荷 | 证据 |
|---|---|---|---|---|---|
| **0** | `0x5D3A1F..0x5D3AD0` | `0x641180` ×2（`0x5D3AB1`、`0x5D3AC4`） | **UIClick** | `'%d|%d|%s'` = `(a, b, *ptr)` | `0x6411A6 push 0xdc707c` |
| **1** | `0x5D3AD1..0x5D3B10` | `0x6411E0` ×1（`0x5D3B07`） | **UIPage** | `'%d'` = 页号 | `0x641242 push 0xdb0ca4` |
| **2** | `0x5D3B11..0x5D3B4A` | `0x641340` ×1（`0x5D3B34`） | **UIKeySetting** | `'%llu'` = 64 位 ID | `0x6413A4 push 0xdb6cbc` |
| **3** | `0x5D3B4B..0x5D3C40` | 无日志器；5 次 `get(0..4)` 后走 **`0x477910`** | **`0x477910(类别, 值a, 值b, 指针, 指针)`**（5 参 cdecl，`add esp,0x14`） | 5 个属性 + 默认值 `0x17`/`6`/`2` | `0x5D3B6A mov edi,0x17`；`0x5D3C38 call 0x477910` |

★ **分支 3 = 独立事件类别**（`0x477910` 第 1 参 `6`），不是 case1 的"第二层记录路径"。见 §3.5。

★ 分支 0 的两处调用是同构但**入口门不同**：`0x5D3AA5 shr ecx,6 / test cl,1` 判定 `out[0xc]&0x40`，走 `0x5D3AB1`（先 `0x5D3AAD mov edx,[edx]` 解引用）；否则走 `0x5D3AC4`。

★★ **UIClick 载荷精确定义**（`0x641180` 的 sprintf 调用约定，`0x64119D..0x6411AB`，**绝对地址**）：

```
0x64119D  mov eax,[ebp+0xc]   ；arg2
0x6411A0  mov ecx,[ebp+8]     ；arg1
0x6411A3  push edx            ；第 3 个变参 = edx（指向元素内部串的指针）
0x6411A4  push eax            ；第 2 个
0x6411A5  push ecx            ；第 1 个
0x6411A6  push 0xdc707c       ；'%d|%d|%s'
```

⇒ **`UIClick` = `<属性1作为%d> | <属性2作为%d> | <一次指针解引用后的字符串>`**。两个 `%d` 来自 case0 里 `get(0)`/`get(1)` 的结果（缺省 0），`%s` 来自 `0x5D3AAD mov edx,[edx]` 得到的指针。
★ 派发器序言 `0x5D3921 cmp eax,2 / sete dl`（`call 0x5ee820` 的结果）给出一个 **bool（0/1）**，在 case0 里作为 `out[0xc]` 的组成——**它决定走 `0x5D3AB1` 还是 `0x5D3AC4`，不是载荷**。

★ 分支 3 的 5 个属性索引是 **0,1,2,3,4 全读**，且 `get(4,...)` 之后有 `cmp edi,0x17; je 跳过` —— **元素 id 仍等于默认值 `0x17` 时不发记录**（`edi` 初值就是 `0x17`，只有 `get(0)` 成功才被覆盖）。

---

## §3 UIPage 日志器 `0x6411E0` 全解剖（含两条此前未记录的门与一个环形窗）

```
0x6411E3  mov eax,[0x849b88c] ; cmp [eax+0xc],0 ; je ret   ← 门1: 服务对象就绪
0x6411F5  cmp byte [0x82ca046],0 ; jne ret                 ← 门2: 某全局开关必须为 0
0x641202  cmp [0x7570924],esi ; je ret                     ← ★ 门3: 去重(与上一页号相同就不记)
```

★★ **门3 `[0x7570924]` = "上一次记录的页号"** —— 同页连续停留只记一次。这解释了 124 卷里 505 条 UIPage 的分布形态。

```
0x64120E  mov ecx,0xc945db8 ; call 0xb75da0 ; fstp dword [ebp-4]  ← ★ 计时对象, 取 1
0x64121B  mov ecx,0xc945db8 ; call 0xb75d80                        ← ★ 同对象, 取 2
```

★ `0xc945db8` 上有两个 getter（`0xb75da0` / `0xb75d80`），一个的返回值被保存为 `float`。这是**页停留时长**的来源（`fistp` 转成整秒）。

```
0x641225  mov ecx,[0x849b994] ; cmp [ecx+0xc],0 ; je 0x641277   ← 门4: UI 统计服务就绪
0x641231  mov edx,[0x765ea7c] ; mov eax,[0x849b99c]
0x64123C  cmp edx,[eax+0xc] ; jge 0x641277                      ← ★ 门5: 计数 < 上限
0x641241  sprintf('%d', esi) → log_event('UIPage', n)
0x641271  inc dword [0x765ea7c]                                  ★ 计数自增
```

★★ **⇒ UIPage 走 `0x640FD0`(log_event) 的那条分支是**限流**的：`[0x765ea7c]` 是已记录页数，上限取自 `[0x849b99c]+0xc`。**

```
0x641277  cmp esi,2 ; je 0x6412ac        ← ★ 页号==2 跳过时长记录
0x64127C  ...
0x641291  fistp qword [ebp-0x10]         ; 停留秒数
0x641297  push eax                        ; 秒
0x641298  push 0xdae091                   ; 见 §4, 非字符串
0x6412A0  push eax / push esi / push 0x10
0x6412A4  call 0x477910                   ; ★ 第二层记录路径
```

接着是**环形窗**：

```
0x6412AC  mov edx,[0x849b998] ; cmp [edx+0xc],0 ; je 0x6412e9
0x6412B8  mov eax,[0x32b5854]              ; 窗内元素个数
0x6412BD  cmp eax,5 ; jb 0x6412dc          ; <5 不搬
0x6412C2  push 0x10 / push 0x7645700 / push 0x76456fc / call 0xc3e400   ; memmove 16B
0x6412D8  ...
0x6412DC  mov [eax*4 + 0x76456fc], esi     ; ★ 追加页号
0x6412E3  inc eax ; mov [0x32b5854],eax
0x6412E9  mov [0x7570924], esi             ; 更新去重哨兵
```

★★ **`0x76456FC` 是 5 槽页号历史环**（20 字节），`0x32B5854` 是当前个数（上限 5），`0x7645700` 是搬移源（= `0x76456FC+4`）。

★ **全镜像只有 `0x2411E0..0x2412F2` 引用这四个地址**（`tools/ptrref_scan.py`：`0x7645700` 1 处、`0x76456FC` 2 处、`0x32B5854` 3 处、`0x7570924` 2 处，全在 UIPage 日志器内）⇒ **自包含记录器，无外部消费者**。

---

## §3.5 `0x477910` 真身份：大厅作用域「动作记录器」，**不是**遥测入口

`0x6412A4` / `0x5D3C38` 都调 `0x477910`。我一度以为它是「第二套遥测入口」。**本卷把它证伪并撤回该猜测。**

### 3.5.1 全镜像 10 个调用点

```
0x1D3C38  fn 0x1D39E0   ← UI 派发器 case3（第 1 参 = edi，缺省 0x17）
0x1E3507  fn 0x1E3400   ← 邻近串 'onboardCharacterID'
0x21260A  fn 0x2122D0
0x23AA04  fn 0x23A820   ← MatchMakingJoin 日志函数
0x2412A4  fn 0x2411E0   ← UIPage 日志器（第 1 参 = 0x10）
0x2BBEC6  fn 0x2BBD70
0x37E3CB  fn ≈0x37E2xx  ← ClientDisconnect 日志函数（第 1 参 = 0x13）
0x37ECE2  fn 0x37EB20   ← ClientLogin 日志函数
0x3DCC41  fn 0x3DCB60
0x3DD56F  fn 0x3DD330
```

### 3.5.2 第 1 个参数是**分流键（flag/序号）**，取值稀疏、语义未定

| 调用点 | 第 1 参 | 出处 |
|---|---|---|
| `0x2412A4` UIPage | **`0x10`** | `0x2412A2 push 0x10` |
| `0x37E3CB` ClientDisconnect | **`0x13`** | `0x77E3C9 push 0x13` |
| `0x1D3C38` UI case3 | **`edi`**，缺省 **`0x17`**（`0x5D3B6A mov edi,0x17`，`get(0)` 成功则被覆盖） | — |
| `0x37ECE2` ClientLogin | **`1`** | `0x77ECE0 push 1` |
| `0x23AA04` MatchMakingJoin | **`0x12`** | `0x63AA02 push 0x12` |
| `0x21260A` fn 0x2122D0 | **`0x0E`** | `0x612608 push 0xe` |
| `0x2BBEC6` fn 0x2BBD70 | **`4`** | `0x6BBEC4 push 4` |
| `0x1E3507` fn 0x1E3400 | **`4`** | `0x5E3505 push 4` |
| `0x3DCC41` / `0x3DD56F` | 未逐点取（诚实缺口） | — |

★ 已观测值 = `{1, 4, 0x0E, 0x10, 0x12, 0x13, 0x17}` —— **稀疏、与业务无单调关系** ⇒ **只能记为"分流键"，不叫"类别枚举"。** 第一版我叫它"类别号"，也是过度命名。

### 3.5.3 关键否证：它体内不调用任何遥测入队

按 **rel32 正解**扫四入口调用点（`next_insn + rel32 == target`）：

```
0x640190 : 7 处     0x6404B0 : 56 处     0x640FD0 : 2 处     0x63FC60 : 7 处
落在 [0x477910, 0x4784C4) 区间内的： 全部 NONE
```

★★ **⇒ `0x477910` 不是遥测入口。** 同时这段扫描**独立复现了 129 卷的四入口调用点数 7/56/2/7** ⇒ **129 的"四入口"模型成立，不变。**

### 3.5.4 它是什么（定性边界）

- 前置门：`[0xe59d20]∈{4,6}`（大厅连接状态）、`0x803830` 单例非空、`0xb7a670()==2`、`0xb7a6e0()` 非 0、`[0x84abacc]==1`、`0x82ca046` 与 类别 的联合判定；
- 体内有 `0x803830` / `0x7f9090`+`0x11150` / `'rank'`（`0xdb4b60`）等**玩家档案/排行**痕迹；
- 5 参 = `(类别, 值1, 值2, 指针, 指针)`。

★★ **定性：一处「大厅内、玩家已登录、按 flag 分流」的 5 参动作记录路径**，服务 UI 事件与登录/断线/匹配三类业务。**具体落地写到哪里（本地上报 or 上报包）未证 ⇒ 诚实缺口。** 我**不**再把它叫"遥测第二入口"。

★★ **更正 §3.5.2**：第 1 参**不是**"类别枚举"，而是 **flag / 开关序号** —— 已观测值 `{0x10, 0x13, 0x17, 0x12, 0x0E, 0x04, 0x01}`，其中 `ClientLogin` 传 **`1`**、`0x2122D0` 传 **`0x0E`**、`0x2BBD70` 与 `0x1E3400` 传 **`4`**、`0x23A820` 传 **`0x12`**。值域不像枚举编号（是稀疏小整数且与业务无单调关系）⇒ **只能记为"分流键"，语义未定。**

---

## §4 `0xDAE091` 定性：**空字符串哨兵**（我上一版的"假阳性"判断是反的）

### 4.0 先自我更正

我最初写这一节时的判断是：`0x9AE091` 处的 `cstr` 读出来是 `b''` ⇒ 「它不是字符串，是指向数据中部的不透明指针，列入假阳性」。

**这个判断是错的，而且错在方向相反**：`cstr` 读出 `b''` 恰恰是因为 **`d[0x9AE091] == 0x00`** ⇒ **它就是一个合法的空 C 字符串**。

### 4.1 功能证据：它是被显式传进来当"无字符串"用的

四处调用点（`0x477910` 的第 4 参）：

```
0x77ECD7  push 0xdae091     ← ClientLogin
0x5E34FD  push 0xdae091     ← fn 0x1E3400（邻近 'onboardCharacterID'）
0x6BBEBC  push 0xdae091     ← fn 0x2BBD70
0x612601  push 0xdae091     ← fn 0x2122D0
```

这四处的共同形态是 `push <空串>; push 0; push 0; push <id>; call 0x477910` —— **调用方在没有字符串可报时，统一传这个地址**。

★★ **⇒ `0xDAE091` = 客户端里约定的「空字符串」常量。** 功能上等价于 `""`。

### 4.2 它的邻居为什么是动画名（这条仍成立，但只是旁证）

原始字节（file `0x9AE090`）：

```
9AE080  6f 67 00 00   7a 6f 6d 62 69 65 5f 61 72 65 6e 61   |og..zombie_arena|
9AE090  00 00 00 00   32 33 33 32   00 00 00 00   32 33 33 34 |....2332....2334|
9AE0A0  00 00 00 00   32 33 33 35   00 00 00 00   32 33 33 36 |....2335....2336|
...
9AE0F0  00 00 00 00   32 33 34 35   00 00 00 00   32 37 38 33 |....2345....2783|
9AE100  00 00 00 00   35 34         6d 70 5f 6d 61 6e 74 6c   |....54..mp_mantl|
9AE110  65 5f 6f 76 65 72 5f 6c 6f 77 5f 66 72               |e_over_low_fr|
```

★★ **结构 = `[u32 0][char id[4]]` 8 字节记录**，id 依次 `2332 2334 2335 2336 2337 2338 2339 2340 2341 2342 2343 2344 2345 2783 54`；**前邻 `dog` / `zombie_dog` / `zombie_arena` / `generic_human`，后邻 `mp_mantle_over_low_fr` / `mp_mantle_up_21_fr` / …**。

⇒ 这一片是 **动画/notetrack 名字池**（角色模型名 + 翻越动作名 + 数字型 notetrack 名）。

★ 但**这只解释了邻居，不解释 `0xDAE091` 本身**：`0x9AE090..0x9AE093` 是**连续四个零字节**，`0x9AE091` 落在这个零串内 ⇒ **从它开始读任何 C 字符串都得 `""`**。所以它被选为「空字符串常量」是**必然成立的**，不是巧合。

★★ **正确结论：`0xDAE091` = 空字符串哨兵。** 而不是「指向数据中部、永不被读的指针」。

### 4.3 这条教训的**正确**写法

我上一版写的教训是「看见像字符串的东西别当字符串」。**那条教训这次是错的**——它让我把一个**正确的**字符串判读推翻了。

真正的教训是另一条：

> **`cstr` 读出 `b''` 有两种可能：①地址处是 NUL（合法的空串）；②地址错位/越界。要区分它们，看调用方怎么用它。**
> 本卷的区分证据：4 处调用点把它当第 4 参传入，且同伴参数全为 0 ⇒ **它是"无字符串"占位 ⇒ ①**。

★ 对照 124 卷 `wfUD3"`：那次是 **ASCII 正则误捕二进制**（字节序列本身被当文本），与本次类型不同 —— **不能合并成一条规则**。我在第一版里把两件事合并了，那是过度概括。

---

## §5 `UIInitialGameMode`（`0x641420`）载荷语义闭合

`tools/callsite_finder.py 0x641420` ⇒ **全镜像 3 个调用点，全在 `0x2B0230`**：

| 调用点 | 该函数内见过的 push 串 |
|---|---|
| `0x2B0249` | `'un_sp_onboard'` |
| `0x2B0269` | `'un_sp_onboard'`、`'un_mp_onboard'` |
| `0x2B0289` | `'un_sp_onboard'`、`'un_mp_onboard'`、`'un_zm_onboard'` |

★★ **⇒ `UIInitialGameMode` 的载荷是"新手引导所属模式"：sp / mp / zm。** 三个调用点在同一函数里依次出现（累计 push 集合递增），说明是**分支选择后调用**，不是三次必调。

★ 与 `UIKeySetting` 对比：后者 `0x641340` 从 `[0xb9a0f0]` 对象（或入参）取 **`+0x20`/`+0x24` 的 64 位值**（`'%llu'`）——**账号/游戏 ID 对**。两个 UI 事件载荷类型完全不同（一个是模式枚举串，一个是 64 位 ID）。

---

## §6 116 卷服务开关表布局复核（结论：116 卷正确）

116 卷原文记：`0xA4E8F8`，`[ptr→服务名][flag 0/1]` 20 项。**这是对的。**
本卷原始字节复核（顺带纠正我此前在别处把它记成“`[name_ptr][enabled]` 反序”的口误 —— 那是我的记忆偏差，116 卷并没有写错）：

```
A4E8F0  ed 03 00 00  10 0c de 00            ← 前一张表
A4E8F8  e0 dd da 00  00 00 00 00  'none'
A4E900  0c de da 00  00 00 00 00  'all'
A4E908  04 0c de 00  00 00 00 00  'critical'
...
A4E940  d0 0b de 00  01 00 00 00  'matchmaking'  ← 1
A4E948  c4 0b de 00  01 00 00 00  'messaging'    ← 1
A4E950  b4 0b de 00  00 00 00 00  'pooledstorage'
A4E958  a8 0b de 00  01 00 00 00  'profiles'     ← 1
A4E960  a0 0b de 00  01 00 00 00  'storage'      ← 1
...
A4E990  38 fe db 00  01 00 00 00  'stats'        ← 1
A4E998  08 9b db 00  70 0b de 00  ← 下一张表开始
```

★★ **⇒ 真布局 = `[ptr→名][flag]`（指针在前、标志在后）。** 这正是 116 卷写的顺序。★ 本卷顺带收回自己的一个口误：我曾把这家表描述成“`[name_ptr][enabled]` 反序”，**116 卷原文其实是对的。**

```
none(0) all(0) critical(0) non_critical(0) eventlog(0) friends(0) group(0) mail(0)
marketplace(0) matchmaking(1) messaging(1) pooledstorage(0) profiles(1) storage(1)
tags(0) teams(0) tencent(0) titleutilities(0) reward(0) stats(1)
```

★★ **启用 5 个：`matchmaking` / `messaging` / `profiles` / `storage` / `stats`。`messaging=1` 与 116 卷 `configs_s.info [dw_service_info]` 的 `messaging=1` 逐项吻合 —— 三链交汇的这一环独立复核通过。**

★ 116 卷「20 项、`messaging=1`、顺序与 `configs_s.info [dw_service_info]` 一致」**全部复核通过**，无出入。唯一要记的是第 1 项 `none` 是占位（index 0），真正的服务从 index 1 起。

---

## §7 状态表

| 项 | 状态 | 证据 |
|---|---|---|
| UIPage 页号 → 页名映射 | ✅ **协议面不存在**（定性，非未找到） | `page_table_hunt.py` 12 段无 UI；§1.4 |
| 页号来源 | ✅ **运行时属性 getter `get(0)`** | `0x5D3ADC..0x5D3AFB` |
| UI 元素对象三层模型 | ✅ 本卷新定 | §1.3 |
| 派发器四分支归属 | ✅ **0=UIClick 1=UIPage 2=UIKeySetting 3=通用采样** | 三日志器调用点定位 |
| 129 卷 case 归属 | ❌→✅ **已更正**（case1 是 UIPage 不是 case3） | §2 |
| UIPage 三道前置门 | ✅ 门1 `[0x849b88c]+0xc`、门2 `[0x82ca046]`、门3 `[0x7570924]` | `0x6411EB/1F5/202` |
| UIPage 限流 | ✅ `[0x765ea7c]` vs `[0x849b99c]+0xc`，记完 `inc` | `0x641231..0x641271` |
| UIPage 5 槽历史环 | ✅ `0x76456FC` / 计数 `0x32B5854` / 无外部消费者 | `0x6412AC..0x6412E9` + `ptrref_scan` |
| 页号 2 的特判 | ✅ `cmp esi,2; je` 跳过时长记录 | `0x641277` |
| `0xDAE091` | ✅ **空字符串哨兵**（落在 4 连零里；4 处调用点当"无字符串"传） | §4 |
| `0x477910` 是否是第五遥测入口 | ❌→✅ **不是**（体内 0 处调四入口） | §3.5.3 |
| 129 四入口模型 | ✅ **成立**（rel32 复现 7/56/2/7） | §3.5.3 |
| `0x477910` 第 1 参语义 | ⚠️ **分流键，值 `{1,4,0x0E,0x10,0x12,0x13,0x17}`，语义未定** | §3.5.2 |
| `0x477910` 落地目标 | ⚠️ **未证**（本地记录 vs 上报包） | §3.5.4 |
| `UIInitialGameMode` 载荷 | ✅ **sp/mp/zm 新手引导** | `0x2B0230` 三处 push |
| `UIKeySetting` 载荷 | ✅ **64 位 ID（`[0xb9a0f0]+0x20/+0x24`）** | `0x64138D..0x6413A4` |
| 服务开关表布局 | ✅ **116 卷 `[ptr][flag]` ×20 是对的**（此前是我记反了，非 116 卷之错）；启用 5 个 | §6 |
| 枚举表 `0xA4E9A0` 是否被引用 | ⚠️ **绝对立即数 0 引用 —— 但此判据在本镜像不可靠**（§8） | `dispatch_table_scan.py` |

---

## §8 方法论警告：绝对立即数扫描在本镜像不可靠

本卷想用「表基址是否被代码以立即数引用」来判「枚举表是活数据还是死数据」。结果发现：**连我们已知是活的服务开关表 `0xA4E8F8`，全镜像也没有一处绝对立即数引用它**（`ptrref_scan.py`：0 次）。

★★ **⇒ 「绝对立即数 0 引用 ⇒ 数据是死的」这个推论在本镜像无效。** 原因：这些表通过**其它结构里的指针**或**运行时计算的基址**访问，而不是 `mov eax, imm32`。

★ 该判据在本卷其它地方是有效的（UIPage 5 槽窗口确实只有 4 处绝对引用，全在日志器内）—— **有效性依赖目标是否被直接寻址**。**不能一刀切。**

---

## §9 复现命令

```powershell
python -I tools\page_table_hunt.py                                   # 12 段 {id,name} 表，无 UI
python -I tools\callsite_finder.py 0x641420 0x641340 0x6411E0 0x641180 # 四日志器调用点
python -I tools\dis_640fd0.py 0x1D3AD1 0x170                         # case1/2/3 全解剖
python -I tools\dis_640fd0.py 0x1D3A1F 0xC0                          # case0
python -I tools\dis_640fd0.py 0x241180 0x120                         # UIClick 模板 '%d|%d|%s'
python -I tools\dis_640fd0.py 0x241290 0x90                          # UIPage 尾段 + 5 槽环
python -I tools\dis_640fd0.py 0x241340 0x70                          # UIKeySetting '%llu'
python -I tools\ptrref_scan.py 0x7645700 0x76456FC 0x32B5854 0x7570924 # 5 槽环无外部消费者
python -I tools\rawdump.py 0x9ae091                                   # 0xDAE091 非字符串
python -I tools\dispatch_table_scan.py 0xA4E9A0 40                    # 枚举表引用扫描
```
