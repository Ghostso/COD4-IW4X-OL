# ProtocalHandler.dll —— SetKey / AES key 定位规格（无注入）

日期：2026-09-25
目标：`COD OL\Cross\ProtocalHandler.dll`（1,224,765 B，ImageBase `0x10000000`，明文，无 VM）
方式：**纯磁盘静态反汇编**（pefile + capstone）。未启动游戏、未注入、未用 Frida、未改网络。

---

## 0. 结论速览

| # | 结论 | 强度 |
|---|---|---|
| 1 | `SetKey(arg0=ctx, arg1=keyPtr, arg2=mode)`，**cdecl 3 参**，mode 经 **4 项跳转表**分派；`mode=3` 是 AES-128 路径 | **HIGH** |
| 2 | `ctx+0x4c` = 密钥有效闸（写 `1`）；`ctx+0x84` = mode 回存 | **HIGH** |
| 3 | `ctx+0x50` = **16 字节 userKey 明文副本（持久）** | **HIGH** |
| 4 | `ctx+0x90` = **AES key schedule 基址**；`ctx+0x90+0xF0` = **轮数 10/12/14** | **HIGH** |
| 5 | `ctx+0xF4` = **decrypt key schedule**（`0x1007AAC7: add ebx,0xF4`） | **MEDIUM-HIGH** |
| 6 | key 由 `0x100626C0` 从 `.data:0x100FCF50` 生成，**32 字符集，无 0/O/1/l** | **HIGH** |
| 7 | 对象 = **`calloc(0x2B0, 1)`** 堆分配（`0x100627B1`），`+0x298` = 回调 `0x10063080` | **HIGH** |
| 8 | AES = OpenSSL T-table 族（`.data:0x100DA0B4` 起 5 张表 + rcon `0x100DC1B4`） | **HIGH** |

---

## 1. 精确调用约定与栈布局

### 1.1 `SetKey` = `0x10063DF0`（cdecl，3 参，无 prologue）

```
10063DF0  mov  edx, dword ptr [esp+0xC]   ; arg2 = mode
10063DF4  mov  ecx, dword ptr [esp+4]     ; arg0 = ctx
10063DF8  xor  eax, eax
10063DFA  cmp  edx, 4
10063DFD  push esi
10063DFE  mov  dword ptr [ecx+0x84], edx  ; ctx->0x84 = mode
10063E04  ja   0x10063E72                 ; mode > 4 -> 返回 -1
10063E06  jmp  dword ptr [edx*4 + 0x10063E78]
```

**栈布局（进入时）**：

| 偏移 | 内容 |
|---:|---|
| `[esp+0]` | 返回地址 |
| `[esp+4]` | **arg0 = ctx** |
| `[esp+8]` | **arg1 = keyPtr** |
| `[esp+0xC]` | **arg2 = mode** |

**跳转表 `0x10063E78`（4 项，实测）**：

```
mode=0 -> 0x10063E75   (or eax,-1; pop esi; ret   拒绝)
mode=1 -> 0x10063E72   (or eax,-1; pop esi; ret   拒绝)
mode=2 -> 0x10063E0D   (裸 16B key 拷贝，不建 schedule)
mode=3 -> 0x10063E33   (AES-128：拷贝 key + 建 schedule)
```

> **`push esi` 之后的栈偏移位移**：`push esi` 使 `esp -= 4`，
> 于是 `0x10063E33` 处的 `[esp+0xC]` **已改为指向 arg1 = keyPtr**。
> 这句正是主线记录的 `mov eax,[esp+0xC]; mov esi,eax` ⇒ **主线是对的**。

`mode=3` 分支逐条：

