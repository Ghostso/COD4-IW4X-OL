# 153 · 房间动作「入队 → 出网」黑箱关闭：三层队列 + clientState 闸门 + 统一发包漏斗 `0x7FAA20`

> 卷次：153（lobby 线路）
> 前置：138（clientState 闸门）、148（房间按钮全链路）、149（出站三入队一真发）、150（FrameUpdate + vtable 全表）、151（容器语义）、152（房间子系统单例）
> 状态：**148–152 遗留的唯一未闭合项——「Ready / ChangeTeamRequest 入队后到底怎么出网」——本卷闭合。**

---

## 一、结论摘要（七个字节级事实）

| # | 事实 | 证据地址 |
|---|---|---|
| ① | **`0x6301A0` = `dwRoomImp::SendReady`**：栈上构造 `{vt=0xDC7624, type=0x10, ready=al}`，结构 12 字节 | `0x6301AE..0x6301C8` |
| ② | **房间动作不是只有一条入队路**：`[dwRoomImp+0x289]!=0` 时走 **vt[0x148]=`0x62C580`** → `0x62C380(kind=2)` → 入 `+0x3A0D4[2]`；否则走 `0x62C5A0` → 入 `+0x3A098` 环形队列 | `0x6300FE..0x630127` |
| ③ | **`+0x3A098` 是「1 秒延迟投递环」**：FrameUpdate 每帧扫它，节点时间戳 ≥ `1.0`（`0xcaddd8`）才提升进 `+0x3A0D4` | `0x632FD1..0x6330BE` |
| ④ | **提升时做 4 字节键去重**：对 node+0x10..0x13 用 FNV 素 `0x1000193` 哈希，命中则合并（摘链+释放+count--） | `0x6330D2..0x63317C` |
| ⑤ | **★ `[0x76446B0]`(clientState) ≥ 10 / ≥ 3 是缓存消息的放行阈值**，`<3` 整段跳过 ⇒ **静态上解释了「房间动作发了但服务端收不到」** | `0x633196`、`0x633292`、`0x63335D`、`0x633423` |
| ⑥ | **`0x62ACD0` = 「合法收件人过滤 + 归并」**：查 `[room+0x1C]` 的连接对象 `+1` 已连、成员表 `+0x18` 计数 / 步进 `0x60` 找到收件人，找不到⇒丢弃 | `0x62ACD0` |
| ⑦ | **★ 真正的出网漏斗 = `0x7FAA20`**（全镜像 ≈110 个调用点），房间侧只经 `0x7E8240`(5 参) / `0x7E8300`(6 参) 两条孪生建包器汇入；再 `0x7FA800` → session 表 `[0x7644694]`→`[0x7659F88+idx*0x114]`→`vt[0x24]` | `0x7E8240`、`0x7E8300`、`0x7FAA20`、`0x7FA800` |

---

## 二、`0x6301A0`：房间「准备」按钮的实际发包构造点

（这是 150 卷记录 `vt[33]=0x6301A0` 的函数体，本卷首次逐指令展开。）

```asm
0x6301A0  push ebp / mov ebp,esp / sub esp,0xC
0x6301A6  mov al, byte ptr [ebp+8]        ; al = ready 布尔（Flash 传入）
0x6301A9  push esi
0x6301AA  push ecx                        ; ★ ecx = this（dwRoomImp）压栈留用
0x6301AB  lea esi, [ebp-0xC]              ; esi → 消息体在栈上
0x6301AE  mov dword ptr [ebp-8], 0x10     ; +4 = type = 0x10  (dwRoomMessageReady)
0x6301B5  mov dword ptr [ebp-0xC], 0xDC7624 ; +0 = vtable
0x6301BC  mov byte ptr [ebp-4], al        ; +8 = ready 字节
0x6301BF  call 0x62C5A0                   ; → 房间动作入队
0x6301C4  pop esi / mov esp,ebp / pop ebp / ret 4
```

**结构定案（12 字节）**：

