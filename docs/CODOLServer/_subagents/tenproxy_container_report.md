# TenProxy.dll TCLS 标签容器 —— 完整逆向裁定报告（子代理 A2）

日期：2026-09-26　工作目录：`D:\BaiduNetdiskDownload\使命召唤OL`

目标：
* 消费者 `COD OL\TenProxy.dll`（ImageBase `0x10000000`，SHA256 `A5EE7EDE762C473F58A87B214213097F6DDA8950AC537B0A959389AEF31348CB`）
* 生产者 `WeGame\tcls\tcls_core.exe`（SHA256 `BB48629EBE7CDA9CE8EF20298D45B10DB2A5959946B61AFB3C28DCBAA37B7EAE`）

方法约束（全程遵守）：纯静态分析。未运行游戏，未创建任何内核映射，
未挂钩/调试/注入，未修改目标文件，未执行 `netsh`/路由/DNS/防火墙/网卡命令，
未使用 `sc`，未删除文件，未下载安装。所有脚本纯 ASCII。

---

## 0. 裁定摘要（先给结论）

**Kuhn 的布局在关键位置是错的，这就是"游戏读出来全是 0"的直接原因。**

| # | Kuhn 假设 | 实测真值 | 证据 |
|---|---|---|---|
| E1 | 通道表指针在 `mapped+0x4C`（tag 0x13） | 在 **`mapped+0x50`**（tag 0x14） | `0x10006392 mov ecx,[eax+0x4C]` 中 `eax = [this+0x18C8] = mapped+4` |
| E2 | 通道子表项是"相对子表的偏移" | 通道子表项是**相对映射基址的绝对偏移** | `0x100082B7` 取项；`0x100082C7 add eax,[ebp-0x18]`；`eax=[this+0x18C4]=mapped base` |
| E3 | 通道读取基址是 `mapped + off` | **是** `[this+0x18CC] = mapped + dword[mapped+0x50]` | `0x1000639B add edx,[ebp-0x10A4]` |

另外两处 Kuhn 未写错、但表述不够精确，本报告予以厘清：

* `mapped+0x000` 的值 `0x40` **不是"版本号"**。消费者只做无符号 `>= 0x40` 判定
  (`0x100062F4`)；生产者写它同时用于"每通道槽容量 = 0x40"
  (`tcls_core 0x407DCA mov [edi+0x14],0x40`)。
* `slot+0x2C` 家族（`0x10008140` / `0x10008250` / `0x100083B0`）读的是
  `[this+0x18CC]` 即**通道基址**，不是 `[this+0x18C8]`。它们只用于通道内 tag。

---

## 1. 调用链与对象布局（复核）

### 1.1 `Invoke` 的 0x566 分支

```asm
0x10001D8E  817d0866050000      cmp dword ptr [ebp+8], 0x566
0x10001D95  7546                jne 0x10001DDD
0x10001D97  68e4180000          push 0x18E4
0x10001D9C  e83db30000          call 0x1000D0DE          ; operator new(0x18E4)
0x10001DA4  8945ec              mov [ebp-0x14], eax
0x10001DB4  8b4dec              mov ecx, [ebp-0x14]
0x10001DB7  e8e6f5ffff          call 0x100013A2          ; -> 0x10005510
0x10001DD5  8b4d0c              mov ecx, [ebp+0xC]
0x10001DDB  8911                mov [ecx], edx            ; *out = object
```

`0x100013A2` 是导入跳转桩，真身即 `0x10005510`：

```asm
0x100013A2  e969410000          jmp 0x10005510
```

### 1.2 构造函数 `0x10005510`

```asm
0x10005559  mov dword ptr [eax], 0x100205D0       ; primary vtable
0x10005562  mov dword ptr [ecx+4], 0x100205A0     ; secondary
0x1000563B  mov dword ptr [ecx+0x18C4], 0         ; mapped base  = NULL
0x10005648  mov dword ptr [edx+0x18C8], 0         ; tag table   = NULL
0x10005655  mov dword ptr [eax+0x18CC], 0         ; channel base= NULL
0x10005662  mov dword ptr [ecx+0x18D0], 0         ; header dword
0x1000566F  mov dword ptr [edx+0x18D4], 0xFFFFFFFF; mapping handle
0x10005696  mov dword ptr [edx+0x18E0], 0         ; initialized flag
```

