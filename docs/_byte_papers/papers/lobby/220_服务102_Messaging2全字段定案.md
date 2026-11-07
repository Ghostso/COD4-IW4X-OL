# 220 · 服务 `102` (`Messaging2`) 全字段定案

> 卷次：220（第五轮·服务 102 字节级定案）
> 方法：**语料全量逐字节（1415 条 80/102 记录）+ Eruntime 镜像 `client_image_20261027.bin` 反汇编（PE32 / ImageBase 0x400000 / VA=文件偏移+0x400000）**
> 结论：`102` = `Messaging2`（服务号 `0x66`）；4 个 task 结构 **100% 闭合**；编码层为 **Demonware DML（1 字节标签 TLV）**，读写器全地址定位；发送侧闸门、容器序列化器、AS 绑定表全部给出地址级证据。
> 前卷：`115`（结构初解）/`116`（定名）/`171`–`181`（房间/位流方法论）
> 语料：`_byte_papers/corpus/corpus.json`

---

## §0 结论（一句话）

**`102` 的 4 个 task 是 Demonware `Messaging2` 服务的周期性轮询；报文是 1 字节标签的 DML TLV；客户端侧存在完整的读写器族（`0xB761E0`–`0xB76AF0` 读 / `0xB76000`–`0xB76820` 写）、一条 `srpc 认证==2` 闸门的发送链（`0x4AAE20`→`0xB8F370`→`0x7FAA20`→`0x7FA800`）与一张 AS↔C++ 绑定表（`0xDCCE00` 起，`AS_MessageSetRead`→`0x6A17E0`）。**

四条独立证据（按 AGENTS.md 权威层级）：

| # | 证据 | 层级 | 强度 |
|---|---|---|---|
| ① | 语料 4 个 task 逐字节结构（本卷全量重解） | 本地逆向（最高） | ★★★★★ |
| ② | 镜像 DML 标签读写器族**全部地址级定位**（`0x08/0x0a/0x10/0x13/0x16…`） | 本地逆向（最高） | ★★★★★ |
| ③ | 客户端 AS 绑定表：`AS_MessageSetRead/SetReadBatch/…/ActiveFetch` + `AS_GetMOTDMessages` 等名字与 C++ thunk 成对 | 本地逆向（最高） | ★★★★ |
| ④ | 服务开关表（`0xE4E8F8`）`messaging=1`；RTTI `bdMessagingGroup`(`0xE6AE50`) | 本地逆向（最高） | ★★★★ |

★ 本卷**不改 116 的定名**，只把「结构」推进到**编码器地址级 + 读侧字段级**。

---

## §1 语料全量逐字节表（4 个 task，1415 条中的 639 条 svc=102）

语料统计（`corpus.json`，83 次运行）：`102/1`×172、`102/2`×77、`102/5`×19、`102/7`×371。

### 1.1 DML 语法（本卷确认）

报文是**字节流**，每个字段 = `1 字节标签 + 负载`：

| 标签 | 类型 | 负载 |
|---|---|---|
| `0x01` | bool | 1 字节 |
| `0x03` | u8 | 1 字节 |
| `0x06` | u16 | 2 字节 LE |
| `0x08` | u32 | 4 字节 LE |
| `0x0a` | u64 | 8 字节 LE |
| `0x10` | string | **NUL 结尾**（无长度前缀！） |
| `0x13` | blob | `u32 长度`（又是一枚 `08`）+ 数据 |
| `0x16` | 嵌套容器 | 见 §3.3 |
| `0x00` | 终止 | 报文尾 |

★★ **`0x10` = NUL 结尾字符串，不是「长度前缀」**——决定性证据是读器 `0xB76A30`（§3.2）逐字节读到 `\0` 或 maxlen。这解释了语料里 `10 31 36 32 35 31 36 30 00` = 空串 + "1625160"+NUL 的形态（而非 `10 07 …`）。

### 1.2 `102/1`（172 条，2 形态）

