# CLIENT-BOOKING-BATTLE-OBJECT-016
# matching 的 "type-2 network object" 到底是什么，以及它是否是 accepted → Battle UDP 的桥梁

> 2026-10-08 执行。**纯静态**。未修改 client / server / senderId / booking response /
> SessionId / Battle endpoint / 28960。未 hook、未 patch、未伪造 UDP/DTLS、未运行游戏。
>
> 分析源：CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin
> （运行期已解壳镜像，10,899,456 B，**VA = 0x00400000 + 文件偏移**，
> 可读范围 `0x00400000 .. 0x00E65000`）。
> 所有 VA 为镜像 VA（imagebase 0x00400000）。
>
> 承接：013（A/B 已关）、014（accepted 出口枚举）、015（listener 7/7 REFUTED + UDP socket 锚点）。
> 本轮**只**沿 015 留下的 `matching->vt+0x5C = 0x62FDE0` 这一条新轴推进。

---

## 0. 结论先行（一句话回答本轮最终问题）

```
TYPE2_OBJECT = 全局 Demonware 网络核单例 [0x8269774] 当前挂载的 "transport 连接对象"
               在 "已连接 / connected" 状态下的形态。

它的 socket 是：
   socket(AF_INET, SOCK_STREAM = 1, IPPROTO_TCP = 6)   ← TCP，不是 UDP
再 connect() 到 Demonware 服务地址（host + 16-bit port）：
   0x7F3800 状态机 case 2 → 日志字符串 "DW_LOBBY_CONNECTED"（CONFIRMED，字符串证据）

⇒ type-2 对象 = Demonware LOBBY TCP 连接。
⇒ 它**不是** accepted → Battle UDP(28960) 的桥梁。
⇒ TYPE2_TO_UDP_RELATION      = REFUTED
⇒ ACCEPTED_TO_TYPE2_RELATION = 数据流存在，但方向是 "accepted 读取/使用 type-2"，
   不是 "accepted 创建 type-2"；不存在 accepted → Battle 的因果链。
⇒ BATTLE_TRIGGER_PATH        = UNRESOLVED
```

**对 015 的一处重要更正**：015 §2 把 `0x62FDE0` 概括为"取全局网络对象 → 取类型 →
`cmp eax,2`"，遗漏了它前面**两道前置守卫**和 `0xb7a670` 的**归一化语义**。
完整反汇编见 §2，语义见 §3。这个更正不改变 015 的任何已关闭结论，
但它把 "type 2" 从"某种不明网络对象"精确定位到**一条 TCP 连接状态**。

---

## 1. FACT_BASELINE（承接 003/006/012/013/014/015，未重查）

```
image_best.bin VA 映射            = 0x00400000 + fileoffset，可读 0x400000..0xE65000   CONFIRMED
超出 0xE65000 的全局              = 只能看到引用它的指令，看不到内容（本轮再次验证）   CONFIRMED
matching 单例                     = [0x082E13FC]，vtable 0x00DC7274，ctor 0x0062C000    CONFIRMED
matching vtable +0x5C             = 0x0062FDE0                                          CONFIRMED（本轮复核，§2）
accepted handler                  = 0x00632680（matching vt+0x13C）                     CONFIRMED
accepted 分支 vt+0x5C 门控调用点   = 0x0063281E call [esi.vt+0x5C] / 0x632822 jne 0x632864 CONFIRMED
accepted down-stream 门控          = 0x629F80 → 0x7F49A0（调用点 0x629FBD）              CONFIRMED
Lobby TCP 通道                     = 0xB81EF0 → 0xBA4080（015 已排除为 Battle）           CONFIRMED（本轮给出"为什么是 Lobby"）
senderId / A-B                    = LOW32/HIGH32 MATCH，已关闭，未重查                    已关闭
listener 链 [matching+4]           = 7/7 REFUTED（5 空实现 + wargod + UI/CEF）            已关闭
[0x0849B61C]                      = UI flag，2 个 reader，非 Battle                      已关闭
0x77FBF0                          = IPX LAN broadcast socket，非 Battle                  已关闭
```

### 1.1 本轮新增的一条方法论更正（重要，给接力者）

015 的 `_015_glob.py` 有**系统性 1 字节回溯假阳性**：

真实指令 `8B 0D 08 BB 4A 08` = `mov ecx, [0x084ABB08]`（位于 `0x470172`）。
`_015_glob.py` 从立即数处（`0x470174`）只回溯 1 字节到 `0x470173`，
而该字节恰好是 `0x0D`（合法 opcode），于是解出假指令
`or eax, 0x084ABB08` 并把引用位置报成写入/读取。

证据：

```asm
0x00470172  8b0d08bb4a08   mov ecx, dword ptr [0x84abb08]   ← 真实指令
（_015_glob.py 报：0x00470173  0d08bb4a08  or eax, 0x84abb08  ← 假）
```

⇒ 凡 `_015_glob.py` 报出的 `or/and/add/xor eax, <0x08xxxxxx 全局>`，
    若原始字节中出现 `8B 0D` / `8B 15` / `A1`，必须用 `_015_dis2.py` 对齐复核。
本轮据此把 `[0x84ABB08]` 的真实引用数修正为**约 130 处 `mov reg,[0x84ABB08]`**。

---

## 2. TYPE2_GATE_FUNCTION = 0x0062FDE0（完整反汇编，CONFIRMED）

```
0062FDE0  8B411C              mov  eax, dword ptr [ecx + 0x1C]
0062FDE3  56                  push esi
0062FDE4  85C0                test eax, eax
0062FDE6  7406                je   0x0062FDEE
0062FDE8  80780100            cmp  byte ptr [eax + 1], 0
0062FDEC  750E                jne  0x0062FDFC
0062FDEE  8B8158070100        mov  eax, dword ptr [ecx + 0x10758]
0062FDF4  0B815C070100        or   eax, dword ptr [ecx + 0x1075C]
0062FDFA  7429                je   0x0062FE25
0062FDFC  E82F3A1D00          call 0x00803830            ; 取全局网络核单例
0062FE01  8BF0                mov  esi, eax
0062FE03  85F6                test esi, esi
0062FE05  741E                je   0x0062FE25
0062FE07  8BCE                mov  ecx, esi
0062FE09  E862A85400          call 0x00B7A670            ; 归一化 "transport type"
0062FE0E  83F802              cmp  eax, 2
0062FE11  7512                jne  0x0062FE25
0062FE13  8BCE                mov  ecx, esi
0062FE15  E856A95400          call 0x00B7A770            ; 取 [单例+0x3C] 句柄
0062FE1A  85C0                test eax, eax
0062FE1C  7407                je   0x0062FE25
0062FE1E  B801000000          mov  eax, 1
0062FE23  5E                  pop  esi
0062FE24  C3                  ret
0062FE25  33C0                xor  eax, eax
0062FE27  5E                  pop  esi
0062FE28  C3                  ret
0062FE29  CC CC CC CC CC CC CC                        ; int3 填充 → 函数边界确认
```