### 1.3 主 vtable `0x100205D0`

| 槽 | 目标 VA | 语义 |
|---|---|---|
| +0x00 | 0x10006BD0 | 析构/清理族 |
| +0x04 | 0x10005E40 | `Initialize` |
| +0x08 | 0x100075F0 | — |
| +0x0C | 0x10007980 | — |
| +0x10 | 0x10007A60 | — |
| +0x14 | 0x10007AB0 | — |
| +0x18 | 0x10007B00 | — |
| +0x1C | 0x10006B20 | — |
| +0x20 | 0x10007CA0 | — |
| **+0x24** | **0x10007DA0** | **`GetDWORD(tag, out)`** |
| **+0x28** | **0x10007EA0** | **`GetBytes(tag, out, lenptr)`** |
| **+0x2C** | **0x10008140** | **表索引 `GetBlock`** |
| **+0x30** | **0x10008250** | **通道 `ChanGetBlock`** |
| +0x34 | 0x100083B0 | 通道 `ChanGetBlock` 变体 |
| **+0x38** | **0x10008510** | **通道 `ChanGetDWORD`** |

`+0x30` 与 `+0x34` 是同一算法的两份拷贝，可视为
`ChanGetBytes` / `ChanGetBytesWide`。

---

## 2. 读取算法（VA 级）

### 2.1 `GetDWORD` @ `0x10007DA0`

```asm
0x10007DB6  cmp dword ptr [eax+0x18C8], 0     ; tag table 非空？
0x10007DBD  je  0x10007E39
0x10007DC2  cmp dword ptr [ecx+0x18C4], 0     ; mapped base 非空？
0x10007DC9  je  0x10007E39
0x10007DCB  cmp dword ptr [ebp+0xC], 0        ; out 非空？
0x10007DCF  je  0x10007E39
0x10007DD4  mov eax, [edx+0x18C8]             ; eax = mapped + 4
0x10007DDD  mov ecx, [ebp+8]                  ; ecx = tag
0x10007DE3  mov eax, [edx+ecx*4-4]            ; ★ table[tag-1]
0x10007DED  mov edx, [ecx+0x18C4]             ; mapped base
0x10007DF3  add edx, [ebp-0x10]               ; entry = mapped + off
0x10007DFC  mov ecx, [eax]                    ; len = entry[0]
0x10007E01  cmp dword ptr [ebp-0x18], 4       ; ★ 长度必须恰好 == 4
0x10007E05  jne 0x10007E1D                    ; 否则不写 out、返回 0
0x10007E11  add edx, [ebp-0x18]               ; entry + 4
0x10007E17  mov ecx, [edx]
0x10007E19  mov [eax], ecx                    ; *out = payload dword
0x10007E59  mov eax, [ebp-8]                  ; 返回值 = 成功标志
```

索引基址是 `[this+0x18C8] = mapped + 4`，索引式 `[base + tag*4 - 4]`
即 **1-based**。`tag` 无上界检查；条目头是 `DWORD len`，必须恰好 `== 4`。

### 2.2 `GetBytes` @ `0x10007EA0`

```asm
0x10007EB6  cmp dword ptr [eax+0x18C8], 0
0x10007ED3  cmp dword ptr [ebp+0x10], 0       ; lenptr 非空？
0x10007EEF  mov eax, [edx+ecx*4-4]            ; table[tag-1]，1-based
0x10007EFF  add edx, [ebp-0x10]               ; entry = mapped + off
0x10007F08  mov ecx, [eax]                    ; len = entry[0]
0x10007F0D  cmp dword ptr [ebp+0xC], 0        ; out == NULL ?
0x10007F11  jne 0x10007F27
0x10007F19  mov [edx], eax                    ; 仅回填 *lenptr = len，返回 1
0x10007F27  ...
0x10007F33  call 0x1000D108                   ; MSVCRT!memset(out,0,*lenptr)
0x10007F40  cmp edx, [ebp-0x18]               ; *lenptr 与 len 取较小
0x10007F4F  n = min(*lenptr, len)
0x10007F64  call 0x1000D15C                   ; MSVCRT!memcpy(out,entry+4,n)
0x10007F6C  mov [ebp-8], 1
```