```
+0x00  vtable  = 0xDC7624          ← 43 类消息 vtable 表第 25 行
+0x04  type    = 0x00000010        ← dwRoomMessageReady
+0x08  payload = [ready:u8]        ← 1 字节
```

`[obj+4]` 就是 13 位位流头里的「类型号」（与 45 卷、94 卷一致）。`0x62C5A0` 内 `mov eax,[esi+4]` / `mov edx,[esi]` / `call [edx]` 正是「取 type + 调 vt[0] 序列化器」。

> `0x6301A0` **没有任何 E8 直接调用点**；它只以地址形式出现在 vtable 里：`0xDC72F8`（= dwRoomImp vtable `0xDC7274` 的 slot **0x84/4 = 33**，与 150 卷一致）和 `0xDC7798`（第二张表）。

---

## 三、更正 148/149：房间动作有**两条**入队路径（`+0x289` 分叉）

150 卷只记录了 `0x62C5A0`。本卷在同一「准备」流程的上位函数里发现分叉：

```asm
0x6300FE  mov dword ptr [ebp-0xC], 0x0F    ; type = 0x0F（另一条房间消息）
0x630105  mov dword ptr [ebp-0x10], 0xDC7618 ; vtable（表第 24 行）
0x63010C  mov dword ptr [ebp-8], ebx        ; payload
0x63010F  je 0x630123                       ; ← 依赖 0x6300F1 的 cmp
0x6300F1  cmp byte ptr [edi+0x289], 0       ; ★ 分叉开关
0x630111  mov eax,[edi] / mov edx,[eax+0x148]
0x630119  lea ecx,[ebp-0x10] / push ecx / mov ecx,edi / call edx   ; ★ vt[0x148]
0x630123  push edi / lea esi,[ebp-0x10] / call 0x62C5A0           ; 否则走 0x62C5A0
```

而 **`vt[0x148]` 的实体 = `0x62C580`**（`0xDC7274+0x148 = 0xDC73BC` 处存放）：

```asm
0x62C580  push ebp / mov ebp,esp
0x62C583  mov eax, [ebp+8] / push eax
0x62C587  push ecx
0x62C588  mov eax, 2            ; ★ kind = 2
0x62C58D  call 0x62C380         ; Family A 发送族，kind=2 ⇒ 入队分支
0x62C592  ret 4
```

`0x62C380` 在 `0x62C393 cmp edi,4` 处判 kind：**kind≠4 ⇒ 落到 `0x62C4BE` 起的入队分支**，末尾：

```asm
0x62C530  mov ecx,[ebp+8]                 ; dwRoomImp
0x62C533  lea eax,[edi+edi*2+0xE82F]      ; edi=2 ⇒ 0xE835
0x62C53A  mov edx,[ecx+eax*4+4]           ; = [dwRoomImp + 0x3A0D4 + 4]（尾部）
0x62C53E  lea eax,[ecx+eax*4]             ; = dwRoomImp + 0x3A0D4
0x62C547  call 0x656A10                   ; 链表插入（+0x3A0D4 队列）
```

算一下：`0xE835*4 = 0x3A0D4` ✅。
⇒ **路径 B：`+0x289!=0` ⇒ 直接入 `+0x3A0D4`（kind 索引槽 2）。**
⇒ **路径 A：`+0x289==0` ⇒ `0x62C5A0` 入 `+0x3A098`（延迟环）。**

148/149 卷「入队只有 0x62C5A0 一途」→ 本卷更正为**两途**。

---

## 四、`0x62C5A0` 的落点复核（对照 149 卷）

```asm
0x62C5B4  mov edi,[ebp+8]
0x62C5BF  add edi, 0x3A098                 ; ★ 容器基址 = dwRoomImp+0x3A098
0x62C5D4  call 0x654CD0                    ; 哈希表「查是否已存在」
0x62C5DB  je 0x62C690                      ; 不存在 ⇒ 新建节点
0x62C651  call 0x654BF0                    ; 已存在 ⇒ 覆盖
```

