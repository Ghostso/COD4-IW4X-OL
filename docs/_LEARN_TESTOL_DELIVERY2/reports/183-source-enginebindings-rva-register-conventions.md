# 183 · RVA 表：三处"少一个参数"与一处"绑错函数"

## 一、范围

本报告学习 `EngineBindings.hpp` 419–658 行。

## 二、`CL_GetConfigString` 的索引在 ESI

```cpp
// CODDIFF(1649370): CL_GetConfigString takes its index in ESI on this build,
// not ECX, so it has NO C calling convention and is stored as a raw pointer.
// 3.3.3.3's sub_4F9850 opens `cmp ecx, 0x1B92`;
// out.exe's sub_514880 opens `cmp esi, 0x31D9` and indexes as [esi + 0x77D8250].
// Declared __fastcall the index went to ECX and the callee read whatever the
// caller had left in ESI, so EVERY index returned the same unrelated string.
```

### 2.1 两个上限

```text
3.3.3.3  0x1B92 = 7058
out.exe  0x31D9 = 12761
```

**这个 `0x31D9` 与之前 `DisconnectWitness` 里 `cmp ebx, 0x31D9` 是同一个数** —— 同一个 configstring 表的边界在两处出现。

### 2.2 症状

`__fastcall` 把索引放 ECX，而被调用者读 ESI ⇒ **每个索引都返回同一个无关字符串**。

这与 `BG_PlayerStateToEntityState`（参数在 ECX vs 栈）、`sub_619E90`（EAX vs 栈）构成**同一族错误**：**寄存器约定猜错**。

## 三、`BG_InitWeaponStrings` 多了一个参数

```cpp
// CODDIFF(1649370): BG_InitWeaponStrings GAINED a parameter. 3.3.3.3's reads
// no stack slot at all; out.exe's sub_42FE80 reads [ebp+8], and both of the
// game's own callers -- CL_ParseGamestate at 0x454B3F and the lazy Com_Frame
// rebuild at 0x4FE1AC -- `push 1` before calling it.
// Declared with no parameters it read that flag off the caller's stack.

using WeaponRegistryInitialize = std::int32_t(__cdecl *)(std::int32_t completeRegistration);
```

**两个独立调用点都 `push 1`** —— 这是参数存在的证据。

**注意与 `DB_FindXAssetHeader` 的对照**：

| | 参数个数 | 后果 |
|---|---|---|
| `DB_FindXAssetHeader` | 我们**少**传一个 | 读栈上残留，随机决定是否创建默认占位符 |
| `BG_InitWeaponStrings` | 我们**少**声明一个 | 读栈上残留当 flag |

**同一族：少参数不崩，只读错**。

## 四、`Scr_PrecacheAnimTrees` 绑错了函数

```cpp
// CODDIFF(1649370): this was bound to sub_74AAF0, which is the INNER per-tree
// worker, not Scr_PrecacheAnimTrees. sub_74AAF0's only caller is sub_74AF50:
//     for (i = 1; i <= dword_789C634[a1]; ++i) sub_74AAF0(i, a2, a1);
// and CL_ParseGamestate calls THAT one, with the anim user in EDI and the
// allocator on the stack:
//     454cef  mov edi, [eax+0AF314h]
//     454cf5  push edx
//     454cf6  call sub_74AF50
// Bound to the worker and called with two cdecl arguments, the loop never ran
// and the worker read a third argument nobody pushed.
```

### 4.1 三层错误叠加

1. **绑到了内层 worker** 而不是外层函数；
2. **外层函数的循环因此从未跑过**（因为根本没调外层）；
3. **worker 读了一个没人压的第三个参数**。

### 4.2 证据形态

`sub_74AAF0(i, a2, a1)` 的调用者只有 `sub_74AF50`，而 `CL_ParseGamestate` 调的是 `sub_74AF50`，且参数布局是 **EDI = anim user + 栈 = allocator**（自定义 ABI）。

## 五、`AnglesToQuaternion` 与 `AnglesToAxis` 的**三处注释**

同一个事实被写了三遍：

```cpp
// NOT AnglesToAxis, whatever it used to be called here. sub_7853E0 reads three
// angles through ESI and writes FOUR floats through EDX; 3.3.3.3's nine-float
// AnglesToAxis 0x0062C1A0 has no counterpart on this build. Kept bound and
// guarded, called by nothing. Section 73f.
static constexpr std::size_t AnglesToQuaternionRva = 0x3853E0;

// AngleVectors ... The counterpart of 3.3.3.3's AnglesToAxis 0x0062C1A0 ...
// does not exist on this build; this is what does ...
static constexpr std::size_t AngleVectorsRva = 0x367890;

// AnglesToQuaternionRva 0x3853E0 ABOVE IS NOT AnglesToAxis. sub_7853E0 reads
// its angles through ESI, writes FOUR floats through EDX, and is an
// angles-to-QUATERNION. See section 73f.
```

**"Kept bound and guarded, called by nothing"** —— 保留了绑定但无人调用，因为删掉会让下一个人重新踩。

## 六、图像尺寸的本地覆盖

