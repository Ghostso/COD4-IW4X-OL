# 164 · AngleVectors 的错位调用、animtree 四个钩子

## 一、范围

本报告学习 **2 处实现**：

- `NativeWeaponBindings.cpp` 前 120 行
- `ClientAnimtreeHook.cpp` 前 100 行

## 二、`AnglesToQuaternion` vs `AngleVectors`：函数选错 + 参数反向

### 2.1 两个错误叠在一起

```text
旧：AnglesToQuaternionRva 0x3853E0 = sub_7853E0
    经 ESI 读角度，经 EDX 写【四个】float
    —— 是 angles-to-QUATERNION
    而 3.3.3.3 的九 float AnglesToAxis 0x0062C1A0 【在本 build 上根本不存在】

新：AngleVectors sub_767890
    四个【栈】参数，__cdecl，三个独立目的地
```

注释解释了后果：

> **寄存器反过来时，它把一个清零的轴缓冲当成角度读，然后在调用者的 `fireAngles` 上盖了一个四元数**，于是它产出的每个 basis 都是三个零向量，而 `SV_IsWeaponFireBasisValid` 拒绝它。

注意这是**双重错误**：函数选错（返回 4 float 而不是 9）+ 参数反向（读的当成写的）。**单独任一个都不会表现为"三个零向量"**。

### 2.2 为什么 `AngleVectors` 能替代 `AnglesToAxis`

> Quake 系引擎把 `AnglesToAxis` 定义为 **`AngleVectors` 且第二行取反**，所以这返回的正是下面各调用者已经期望的 `(forward, LEFT, up)`。

即：`AnglesToAxis` 的行是 `(forward, right, up)` 但 right 是**左手系**的否定，`AngleVectors` 直接给 `(forward, right, up)` 的左手版本。**调用者期望的是后者。**

### 2.3 调用序列

```asm
push upData         ; axis+6
push rightData      ; axis+3
push forwardData    ; axis+0
push anglesData
mov eax, function
call eax
add esp, 10h        ; 4 个参数 × 4 字节
```

**参数从右往左压**，`add esp, 10h` = 16 字节 = 四个指针。

### 2.4 三个 `playerState` 偏移在**三个文件**里各写一份

```text
EFlagsOffset                  = 0x104
ViewAnglesOffset              = 0x160
LinkEntityOffset              = 0x248
CurrentWeaponOffset           = 0x3F8
WeaponPositionFractionOffset  = 0x404
UnlinkedEntityNum             = 2047
TurretViewFlags               = 0x0C00
```

注释（这是本组最重要的一条结构性警告）：

> **与 `NativeWeaponMovementBindings.cpp` 里同一个未移植块——这是第三个持有 `playerState_s` 偏移的文件，且与 3.3.3.3 树的该文件逐字节相同。同一个结构，三个文件，其中一个被移植了。值与证据在 `NativeWeaponMovementBindings.cpp` 里说一次。**

即：`0x104`（eFlags）等偏移在三个文件里重复定义，**只有一个文件更新到了 1649370**。而 `ViewAnglesOffset = 0x160` 与之前报告里"lerp frame 从 0x160 挪到 0x17C"是同一族偏移——**这里有同样的风险**。

### 2.5 SEH 的边界

```cpp
__try { function(-1, playerState.bytes.data(), origin, time); completed = true; }
__except (EXCEPTION_EXECUTE_HANDLER) { completed = false; }
```

注释：

> 保留的客户端原语在重建的服务端全局或输入不完整时**会 fault**。**SEH 遏制源事务，但在一次会改状态的调用之后无法回滚原生状态。**

即：SEH 只保护"不崩"，不保护"没改动"。

## 三、animtree：四个钩子，四层深度

### 3.1 第一层（12.140）：看**选了哪个资产**

```text
ResolveCallRva = 0xB28B    (0x0040B28B)
ResolveRva     = 0x34ACF0  (0x0074ACF0)
OriginalCall   = E8 60 FA 33 00
```

记录：被要求的名字、返回的指针、该指针处的条目数。

### 3.2 第二层（12.143）：看**每个树怎么被构建**

```text
0074AC1A  51              push ecx              ; 名字
0074AC1B  E8 00 B0 03 00  call sub_785C20       ← 被替换
0074AC20  83 C4 0C        add  esp,0Ch          ; cdecl，3 个参数
0074AC2C  8B D8           mov  ebx,eax          ; 构建出的树
```

注释：