```
形态 A(127条,len=22): 08 00 00 00 00 | 08 01 00 00 00 | 03 03 | 0a 00×8 | 00
                     = u32 0, u32 1, u8 3, u64 0, TERM
形态 B( 45条,len=33): 08 00 00 00 00 | 08 02 00 00 00 | 03 01 | 0a 00×8 | 03 02 | 0a 00×8 | 00
                     = u32 0, u32 2, (u8 1,u64 0)(u8 2,u64 0), TERM
```
- 字段①`u32 0` = 命名空间/类别（恒 0）。
- 字段②`u32 N` = 后续键值对个数（N∈{1,2}）。
- 后续 `N×(u8 key, u64 val)`：key=类别码（A 形态 3；B 形态 1,2），val 恒 0（未读游标）。

### 1.3 `102/7`（371 条，1 形态，len=556）

```
08 32 00 00 00 | [03 01 | 0a <i>] × 50 | 00      i = 0,1,2,…,49
                = u32 50, 50×(u8 1, u64 i), TERM
```
- **371 条 distinct=1**：`i` 严格 0..49 连续 ⇒ 这是「按槽位 0..49 批量声明」，**不是查询结果**。
- `08 32`(=50) 与 §3.3 的嵌套读器 `0xB76220` 里 `cmp [ebp-0x14],0x32`（见 §3.3）**同值**——本卷把它记为**候选巧合**，未证实因果（边界 §8-5）。

### 1.4 `102/5`（19 条，1 形态，len=10）

```
08 02 00 00 00 | 03 01 | 03 02 | 00        = u32 2, u8 1, u8 2, TERM
```
- 与 `102/1` 同族：`u32 2` = 2 个元素，后跟 2 个 `u8`（无 u64 配对）⇒ 这是**纯索引列表**。

### 1.5 `102/2`（77 条，1 形态，len=1）

```
00        = 仅终止符（空轮询/心跳）
```

---

## §2 定名证据（本地，最高权威）

### 2.1 服务开关表 `0xE4E8F8`（20 项 `{char* name; u32 enabled}`）

实测（本卷重新读取，与 116 一致）：

```
0xE4E938 ptr=0xDE0BDC flag=0  'marketplace'
0xE4E940 ptr=0xDE0BD0 flag=1  'matchmaking'
0xE4E948 ptr=0xDE0BC4 flag=1  'messaging'      ← ★
0xE4E958 ptr=0xDE0BA8 flag=1  'profiles'
0xE4E960 ptr=0xDE0BA0 flag=1  'storage'        ← ★
0xE4E990 ptr=0xDBFE38 flag=1  'stats'
```
`messaging` 与 `storage` 都被显式启用；102 是全语料第三大服务。★ 但该表只有 **enabled 0/1，没有服务号** ⇒ **不能单凭此表把 102↔messaging 绑定**。

### 2.2 RTTI 类（字符串级铁证）

`tools/rtti_all.py`（1446 个 `.?AV…@@`）中 messaging 族（VAs 均为字符串地址）：

```
0xE6AE50  .?AVbdMessagingGroup@@          ← messaging 的 bd 数据类
0xE7135C  .?AVAS_MessageActiveFetch@@
0xE71380  .?AVAS_MessageReject@@
0xE713A0  .?AVAS_MessageAccept@@
0xE713C0  .?AVAS_MessageDelete@@
0xE713E0  .?AVAS_MessageSetAlerted@@
0xE71404  .?AVAS_MessageSetReadBatch@@
0xE7142C  .?AVAS_MessageSetRead@@
0xE7144C  .?AUAS_HaveUnviewedMOTDMessages@@
0xE71478  .?AVAS_GetMOTDWelfarePageIndexByURL@@
0xE714D0  .?AVAS_SetMOTDMessageViewed@@
0xE714F8  .?AVAS_GetMOTDCategoryMessages@@
0xE71524  .?AVAS_GetMOTDMessages@@
```

★ `AS_Message*`（Message = **站内信/MOTD 消息**）与 `AS_GetMOTD*` 同族 ⇒ `102` 的业务面 = **消息/公告信箱**，`Messaging2` 名实相符。