### 2.1 this / 参数 / 返回值（CONFIRMED）

```
调用约定   __thiscall
this       ECX = matching 单例 [0x082E13FC]（唯一调用点 0x63281E，ecx=esi=matching）
           证据：调用点 0x632680 起 0x63268B mov esi,ecx，0x63281E 前 ecx 未被改写
参数       无（栈上无 push；ret 而非 ret n）
返回值     EAX = bool
             1 = "存在有效 type-2 network object" → accepted 分支跳过 listener 广播
             0 = "不存在"                       → accepted 分支执行 listener 广播
副作用     无。函数不写任何内存（全为 mov/test/cmp/call）
```

### 2.2 与 accepted handler 的接口（CONFIRMED）

```asm
0x0063281E  call [esi.vt+0x5C]        ; esi = matching, vt = 0xDC7274
0x00632822  jne  0x632864             ; 返回非 0（=1）→ 跳过下面全部
0x00632824  mov  edi,[esi+4]          ; 只有返回 0 才到达 listener 广播
0x00632827  mov  byte [0x0849B61C], 1
...
0x00632864  call 0x655930             ; 清理
```

附：matching vtable `0x00DC7274` 第 23 项（字节偏移 +0x5C）= `0x0062FDE0`。CONFIRMED。

---

## 3. TYPE2_CHECK_SEMANTICS（"type 2 network object exists" 的精确判据）

判定不是单字段比较，而是**四段链**。逐段给出，全部 CONFIRMED（指令级）。

### 3.1 前置守卫（015 遗漏，本轮补齐）

```
GATE-A: [this+0x1C] != 0 且 byte[[this+0x1C] + 1] != 0
        → 成立则跳过 GATE-B，直接进入 NET-CHECK
GATE-B: ([this+0x10758] | [this+0x1075C]) != 0
        → 不成立则**直接 return 0**（广播）
NET-CHECK: 见 3.2
```

`this` = matching 单例。`[matching+0x1C]` 是一个对象指针；同一字段在 matching 的
其它函数里被当作"会话/地址对"读取：

```asm
; 0x006317F5 (matching 内 type-2 消费者)
mov edx, [ecx+0x1C]        ; ecx = [ebp+8] = 会话对象
mov ecx, [edx+0x14]        ; 第二个 dword
mov edx, [edx+0x10]        ; 第一个 dword
push ecx / push edx        ; 成对作为参数传下去
call 0xB8EC00
```

⇒ `[matching+0x1C]` = 一个 16 字节级的小对象，+0x10/+0x14 是**成对字段**。
等级：`[matching+0x1C] 存在性参与门控` = CONFIRMED；
     `其 +0x10/+0x14 的语义（IP:port? 64-bit id?）` = CANDIDATE。

### 3.2 NET-CHECK：单例 → transport → 归一化 type

```asm
0x803830( )        → 全局网络核单例 [0x8269774]（懒创建，见 §5）
0xB7A670(sing)     → 归一化 type，要求 == 2
0xB7A770(sing)     → 取 [sing+0x3C] 句柄，要求 != 0
```

#### (a) 0x00803830 = 全局网络核单例懒获取器（CONFIRMED）

```asm
00803830  mov  eax, [0x8269774]
00803835  test eax, eax
00803837  jne  0x8038A7                 ; 已创建 → 直接返回
00803839  push 0x1618                   ; ★ 对象大小 5656 字节
0080383E  call 0xB74220                 ; operator new
00803843  add  esp, 4
00803846  test eax, eax
00803848  je   0x80388C
0080384A  mov  ecx, eax
0080384C  call 0xB82130                 ; ★ 构造（vtable 0xD599DC）
00803851  mov  [0x8269774], eax
0080385A  push 0x0E39B6E8               ; 一个全局（值不可读，超出 dump）
00803861  call 0xB7A400                 ; [sing+0x4F0] = 该全局
00803866  push 4
00803868  call 0xC3E9F5                 ; operator new(4)
0080387B  mov  dword [eax], 0xDE6814    ; ★ 4 字节观察者对象 vtable
00803881  call 0xB7A640                 ; 注册（见 §7）
00803886  mov  eax, [0x8269774]
0080388B  ret
```

单例 vtable = **0x00D599DC**（由 ctor 0xB82130 的 0xB82173 mov [esi],0xD599DC 写入）。
0x803830 的直接调用者约 **280 处**（全镜像），覆盖 0x47/0x4A/0x62/0x63/0x7F/0x81/0xB8 各模块，
说明它是**全局唯一网络核**。CONFIRMED。

#### (b) 0x00B7A670 = 归一化 transport type（CONFIRMED，本轮关键修正）

```asm
00B7A670  push esi
00B7A671  mov  esi, ecx
00B7A673  mov  ecx, [esi + 0x4F4]        ; ★ 当前 transport 指针
00B7A679  test ecx, ecx
00B7A67B  jne  0xB7A681
00B7A67D  xor  eax, eax                  ; 无 transport → 0
00B7A67F  pop  esi / ret
00B7A681  call 0xBA0780                  ; ★ 原始 type
00B7A686  cmp  byte ptr [esi + 0x4F8], 0 ; ★ 单例级"已连接"字节
00B7A68D  jne  0xB7A699                  ; 非 0 → 原样返回
00B7A68F  cmp  eax, 2
00B7A692  jne  0xB7A699
00B7A694  mov  eax, 1                    ; ★ [单例+0x4F8]==0 时 type2 塌缩成 1
00B7A699  pop esi / ret
```

**语义（严格）**：
`0xB7A670(sing) == 2` ⟺ `byte[sing+0x4F8] != 0` **且** `0xBA0780([sing+0x4F4]) == 2`。
（当 `[sing+0x4F8]==0` 时返回值恒不可能为 2。）

#### (c) 0x00BA0780 = 原始 type 读取（CONFIRMED，全镜像唯一调用者 = 0xB7A681）

```asm
00BA0780  cmp  dword [ecx + 0x644], 0
00BA0787  mov  eax, [ecx + 0xC8]         ; ★ 原始 type 字段
00BA078D  je   0xBA079F
00BA078F  cmp  eax, 2
00BA0792  je   0xBA0799
00BA0794  cmp  eax, 1
00BA0797  jne  0xBA07B1
00BA0799  mov  eax, 2                    ; [t+0x644]!=0 且 raw∈{1,2} → 2
00BA079E  ret
00BA079F  cmp  eax, 2
00BA07A2  jne  0xBA07B1
00BA07A4  xor  eax, eax
00BA07A6  cmp  dword [ecx + 0x5E8], 3
00BA07AD  sete al
00BA07B0  inc  eax                       ; [t+0x644]==0 且 raw==2 → 1 或 2
00BA07B1  ret                            ;   取决于 [t+0x5E8]==3
```

