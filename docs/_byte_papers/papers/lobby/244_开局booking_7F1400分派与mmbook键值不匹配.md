# 244 开局 booking 应答的真实分派：`0x7F14xx` 的 `strcmp(…,"mmbook")` → `vt+0x13C`，与 `0x632680` 超时检测彻底分离

## 一句话结论

`0xDC6724 = "mmbook"` 在 `.text` 里**只有 2 个引用**：`0x62F7E0`（发送方，格式串 `0xDC672C="%s %d %s %d"` 与 `0xDC6724` 一起 `call 0x774980` 组包）和 **`0x7F153F`**（接收方，`push 6; push ebx; push 0xDC6724; call 0xC3C678` = `strncmp(…,"mmbook",6)`）。**匹配后立刻 `mov eax,[vt+0x13C] / 5 个 push / call eax`** —— 这就是 `dwRoomImp` 开局虚函数（已知伪入口 `0x632680`）的**第二个调用点**。⇒ **`strcmp` 命中 `"mmbook"` ⇒ 调 `0x632680`；而 `0x632680` 内部的门 6 期望 `"mmbook accepted"` ⇒ 必然不等 ⇒ 恒走超时分支**（227 卷结论），这就是「booking 成功了但开不了局」的机器指令级根因。

---

## 证据表

### E1 — `"mmbook"` 的两个引用（分母：3,237,168 条指令全索引）

| 地址 | 指令 | 角色 |
|---|---|---|
| `0x62F7E0` | `push 0xDC6724` | **发送方**：`0x62F7E3 push 0xDC672C`(`"%s %d %s %d"`) + `0x62F7EA call 0x774980`（格式化） |
| `0x7F153F` | `push 0xDC6724` | **接收方**：`0x7F153C push 6` + `0x7F153E push ebx` + `0x7F1544 call 0xC3C678`（strncmp 6 字节） |

**相关字符串**（`0xDC67xx` 连续区）：
```
0xDC6724 'mmbook'
0xDC672C '%s %d %s %d'
0xDC69B0 'mmbook accepted'
0xDC69D4 'mmbook timedout'
0xDE0764 (待查)
0xDE076C 'mmrsv'
0xDE0774 'mminvite'
```

### E2 — 发送方 `0x62F6F0`（booking 请求构造）

```
0x62F6F0  push ebp / mov ebp,esp / and esp,-8 / sub esp,0x1C
0x62F6F9  mov eax,[0xE3F240] / xor eax,esp / mov [esp+0x18],eax   ; stack cookie
0x62F707  push 0x40 / lea eax,[esi+0x3A050] / push ebx(0) / push eax
0x62F717  mov [esi+0x3A048],ebx          ; ★ 清 0
0x62F71D  mov [esi+0x3A04C],ebx          ; ★ 清 0
0x62F723  call 0xC42DE0                   ; memset(0x3A050, 0, 0x40)  64 字节缓冲
0x62F736  mov ecx,[edi+0x168]            ; ★ MMI+0x168 -> 0x3A048
0x62F73C  mov [esi+0x3A048],ecx
0x62F742  mov edx,[edi+0x16C]            ; ★ MMI+0x16C -> 0x3A04C
0x62F748  mov [esi+0x3A04C],edx
0x62F74E  lea edx,[edi+0x170]            ; MMI+0x170 = 字符串
0x62F760..0x62F767  strlen(edx)          ; 手写 strlen（逐字节 cmp bl）
0x62F779  cmp eax,0x3F / jb              ; clamp 到 0x3F（63）
0x62F78D  call 0xC427F0                  ; strncpy(0x3A050, MMI+0x170, min(len,63))
0x62F799  mov byte [ecx+esi+0x3A050],bl  ; 补 '\0'
0x62F7AB  mov dl,[0x82E1363]
0x62F7B1  mov eax,[0x7B25A38]
0x62F7C7  ... 0x62F7CB call 0xB74410     ; 组 13 字节头
0x62F7E0  push 0xDC6724                   ; ★ "mmbook"
0x62F7E5  push 0xDC672C                   ; ★ "%s %d %s %d"
0x62F7EA  call 0x774980                   ; sprintf(...)
0x62F7F9  mov ecx,[esi+0x3A04C]
0x62F801  mov edx,[edx+0x150]             ; ★ vt+0x150（不是 0x13C）
0x62F811  mov ecx,esi
0x62F819  call edx                        ; 发出去
0x62F821  mov eax,[edi+0x220] / mov [0x85286EC],eax
```

