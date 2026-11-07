# 135 · AS 注册链三层归属闭合：3 个容器类 + 44 个分批函数 + GFx 转发器表

> ★★ **137 卷更正（三条）**：①「**更正 130：`0x5D39E0`=`AS_SetRecommendedSetting`**」**作废** —— 真名是 **`AS_UILog`**，因此 **130 卷「`0x1D39E0` 是 UI 事件派发器」是对的**；②`0x5D3CB0` 的真名是 **`AS_SetVideoSetting`**（不是 `AS_IIPS_Response`）；③「`AS_UILog`/`AS_QuickMatch`/`AS_setdvar` 三者同址 `0x8435E0` 空实现」**作废** —— 共享 `0x8435E0` 的 22 个对象名单见 137 §1.1（**`AS_UILog` 不在其中**，它是真实现）。根因：131 的名字列错位一格（137 §1.1）。

> 配套探讨：[135 探讨 · 判据窗口跨函数：一个假条目如何连锁制造两条假结论](135_AS注册链三层归属与GFx转发器表_探讨.md)
> 前序：131（806 描述符行定名）、132（829 vtable 对象）、133（838→828 注册器 + 816 短名）、134（828 重验 + UiCppMainMenu）
> 性质：**机制层收口** + **对 134 的两条实质性更正**。

---

## §0 八条结论

1. **三层归属闭合**。整条链是：
   `0x5ED010`（一次性 Scaleform/AS 初始化）→ **3 个容器主函数**（`0x5EBB00` / `0x5EBB90` / `0x5EBDD0`）→ **分批函数**（27 个分组，44 个被主函数直接调用）→ **828 个单名注册器**。
2. **三个 AS3 容器类名**（字符串池 `0xDC418C/0xDC41B4/0xDC41D4`，全镜像**各被引用恰好 1 次**）：
   `codo.common.CFunctionCommonContainer` / `codo.common.CFunctionContainer` / `codo.common.CFunctionInGameContainer`。
3. **注册机制 = AS3 侧"定义属性"**，不是 C 表：注册器尾段是
   `[[edi+8]]->vt[0x14]( [edi+0x10], "<短名>", &Value16, bool(( [edi+0xc] & 0x8F )==0x0A) )`，
   其中 `edi = &容器`、`esi = 全局 Scaleform 单例`。⇒ 133 的"表不存在"现在是**机制级解释**：名字→对象映射在 **AS3 对象内部**。
4. 容器对象本身是**反射取的 AS3 类**：容器构造器 `0x730690` 里调
   `0x830B00(global, "flash.utils.getDefinitionByName", this, &局部Value, 1)`（字符串 `0xDD6098`）。
5. ★★ **GFx 转发器 thunk 表**：`0x830AC0..0x830BC0` 共 **9 个 17 字节同形 thunk**，一律
   `push ebp; mov ebp,esp; mov ecx,[ecx+0xC]; mov eax,[ecx]; mov eax,[eax+slot]; pop ebp; jmp eax`，
   slot ∈ `{0xB0,0xB4,0xB8,0xBC,0xC0,0xC4,0xC8,0xE4,0xE8}`。
   ⇒ **`0x830BC0` = slot 0xC0 的转发器**（133/134 遗留的"`0x830BC0` 容器语义未解"当场闭合）；
   `0x830B00` = slot 0xE4 的转发器（`getDefinitionByName` 走它）。
6. **分批函数有统一序言** `57 8b f8 56`（`push edi; mov edi,eax; push esi`），函数体 = N 组
   `push esi; call <注册器>; add esp,4`，尾 `ret` / `pop edi; ret`。⇒ **有一个机械可扫的族指纹**。
7. **0x5EBB90 体内 44 个不同的 `E8` 目标 = 44 个分批函数**；按注册器归属汇总：
   `0x5EBB90`→347、`0x5EBB00`→217、`0x5EBDD0`→94、`0x748A70`→28、`0x5ED010`→25、`0x748970`→11、`0x7489E0`→6、`0x748AE0`→5、`0x748CB0`→5、`0x748B90`→4。
   其中 `0x748xxx` 一族 = **第二注册站点（按 View 注册，非三个全局容器）**。
