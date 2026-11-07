# 198 · 玻璃片上限的推导、DObj 偏移、共享动画时钟的冻结

## 一、范围

本报告学习 `EngineBindings.cpp` 1048–1228 行。

## 二、`MaximumFxGlassPieceLimit` **不是自由常量**

### 2.1 三条精确关系（37 份 fastfile 实测）

```text
pieceWordCount == ceil(pieceLimit / 32)     37/37    可用性位集
pieceLimit     == initialPieceCount + 1024  27/27    ← 关键的那条
geometryLimit  == 8 * pieceLimit            37/37
```

**在有玻璃的 27 份地图上全部成立**（其余十份全零，`mp_rust_long` 是其中之一）。

### 2.2 结论

> 第二条意味着 **`MaximumFxGlassPieceLimit` 不是一个自由常量**，就像 §59b 的 `lastChanged` 宽度不是一样：**地图编译器把片数组的大小设成初始片数加上为打碎玻璃产生的碎片预留的【固定 1024】**，**而 1024 就是 `SvGlassPieceCount`** —— 与 out.exe 自己的稀疏列表读取器硬编码的终止符同一个数（`sub_447500 @0x447527`：`i = BITS(11); 1024 ends it`）。

> **所以在下面的 initialPieceCount 检查之下，`pieceLimit <= 2048` 是【跟随】出来的。它不是合理性猜测；它正是另一个检查允许的最大值**，这就是为什么 `static_assert` 把两者绑在一起，而不是留两个数字各自漂移。

### 2.3 观测到的最大值

```text
definitionCount   41    mp_terminal_cls
pieceLimit        1903  mp_conflict
initialPieceCount 879   mp_conflict
cellCount         203   mp_battlecity
```

> **1903 是这个界的 93%，879 是 `SvGlassPieceCount` 的 86%，所以两个都没有多少余量了——如果哪天有地图在这里被拒，这些是应当先打印的数字。**

`definitionCount` 的上限 1024 **故意放松**（观测值只有 41）—— 引 §51h："不要收紧一个（没有关系支撑的）"。

## 三、动画树上下文与句柄：**相邻但不同**

```cpp
AnimTreeContextOffset = 0xACE70
AnimTreeHandleOffset  = 0xACE64      // 12 字节之前
```

### 3.1 反汇编

```text
454c63  mov eax, dword_827F730
454c68  add eax, 0ACE70h
454c77  call sub_404D80
```
`sub_404D80` 从那里填 `a1+4`、`a1+8`、`a1+12`、`a1+16`。

**句柄**：

```text
v1 = *((_DWORD *)dword_827F734 + 177049);   // +0xACE64
*((_DWORD *)dword_827F734 + 26624) = *v1;   // +0x1A000
```

### 3.2 那次"检查了一个没人写的字"

> **检查上下文槽来判断"动画树在不在"，是检查一个没有任何东西写的字。**

### 3.3 那条 `static_assert`

```cpp
static_assert(
    AnimTreeContextOffset + 4 * sizeof(uint32_t) <= ServerCharacterInfoBaseOffset,
    "the anim tree handle and context must not run into the derived "
    "characterInfo array inside the shared anim-condition storage");
```

注释：

> **两者都是同一个已安装 anim-condition 块里的偏移，而且**没有一个是本项目能选的**：引擎在 `+0xAF350` 推导 characterInfo 数组、在 `+0xACE64/+0xACE70` 读动画树，**不管我们做什么**。
>
> **在 3.3.3.3 上数组坐在动画树【下面】；在这个 build 上它坐在【上面】**，所以断言写成本 build 地址实际延伸的方向。**两种情况下要紧的只是两者不重叠。**

## 四、`CharacterInfoDObjDirtyOffset` 与 `AnimTreeOffset`：+100

### 4.1 两个旧值都是 3.3.3.3 的

```cpp
// CODDIFF(1649370): BOTH OF THESE WERE 3.3.3.3's AND BOTH ARE +100 HERE, which is
// the same +0x64 shift sv_native_characterinfo_mp.cpp already derived for
// 0x1F4..0x208 -> 0x258..0x26C. These two sat in the same struct and were missed.
constexpr std::size_t CharacterInfoDObjDirtyOffset = 660;   // 旧 560
constexpr std::size_t CharacterInfoAnimTreeOffset  = 900;   // 旧 800
```

**`+100 = 0x64`** —— 与之前 §154 里"两者都移动了同样的 +0x1C"是同一种模式，只是数值不同。