`out==NULL` 时退化为"只取长度"。没有对 `tag`、`entry off` 做容器边界检查。

### 2.3 `Initialize` 的指针落点

```asm
0x100062E3  mov edx, [ebp-0xC8C]              ; mapped view
0x100062E9  mov eax, [edx]                    ; ★ mapped+0x00
0x100062EB  mov [ecx+0x18D0], eax
0x100062F4  cmp dword ptr [ecx+0x18D0], 0x40  ; ★ 无符号 >= 0x40 才继续
0x100062FB  jae 0x10006326
0x1000631D  mov dword ptr [ebp-0x34], 0       ; 失败标志

0x1000635E  cmp dword ptr [ebp-0x34], 0
0x10006362  je  0x1000682C                    ; 失败则跳过全部 tag 读取
0x10006371  mov [ecx+0x18C4], edx             ; ★ mapped base
0x1000637D  add eax, 4
0x10006383  mov [ecx+0x18C8], eax             ; ★ mapped + 4
0x1000638C  mov eax, [edx+0x18C8]             ; = mapped + 4
0x10006392  mov ecx, [eax+0x4C]               ; ★★ 读写位置 = mapped + 0x50
0x1000639B  mov edx, [ebp-0xC8C]              ; mapped
0x100063A1  add edx, [ebp-0x10A4]             ; mapped + 该 DWORD
0x100063AA  mov [eax+0x18CC], edx             ; ★ 通道基址
```

**Kuhn 的第一个硬错**：`eax = mapped + 4`，于是 `[eax+0x4C]` 落在
`mapped + 0x50`，对应标签槽 `tag = 1 + (0x50-4)/4 = 0x14`。

### 2.4 校验、魔数、版本

只有三条"会不会拒绝"的判定：

1. `mapped+0x00 >= 0x40`（无符号，`0x100062F4`）。
2. 三个指针非空（`0x10007DB6` / `0x10007DC2` / `0x10007DCB` 等）。
3. 条目 `len == 4` 才会写 DWORD 输出（`0x10007E01`）。

**没有魔数、没有 CRC、没有版本字符串比较、没有签名校验。**

---

## 3. 通道子表（二级结构）

### 3.1 `ChanGetDWORD` @ `0x10008510`（槽 +0x38）

```asm
0x10008558  mov edx, dword ptr [ecx+0x4C]     ; ecx = [this+0x18CC]
0x1000855E  mov ecx, [eax+0x18C4]             ; mapped base
0x10008567  add ecx, [ebp-0x10]               ; sub = mapped + dword[p_channel+0x4C]
0x1000856D  mov edx, [ebp+0x10]               ; channel
0x10008573  mov ecx, [eax+edx*4-4]            ; ★ channel 1-based
0x10008583  add eax, [ebp-0x18]               ; entry = mapped + off
0x1000858C  mov eax, [edx+ecx*4-4]            ; ★ tag 1-based
0x100085A8  mov ecx, dword ptr [eax]          ; len
0x100085AD  cmp dword ptr [ebp-0x28], 4       ; 长度必须 == 4
```

`0x10008250` / `0x100083B0` 是同一算法（`0x10008299 8b514c` 起）。

### 3.2 索引式

```text
p_channel    = [this+0x18CC] = mapped + dword[mapped+0x50]
sub_off      = dword[p_channel + 4*(channel-1)]
entry_off    = dword[mapped + sub_off + 4*(tag-1)]
entry        = mapped + entry_off
entry+0x00   = DWORD len (DWORD 读要求 len == 4)
entry+0x04   = payload
```

**子表项是绝对偏移**：`0x100082C7 add eax,[ebp-0x18]` 中
`eax` 已经来自 `[this+0x18C4]`，也就是映射基址。

### 3.3 tag 0x12 / 0x13 的真实语义

游戏侧 `ApplySettings`：