8. ★★ **更正 134 两条**：`0x6AEBD0` 是**分批函数**（体内 26 组 `push esi; call`，尾 `pop edi; ret`，长 0xEE），`0x728350` 是**一次性惰性初始化**（长 0x2D，体内无 vtable 写入）。**两者都不是注册器**。134 §⑤「2 个漏覆盖是过滤器 bug」**作废**——真因是 134 的判据窗口"体内前 0x300 字节"**跨进了下一个函数**。`tools/as_regfns_v2.json` 的 828 至少含 3 个非注册器（`0x6A7650`/`0x6AEBD0`/`0x728350`）⇒ **真注册器 ≤ 825**。

---

## §1 一次性初始化：`0x5ED010`

一个 `if(已初始化) return;` 的闸门函数，前后两条全局门：

```
0x005ED010  55            push ebp
0x005ED011  8bec          mov ebp,esp
0x005ED013  83ec14        sub esp,0x14
0x005ED016  53 56 57      push ebx / esi / edi
0x005ED019  e8e2431400    call 0x731400
0x005ED01E  e83d87fdff    call 0x5c5760
0x005ED023  686806dc00    push 0xdc0668    ; 'tencent_e3_loadout'
0x005ED028  e863211800    call 0x76f190    ; 查 dvar
0x005ED030  85c0 / 751e   test eax,eax / jne 0x5ed052
0x005ED034  6891e0da00    push 0xdae091    ; ← 空字符串哨兵(130 卷)
0x005ED039  6800010000    push 0x100
0x005ED03E  68d08cdb00    push 0xdb8cd0    ; '-1'
0x005ED043  686806dc00    push 0xdc0668    ; 'tencent_e3_loadout'
0x005ED048  e8133c1800    call 0x770c60    ; 建 dvar(name, "0x100 标志", "-1", 默认="")
...
0x005ED063  833da0e97a0c00  cmp dword ptr [0xc7ae9a0],0
0x005ED06A  c605874a2c0801  mov byte ptr [0x82c4a87],1
0x005ED071  0f85b4020000    jne 0x5ed32b   ; ← 门 1: 若 !=0 直接退出
0x005ED077  833d98bb770c00  cmp dword ptr [0xc77bb98],0
0x005ED07E  0f85a7020000    jne 0x5ed32b   ; ← 门 2: 若 !=0 直接退出
0x005ED084  8b156cea6507    mov edx,[0x765ea6c]
0x005ED0D4  b8dc42dc00      mov eax, 0xdc42dc   ; 'scaleform/default/codo.gfx'
0x005ED0E7  e8e4e8ffff      call 0x5eb9d0
0x005ED0EC  e82fe7ffff      call 0x5eb820
0x005ED0F1  8b0d98bb770c    mov ecx,[0xc77bb98]
0x005ED0FB  c745f808000000  mov dword ptr [ebp-8], 8
0x005ED102  8b11 / 8b928c000000 / ffd2
                           mov edx,[ecx] ; mov edx,[edx+0x8c] ; call edx   ; 全局单例 vt[0x8C](&{8,0})
0x005ED110  a198bb770c      mov eax,[0xc77bb98]
0x005ED116  33ff            xor edi,edi
0x005ED118  be5897e600      mov esi, 0xe69758
0x005ED11D  e87e421400      call 0x7313a0
0x005ED125  e866eaffff      call 0x5ebb90    ; ★ 主容器注册
...
```

三点：
- `[0xc77bb98]` = **Scaleform/AS 全局单例**（下文所有 `esi`）。
- 门是 `[0xc7ae9a0]` / `[0xc77bb98]` 两处**一次性**标志 ⇒ AS 注册只做一次。
- `0xdae091`（130 卷定的"空字符串哨兵"）在这里**有语义正常的调用者**：它是 `tencent_e3_loadout` 这个 dvar 的**默认值**（空串）。⇒ 130 的判据被一个真实调用点**独立复现**。

---

## §2 三个容器主函数

容器类名的三处引用（工具 `imm_ref_135.py`）：

```
imm32 0x00DC418C : 1 处
   0x005EBB12  mov edi,imm32    ctx: 56 57 bf 8c 41 dc 00 8d 75   ; 'codo.common.CFunctionCommonContainer'
imm32 0x00DC41B4 : 1 处
   0x005EBB9E  mov edi,imm32    ctx: 56 57 bf b4 41 dc 00 8d 75   ; 'codo.common.CFunctionContainer'
imm32 0x00DC41D4 : 1 处
   0x005EBDDE  mov edi,imm32    ctx: 56 57 bf d4 41 dc 00 8d 75   ; 'codo.common.CFunctionInGameContainer'
```