### 4.2 反汇编证据

```text
sub_40AB30，a5 是 characterInfo：
    *(a5 + 660)  是 REBUILD 标志 —— 提前退出是
        if (*(a5 + 924) == v12 && !*(a5 + 660)) return 0;
        而函数在出去的路上用 v18[165] = 0 清它（165*4 = 660）
    *(a5 + 900)  是 ANIM TREE —— 它被装进 v46 并作为 DObj create 的第三个参数，
        即本项目自己的 serverDObjCreateAdapter 签名里的 `tree`
    560 和 800 在那个函数里【任何地方都不出现】
```

### 4.3 后果

> **第一个的后果不是外观问题**：把 dirty 标志写到 560 让引擎的 660 保持清零，**所以 `BG_UpdatePlayerDObj` 走了它的提前退出，并且【根本没有重建玩家的 DObj】。**

## 五、DObj 结构偏移的完整表

```text
DObjModelCountOffset      9
DOjbBoneCountOffset       10
DObjModelHideMaskOffset   12
DObjSkelStateOffset       20
DObjSkelStateSize         136
DOjbSkelPartBitsOffset    116
DObjSkelEpochOffset       148
DObjPoseMatricesOffset    152
DOjbBoneHideBitsOffset    160
DObjModelPointersOffset   192
DObjScaleOffset           200
DObjScaleComponentCount   3
```

### 5.1 `DObjScaleOffset = 200` 是**向量不是标量**

```text
CONFIRMED AGAINST out.exe, AND IT IS A VECTOR.
sub_781960 writes THREE floats here and nothing else touches them:
    *(float*)(dobj + 200) = 1.0;
    *(float*)(dobj + 204) = 1.0;
    *(float*)(dobj + 208) = 1.0;
    *(_DWORD*)(dobj + 212) = -1;
```

结论：

> **所以 200 是每轴模型缩放的 X 分量，不是标量，而对象延伸到 216** ——
> **这独立确认了 0xD8 步长，因为 0xCC 会把 208 和 212 都切掉。**
>
> **只写 X 而 Y 和 Z 保持原样是非均匀缩放**：**每个 modelScale 都是 1.0 时无害，而一旦有一个不是，模型就被拉伸。**

### 5.2 同一函数确认的另两处

```text
memset(dobj + 20, 0, 0x88)   = DObjSkelStateOffset 20 + DObjSkelStateSize 136
                             = 0x88 ✓
它跨 DObjBoneHideBitsOffset 清零 160..188
```

`0x88 = 136` ✓。

## 六、`NativeDObjModel` 是 44 字节

```cpp
struct NativeDObjModel {
    void* model{};              // 4
    uint16 boneName{};          // 2
    uint8 ignoreCollision{};    // 1
    uint8 pad{};                // 1
    array<byte, 36> reserved{}; // 36
};
static_assert(sizeof(NativeDObjModel) == 44);
```

**4 + 2 + 1 + 1 + 36 = 44** ✓。

前 8 字节是具名的，**其余 36 字节标为 `reserved`** —— 不假装知道。

## 七、XModel 偏移

```text
XModelNameOffset               0
XModelBoneCountOffset          4
XModelBoneClassificationOffset 60
XModelGeometryOffset           312
XModelGeometryEntrySize        28
XModelGeometryPointerOffset    24
```

**与 §143 里 `sv_forge_publish_mp` 的 XModel 表一致**（boneCount +4、boneNames +44 等），但这里是**读**用的偏移。

`XModelGeometryEntrySize = 28` 与 `XModelGeometryPointerOffset = 24` —— 每个几何条目 28 字节，指针在 +24。

## 八、共享动画时钟：整块被 +0x18530 重定位而**没有移植**

这是本组最重要的一段。

### 8.1 两个时钟在哪

```text
VA 0x00524931  mov [esi+0x000AE4C8], edi   ← 帧时间
VA 0x00524937  mov [esi+0x0015DE60], edi   ← 镜像到这里
VA 0x00524A43  mov ecx, [edi+0x3574]       ← 快照时间
VA 0x00524A49  mov [edi+0x0015DE64], ecx   ← 镜像到这里
```

注释：

> **通过 anim-condition 基址做位移扫描只找到【读】，因而得出"没有任何东西设置它们"** ——
> **CODOL 是通过块所嵌入的【外层结构】写它们的**，在 `lea eax, [ebx + 0xC7088]`（VA 0x00448351、0x005249C2），所以同样的字是 `outer + 0x15DE60` 与 `outer + 0x15DE64`。

