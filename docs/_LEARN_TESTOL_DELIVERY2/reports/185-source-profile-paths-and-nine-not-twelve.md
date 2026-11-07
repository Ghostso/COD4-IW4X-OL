# 185 · profile 读取的四条路与"9 不是 12"

## 一、范围

本报告学习 `EngineBindings.hpp` 897–1136 行。

## 二、`sub_50FF30`：按路径读 profile

```text
格式化路径 characterClasses[<character>].slots[<slot>]
从公开 profile 取值
当 profile[69948] 置位时，用 ROL32(value ^ *(dword*)(profile + 69944), 8) 解混淆
```

注释：

> 这是 §64c 的"profile-blob 路线"，而且它是**这个 build 上已经存在的函数**，不是要写的移植。

两个偏移在这里出现：`69944 = 0x11138`（key）、`69948 = 0x1113C`（flag）—— 与后文的 `ProfileDecodeKeyOffset` / `ProfileObfuscatedFlagOffset` 完全一致。

## 三、`sub_50FC20`：更好的那条路

### 3.1 为什么旧路不可移植

```text
captureClientLoadoutRequest 曾需要 weaponSlotReadStaged_，
它唯一已知地址是 3.3.3.3 的 0x1945B0，【不可移植】：
那个函数用 ROL-8 阶梯在 key 全局的旋转 15/14/13/12/11 上解码一个混淆的 staged 数组，
而 out.exe 【任何地方都没有这样的阶梯】—— 逐旋转扫描都找不到簇，因为混淆是每 build 重掷的。
留空则每次职业读取都失败，classMask 保持 0，
capture 无论存储的 profile 多好都回答 NO_LOADOUT。
```

### 3.2 新路：按路径解析

```text
weaponClasses[<class>].<field>             (ecx == -1)
weaponClasses[<class>].<field>[<element>]  (ecx == element)
```

调用约定：

```text
ecx = 元素索引或 -1
edx = 字段名
栈上一个字节 = 职业索引
```

返回值：

> **用 profile 自己的 key 在 `+0x11138` 解混淆，门控在 `+0x1113C`，并【返回值减一】** —— 文档存 `id+1` 所以 0 可以表示"这里没有"。

**`retn` 是普通的** ⇒ **调用者弹栈参数**。

### 3.3 字段名不是猜的

> 它们从 `mp/playerdata.def`（`code_post_gfx_mp` 里的 StructuredDataDef 资产）读出：

```text
weaponClasses 携带：
    name / primaryBase / primaryAttach / secondaryBase / secondaryAttach
    perks / lethal / tactical / killstreaks / deathstreak
    meleeWpn / swordWpn / special / wildcards / characterIndex
```

**15 个字段名**，与 `PlayerDataDef::resolve` 的路径机制直接衔接。

### 3.4 为什么读"已保存的"比"暂存的"更对

> **现在大厅会持久化一份 profile，所以读已保存的 profile 也是更正确的来源：它返回的是玩家真正建好并保留的东西。**

## 四、那次"注释是错的"的更正

### 4.1 原注释

> out.exe "任何地方都没有这样的阶梯 —— 逐旋转扫描都找不到簇，因为混淆是每 build 重掷的"。

### 4.2 更正

> **阶梯是在的。**`sub_6BB0F0` 用**正是 3.3.3.3 的旋转 16/15/14/13/12/11** 和同样的 ROL-8 解码六个附件，key 是 `dword_E57A70`。
>
> **早先的扫描看不见它，是因为它找的是 3.3.3.3 的【寻址】不是它的【算术】**：

```text
3.3.3.3   stride 40，表是【全局】      cmp byte_2E74038[eax*8], 0
OLfinal   stride 76，表是【参数】      cmp [ecx+eax*76+280], 0
```

结论：

> **一个以全局为键的字节签名在表从 ECX 到来时是不可发现的。只按阶梯匹配，在 out.exe 里正好找到【一处】，就是这里。**

**这是本组最重要的一条方法论述**：**签名匹配要匹配不变的（算术），不要匹配可变的（寻址）。**

## 五、`sub_7C5BA0` 写出的 160 字节记录

```text
word 12..23   十二个角色物品 id
word 24..30   武器 0：itemId 然后【六个】附件 id
word 31..37   武器 1    （每武器 7 个字 = 14 字节）
word 38..44   武器 2
word 45..51   武器 3
```

**四种武器**（主/副/致命/战术？），每把 7 个字。