三个 `mov edi,<类名>` 正好落在三个函数入口 `0x5EBB00` / `0x5EBB90` / `0x5EBDD0` 内（`0x5EBB12`/`0x5EBB9E`/`0x5EBDDE` 距入口分别 `+0x12`/`+0x0E`/`+0x0E`）。主函数 `0x5EBB90` 的样本：

```
0x005EBB90  55 8bec 83ec20   push ebp; mov ebp,esp; sub esp,0x20
0x005EBB96  a198bb770c       mov eax,[0xc77bb98]        ; eax = 全局单例 → 后面所有分批函数拿它当 esi
0x005EBB9B  56 57            push esi; push edi
0x005EBB9D  bfb441dc00       mov edi, 0xdc41b4          ; ★ 容器类名 = 'codo.common.CFunctionContainer'
0x005EBBA2  8d75e0           lea esi,[ebp-0x20]         ; esi = 局部(&容器)
0x005EBBA5  e8e64a1400       call 0x730690              ; 构造/取容器对象(见 §3)
0x005EBBAA  8bc6             mov eax,esi                ; eax = &容器
0x005EBBAC  8b3598bb770c     mov esi,[0xc77bb98]
0x005EBBB2  e8b97d0b00       call 0x6a3970              ; 分批函数 #1
0x005EBBC0  e8bbc71300       call 0x728380              ; 分批函数 #2
0x005EBBCE  e8dd87feff       call 0x5d43b0              ; ★ 分批函数 = "房间/对战"组(38 个注册器)
0x005EBBDC  e8cf640a00       call 0x6920b0
...                          (区间内共 44 个不同 E8 目标)
```

**每个分批函数拿到的入参**：`eax = &容器`（⇒ 其体内 `mov edi,eax` 得到 §0-3 的 `edi`）、`esi = 全局单例`（⇒ 它 `push esi` 传给每个注册器）。

---

## §3 容器构造器 `0x730690`：`flash.utils.getDefinitionByName`

```
0x00730690  55 8bec 83ec20   push ebp; mov ebp,esp; sub esp,0x20
0x00730696  83caff / 33c9    or edx,-1 ; xor ecx,ecx
0x0073069B  8955e0           mov [ebp-0x20],edx        ; ┐局部 Value(20B):
0x0073069E  8955e4           mov [ebp-0x1c],edx        ; │  dword0/1 = -1,-1
0x007306A1  894de8           mov [ebp-0x18],ecx        ; │  dword2   = 0
0x007306A4  c745ec06000000   mov [ebp-0x14],6          ; │  dword3   = 6
0x007306AB  897df0           mov [ebp-0x10],edi        ; ┘  dword4   = <类名字符串>
0x007306AE  8916             mov [esi],edx             ; ┐this(16B) 清零:
0x007306B0  895604           mov [esi+4],edx           ; │  [0]=-1 [4]=-1 [8]=0 [0xC]=0
0x007306B3  894e08           mov [esi+8],ecx           ; │
0x007306B6  894e0c           mov [esi+0xc],ecx         ; ┘
0x007306B9  3bc1 / 7416      cmp eax,ecx ; je 0x7306d3   ; 全局单例为 0 则跳过
0x007306BD  6a01             push 1
0x007306BF  8d4de0           lea ecx,[ebp-0x20]
0x007306C2  51               push ecx                   ; arg4 = &局部Value
0x007306C3  56               push esi                   ; arg3 = this(&容器)
0x007306C4  689860dd00       push 0xdd6098             ; ★ 'flash.utils.getDefinitionByName'
0x007306C9  8bc8             mov ecx,eax               ; this = 全局单例
0x007306CB  e830041000       call 0x830b00             ; = [[global+0xC]]->vt[0xE4]
0x007306ED  8bc6 / 8be5 5d c3   mov eax,esi ; leave ; ret
```

★★ **这是整条链上最关键的一环**：容器对象**不是 C++ 静态对象**，是通过 AS3 反射
`flash.utils.getDefinitionByName("codo.common.CFunctionContainer")` 在**已加载的 SWF codo.gfx 里**取到的 AS3 类对象。所以"名字→对象表"根本无处可寻，因为**表在 SWF/AS3 运行时里**，C++ 侧只有"往那个类对象上挂属性"的动作。

