# 199 · 十个回调槽的整表重定位，与"op=8 就是执行地址零"

## 一、范围

本报告学习 `EngineBindings.cpp` 1228–1407 行。

## 二、那个"每个移植者和每个审计者都走过去"的数组初始化器

### 2.1 症状

```text
四个具名偏移（0xAF320..0xAF334）早就移植到本 build 的 0xAF3xx，
而喂给同一块的十对没有 —— 所以循环往 0x96DF0..0x96E1C 写了十个指针，
【out.exe 上没有任何东西读它们】
    （.text 的位移扫描：那十个偏移里九个【零】个消费者，0xAF350 有 48 个）
【并让引擎真正读的每一个槽保持零】。
```

### 2.2 崩溃形态

```text
sub_40AB30 在 0x0040AD1F 通过 `mov edx,[ecx+0xAF324]; push eax; call edx` 到达回调，
【没有 null 检查】—— 所以一个零槽【会被调用】，
而见证器报 `code=0xC0000005 op=8 target=0x00000000`。
```

**`op=8` 就是"CPU 试图【执行】地址零"** —— 这是 §193 里 `operation` 三值中的 `8 = execute`。

### 2.3 为什么恰恰不是被故意置空的那个

> **只有 `0xAF32C` 是被守卫的**（`0x0040AE28` 的 `test eax,eax; je`），**所以本项目刻意置空的那一个槽从来不是崩的那个。**

**"我们小心处理的那个不是坏的，坏的是我们没在意的"** —— 这是很典型的一类。

### 2.4 为什么整表都被走过去

> **这是【一个数组初始化器】，这就是为什么每个移植者和每个审计者都走过去了。**

**数组初始化器会被"看过"但不会被"逐个检查"** —— 因为它的形态暗示着"这是数据不是逻辑"。

## 三、两次安装点的对照

```text
3.3.3.3 0x00445924   mov [edi+0x15DE7C], 0x004453E0
out.exe 0x00454750   mov [ebx+0x180C24], 0x00453420
```

> **两份 build 是同一个函数，逐指令匹配、同样顺序，只在被重定位的全局上不同。**
>
> **而第二份同样的块在 0x00448140 / 0x004565E0。**

### 3.1 外层结构的两个偏移

```text
每个偏移在这里是 `outer - 0xC7088`（3.3.3.3）与 `outer - 0xD1900`（out.exe）
    —— 正是本文件存储注释已经说过的两个 delta
外层表本身平移了平坦的 0x22DA8
而 (0x22DA8 - 0xD1900 + 0xC7088) 正好是 ServerCharacterInfoBaseOffset 已携带的 +0x18530
```

**验算**：

```text
0x22DA8 - 0xD1900 + 0xC7088
= 0x22DA8 - 0xD1900 = -0xAEB58
-0xAEB58 + 0xC7088 = 0x18530  ✓
```

> **两次独立测量对十个槽全部落在同一个 delta 上。**

## 四、三条互不共享步骤的额外确认

### 4.1 第 6、7 项落到 `HunkAllocXAnimRva`

```text
entries 6 and 7 come out at RVA 0x368220, which is HunkAllocXAnimRva
    —— 已经因为另一条推导被绑定并加了前缀守卫
```

**表里的两个槽都指向同一个函数** —— 而那个函数是独立绑定的。

### 4.2 get-DObj 项落到 `0x053600`

```text
它的函数体是 `movzx eax, word [eax*2 + 0x7855720]`
对照 3.3.3.3 的 `[eax*2 + 0x2EF4858]`
    —— 同一个 client DObj map，sub_53DF40 在 0x0053DFC9 索引它
       以找到它交给 BG_UpdatePlayerDObj 的 DObj
```

**RVA 与函数体同时吻合** —— 这是最强的确认。

### 4.3 消费者计数逐个匹配

```text
2/1/1/2/3/1/1/1 对 0x96DF4..0x96E1C 与 0xAF324..0xAF34C
```

**每一槽被引用的次数在两个 build 上相同** —— 这是一条**结构等价**证据，而不是地址证据。

## 五、十对 (偏移, RVA) 的完整表