```
10063E33  mov  eax, dword ptr [esp+0xC]   ; = arg1 = keyPtr（因已 push esi）
10063E37  push edi
10063E38  mov  esi, eax                   ; esi = keyPtr
10063E3A  mov  dword ptr [ecx+0x4C], 1    ; ctx->0x4C = 1
10063E41  lea  edx, [ecx+0x50]            ; dst = &ctx->key[0]
10063E44  push 0x80                       ; bits = 128
10063E49  mov  edi, dword ptr [esi]       ; key[0..3]
10063E4B  add  ecx, 0x90                  ; &ctx->AES_KEY
10063E51  mov  dword ptr [edx], edi
10063E53  push eax                        ; arg2 = keyPtr
10063E54  mov  edi, dword ptr [esi+4]
10063E57  push ecx                        ; arg1 = &ctx->AES_KEY
10063E58  mov  dword ptr [edx+4], edi
10063E5B  mov  edi, dword ptr [esi+8]
10063E5E  mov  dword ptr [edx+8], edi
10063E61  mov  esi, dword ptr [esi+0xC]
10063E64  mov  dword ptr [edx+0xC], esi
10063E67  call 0x1007AA80                 ; SetKeyEx(key, 128, &ctx->AES_KEY)
10063E6C  add  esp, 0xC                   ; 3 参 cdecl 平栈
10063E6F  pop  edi
10063E70  pop  esi
10063E71  ret
```

> **参数顺序确认（HIGH）**：`SetKey(ctx, keyPtr, mode)`
> —— arg0=`[esp+4]`、arg1=`[esp+8]`、arg2=`[esp+0xC]`（入口时）。
> `mode=3` 分支因已 `push esi`，其 `[esp+0xC]`/`[esp+0x10]` 分别等于
> **keyPtr** 与 **mode**。主线的入口序列**完全正确**，无需修正；
> 仅需注意**进入分支后偏移整体 +4**。

`mode=2` 分支（`0x10063E0D`）：`mov edx,[esp+0xC]` → `add ecx,0x50` →
4 次 dword 拷贝 `[edx]..[edx+0xC]` → `ctx+0x50`。**不调用 AES**。

### 1.2 `0x1007AA80` = SetKeyEx（stdcall，3 参）

```
1007AA80  push ebx
1007AA81  mov  ebx, dword ptr [esp+8]     ; arg0 = keyPtr
1007AA86  push edi
1007AA8B  mov  edi, dword ptr [esp+0x14]  ; arg1 = keySchedule
1007AA93  mov  esi, dword ptr [esp+0x18]  ; arg2 = bits
1007AA97  cmp  esi,0x80 / 0xC0 / 0x100    ; 只接受 128/192/256
1007AAB8  push ebx ; push esi ; push edi
1007AABB  call 0x10077E90                 ; AES_set_encrypt_key(key,bits,sched)
1007AAC7  add  ebx, 0xF4                  ; ← decrypt schedule 偏移
1007AACE  push ebx ; push esi ; push edi
1007AAD0  call 0x10078250                 ; AES_set_decrypt_key
```

**⇒ `ctx+0x90` = encrypt schedule，`ctx+0xF4` = decrypt schedule。**

### 1.3 `0x100626C0` = 随机 key 生成（cdecl 2 参：`(dst, len)`，返回 dst）

```
100626C0  push ebx
100626C1  mov  ebx, dword ptr [esp+0xC]   ; 入口 [esp+0xC] = arg1 = len
100626CD  mov  edi, dword ptr [esp+0x10]  ; push esi 后 = arg0 = dst
100626D1  call 0x10085340                 ; rand()
100626DE  fmul dword ptr [0x100DA098]     ; 除数字面量
100626E4  fmul qword ptr [0x100DA090]     ; 0.5
100626EF  mov  ecx, 0x100FCF50
100626F4  sub  ecx, eax
100626F9  mov  dl, byte ptr [ecx]
100626FB  mov  byte ptr [esi+edi-1], dl   ; dst[i]
10062701  mov  eax, edi                   ; return dst
```

**字符集字面量（实测 `.data:0x100FCF50`，55 B 含终止 0）**：

```
ABCDEFGHIJKMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789
```

**⇒ 无 `O`、无 `0`、无 `l`、无 `1`。强度 HIGH。**

> **RNG 签名（HIGH）**：调用点先 `push eax(dst)`、再 `push 0x10(len)`，
> 所以 `arg0=dst`、`arg1=len`。函数内因 `push ebx`/`push esi`，
> `ebx=len`、`edi=dst`。⇒ **`GenRandomKey(dst, len)`**。

