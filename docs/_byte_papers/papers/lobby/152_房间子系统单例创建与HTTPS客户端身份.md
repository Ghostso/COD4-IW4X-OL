# 152 · 房间子系统单例创建 + HTTPS 客户端身份

> 前序：151（容器语义验证 + 加密全局指针层）、150（帧更新 + vtable 全表）、147（消息泵 this=srpc）
> 性质：**按序追「全局唯一写点」**。本卷定位了 `dwRoomImp` 的**唯一创建点**，
> 并**更正一个跨三卷的误判**：147 卷追的「连接建立」用的是 HTTPS 客户端，不是游戏服连接。

---

## §0 九条结论

1. ★★★★★ **`0x639D00` = 「房间子系统初始化」**，一次创建 **3 个单例**：
   | 全局 | 大小 | 构造器 | 身份 |
   |---|---|---|---|
   | **`[0x82E13FC]`** | `0x3A128` | `0x62C000` | **`dwRoomImp`** |
   | `[0x82E1400]` | `0x3A160` | `0x638210` | 另一个（待定）|
   | `[0x82E1404]` | `0x38` | 内联（vtable `0xDC74E0`）| **`dwInvitationImp`** |
2. ★★★★★ **`[0x82E13FC]` 全镜像 read=299 / write=1，唯一写点 = `0x639D1E`**。
   **⇒ `dwRoomImp` 是启动时创建一次的单例，总是存在。**
3. ★★★★ **`0x639D80..0x639E25` 是 `dwRoomImp` 初始化**：
   清 `+0x38528`(0x1E8) / `+0x38540`(0x1E8) / `[0xE36E4D8]`(0x730)，
   调 `0x63B0F0` / `0x7C5060` / `0x724CE0`。
4. ★★★★★ **`[0x84ABB14]` = HTTPS/TLS 客户端**：
   ```asm
   0x7F2C03  push 0x32D0                    ; 13008 字节
   0x7F2C08  call 0xB74220                  ; 分配
   0x7F2C15  push 0x81A76A8                 ; ★ "formal-zone-auth.codol.qq.com"
   0x7F2C1D  call 0xB99090                  ; 构造
   0x7F2C26  mov [0x84ABB14], eax           ; ★★ 唯一写点
   0x7F2C33  push 0xDC9CA4                  ; ★ "cacert.pem"
   0x7F2C3A  call 0xB9A100                  ; 加载 CA 证书
   ```
5. ★★★★★ **更正 145/147 卷的跨卷误判**：147 卷追的
   `0x7F3890 → 0x7F3912 → 0xB82070 → 0xB81EF0 → 0xBA2800`「连接建立链」，
   其参数来自 `[0x84ABB14]`（**HTTPS 客户端**）⇒
   **那是腾讯认证服务器的连接，不是游戏服连接。**
6. ★★★★ **`[0x84ABB08]` 两个写点**：`0x7F2BE9`（`call 0xB88B80` 后存）/
   `0x7F2BF2`（`xor eax,eax` 后清 0）。
7. ★★★★ **`[0x84ABB0C]` 两个写点**：`0x801A3B` / `0x801A45`。
8. ★★★ **`[0x82E1408]` = 房间报文文本载荷指针**（read=2 / write=1）—— 与 139 卷一致。
9. ★★★ **`[0x82E142C]`（read=2 / write=1 @`0x639F30`）** 也是房间子系统的一部分。

---

## §1 `0x639D00` 房间子系统初始化（逐字节）

```asm
0x639D00  push ecx / push esi / push edi
0x639D03  push 0x3A128                  ; ★ dwRoomImp 大小
0x639D08  call 0xC3E9F5                 ; 分配
0x639D0D  xor edi,edi
0x639D12  cmp eax,edi / je 0x639D25
0x639D16  push 1
0x639D18  push eax
0x639D19  call 0x62C000                 ; ★ dwRoomImp 构造器
0x639D1E  mov [0x82E13FC], eax          ; ★★★ 唯一写点
0x639D23  jmp 0x639D2B
0x639D25  mov [0x82E13FC], edi          ; 分配失败 ⇒ 0

0x639D2B  push 0x3A160                  ; 第二个对象
0x639D30  call 0xC3E9F5
0x639D3D  call 0x638210
0x639D42  mov [0x82E1400], eax

0x639D4F  push 0x38                     ; 第三个：dwInvitationImp
0x639D51  call 0xC3E9F5
0x639D5F  mov [esi+4],edi ... mov [esi+0x20],edi
0x639D71  mov dword [esi], 0xDC74E0     ; ★ vtable（150 卷表：dwInvitationImp）
0x639D83  call 0xB75DD0
0x639D88  mov [0x82E1404], esi

; ---- 初始化 dwRoomImp ----
0x639D96  mov esi,[0x82E13FC]
0x639D9C  push 0x1E8
0x639DA1  add esi, 0x38528
0x639DA9  call 0x769840                 ; memset-ish
0x639DB1  push 0x730
0x639DB7  push 0xE36E4D8                ; ★ 全局数组（0x730 字节）
0x639DBC  mov dword [esi], 1
0x639DC2  call 0xC42DE0                 ; memset
0x639DCA  push 1
0x639DCC  mov ecx, 0xE36EBE8
0x639DD1  call 0xB94940                 ; 构造
0x639DD6  mov esi,[0x82E1400]           ; 第二个对象同样处理
0x639DE1  add esi, 0x38540
0x639E02  call 0xC42DE0
0x639E16  call 0x63B0F0
0x639E1B  call 0x7C5060
0x639E20  call 0x724CE0
0x639E25  push 0xDAE091                 ; 空串
```

★ **`dwRoomImp` 的大小 `0x3A128` 与 139 卷的记录完全一致。**