`0x3A098` 不是链表而是**哈希表**：`+0x3A098`=count、`+0x3A09C`=cap、`+0x3A0A8`=bucket 数组（FrameUpdate 里 `0x632FE3` / `0x6330A8` 的用法印证）。

---

## 五、FrameUpdate `0x632D90` 三段：提升 → 去重 → clientState 闸门

### 5.1 段一：`+0x3A098` → `+0x3A0D4`（1 秒延迟）

```asm
0x632FD1  cmp dword ptr [ebx+0x3A098], 0
0x632FD7  je 0x633006
0x632FD9  mov edx,[ebx+0x3A09C]            ; cap
0x632FF5  inc eax / add ecx,4 / cmp eax,edx ; 找第一个非空桶
0x633003  mov eax,[ecx+eax*4]              ; eax = 节点指针
0x63300B  test eax,eax / je 0x633196
0x633018  mov ecx,esi / call 0xB75DA0      ; 取节点时间戳
0x63301F  fcomp dword ptr [0xcaddd8]       ; ★ 与 1.0f 比较
0x63302A  jne 0x63317E                     ; <1 秒 ⇒ 只推进迭代器 0x654D60
0x633030  cmp dword ptr [esi+8],0          ; 节点 +8 = 消息指针
0x63307F  mov ecx,[ebx+0x3A0D8]            ; ★ +0x3A0D4 队列尾部
0x633085  lea eax,[ebx+0x3A0D4]
0x633093  call 0x656A10                    ; 插入 +0x3A0D4
...
0x633176  dec dword ptr [ebx+0x3A098]      ; 原环 count--
```

`0xcaddd8 = 1.0f`（实测读盘）。⇒ **房间动作被强制延迟 ≥1 秒后才进主发送队列。**

### 5.2 段二：4 字节键 FNV 去重

```asm
0x6330D8  movzx eax, byte ptr [ecx+0x11]
0x6330E3  imul edx, edx, 0x1000193         ; ★ FNV-1a 素数
0x6330E9  xor eax, edx
0x6330EF  imul eax, eax, 0x1000193
0x6330F5  xor eax, edx                     ; 键 = node+0x10..0x13 四字节
0x633103  mov edx,[ebx+0x3A09C] / dec edx / and edx,eax
0x633112  mov edi,[eax+edx*4]              ; 桶链
0x633121  cmp ecx,dword ptr [edi+0x10]     ; 键相同 ⇒ 命中
0x633176  dec dword ptr [ebx+0x3A098]      ; 合并：摘链 + 释放 + count--
```

⇒ **同键房间消息在 1 秒窗内被合并**（这是「连点准备只发一次」的静态根据）。

### 5.3 段三：**clientState 闸门（★ 本次最重要的新事实）**

```asm
0x633196  cmp dword ptr [0x331c0c8], 0     ; 加密全局（151 卷：mask 0xD362501F）
0x63319D  mov esi, dword ptr [0x76446b0]   ; ★ esi = clientState (CA_*)
0x6331A6  je  0x633493                     ; 无连接对象 ⇒ 整段跳过
0x6331AC  mov edx,[ebx] / mov eax,[edx+0x54]
0x6331B5  call eax                         ; vt[0x54] = "已连接?" 探测
0x6331B7  je  0x633493
...
0x633292  cmp esi, 0xa                     ; ★ clientState >= 10 ?
0x633295  jl  0x63335D
   ... 走 0x774980(format) + 0x675260 + 0x675840，把 +0x3A100 缓存逐条投递
0x63335D  cmp esi, 3                       ; ★ clientState >= 3 ?
0x633360  jl  0x633423
   ... 走 0x774980 + 0x675260（6 个 dword 参数）
0x633423  cmp dword ptr [ebx+0x3A120], 0   ; <3 ⇒ 仅走内部广播 0x634340
0x63342A  je  0x633493
```

**这是「房间动作没有发出去」在静态层面的直接解释**：`[0x76446B0]` = clientState，只有 `>= 10` 或 `>= 3` 才放行缓存投递；`< 3` 时 `0x3A100` 缓存里的房间消息**永远不会被写进发送环**。