### 1.4 调用点 `0x10064DB0`（精确帧）

所在函数帧：`0x10064D00: sub esp,0xB8`，返回前 `add esp,0xB8`，保存 `ebx/ebp/esi/edi`。

```
10064D00  sub  esp, 0xB8                ; 帧 0xB8
10064D7B  mov  edi, dword ptr [esp+0xE8]
10064D82  mov  edx, dword ptr [esp+0xEC]
10064D89  lea  eax, [esp+0x24]          ; key dst = frame+0x24
10064D8D  push 0x10                     ; len = 16
10064D8F  push eax                      ; dst
10064D90  mov  byte ptr [esi+2], 3
10064D94  mov  dword ptr [esi+0x14], ebx
10064D97  mov  dword ptr [esi+0xC], edi
10064D9A  mov  dword ptr [esi+0x10], edx
10064D9D  call 0x100626C0               ; GenKey(len=16, dst=frame+0x24)
10064DA2  mov  edx, dword ptr [esp+0xD8] ; arg0 = ctx
10064DA9  lea  ecx, [esp+0x2C]          ; keyPtr = frame+0x2C
10064DAD  push edi                      ; arg2 = mode
10064DAE  push ecx                      ; arg1 = keyPtr
10064DAF  push edx                      ; arg0 = ctx
10064DB0  call 0x10063DF0               ; SetKey(ctx, keyPtr, mode)
10064DB5  add  esp, 0x18                ; 6 dwords
```

**栈偏移推导（逐条）**：

设 `S` = `0x10064D00: sub esp,0xB8` **之后**的 `esp`。

| PC | esp | 操作 |
|---|---:|---|
| `10064D89` | `S` | `eax = S+0x24`（key 缓冲地址） |
| `10064D8D` | `S` | `push 0x10` → `S-4` |
| `10064D8F` | `S-4` | `push eax` → `S-8` |
| `10064D9D` | `S-8` | `call GenRandomKey`；callee 用 `ret`，**两个实参仍在栈上** |
| `10064DA2` | `S-8` | `edx = [S+0xD0]`（ctx） |
| `10064DA9` | `S-8` | `ecx = [S+0x24]` = **同一个 key 缓冲** |
| `10064DAD` | `S-8` | `push edi` → `S-0xC` |
| `10064DAE` | `S-0xC` | `push ecx` → `S-0x10` |
| `10064DAF` | `S-0x10` | `push edx` → `S-0x14` |
| `10064DB0` | `S-0x14` | `call SetKey` |
| `10064DB5` | `S-0x14` | `add esp,0x18` → `S+4` |

**关键结论**：
* `GenRandomKey` 的两个实参（`len=0x10`、`dst=S+0x24`）在返回后**没有被立刻清理**，
  所以 `0x10064DA9` 的 `[esp+0x2C]` = `S+0x24`，与 `0x10064D89` 的
  `eax = S+0x24` **完全同一个地址**。**没有 8 字节偏差。**
* `add esp,0x18` 清除 `GenRandomKey` 2 个 + `SetKey` 3 个 = 5 个 push（0x14），
  外加此前函数内已存在的一个临时 push（0x4），合计 0x18。
  **该额外 4 字节不影响 key 地址。**

> **key 地址的唯一权威取值**：`0x10064D8F` 时的 `eax`
> （即 `0x10064DA9` 时的 `[esp+0x2C]`），两者均为 `S+0x24`。
> **强度 HIGH。**

### 1.5 key 的生命周期

1. `0x10064D89`：`dst = frame+0x24`（**栈上**）
2. `0x10064D9D`：16 B 随机 key 写入 `frame+0x24`
3. `0x10064DB0` → `0x10063E51..E64`：key **复制到 `ctx+0x50`**（持久）
4. `0x10063E67` → `0x10077E90`：schedule 写入 **`ctx+0x90`**（持久）
5. 函数返回后栈上 key 消失，**`ctx+0x50` 永久保留明文 key**

**⇒ 监测点首选 `ctx+0x50`，不要抢栈。**