---

## §4 注册器体内逐字节（`0x64F620` = 挂 `JoinRoom`）

```
0x0064F620  55 8bec 83ec28      push ebp; mov ebp,esp; sub esp,0x28
0x0064F626  8b0ddc78e700        mov ecx,[0xe778dc]         ; 分配器单例
0x0064F62C  83c8ff              or eax,-1
0x0064F630/33/36  8945dc/e0 8945e0   mov [ebp-0x24],eax ; mov [ebp-0x20],eax   ; Value16 头
0x0064F636  8b01                mov eax,[ecx]
0x0064F638  8b5028              mov edx,[eax+0x28]         ; 分配器 vt[0x28]
0x0064F63B  6a00 6a08           push 0 ; push 8
0x0064F63F/46  mov [ebp-0x1c],0 ; mov [ebp-0x18],0
0x0064F64D  ffd2                call edx                   ; alloc(0, 8) -> 8 字节对象
0x0064F653  c700f47adc00        mov dword ptr [eax], 0xdc7af4   ; 父类 vptr(Scaleform::GFx::FunctionHandler)
0x0064F659  c7400401000000      mov dword ptr [eax+4], 1
0x0064F660  c7001089dc00        mov dword ptr [eax], 0xdc8910   ; ★ 自身 vtable(=某个 AS_* 对象)
0x0064F666  8bf0                mov esi,eax
0x0064F66C  8b4d08              mov ecx,[ebp+8]            ; ecx = 全局单例(分批函数 push 的 esi)
0x0064F66F  6a00 56 8d45dc 50    push 0 ; push esi ; lea eax,[ebp-0x24] ; push eax
0x0064F676  e845151e00          call 0x830bc0              ; ★ = [[global+0xC]]->vt[0xC0](&Value16, obj, 0)
0x0064F67B  8b45e8              mov eax,[ebp-0x18]
0x0064F67E  a88f / 742b         test al,0x8f ; je 0x64f6ad   ; ★ 门: 不合规则跳过"挂名"
0x0064F682  8b470c              mov eax,[edi+0xc]
0x0064F685  8b4f08              mov ecx,[edi+8]            ; [[edi+8]] = 容器对象的 vtable 宿主
0x0064F688  8b11 / 8b5214       mov edx,[ecx] ; mov edx,[edx+0x14]
0x0064F68D  258f000000 / 3c0a  and eax,0x8f ; cmp al,0xa
0x0064F694  0f94c0 0fb6c0       sete al ; movzx eax,al           ; bool = ((容器.flags & 0x8F)==0x0A)
0x0064F69A  50                  push eax                   ; arg4
0x0064F69B  8d45dc 50           lea eax,[ebp-0x24]; push eax   ; arg3 = &Value16
0x0064F69F  8b4710              mov eax,[edi+0x10]
0x0064F6A2  683027dc00          push 0xdc2730              ; ★ arg2 = 'JoinRoom'
0x0064F6A7  50                  push eax                   ; arg1 = 容器.成员
0x0064F6A8  ffd2                call edx                   ; ★ 定义属性
0x0064F6AD  85f6 / 740a / 8bce e83877 1d00   test esi,esi ; je ; mov ecx,esi ; call 0x826df0  ; 释放 8B 对象
0x0064F6BB  c1e806 a801 7412    shr eax,6 ; test al,1 ; je 0x64f6d4      ; 尾清理
0x0064F6D2  ffd0                call eax
0x0064F6D4  5e 8be5 5d c3        pop esi ; leave ; ret
```

⇒ 一个注册器 = **造一个 8 字节 handler 对象 + 往容器上定义名为 `<短名>` 的属性**。

★ 两个此前未解释的点现在闭合：
- `test al,0x8f / je` 与 `and eax,0x8f / cmp al,0xa` 是**同一个掩码** `0x8F`：前者判断 `0x830BC0` 的产物是否合法（不合法就整段跳过），后者判断**容器标志位**是否等于 `0x0A`，把结果当 bool 传给"定义属性"。⇒ 134 §边界 1「`test al,0x8F; cmp al,0x0A` 语义未定」现为：**掩码 0x8F 的标志位比较**（`0x0A` 时的确切含义仍未定）。
- 短名字符串**不带 `AS_` 前缀**（`JoinRoom`），而 RTTI 类名带（`AS_JoinRoom`）；但 `0x650FA0` 压的是 `AS_ShowShoutcastAndUpdateBypassMouseInput`（**带前缀**）。⇒ 前缀有无**不统一**，两种都出现过。

