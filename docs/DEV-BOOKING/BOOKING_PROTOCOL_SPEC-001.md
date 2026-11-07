# BOOKING_PROTOCOL_SPEC-001（静态规格，第二阶段）

> 本文**只写有反汇编证据的结论**。无证据一律 `UNKNOWN`。
> **未修改 Server / Golden / patch / KDF hook**。

```
分析源   image_best.bin（运行期镜像 VA 0x400000..0xE65000，10,899,456 B，已解壳）
方法     反汇编 + 数据引用图 + vtable 归属回溯
纪律     不发送任何猜测性 Booking response
```

---

## 0. P0 结论：accepted handler 不是被 call 的，而是挂在 vtable 上

### 0.1 穷举结果（CONFIRMED）

```
0x632680 的直接 call rel32        = 无
0x632680 的 dword 引用（vtable 槽）= 2 处：0x00DC73B0 / 0x00DC7850
```

### 0.2 精确虚调用点（CONFIRMED）

用"寄存器同源"约束（`mov reg,[obj+disp]` 紧跟 `call 同寄存器`）全镜像扫描：

```
[accepted] 0x0091B19C  mov edx,[eax+0x140]  ->  0x0091B1A3  call edx
[timedout] 0x00632FC4  mov edx,[eax+0x13C]  ->  0x00632FCD  call edx （同模块内自调用）
其余 6 条 +0x13C 命中属别的结构体（偏移巧合），已过滤
```

### 0.3 但 0x91B19C **不是**响应分发（重要澄清）

```asm
0091B190  push ebp / mov ebp,esp / sub esp,8
0091B198  mov  esi, ecx
0091B19A  mov  eax,[esi]              ; eax = vtable
0091B19C  mov  edx,[eax+0x140]
0091B1A2  push edi                    ; 仅 1 个 push（对齐用）
0091B1A3  call edx                    ; ★ 无 5 个栈参数
0091B1A5  test al, 0xf                ; ★ 立即用返回值
```

而真解析器 `0x632680` 是 `ret 0x14`（**5 个栈参数**）。

**⇒ 签名不匹配，`0x91B19C` 调用的不是我们的解析器** —— 它属于另一个对象。

### 0.4 真正的对象（CONFIRMED）

回溯 vtable 起点 `0x00DC7270`，**唯一**引用点 = `0x0062C025`，
即**匹配对象的构造函数 `0x62C000`**：

```asm
0062C000  push ebp / mov ebp,esp
0062C005  mov  ebx,[ebp+8]             ; ebx = this
0062C00C  mov  dword [ebx+4], edi      ; 清零
0062C01E  push 1
0062C020  lea  ecx,[ebx+0x20]
0062C023  mov  dword [ebx], 0xDC7274   ; ★ 安装 vtable
0062C02C  call 0x806B50
0062C033  lea  ecx,[ebx+0x258]
0062C039  call 0xB94940
0062C041  mov  byte [ebx+0x281], al
0062C04D  mov  word [ebx+0x278], di     ; ★ 解析器检查的守卫
0062C061  mov  byte [ebx+0x280], 0
```

---

## 1. 对象构造链（CONFIRMED）

`0x62C000` 被 4 处调用，其中两处是"容器构造"：

```asm
00638210  push ebp / mov ebp,esp
00638225  mov dword [ebx+0x10], 0xDC7D4C
00638230  mov dword [ebx],      0xDC73DC    ; 容器 vtable #1
00638236  mov dword [ebx+0x10], 0xDC7474    ; 容器 vtable #2（多继承）
0063823D  call 0x62C000                      ; ★ 构造子对象
00638242  mov dword [esi], 0xDC7714
00638254  mov dword [edi], 0xDC787C
```

```asm
00638370  mov eax, 0x3A134                   ; ★ 对象大小 = 0x3A134
0063837B  call 0xC43280
00638398  call edx
006383A1  call 0x62C000
```

容器 ctor 的唯一调用者 = `0x639D3D`（CONFIRMED）。

### 对象布局（CONFIRMED，取自 ctor 写偏移）

```
this+0x0000  vtable 指针（表 @0xDC7270）
this+0x0278  word      守卫（解析器要求 != 0）
this+0x0280  byte
this+0x0281  byte
this+0x0282  dword
this+0x3A048 dword     字段A
this+0x3A04C dword     字段B
this+0x3A050 byte[64]  定长缓冲
this+0x3A090 子对象
this+0x3A098 dword     计数
this+0x3A09C dword     计数上限
this+0x3A0A8 dword*    数组指针
对象总大小 = 0x3A134
```

> `0x3A048 < 0x3A134` —— 字段A/B 是该大对象的**尾部成员**。

---

## 2. 谁给字段A/字段B 赋值（P2 结论）

### 2.1 全镜像写入点扫描（CONFIRMED）

```
disp=0x3A048 命中 8 处，逐条判定：
   0062C282  CLEAR_WRITE（ctor 路径）
   0062F6C5  CLEAR_WRITE  mov [esi+0x3A048], eax   (eax=0)
   0062F717  CLEAR_WRITE  mov [esi+0x3A048], ebx   (ebx=0)
   0062F809  READ         mov ecx,[esi+0x3A048]   ← mmbook 发送前读
   006326BB  READ         （accepted 解析器比对）
   006328F7  CLEAR_WRITE  mov [esi+0x3A048], edi   (edi=0，拒绝路径)
   00632FBE  READ         （timeout 路径）
   0062F73D  未对齐命中，非指令

disp=0x3A04C 同理：全部 CLEAR_WRITE 或 READ
```

### 2.2 结论