| 偏移 | RVA | 语义 |
|---|---:|---|
| 0xAF320 | 0x053430 | — |
| 0xAF324 | 0x053420 | ← 崩溃点，无守卫 |
| 0xAF328 | 0x0535B0 | CreateDObj |
| 0xAF32C | 0x0534A0 | AppendWeaponModel（**唯一有守卫**） |
| 0xAF330 | 0x26BF60 | FreeDObj |
| 0xAF334 | 0x053600 | GetDObj |
| 0xAF338 | **0x368220** | HunkAllocXAnim |
| 0xAF33C | **0x368220** | HunkAllocXAnim（同一函数） |
| 0xAF348 | 0x049030 | — |
| 0xAF34C | 0x048FF0 | — |

**注意 0xAF340 与 0xAF344 缺失** —— 表里有 10 项但偏移不连续。

## 六、两条 `static_assert` 把表与具名常量绑在一起

### 6.1 第一条

```cpp
static_assert(
    ServerCreateDObjCallbackOffset == ServerAnimationCallbackRvas[2].first &&
    ServerAppendWeaponModelCallbackOffset == ServerAnimationCallbackRvas[3].first &&
    ServerFreeDObjCallbackOffset == ServerAnimationCallbackRvas[4].first &&
    ServerGetDObjCallbackOffset == ServerAnimationCallbackRvas[5].first,
    "the stock callback table and the four adapter slots must name the same "
    "four offsets -- they were 0x96DF8..0x96E04 and 0xAF328..0xAF334 at once");
```

注释：

> **四个具名偏移和这张表是同样的四个槽，而它们【漂移分开了四个小节】而没有东西注意。把它们绑在一起，让下一次半边移植无法编译：**这是对着修好它的那个东西做 `==`，而不是一个每个更小值都满足的界。

**"对着修好它的那个东西做 `==`"** —— 与 §148 里 `19 + 18 == 37` 的 `==` 而非 `<=` 是同一条纪律。

### 6.2 第二条

```cpp
static_assert(
    ServerAnimationCallbackRvas[6].second == EngineBindings::HunkAllocXAnimRva &&
    ServerAnimationCallbackRvas[7].second == EngineBindings::HunkAllocXAnimRva,
    "out.exe's installer writes HunkAllocXAnim into both of these slots, and "
    "that binding is derived independently and prefix-guarded");
```

**两个槽都指向同一个函数，且那个函数的绑定来自独立推导并有前缀守卫** —— 所以这条断言是"两个独立来源的一致性检查"。

## 七、动画脚本表：`0x1A004 + 0x204 * movetype`

```cpp
NumberOfPlayerAnimationsOffset = 0x1A000
MaximumPlayerAnimations = 1024
AnimScriptStateTableOffset = 0x1A004
AnimScriptItemsStride = 0x204
AnimScriptMoveTypeCount = 47
```

### 7.1 两个 build 的逐指令对照

```text
3.3.3.3
    0x00409501  imul eax, eax, 204h
    0x00409508  lea  ebx, [eax+ecx+1A004h]   ecx = [0x07817B84]
    0x0040951E  sub  ebx, 5EBCh

out.exe
    0x00407C41  imul eax, eax, 204h
    0x00407C48  lea  esi, [eax+ecx+1A004h]   ecx = [0x0827F734]
    0x00407C5E  sub  esi, 5EBCh
```

**`0x1A004`、`0x204`、`47 = 0x5EBC/0x204` 全部沿用**。

### 7.2 动画全局对

```text
3.3.3.3  0x07817B80 / 0x07817B84
out.exe  0x0827F730 / 0x0827F734
```

注释：

> **第二个是 anim-script blob，第一个是 `sub_407E10` 在 `+0xAF350` 以步长 0x450 索引的 characterInfo 数组**（`0x00407E37..0x00407E43`）。
>
> **`0xAF350` 在 3.3.3.3 的 `.text` 里出现【零】次**，这就是为什么那一个是无歧义的。

**"在另一个 build 里零次出现"** 是非常强的判别证据。

### 7.3 两个全局持**同一个指针**

```text
CODOL 自己的加载器在 0x00445DAF 做 `mov esi, [0x7817B80]`
并调 BG_AnimParseAnimScript 0x00409040，它的第一个动作（0x0040905E）是
    mov [0x7817B84], esi
```

**所以"两名字一个指针"** —— 而 §184 里 §188 也提到"`initializeServerAnimation` 已经门控它们相等"。

## 八、条件槽：`0x2EC` + 8 字节步长

```cpp
CharacterInfoConditionBaseOffset   = 0x2EC    // 748
CharacterInfoMoveTypeConditionOffset = 0x304  // 772
CharacterInfoConditionCount = SvNativeAnimConditionCount
```

### 8.1 证据