> 与 138 卷「`[0x76446B0]` = clientState(CA_*)，开局闸门 <3 ⇒ 拒绝本地开局」互为独立印证：同一全局，两处闸门。

---

## 六、`0x62ACD0`：合法收件人过滤（房间消息的第二道门）

FrameUpdate 在 `0x6335D7` 调用它（**唯一调用点**）。

```asm
0x62ACD0  mov edi,[ebp+8]
0x62ACDC  mov eax,[edi+0x1c] / test / je 0x62AE59     ; ① 必须有网络连接对象
0x62ACE7  cmp byte ptr [eax+1], 0 / je 0x62AE59       ; ② 该对象 +1 = 已连接标志
0x62ACF1  call 0x803830 / test esi / je 0x62AE59      ; ③ srpc 单例必须存在
0x62AD02  call 0xB7A670 / cmp eax,2 / jne 0x62AE59    ; ④ srpc 状态 == 2
0x62AD12  call 0xB7A770 / test / je 0x62AE59          ; ⑤ 会话对象非空
0x62AD1F  cmp byte ptr [edi+0x283], 0 / jne 0x62AE59  ; ⑥ 不在「拆房」流程中
```

**六个闸门任一失败 ⇒ 静默 return（不报错、不重试）。**

随后扫描 4 个 kind 子队列（`+0x3A0F4` 每 −0xC 一档，直到 `+0x3A0BC`）：

```asm
0x62AD40  mov eax,4 / lea ecx,[edi+0x3A0F4]
0x62AD50  cmp dword ptr [ecx],0 / jne 0x62AD99
0x62AD55  sub ecx,0xC / dec eax / jns 0x62AD50
0x62ADAF  mov edi,[edi+0x3A0BC]              ; 取该 kind 队头
0x62ADB5  mov eax,[edi+8] / mov ecx,[edi+0xC] ; 收件人 = 8 字节（低/高）
0x62ADE3  mov ecx,[ebp+8] / mov ecx,[ecx+0x1C] ; room→连接对象
0x62ADE6  mov edx,[ecx+0x18]                  ; ★ 成员数
0x62ADEF  add ecx,0x40                        ; ★ 成员记录基址 +0x40
0x62ADF2  cmp dword ptr [ecx], esi            ; 比较成员 ID
0x62ADFF  add ecx,0x60                        ; ★ 步进 0x60
0x62AE06  cmp eax,edx / jae 0x62AE17          ; 找不到 ⇒ 跳过（丢弃）
0x62AE0A  push edx / lea eax,[ebp-0x1C] / push eax / call 0x656A10   ; 收集
```

⇒ **房间消息只投给「成员表里存在」的收件人**；非成员收件人的消息被静默丢弃。成员记录步进 **0x60**、ID 在 **+0x40**。这解释了 139 卷「Manifold 归属者 ID：0=广播、=账号ID=定向、其他⇒静默丢弃」为何如此——丢弃点就在这里。

---

## 七、最终出网：两条孪生建包器 → 统一漏斗 `0x7FAA20`

### 7.1 `0x7E8240`（5 参数版）

```asm
0x7E8240  push ebp / mov ebp,esp / push ecx / push esi
0x7E8245  call 0x803830                 ; srpc
0x7E8256  call 0xB7A670 / cmp eax,2     ; ★ 闸门：状态==2
0x7E8266  call 0xB7A770 / test / je     ; ★ 闸门：会话非空
0x7E8273  ... push 6 个参数（[edi+0x14],[edi+0x10] + [ebp+8/0xC/0x10]）
0x7E828D  call 0xB8ED40                 ; 建包（5 段）
0x7E8299  inc dword ptr [0x849B798]     ; 引用计数++
0x7E82A5  ... push 0x7E8210             ; 完成回调
0x7E82BC  push 0x16                     ; ★ 传输层 type = 22
0x7E82C2  call 0x7FAA20                 ; → 统一漏斗
```

### 7.2 `0x7E8300`（6 参数版）

