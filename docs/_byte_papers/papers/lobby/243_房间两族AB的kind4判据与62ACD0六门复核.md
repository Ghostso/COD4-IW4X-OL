# 243 房间两个发送族 A/B 的 `kind==4` 判据 + `0x62ACD0` 的六道静默门

## 一句话结论

两个发送族不是「A 是房间、B 是私聊」——**它们是同一个 `0x634340` 的两个出口，按 `kind` 值分流**：
`kind==4` 走族 A `0x62C380`→`0x7E8240`（`0xB8ED40`，5 个栈参）；`kind!=4` 走族 B `0x62C870`→`0x7E8300`（`0xB8EE70`，6 个栈参，多一个内联常量 `1`）。
**两族的 `kind` 判据连参数位置都不同**（族 A 用 `eax`，族 B 用 `[ebp+0x14]`）。而 `0x62ACD0` 是**另一条路**（队列迁移），它的 6 个 `cmp/test` 里**门 5 是门 4 的同义反复**，且**每一道失败都是 `ret 4` 静默返回、全函数无任何日志**。

---

## 证据表

### E1 — `kind` 从哪来：`0x634340` 的两个 `call` 点，判据同一个寄存器

`0x634340`（Manifold 分派 `[0x06]` 的目标）里有两处调用：

**族 A（`kind==4` 由 `0x62C380` 自己判）**：
```
0x634340  0x63435F mov edi,ecx
0x634340  0x6346?  lea ecx,[ebp-0x1E0]
0x634670  push ecx                       ; 参数3（输出对象）
0x634671  push ebx                       ; 参数2
0x634672  mov eax, 4                     ; ★ 参数0 = kind = 4（寄存器传参）
0x634677  call 0x62C380
```
**★ `mov eax,4` 是「寄存器传参」** —— `0x62C380` 开头 `0x62C38F mov edi,eax` 把它读到 `edi`，
然后 `0x62C393 cmp edi,4 / 0x62C396 jne 0x62C4BE`。**`eax!=4` 就跳去 `0x62C4BE`（另一分支）**。

**族 B（`kind` 由调用者栈参给）**：
```
0x634340  0x634615 mov edx,[ebp-0x1EC]
0x63461B  push 4                         ; 参数4
0x63461D  push edx                       ; 参数3
0x63461E  push esi                       ; 参数2
0x63461F  push ebx                       ; 参数1
0x634620  lea eax,[ebp-0x220]
0x634626  call 0x62C870                  ; ★ 族 B 自己读 [ebp+0x14] == 4
```
`0x62C870` 开头：
```
0x62C873  sub esp,0x1C
0x62C876  cmp dword [ebp+0x14], 4        ; ★ 参数4（第 4 个 push 进来的）= 4 ?
0x62C87A  push ebx / push esi / push edi
0x62C87D  mov edi, eax
0x62C87F  push 0x24
0x62C881  jne 0x62C99F                   ; ★ !=4 走另一分支
```
**★ 族 B 的 `kind` 在栈上第 4 个参数（`[ebp+0x14]`），不是 `eax`。这是两族第一个不对称。**

### E2 — 两族的真正区别：**参数个数**与**出口**

| | 族 A `0x62C380` | 族 B `0x62C870` |
|---|---|---|
| 入口 | `eax`（寄存器） | `[ebp+0x14]`（栈，第4参） |
| `kind==4` 分支 | `0x62C393 cmp edi,4 / jne 0x62C4BE` | `0x62C876 cmp [ebp+0x14],4 / jne 0x62C99F` |
| 位流分配 | `0x62C39C call 0xB74220(0x24)` | `0x62C887 call 0xB74220(0x24)` |
| 位流构造 | `0x62C3A8 push 0; push 0; 0x62C3AE call 0xB778E0` | `0x62C895 push ebx; push ebx; 0x62C899 call 0xB778E0` |
| 序列化 | `0x62C3C9 mov eax,[ebx]; mov edx,[eax]; 0x62C3D4 call edx`（vtable[0] = 写侧） | 同（`0x62C8B3..0x62C8BD`） |
| 外层封包 | `0x62C3D6 alloc 0x1C` + 装 `0xDB7154` + `0x62C43D call 0xB767D0` | `0x62C8BF alloc 0x1C` + 装 `0xDB7154` + `0x62C91A call 0xB767D0` |
| **出口** | **`0x62C45A call 0x7E8240`** 带 **3 个栈参**：`push edi([esi+0x1C]?)` / `push edi(长度)` / `push eax` | **`0x62C93D call 0x7E8300`** 带 **4 个栈参**：`push eax` / `push edi` / `push eax` / `push ecx` |
| `0x7E8240` 参数数 | 3（`ret` 无清理 ⇒ cdecl） | — |
| `0x7E8300` 参数数 | — | 4（`0x7E8339 push 1` 那一位是**第 4 参**） |