```asm
0x0064182F  push eax              ; &channel
0x00641830  push 0x12
0x00641832  call [edx+0x24]       ; GetDWORD(tag=0x12)
0x0064185A  push edx              ; channel
0x0064185B  push 0x331CAF8
0x00641860  push 5
0x00641862  call [eax+0x38]       ; ChanGetDWORD(channel, 5)
```

* **tag 0x12 = 通道号（1-based）**。
* **tag 0x13 没有特殊语义**。固定位置的通道表指针实际在 **tag 0x14**。

---

## 4. 生产者交叉验证（`tcls_core.exe`）

`sub_407980` 拼名字 → `sub_407D10`：

```asm
0x00407D5E  push 0x80000                    ; size = 512 KiB
0x00407D81  call [KERNEL32!CreateFileMappingW]
0x00407D9A  call [KERNEL32!MapViewOfFile]   ; FILE_MAP_ALL_ACCESS 0xF001F
0x00407DCA  mov  dword ptr [edi+0x14], 0x40 ; ★ 槽容量 = 0x40
0x00407DD3  mov  dword ptr [eax], 0x40      ; ★ mapped+0x00 = 0x40
0x00407DDB  mov  ecx, [edi]                 ; mapped
0x00407DDD  add  ecx, 4
0x00407DE0  mov  [edi+4], ecx               ; table  = mapped + 4
0x00407DE3  add  ecx, 0x100                 ; + 0x40*4
0x00407DE9  mov  [edi+8], ecx               ; next   = mapped + 0x104
0x00407DEC  mov  [edi+0xC], ecx             ; cursor = mapped + 0x104
```

生产者侧的槽写入（`0x00408060` / `0x004080B0`）：

```asm
0x00408063  mov eax, [ebp+8]                ; tag
0x00408068  cmp eax, 1 / jl  skip           ; ★ tag 下界 = 1
0x0040806D  cmp eax, [edx+0x14] / jg skip   ; ★ tag 上界 = 槽容量
0x00408088  mov [esi+eax*4-4], ecx          ; table[tag-1] = 相对映射基址偏移
0x00408093  mov dword ptr [ecx], 4          ; ★ 条目头 len = 4
0x00408099  mov [ecx+4], eax                ; payload = DWORD
0x0040809C  add dword ptr [edx+0xC], 8      ; 游标 += 8
```

游标复位（`0x00407FF0`）与偏移计算（`0x00407F60`）：

```asm
0x00407FF5  mov edx, [eax+0xC]              ; cursor
0x00408005  lea ecx, [edx+ecx*4]            ; base = cursor
0x00408008  mov [eax+0xC], ecx              ; cursor = base + 4*n
0x00408049  mov eax, [p_table + tag*4 - 4]  ; table[tag-1]
0x0040804D  sub ecx, [edx]                  ; 相对映射基址
```

**生产者的槽语义与消费者的读取算法完全一致**，并证实：

* `mapped+0x00` = 槽容量（消费者只当"必须 >= 0x40"）；
* `table[tag-1]` = 相对映射基址的偏移，`tag` 属 `[1, 0x40]`；
* 条目 = `[DWORD len][payload]`，DWORD 载荷恰好 4 字节。

---

## 5. 对 Kuhn 假设的裁定

Kuhn 的 `_tcls_shm_layout.py` 生成的是：

```text
table[0x12-1] = 普通条目偏移（把 tag 0x12 当条目）
table[0x13-1] = chan_off        （把通道表指针放在 tag 0x13 / mapped+0x4C）
chan = mapped[chan_off]         （把第一项当"相对子表偏移"）
```

在真实读取代码下：

1. `Initialize` 读 `mapped+0x50`（Kuhn 只写到 `mapped+0x4C`）→ 读到 **0**
   → `p_channel = mapped + 0 = mapped`，后续把映射头当通道表。
2. 即使 `0x50` 非 0，Kuhn 的通道项被当"相对子表偏移"，
   而真值是"相对映射基址的绝对偏移"。
3. `GetDWORD(0x12)` 在 Kuhn 布局下**能拿到 1**，所以问题不在通道号，
   而在通道表指针位置与子表偏移语义。

用 `_tp_verify.py` 模拟两种布局（真实指令语义）：