完全同构，只是 `call 0xB8EE70`（6 段）与 `push 0x16`；并且**它有 `0x803830`/`B7A670==2`/`B7A770!=0` 同一组闸门**。

### 7.3 调用者（实测穷举）

| 建包器 | 调用点 | 归属 |
|---|---|---|
| `0x7E8240` | `0x62B800` / `0x62C45A` / `0x633839` | `0x62B7xx` 发送器 / `0x62C380`(kind=4) / FrameUpdate 批量包 |
| `0x7E8300` | `0x62C93D` | `0x62C870`(kind=4) —— **全镜像唯一调用点** |

⇒ 150 卷「kind==4 ⇒ 真发，唯一真发点是 `0x7E8300`」**成立**；本卷补上它的孪生兄弟 `0x7E8240`（此前漏计）。

### 7.4 `0x7FAA20` = 统一发包漏斗

```asm
0x7FAA20  push ebp / mov ebp,esp
0x7FAA33  push 0x8435D0                 ; ★ 哨兵回调 = 单字节 C3 (ret)
0x7FAA56  call 0x7FA800                 ; 真正落到会话层
0x7FAA85  ret
```

实测 `0x8435D0` 首字节 = **`0xC3`**（`ret`）⇒ 这就是 137 卷「B9 双命令表+哨兵桩」中的同一个桩，说明这里的「回调位」是被**故意留空**的。

`0x62C5A0` 里也埋了同一个桩（`0x62C7xx` 附近 `push 0x8435D0`），一脉相承。

### 7.5 `0x7FA800` = 会话层投递

```asm
0x7FA800  ...
0x7FA81D  mov eax,[0x7644694]           ; ★ 会话槽位索引
0x7FA826  imul eax,eax,0x114            ; ★ 会话结构大小 0x114
0x7FA82C  mov eax,[eax+0x7659F88]       ; ★ 会话对象表基址 0x7659F88
0x7FA832  mov edx,[eax] / mov ecx,eax
0x7FA836  mov eax,[edx+0x24] / call eax ; ★ vt[0x24] = 会话发送接口
0x7FA84D  mov esi, 0xE56FFE0            ; ★ 通道槽表
0x7FA852  cmp dword ptr [esi],0 / je 0x7FA920
0x7FA85B  add esi,0x50                  ; ★ 步进 0x50
0x7FA85E  cmp esi,0xE5713E0             ; 表尾
0x7FA8A8  call 0x7FA640                 ; 入通道队列
```

通道槽表 = `0xE56FFE0 .. 0xE5713E0`，步进 `0x50` ⇒ **`0x1400/0x50 = 64` 个发送通道槽**。

---

## 八、八个房间容器一览（本卷补全 `+0x3A090..+0x3A120`）

| 偏移 | 类型 | 语义 | 关键证据 |
|---|---|---|---|
| `+0x3A090` | timer | 房间动作节流计时 | `0x632F84` `0xB75DA0`+`fild [x+0xC]` |
| `+0x3A098` | **哈希表**（count/cap/buckets） | **房间动作延迟投递环**（1 秒） | `0x62C5BF`、`0x632FD1` |
| `+0x3A09C` | u32 | 上表容量 | `0x632FD9`、`0x633103` |
| `+0x3A0A8` | bucket 数组 | 上表桶 | `0x632FE3`、`0x6330A8` |
| `+0x3A0B0` | list（head/tail/count） | **原始报文 FIFO**（未过滤） | `0x629730`→`0x6568F0`；`0x633517` 出队 |
| `+0x3A0BC` | **4 槽队列数组**（步进 0xC） | 按 kind 分流的待发送队列 | `0x62AD99`、`0x6336EC` |
| `+0x3A0D4` | list（head/tail/count） | **主出站队列**（kind 索引 0..3 的其中一槽） | `0x62C53E`、`0x62C72F`、`0x633085` |
| `+0x3A0F8` | timer | 批量打包节流（阈 `0.2s`=`0xde7c10`） | `0x63361B` `fcomp [0xde7c10]` |
| `+0x3A100` | list | **入站消息缓存**（按 clientState 10/3 放行） | `0x6332A6`、`0x6333C1` |
| `+0x3A110` | timer | 入站缓存老化（`0xdada58`） | `0x633379` |
| `+0x3A118` | list | 成员记录表（步进 `0x208`，用于广播） | `0x6331BD`、`0x654E00` |
| `+0x3A120` | u32 | 广播开关 | `0x633423` |