**`0x7E8300` 的 4 参展开**（`0x7E8333..0x7E833F`）：
```
0x7E8333  mov ecx,[ebp+0x14]   ; 参数4
0x7E8336  mov edx,[ebp+0x10]   ; 参数3
0x7E8339  push 1               ; ★ 常量 1（不是参数，是内联）
0x7E833B  push ecx             ; 参数4
0x7E833C  mov ecx,[ebp+0xC]    ; 参数2
0x7E833F  push edx             ; 参数3
0x7E8340  mov edx,[ebp+8]      ; 参数1
0x7E8343  push ecx             ; 参数2
0x7E8347  push edx             ; 参数1
```
⇒ `0x7E8300` 实际调 `0xB8EE70` 带 **6 个栈参**（`1, arg4, arg3, arg2, arg1` + `[edi+0x14]`,`[edi+0x10]`）。
`0x7E8240` 调 `0xB8ED40` 带 **5 个栈参**（无那个常量 `1`）。

### E3 — `0x7E8240` / `0x7E8300` 的三道公共闸门（完全相同，逐指令对齐）

```
0x7E8245 / 0x7E8305   call 0x803830        ; srpc 惰性构造器 -> 对象或 NULL
0x7E824C / 0x7E830C   test esi,esi / je    ; 门1：对象存在
0x7E8256 / 0x7E8316   call 0xB7A670        ; 见下，返回「状态值」不是布尔
0x7E825B / 0x7E831B   cmp eax,2 / jne      ; 门2：必须 == 2
0x7E8266 / 0x7E8326   call 0xB7A770        ; 内部又调 0xB7A670 + cmp eax,2
0x7E826B / 0x7E832B   test eax,eax / je    ; 门3：非零
```

### E3b — ★`0xB7A670` 的返回值域（必须逐个 `ret` 数，不能假设是布尔）

```
0xB7A670  push esi
0xB7A671  mov esi,ecx
0xB7A673  mov ecx,[esi+0x4F4]       ; ★ srpc+0x4F4 = HMAC 会话对象
0xB7A679  test ecx,ecx / 0xB7A67B jne 0xB7A681
0xB7A67D  xor eax,eax               ; ← ret#1: 无会话 => 0
0xB7A680  ret
0xB7A681  call 0xBA0780             ; eax = 状态值（见 E3c）
0xB7A686  cmp byte [esi+0x4F8],0    ; ★ 强制位
0xB7A68D  jne 0xB7A699              ; ← 强制位!=0：**跳过** cmp，原样返回状态值
0xB7A68F  cmp eax,2 / 0xB7A692 jne 0xB7A699   ; 状态!=2 => 原样返回
0xB7A694  mov eax,1                 ; ← 状态==2 且 无强制 => 返回 1
0xB7A699  pop esi / ret             ; ← ret#2: eax ∈ {1, 原状态值}
```

**★ 返回值域 = `{0} ∪ {0xBA0780 的状态值} ∪ {1}`。**
**⇒ 它返回 2 是可能的**（当 `+0x4F8 != 0` 且状态值 == 2）。
**⇒ 调用点的 `cmp eax,2` 不是恒失败，而是要求「强制位开着 且 状态==2」。**