```text
== Kuhn model ==
  mapped+0x050 = 0x0        -> channel table base = 0x0
  GetDWORD(0x12) = 1
  chan GetBytes(8) len=64  '\x00'*64        <-- 垃圾
  chan GetDWORD(7) = 0     match8=False     <-- ApplySettings 直接 reject

== Corrected model ==
  mapped+0x050 = 0x104      -> channel table base = 0x104
  GetDWORD(0x12) = 1
  chan GetBytes(8) len=23  '127.0.0.1;443;1004;0;0\x00'
  chan GetDWORD(7) = 23    match8=True      <-- 通过 0x64191E 长度校验
```

**修正的布局（正确）**：

```text
mapped+0x000  DWORD      槽容量 N (生产者写 0x40，消费者要求 N >= 0x40)
mapped+0x004  DWORD[64]  表：table[tag-1] = 条目偏移（相对映射基址）
mapped+0x104             条目区起点
entry+0x000   DWORD      载荷字节长度
entry+0x004   bytes      载荷

通道：
  mapped+0x050 (tag 0x14 槽)  DWORD  通道表偏移
  ch_base = mapped + 该偏移
  dword[ch_base + 4*(channel-1)]                子表偏移（绝对）
  dword[mapped + 子表偏移 + 4*(tag-1)]          条目偏移（绝对）
```

---

## 6. 最小可被接受的映射（byte 级规格）

名字 `TCLS_SHAREDMEMEMORY` + 十进制游戏 PID（没有 `+`，没有下划线）；
大小 `0x80000`；保护 `PAGE_READWRITE`；视图 `FILE_MAP_ALL_ACCESS (0x000F001F)`。

### 6.1 固定头

| 偏移 | 宽度 | 值 | 说明 |
|---|---|---|---|
| `0x000` | 4 | `0x00000040` | 槽容量；`Initialize` 要求 `>= 0x40` |
| `0x004` | `0x100` | 64 个 DWORD | `table[tag-1] = 条目偏移`（相对映射基址） |
| `0x104` | — | — | 条目区惯例起点 |

### 6.2 强制标签（缺一即失败）

| 标签 | 读法 | 槽偏移 | 载荷 | 作用 |
|---|---|---|---|---|
| `0x12` | `GetDWORD` | `0x004+4*(0x12-1)=0x048` | 通道号，≥1 | `0x64182F` 选通道 |
| `0x14` | 裸读 `DWORD` | `0x004+4*(0x14-1)=0x050` | 通道表偏移 | `Initialize` 建立通道基址 |

### 6.3 通道表与子表

| 位置 | 值 |
|---|---|
| `mapped + dword[0x050] + 4*(channel-1)` | 子表偏移（绝对） |
| `mapped + 子表偏移 + 4*(tag-1)` | 条目偏移（绝对） |

通道内必需的三个标签：

| 通道标签 | 槽偏移 | 载荷 |
|---|---|---|
| `0x05` | `sub+0x10` | `DWORD`（写进 `block+0x538`） |
| `0x07` | `sub+0x18` | `DWORD` = `len(tag8 载荷)`，**必须严格相等** |
| `0x08` | `sub+0x1C` | ASCII 字段串，`;` 或 `:` 分隔，字段数 ∈ {9,7,5} |

`0x08` 推荐 5 段 `HOST;PORT;f3;f4;f5`，末尾 `\0` 计入长度。
`0x64191E` 逐字节比较 `GetDWORD(0x07)` 与 `GetBytes(0x08)` 的长度。

### 6.4 让 `Initialize` 累积成功（推荐）

`Initialize` 用 `ebp-0x34` 串联每个 tag 的成败，第一个失败之后
后续 tag 全被跳过、`[this+0x18E0]` 保持 0。建议按序全部自洽：

