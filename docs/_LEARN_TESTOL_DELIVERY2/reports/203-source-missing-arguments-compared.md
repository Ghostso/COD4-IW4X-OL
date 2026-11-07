# 203 · 两次"少压一个参数"，与一次完整的自我更正

## 一、范围

本报告学习 `EngineBindings.cpp` 1945–2124 行。

## 二、`invokeSVUnlinkEntity` / `invokeBGFindAnims`：同一种最简适配器

```cpp
__asm { mov eax, entity; mov edx, function; call edx; }
```

**EAX 传参** —— 与 `invokeSVLinkEntity`、`invokeServerDObjGet` 同族。

`invokeBGFindAnims` 的 `animTreeContext` 同样在 EAX。

## 三、`invokeWorldCharacterModelResolve`：**未调用**的调用约定记录

### 3.1 那段声明

```cpp
// CODDIFF(character_customization): UNCALLED on OLfinal. This is the
// 3.3.3.3 thunk for WorldCharacterModelResolve 0x0040C980, and that
// function is absent from OLfinal entirely (§16a), so
// resolveCharacterModelNames() will need a different thunk against
// sub_61B6C0 rather than this one. Kept because it is the precise record
// of the calling convention the 3.3.3.3 path used -- faction, selection
// ids, female, colour in, a sparse 11-slot model-id list out -- which is
// what the OLfinal replacement has to reproduce the MEANING of.
```

### 3.2 契约

```text
输入  faction / selectionIds / female / color
输出  modelIds（稀疏的 11 槽模型 id 列表）
```

**`sparse 11-slot`** —— 与 §202 的"十一个 char*"一致。

### 3.3 汇编

```asm
push color
push female
push selectionIds
push modelIds
mov eax, faction
mov edx, function
call edx
add esp, 16
```

**五个入口**：EAX + 四个栈。

**压栈顺序与声明相反**：

```text
push color        （第四个）
push female       （第三个）
push selectionIds （第二个）
push modelIds     （第一个）
```

⇒ 第一个栈参数在最低地址 ✓，`add esp, 16` = 四个参数 ✓。

### 3.4 "保留因为它是精确记录"

> **保留它是因为它是 3.3.3.3 那条路径所用调用约定的精确记录**……**而那是 OLfinal 替代品必须复现其【含义】的东西。**

**保留一段不会执行的代码**，理由是它把"含义"固定下来 —— 这与 §183 里"保留了绑定但无人调用"是同一种做法。

## 四、`invokeBGUpdatePlayerDObj`：三个栈参数

### 4.1 游戏自己的调用点

```text
sub_53DF40 @0x53DFF5:
    movzx ecx, cl        ; ECX = 一个 BOOL —— 当 [esi+194h] == [eax+3BB0h] 且类型不是 2 时为真
                         ;   （即"这是我们自己的客户端"）
                         ;   【零是 dedicated 服务器所意味的】
    mov edx, [ebp+arg_0] ; EDX = 来自调用者的一个指针
    push edi             ; a3 = characterInfo（base +0xAF350，步长 0x450）
    push edx             ; a2 = esi+0xF4（entityState）
    push eax             ; a1 = 该实体【已存在的 DObj】，或 0
    call sub_40AB30 / add esp, 0Ch      ; 三个栈参数，调用者清理
```

### 4.2 与 3.3.3.3 的差别

```text
3.3.3.3 的 BG_UpdatePlayerDObj 0x0040B700 读【四】个栈参数：[ebp+8]、+0Ch、+10h、+14h
而 out.exe 的 sub_40AB30 只读【三】个。
第四个（3.3.3.3 的 attachIgnoreCollision）在这里没了，
所以补它的 `push 0` 被去掉，清理从 16 变成 12。
```

**与 §182 里 `BG_InitWeaponStrings` 相反**：那里本 build **多**了一个参数，这里**少**了一个。

**"自我平衡而非有害"**：

> 它自我平衡而不是有害，因为这是调用者清理的调用而这段代码清理了它压的；**但它仍然描述的是错误的函数**。

**这是"少压/多压但清理匹配"的典型**：不会崩，只是参数错。

### 4.3 那段完整的自我更正（本组最有价值的部分）

原注释：

> `a1` 被读作"一个 ANIM TABLE 条目，**不是**已存在的 DObj"，并得出结论说这个约定在不做模型工作的情况下不可移植。

更正：