⇒ "type 2" 由 **transport+0xC8 原始类型** + **transport+0x644 模式** +
  **transport+0x5E8 状态** + **singleton+0x4F8 字节** 四者共同决定。
  没有任何函数名/字符串可以替代这个判据（遵守任务 §四：禁止用函数名猜语义）。

#### (d) 0x00B7A770 = 取 [sing+0x3C]（CONFIRMED）

```asm
00B7A770  push ebp / mov ebp,esp / SEH
00B7A794  mov  esi, ecx
00B7A796  call 0xB7A670
00B7A79B  cmp  eax, 2
00B7A79E  je   0xB7A7B7
00B7A7A0  call 0x8435D0                 ; 共享空实现（ret），非 type2 → 返回 0
00B7A7A5  xor  eax, eax / ret
00B7A7B7  cmp  dword [esi + 0x3C], 0
00B7A7BB  jne  0xB7A7E7
00B7A7BD  push 4 / call 0xB74220        ; new(4)
00B7A7D5  mov  ecx, [esi + 4]           ; ★ 单例 +0x04 的"被包装对象"
00B7A7DB  call 0xB84540                 ; 新对象[0] = 该指针
00B7A7E4  mov  [esi + 0x3C], eax
00B7A7E7  mov  eax, [esi + 0x3C] / ret
```

同族懒句柄（同一模式，全部写 [sing+0xNN] = 4 字节对象 {[sing+4]}）：
0xB7A920 → [sing+0x48]、0xB7A800 → [sing+0x40]、0xB7A880/0xB7A900 等同族。

⇒ 门控实质上问的是：**"Demonware 网络核当前有一条已建立连接，且能给出 +0x3C 句柄"**。

---

## 4. TYPE2_OBJECT_VTABLE

```
TYPE2_OBJECT_VTABLE = 0x00D5A4F4        （CONFIRMED）
写入点：0x00BA2844  mov dword ptr [esi], 0xD5A4F4
（0x00BA282D 先写 0x00DB6AE4，随即被覆盖；属 ctor 内部临时 vtable）
```

旁证（**同一 rodata 页 0xD5Axxx 的字符串**，把该类钉在 Demonware 网络库上）：

```
0x00D5A4FC  "HMAC mismatch"          ← 与本 vtable 紧邻
0x00D5A50C  "HMAC calculation"
0x00D5A9CC  "stun.au.demonware.net"
0x00D5A9E4  "stun.jp.demonware.net"
0x00D5A9FC  "stun.eu.demonware.net"
0x00D5AE2A  "...DemonwarePortMapping..."
0x00DB4E94  "demonware"
0x00DC6610  "stun.us.demonware.net"
```

⇒ 0xD5A4F4 是 Demonware 网络核心（bdNet/bdTransport 层）的 transport 类 vtable。
  **类名未恢复**（dump 内 RTTI 完全剥离：_016_rtti.py 全镜像 0 条 type descriptor），
  因此本轮**不**给出类名字符串，只给 vtable 地址 + 结构 + 字符串旁证。

---

## 5. TYPE2_OBJECT_CONSTRUCTOR = 0x00BA2800（CONFIRMED）

```
分配者：0x00B81FC4（唯一调用点）
        push 0xAE8 → call 0xB74220     ; ★ 对象大小 0xAE8 = 2792 字节
唯一调用者：0xB81EF0（见 §6）
```

ctor 0x00BA2800 已确认的字段布局（节选，均为指令级）：

```
+0x000  dword  vtable = 0xD5A4F4                      0xBA2844
+0x004  dword  拥有者/被包装对象指针（ctor 清零，后由 §6 赋值）   0xBA2836
+0x008  0x88 字节 地址描述符（rep movsd 0x22）         0xBA284A call 0xB75340
+0x090  byte   参数[ebp+0x94]                          0xBA2861
+0x091  byte   参数[ebp+0x98]                          0xBA286D
+0x094  dword  参数[ebp+0x9C]                          0xBA2873
+0x098  dword  参数[ebp+0xA0]                          0xBA2879
+0x0C0  dword  0                                      0xBA28AF
+0x0C4  dword  socket fd / 连接句柄，初值 -1           0xBA28BF call 0xC738D0
+0x0C8  dword  原始 transport type，初值 0             0xBA28D4
+0x0CC  dword  = 网络核单例指针（参数[ebp+0x90]）       0xBA28DA
+0x0F0/+0x100/+0x110/+0x508  string/容器（0xB75DD0 初始化）
+0x510  0x28 字节子对象（call 0xC73000）                0xBA2920
+0x530  byte   0
+0x538  dword  地址块（后续被 0xBA4080 覆盖为 0x2C dwords）0xBA2938
+0x5E8  dword  状态整数，初值 0                         0xBA2962 区
```

### 5.1 连接子对象 [t+0xC4]（socket fd）

```asm
0x00C738D0  mov eax, ecx
0x00C738D2  mov dword [eax], 0xFFFFFFFF     ; fd = -1（未连接）
0x00C738D8  ret

0x00C738E0（setter）: eax = 0xC768D0(arg); [esi] = eax; return eax != -1
   被 0xBA29E6 / 0xBA3678 / 0xBAFDE3 调用（都在 transport 类内）
```

---

## 6. TYPE2_OBJECT_CREATE（完整创建链，CONFIRMED）

**唯一创建链**（每一跳都是唯一直调；已用 direct_callers 双向确认）：