| 顺序 | 标签 | 槽 | 载荷 | 条目长度 |
|---|---|---|---|---|
| 1 | `0x0F` | `+0x2C` | TCLS 窗口名（UTF-16，可空串） | 实际字节数 |
| 2 | `0x02` | `+0x24` | `DWORD` | `4` |
| 3 | `0x06` | `+0x24` | `DWORD` | `4` |
| 4 | `0x03` | `+0x28` | 1 字节，`> 0` | `1` |
| 5 | `0x04` | `+0x28` | GameSignature，≤ `0x80` | 实际字节数 |
| 6 | `0x05` | `+0x28` | LoginKey，≤ `0x10` | 实际字节数 |
| 7 | `0x1A` | `+0x28` | 1 字节，`> 0` | `1` |
| 8 | `0x1B` | `+0x28` | JumpSignature，≤ `0x70` | 实际字节数 |
| 9 | `0x10` | `+0x2C` | ≤ `0x28` 字节，**会被 `wcslen` 当宽串** | 实际字节数 |
| 10 | `0x0E` | `+0x2C` | ≤ `0x410` 字节 | 实际字节数 |

> 第 9 条注意：`0x100067B9 call wcslen` 把 `0x10` 载荷当宽字符串，
> 载荷内必须有 `\0\0` 终止，否则越界读。建议写 `b"\x00\x00"`。

### 6.5 供 `ApplySettings`（`0x641600`）使用的标签

```asm
0x00641642  call [eax+0x24]   ; GetDWORD(tag=1) -> 必须返回 1
0x00641661  push 0x16         ; GetBytes(0x16, block+0x04, &block+0x14)
0x00641694  push 0x18         ; GetBytes(0x18, block+0x18, &block+0x98) 预置 0x80
0x006416C4  push 0x19         ; GetBytes(0x19, block+0x9C, &block+0xAC) 预置 0x10
0x0064173F  push 7            ; GetBytes(7, NULL, &block+0x4B0) 取长度
0x00641787  push 7            ; GetBytes(7, block+0x0B0, &block+0x4B0)
0x006417B1  push 0x1B         ; GetBytes(0x1B, NULL, &block+0x534) 取长度
0x006417F9  push 0x1B         ; GetBytes(0x1B, block+0x4B4, &block+0x534)
0x00641830  push 0x12         ; GetDWORD(0x12) 通道号
0x00641862  call [eax+0x38]   ; ChanGetDWORD(channel, 5)
0x00641896  call [edx+0x38]   ; ChanGetDWORD(channel, 7)
0x006418F8  call [edx+0x30]   ; ChanGetBytes(channel, 8)
0x0064191E  cmp tag7, tag8len ; ★ 不等 -> [0x331C5C0] = 0
0x00641BC8  mov [0x331C5C0], eax
```

因此 `[0x331C5C0] != 0` 的最小集合是：
`0x01`、`0x12`、`0x14`、`0x16`、`0x18`、`0x19`、`0x1B`、`0x07`，
加通道 `0x05` / `0x07` / `0x08`。

### 6.6 生成脚本

```text
python _tenproxy_build.py --host 127.0.0.1 --port 443 ^
       --out _tenproxy_shm.bin --json _tenproxy_shm.json
```

产物 `_tenproxy_shm.bin`（`0x80000` 字节，97 字节非 0，
SHA256 `9A6F8ED4B771FD0C65915979F01E89070A9D0EAF83711FFF91F69BBDDC12CFA6`）。
关键结构地址由脚本每次重算并打印在 `_tenproxy_shm.json`：

```text
slot_capacity@0x000 = 64
table_slot_tag_0x13@0x04C = 0      (Kuhn 会写这里，消费者不读)
channel_ptr@0x050   = 0x104        (★ 消费者真正读的位置)
channel_table       = 0x104
channel0_subtable   = 0x108
sub_entry_tag5      = 0x454
sub_entry_tag7      = 0x44C
sub_entry_tag8      = 0x430
tag8_len            = 23
tag8_text           = "127.0.0.1;443;1004;0;0\0"
```

实测字节（`Format-Hex` 片段）：