> 12.140 的钩子看**哪个资产被选中**；这一个看每一个树**被构建**，**那是更低一层，也是 519 项树与 123 项树分叉的地方。**

### 3.3 第三层（12.145）：看**输入的字节是否就不同**

```text
0074ABB9  51              push ecx              ; 名字
0074ABBA  E8 41 FE FF FF  call sub_74AA00       ← 被替换
0074ABBF  83 C4 0C        add  esp,0Ch          ; cdecl，3 个参数
```

`sub_74AA00` 找 `animtrees/<name>.atr`（资产类型 36），读它，交给 `Scr_AnimTreeParse`。

理由写得极好：

> **一个确定性的解析器不可能把同样的字节在这里变成 519 个成员、在那里变成 123 个，所以问题在于 INPUT 是否不同。**钩子自己重做资产查找，并记录加载器会读到的大小：`v4 = *(DWORD*)(asset + 8) + 1`。

### 3.4 第四层（12.146）：看**节点分配器的 EAX**

```text
AllocRva = 0x388540
AllocCallRvas = { 0x38731C (clone), 0x3886F8 (root), 0x38878C (ancestor), ... }
```

理由：

> `sub_788540` 是 animtree 节点的**唯一创建者**，而它的 **KEY 从 EAX 进来**，所以一个普通 C 钩子看不到它——**这个钩子是一个 naked thunk，记录 EAX 然后跳过去，不改动调用者的栈和返回地址。**
>
> **为什么**：线上只可能携带 key 0 或 2，**而 demo 的演员携带 key 112，祖先 20/100/101/102**。**这两个事实里有一个有洞，只有观察才能说清是哪个。**

节流：`key 0 和 2 被跳过`（因为是正常的），日志封顶——**节点创建是热路径，12.100 测到每 30 秒有几百个节点翻腾**。

### 3.5 名字→资产查找的四层结构（12.138）

```text
string table   *(void**)dword_789C524，20 字节步长
               +0..1 refcount，+3 length，+4.. 名字内联
buckets        0x7A5F100，每项 u16，索引 ((kind*101) + sid*2) & 0xFFFF
registry       0x7A7F100，16 字节项，每 bank 4096
               +0 value，+4 u16 next，+6 type，+8 key=(kind<<16)|(sid>>8)
```

`sub_74C610` **把匹配到的节点移到链首**：

> 所以两个同键条目中哪个胜出**取决于访问顺序**——**这正是这次遍历要暴露的东西。**

### 3.6 已加载 zone 表（12.126）

```text
ZoneCountRva = 0x1A2ACF4   (0x01E2ACF4)
ZoneTableRva = 0x25C9DE8   (0x029C9DE8)
ZoneStride   = 164
ZoneNameOffset = 8
```

注释：**以 RVA 形式持有，所以不假设镜像加载在首选基址。**

### 3.7 五个钩子的原字节都存了

```cpp
OriginalCall         = { 0xE8, 0x60, 0xFA, 0x33, 0x00 };
OriginalBuildCall    = { 0xE8, 0x00, 0xB0, 0x03, 0x00 };
OriginalPopulateCall = { 0xE8, 0x41, 0xFE, 0xFF, 0xFF };
```

与之前报告里 `FrameHook.cpp` **没有**原字节校验形成对照——这里是有的。

## 四、关键结论

1. **函数选错 + 参数反向可以叠加成"三个零向量"这种既不崩也不报错的形态**，只有 `SV_IsWeaponFireBasisValid` 这种"结局处校验"能抓住。
2. **同一个结构的偏移散在三个文件里，只有一个被移植**——这是本项目反复出现的结构性问题（前面记过"一个数字出现在多于一个文件里"）。
3. **确定性解析器不会把同样输入变成不同结果**，所以差异必然在输入；这是 12.145 的推理骨架，也适用于任何"同样的代码不同输出"的排查。
4. **只能通过寄存器传递的东西需要 naked thunk**，普通 C 钩子看不到 EAX。
5. **访问顺序决定链上谁胜出**（`sub_74C610` 移到链首），所以同键条目是顺序相关的。
6. **热路径要节流并按值过滤**（跳过 key 0/2）。

## 五、未闭合点

- `NativeWeaponBindings.cpp` 的三个偏移未与本 build 对齐（注释自己指出）。
- animtree 的 519 vs 123 尚未归因，四个钩子是为了定位它。
- `sub_788540` 之外是否还有其它节点创建路径，12.109.2 说没有，但未在本组复核。