```
0x7F3800   Demonware 连接状态机 step（返回 [0x84ABA7C]）
  │        （唯一调用者 0x7F276A）
  ├─ case 0 → 0x7F3890        ★ 唯一 transport 创建者
  │     0x7F38A4  call 0x803830            ; 网络核单例
  │     0x7F38B3  movzx eax, word [0x81A9780]   ; ★ 16-bit PORT（配置）
  │     0x7F38BB  push 0x0E3EC988               ; 地址格式串（值不可读）
  │     0x7F38C6  call 0xB75370                 ; 构造地址描述
  │     0x7F38CB  eax = [0x84ABB08]  ; 首选地址对象
  │     0x7F38D4  eax = [0x84ABB14]  ; 回退地址对象
  │     0x7F38DD  ecx = [0x84ABB0C]
  │     0x7F38E7/0x7F38F0  call 0xB983C0 / 0xB9A0E0（解析/引用）
  │     0x7F38FC  push 1 / push eax / sub esp,0x88 / 拷贝描述符
  │     0x7F3912  call 0xB82070
  │     0x7F3917  [0x84ABA7C] = (al != 0)
  │
  ├─ 0x7F3800 case（type 读回）
  │     0x7F3826  call 0xB838A0            ; 网络核消息泵（见 6.2）
  │     0x7F3838  call 0xB7A670
  │     0x7F3842  jmp [eax*4 + 0x7F3878]   ; 跳表：type 0..4
  │         type 2 → 0x7F385A  mov [0x84ABA7C], 2
  │     0x7F278E  push 0xDE0938 "DW_LOBBY_CONNECTED"   ★★★ 语义锚点
  │     0x7F2773  push 0xDE0928 "DW_LOBBY_ERROR"
  │
  └─ 0x7F276A 被 0x7F26C0 状态机调用；0x7F26C0 的其它 case 有
       "DW_DNS_ERROR"(0xDE08D8) / "DW_DNS_COMPLETE"(0xDE08E8) /
       "DW_ACCOUNT_ERROR"(0xDE08F8) / "DW_DUPLICATE_LOGIN"(0xDE0610) /
       "DW_ACCOUNT_LOGIN_COMPLETE"(0xDE090C)

0x7F3912 call 0xB82070
  └─ 0x7F3912 是 0xB82070 的**唯一**调用者
     0x00B820C5  mov byte [esi+0x4E8], 1
     0x00B820D3  call 0xB81EF0
     └─ 0xB81EF0 是 0xB82070 的唯一直调，且自己只被 0xB820D3 调用

0xB81EF0(sing, 0x88-描述符, addrObj, port, byte)
  0xB81F46  参数检验
  0xB81F52  if ([sing+0x4F4]) { 0xBA41B0(old); 0xB815E0(sing); }   ; 先销毁旧 transport
  0xB81F6B  [sing+0x5B0] = byte 参数
  0xB81F7C  lea edi,[sing+0x500]; ecx=0x2C; rep movsd                ; ★ 0xB0 字节地址块
  0xB81F7C  push 0xAE8 / call 0xB74220 / 0xBA2800(ctor)              ; 建 transport
  0xB81FD9  释放旧的 [sing+0x4F4]
  0xB81FFD  mov [sing+0x4F4], esi                                    ; ★ 挂载唯一 transport
  0xB8200B  call [0xCA8128]                                          ; 加引用
  0xB8201E  mov byte [sing+0x4F8], 0                                 ; ★ 清除"已连接"字节
  0xB82025  call 0xBA4080(t, &[sing+0x500])                          ; ★ 连接

0xBA4080(transport, &addrBlock)                                      ; 唯一调用者 0xB82025
  0xBA4098  push 8 / push [t+0x5F4] / call 0x6431B0 / call 0xB771A0
  0xBA40A0  mov dword [t+0xC8], 1      ; ★ 原始 type 先设 1（= 连接中）
  0xBA40AA  mov dword [t+0x5E8], 0
  0xBA40C0  rep movsd 0x2C ← addrBlock → [t+0x538]
  0xBA40DA  call 0xBA9970(&[t+0x538], 0, &out)
  0xBA40E7  call 0xBA0760(t, &out, 2)
  0xBA4106  lea eax,[t+8]; 拷贝 0x88 字节到栈
  0xBA411A  call 0xC73900(&[t+0xC4], &[t+8])     ; ★ 真正连接
  0xBA411F  cmp eax, 1
  0xBA4127  je  →  mov dword [t+0xC8], 2          ; ★ 原始 type = 2
  0xBA414B  cmp eax, -2 → 另一成功分支（0xBA4150）
  0xBA417B  否则 push 0x12 / call 0x4F7940 / call 0xBA3420 / 返回 0

0xC73900(connSub, addrStruct)                                        ; 唯一调用者 0xBA411A
  0xC73941  call 0x8534A0(&addrStruct) → call 0xB77010 → 地址对象
  0xC73952  call 0xB75440(&addrStruct) → AX = PORT（16-bit）
  0xC73957  edx = [connSub] = fd
  0xC7395D  sub esp,0x84 / rep movsd 0x21（拷贝地址对象）
  0xC7396D  call 0xC76920(fd, 地址对象, port)
  0xC73989  return connect 结果

0xC76920(fd, addr, port)  ——  __cdecl, ret 0x90
  0xC76947  mov eax, 2
  0xC7694D  mov word [ebp-0x14], ax        ; ★ sin_family = AF_INET = 2
  0xC76951  mov [ebp-0x10], ecx            ; ★ sin_addr = [addr+4]（4 字节，网络序）
  0xC76954  call [0xCA8550]                ; ★ htons
  0xC7695D  mov word [ebp-0x12], ax        ; ★ sin_port（网络序）
  0xC76961  push 0x10 / lea eax,[ebp-0x14] / push eax
  0xC76968  push [ebp+8]                   ; fd
  0xC76968  call [0xCA84F0]                ; ★★★ connect()
  0xC76970  jns 0xC76A04
  0xC76A09  mov eax, 1 / ret               ; ★ 成功返回 1
  0xC76976..0xC769F3  WSA 错误码映射 → 返回 -1/-2/-5/-6/-8/-9
```

### 6.1 socket 的创建（**TCP**，本轮决定性发现，CONFIRMED）

```asm
fd 创建：0x00C738E0 → 0x00C768D0
0x00C768D0  push 6      ; ★ IPPROTO_TCP
0x00C768D6  push 1      ; ★ SOCK_STREAM
0x00C768D9  push 2      ; ★ AF_INET
0x00C768DB  call [0xCA8548]          ; = socket()   ← 站点 0xC768DD
0x00C768E1  mov esi, eax
0x00C768EE  push &mode / push 0x8004667E / push esi / call [0xCA854C]   ; ioctlsocket(FIONBIO)
0x00C7690A  mov eax, esi / ret
```

⇒ **type-2 transport 的 socket 是 socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)。**
  路径上不存在任何 SOCK_DGRAM。CONFIRMED。

### 6.2 网络核消息泵 0xB838A0（与 type-2 标志的写入点）

```
0xB838A0..0xB83AEE：从 [sing+0x4F4] 轮询 transport
  0xB83951  call 0xBA47E0(transport, &kind, &)
  0xB83987  jmp [kind-1 * 4 + 0xB83AF0]      ; 5 路跳表
       kind 1 → 0xB839D5 → 0xB79CD0
       kind 2 → 0xB83A09 → 0xB82A90
       kind 3 → 0xB83A2F → 0xB761E0 → [sing+0x5B4]
       kind 4 → 0xB83A4B → 0xB769A0
                0xB83A76  [ [sing+4] + 0x50 ] = out[0]
                0xB83A82  [ [sing+4] + 0x54 ] = out[1]
                0xB83A88  mov byte [sing+0x4F8], 1     ; ★★ "已连接"字节置 1
       kind 5 → 0xB83997 → 0xB7A000
  0xB83A9A  循环回 0xB83951（直到 [sing+0x4F4]==0）
```