注释：

> **每武器七个字正是 `WeaponRequest` 逐字段的长度**，这就是为什么它能无重解释地映射过来。**偏移是从 `sub_7C5A50` 的【写】读出来的**（`v14 = a3+48` 每 7 个字推进；`v8 = a3+52` 写 `v8-1..v8[3]` 然后推进后再写 `v8-3`），**不是从结构形状推断的**。

## 六、缓存记录：读比重建好

```text
sub_7C5500 是 38 槽缓存，按两个 dword 键控
sub_7C6480 取一个槽、从 slot+8 memcpy 出 160 字节，【然后才】调 sub_7C5BA0 重建回去
所以 slot+8 持有客户端【最后一次为自己建的】记录，而且它持久
```

槽布局：

```text
槽步长        42 dword = 168 字节
slot + 4      标志字节
slot + 8/+12  两个键
slot + 8      160 字节记录从这里开始
              （它的头两个 dword 【就是】那两个键 —— sub_7C6480 通过同一个指针写它们，
                这就是为什么角色物品落在 word 12、武器落在 word 24）
```

结论：

> **读它是一次有界内存读。重建它是桥线程上的一次原生调用，而那正是让 `profileSlotProbeEnabled()` 默认关闭的危险。优先读；把调用只留作回退。**

### 6.1 怎么不调任何东西就认定"哪个槽是玩家的"

```text
mov ecx, dword_84ABB08      ; 当它为 null 时用 dword_84ABB14
call sub_B9A0F0             ; 返回 ecx + 216
mov esi, [eax+20h]          ; key 1 -> owner + 248
mov edi, [eax+24h]          ; key 2 -> owner + 252
```

注释：

> 没有这个，读会取**第一个已填充的槽**，**在有其他成员的大厅里那是他们的职业与玩家的职业之间的一次掷硬币**——**而一个"错但貌似合理"的职业是最难察觉的一类错。**

## 七、`CharacterProfileSlotCount = 9` 而不是 12

### 7.1 实测

```text
character_slots: [545, 0, 0, 0, 0, 0, 0, 0, 0, null, null, null]
```

> 槽 0..8 返回值；**槽 9、10、11 【抛异常】**。所以 `characterClasses[N].slots` 是**九项**，而 `CharacterItemCount` 的十二是**另一个数组**的大小——`sub_619E90` 填的那个物品记录。

### 7.2 后果

> **在一个九宽的数组上循环十二宽的索引是读越界，而 `__try` 在这里救不了你。**

## 八、五职业必须从文档读，不能从记录缓存

> 缓存/记录路径（`LoadoutRecordBuildRva`）**只持有玩家【选中的那一个】职业**，所以镜像它会让 `custom1..custom5` 完全相同，**而切换职业就成了空操作**。
>
> 客户端自己编辑的结构化 profile 文档**按角色持有全部五个**，而读它是**纯内存读**——不是 `profileSlotProbeEnabled()` 关闭的那个 `sub_50FF30` 原生调用。

### 8.1 三个偏移与一次旋转

```text
sub_7F9090 返回 &dword_E54BC48（profile manager 全局）
+0xA0      文档
+0x11138   混淆 key
+0x1113C   flag
存的 dword 解码为 ROL32(raw ^ key, 8)
ProfileDocumentSize = 0x8000
```

> 三个偏移和那个旋转都从 `sub_50FF30` / `sub_76BCF0` 读出，**而整个方案用 `Tools/olfinal/decode-profile-blob.py` 对着实机转储离线验证过**，它用这种方式读出每个职业各自不同的武器。

## 九、1607/37/5/22/29 与 605/14/5 是**回退值**

```cpp
// NO LONGER THE ANSWER -- THE FALLBACK, AND THE CROSS-CHECK.
// resolveProfileLayout() reads all of these off the loaded def BY NAME and logs
// any that disagree; these values are used only when that walk fails.
```

**五个武器类常量**：

```text
weaponClasses 基址 1607、元素步长 37、每角色 5 个职业
primaryBase = 子序号 22、secondaryBase = 子序号 29
60 = 12 角色 × 5 职业
当前角色的五个 = [character*5 + 0 .. +4]
```

**三个角色类常量**：

```text
characterClasses 基址 605、元素步长 14、slots 子序号 5（九宽）
```

注释：

> **它们在 3.3.3.3 上是【错的】，那边 weaponClasses 在 1154、步长 36**。**这正是那个 walk 存在的原因。**

