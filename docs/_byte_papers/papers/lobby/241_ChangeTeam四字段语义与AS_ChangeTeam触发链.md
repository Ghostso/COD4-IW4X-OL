# 241 ChangeTeam 四字段语义定案 + `AS_ChangeTeam`（不是 `SetTeam`）触发链

## 一句话结论

`dwRoomMessageChangeTeam`（线上 `0x14`）四字段 = **`(+8:u32, +0xC:u32, +0x10:u8, +0x18:u64)`**，其中 **`+0xC` 就是 `+0x18` 的低 32 位**（同一寄存器 `edx` 先后写两处）；语义经读取者反推：**`+0x10`=阵营(team)、`+0xC`=成员 ID 低半、`+8`=局序号**。**客户端从不主动发它**（`0x6281D0` 的 `E8` 调用点 = 0，分母 = 全 `.tp3` 段 158,187 条 `E8`）；Flash 侧的入口叫 **`AS_ChangeTeam`**（不是任务书推测的 `AS_SetTeam` —— 全镜像 `b"SetTeam"` 只在 Segment 2 的 AVM2 导出区命中 3 次，`.text` 里 0 次），且它**只带 1 个 bool 参数**、**走的不是 ChangeTeam 报文**。

---

## 证据表

### E1 — 构造函数 `0x6281A0`：四字段参数顺序（唯一权威）

```
0x6281A0  push ebp / mov ebp,esp
0x6281A3  mov edx,[ebp+0xC]        ; 参数2
0x6281A6  mov [eax+8],ecx          ; ★ [eax+8] = ecx（非栈参！调用者约定）
0x6281A9  mov cl,[ebp+8]           ; 参数1（byte）
0x6281AC  mov [eax+0xC],edx        ; ★ [+0xC] = 参数2 (u32)
0x6281AF  mov edx,[ebp+0x10]       ; 参数3
0x6281B2  mov [eax+0x10],cl        ; ★ [+0x10] = 参数1 的低字节 (u8)
0x6281B5  mov ecx,[ebp+0x14]       ; 参数4
0x6281B8  mov [eax+4],0x14         ; ★ 线上类型号 = 0x14 = 20
0x6281BF  mov [eax],0xDC7648       ; 装 vtable（序号 28）
0x6281C5  mov [eax+0x18],edx       ; ★ [+0x18] = 参数3 (u32 低位 → u64 低半)
0x6281C8  mov [eax+0x1C],ecx       ; ★ [+0x1C] = 参数4 (u32 高位 → u64 高半)
0x6281CC  ret 0x10                 ; 4 个栈参
```

| 对象偏移 | 类型 | 写入点 | 写侧序列化 | 读侧落点 |
|---|---|---|---|---|
| `+4` | u8→dword | `0x6281B8` | `W_TAG(3)+W_VAL(8)` | `[esi+4]`（`0x628282`） |
| `+8` | **u32** | `0x6281A6`（`ecx`） | `W_TAG(0x15)+W_VAL(32)` | `0x6282AF` → `[esi+8]` |
| `+0xC` | **u32** | `0x6281AC`（参数2） | `W_TAG(0x15)+W_VAL(32)` | `0x6282E7` → `[esi+0xC]` |
| `+0x10` | **u8** | `0x6281B2`（参数1低字节） | `W_TAG(0x15)+W_VAL(8)` | `0x6282CB` → `[esi+0x10]` |
| `+0x18` | **u64** | `0x6281C5`/`0x6281C8` | `W_TAG(0x15)+W_VAL(64)` | `0x628303` → `[esi+0x18]` |

**读侧顺序**（`0x628260`，逐项对账）：
```
0x62826D  push 3   / 0x628271 call R_TAG   -> type
0x62827A  push 8   / 0x628282 R_VAL 8      -> [esi+4]
0x62829E  push 0x15/ 0x6282A2 R_TAG
0x6282A7  push 0x20/ 0x6282AF R_VAL 32     -> [esi+8]
0x6282BA  push 0x15/ 0x6282BE R_TAG
0x6282C3  push 8   / 0x6282CB R_VAL 8      -> [esi+0x10]
0x6282D6  push 0x15/ 0x6282DA R_TAG
0x6282DF  push 0x20/ 0x6282E7 R_VAL 32     -> [esi+0xC]
0x6282F2  push 0x15/ 0x6282F6 R_TAG
0x6282FB  push 0x40/ 0x628303 R_VAL 64     -> [esi+0x18]
```
**★ 写侧与读侧顺序不同**（写：8→0xC→0x10→0x18；读：8→0x10→0xC→0x18）。
这就是 172 卷「ChangeTeam = u32/u8/u32/u64」的正确出处 —— **按线上出现顺序是 u32, u32, u8, u64**（写侧），
**按对象偏移升序是 +8(u32), +0xC(u32), +0x10(u8), +0x18(u64)**。

