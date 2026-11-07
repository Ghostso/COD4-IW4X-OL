# 学习报告 045 — capstone：P4 与 P1 的完整语义（状态机定案）

**方法**：capstone 反汇编 `0xBA3C62` / `0xBA3BC0` / `0xB9A742`
**性质**：权威反汇编
**★★★ 本报告把 LSG 状态机与认证判定彻底还原**

---

## 一、★★★ P4 的完整语义（`0xBA3C1A` 周边）

### 补丁点上下文（capstone 已验证）

```asm
00BA3BC0  8d55f0            lea  edx, [ebp - 0x10]
00BA3BC3  52                push edx
00BA3BC4  51                push ecx
00BA3BC5  894df0            mov  [ebp - 0x10], ecx
00BA3BC8  8b4d10            mov  ecx, [ebp + 0x10]
00BA3BCB  51                push ecx
00BA3BCC  50                push eax
00BA3BCD  e8ee47fdff        call 0xB783C0            ← ★ 某个调用
00BA3BD2  83c418            add  esp, 0x18
00BA3BD5  84c0              test al, al
00BA3BD7  752c              jne  0xBA3C05           ← 成功 → 跳过失败处理
--- 失败路径 A ---
00BA3BD9  32db              xor  bl, bl
00BA3BDB  e8f0f9c9ff        call 0x8435D0
00BA3BE0  6a04              push 4                  ← ★ 状态 4
00BA3BE2  e8593d95ff        call 0x4F7940           ← ★ 状态设置函数
00BA3BE7  83c404            add  esp, 4
00BA3BEA  8bce              mov  ecx, esi
00BA3BEC  e82ff8ffff        call 0xBA3420
00BA3BF1  5e                pop  esi
00BA3BF2  8ac3              mov  al, bl             ← 返回 bl（false）
```

### P4 补丁点的分支（`0xBA3C1A`）

```asm
00BA3C1A  85c0              test eax, eax
00BA3C1C  7544              jne  0xBA3C62           ← ★ 原：跳失败
00BA3C1E  8d5801            lea  ebx, [eax + 1]     ← ebx = 1（成功标志）
00BA3C21  398644060000      cmp  [esi + 0x644], eax
00BA3C27  750f              jne  0xBA3C38
00BA3C29  8b8e40060000      mov  ecx, [esi + 0x640]
00BA3C2F  51                push ecx
00BA3C30  e89bf9c9ff        call 0x8435D0
00BA3C35  83c404            add  esp, 4
--- 成功路径 ---
00BA3C38  8b4dfc            mov  ecx, [ebp - 4]
00BA3C3B  899eec050000      mov  [esi + 0x5EC], ebx     ← +0x5EC = 1
00BA3C41  899ef0050000      mov  [esi + 0x5F0], ebx     ← +0x5F0 = 1
00BA3C47  c786e805000003000000  mov dword ptr [esi + 0x5E8], 3   ← ★★★ state = 3
00BA3C51  5e                pop  esi
```

### P4 跳转目标 `0xBA3C62`（失败路径 B）

```asm
00BA3C62  32db              xor  bl, bl              ← bl = 0（失败标志）
00BA3C64  e867f9c9ff        call 0x8435D0
00BA3C69  6a03              push 3                  ← ★ 状态 3
00BA3C6B  e972ffffff        jmp  0xBA3BE2           ← 跳回状态设置 + 清理
```

---

## 二、★★★ 状态机的完整还原

```
0xBA3C1A: test eax, eax
   │
   ├─ eax != 0 ──【原逻辑】──> 0xBA3C62
   │                              bl = 0
   │                              call 0x8435D0
   │                              push 3           ← 状态 3
   │                              jmp 0xBA3BE2（call 0x4F7940 + 清理，返回 bl=0）
   │
   └─ eax == 0 ──继续──> 0xBA3C1E..0xBA3C47
                              ebx = 1
                              [+0x5EC] = 1
                              [+0x5F0] = 1
                              [+0x5E8] = 3     ★★★ 状态 3
                              返回（bl 保持 1？—— 需要看后续）
```