### E3c — `0xBA0780` 的完整返回值域（三个 `ret` 全读）

```
0xBA0780  cmp dword [ecx+0x644], 0
0xBA0787  mov eax,[ecx+0xC8]
0xBA078D  je  0xBA079F                  ; [+0x644]==0 -> 走 0xBA079F
0xBA078F  cmp eax,2 / 0xBA0792 je 0xBA0799   ; [+0x644]!=0 且 [+0xC8]∈{1,2}
0xBA0794  cmp eax,1 / 0xBA0797 jne 0xBA07B1  ; 否则原样返回
0xBA0799  mov eax,2 / ret               ; ← ret#1: 2
0xBA079F  cmp eax,2 / 0xBA07A2 jne 0xBA07B1  ; [+0x644]==0 且 [+0xC8]!=2 => 原样
0xBA07A4  xor eax,eax
0xBA07A6  cmp dword [ecx+0x5E8],3 / sete al / inc eax
0xBA07B1  ret                           ; ← ret#2/#3: 1 或 2
```
**返回值域 = `{1, 2} ∪ {[+0xC8] 原值}`** ⇒ **含 2**。与 176 卷一致（本卷独立复核，逐 `ret` 确认）。

**⇒ 门4 的判据链完整**：
`0xB7A670 returns 2` ⟺ `srpc+0x4F4 != NULL` ∧ `srpc+0x4F8 != 0` ∧ `0xBA0780()==2`。
**「会话存在 ∧ 强制位 ∧ 状态2」三个条件同时成立才放行。**

### E4 — `0x62ACD0` 六个 `cmp/test` 的实读

| # | 地址 | 指令 | 通过条件 | 失败 |
|---|---|---|---|---|
| 1 | `0x62ACDC` | `mov eax,[edi+0x1C]` / `test eax,eax` | 非零 | `je 0x62AE59` |
| 2 | `0x62ACE7` | `cmp byte [eax+1],0` | **`[+1] != 0`** | `je 0x62AE59` |
| 3 | `0x62ACF1` | `call 0x803830` / `test esi,esi` | srpc 对象存在 | `je 0x62AE59` |
| 4 | `0x62AD02` | `call 0xB7A670` / `cmp eax,2` | **`== 2`** | `jne 0x62AE59` |
| 5 | `0x62AD12` | `call 0xB7A770` / `test eax,eax` | 非零 | `je 0x62AE59` |
| 6 | `0x62AD1F` | `cmp byte [edi+0x283],0` | **必须是 0** | `jne 0x62AE59` |

**门 4 的真实条件**（见 E3b/E3c）：`srpc+0x4F4 != NULL` ∧ `srpc+0x4F8 != 0` ∧ `0xBA0780()==2`。
**门 5 是门 4 的同义反复**：`0xB7A770` 第一件事就是 `0xB7A796 call 0xB7A670 / 0xB7A79B cmp eax,2 / 0xB7A79E je 0xB7A7B7`，
不等则 `0xB7A7A0 call 0x8435D0`（空桩）+ 返回 0。**所以门5 不提供新判据。**

**★ 六道门全部静默**：`0x62ACD0` 全函数**没有任何日志调用**（无 `0x4F82E0`、无 dvar 打印），
唯一的失败出口 `0x62AE59` 就是 `mov esp,ebp / pop ebp / ret 4`。
**⇒ 任何一道门失败，调用者（`0x6335D7`，FrameUpdate 内）完全不知道。**

### E5 — `0x62ACD0` 的真实业务（门全过之后）