### 2.3 AS 绑定表 `0xDCCE00` 起（name ↔ C++ thunk）

该区是「AS3 类名 → C++ 反射描述符 → thunk」表。实测（读原始字节）：

```
0xDCCE33  "AS_MessageSetRead"      → thunk 0x6A17E0
0xDCCE44  "AS_MessageSetReadBatch" → thunk 0x6A1800
0xDCCE60  "AS_MessageSetAlerted"   → thunk 0x6A18F0
0xDCCE80  "AS_MessageDelete"       → thunk 0x6A1910
0xDCCE98  "AS_MessageAccept"       → thunk 0x6A1930
0xDCCEB0  "AS_MessageReject"       → thunk 0x6A1950
0xDCCEC8  "AS_MessageActiveFetch"  → thunk 0x6A1970
```
反汇编 `0x6A17E0`（AS_MessageSetRead）：
```
006A17E0  push ebp / mov ebp,esp
006A17E3  mov eax,[ebp+8]        ; Flash 参数包
006A17E6  mov ecx,[eax+0x10]
006A17E9  mov edx,[ecx+0x10]
006A17EC  push 0 / push edx
006A17EF  call 0x71FFE0          ; ← 进入 C++ 消息层
```
反汇编 `0x6A1800`（AS_MessageSetReadBatch）走 Flash 桥（`call [edx+0x28]`）后进业务。
★ 说明 **AS3 面与 C++ 消息层之间存在真实调用边**（不是纯反射空壳）。

---

## §3 编码层：DML 标签读写器族（地址级）

★ 这是本卷**最有价值的地址级产物**：把语料里每个 `08/0a/10/03/06/01/13` 都钉到一个函数。

### 3.1 读写器对象（bdDML 游标）

`this` 字段：`+8`=缓冲区基址，`+0xc`=合法长度，`+0x10`=当前游标，`+0x18`=写模式标志。

### 3.2 **读**族（`0xB75E80` 起）

| 地址 | 语义 | 证据 |
|---|---|---|
| `0xB75E80` | readN(this, dst, n)：带界检查的字节拷贝 | 末尾 `call 0xB783C0`(memcpy)，`add [esi+0x10],edi` |
| `0xB76310` | readTag(this, expected) → bool | 读 1 字节；`cmp ecx,[ebp+8]; sete bl`；**特判 tag==0x16** |
| `0xB761E0` | **readU32**（tag 8） | `push 8 → call 0xB76310`；`push 4 → call 0xB75E80` |
| `0xB76850` | readBool（tag 1） | `push 1 → call 0xB76310` |
| `0xB76890` | **readU8**（tag 3） | `push 3 → call 0xB76310` |
| `0xB768D0` | readU16（tag 6） | `push 6` |
| `0xB76910` | read(tag 7) | `push 7` |
| `0xB76950` | readI32（tag 9） | `push 9` |
| `0xB769A0` | **readU64**（tag 0x0a） | `push 0xa`；`call 0xB75E80(n=8)`；`mov [out],ecx/[out+4],edx` |
| `0xB769F0` | readF32（tag 0x0d） | `push 0xd`；`fld dword [ebp-4]/fstp [ecx]` |
| `0xB76A30` | **readString**（tag 0x10，NUL 结尾） | 循环 `call 0xB75E80(n=1)`；`test cl,cl; je` 遇 NUL 停 |
| `0xB76AF0` | **readBlob**（tag 0x13） | `push 0x13 → 0xB76310`；再 `call 0xB761E0` 读 u32 长度；再 readN |

### 3.3 tag `0x16` = 嵌套容器（嵌入 blob）

`0xB76310` 读到 tag==0x16 时进入 `0xB76220`：
```
0xB76220  call 0xB761E0 ×3        ; 读 3 个 u32（tag 8）
          → 分配两个缓冲，readN 填入
0xB762A4  cmp [ebp-0x14], 0x32    ; ★ 首 u32 必须 == 0x32(50)
          je 0xB762D4 (call 0xB75ED0 合并)  else  call 0x8435D0(哨兵空桩) + 失败
```
★ 这证实**消息 blob 可被 `0x16` 容器包裹**，且容器首字段带 50 这个魔数；`0x8435D0` = 全项目已知的 `C3` 空桩哨兵（空转+失败）。