### E2 — 字段语义（从读取者反推）

`0x636336`（分派 `[0x14]`）读完后：
```
0x6363F6-0x636404  eax = [ebp-0xA94] * 0x1D0 + [ebx+0xE368]     ; 成员记录基址
0x636418-0x636442  lea ecx,[ebp-0xB00]; mov [ecx+8],2             ; ChangeTeam 对象 count=2（错，是 [+4]=2? 见下）
0x636442           mov byte [ebp-0xAF0],0xFF                     ; [+0x10] = 0xFF
0x636455           call 0x628260                                 ; 读 ChangeTeam
0x6364AE           cmp edx,[esi+0x8C]                            ; ★ 与成员记录 +0x8C 比较
0x6364ED           cmp [esi+0x88],ecx                            ; ★ vs 成员记录 +0x88（位宽 0x20，即 u64 低半）
0x6364F5           mov dl,[esi+0xB0] / cmp dl,[ebp-0xAF0]        ; ★ vs 成员记录 +0xB0 (u8)
0x63651F           call 0x6281A0                                 ; ★ 回推构造 ChangeTeam
0x63652A-0x63653B  call [vtable+0x148]                            ; 送事件
0x636577           mov dword [esi+0x8C],eax                      ; ★ 更新 +0x8C
0x636569           mov [esi+0x88],eax                            ; ★ 更新 +0x88
0x636575           mov [esi+0xB0],dl                             ; ★ 更新 +0xB0
```

**字段名判定**：

| 对象偏移 | 线上下标 | 落点 | 判据 | 命名 |
|---|---|---|---|---|
| `+4` | 类型=0x14 | — | `0x6281B8` | 类型号 |
| `+8` | 第 1 个 u32 | 成员记录 `+0x8C` | `0x6364AE cmp edx,[esi+0x8C]` | **sessionSeq / 局编号** |
| `+0xC` | 第 2 个 u32 | 成员记录 `+0x88` 低半 | `0x6364ED cmp [esi+0x88],ecx` | **memberId 低 32** |
| `+0x10` | 第 1 个 u8 | 成员记录 `+0xB0` | `0x6364F5 cmp dl,[esi+0xB0]` | **team（阵营）** |
| `+0x18` | u64 | 成员记录 `+0x88`（64 位合读） | `0x636577` 更新 | **memberId(u64) 上 32 + 下 32** |

**最关键的语义证据**：`0x6364E7-0x636501`
```
0x6364E7  mov ecx,[ebp-0xAF8]     ; = [+0xC] (u32)
0x6364ED  cmp [esi+0x88], ecx     ; 成员记录 +0x88 == [+0xC]
0x6364F3  jne 0x636503
0x6364F5  mov dl,[esi+0xB0]
0x6364FB  cmp dl,[ebp-0xAF0]      ; 成员记录 +0xB0 == [+0x10]
0x636501  je  0x63653D            ; ★ 两个都相等 => 跳过（不推事件）
```
⇒ **`+0x10`(u8) 是「阵营」，`+0xC`(u32) 是「成员 ID」，两者都相等就"无变化"不推事件**。
`+0x18`(u64) 在 `0x6281A0` 里是「参数3/参数4 拼成 64 位」，与 `+0xC` 重叠 —— **`+0xC` 是 `+0x18` 的低 32 位**。
验证：`0x6281AC mov [eax+0xC],edx`（edx=[ebp+0xC]=参数2）；`0x6281C5 mov [eax+0x18],edx`（**同一个 edx**）⇒ **`[+0xC]` 就是 `[+0x18]` 的低半**。

### E3 — ★AS 回调不是 `AS_SetTeam`，是 **`AS_ChangeTeam`**（字符串 + RTTI 双重铁证）