---

## §5 GFx 转发器 thunk 表

工具 `gfx_fwd_scan.py` 扫同形 17 字节模板，全镜像 **9 个**，全部集中在 `0x830AC0..0x830BC0`：

| thunk | 转发到 |
|---|---|
| `0x830AC0` | `[global+0xC]->vt[0xC8]` |
| `0x830AE0` | `vt[0xC4]` |
| `0x830B00` | `vt[0xE4]` ← `getDefinitionByName` |
| `0x830B20` | `vt[0xE8]` |
| `0x830B40` | `vt[0xB0]` |
| `0x830B60` | `vt[0xB4]` |
| `0x830B80` | `vt[0xB8]` |
| `0x830BA0` | `vt[0xBC]` |
| `0x830BC0` | `vt[0xC0]` ← **注册器用它** |

每个 thunk 的字节（`0x830BC0`）：

```
0x00830BC0  55            push ebp
0x00830BC1  8bec          mov ebp,esp
0x00830BC3  8b490c        mov ecx, dword ptr [ecx+0xc]
0x00830BC6  8b01          mov eax, dword ptr [ecx]
0x00830BC8  8b80c0000000  mov eax, dword ptr [eax+0xc0]
0x00830BCE  5d            pop ebp
0x00830BCF  ffe0          jmp eax
```

⇒ **133/134 遗留的"`0x830BC0` 的容器语义未解"就此闭合**：它**不是**容器，是 **Scaleform 全局单例的 `[+0xC]` 子对象的 vtable 转发器（slot 0xC0）**。整个 `0x830Axx..0x830Cxx` 是**一张机器生成的转发器表**（一处 17 字节模板 × N 个 slot）。

---

## §6 三层归属统计（工具 `as_batch_135.py`）

| 上层函数 | 注册器数 | 性质 |
|---|---|---|
| `0x5EBB90` | 347 | `CFunctionContainer` 主函数 |
| `0x5EBB00` | 217 | `CFunctionCommonContainer` |
| `0x5EBDD0` | 94 | `CFunctionInGameContainer` |
| `0x748A70` | 28 | **View 注册站点**（→ `0x73DF20` = `UiCppMatchSelectView::Init`） |
| `0x5ED010` | 25 | 一次性初始化（直接调的注册器） |
| `0x748970` | 11 | View 站点 |
| `0x7489E0` | 6 | View 站点 |
| `0x748AE0` | 5 | View 站点 |
| `0x748CB0` | 5 | View 站点 |
| `0x748B90` | 4 | View 站点 |

★★ 两条独立证据互证同一数字 **28**：132 卷从 RTTI 拿到 `?N@??Init@UiCppMatchSelectView@@` 局域类 **28 个**；本卷从调用图拿到 `0x73DF20`（分批函数）**28 个注册器**。**RTTI 名 ⊗ 调用次数 = 28**。

★ **0x5CEB10**（217 个注册器）与 133 §七记录的"`0x5CEB10` 调 220 次"对账：**220 = 217 个注册器 + 3 个非注册器调用**（构造/工具调用）。133 的观测数被分解。

★ **第二注册站点 `0x748xxx`** 的存在解释了"通用动作名在多个 View 上重复出现"：View 各自向**自己的**容器注册（不是向三个全局容器）。134 关于"无任何双注册"的结论只对 **vtable 写入**成立（每个注册器只写一个 vtable），与"同一个短名被多个注册器压入"**不矛盾**。

---

## §7 修正 134 的两条

### 7.1 `0x6AEBD0` 是分批函数，不是注册器

134 §⑤ 说 `0x6AEBD0`（头 `57 8b f8`）是 `AS_GetHeadSeason` 的注册器、被过滤器误杀。实测全函数：

```
0x006AEBD0  57 8bf8 56   push edi; mov edi,eax; push esi     ; ← 分批函数序言
0x006AEBD4  e8e7000000   call 0x6aecc0   ;  push esi; call … ×26, 每个后接 add esp,4
...          (26 组 push esi / call / add esp,4)
0x006AECBD  5f           pop edi
0x006AECBE  c3           ret                                     ; 总长 0xEE
```

