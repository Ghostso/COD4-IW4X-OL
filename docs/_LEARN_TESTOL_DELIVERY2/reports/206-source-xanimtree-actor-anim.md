# 206 · XAnimTree 的两端、演员击打动画的三个常量、动画脚本解析的双参数

## 一、范围

本报告学习 `EngineBindings.cpp` 2482–2661 行。

## 二、`clearNativeXAnimTree` 的循环体

```cpp
for (std::size_t guard{}; *children && guard < 64; ++guard)
{
    reinterpret_cast<void(__cdecl*)(void*, int)>(freeInfo)(tree, *children);
}
__except (EXCEPTION_EXECUTE_HANDLER) { }
```

### 2.1 每次先重读 `*children`

```text
循环条件 `*children` 是每次重新读的
```

因为 `freeInfo` 会**改 tree 的 children 字段**（§184 里 `XAnimFreeInfo` 最后 `mov word [edx+4], ax`）。

**所以这是"释放一个子节点、再看还剩几个"的循环**，而不是"遍历一个固定列表"。

### 2.2 空 `__except`

**与 §196 的 `serverDObjFreeAdapter` 相同的形态** —— 释放失败就算了。

## 三、`createNativeXAnimTree`：树头是 8 字节

```cpp
tree = allocator(sizeof(void*) * 2);       // 8 字节
if (!tree) return nullptr;
auto** fields = (void**)tree;
fields[0] = anims;
fields[1] = nullptr;
```

### 3.1 与 §205 的偏移对照

```text
+0  fields[0] = anims       ← §205 的 `+0 anims`
+4  fields[1] = nullptr     ← §205 的 `+4 children`
```

**`sizeof(void*)*2 = 8`** 因为本 build 是 x86（`sizeof(void*) == 4`）。

### 3.2 初始化值

```text
anims    = 传入的 anims
children = nullptr
```

即 `{anims, 0}` —— **正是 §184 说的"创建后的状态"**。

## 四、`setActorHitAnimation`：六个栈参数 + 三个魔数

### 4.1 完整调用

```asm
push 0
push 03F800000h      ; 1.0f
push 03E4CCCCDh      ; 0.2f
push 03F800000h      ; 1.0f
push 0
push dobj
mov ecx, node
xor eax, eax         ; EAX = 0
call function        ; module + 0x3891D0
add esp, 24          ; 六个栈参数
```

### 4.2 三个 float 常量

```text
0x3F800000 = 1.0f
0x3F800000 = 1.0f
0x3E4CCCCD = 0.2f
```

**注释里说的 "flags0 and 0.2s"** 对应：

```text
flags     = 0（两个）
weight    = 1.0f
reason    = 0.2s（秒）
```

而 §`sv_zm_presentation_mp.hpp` 里"rounded asset duration + 250ms settling allowance"、§205 里"0.2s"——**`0.2` 是那个混合时长**。

### 4.3 六个栈参数的顺序

```text
[esp+0]  dobj        （第一个）
[esp+4]  0
[esp+8]  1.0f
[esp+12] 0.2f
[esp+16] 1.0f
[esp+20] 0
```

**`xor eax, eax`** 是第七个入口（EAX = 0）。

### 4.4 notifyType 的两难

注释给了这条**很具体的取舍**：

```text
CODDIFF(0x7869E0,0x786860): collision-only server poses use notifyType0.
Client notifyType2 appends to 0x81AA7B0; this server has no client drain,
so copying the render-side flag grows that queue indefinitely.
```

> **碰撞专用的服务端姿势用 `notifyType0`。客户端 `notifyType2` 会追加到 `0x81AA7B0`；本服务器没有客户端排空，所以照抄渲染侧的标志会让那个队列无限增长。**

**"没有消费者就必须不产生"** —— 因此选 0 而不是 2，尽管客户端用 2。

而：

> **独立序列化的客户端动画/FX 事件仍然保持 type2。**

**两类事件用两个不同值** —— 因为一个有消费者一个没有。

## 五、`advanceActorHitAnimation`：EDI + 一个栈参数

```asm
push seconds
mov edi, dobj
call function         ; module + 0x388200
add esp, 4
```

**`dobj` 在 EDI、`seconds`（float）在栈**。

注释：

> `5401DA/549932` 用 EDI=DObj 与栈上的历经秒数调 `788200`；**它拥有原生时钟/混合**。

**"它拥有原生时钟"** —— 所以服务端只提供 `seconds`，时钟在原生侧。

## 六、`invokeBGAnimParseAnimScript`：**两个栈参数不是一**

### 6.1 那次"直接杀死进程"