```text
sub_407790（条件遍历器，BG_AnimScriptEvent 用它选动画）读
    *(DWORD*)(characterInfo + 8 * conditionIndex + 748)
以及它在 +752 的伙伴
所以本 build 的数组基是 748 = 0x2EC，步长 8 字节
```

**"+752 的伙伴"** = 类型表 —— 与 §`EngineBindings.hpp` 里 `dword_E608C8[2 * conditionIndex]` 一致。

### 8.2 第三个 `+100`

> 那是 3.3.3.3 的 +100，**而它正是已经为它的两个邻居测到的【同一个 +100】**：
> `CharacterInfoDObjDirtyOffset 560 → 660` 与 `CharacterInfoAnimTreeOffset 800 → 900`。
>
> **一个区域里三个字段同意这个位移，这才是使它成为一次重定位而不是巧合的东西。**

### 8.3 movetype 槽**按索引携带**

```text
0x2A0 - 0x288 = 24 = 条件槽 3
所以在这是 748 + 24 = 772 = 0x304
在另一个 build 上确立槽 3 的东西仍然成立；只有基址移动了
```

## 九、条件数量**是 19 不是 38**

```text
CODDIFF(1649370): THIS WAS 38 AND out.exe SAYS 19.
条件 NAME 表在 VA 0x00E60828 以 {0, 0xFFFFFFFF} 在索引 19 终止（VA 0x00E608C0），
而平行的条件 TYPE 表 sub_407790 索引为 dword_E608C8[2 * conditionIndex]
在 VA 0x00E608C8 晚一项开始，有它自己的十九项。
```

**数 38 的后果**：

> **让 `nonzero=N/38` 读到十九个真实条件槽【加上】十九个无关的 characterInfo（0x384..0x41C），所以它打印的数字是测量值加上它的邻居。**

**"测量值加上它的邻居"** —— 这是最隐蔽的一类错误：**数字看起来合理，只是包含了不该算的东西**。

## 十、`Scr_BeginLoadAnimTrees` 的六个偏移全部是 3.3.3.3 的

### 10.1 那个致命后果

```text
0x2B371B8 在 out.exe 里【零】个交叉引用 —— 引擎既不读也不写它 ——
所以 Scr_BeginLoadAnimTrees 的复现是在【没有任何东西看的地方】设置动画树加载状态，
而脚本解析的资产查找走了【LOAD 路径】而不是 register-for-precache 那条。
那就是到达资产数据库的内联 load pump 并【杀死进程】的东西。
```

**因果链**：

```text
偏移错误 → 状态写到没人看的地方 → 资产查找走错分支 → 进入 load pump → 进程死
```

### 10.2 真正的块

```text
454c21  mov byte_789C640, 1     loading      +0x118
454c28  mov dword_789C634, edi  count        +0x10C
454c2e  mov dword_789C534, edi  parsing      +0x00C
454c34  call sub_74CED0         Scr_CreateObject
454c4d  mov dword_789C528, eax  the object   +0x000
454c52  mov dword_789C52C, edi  secondary    +0x004
454c58  mov dword_789C680, edi  scratch      +0x158
```

**七个字段**（而常量只暴露了三个：`Object`、`Loading`、`Count`、`Parsing` 四个 + 隐含的）。

### 10.3 那句方法论

> **六个偏移里有两个恰好未变；结构体的头是稳定的而尾巴移动了。这正是为什么"因为看起来还对就移植一个偏移"不管用。**

## 十一、关键结论

1. **数组初始化器会被"看过"但不被"逐个检查"**，而十个槽全错就能造成"调用地址零"。
2. **`op=8` 直接说明是执行违例**，不是读/写。
3. **唯一有守卫的那个槽恰恰不是崩的那个** —— 我们小心的不是坏的。
4. **两次独立测量（外层表平移 + 结构右移）落在同一个 delta** 才算重定位。
5. **消费者计数逐槽相同**是结构等价证据，与地址证据互相独立。
6. **`0xAF350` 在 3.3.3.3 里零次出现** ⇒ 无歧义的判别。
7. **一个区域三个字段同意同一位移**才是重定位而不是巧合。
8. **数错条件数量会让统计"包含邻居"** —— 数字合理但含义错。
9. **"偏移写到没人看的地方"会导致走错分支并最终杀死进程**。

## 十二、未闭合点

- `0xAF340`/`0xAF344` 为什么不在十项表里未说明。
- `EngineBindings.cpp` 1407 行之后未读取。