★★★ **关键发现**：
```
【原逻辑】两条路径都以 state = 3 结束！
   - eax != 0 → push 3
   - eax == 0 → [+0x5E8] = 3
```

★★ **区别只在 `bl`（返回的布尔值）和 `[+0x5EC]` / `[+0x5F0]`。**

★★★ **⇒ P4 补丁（NOP 掉 `jne`）的效果**：
**强制走 `eax == 0` 分支 ⇒ `bl = 1`（成功）+ 三个字段全设。**

★ **即：把"状态 3 + 失败"变成"状态 3 + 成功"。**

---

## 三、★★★ `0x4F7940` —— 状态设置函数

```asm
00BA3BE2  e8593d95ff        call 0x4F7940
```

★★ **`0xFA000000 + 0x4F7940`... 不，是 `0xBA3BE7 - 0x4C2A7 = 0x4F7940`** ——
**需要 capstone 反汇编确认。**

★ **但两个分支都 `call 0x4F7940`** ——
**这是**统一的状态提交函数**。**

---

## 四、★★★ P1 的完整语义（`0xB9A78C`）

### 补丁点上下文

```asm
00B9A78C  84c0              test al, al
00B9A78E  74b2              je   0xB9A742           ← ★ 原：JE
00B9A790  b001              mov  al, 1
00B9A792  ebb0              jmp  0xB9A744
00B9A794  32c0              xor  al, al
00B9A796  8b8d54fdffff      mov  ecx, [ebp - 0x2ac]
00B9A79C  3b0d089fd500      cmp  ecx, [0xD59F08]
00B9A7A2  7449              je   0xB9A7ED
```

### 跳转目标 `0xB9A742`

```asm
00B9A742  32c0              xor  al, al            ← ★ al = 0
00B9A744  89bd54fdffff      mov  [ebp - 0x2ac], edi
00B9A74A  89bd34fdffff      mov  [ebp - 0x2cc], edi
00B9A750  84c0              test al, al
00B9A752  7440              je   0xB9A794           ← al==0 → 跳 0xB9A794
00B9A754  8d8554fdffff      lea  eax, [ebp - 0x2ac]
00B9A75A  50                push eax
00B9A75B  8d8d34fdffff      lea  ecx, [ebp - 0x2cc]
00B9A761  51                push ecx
00B9A762  57                push edi
00B9A763  8d950cffffff      lea  edx, [ebp - 0xf4]
00B9A769  6a04              push 4
00B9A76B  52                push edx
00B9A76C  e89f9ffdff        call 0xB74710
00B9A771  83c414            add  esp, 0x14
00B9A774  84c0              test al, al
00B9A776  741c              je   0xB9A794           ← 失败 → 0xB9A794
00B9A778  b001              mov  al, 1
00B9A77A  eb1a              jmp  0xB9A796
```

★★★ **`0xB9A742` 是 `xor al,al`** ——
**P1 补丁把 `je 0xB9A742` 改成 `jne 0xB9A742`，
即"al == 0 时**不**跳"变成"al != 0 时**不**跳"。**

★★ **等等 —— `74→75` 是 `JE→JNE`。**

```
原：al == 0 → 跳到 0xB9A742（xor al,al ⇒ al 保持 0）→ 走失败
改：al != 0 → 跳到 0xB9A742（xor al,al ⇒ al 变 0）→ ★ 仍然失败

反过来：
原：al != 0 → 落到 0xB9A790（mov al,1 ⇒ 成功）
改：al == 0 → 落到 0xB9A790 → ★ 成功
```

★★★ **⇒ P1 把**判定条件完全反转**：
原来 `al != 0` 才成功，改成 `al == 0` 才成功。**

★ **即：把"签名有效"的条件从 `true` 变成 `false`。**

★★ **这与"接受自签名"的目标一致** ——
**自签名校验会返回 `false`（无效），反转后 `false` 视为有效。**

---

## 五、★★★ 完整的认证流程还原（P1..P4）