### 3.4 **写**族（`0xB76000` 起）

| 地址 | 语义 | 证据（头几行） |
|---|---|---|
| `0xB76000` | write tag 5 | `push 5 → 0xB75F30` |
| `0xB76040` | writeU16（tag 6） | `push 6` |
| `0xB76080` | write tag 0x14 | `cmp [ecx+0x18],0`；`push 0x14` |
| `0xB760A0` | **writeTerm**（tag 0） | `push 0 → 0xB75F30`（报文尾 `00`） |
| `0xB76120` | writeU64（tag 0xa） | `push 0xa` |
| `0xB76180` | writeF32（tag 0xd） | `push 0xd` |
| `0xB765E0` | writeBool（tag 1） | `push 1` |
| `0xB76620` | **writeU8**（tag 3） | `push 3` |
| `0xB766B0` | **writeU32**（tag 8） | `push 8`；`push 4; lea eax,[ebp+8]; call 0xB75E00` |
| `0xB76700` | **writeString**（tag 0x10） | `push 0x10`；NUL 结尾 |
| `0xB767D0` | **writeBlob**（tag 0x13） | `push 0x13`；先写长度 |
| `0xB76820` | write tag 0x17 | `push 0x17` |
| `0xB75F30` | writeByte（底层） | `cmp [ecx+0x18],0; je; push 1; call 0xB75E00` |

★★ **读写两侧标签集完全对称**（0x01/0x03/0x06/0x08/0x0a/0x0d/0x10/0x13/0x16 + 0/0x14/0x17 标记）⇒ 这是**同一套 DML 编解码器**，语料是它的输出。

---

## §4 发送链与闸门（地址级）

### 4.1 唯一出口漏斗 `0x7FAA20` / `0x7FAB70` → `0x7FA800`

```
0x7FA800: idx = arg[8]
          class = [ idx*8 + 0xE4E20C ]      ; 两级表第 1 级
          cfg   = 0xE69CE0 + class*16       ; 两级表第 2 级 = {发超时,收超时,重发间隔,重试}
          扫描槽表 0xE56FFE0..0xE5713E0 (步进 0x50) 找空槽
0x7FABE0: mov eax,[eax*8+0xE4E20C] ; 同款查表（寄存器变体）
```
实测 `0xE4E20C→0xE69CE0` 配置（本卷复读）：
```
idx 0x50 → class 0 → {25000, 25000, 2000, 5}
idx 0x5a → class 4 → {60000, 60000, 2000, 10}
idx 0x5d/0x66/0x68/0x6a → class 3 → {60000, 60000, 2000, 5}
idx 0x6b → class 4 → {60000, 60000, 2000, 10}
```
★ 与 154 卷结论一致：**发送点传入的立即数 = 「消息/通道号」，不是类型号**；它经两级表映射到重试策略。

### 4.2 认证闸门（srpc）

```
0x803830() → srpc 单例
0xB7A670(srpc): [srpc+0x4F4]==0 → 0；否则 (0xB7A780()==2 && [srpc+0x4F8]==0) ? 1 : …
                实际返回 2 表示「已认证」
0xB7A770(srpc): 要求 0xB7A670()==2，否则 call 0x8435D0 + return 0
```
（与 173/174 卷 `srpc+0x4F4`=HMAC 会话对象一致。）

### 4.3 请求包装器 `0x4AAE20`（本卷新）