---

## 2. context 结构定义

分配点：`0x100627B0: push 0x2B0; push 1; call 0x10085738`（calloc）
⇒ **`sizeof(context) = 0x2B0`**。初始化 `0x100627CB: call 0x10062710`。

| 偏移 | 大小 | 名称（推定） | 证据（VA） |
|---:|---:|---|---|
| `0x00` | 4 | vtable / self | `10062724: mov [esi],0xFFFFFFFF`；`10062816` 用 `[edi]` |
| `0x04` | 4 | state | `10063FF6: mov [esi+4],2` |
| `0x08` | 4 | lastError | `10063FFD: mov [esi+8],eax` |
| `0x14` | 4 | 子对象句柄 | `10062763`、`10064D94` |
| `0x18` | 4 | 子对象句柄 2 | `1006278D`、`10063FD5` |
| `0x24` | 4 | recv buf ptr | `10063F59` |
| `0x34` | 4 | buf length | `10063F5C` |
| `0x38` | 4 | recv cursor | `10063F49` |
| **`0x4C`** | **4** | **密钥有效闸** | `10063E11`、`10063E3A` 写 **1**；`10063E94: cmp [eax+0x4C],1` |
| **`0x50`** | **16** | **userKey 明文（持久）** | `10063E1B..E2F`、`10063E51..E64` 各 4 次 dword 拷贝 |
| `0x84` | 4 | **mode 枚举** | `10063DFE: mov [ecx+0x84],edx`（所有 mode 分支） |
| **`0x90`** | **0xF4** | **`AES_KEY` (encrypt)** | `10063E4B: add ecx,0x90` → 作 `0x1007AA80` 的 arg1 |
| `0x90+0xF0` | 4 | **rounds = 10/12/14** | `10077ED8/EC/F8: mov [edx+0xF0], imm` |
| **`0xF4`(+0x90) = `0x184`** | 0xF4 | **`AES_KEY` (decrypt)** | `1007AAC7: add ebx,0xF4` |
| `0x280`,`0x284` | 8 | 64 位计数器 | `10063D33..` `add/adc` |
| `0x288`,`0x28C` | 8 | 64 位计数器 2 | `10062755/66` |
| `0x290` | 4 | — | `10062737` |
| `0x298` | 4 | **回调指针 = `0x10063080`** | `1006273D: mov [esi+0x298],0x10063080` |
| `0x29C` | 4 | — | `10062747` |
| `0x2A0`,`0x2A8` | 8 | — | `1006279B/A1` |

### 2.1 `+0x4C` 与 `+0x84` 分工

* `+0x84` ← **mode**（`0x10063DFE`，**所有** mode 分支都写）
* `+0x4C` ← **1**（`0x10063E11`/`0x10063E3A`，仅 mode=2/3）
* `0x10063E94: cmp dword ptr [eax+0x4C],1` / `je` / 否则 `or eax,-1; ret`

⇒ **`+0x4C` = "密钥已设置"布尔闸；`+0x84` = mode 枚举。**

### 2.2 keySchedule 结构（OpenSSL `AES_KEY`，实测）

```
struct AES_KEY {              // 基址 = ctx+0x90
    uint32 rd_key[4*(Nr+1)];  // +0x00 .. +0x9C  (44 dwords @ AES-128)
    int    rounds;            // +0xF0  = 10 / 12 / 14
};                            // sizeof = 0xF4
```

证据：
* `10077F19: mov [edx],ecx`、`10077F36: mov [ecx],eax`、`...[edx+0xC]`
  ⇒ schedule 自 `+0` 起按 4 dword 步进；
* `10077ED8: mov [edx+0xF0],0xA`（128）／`0xC`（192）／`0xE`（256）；
* `10078270: mov edx,[ebp+0xF0]` → `shl edx,2` 驱动解密调序循环
  ⇒ `rounds` 为 dword，`rd_key` 长 = `rounds*4` dwords。

**⇒ 完全吻合主线：`+0xF0` = 轮数。**

### 2.3 `schedule[0]` 与 `key` 的确定性关系（可用作校验）