> `a1` 是 `unk_77E9720 + idx*0xD8`，其中 `idx = word[entityNumber*2 + 0x7855720]` —— **而 `0x7855720` 是 client DObj MAP，正是 out.exe 自己的 get-DObj 回调 `sub_453600` 在 `0x00453606` 索引的同一张表。**
>
> **它就是已存在的 DObj，而这正是这段代码一直在传的东西。**

### 4.4 那两个"看起来可疑但正确"的值

> **ECX 0 和 EDX -1 也是对的**：`sub_40AB30` 在 `0x0040AC0A` 把 EDX 与 -1 比较并走一个**有记录的跳过分支**，**所以 -1 是一个被处理的哨兵而不是错误指针。**

### 4.5 结论

> **每一个参数都是正确的，而崩溃在完全不同的地方——见上面的回调表。**

**"每个参数都对，崩溃在别处"** —— 而"别处"就是 §199 里那十个未移植的回调槽。

**这条注释的价值**：它明确否定了"参数有问题"这个方向，**防止下一个人再往这个方向查**。

## 五、`invokeBGPlayerAnimation`：`__usercall` 的完整记录

### 5.1 IDA 的输出

```text
int __usercall sub_40A960@<eax>(_DWORD *a1@<edi>, int a2, int a3, int a4)
```

**EDI + 三个栈参数，返回值在 EAX。**

### 5.2 游戏自己的调用点

```text
sub_53DD40 @0x53DE89:
    push eax   ; eax = 0     -> a4
    push ebx   ; esi+0xF4    -> a3，实体
    push edx                 -> a2
    call sub_40A960 / add esp, 0Ch
```

### 5.3 原来少了第三个

```text
// This pushed only TWO and cleaned 8, so the engine read a4 out of ol-mod's own
// stack frame -- the same defect that made SVTrace return garbage.
```

**"引擎从 ol-mod 自己的栈帧里读 a4"** —— 与 `DB_FindXAssetHeader` 少参数完全同族。

> **第三个参数现在按游戏传的 0 压入，而清理匹配。**

### 5.4 `a2` 保持 -1

> **`a2` 保持 -1：游戏在那里传 `edx`，而 `edx` 的所有者在该调用点未确立。**

**"未能确立的就保持怀疑值"** —— 而 -1 在这里是哨兵（见上）。

### 5.5 与 `invokeBGUpdatePlayerDObj` 并排复核

> **与 `invokeBGUpdatePlayerDObj` 一起对着 out.exe 重新读过，而这个是【对的】。**
> `sub_40A960` 读 `[ebp+8]`、`+0Ch`、`+10h` 而不再往后，**所以本 build 上计数也是三**，
> 而 out.exe 自己的调用点 `0x0053DE89` 压 `eax`=0、`ebx`=entityState、`edx` 按那个顺序，然后 `add esp, 0Ch`。

**EDI 是 characterInfo**：

```text
0x0053DE1F 推导为 `lea edi, [ecx + eax + 0xAF350]`
    —— 同一个 per-client 数组、同一个偏移
```

## 六、两次"参数个数错"的对照

| | `BG_UpdatePlayerDObj` | `BG_PlayerAnimation` | `BG_InitWeaponStrings` |
|---|---|---|---|
| 3.3.3.3 | 4 | — | 0 |
| 本 build | **3**（少一个） | **3** | **1**（多一个） |
| 症状 | 自我平衡，无害 | 引擎从本侧栈帧读 | 引擎从本侧栈帧读 |
| 修法 | 去掉 `push 0`，清理 16→12 | 补 `push 0`，清理 8→12 | 声明补参数 |

**三种情况都发生了**：少一个、多一个、声明少一个。

**共同点**：**清理与压入匹配时不会崩，只是参数错**。

## 七、关键结论

1. **保留不执行的代码是为了固定"含义"**（`invokeWorldCharacterModelResolve`）。
2. **参数少压/多压但清理匹配时不会崩**，只是读到栈上残留 —— 三个函数各中一次。
3. **"每个参数都对，崩溃在别处"要写进注释**，否则下一个人会再往那个方向查。
4. **`EDX = -1` 是有记录的哨兵**，不是错误指针。
5. **未能确立来源的参数保持怀疑值**（`a2 = -1`）。
6. **`__usercall@<eax>(a1@<edi>, ...)` 是 IDA 对"寄存器 + 栈混合"的标准输出**。

## 八、未闭合点

- `a2` 的 `edx` 所有者仍未确立。
- `invokeBGPlayerAnimation` 的完整实现（2124 行之后）未读取。
- `EngineBindings.cpp` 剩余约 910 KB 未读取。