```text
CODDIFF(1649370): 两个栈参数不是一个。
sub_407530 两个都载入 —— `mov eax,[ebp+arg_0]` 取计数，
`mov ebx,[ebp+arg_4]` 紧随其后 —— 而 arg_4 不是装饰：
它直接进入脚本解析器在 0x407663 的 ECX（`mov ecx, ebx; call sub_4064A0`）。
只压计数让那个 ECX 读我们栈上 `count` 上面的东西，
而它【直接杀死进程】而不是抛出任何这个 __try 能抓住的东西。
```

**这是最严重的一类**：

```text
参数少压 → ECX 读到栈垃圾 → 用作指针 → 直接死进程，__try 抓不住
```

**"__try 抓不住"** 的原因注释没写，但结合 §192/§193 的讨论，可能是**栈破坏后异常发生在 SEH 帧之外**，或者**是访问违例但 SEH 链已被破坏**。

### 6.2 实际的调用

```asm
push 0          ; arg_4 = 0（CL_ParseGamestate 在 0x454CD6 传的）
push count      ; arg_0 = &animationCount
mov ecx, loadAnims
mov esi, animScriptData
mov eax, function
call eax
add esp, 8      ; 两个栈参数
```

**四个入口**：

```text
ECX = loadAnims
ESI = animScriptData
栈  = &count / 0
```

## 七、`invokeScrBeginLoadAnimTrees`：五个状态字段

### 7.1 三个先写

```text
state[ScrAnimLoadingOffset      = 0x118] = 1     （u8）
state[ScrAnimTreeCountOffset    = 0x10C] = 0     （u32）
state[ScrAnimTreeParsingOffset  = 0x00C] = 0     （u32）
```

**与 §199 里 `CL_ParseGamestate` 在 `0x454C1A` 写的三个字段一致**：

```text
454c21  mov byte_789C640, 1     loading      +0x118
454c28  mov dword_789C634, edi  count        +0x10C
454c2e  mov dword_789C534, edi  parsing      +0x00C
```

### 7.2 调 `Scr_CreateObject`

```cpp
std::uint32_t object{};
auto* variable = ((uint32_t*(__cdecl*)(uint32_t*))createObject)(&object);
if (!variable || !object) return false;
variable[1] = 23;
variable[0] = 0;
```

**两个返回值**：函数返回的 `variable`（一个数组）与通过输出参数得到的 `object`。

`variable[1] = 23` —— **23 是什么**？注释没写。可能与 `SCR_*` 类型有关。

### 7.3 三个后写

```text
*(u32*)state                                  = object      （+0x000）
state[ScrSecondaryAnimTreeObjectOffset = 0x004] = 0
state[ScrAnimTreeScratchOffset        = 0x158] = 0
```

**五个字段全部**：

```text
+0x000  object
+0x004  secondary
+0x00C  parsing = 0
+0x10C  count = 0
+0x118  loading = 1
+0x158  scratch = 0
```

**六个，不是五个。**

与 §199 里那七条反汇编 **逐项对应** ✓

## 八、`invokeBGLoadAnimTrees`：ESI + 一个栈参数

```asm
push mapName
mov esi, gameType
mov eax, function
call eax
add esp, 4
```

**`gameType` 在 ESI、`mapName` 在栈** —— 与 §202 里 `invokeLevelZoneLoad` 形状完全相同（ECX vs ESI 的差别）。

**这两个函数签名相似，但寄存器不同（ECX vs ESI）** —— 所以不能互相复制。

## 九、本组新增的四种 ABI

| 适配器 | 参数位置 |
|---|---|
| `setActorHitAnimation` | **EAX + ECX + 栈 6** |
| `advanceActorHitAnimation` | **EDI + 栈 1** |
| `invokeBGAnimParseAnimScript` | **ECX + ESI + 栈 2** |
| `invokeScrBeginLoadAnimTrees` | 栈 1（普通 cdecl） |
| `invokeBGLoadAnimTrees` | **ESI + 栈 1** |

**到 §206 为止共 26 个适配器**。

## 十、关键结论

1. **`clearNativeXAnimTree` 每次重读 `*children`**，因为 `freeInfo` 会改它。
2. **树头 8 字节 = `{anims, children}`**，与"创建后状态"一致。
3. **`setActorHitAnimation` 的 `0.2f` 是混合时长**，三个 float 常量各有语义。
4. **`notifyType` 选 0 而不是 2，因为本服务器没有消费者** —— 没有消费者就必须不产生。
5. **参数少压让 ECX 读栈垃圾，直接杀死进程且 `__try` 抓不住**。
6. **`invokeLevelZoneLoad`（ECX）与 `invokeBGLoadAnimTrees`（ESI）签名相似但寄存器不同**。

## 十一、未闭合点

- `variable[1] = 23` 的语义未说明。
- `EngineBindings.cpp` 2661 行之后未读取。