```cpp
static constexpr std::uint32_t ExpectedTimestamp = 0x6096930A;
// LOCAL OVERRIDE (olmod-local, 2026-10-03): the distributed client here is
// codoMP_client_shipRetail.exe SHA256 3699...B537, whose PE header reports
// SizeOfImage 0x0E659000 instead of 0x0E5D6000. Every ExpectedRVA below was
// re-read from that image's RUNTIME memory and every sampled prefix matched
// byte-for-byte ... so the only mismatch is this header field.
static constexpr std::size_t ExpectedImageSize = 0x0E659000;
```

**只有 SizeOfImage 不同，其余逐字节相同** —— 而这句话背后是"五个函数的前缀都核过"。

`SHA256` 完整写出，所以这个覆盖是可复核的。

## 七、两个 DObj 表：一个指针映射，一个直接索引

```cpp
// CODREF(bg_update_player_dobj): the SECOND entity-to-DObj table. One
// 0xCC-stride pool at VA 0x02E8E850 is reached through two different maps:
// ServerDObjGet VA 0x0059E570 divides a gentity POINTER down to an index
// and reads VA 0x02E8D050, while the callback this project installs at
// animBase+0x96E04 (RVA 0x0455D0) indexes VA 0x02EF4858 by entityState.number directly.
// BG_SetLerpFrameAnimation VA 0x00409BF0 resolves its DObj through that
// callback and BAILS at 0x00409C2E when it returns null - so a player
// absent from THIS table never has an animation set at all, however
// healthy the other table looks.
```

### 7.1 两个映射的差别

```text
ServerDObjMap (0x02E8D050)：gentity 指针 → 除下来得索引
ServerAnimDObjMap (0x02EF4858)：entityState.number 直接索引
```

**两个表指向同一个 0xCC 步长的池**，但**索引方式不同**。

### 7.2 后果

> **玩家不在【这个】表里就永远不会有动画设置**，**无论另一个表看起来多健康**。

这是一条很具体的陷阱：**检查错的那个表会得出"一切正常"**。

## 八、playerState 自己的访问器对

```cpp
// CODREF(playerstate_accessor): THE PLAYERSTATE CARRIES ITS OWN ACCESSOR PAIR,
// keyed on two DIFFERENT cookies from the same CryptGenRandom pool. The engine's
// playerState initializer sub_5BEB50 ... sets it up per state:
//     mov edx, dword_E60B74      ; setKey
//     lea eax, [edi+ebx+20h]     ; SET slot  = playerState + 0x20
//     lea ecx, [edi+ebx+24h]     ; GET slot  = playerState + 0x24
//     mov edx, dword_E60B78      ; getKey
//     call sub_403C70
// and PmoveSingle decodes the GET slot with exactly that second cookie.
```

**这解释了之前报告里"复制 playerState 会毁掉指针"的机制**：

- SET 槽在 `+0x20`、GET 槽在 `+0x24`；
- 两个 cookie 来自同一个 `CryptGenRandom` 池但**不同**；
- `sub_5BEB50` **每个状态初始化时**设置它们。

**所以 cookie 是全局的（`dword_E60B74/78`），而槽位是实例局部的**。复制实例不改变槽位偏移，**但 `sub_403C70` 建立的编码包含槽位地址**——这就是 `rebindNativePlayerStateAccessors` 要做的事。

### 8.1 与 lerp frame 访问器对的对照

之前报告里：

```text
SET 存在 +0x1C，以 +0x20 的地址为键
GET 存在 +0x20，以 +0x1C 的地址为键
```

而这里是：

```text
SET 槽 = playerState + 0x20
GET 槽 = playerState + 0x24
```

**两对访问器、两组偏移、都做交叉键控**。这是同一个模式在结构的不同部位出现两次。

## 九、XAnimFreeInfo 与 XAnimClearTree 的区别

```text
BO1 的 XAnimClearTree 只是：
    if (tree->children) { XAnimFreeInfo(tree, tree->children); assert(!tree->children); }
CODOL 的是 VA 0x006497C0：索引 56 字节节点池（VA 0x0374DB08），
    递归 children（0x00649879）与 siblings（0x00649813），
    把每个节点还给池，最后
    mov edx,[ebp+8] / mov word [edx+4], ax   （0x006498B2）
    所以树自己的 children 字段归 0。
```

结论：

> **把树恢复到它【创建后】的状态——`{anims, 0}`——没有节点泄漏**，而**把目标权重清零做不到这一点**。

即：**两种"清空"语义不同**，一个复位结构，一个只复位权重。

## 十、关键结论

1. **寄存器约定猜错有四种表现**（ECX/ESI、EAX/栈、参数个数、绑错函数），共同点是**不崩、只读错**。
2. **`0x31D9` 这个 configstring 上限在两个不相关的函数里出现**，可以互相校验。
3. **"保留了绑定但无人调用"是防止重踩的手段**。
4. **两个表指向同一个池但索引方式不同** ⇒ 检查错的那个会得出"一切正常"。
5. **playerState 与 lerp frame 各有一对交叉键控的访问器**，是同一模式在结构不同部位出现两次。
6. **"清空"有"复位结构"与"复位权重"两种**，前者无泄漏。

## 十一、未闭合点

- `ExpectedImageSize` 的本地覆盖仍待上游修正（`0x0E5D6000`）。
- `ServerAnimDObjMap` 的两个字是否对活玩家都已填充是 `TODO(CODOL)`，仅诊断。
- `EngineBindings.hpp` 658 行之后的声明未读取。