---

## 九、更正前卷

| 卷 | 原结论 | 本卷更正 |
|---|---|---|
| 148/149 | 房间动作入队只有 `0x62C5A0` 一途 | **两途**：`+0x289!=0` 走 `vt[0x148]=0x62C580`→kind=2→`+0x3A0D4` |
| 149 | 「kind==4 是唯一真发」 | 成立，但**真发建包器有两个**：`0x7E8300`（6 参，唯一调用 `0x62C93D`）**与 `0x7E8240`（5 参，调用 `0x62B800/0x62C45A/0x633839`）** |
| 152 | 「所有出网必经 `0x62C870(kind=4)` → `0x7E8300`」 | 需补：最终漏斗是 **`0x7FAA20`**（≈110 调用点），`0x7E8300/0x7E8240` 只是房间子系统的两条入口 |
| 150 | FrameUpdate 只管「可达性 + 三容器」 | 补：`+0x3A098` 1 秒延迟提升、4 字节 FNV 去重、**clientState 10/3 闸门** |

---

## 十、未闭合 / 边界

1. `0x7E7EE0`（`push 0x13` = 传输 type 19 = P2PInfo）等 6 个 `0x7E7xxx` 函数**直接**调 `0x7FAA20`，不经 `0x62Cxxx`；它们与 `0x7E8240/0x7E8300` 的分工（哪条走「房间信道」、哪条走「监听/回环」）尚未按类型逐条对账。
2. `0x7FA800` 的 64 个通道槽 `0xE56FFE0..+0x50*64` 各自的 `+0x28` 回调（`0x7FA6CD` 处拷贝）尚未解出。
3. `0x7E8240/0x7E8300` 里 `[edi+0x10]` / `[edi+0x14]` 的两个句柄（应是「会话号 + 通道号」）尚未与 `0x7644694` 对上。

---

## 十一、方法论

1. **「入队」不是终点，必须再往下数三层**：延迟环 → 主出站队列 → 建包器 → 漏斗。148–152 卷都停在第一层，所以反复「看得到入队、看不到出网」。
2. **`push imm32` 与 `mov [ebp-8], imm32` 是两种不同的「常量」**：前者是调用方传的**传输层 type**（`0x16`/`0x13`/`0x22`），后者才是**消息类型号**（`0x10`/`0x0F`）。混读会把两层协议搅在一起。
3. **同一全局变量在不同函数里的阈值代表不同语义**：`[0x76446B0]` 在 138 卷是「开局闸门 <3」，在本卷是「缓存投递闸门 10/3」。**必须按调用点分别记录，不能合并成一个「状态」**。
4. **「有一条 E8 调用点」不等于「入口唯一」**：`0x6301A0` 零 E8、只有 vtable 引用；`0x62ACD0` 只有 1 个 E8。查入口要**同时扫 E8 与 `.rdata` 常量表**。
5. **哨兵桩要用字节读验证，不能靠命名**：`0x8435D0` 实读 `C3` 才敢断定它是空桩。
6. **队列结构靠「谁写 count」自证**：`0x656A10` 只 `inc [ebx+8]` ⇒ (head,tail,count) 三元组；`0x654CD0` 只 `dec [ebx]` ⇒ 哈希表 count。

---

## 十二、黑箱账目更新

- 关闭：**房间动作 入队→出网 全链**（本卷）。
- 新开：`0x7E7xxx` 六函数 ↔ `0x7E8240/0x7E8300` 两建包器的**信道分工**；`0x7FA800` 64 通道槽语义。
- 累计：lobby 线路静态黑箱自 137 卷起 13 项 → 152 卷 1 项 → **本卷 0 项（主链）**，剩 2 项为「信道分工」细化项。