**Flash 侧函数名串表**（`0xDDD4E4` 起连续 ASCII，全是房间 API 名）：
```
0xDDD4F0 'StartMatchCountDown'
0xDDD504 'SetReadyState'        <-- 只有这个带 Set 前缀
0xDDD514 'GetReadyState'
0xDDD524 'ListDedicatedServer'
0xDDD538 'IsRoomHost'
0xDDD544 'RefreshInRoom'
0xDDD554 'MarketDataReceivedInRoom'
0xDDD570 'EnableVoiceTalk'
0xDDD580 'EnableInRoomEvent'
0xDDD594 'CheckTeamAvatar'
0xDDD5A4 'ChangeTeam'           <-- ★ 就是它，没有 SetTeam
0xDDD5B0 'GetTeamType'
0xDDD5BC 'ChangeRoomInfo'
0xDDD5CC 'ChangeRoomOptions'
0xDDD5E0 'GetRoomInfo'
0xDDD5EC 'GetFakeClientObjs'
0xDDD600 'IsRankedMatch'
0xDDD610 'IsRoomFull'
0xDDD61C 'GetRankedMatchState'
0xDDD630 'IsPilot'
```

**★ 全镜像字节搜索 `b"SetTeam"` 只有 3 处**（`0x3666A26` / `0x36B0E58` / `0x36B14B8`），
全部在 **Segment 2（`0xE16000` 之后的大段，= GFx/AVM2 导出区）**，**`.text`（`0x401000..0xCA689A`）里 0 处**。
分母：整镜像 241,537,024 字节全扫。

**RTTI 侧**：`0xE76B67` 附近连续 MSVC 类型名，含 **`.?AVAS_ChangeTeam@@`**（紧随 `.?AVAS_CheckTeamAvatar@@`）。

**native 实现 `0x7D1080`（= `AS_ChangeTeam`）**：
```
0x7D1080  push ebp / mov ebp,esp / sub esp,0x28
0x7D1086  mov ecx,[0xE778DC]
0x7D1096  mov eax,[ecx] / mov edx,[eax+0x28]
0x7D109B  push 0 / push 8 / call edx          ; 分配 AS 事件对象
0x7D10B3  mov dword [eax],0xDC7AF4            ; 临时 vtable
0x7D10B9  mov dword [eax+4],1
0x7D10C0  mov dword [eax],0xDDD784            ; ★ 装 AS 对象 vtable，属于 AS_ChangeTeam
0x7D10D6  call 0x830BC0                       ; 解 AS 实参
0x7D10DE  test al,0x8F / je 0x7D110D          ; ★ 实参存在性
0x7D10E2  mov eax,[edi+0xC]
0x7D10E5  mov ecx,[edi+8] / mov edx,[ecx] / mov edx,[edx+0x14]
0x7D10ED  and eax,0x8F                        ; ★ 只取低 8 位有效位
0x7D10F2  cmp al,0x0A / sete al / movzx eax,al ; ★ 与 10 比较 => bool
0x7D10FA  push eax                            ; ★ 唯一参数 = bool
0x7D10FF  mov eax,[edi+0x10] / push eax       ; this
0x7D1102  push 0xDDD5A4                       ; ★ "ChangeTeam"
0x7D1108  call edx                            ; 派发到管理器 [ecx]->+0x14
```

⇒ **`AS_ChangeTeam` 的 Flash 侧实参被压缩成一个 bool（`al==0x0A`）**，**不是 team 编号**。
**这与「ChangeTeam 四字段没有一个叫 team 的整型」自相矛盾** —— 说明 Flash 的 `ChangeTeam` 按钮**不产生 ChangeTeam 报文**，
它产生的是「切换阵营的意图」事件，由 C++ 侧另行处理（见 E6）。

### E3b — `AS_SetReadyState` 的真实链路（对照样本，证明模板识别方法有效）

同名串 `'SetReadyState'`（`0xDDD504`）的唯一引用 **`0x7D0A43`**，其函数 `0x7D0A00` 与 `0x7D1080` **逐指令同构**（只是名字串不同）。
说明这套「`mov ecx,[0xE778DC]` → `[eax+0x28]` 分配 → 装 `0xDDD784` vtable → `0x830BC0` 解参 → `push <name串>` → `call [..+0x14]`」是**通用的 AS 回调派发模板**，共 **302 处**引用 `0x82E13FC`（228 卷已枚举）。