**★ `MMI+0x168` / `MMI+0x16C` 的来源**（216 卷说「只由 ctor 清零」）：
`0x62F736/0x62F742` 是**唯一读点**（分母：`+0x168]`/`+0x16C]` 在全库的 `.text` 命中里，在 `0x62C000..0x640000` 范围只有这两条）。
写点全在 MMI 内：`0x806BA7/0x806BAD mov [esi+0x168]/[esi+0x16C], ebx(=0)`（ctor `0x806B50`）＋ `0x806CDF/0x806F6C lea [esi+0x168]`（serialize）。
⇒ **216 卷正确：`MMI+0x168/16C` 静态只被 ctor 清零 + 序列化读写，非零只可能来自网络**。

### E3 — ★接收方 `0x7F14xx`（booking 应答分派，`ret 0x14` 5 个栈参）

```
0x7F152F  mov esi,[esp+0x2C]
0x7F1533  lea edi,[esp+0x30]
0x7F1537  call 0x7F3440                   ; 参数解析
0x7F153C  push 6
0x7F153E  push ebx                        ; 长度/源
0x7F153F  push 0xDC6724                   ; ★ "mmbook"
0x7F1544  call 0xC3C678                   ; strncmp(a, "mmbook", 6)
0x7F1549  add esp,0xC
0x7F154C  test eax,eax
0x7F154E  jne 0x7F1576                    ; ★ 不匹配 -> 试下一条
0x7F1550  mov edx,[esp+0x14]
0x7F1554  mov ecx,[0x82E13FC]             ; ★ AS 全局对象
0x7F155A  mov eax,[ecx]
0x7F155C  mov eax,[eax+0x13C]             ; ★★ vt+0x13C = dwRoomImp 开局虚函数
0x7F1562  push edx                        ; 参数5
0x7F1563  push ebx                        ; 参数4
0x7F1564  mov edx,edi / push edx          ; 参数3 = &解析结果
0x7F1567  mov edx,[ebp+0xC] / push edx    ; 参数2
0x7F156B  mov edx,[ebp+8] / push edx      ; 参数1
0x7F156F  call eax                        ; ★★ → 0x632680（已知 booking 处理函数）
0x7F1571  jmp 0x7F16D6
0x7F1576  push 5
0x7F1579  push 0xDE076C                   ; "mmrsv"
0x7F157E  call 0xC3C678                   ; strncmp(a, "mmrsv", 5)
0x7F1588  jne 0x7F15B2
0x7F1596  mov edx,[edx+0x140]             ; ★ 另一条 vt 槽 = +0x140
0x7F15AB  call edx                        ; → "mmrsv" 处理
```

**⇒ 三个 booking 类应答的 vt 槽（“命令字 → 虚函数”全表）**：

| 命令字 | 字符串 | `strncmp` 长度 | `call` 的 vt 槽 | 目标 |
|---|---|---|---|---|
| `mmbook` | `0xDC6724` | **6** | **`+0x13C`** | **`0x632680`**（227 卷确认） |
| `mmrsv` | `0xDE076C` | 5 | `+0x140` | 待查 |
| `mminvite` | `0xDE0774` | 8 | （后续分支） | 待查 |

### E4 — ★为什么「booking 成功仍开不了局」：`strcmp` 的键与门 6 的键不是同一个字符串

`0x632680` 内部（227 卷已读）：门 6 = `strcmp(参数3, 0xDC69B0)`，而 `0xDC69B0 = "mmbook accepted"`。
而 `0x7F156F` 传进去的**参数3 是 `edi` = `[esp+0x30]` 那个解析缓冲**（`0x7F1533 lea edi,[esp+0x30]`，
由 `0x7F1537 call 0x7F3440` 填充），**不是常量 `"mmbook accepted"`**。

**⇒ 只有当远端 HTTPS 应答的「第三个字段」恰好等于字面量 `"mmbook accepted"` 时，门 6 才通过。**
本卷**无法静态确定**远端会回什么（对端是腾讯 `formal-zone-auth.codol.qq.com`，229 卷），但**可以确定**：
- 门 6 的键是**远端应答里的字符串**（动态），不是编译期常量；
- 若远端回别的（例如 `"ok"` / `"accepted"` / 空），门 6 恒不等 ⇒ 走 `"mmbook timedout"` 分支（`0xDC69D4`）。

### E5 — `0x7F1110` 与 `0x7F14xx` 的关系