```
0x62AD2C  xor eax,eax
0x62AD2E  mov [ebp-0x1C],eax / [ebp-0x18],eax / [ebp-0x14],eax   ; 局部 list 清空
0x62AD40  mov eax,4
0x62AD45  lea ecx,[edi+0x3A0F4]      ; ★ dwRoomImp+0x3A0F4
0x62AD50  cmp dword [ecx],0          ; 从高到低扫 5 个 slot
0x62AD55  sub ecx,0xC                ; ★ 步进 0xC
0x62AD58  dec eax / jns 0x62AD50
0x62AD5B  cmp [ebp-0x14],0 / je 0x62AD88
0x62AD61  lea esi,[edi+0x3A0D4]      ; ★ dwRoomImp+0x3A0D4
0x62AD67  mov eax,[esi+4]
0x62AD6D  push eax / push esi / 0x62AD6F call 0x656A10     ; 从 list 摘节点
0x62AD77  lea eax,[ebp+8] / 0x62AD7D call 0x6569A0         ; 插入另一个 list
0x62AD88  lea edi,[ebp-0x1C] / 0x62AD8B call 0x655C10      ; 销毁临时 list
0x62AD90  pop edi / pop esi / pop ebx / ret 4
```
⇒ **`0x62ACD0` = 「把 `dwRoomImp+0x3A0F4` 起的 5 槽 × 0xC 的链表，搬到 `+0x3A0D4` 那个链表」**。
**这是队列迁移/清理，不是"发送前的校验"。**

### E6 — `0x62ACD0` 的唯一调用者

**全库 `E8` 索引：`0x62ACD0` 的调用点只有 `0x6335D7`（1 处）**，在 `0x632D90`（`FrameUpdate`）内。
`0x6335D7` 处前面的条件是 `0x6335D? cmp ... / je` —— 是 **FrameUpdate 的周期性清理**，不是发送路径。

---

## 边界表

| # | 未解项 | 可独立核验任务 | 已穷尽排查 |
|---|---|---|---|
| B1 | `0x7E8300` 第 4 参那个内联常量 `1` 的语义 | 追 `0xB8EE70`（参数 6 个）的第 1 个参数用途 | ⚠️ 未做。`0x7E8339 push 1` 是硬编码，但**消费点在 `0xB8EE70` 内部**，需单独开卷 |
| B2 | `0x7E8240`(3 参) vs `0x7E8300`(4 参 + 常量1) 是不是「可靠/非可靠」两档 | 对比 `0xB8ED40` 与 `0xB8EE70` 的差异参数 | ⚠️ 未做。已定位两者是不同函数（不是同一函数的包装） |
| B3 | `+0x4F8`（强制位）谁置 1 | 全库扫 `mov byte [reg+0x4F8], 1` | ⚠️ 未做。已知 `0xB7A686` 只读 |
| B4 | `0x62ACD0` 迁移的 5 槽 × 0xC 结构 | 读 `dwRoomImp+0x3A0F4` / `+0x3A0D4` 的初始化点 | ⚠️ 未做。见 143 卷「`+0x3A098` 1 秒延迟哈希」可能相关 |
| B5 | `0x62C380` 的 `edi!=4` 分支（`0x62C4BE`）做什么 | 读 `0x62C4BE..0x62C572` | ⚠️ 未做。已知它同样 `alloc 0x24` + `0xB778E0`（`0x62C4E4`），但 `push` 用 `esi`（=0） |

## 更正

- **154/172 卷「唯一出口 `0x7E8300`，只有 1 个调用点」**：**不完整**。另有 **`0x7E8240`**（族 A 出口，3 个 `E8` 调用点：`0x62B800`/`0x62C45A`/`0x633839`）。**房间有两条出网口，不是一条。** 两者闸门逐指令相同（E3），区别只在参数个数（5 vs 6）。
- **173 卷「`0xB7A670` = 会话存在 且（`+0x4F8` 强制 ‖ `0xBA0780()==2`）」**：方向写反了。真值是：
  `+0x4F8 != 0` ⇒ **跳过** `cmp eax,2`，**原样返回状态值**（可以为 2）；
  `+0x4F8 == 0` ⇒ 状态值必须 `==2`，此时返回 **1**。
  **「强制」不是「无条件放行」，是「不再降级成 1」** —— 两者对下游 `cmp eax,2` 的结果完全不同。
- **172 卷「六道静默门」**：计数对（6 个 `cmp/test`），但**门 5 是门 4 的同义反复**（`0xB7A770` 内部第一件事就是同一对 `call 0xB7A670 / cmp eax,2`）；**真独立判据只有 5 个**。