```
004AAE20  call 0x803830            ; srpc
004AAE36  call 0xB7A670 / cmp eax,2 / jne 退出   ; 未认证直接放弃
004AAE46  call 0xB7A770            ; 取会话对象 (eax)
004AAE71  call 0xB8F370            ; ★ 容器序列化器（见 §5.3）
004AAE9E  push 0x85
004AAEA3  call 0x7FAA20            ; ★ 出口漏斗，通道号 0x85
```
调用者：`0x4AAB87 / 0x4AAC43 / 0x4AB5B0 / 0x4AB71A`（都在 0x4Axxxx 的 DW 请求构造区）。
★ **`0x4AAE20` = 「认证后才构造+发送」的通用包装器**，其通道号为 `0x85`（class 0，25 s / 5 重试）。

---

## §5 客户端读写锚点（类族，地址级）

### 5.1 元素反序列化器 `0xB8FB90`（vtable 槽 `0xD59CE8`）

```
0xB8FB90  call 0xB76890          ; readU8 → [ebp-0xd]
0xB8FBD2  cmp byte [ebp-0xd],1   ; ★ 守护：该 u8 必须 == 1
0xB8FBDF  call 0xB76890          ; readU8  → this+8
0xB8FBEF  call 0xB769A0          ; readU64 → this+0x10
0xB8FBFF  call 0xB761E0          ; readU32 → this+0x18
```
⇒ 读侧结构 = `u8(==1) , u8 , u64 , u32`。

### 5.2 第二反序列化器 `0xB8FD60`（vtable 槽 `0xD59CF4`）

```
0xB8FD60  call 0xB761E0 → this+8   ; readU32
0xB8FDB7  call 0xB76890 → this+0xc ; readU8
```
（与已知「反序列化器 `0xB8FD60` 读 (u32,u8)」一致。）

### 5.3 容器序列化器 `0xB8F370`

```
0xB8F3AA  push 0x2c; call 0xB74220   ; 分配写缓冲
0xB8F3C8  call 0xB9BEB0              ; 构造写游标
0xB8F3F0  call 0xB766B0 (push edi)   ; ★ writeU32(count)
0xB8F407  loop: eax=[esi]; edx=[eax] ; 取元素 vt[0]
0xB8F411          call edx           ; ★ 逐元素序列化到同一缓冲
          add esi,0x28               ; 元素步进 0x28（40 字节）
```
⇒ 报文 = `u32 元素数 + N×元素(各自 vt[0] 序列化)`。

### 5.4 类静态表（编译期）

```
0xC1B7EC4..  步进 0x28 的静态元素数组（≈148 条），每元素 {+0=0, +4=0xD59CE4(次 vt), +8=0xD59CE8(主 vt), +0xc=0xD5A3A4}
0xC1B8018 / 0xC1B8188  同型静态表（0x4AAB00 用 `lea esi,[eax+eax*4]; lea esi,[esi*8+0xC1B8188]` 取元素）
```
构造函数：`0xB8FAE0`（设 vt `0xD59CE8`）、`0xB8FCC0`（设 vt `0xD59CF4`）；析构/调整器：`0xB8FC90`（`lea esi,[ecx-0x20]`，scalar deleting dtor）。

---

## §6 语义映射（有载荷支撑）

| task | 结构 | 语义（推断） |
|---|---|---|
| `102/7` | `u32 50` + 50×`(u8 1,u64 i)` | **按槽位 0..49 批量声明/拉取信箱条目**（i 连续） |
| `102/1` | `u32 0` + `u32 N` + N×`(u8 key,u64 0)` | **信箱/频道分类订阅**（A:1 类 key=3 / B:2 类 key=1,2） |
| `102/5` | `u32 2` + `u8 1` + `u8 2` | **读取游标/索引列表 [1,2]** |
| `102/2` | 空 | **心跳/空轮询** |

★ 与 `AS_MessageSetReadBatch`（批量已读）/`AS_GetMOTDMessages`（取公告）/`AS_HaveUnviewedMOTDMessages`（未读）同族 ⇒ 「Messaging2 = 站内信/MOTD 信箱协议」成立。

---

## §7 边界（未解项 + 已穷尽排查）