## 十、`sub_619AD0` 的两次遍历与"零是正常"

> `sub_619AD0` 对十二项物品记录做**两次**遍历，第二次用**角色自己携带的**每槽默认表填每一个**空**项——`0x34` 字节角色记录 `+0xC` 的十二个 uint16，通过同一套桶方案、用 `def[+5] == 2` 作类型检查。

结论：

> **所以服务端只写一个值——条目 0——而引擎推导另外十一个。**
>
> **这也是为什么这个账号上每个角色都读作 `slots = [545,0,...]`：那些零不是空 profile，它们是【常态】，意思是"这里用角色的默认值"（§66a）。**

### 10.1 槽名的黄金对照

```text
槽  0 cha   1 fpa   2 boo   3 fja   4 han   5 hea   6 ves   7 heg
545 cha_infbasea → fpa_infbasea, boo_infbasea, fja_infbasea,
                   han_infbasea00, hea_socomb
```

注释：

> **槽是有名字的，而那些名字是这个移植的【黄金对照】，因为它们来自客户端自己的表、与它不共享任何代码。**

## 十一、变体选择器是**线的函数**，不是常量

```text
sub_61B6C0 的第四个参数 → sub_80DEF0 → 对变体位掩码贡献一位
out.exe 自己的前端调用者只在它是 1 或 2 时保留值，否则【替换成 2】
    （0x61D81B，`lea eax,[ecx+2]` 且 ecx 为零）

§166 命名了语义并【移动了所有者】：
    【对局内】调用者是 CG_SetupClientCharacterInfo 0x00541800，
    它传 *(int*)(clientState + 0x154) + 1 —— 【本服务器发送的那个阵营字段】加一。
```

结论：

> **所以选择器不是本侧可以选的常量：它是线的一个函数**，而 `characterVariantSelector(faction)` 在 `.cpp` 里是唯一计算它的地方。
>
> **这个常量是刻意【删除】而不是留成没人读的默认值**——**一个陈旧默认值正是这个 dedicated 一整个会话解析成变体 2 而客户端解析成变体 1 的方式**（§67d，由 §166 更正）。

## 十二、`sub_50FF30` 的空 profile 守卫是假的

```text
sub_50FF30 开头：
    v2 = sub_7F9090() + 160; if (!v2) return 0;
```

> **这【抓不到】空 profile**：manager 为 null 时 `v2 = 160`，检查通过，然后 160 被解引用。

后果：

> **在没有解析过的公开 profile 时调用它是访问违例，而 `__try` 救不了你：CODOL 自己的崩溃报告器先接住 fault 并写一个 ClientException。**

`CodolMatchFlow.py` 的守卫：

> 它从不在不检查 profile 的情况下调任一访问器（`readCurrentCharacter` 在 `publicProfile.ready` 为假时返回 null），**而那个守卫是承重的——不带它移植这个调用杀掉了客户端。**

### 12.1 五个 profile 常量

```text
ProfileManagerRva            0xE14BC48
PublicProfileOffset          16
ProfileChunkMaskOffset       0x1008C
ProfileOperationOffset       116
ProfileParsedOffset          0x1112C
ProfileRequiredChunkMask     0x07FFFFFF
```

`0x07FFFFFF` 是 **27 位**，与 `ClientSlot::profileStatsRequiredMask` 的默认值完全一致——同一个东西的两个视图。

## 十三、关键结论

1. **签名匹配要匹配算术（旋转序列），不要匹配寻址（全局 vs 参数）**——这是本组最重要的一条。
2. **`retn` 普通 ⇒ 调用者弹栈**，而返回值要**减一**（文档存 `id+1`）。
3. **缓存记录读优于重建**，因为重建是桥线程上的原生调用。
4. **"第一个已填充的槽"是掷硬币**——必须按 owner 键认领。
5. **9 不是 12**：`characterClasses[N].slots` 九宽，`CharacterItemCount` 十二宽是另一个数组。
6. **零是常态**（用角色默认值），不是空 profile。
7. **变体选择器是线的函数**，删除常量而不是留默认值。
8. **`+160` 的空检查抓不到空 manager**，`__try` 也抓不到（崩溃报告器先接）。

## 十四、未闭合点

- `resolveProfileLayout()` 的按名 walk 失败后的回退值仍是 3.3.3.3 错的那组（但只在 walk 失败时用）。
- `EngineBindings.hpp` 1136 行之后未读取。