**"扫描一个基址得出'没人写'是最容易犯的错误"** —— 与 §184 里"populator 在另一个基址所以被漏掉"是同一族。

### 8.2 两个时钟各自驱动什么

```text
+0x96DD8  截止时间
    BG_SetLerpFrameAnimation VA 0x00409D1B 写 characterInfo +0x338 = now + 400
    VA 0x00409E12 把余量读回为 `+0x338 - now`
    PmoveSingle VA 0x00419FD8/0x00419FF8 用 jge/jle 比较 playerState +0x33C

+0x96DDC  lerp 帧推进
    VA 0x0040A302 当它等于 lerpFrame +0x38 时【跳过整个推进】
    VA 0x0040A385 取 `now - lerpFrame+0x38` 作为经过的毫秒
    VA 0x0040A3B5 把它存回 lerpFrame +0x38
```

### 8.3 冻结的完整因果链

> **本项目在服务端拥有这个块并把它清零，所以两个时钟永远读 0。**`+0x96DDC` 的消费者然后拿 0 与一个时间也是 0 的 lerp 帧比较，**在第一帧之后的每一帧都走它的跳过分支，于是没有任何动画推进**：**摆好姿的骨架冻结在最后一次latch 的那个动画上**。
>
> **那就是每命一次的 hitbox 故障——第一条命全长，而其后的每一条命都卡在重生当时恰好发布的那个动画上。**

### 8.4 九偏移整块被 +0x18530 重定位

```cpp
// CODDIFF(1649370): THIS WHOLE BLOCK IS RELOCATED BY +0x18530 AND WAS NOT PORTED.
```

`0xAF350 - 0x96E20 = 0x18530` ✓

### 8.5 四条直接确认

```text
BG_UpdatePlayerDObj (sub_40AB30) 通过存储基址到达这些回调：
    (*((void(__cdecl**)(...))dword_827F730 + 179402))(...)   7 参数 → CREATE
    (*((...**))dword_827F730 + 179403))(&v53, v39, a5, a2)   4 参数 → APPEND
    (*((...**))dword_827F730 + 179404))(*(_DWORD*)a4, a2)    2 参数 → FREE
```

```text
717608, 717612, 717616 = 0x96DF8, 0x96DFC, 0x96E00 各加 0x18530 ✓
而参数个数与本项目自己的适配器签名相符
```

```text
该函数与 sub_407EA0 都测试
    *((_BYTE*)dword_827F730 + 717596)   = 0x96DEC + 0x18530   ← 非对称 anim-script 标志
```

### 8.6 旧值错了两遍

> **`0x96DD8..0x96E04` 全都坐在 `AnimTreeContextOffset 0xACE70` 之前**，**而 `BG_FindAnimTrees` 从基址 memset 0xACE70 字节** ——
> **所以本项目安装的那些回调还不只是放错了地方，它们坐在引擎每次动画树加载都会清零的那块区域【里面】。**
>
> **修正后的偏移坐在它上面，在动画数组与 characterInfo 之间。**

**"放错了地方"与"放在引擎要清零的区域里"是两个不同的错误**，后者更严重。

## 九、关键结论

1. **`pieceLimit == initialPieceCount + 1024` 在 27/27 地图上成立** ⇒ 2048 是推导值不是猜测。
2. **句柄与上下文相邻但不同**（`0xACE64` vs `0xACE70`）；检查上下文槽是检查一个没人写的字。
3. **`+100` 的两个 characterInfo 偏移**：写错会让 `BG_UpdatePlayerDObj` 走提前退出，**根本不重建**。
4. **`DObjScaleOffset` 是三分量向量**，只写 X 会在 scale≠1 时拉伸模型；**对象延伸到 216 独立确认了 0xD8**。
5. **通过一个基址做位移扫描会漏掉通过外层结构写的值**。
6. **两个时钟恒零 ⇒ 每一帧都走跳过分支 ⇒ 骨架永远冻结在最后一次 latch 的动画上**。
7. **旧偏移不仅错，而且落在引擎每次加载都会 memset 的区域里**。

## 十、未闭合点

- 两个时钟的写点（`outer + 0x15DE60/64`）在本项目里是否已被设置，本组未见。
- `EngineBindings.cpp` 1228 行之后未读取。