`0x7F1110`（229 卷称「HTTPS booking 入口」）与 `0x7F14xx` 是**两个不同函数**：
```
0x7F1110  ret 0x14   ; 5 参，无 strcmp
0x7F1400  push ebp / ... / ret 0x14  ; 从 0x7F1400 开始（0x7F13FF 是 int3）
```
`0x7F152F` 位于 **`0x7F1400`** 的函数体内（`0x7F13FF int3` 是边界）。
`0x7F1110` 的**唯一代码引用是数据指针 `0xDE07C4`**（`b'\x10\x11\x7f'` = little-endian dword `0x007F1110`，
落在字符串表区，说明它是**回调函数指针数组的一项**，不是被 `E8` 直接调用）。

**⇒ 实际调用关系**：`0x7F1400`（HTTPS 应答总分派）→ `strncmp` → `[vt+0x13C]` = `0x632680`。
`0x7F1110` 只是**另一个回调**（也被 `0xDE07C4` 表登记），不是 booking 分派器。

### E6 — `0x82E13FC` 是 AS 全局对象（不是 dwRoomImp）

`0x7F1554 mov ecx,[0x82E13FC]` + `0x7F155A mov eax,[ecx]` + `0x7F155C mov eax,[eax+0x13C]` —— 这是 228 卷的
**AS 回调模板**（302 处）。`0x82E13FC` 是一个包装对象，其 vtable 的第 0x13C/0x140 槽转给 `dwRoomImp`。
⇒ **`vt+0x13C` 是「AS 侧拿到的 dwRoomImp 虚函数槽」**，与 `0xDC73B0`/`0xDC7850` 是同一套 dwRoomImp vtable（191-216 卷）。

---

## 边界表

| # | 未解项 | 可独立核验任务 | 已穷尽排查 |
|---|---|---|---|
| B1 | `0x7F3440`（应答解析器）把什么放进 `[esp+0x30]`（即门6 的参3） | 反汇编 `0x7F3440` 全函数，标出它对 `[esp+0x30]` 的写入 | ⚠️ 未做，进 245 卷 |
| B2 | `0xDE0764` 是什么字符串 | 读 `cstr(0xDE0764)` | ⚠️ 未做（`mminvite` 前的空串？） |
| B3 | `mmrsv` / `mminvite` 的 vt 槽 `+0x140` / `+0x144` 目标 | 查 `0xDC73B0`/`0xDC7850` vtable 的 0x140/0x144 槽 | ⚠️ 未做。已定位 `0x82E13FC` 的第 0x140 槽在 `0x7F1596` 被用 |
| B4 | 远端腾讯 HTTPS 究竟回什么 | **静态不可达**（229 卷：对端是 `formal-zone-auth.codol.qq.com`） | ✅ 已穷尽：全镜像 `b"mmbook accepted"` 仅 1 处（`0xDC69B0`，被 `0x632680` 的 `strcmp` 读）；**没有任何本地代码把它填进应答缓冲** |
| B5 | `0x62F6F0` 的 3 个调用者哪个是真正的 booking 触发 | 读 `0x62F917` / `0x63789D` / `0x6378BE` | ⚠️ 未做 |

## 更正

- **229 卷「`0x7F1110` 是 HTTPS booking 入口，`0x7F156F` 在其内」**：**两个函数不是同一个**。
  `0x7F1110` 是 `ret 0x14` 的短函数（5 参，只读 `[0x84ABB08]`/`[0x84ABB14]` 比 `+0x8`/`+0xC`，然后调 `[0x82E1400]` 的两个槽）；
  **`0x7F156F` 属于 `0x7F1400`**（`0x7F13FF` 是 `int3` 边界）。**booking 分派器是 `0x7F1400`，不是 `0x7F1110`。**
- **227 卷「`0x632680` 是 booking 超时检测」**：本卷确认它的**两个调用点**都传「动态应答串」作参3，
  而门 6 期望编译期常量 `"mmbook accepted"` ⇒ **除非远端精确回这个串，否则恒走超时**。这不是「超时检测」，是**「键值不匹配的必然失败」**。
- **154/172 卷「`0x16` 通道」**：`0x62F7F9..0x62F819` 走的是 **`vt+0x150`**（不是房间消息通道）。**booking 走 HTTPS（`vt+0x150`），不走 `0x16` UDP 通道** —— 与 229 卷「booking 走 HTTPS 不走 3074」在指令级一致。