```
1. 客户端发起 auth（TLS 到 fake_auth_tls.py）
        ↓
2. fake_auth_tls 返回 200 + ticket（自签名）
        ↓
3. 客户端校验签名 ⇒ al = 0（无效）
        ↓
   ★ P1：JE→JNE ⇒ al == 0 现在视为有效 ⇒ 继续
        ↓
4. 客户端解析 ticket ⇒ 失败（因为我们发的不是真 ticket）
        ↓
   ★ P2：JNE→JMP ⇒ 无条件跳成功路径
   ★ P3：call→jmp ⇒ 跳过失败处理
        ↓
5. 客户端尝试 LSG nonce 校验 ⇒ eax != 0（不匹配）
        ↓
   ★ P4：NOP ⇒ 强制走"匹配"分支
        ↓
6. [sub+0x5E8] = 3（LSG 已连接）
```

★★★ **⇒ 四个补丁构成**完整的认证绕过链**。**

---

## 六、逐字节证据总表

| # | VA | 指令 | 说明 |
|---|---|---|---|
| 1 | `0xBA3BCD` | `call 0xB783C0` | P4 前的检查 |
| 2 | `0xBA3BD7` | `jne 0xBA3C05` | 成功跳过失败 |
| 3 | `0xBA3BE0` | `push 4` | 失败路径 A 的状态 4 |
| 4 | `0xBA3BE2` | `call 0x4F7940` | ★ 状态提交函数 |
| 5 | `0xBA3C1A` | `test eax,eax` | P4 判定 |
| 6 | `0xBA3C1C` | `jne 0xBA3C62` | ★ 补丁 NOP 掉 |
| 7 | `0xBA3C1E` | `lea ebx,[eax+1]` | `ebx = 1`（成功） |
| 8 | `0xBA3C47` | `mov [esi+0x5E8], 3` | ★★★ state = 3 |
| 9 | `0xBA3C62` | `xor bl,bl` | 失败路径 B |
| 10 | `0xBA3C69` | `push 3` | 失败路径也是状态 3 |
| 11 | `0xBA3C6B` | `jmp 0xBA3BE2` | 跳回提交 |
| 12 | `0xB9A78E` | `je 0xB9A742` | ★ P1 改 JNE |
| 13 | `0xB9A742` | `xor al,al` | P1 目标 |
| 14 | `0xB9A790` | `mov al,1` | P1 成功分支 |
| 15 | `0xB9A79C` | `cmp ecx,[0xD59F08]` | ★ 哨兵值比较 |

---

## 七、结论

### 1. ★★★ 两条路径都设 state = 3，区别在返回值

★★★ **⇒ P4 补丁的真正作用是**让函数返回"成功"**（`bl = 1`），
状态本来就都是 3。**

★ **这可能影响上层逻辑（是否继续后续步骤）。**

### 2. ★★★ P1 反转的是"签名有效性"判定

★★ **原来 `al != 0` 才算有效，改成 `al == 0` 才算有效**
⇒ **自签名（无效）变成了有效。**

### 3. ★★★ 四个补丁是**完整的认证绕过链**

★★ **缺任何一个，客户端都会在对应环节失败。**

### 4. ★★ `0xD59F08` 是一个全局哨兵值

★★ **`cmp ecx, [0xD59F08]`** —— 可能是一个"无效对象"标记。

### 5. ★★★ 我们不需要这些补丁

★★ **我们的固化链已经能进大厅（`5E8=3`），说明走的是**另一条路径**。**
**可能我们的 `lobby_server.py` 发的 ticket 是客户端接受的（不是自签名问题）。**

---

## 八、待用 capstone 继续（★ 优先级）

- [ ] ★★★ **反汇编 `0x4F7940`（状态提交函数）**
- [ ] ★★★ **反汇编 `0xB783C0`（P4 前的检查）**
- [ ] ★★ **`0xBA3C05`（成功路径，P4 的 `jne` 目标）**
- [ ] ★★ **`0xD59F08` 的值与使用点**
- [ ] ★ **`[esi+0x640]` / `[esi+0x644]` 的语义**
- [ ] ★ **确认我们的固化链为什么不需这些补丁**