```text
+0x050  04 01 00 00              ; 通道表偏移 0x104（高 16 位为 0）
+0x104  08 01 00 00              ; 通道表[0] = 子表偏移 0x108
+0x108  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
+0x10C  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00   ; 通道表其余为 0
+0x42C  01 00 00 00              ; tag 0x1A 条目 len=1
+0x430  17 00 00 00              ; tag 0x08 条目 len=0x17
+0x434  31 32 37 2E 30 2E 30 2E 31 3B 34 34 33 3B 31 30 30 34 3B 30 3B 30 00
                               ; "127.0.0.1;443;1004;0;0\0"
+0x44C  04 00 00 00              ; 通道 tag7 条目 len=4
+0x450  17 00 00 00              ; 通道 tag7 值 = 0x17 = 23
+0x454  04 00 00 00              ; 通道 tag5 条目 len=4
+0x458  00 00 00 00              ; 通道 tag5 值 = 0
```

---

## 7. 未解 / 未确认

1. **`tag 0x16` 语义未解**。`ApplySettings` 要求它是 `len == 4` 的 DWORD，
   `Initialize` 不读它；其下游含义（透传给 `0xb88cc0`）本轮未解。
2. **`tag 0x1A` 的真实判据未解**。`Initialize` 仅在其后所有前置 tag 成功后
   才读它，并用 `& 0xFF > 0` 判定。
3. **`tag 0x10` 的宽度语义未解**。`0x100067B9` 用 `wcslen`，
   但 `0x10006765` 只给 `0x28` 字节上限，二者单位不自洽（推断为宽字符计数）。
4. **`tag 0x03` 的下游语义未解**（1 字节、`> 0` 触发分支）。
5. **`tag 0x06` 与 `tag 0x0E` 的下游语义未解**。
6. **`GetDWORD` 无 tag 上界检查**：`tag > 0x40` 可越读；本报告未利用。
7. **真实业务值无来源**：HOST / PORT / uId / OpenID / LoginKey /
   GameSignature / JumpSignature 在本机静态文件中不可恢复。
   本报告只给容器格式，不给真实凭据。

---

## 8. 脚本与产物

| 文件 | 作用 |
|---|---|
| `_tp_dis.py` | TenProxy.dll 反汇编 / 切片 / vtable |
| `_tp_dump.py` | 把 VA 区间反汇编落盘 |
| `_tp_producer.py` | `tcls_core.exe` 反汇编 |
| `_tenproxy_build.py` | 生成 `TCLS_SHAREDMEMEMORY` 字节镜像 |
| `_tp_verify.py` | 用真实读取语义对比 Kuhn 与修正布局 |
| `_tp_init_full.txt` | `Initialize` 全量反汇编（686 行） |
| `_tp_getr_full.txt` | `GetDWORD` / `GetBytes` 全量反汇编（292 行） |
| `_tp_tcls_producer_7d10.txt` | 生产者 `sub_407D10` 全量反汇编 |
| `_tenproxy_shm.bin` | 示例映射字节镜像（`0x80000` 字节） |
| `_tenproxy_shm.json` | 示例映射的机器可读结构摘要 |

---

## 9. 最终结论（严格区分事实与推断）

1. **[事实]** `Initialize` 只检查 `mapped+0 >= 0x40`，无魔数、无版本字符串、
   无校验和。
2. **[事实]** 标签表基址 = `mapped+4`，`table[tag-1]` 是相对映射基址的条目偏移，
   `tag` 为 1-based。
3. **[事实]** 条目格式为 `[DWORD len][payload]`；`GetDWORD` 要求 `len == 4`，
   没有类型字段。
4. **[事实]** 通道表指针在 `mapped+0x50`（tag 0x14），不是 Kuhn 写的
   `mapped+0x4C`（tag 0x13）。
5. **[事实]** 通道表与子表的条目都是相对映射基址的绝对偏移，两级均 1-based。
6. **[事实]** 通道号是 `GetDWORD(0x12)`；`tag 0x13` 无特殊语义。
7. **[事实]** 生产者 `tcls_core.exe sub_407D10` 与消费者 `TenProxy.dll`
   的槽语义、条目格式完全一致，互为交叉验证。
8. **[推断]** Kuhn 映射"游戏读出全 0"的根因是第 4、5 条；
   修正这两点后容器即可被正确读取。
9. **[推断]** `Initialize` 会在第一个失败的 tag 处停止后续读取，
   但止步本身不会崩溃，只是拿不到后续标签；要让 `[0x18E0]=1`
   需要第 6.4 节的标签按序自洽。