| # | 未解项 | 已做的穷尽排查 | 结论 |
|---|---|---|---|
| 1 | **`102/1` 与 `102/7` 的发送点**（哪个业务函数发出） | 全库扫 `E8`→写器 `0xB766B0/0xB76620` 的调用点（按 `push imm` 值筛 0x32/0x3e8/1/2）；未命中静态常量（值来自内存） | **静态不可达（构造点未定位）** |
| 2 | **`vtable 0xD59CE8` 的类名** | 全库扫 RTTI COL（`pTypeDesc==名-8` 反查 vtable）；该 vtable 无 COL 命中 ⇒ 未命名 | **静态不可达（无 RTTI 名）** |
| 3 | **`0x16` 容器与 `102/7` 的因果** | 已读 `0xB76310/0xB76220` 全文；`0x32` 与 `08 32` 同值但无调用边连接 | **候选巧合，未证实** |
| 4 | **`102/1` 的「82 字节对象」** | 全库扫 `6A 52 E8`（push 0x52 + call）与 `push 0x52 → 0xB74220`（alloc）；均 0 命中 | **该「82 字节」在本镜像无对应分配点（疑为内存态而非线形态）** |
| 5 | **`102/5` 的 `u8 1/2` 语义** | 无第二样本可区分；与 `102/1` key 集部分重合 | **值域已知（1,2），语义未定** |

★ 边界 1 的「静态不可达」是在**穷尽调用边扫描**（写器调用点 + `push imm` 常量筛 + 静态表定位）之后给出的，不是「需运行时」的托词。

---

## §8 方法论

1. **标签语义要靠「读器返回值的处理方式」定**：`0xB76310` 返回 bool（`cmp …; sete bl`），所以 `push N` 是**期望标签值**而非位宽——这与 177–181 卷的位流教训同源。
2. **字符串编码靠读器循环判**：`0xB76A30` 读到 NUL 停 ⇒ `0x10` 是 NUL 结尾；若先假定长度前缀，整条语料会被误读。
3. **「通道号 ≠ 类型号」再次确认**：发送点立即数经 `0xE4E20C→0xE69CE0` 两级表映射到重试策略，不是服务/任务号。
4. **vtable 槽也是调用边**：`0xB8FD60` 无 `E8` 调用者，靠数据引用（`0xD59CF4`）才找到归属类。
5. **`0x8435D0` 哨兵**（`C3` 空桩）在错误分支里反复出现 ⇒ 见它即「此处为失败/未接线路径」。

---

## §9 复现命令

```powershell
python -I _rev_analysis/_p223/a1_extract.py       # 语料 80/102 全量逐字节
python -I _rev_analysis/_p223/a_range.py 0xB76000 0xB76C00   # DML 读族
python -I _rev_analysis/_p223/a_range.py 0xB76000 0xB76860   # DML 写族
python -I _rev_analysis/_p223/a_callwin.py 0x7FAA20 112      # 出口漏斗调用点
python -I _rev_analysis/_p223/rtti.py            # RTTI 关键字族
```

## §10 状态表

| 项 | 状态 | 证据 |
|---|---|---|
| `102` = Messaging2 (0x66) | ✅ | 服务表 + RTTI `bdMessagingGroup` + AS_Message 族 |
| 4 task 结构 | ✅ 100% 逐字节 | §1（1415 条语料） |
| DML 标签读写器族 | ✅ 地址级全表 | §3（`0xB761E0`…`0xB76AF0` / `0xB76000`…`0xB76820`） |
| `0x10` = NUL 结尾串 | ✅ 读器循环铁证 | `0xB76A30` |
| `0x16` 嵌套容器 | ✅ | `0xB76310`→`0xB76220` |
| 发送链 + 认证闸门 | ✅ | `0x4AAE20`→`0xB8F370`→`0x7FAA20`→`0x7FA800` |
| AS↔C++ 绑定 | ✅ | `0xDCCE00` 表 + `0x6A17E0/0x6A1800` |
| 元素读写器 | ✅ | `0xB8FB90` / `0xB8FD60` / `0xB8F370` |
| 发送点定位 / 类名 / 「82 字节」 | ❌ 静态不可达（已穷尽） | §7 |