⇒ 它是**分批函数**（26 个注册器 `0x6AECC0..0x6AFF80`），尾 `pop edi; ret`（不是注册器的 `ret`/`c2 04 00`）。
**134 在它体内"前 0x300 字节"看到的 vtable 写入，属于紧随其后的第一个注册器 `0x6AECC0`，不是它自己。**

### 7.2 `0x728350` 是一次性惰性初始化，不是注册器

```
0x00728350  53            push ebx
0x00728351  bb01000000    mov ebx, 1
0x00728356  841d44867b0e  test byte ptr [0xe7b8644], bl
0x0072835C  7518          jne 0x728376                  ; 已做过 -> 直接返回
0x0072835E  091d44867b0e  or dword ptr [0xe7b8644], ebx  ; 置"已做"标志
0x00728364  e8c75dd8ff    call 0x4ae130
0x00728369  68005dca00    push 0xca5d00
0x0072836E  e811655100    call 0xc3e884
0x00728376  881d09637b0e  mov byte ptr [0xe7b6309], bl
0x0072837C  5b            pop ebx
0x0072837D  c20400        ret 4
```

全函数 **0x2D 字节，无任何 vtable 写入**。134 看到的 vtable 写在**下一个函数 `0x728380`**（真正的分批函数，头也是 `57 8bf8 56`，体内 28 组 `push esi; call`）。

### 7.3 根因：判据窗口跨进了下一个函数

134 的过滤判据之一是「**体内前 0x300 字节**有 `mov [reg],<vtable>`」。对 `0x6AEBD0`（长 0xEE）与 `0x728350`（长 0x2D），这个窗口都**越过了本函数末尾、伸进下一个函数**，于是把邻居的 vtable 写当成了自己的。⇒ 与 134 §四 自己在 `0x830BC0` 上总结的教训**同族**（"`.tp3` 里向上找最近 `cc cc` 会撞进大函数内部"），但 134 只在**向上**方向设了防，**向下**方向没有。

### 7.4 对计数的影响（诚实修正）

`tools/as_regfns_v2.json`（828 条）中含至少 **3 个非注册器**：
`0x6A7650`（0x1D 字节，`call 0x4f7150/0x4ad5f0`，无 vtable 写、无短名）、`0x6AEBD0`（分批函数）、`0x728350`（惰性初始化）。
⇒ **真注册器 ≤ 825**；134 的"828 覆盖 828/828"应读作"828 条候选覆盖 828 个对象，其中 ≥3 条候选不是注册器"。
（对照：`0x650FA0` = `AS_ShowShoutcastAndUpdateBypassMouseInput`、`0x6AF380` = `AS_TryToUpdatePrimaryWeaponCountToPartyMember`——本工具报"无短名"的同批里，这两个**是真注册器**，说明本工具的短名过滤器偏严，不能单独用来判定。）

---

## §8 名字池：`0xDC26C0` 起的连续 AS 名块

```
0x00DC26C0  peakerChannel          …IsInGlobalChannel / IsInBigSpeakerChannel
0x00DC26FC  SendGlobalChatBrokenTLog
0x00DC2718  CancelList
0x00DC2724  CreateRoom
0x00DC2730  JoinRoom
0x00DC273C  QuickMatch
0x00DC2748  EnableRoomListEvent
0x00DC275C  EnableQuickMatchEvent
0x00DC2774  IsLogOnLobby
0x00DC2784  TencentGetAASRecord
0x00DC2798  UILog
0x00DC27A0  SetRecommendedSetting
0x00DC27B8  SetTierSetting
0x00DC27C8  SetVideoSetting
0x00DC27D8  IIPS_Response
0x00DC27E8  JumpGame
0x00DC27F4  GetGroupCounts
0x00DC2804  GetLockedMapsFromPublisher
0x00DC2820  GetServerTime
0x00DC2830  buy_token_cp / buy_token_cc / token / spend_token / timeLeft / round
0x00DC2878  gametypeID / cardIconURL / cardBackgroundURL / cardNameplateColor
0x00DC28B8  cardFrameURL / statusIconIndex / statusIcon / rankIcon / xpgained / chestID
0x00DC2908  isSpecialItem / ui_top_players_reward_items / rewards
0x00DC293C  scr_hostage_roundlimit / spy_top%d_info / %d|%d|%d|%d|%d
0x00DC2974  confirmCorpse / nickname / role / kills2 / ui_spy_winner / winner / isSpecta…
```