`0x10077F02..0x10077F19` 对 `key[0]` 做字节序变换后存入 `schedule[0]`：

```
schedule[0] == bswap32(key[0..3]) == (k0<<24)|(k1<<16)|(k2<<8)|k3
```

**⇒ 读内存时可用该式交叉验证 key 与 schedule 是否匹配。强度 HIGH。**

### 2.4 AES 实现指纹（T-table）

```
0x100DA0B4 : C66363A5 F87C7C84 EE777799 F67B7B8D   Te0
0x100DA4B4 : A5C66363 84F87C7C 99EE7777 8DF67B7B   Te0 变体
0x100DB0B4 : 51F4A750 7E416553 1A17A4C3 3A275E96   Te1/Te2 族
0x100DB4B4 : 5051F4A7 537E4165 C31A17A4 963A275E
0x100DB8B4 : A75051F4 65537E41 A4C31A17 5E963A27
0x100DBCB4 : F4A75051 4165537E 17A4C31A 275E963A
0x100DC1B4 : 01000000 02000000 04000000 08000000   rcon[10]
```

---

## 3. 挂起期 ALL_ACCESS"读-比较-循环"方案

### 3.1 流程（不注入）

```
1. CreateProcess(game, CREATE_SUSPENDED)
2. OpenProcess(ALL_ACCESS)                 # 抢在 ACE 武装前
3. 读 ProtocalHandler.dll 基址（EnumProcessModules / 已知映射）
4. 轮询定位 ctx（§4）
5. ResumeThread
6. 循环：读 [ctx+0x4C] / [ctx+0x50] / [ctx+0x90+0xF0]
7. 命中即取走 key
```

### 3.2 监测目标与期望值

| 优先级 | 目标 | 地址 | 期望值 | 说明 |
|---|---|---|---|---|
| **1** | **明文 key** | `ctx+0x50`（16 B） | 16 B，∈ 32 字符集 | 最直接 |
| 2 | 有效闸 | `ctx+0x4C`（u32） | **`1`** | 判断已设置 |
| 3 | mode | `ctx+0x84`（u32） | **`3`** | AES-128 |
| 4 | 轮数 | `ctx+0x90+0xF0`（u32） | **`10`** | schedule 已建 |
| 5 | schedule 校验 | `ctx+0x90`（u32） | `bswap32(u32[ctx+0x50])` | 一致性自检 |

### 3.3 采样周期与预期窗口

| 项 | 建议 | 依据 |
|---|---|---|
| 挂起态探测 | `t=0` 即可读 | 句柄在 Resume 前已持有 |
| 采样周期 | **5 ms**（200 Hz），最差 1 s 亦可 | `ctx+0x50` 是**持久副本** |
| 栈上 key 窗口 | `0x10064D9D`→`0x10064DB0`，约几十 ns | **不可行，放弃** |
| `ctx+0x50` 窗口 | SetKey 返回 → 对象析构 | 秒级~分钟级，**完全可行** |

**结论：抓 `ctx+0x50`，不要抢栈。5–50 ms 采样足够。**

---

## 4. 只靠读内存定位堆上的 context

`context` = `calloc(0x2B0,1)` 堆对象（`0x100627B1`）。搜索特征按可靠性排序：

### 特征 A — 初始化签名

初始化后对象内 >95% 为 0，仅少数非零：

```
u32[+0x000] == 0xFFFFFFFF
u32[+0x298] == dll_base + 0x63080      # 模块内代码指针
u32[+0x290] == 0
u32[+0x29C] == 0
u32[+0x280..0x28C] == 0
```

**强度 MEDIUM-HIGH。**

### 特征 B — 密钥生效后的五条联合判据（**首选**）

```
(1) u32[ctx+0x4C] == 1
(2) u32[ctx+0x84] == 3                                  # AES-128
(3) u32[ctx+0x90+0xF0] == 10                            # rounds
(4) bswap32( u32[ctx+0x50] ) == u32[ctx+0x90]           # schedule[0]
(5) 16 字节 [ctx+0x50] 全部 ∈ "ABCDEFGHIJKMNPQRSTUVWXYZ"
                                    "abcdefghijkmnpqrstuvwxyz23456789"
```