---

## §2 ★★★★★ HTTPS 客户端（跨卷更正）

```asm
0x7F2BFA  mov eax,[0x84ABB14]
0x7F2BFF  test eax,eax / jne 0x7F2C33
0x7F2C03  push 0x32D0                    ; 13008 字节
0x7F2C08  call 0xB74220
0x7F2C10  test eax,eax / je 0x7F2C24
0x7F2C14  push edi
0x7F2C15  push 0x81A76A8                 ; ★ "formal-zone-auth.codol.qq.com"
0x7F2C1A  push ebx
0x7F2C1B  mov ecx,eax
0x7F2C1D  call 0xB99090
0x7F2C26  mov [0x84ABB14], eax           ; ★★ 唯一写点
0x7F2C2B  test eax,eax / je 0x7F2D87
0x7F2C33  push 0xDC9CA4                  ; ★ "cacert.pem"
0x7F2C38  mov ecx,eax
0x7F2C3A  call 0xB9A100                  ; 加载证书
0x7F2C3F  mov eax,[0x849B870]
0x7F2C44  cmp dword [eax+0xC],0 / je
0x7F2C4A  mov ecx,[0x849B86C]
0x7F2C50  mov edx,[ecx+0xC]
0x7F2C53  mov ecx,[0x84ABB14]
0x7F2C59  push edx
0x7F2C5A  call 0xB998D0                  ; 设置参数
0x7F2C64  cmp dword [0x331C5C0],0
0x7F2C71  cmp byte [0x849B501],0
0x7F2C78  mov bl,[0xE3EC97C]
```

**⇒ `0x84ABB14` 是「HTTPS 客户端」，目标是腾讯认证域名，并加载 `cacert.pem`。**

### 2.1 更正 147 卷

147 卷追的链路：

```
0x7F3890 → 0x7F38CB mov eax,[0x84ABB08]
         → 0x7F38D4 mov eax,[0x84ABB14]   ← ★ 这里是 HTTPS 客户端
         → 0x7F38F0 call 0xB9A0E0          ; lea eax,[ecx+0x28]
         → 0x7F3912 call 0xB82070          ; 「连接建立」
```

**⇒ `0xB82070` 拿到的是 HTTPS 客户端对象的一个字段（`+0x28`），
它建立的是 **HTTPS 认证连接**，不是游戏服连接。**

★★★ **这解释了一个长期矛盾**：147 卷读到 `[0x84ABA7C] = 2`（「已连接」）却
`srpc+0x4F4` 之外什么都对不上 —— 因为那个「已连接」是**认证连接**的状态。

---

## §3 房间路径全局的读写比总表

| 全局 | read | write | 唯一/主要写点 |
|---|---|---|---|
| `0x82E13FC`（dwRoomImp）| **299** | **1** | `0x639D1E` |
| `0x84ABB08` | 127 | 2 | `0x7F2BE9` / `0x7F2BF2` |
| `0x84ABB14`（HTTPS 客户端）| 123 | **1** | `0x7F2C26` |
| `0x84ABB0C` | 7 | 2 | `0x801A3B` / `0x801A45` |
| `0x76446B0`（clientState）| 43 | 5 | — |
| `0x8269774`（srpc）| 27 | 3 | `0x803850` / `0x80388D` |
| `0x84ABA7C`（连接状态）| 4 | 5 | — |
| `0x82E1408`（文本载荷）| 2 | 1 | — |
| `0x82E142C` | 2 | 1 | `0x639F30` |

★ **`0x82E13FC` 的 299:1 是全表最极端的 —— 它是"创建一次、处处读"的典型单例。**

---

## §4 对「房间动作不出网」的影响

**本卷没有推翻 149/150 卷的结论**，反而补强：

- `dwRoomImp` **总是存在**（299 读 / 1 写，启动时创建）⇒ **不是"对象未创建"**
- Ready/ChangeTeamRequest 的发送侧构造点 → `0x62C5A0` 入队 `+0x3A098`
- `+0x3A098` 的遍历只做清理
- 唯一的网络出口 `0x7E8300` 只被 `0x62C870(kind=4)` 调用

**⇒ 房间动作的「入队 → 出网」缺口仍然存在。**

---

## §5 诚实边界

1. **`0x638210` 构造的 `[0x82E1400]`（0x3A160）身份未定**。
2. **`0x639D00` 函数的调用者未追**（谁触发房间子系统初始化）。
3. **`[0x84ABB08]`（`0xB88B80` 构造）的身份未定** —— 它与 HTTPS 客户端配对使用。
4. **`0xB82070` 的 `[ebp+0x90]` 具体字段（`https+0x28`）语义未定**。
5. **`0xE36E4D8` / `0xE36EBE8` 两个全局的身份未定**。

---

## §6 工具

| 工具 | 用途 |
|---|---|
| `tools/s151g_roomglobals.py` | 房间路径全局的读写比批量统计 |
| `tools/as_show_135.py` | 反汇编器 |

## §7 方法论

1. ★★★★★ **「读多写少」的全局，写点就是它的创建点** —— 追一个写点 = 找到整个子系统的初始化。
2. ★★★★★ **一个初始化函数里连续创建多个单例**（本例 3 个：0x3A128 / 0x3A160 / 0x38）
   ⇒ 把它整段读完，能一次拿到全部单例。
3. ★★★★ **字符串常量是最强的身份判据**：
   `"formal-zone-auth.codol.qq.com"` + `"cacert.pem"` ⇒ 无条件确定是 HTTPS 客户端。
4. ★★★★ **跨卷结论要用新证据回检** —— 147 卷的「连接建立」被本卷更正。
5. ★★★ **分配大小是类的指纹**：`0x3A128` 一次锁定 `dwRoomImp`。