⇒ [sing+0x4F8] 由 **transport 上报的 kind==4 报文**置 1；
  0xBA4080（每次新建连接）把它清 0（0xB8201E）。
  [sing+4]+0x50/+0x54 被赋值 → 这是单例持有的"最近一次会话/端点对"（8 字节）。
  等级：`+0x50/+0x54 被写` = CONFIRMED；`语义` = CANDIDATE（8 字节，可能是 64-bit 会话 id）。

### 6.3 TYPE2_OBJECT_CREATE 汇总

```
TYPE2_OBJECT_CREATE = 0x7F3890
  → 0xB82070 → 0xB81EF0 → new(0xAE8) + 0xBA2800 (ctor)
  → 0xBA4080 → 0xC73900 → 0xC768D0 (socket TCP) / 0xC76920 (connect)
  → 原始 type [t+0xC8]: 0 → 1 (0xBA40A0) → 2 (0xBA4127)
  → 单例 [sing+0x4F4] = transport, [sing+0x4F8] = 0（由 6.2 再置 1）
```

---

## 7. TYPE2_OBJECT_REGISTRATION

| 注册项 | 载体 | 写入点 | 等级 |
|---|---|---|---|
| 全局网络核单例 | [0x08269774] | 0x803851（懒建）+ 0x80388F/0x8038A3（失败回滚） | CONFIRMED |
| 单例 vtable | 0xD599DC | 0xB82173 | CONFIRMED |
| 观察者/回调对象 | vtable 0xDE6814，4 字节 | 0x80387B 建，0x803881 注册（0xB7A640） | CONFIRMED |
| 观察者落点 | [sing+0x1610]，并转发给 transport [t+0xAE4] | 0xB7A646；0xBA0DE0（唯一调用者 0xB82041） | CONFIRMED |
| 字符串键映射表 | [sing+0x1BC]（0xB7FCD0 查表） | 0xB80FF0（要求 type2，建 0x18 字节条目） | CONFIRMED |
| 网络名字/标识全局 | [sing+0x4F0] = [0x0E39B6E8] | 0xB7A400（唯一调用者 0x803861） | CONFIRMED（值不可读） |
| 懒句柄族 | [sing+0x38/0x3C/0x40/0x48/...] = 4 字节 {[sing+4]} | 0xB7A770/0xB7A920/0xB7A800/... + 0xB84540 | CONFIRMED |
| 地址对象（全局） | [0x084ABB08]（首选）、[0x084ABB14]（回退）、[0x084ABB0C] | 写点 0x7F2BEA、0x7F2BF3、0x7F2C26、0x801A3C、0x801A46 | CONFIRMED（值不可读） |
| 连接状态全局 | [0x084ABA7C]（0/1/2） | 写 0x7F3849/0x7F385A/0x7F391E/0x7F3943 | CONFIRMED |
| DW 连接阶段全局 | [0x084ABA50]（1..5） | 0x7F26C0 状态机 | CONFIRMED |

0xDE6814 的 vtable 内容（4 字节适配器类）：

```
+0x000  0x00C77130     ; 方法
+0x004  0x008038B0     ; 析构（写 vtable 0xDE6808，可选 free）
```

⇒ 该观察者只有 2 个槽，属"最小通知对象"，与 015 §4.4 的 listener #4（[0x0849B60C]）
  同类（015 已证其 +0x24 为空实现）。**注意：这与 §3 / §7 的 type-2 门控无关，
  不要把它误当成第 8 个 listener**（任务 §一.2 的禁令继续有效）。

---

## 8. TYPE2_OBJECT_DOWNSTREAM

0xB7A770（取 [sing+0x3C]，强制 type==2）的全镜像调用者共 21 处，
其中一个就是本轮门控 0x62FE15。其余按模块列出（全部 CONFIRMED 调用点存在）：

| 调用点 | 语义 |
|---|---|
| 0x62F519 | matching：type2 + [sing+0x3C] + byte[[matching+0x1C]+1]!=0 + 0x7E8120(0x634240) |
| 0x62AD12 | matching：type2 + [sing+0x3C] + byte[matching+0x283]==0 |
| 0x6317DD | matching：0xB8EC00([sing+0x3C], …, [[matching+0x1C]+0x10], [+0x14], …) |
| 0x641E2F | 配置/登录模块：type2 → 0xB7AB60 → 0xB8A530 |
| 0x818E41 | 状态机模块：type2 → [sing+0x3C] → new(0x1C) 包装 |
| 0x818FD0 | 同上族 |
| 0x7F49D6 | **accepted 下游**（见 §12） |
| 0x7E7DAE/0x7E7E5B/0x7E7F0F/0x7E7FF9/0x7E8145/0x7E8266/0x7E8326/0x7E83F6/0x7F0B1E | UI/任务提交族 |
| 0x4AA7D2/0x4AAE46/0x4AAF07/0x4AAFB2/0x4AB062/0x4AB11C | 启动/引导族 |

⇒ 所有下游都是"**在已有连接上提交任务/读写状态**"，**没有任何一个是 socket 创建**。
  0xB7A770 使 type-2 成为这些功能的**前置条件**，而不是它们的目标。

0xB7A670（type 读取）另有约 200 处引用（015 §5 的 5 个 listener 也在其列，
但那是 +0x24 回调链，与本轴无关）。注意区分。

---

## 9. GAME_IP_STORAGE / GAME_PORT_STORAGE

### 9.1 type-2 transport 的地址（本轮新证，HIGH-CONFIDENCE）

```
地址描述符  = [transport + 0x08]，0x88 字节
              （ctor 复制，来源 = 0xB81EF0 的 0x88 参数 = 0x7F3890 构造的描述符）
IP          = [addrStruct + 0x04]，4 字节，**网络序**，直接进 sin_addr
              （0xC76951  mov [ebp-0x10], ecx  ← [ebp+0xC] = addrStruct+4）
PORT        = 由 0xB75440(&addrStruct) 取出的 16-bit，**HOST 序**，
              经 0xC76954 htons() 后写入 sin_port
```

### 9.2 全局配置里的 port / host（CONFIRMED 字段，值不可读）