```
A_SOURCE = CLEAR_ONLY_IN_THIS_IMAGE
B_SOURCE = 同上
⇒ 本镜像内**没有任何指令**把非零值写进 [this+0x3A048]
⇒ REAL_VALUE_WRITE 发生在本镜像之外

EXTERNAL_MODULE_WRITE = UNKNOWN（不假设具体模块）
```

> `0x62F7F9/0x62F809` 证明**发送时读**这两个字段并由 `[edx+0x150]` 外发。
> 若发送时它们就是 0，则响应回显 0 即可通过比对 —— **CANDIDATE**，
> 必须靠运行期观测证实。

---

## 3. Reservation array（P5）

```
[this+0xE360]  dword  当前预约索引
stride = 0x238
item+0x00 = 字段A
item+0x04 = 字段B
数组基址 = this+0x75D8
```

### 已知访问点（CONFIRMED）

| 地址 | 指令 | 说明 |
|---|---|---|
| `0x6326AA` | `cmp [esi+0xE360], edi` / `jl` | 索引 < 0 → 拒绝 |
| `0x6326EF` | `mov eax,[esi+0xE360]` | 取索引 |
| `0x6326F5` | `imul eax,eax,0x238` | 算偏移 |
| `0x6326FB` | `mov edx,[eax+esi+0x75D8]` | 读 item+0x00 |
| `0x632707` | `mov eax,[eax+esi+0x75DC]` | 读 item+0x04 |

### 未找到（UNKNOWN）

```
① 对 this+0x75D8 的初始化/写入        —— 未找到
② [this+0xE360] 的写入点              —— 未找到
③ 数组容量/边界检查                    —— 未找到

RESERVATION_ARRAY_SOURCE = UNKNOWN
（findSessions / playlist=10 / 6/14 request / server response
  四条**都无法证实，也都未被证伪**）
```

> 按要求：**不把 reservation array 简单当作 room ID**。
> 现有证据只支持"stride=0x238 的数组，项内两个 dword 与 A/B 比对"。

---

## 4. Response channel（P3）

```
accepted handler 的调用方式 = 虚调用（非直接 call）   CONFIRMED
直接虚调用点 0x91B19C       = 签名不匹配               REFUTED 作为响应入口
vtable 唯一构造点 0x62C000  = 匹配对象 ctor            CONFIRMED
容器 ctor 0x638210/0x638370                            CONFIRMED
容器 ctor 唯一调用者 0x639D3D                          CONFIRMED
```

### 仍未定位（UNKNOWN）

```
① 谁遍历 vtable 并调用 +0x140
   全镜像"寄存器同源 mov+call"只找到 0x91B19C（已证伪）
   ⇒ 调用点可能在：另一模块（Base.dll / TenProxy）、
      成员函数指针表遍历（mov reg,[table+idx*4]; call reg）、
      或运行期才解密的分发器
② 通道类型（TCP/UDP/IPC/共享内存）                 UNKNOWN
③ 是否经过 0x85 push / DedicatedControl / bridge    UNKNOWN
```

**RESPONSE_CHANNEL = UNKNOWN**（已排除"直接 call"与"0x91B19C"两种可能）

---

## 5. 本阶段验收表（P7）

| 环节 | 状态 | 证据 |
|---|---|---|
| `6/14` request 构造 | **CONFIRMED** | `0x62F7E0`：`"%s %d %s %d"` + `"mmbook"` |
| request 内层信封 | **CONFIRMED** | 实测帧 = 裸 u32 长度 + 文本 |
| A/B 随 request 外发 | **CONFIRMED** | `0x62F7F9/0x62F809` 读后 push，`call [edx+0x150]` |
| A/B 赋值来源 | **UNKNOWN**（本镜像仅清零） | 全量写入点扫描 |
| response channel | **UNKNOWN** | 唯一 +0x140 虚调用点签名不符 |
| response parser | **CONFIRMED** | `0x632680`，`ret 0x14` |
| `"mmbook accepted"` 判定 | **CONFIRMED** | `push 0xF` + `push 0xDC69B0` + `call 0xC3C678` |
| A/B 校验 | **CONFIRMED** | `0x6326B9` / `0x6326C8` |
| reservation 校验 | **CONFIRMED**（判定）/ **UNKNOWN**（数据来源） | `0x6326F5` imul 0x238 |
| booking success 副作用 | **CONFIRMED** | `0x632745` `mov [esp+0x28],1` |
| 失败路径 | **CONFIRMED** | `0x632876` → `0x62F6C0` 复位 |
| Battle/28960 关联 | **UNKNOWN** | 未找到任何字段携带 28960 |

---

## 6. 下一步唯一最短路径（仍纯静态）

```
① 找"函数指针表遍历"分发器：
   搜 mov reg,[base+idx*4+disp] ; call reg 的循环，base 落在 0xDC7270 附近
② 检查 Base.dll（60 MB）是否含同 offset 0x140 的分发
   —— 本镜像只是 exe；响应可能由 Base.dll 处理
③ 定位 [this+0x278] 置非零处 —— 那是"预约流程真正开始"的信号，
   其调用者极可能是 response channel
④ 定位 this+0x75D8（reservation array 基址）与 [this+0xE360] 的写入
⑤ 全部确认后才写实现方案；本阶段不动 Server
```

### 明确拒绝的猜测

```
✗ "response = echo(A,B)"        —— 未证实（发送时 A/B 可能为 0）
✗ "booking response 携带 28960" —— 未找到任何字段
✗ "通道 = 0x85 push"            —— 未证实
✗ "通道 = DedicatedControl"     —— 未证实
```