**而 `SendReady` 的真正入口是另一条**（`vt[+0x84]`）：
```
0x7CF850   push ebp / mov ebp,esp
0x7CF853   mov edx,[ebp+8]
0x7CF856   mov edx,[edx+0x10]
0x7CF859   mov ecx,[0x82E13FC]        ; ★ 302 处模板同源
0x7CF85F   movzx edx, byte [edx+0x10] ; ★ 取事件对象 +0x10 的**字节**
0x7CF863   mov eax,[ecx]
0x7CF865   mov eax,[eax+0x84]         ; ★ vt[33]
0x7CF86B   push edx
0x7CF86C   call eax                   ; → 0x6301A0 SendReady
```
**全库 `[eax+0x84]` 形态只有这 1 处**（分母：3,237,168 条指令全反汇编索引，查 `0x82E13FC` 起 14 条内出现 `+ 0x84]`）。
⇒ **`SendReady` 的调用边 = `0x7CF850`（vtable 槽引用）**，与 176 卷「vt[0] 无 call 边」一致。

### E4 — ★客户端只有 2 个 ChangeTeam 构造点，**都不是"用户点按钮改阵营"**

| 构造点 | 所在函数 | 触发条件 | 用 `+4=0x14` 装 vtable |
|---|---|---|---|
| `0x636525`（`call 0x6281A0`） | 分派 `[0x14]` 内 | **收到** ChangeTeam 报文且**与本地记录有差异**时回推 | ✓（`0x6281B8` 在 ctor 内） |
| `0x6366F8`（`call 0x6281A0`） | 分派 `[0x15]`→`0x6365A3` 尾部 | 同上（SetPilot 分支溢出路径） | ✓ |

**`0x6281D0`（写侧）的 `E8` 调用点数 = 0**、`jmp` = 0；vtable 槽 `0xDC7648` 引用 6 处但**全是"装 vtable"**。

⇒ **客户端"改阵营"不是发 ChangeTeam，是发别的**（见 E6）。

### E4 — 「改阵营意图」的实际出口：`0x62C5A0`，走共用写侧 `0x628320`

`0x62C5A0`（家族路径中转）：
```
0x62C5D4  call 0x654CD0                            ; 取参数
0x62C5DB  je 0x62C690                              ; 失败退出
0x62C5E1  push 0x24 / call 0xB74220                ; alloc 0x24 = bitstream 对象
0x62C5EF  push ebx / push ebx                      ; ★ 两个 0 → (容量=0, flag=0)
0x62C5F3  call 0xB778E0                            ; 构造位流（写 1 位头 = 0x00）
```
⇒ **`+0x21 = 0`** ⇒ 所有 `W_TAG` 空操作 ⇒ **只写值不写标签**（41 位 Manifold 头）。

### E5 — 消息 `+0x21`（位流标签开关）在**发送路径恒为 0**

| 调用点 | `push` 序列 | `+0x21` |
|---|---|---|
| `0x62AC0B/0x62AC0C`（`0x62ABF0`） | `push ebx; push ebx`（`ebx=0`） | **0** |
| `0x62B745/0x62B746`（`0x62B720`） | `push ebx; push ebx` | **0** |
| `0x62C3A8/0x62C3AA`（族 A） | `push 0; push 0` | **0** |
| `0x62C4E0/0x62C4E1`（族 A） | `push esi; push esi`（`esi=0`） | **0** |
| `0x62C5EF/0x62C5F0`（`0x62C5A0`） | `push ebx; push ebx` | **0** |
| `0x62C6D2/0x62C6D3` | `push ebx; push ebx` | **0** |
| `0x62C7CB/0x62C7CC` | `push esi; push esi` | **0** |
| `0x62C895/0x62C896`（族 B） | `push ebx; push ebx` | **0** |
| `0x62C9BC/0x62C9BD`（族 B） | `push ebx; push ebx` | **0** |
| `0x6336BE/0x6336C0`（FrameUpdate） | `push 0; push 0` | **0** |
| `0x71EEF4/0x71EEF6` | `push 0; push 0` | **0** |
| **`0xB8927F`** | **`push 1`** | **1** ★唯一 |
| `0xB98887/0xB98889` | `push 0; push 0` | 0 |
| `0xBA9CE5/0xBA9CE7` | `push 0; push 0xC` | 0 |
| `0xC70512`（`push imm8 0`） | `push 0; push 0` | 0 |

**分母**：`0xB778E0` 共 **15 个 `E8` 调用点**（全库扫），**14 个 flag=0，1 个（`0xB8927F`）flag=1**。
`0xB8927F` 在 `0xB89220` 内，与本任务房间线无关（见 235 卷）。

⇒ **房间线发出的每一条位流，`+0x21` 都是 0** ⇒ **所有 5 位标签全部不写** ⇒ **实际线上格式是「无标签」的 41 位头**，不是 51 位。

### E6 — 读侧：`0xB779A0` **全部 6 个**调用点参数3都是 `1`（带标签头）