⇒ **`0xDC26C0..0xDC2820` 是 AS 短名的连续块，与 131 卷的表逐项吻合**（131 的"事件/接口名"就是这里、这些字符串）。块之后立刻转入**战斗模式 UI 字段名**（`buy_token_*`/`xpgained`/`spy_top%d_info`/`scr_hostage_roundlimit`）⇒ 字符串池按"用途段"排列，AS 名段是一条可界定的条带。

三个容器类名所在的 `0xDC418C..0xDC41D4` 是**另一个条带**（紧邻 `IME.gfx`、`scaleform/default/codo.gfx`、`$font_2..$font_6`、`$IMECandidateListFont`）⇒ **Scaleform 资源/类名条带**。

---

## §9 诚实边界

1. `0x0A`（掩码 0x8F 后）的**确切语义**未定；只确定它是"容器标志位比较 → bool 参数"。
2. GFx 转发器表里每个 slot 对应的**具体 GFx/C++ 方法名**未定（运行时 vtable，无静态立即数）；只按 slot 偏移命名。
3. `0x748xxx`（View 注册站点）的**入口函数**未定（`0x748A70` 等来自 `entry_of` 近似；"28"这个数字由 RTTI 独立确证，但 `0x748A70` 这个 VA 是弱证据）。
4. `0x730690` 局部 Value 的第 4 个 dword（=6）语义未定；`0xDA0E18`（'1'）等相邻串未逐一归类。
5. 「真注册器 ≤ 825」是**下界口径**：只证明"828 里 ≥3 个不是"，未穷举重算到精确值。
6. 分批函数**数量**在两种口径下不同（按 `cc cc` 前导序言扫 = 15；按调用图分组 = 27；按 `0x5EBB90` 体内直调 = 44）——因为"分批函数"存在**嵌套**（分批函数调用分批函数），三种口径量的不是同一个集合。**这不是矛盾，但报告时必须说明口径**。

---

## §10 方法论（本卷新增）

1. ★★ **判据窗口必须双向设防**：134 学会了"向上找 `cc cc` 会撞进数据区"，但"体内前 N 字节"这个**向下**窗口同样会跨函数。**凡是"N 字节窗口"，先问"如果窗口比函数长会怎样"。**
2. ★★ **"找不到表"的终极答案常常是"表在另一台运行时里"**：名字→对象映射不在 C++ 侧，而在 **AS3/SWF 运行时**（`getDefinitionByName` 取类 + 定义属性）。⇒ "静态面无表"≠"无映射"。
3. ★ **一个假条目会连锁制造假结论**：`0x6AEBD0`/`0x728350` 被当成注册器后，134 不得不发明"MSVC 叶子函数省略 `push ebp`"来解释它们——**解释越费劲，越可能前提就是错的**。
4. ★ **同形字节模板 = 族指纹**：`57 8b f8 56`（分批函数）、17 字节转发器、0xB9 注册器模板——**先找"一族共用的字节形状"，再谈语义**。
5. ★ **数量差异先问口径**：15 / 27 / 44 三个数并存不是错误，是三个集合（含嵌套）。**报数必须报定义**。
6. ★ **交叉确认要用不同证据类型**：28 这个数由 RTTI 名（数据）与调用次数（代码）两路独立给出 ⇒ 强度高于任一路。

---

## §11 工具

| 工具 | 用途 |
|---|---|
| `tools/gfx_fwd_scan.py` | 扫 GFx 转发器 thunk 表（17 字节同形模板） |
| `tools/str_range_135.py` | 打印 VA 区间内的可打印字符串 |
| `tools/imm_ref_135.py` | 找 imm32(=VA) 的代码引用点并按操作码分类 |
| `tools/calls_in_range_135.py` | 列 VA 区间内所有 `E8` 直接调用目标 |
| `tools/as_func_135b.py` | 从函数中部反推入口并整段反汇编 |
| `tools/as_chain_135.py` | 找目标 VA 的 `E8` 调用者 + 窗口反汇编 |
| `tools/as_batch_135.py` | 注册器 → 分批函数 → 上层函数 三层归属 |
| `tools/as_batch_prologue_135.py` | 按序言 `57 8b f8 56` 普查分批函数族 |
| `tools/as_reg_vfy_135.py` | 重验 828 条候选（体内是否有短名 push） |
| `tools/as_show_135.py` | 批量反汇编 VA 列表（到首 ret） |