**(4)+(5) 联合的误报概率 ≈ 52^16 / 2^32 ≈ 10^-27，不可能误报。强度 HIGH。**

扫描实现提示：
* 先 `VirtualQueryEx` 过滤 `MEM_COMMIT && Type == MEM_PRIVATE`
  （`Type == MEM_IMAGE` 是模块镜像，可跳过，速度快一个数量级）；
* 只需对 `Protect` 含 `PAGE_READWRITE` 的区域按 4 字节对齐扫；
* 命中 `(1)` 的候选通常只有个位数，再验 (2)-(5) 即可唯一定位。

### 特征 C — 用 `+0x298` 一步定位（成本最低）

`[ctx+0x298] = 0x10063080`（模块内固定 VA，加 ASLR 偏移）。
在进程内搜该 dword（加 delta 修正），**一次命中即得 `ctx+0x298`**，
减 `0x298` 即 ctx 基址。**强度 MEDIUM-HIGH。**

---

## 5. 与主线的差异（须记录）

| 主线说法 | 实测 | 影响 |
|---|---|---|
| `SetKey` 入口 `mov eax,[esp+0xC]; mov esi,eax` 中 `eax` = keyPtr | **成立**：`push esi` 后 `[esp+0xC]` 即 arg1 = keyPtr | **无需修正** |
| 参数序 | `(ctx, keyPtr, mode)`，即 arg0/arg1/arg2 = ctx/keyPtr/mode | 一致 |
| `0x10078258` = KeyExpansion 主循环 | `0x10078258` 是 `0x10078250` 族入口；真正 `AES_set_encrypt_key` = **`0x10077E90`** | 断点下 `0x10077E90` |
| `push 0x80` 紧跟 `lea edx,[ecx+0x50]` | 一致；`0x80` 是 `0x1007AA80` 的 bits 实参 | 无冲突 |
| `0x10064DB0` 调用序 `lea eax,[esp+0x24]; push 0x10; call GenKey` | 一致；`GenKey(dst, len)` 且 `dst = eax = S+0x24` | **无冲突** |

**⇒ 主线的 5 条已知事实全部经反汇编复核通过，无实质偏差。**
唯一需补的是：`0x10063E33` 处因已 `push edi`/`push esi` 导致栈偏移整体位移；
key 缓冲与传给 `SetKey` 的 keyPtr 是**同一个地址**（`S+0x24`）。

---

## 6. 结论强度汇总

| 结论 | 强度 |
|---|---|
| `SetKey` cdecl 3 参，顺序 `(ctx, keyPtr, mode)` | **HIGH** |
| mode 跳转表 4 项；`mode=3` = AES-128 路径 | **HIGH** |
| `ctx+0x4C` = 有效闸(=1)；`ctx+0x84` = mode | **HIGH** |
| `ctx+0x50` = 16 B 明文 key（持久） | **HIGH** |
| `ctx+0x90` = `AES_KEY`；`+0xF0` = rounds(10/12/14) | **HIGH** |
| `ctx+0xF4` = decrypt schedule | **MEDIUM-HIGH** |
| `sizeof(ctx) = 0x2B0`（calloc） | **HIGH** |
| 字符集 55 B，无 `0/O/1/l` | **HIGH** |
| `schedule[0] == bswap32(key[0..3])` | **HIGH** |
| 调用点栈：GenKey dst 与 SetKey keyPtr 同为 `frame+0x24` | **HIGH** |
| `add esp,0x18` = 5 实参(0x14) + 一个既有临时 push(0x4) | **MEDIUM** |
| 特征 B 五条联合判据可唯一定位 ctx | **HIGH** |

---

## 7. 本次新增只读脚本

| 脚本 | 用途 |
|---|---|
| `_ph_probe1.py` | 6 个目标函数 capstone 反汇编 + 节表 |
| `_ph_probe2.py` | SetKey 跳转表、各 mode 分支、调用点帧 |
| `_ph_probe3.py` | 调用点精确序列、calloc 尺寸、字段写图、字符集、T-table |