```
[0x081A9780]  u16  PORT 字段
   写点    0x641A86 / 0x641B50 / 0x641B9F   mov word [0x81A9780], ax
            ax 来自 0xC3C234(<字符串>) = atoi
   类型    由 0x77EF77 声明为 "%hu"（INI 序列化器 0xC42052(fmt="%hu", [0x81A9780])）
   读点    0x7F38B3   movzx eax, word [0x81A9780]   ← 直接喂给 transport 连接
[0x081A7F34]  char[59] HOST 字段（"%59s"，写点 0x77EF64 / 0x641A62 / 0x641A92）
[0x081A76A8]  char[59] HOST 字段（"%59s"，写点 0x77EF8A / 0x641AD5 / 0x641B5E）
[0x081A9EB8] / [0x081A9EC0] / [0x081A9EC4]  同类端点字段
[0x00E51184]  dump 中存在字符串 "211.147.81.116"（CODOL 真实服 IP），
              被 0x641AF0 的拷贝循环写入
[0x0331CAF8]  4 字节 IP，由 0x6415C0 以 "%d.%d.%d.%d" 格式化  ← CANDIDATE
```

⚠ [0x081A9780] / [0x084ABB08] 等全局本体**落在 dump 覆盖范围之外**
（RVA > 0xA65000），只能看到读写指令，看不到值。因此
"[0x081A9780] 是否等于 3074"**无法静态判定**；但
012 的动态事实（唯一出站 TCP 为 127.0.0.2:3074）+ 本节 TCP + DW_LOBBY_CONNECTED
三者互洽 ⇒ [0x081A9780] = **Demonware Lobby 端口**（CANDIDATE，值未读）。

### 9.3 承接 015 的 socket 侧

```
CONFIRMED（015）: bdSocket 类 vtable 0xD8E3A8，对象 +0x06 = htons(port)（网络序）
                                                 +0x08 = inet_addr(ip)（网络序）
CANDIDATE（015）: session 侧 +0x18 = 4B IP，+0x1C = 2B port（HOST 序），读点 0x77DC69
本轮新增候选     : [sing+4]+0x50/+0x54（8 字节，由 transport kind-4 报文写入）
```

---

## 10. UDP_SOCKET_CREATE_POINTS（本轮用 IAT 全量枚举 + 分类）

全部 `call dword ptr [0xCA8548]`（= ws2_32 socket）站点，共 **9** 处：

| # | 站点 | push 参数 | 解释 | Battle |
|---|---|---|---|---|
| 1 | 0x77FC13 | 0x3E8, 2, 6 | socket(AF_IPX, SOCK_DGRAM, NSPROTO_IPX) | REFUTED（015） |
| 2 | 0xAD6D7F | edx, eax, ecx（动态） | 家族/类型运行期决定 | UNKNOWN |
| 3 | 0xBB18BB | 0x11, 2, 2 | socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP) | CANDIDATE（015） |
| 4 | 0xC653DE | 6, 1, 2 | socket(AF_INET, SOCK_STREAM, IPPROTO_TCP) → [obj+0x14]/[obj+0x18] | CANDIDATE（015，类 0xD8E3A8） |
| 5 | 0xC6541E | 0x11, 2, 2 | socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP) | CANDIDATE（015，类 0xD8E3A8） |
| 6 | **0xC768DD** | **6, 1, 2** | **socket(AF_INET, SOCK_STREAM, IPPROTO_TCP) = type-2 transport** | **REFUTED（本轮）** |
| 7 | 0xC7BAF8 | 0, 1, 2 | 裸 TCP helper | 非 Battle（helper） |
| 8 | 0xC7BB08 | 0, 2, 2 | 裸 UDP helper | 非 Battle（helper） |
| 9 | 0xC7BB1B | 0, eax, 1 | AF_UNIX 风格裸 helper | 非 Battle（helper） |

全部 `call dword ptr [0xCA84F0]`（= connect）站点，共 4 处：

```
0xAD6FC1   0xC6548C（类 0xD8E3A8 bind/connect 区）   0xC7696A（★ type-2）   0xC7BC62
```

⇒ **UDP socket 创建点仍然是 015 的 4 个（#2/#3/#5 + helper），本轮没有新增，
  也仍然没有任何一处能被证明接到 Battle endpoint。**
  type-2 路径明确走 #6（TCP），与全部 UDP 站点互斥。

---

## 11. TYPE2_TO_UDP_RELATION = REFUTED

```
证明（反向，指令级）：
 (1) type-2 的 fd 只能由 0xC738E0 → 0xC768D0 产生，而 0xC768D0 是
     push 6 / push 1 / push 2 = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)。
     ⇒ 不是 SOCK_DGRAM。
 (2) type-2 的"已连接"状态由 connect()（0xC7696A）返回 1 决定
     （0xC76A09 mov eax,1），连接语义 = 流式连接，不是无连接 UDP。
 (3) type-2 的创建链 0x7F3890 → 0xB82070 → 0xB81EF0 → 0xBA2800 → 0xBA4080
     → 0xC73900 → 0xC76920 中，**没有任何一跳**调用 #3/#5（0xBB18B0 / 0xC65410）
     或它们的工厂 0xC65D70。
 (4) 015 的 4 个 UDP 创建点的调用者链（0xA0542B / 0xA2F953 / 0x9FDC68 / 0xC73E60）
     与本链无交集。本轮复查 0xC73E60 所属类 vtable 0xD95538：
     装入点仅 0xC73E34（ctor）与 0xC740B2；ctor 0xC73E30 的调用者
     0xBAC43B / 0xBAD492 / 0xBAEE78 均在 transport 类的**非 lobby** 分支，
     不参与 0x7F3890 链。

⇒ TYPE2_TO_UDP_RELATION = REFUTED（CONFIRMED 级）
   反过来说：type-2 对象**本身就是一条 TCP 连接**，不可能是 28960/UDP 的载体。
```

---

## 12. ACCEPTED_TO_TYPE2_RELATION

```
存在数据流，但方向是"读"，不是"建"：

A) 门控读取（唯一、直接）
   0x63281E call [matching.vt+0x5C] = 0x62FDE0
     0x62FDFC → 0x803830 → 0xB7A670 → 0xBA0780 → [transport+0xC8]
   该读取发生在 accepted 分支内部，位于 listener 广播之前。

B) 下游使用（间接）
   0x632680 accepted → … → 0x629F80 → 0x7F49A0（调用点 0x629FBD）
     0x7F49C9 call 0x803830
     0x7F49D6 call 0xB7A670   ; 要求 == 2
     0x7F49E0 push 0xDAE091（= 空字符串字面量，byte[0xDAE091] == 0，已复核）
     0x7F49E7 call 0xB7A800   ; 取 [sing+0x40] 句柄
     0x7F4A1B cmp  byte [esi+0x225], 0
     0x7F4A3C call 0xB9AF00 / 0x7F4A45 call 0x7F5E40   ; 在 lobby 连接上提交任务
   ⇒ accepted 下游**消费**已有的 type-2（lobby）连接。

C) 反向（创建）不存在
   0x632680 → 0x629F80 的调用面内没有任何写入：
     [0x08269774] / [sing+0x4F4] / [sing+0x4F8] / [t+0xC8] / [0x084ABA7C] / [0x084ABA50]
   两个仅有的 transport 创建者 0x7F3890（唯一）与 0xB82070（唯一）
   都不在 accepted 的调用图内（调用者分别是 0x7F3800 与 0x7F3912）。

⇒ ACCEPTED_TO_TYPE2_RELATION = 单向（accepted ⇒ 读/用 type-2）
   accepted 不会创建 type-2；type-2 由 Demonware 连接状态机（0x7F3800/0x7F3890）
   在登录完成后独立建立。
```