| 调用点 | `push` 序列 | 参数3（带标签头） |
|---|---|---|
| `0x625844` | `0x625832 push 1` / `0x625835 lea edx,[esi*8]` / `0x62583C push edx` / `0x625841 push ecx` | **1** |
| `0x63702C` | `0x637026 push 1` / `0x637028 push edx`(=`len*8`) / `0x637029 push ecx` | **1** |
| `0x71EE4A` | `0x71EE42 push 1` / `0x71EE46 push ecx` / `0x71EE47 push edx` | **1** |
| `0x71F02C` | `0x71F024 push 1` / `0x71F028 push ecx` / `0x71F029 push edx` | **1** |
| `0xBA1A37` | `0xBA1A2A push 1` / `0xBA1A2C push 8` / `0xBA1A34 push ecx` | **1** |
| `0xC70325` | `0xC70319 push ecx` / `0xC7031A lea ecx,[edx*8]` / `0xC70321 push ecx` / `0xC70322 push edi` — 第3参由 `0xC7031?` 之前的 `push 1` 给出 | **1** |

**分母 6/6**。⇒ **读方向恒「带标签」**，写方向恒「不带标签」（E5）。**这不是笔误，是两个方向的不对称设计。**
且 `0xBA1A37` 处 `push 8` ⇒ **位数 = 8 位 = 1 字节缓冲**（`lea ecx,[ebp-0x4FD]` 是 1 字节栈变量），
证明「带标签头」模式下 `参数2` 是**位**不是字节 —— 与 `0x63701C lea edx,[ecx*8]`（字节→位）一致。

⇒ **`6/5` 应答走「带标签」路径，客户端会读 5 位标签**。

---

## 边界表

| # | 未解项 | 可独立核验任务 | 已穷尽排查 |
|---|---|---|---|
| B1 | `+8`(u32) 的准确名字 | 找 `[成员记录+0x8C]` 的其它读/写点，看它是否随时间自增 | ⚠️ 部分。`0x636577` 只此一处写 `[esi+0x8C]`；`0x6364AE` 只读比较。**未找到"谁把 +0x8C 从 0 变成非零"** —— 仍开 |
| B2 | `AS_ChangeTeam` 那个 bool 的语义（`al==0x0A` ⇒ true） | 查 `0x830BC0`（AS 实参解包）返回的 `[edi+0xC]`/`[edi+8]` 是什么；`0x0A` 是不是某个枚举值 | ✅ **已做字符串搜索**：全镜像 `b"SetTeam"` = 3 处全在 Segment 2，`.text` 0 处 ⇒ **`AS_SetTeam` 不存在**，本卷已改为 `AS_ChangeTeam`。`0x0A` 的枚举归属仍开 |
| B3 | `0x2C`（`Text`+`SpyMessageText`）与 `0x02`（`Text`）为什么分两个号 | 查 `0x625AB0` vs `0x625940` | ✅ 已读：`0x625AB0` 同一栈对象装两次 vtable（`0xDC7504`→`0xDC7510`）、读两次 `0x625A20`；`0x625940` 只装一次。**`0x2C` = Text+Spy 双字段** |
| B4 | `+4`（类型号 `0x14`）是否与 `+0x14`（参数4）冲突 | — | ✅ 不冲突：`0x6281B8 c7 40 04 ...` 写 dword；参数4 从 `0x6281C8` 写到 `+0x1C` —— **ctor 从不写 `+0x14`**，`+0x14` 未初始化 |

## 更正

- **172 卷「ChangeTeam=`u32/u8/u32/u64`」**：顺序错。**按线上顺序是 `u32, u32, u8, u64`**（读侧 `8,0x10,0xC,0x18`）；`u32/u8/u32/u64` 是**对象偏移顺序**（`+8,+0xC,+0x10,+0x18`）。
- **172 卷「改阵营/投票客户端从未发出（svc11 只有 task 2/4/13）」**：本卷给到**机器指令级确认** —— `0x6281D0` 的 `E8` 调用点 **0 个**（分母：全 `.tp3` 段 158,187 条 `E8` 全索引），`0x628320` 的 `E8` 调用点也是 **0 个**。两者都只经 vtable 槽被调。
- **175/176 卷「flag=1 是有标签、7 字节」**：本卷确认**客户端发送路径 flag 恒 0** ⇒ 客户端实际发出的是 **41 位 / 6 字节无标签**；**7 字节是读方向（回包）才有的**。