### 12.1 由此解释 012 / 015 的动态观察（不自相矛盾）

```
mmbook accepted 报文**本身**是从 lobby 通道收到的
  ⇒ 送达时 [sing+0x4F4] 必然已存在且已连接
  ⇒ 0xB7A670(sing) 极可能 == 2（若 [sing+0x4F8] 已被 kind-4 报文置 1，
     或 [t+0x644] != 0）
  ⇒ 0x62FDE0 返回 1
  ⇒ 0x632822 jne 0x632864：**listener 广播与 [0x0849B61C]=1 被跳过**

这正好解释 015 §2 的现象（"广播不是无条件执行"），
也说明 015 的 "accepted → listener" 轴不仅被 7/7 REFUTED，
而且在真实运行中**大概率根本没有被执行**。
```

---

## 13. ACCEPTED_TO_BATTLE_PATH

```
0x00632680 accepted
  ├─ [this+0x288]=1 / [0x0849B61C]=1                （仅当 vt+0x5C 返回 0）
  ├─ vt+0x150 → vt+0x14C 序列化入队 [this+0x3A0B0]  （006/014 已证非 Battle 直连）
  ├─ vt+0x148 状态迁移
  ├─ vt+0x5C → 0x62FDE0 = TYPE2 GATE（§2/§3）
  │     ├─ =1 → 跳过 listener 广播（仅清理 0x655930）
  │     └─ =0 → listener +0x24 广播（015：7/7 NOT_BATTLE）
  ├─ 0x6293B0 由 reservation item 构造会话记录
  ├─ 0x629F80 → 0x7F49A0 → 0x803830/0xB7A670/0xB7A800
  │                              → 0xB9AF00 / 0x7F5E40（**lobby TCP** 任务提交）
  └─ 0x655930 清理

  × socket() / WSASocket() / sendto() / recvfrom() / DTLS / ECDH：无
  × 28960 常量消费点：无（承接 015 §12.6）
  × 写入 type-2 任何字段：无
```

⇒ accepted 分支的可达出口**全部**落在：UI flag / telemetry / 消息队列 / 会话记录 /
  **Demonware lobby TCP 连接的任务提交**。没有一条通向 Battle UDP。

---

## 14. BATTLE_TRIGGER_PATH 判定

```
BATTLE_TRIGGER_PATH = UNRESOLVED

LISTENER_PATH_CLOSED = YES（015，7/7 REFUTED，本轮未重开）
SENDERID_PATH_CLOSED = YES（013，未重查）
LOBBY_PATH_EXCLUDED  = YES（015 排除；本轮给出"为什么"：
                            0xB81EF0/0xBA4080 是 Demonware LOBBY TCP 连接的唯一创建者，
                            其状态字符串为 DW_LOBBY_CONNECTED）

重点：本轮新增关闭一条轴
TYPE2_OBJECT_PATH_TO_BATTLE = REFUTED
  type-2 network object = Demonware lobby TCP 连接（socket(2,1,6) + connect()）
  ⇒ 它既不是 Battle UDP，也不是 accepted → Battle 的中间桥梁。
```

### 14.1 本轮最终问题的直接回答

> **matching 中的 type-2 network object 到底是什么？**
>
> 它是全局 Demonware 网络核单例 [0x08269774]（vtable 0xD599DC，0x1618 字节）
> 当前挂载的 **transport 连接对象**（vtable 0xD5A4F4，0xAE8 字节）处于
> "已连接"状态时的归一化类型值。
> 该 transport 用 **socket(AF_INET, SOCK_STREAM, IPPROTO_TCP)** 创建 fd
> （0xC768D0），再用 **connect()**（0xC76920）连到 Demonware 服务端点；
> connect 成功 ⇒ [transport+0xC8] = 2 ⇒ 归一化 type = 2。
> 该状态机在 type==2 时打印 **"DW_LOBBY_CONNECTED"**（0x7F278E）
> ⇒ **type-2 = Demonware LOBBY 的 TCP 连接**。
>
> **它是否是 accepted → Battle UDP 的中间桥梁？**
>
> **不是。** TYPE2_TO_UDP_RELATION = REFUTED（§11），
> ACCEPTED_TO_TYPE2_RELATION = 单向读/用（§12）。
> 它与 28960/UDP 在 socket 层面互斥（TCP vs UDP），
> 且 accepted 分支不写它的任何字段。

---

## 15. 证据等级表

| 项 | 地址 | 等级 |
|---|---|---|
| matching vt+0x5C = 0x62FDE0 | 0xDC7274+0x5C | CONFIRMED |
| 0x62FDE0 完整语义（含两道前置守卫） | 0x62FDE0..0x62FE28 | CONFIRMED |
| 0x62FDE0 ABI：__thiscall / 无参 / 返回 bool | 同上 + 调用点 0x63281E | CONFIRMED |
| 网络核单例 [0x8269774]、大小 0x1618、vtable 0xD599DC | 0x803830..0x80388B、0xB82173 | CONFIRMED |
| 单例调用者规模（约 280） | direct_callers(0x803830) | CONFIRMED |
| 0xB7A670 归一化语义（4 字段） | 0xB7A670、0xBA0780 | CONFIRMED |
| 0xB7A770 = 懒建 [sing+0x3C] | 0xB7A770..0xB7A9A9 | CONFIRMED |
| transport vtable 0xD5A4F4 | 0xBA2844 | CONFIRMED |
| transport ctor 0xBA2800、大小 0xAE8 | 0xBA2800、0xB81FC4 | CONFIRMED |
| 唯一创建链 0x7F3890→0xB82070→0xB81EF0→0xBA4080 | 各自 direct_callers 均唯一 | CONFIRMED |
| socket(AF_INET, SOCK_STREAM, IPPROTO_TCP) | 0xC768D0（站点 0xC768DD） | CONFIRMED |
| connect(fd, ip, port) | 0xC76920（站点 0xC7696A） | CONFIRMED |
| connect 成功返回 1 ⇒ [t+0xC8]=2 | 0xC76A09、0xBA411F/0xBA4127 | CONFIRMED |
| type-2 ⟹ "DW_LOBBY_CONNECTED" | 0x7F3838..0x7F385A + 0x7F278E | CONFIRMED |
| [sing+0x4F8] 由 kind-4 报文置 1 | 0xB83A88 | CONFIRMED |
| 观察者对象 vtable 0xDE6814，落点 [sing+0x1610]/[t+0xAE4] | 0x80387B/0x803881/0xB7A646/0xBA0DE0 | CONFIRMED |
| 字符串键表 [sing+0x1BC] | 0xB80FF0→0xB7FCD0 | CONFIRMED |
| lobby 端口字段 [0x81A9780]（u16，"%hu"） | 写 0x641A86/0x641B50/0x641B9F；读 0x7F38B3 | CONFIRMED |
| lobby host 字段 [0x81A7F34]/[0x81A76A8]（"%59s"） | 写 0x641A62/0x641AD5；声明 0x77EF64/0x77EF8A | CONFIRMED |
| [0x81A9780] == 3074 | 全局不可读 | CANDIDATE（012 动态互洽） |
| [0x84ABB08]/[0x84ABB14]/[0x84ABB0C] = DW 地址对象 | 读 0x7F38CB..0x7F38E7；写 0x7F2BEA | CONFIRMED（值不可读） |
| [matching+0x1C] 参与门控 | 0x62FDE0、0x62F526、0x6317F5 | CONFIRMED |
| [matching+0x1C]+0x10/+0x14 语义 | 0x6317F5..0x631806 | CANDIDATE |
| [sing+4]+0x50/+0x54 = 8 字节会话/端点对 | 0xB83A76/0xB83A82 | CANDIDATE |
| transport 地址：IP @ [t+8]+4（网络序） | 0xC76951 | HIGH-CONFIDENCE |
| transport 地址：PORT @ 0xB75440(&[t+8])（主机序→htons） | 0xC73952/0xC76954 | HIGH-CONFIDENCE |
| [0x331CAF8] = 4B IP（"%d.%d.%d.%d"） | 0x6415C0 | CANDIDATE |
| UDP socket 创建点 | 0xBB18B0/0xC65410/0xC7BB00/0xAD6D7F | CONFIRMED（存在）；归属 Battle = UNRESOLVED |
| type-2 路径上存在 UDP | — | **REFUTED** |
| accepted → 创建 type-2 | — | **REFUTED** |
| accepted → 读/用 type-2 | 0x63281E、0x629FBD | CONFIRMED |
| dump 内 RTTI 可用 | 全镜像 0 条 type descriptor | REFUTED |
| _015_glob.py 的 or eax,<全局> 结果 | 系统性 1 字节回溯假阳性 | REFUTED（§1.1） |

---

## 16. NEXT_GATE

```
1. 【已关闭，本轮新增】type-2 轴：
   type-2 = Demonware lobby TCP 连接 ⇒ 与 Battle UDP 无关。
   ⇒ 不要再去 0x62FDE0 / 0xB7A670 / 0xBA0780 / 0x7F3890 / 0xB81EF0 / 0xBA4080
     找 Battle。也不要再去 [matching+4] 找第 8 个 listener。

2. accepted → Battle 的缺口**不在 Demonware 网络核内**，剩三条独立轴：
   a) 【会话/端点轴】[matching+0x1C]（+0x10/+0x14 成对字段）与
      0x6293B0 / 0x629F80 的非 lobby 出口；
      以及 0x77DC69（BD_NULL ip:port，+0x18/+0x1C）是否被 IW-engine 消费。
   b) 【IW-engine UDP 轴】015 §12.2 的类 0xD8E3A8（0xC65D70 工厂 /
      0xC65410 UDP / 0xC653D0 TCP）向上调用者：
      0xA0542B（→ 0xC65220 bdSocket::connect）、0xA2F953（→ 0xC65340）、
      0x9FDC68（→ 0xC65190）。目标：接到 matching 或会话对象。
   c) 【未分类 socket】0xAD6D7F（家族运行期决定）与 0xC7BB1B（AF 参数化）。
      这两处 015/016 都未归属任何模块，是仅存的"家族未知"socket 站点。

3. 下一轮建议**转动态**（任务 §15 的 Hard Stop 要求）：
      PVE-BATTLE-UDP-DYNAMIC-016
   目标仅一个：确认客户端在 PvE matchmaking 全过程是否**创建过任何** UDP socket
   （AF_INET/SOCK_DGRAM）以及其目标端口。
   若动态证明"从不创建 UDP socket"，则 Battle 侧必须由服务端/其它进程发起，
   应改查服务端与 28960 的绑定与握手（battle_server.py 之外的真实链路）。

4. 静态留待的动态不可替代项：
   - [0x081A9780]（端口）、[0x084ABB08]/[0x084ABB14]（地址对象）、
     [0x08269774]（网络核）本体值；
   - 0x0E39B6E8 / 0x0E3EC988（超出 dump 的字符串/全局）。
```

---

## 17. 纪律核对

```
STATIC ONLY                        = 是（未运行游戏、未发包、未启动任何服务）
client 修改 / server 修改           = 无
senderId 修改 / booking response 修改 = 无
SessionId 修改 / Battle endpoint 修改 = 无
28960 修改 / 手工 UDP / 手工 DTLS    = 无
hook / patch / ACE-TenProtect bypass = 无
重新研究已关闭路线                   = 无
  （listener 仅在区分"观察者注册"与"type-2 门控"时引用，未重走；
    senderId / Lobby socket 未重查）
新增文件：仅 DEV-BOOKING\CLIENT-BOOKING-BATTLE-OBJECT-016.md
         与 DEV-BOOKING\scripts\_016_rtti.py、_016_dispr.py（只读分析脚本）
附件地址全部为只读读取
```

---

## 18. 本轮新增工具（只读，供接力）

```
DEV-BOOKING\scripts\_016_rtti.py   全镜像 RTTI type descriptor 枚举/过滤
                                   （结论：0 条 → 本 dump 已剥离 RTTI）
DEV-BOOKING\scripts\_016_dispr.py  resync 反汇编 + [reg+disp] 范围过滤
                                   用法: python _016_dispr.py <lo> <hi> <disp,disp,...> [--w]
                                   （--w 的写判定为"首操作数为内存"，请以指令文本复核）
复用（015）：_015_lib.py / _015_dis2.py / _015_hex.py / _015_glob.py / _015_str.py
             _015_glob.py 的 1 字节回溯假阳性见 §1.1，务必用 _015_dis2.py 复核
```
