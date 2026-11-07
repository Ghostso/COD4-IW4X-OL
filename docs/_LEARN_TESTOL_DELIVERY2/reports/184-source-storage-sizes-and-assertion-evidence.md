# 184 · 三个尺寸常量与它们各自的证据

## 一、范围

本报告学习 `EngineBindings.hpp` 658–897 行。

## 二、`ServerAnimConditionStorageSize = 0x100000`（1 MiB）

### 2.1 原来是 0xA6000，而游戏写 0xACE70

```text
BG_FindAnimTrees 开头：
    40b21e  push 0ACE70h; Size
    40b225  push eax          ; eax = dword_827F730，即这个数组
    40b226  call _memset
```

即 **708,208 字节**，**比 0xA6000 多出 28,272 字节**。

### 2.2 为什么是"损坏而不是崩溃"

> 活日志显示 `serverLoadAnimStorage_` 正好从 `base + 0xA6000` 开始，**所以越界落进下一个成员而不是未映射内存，这就是它造成损坏而不是崩溃的原因。**

### 2.3 读的偏移还要更深

```text
+0xAF31C  sub_407530 的 script-mode 字节
+0xAF314  sub_74AF50 的 anim user     +0xAF338 它的 allocator
+0xAF350  sub_407E10 的 per-entry 数组，步长 0x450
+0xAF318  CL_ParseGamestate 在 0x454CD4 写这里
0xAF350 + 18 * 0x450 = 0xB4200
游戏自己的块是 `ebx + 0xD1900`，在一个更大的分配里
```

### 2.4 结论与策略

> **所以这是向上取整到远超每一个实测偏移，而不是拟合它们：过度分配花的是地址空间，分配不足是把别人的内存交给引擎，而失败表现可以是任何样子。**

**"失败表现可以是任何样子"** 是这条的最强理由——不是"会更慢"或"会报错"，而是"无法归因"。

### 2.5 一条 static_assert

```cpp
static_assert(ServerAnimConditionStorageSize >= 0xACE70,
    "BG_FindAnimTrees memsets 0xACE70 bytes at this base");
static_assert(ServerAnimConditionStorageSize >= 0xAF350 + 18 * 0x450,
    "sub_407E10 indexes +0xAF350 with a 0x450 stride, per client");
```

**断言消息里带来源**，所以编译器报错时你直接知道该看哪个函数。

## 三、`scriptEvents` 的位置决定了初始化顺序合法

```text
BG_AnimParseAnimScript sub_407530 清 +0x1A004 的 movetype 表与 +0x25D7C 的一段 scrap 脚本，
    但【不清】scriptEvents ⇒ 解析会累积进它
唯一清零它的是 BG_FindAnimTrees sub_40B210 的 memset(dword_827F730, 0, 0xACE70)
initializeServerAnimation 跑 parse → BG_FindAnimTrees → BG_FinalizePlayerAnims，
    这正是 CL_ParseGamestate 自己的顺序（0x00454CDF, 0x00454D38, 0x00454D42）
```

结论：

> **这只有在整个事件表落在 memset 之内、characterInfo 数组之外时才成立；断言它，而不是相信这条注释。**

两条 static_assert：

```cpp
static_assert(事件表末尾 <= 0xACE70,
    "BG_FindAnimTrees' 0xACE70 memset must cover the whole event table, "
    "or finalize's re-parse would append to a stale one");
static_assert(事件表末尾 <= 0xAF350,
    "the event table must not overlap the per-client characterInfo "
    "array sub_407E10 derives at +0xAF350");
```

**这两个断言把"区间关系"变成编译期约束** —— 这是本项目反复出现的模式（尸体环 `19+18==37`、尺寸 `static_assert`）。

## 四、`ServerCharacterInfoBaseOffset`：测量早就在，只是常量没动

### 4.1 两个构建的写法

```text
3.3.3.3  0x004094C0
    mov ecx,[eax+0x144] ; imul ecx,ecx,0x3B8 ; lea edi,[ecx+edx+0x96E20]
本 build  clientNum 在 ps+0x158，步长 0x450，基址 0xAF350
```

### 4.2 统计证据

> 扫描每一个这样的站点：**3.3.3.3 上 0x96E20 出现在 14 个中的 12 个**，**这里 0xAF350 出现在 16 个中的 11 个**，**两边剩下的都是结构【内部】的字段读**（那边 `base + 0x2D0 / 0x308`，这里 `base + 0x334 / 0x37C`）。

即：**离群值能自我解释**（它们是结构内部的字段，不是数组基址），所以统计是干净的。

第三条独立证据：

> 它与 0x53DE1F 的动画投影一致，那里以 `lea edi, [ecx + eax + 0xAF350]` 到达同一个数组。

### 4.3 那句自我批评

> **测量早就在这个文件里了**——上面的存储注释列着"`+0xAF350` sub_407E10 的 per-entry 数组，步长 0x450"，而它下面的 static_assert 就是按这些精确数字写的。**代码实际放置数组用的常量只是从没被移过来对齐，于是存储按正确的区域配了大小，而数组被放进了它内部的另一个地方。**

**这是一个"注释与代码不一致"的精确描述**：注释是对的，断言是对的，只有那个常量是旧的。

### 4.4 `TODO(CODOL)`：必要但不充分

```text
2026-08-16 在它落地后立刻实测：torsoAnim 仍只在 5% 的样本里携带真实索引，
    而 legsAnim 是 98%，所以 sub_AA94C0 仍在选择 locomotion 动画之前退出，
    【命中骨架仍低一个姿态】。
```

并排除了一个候选：

> **不是另一个动画全局**——CODOL 的加载器在 `0x004445DAF` 做 `mov esi,[0x7817B80]`，而 `BG_AnimParseAnimScript` 在 `0x0040905E` 直接把它存进 `0x7817B84`，**所以两个名字持有一个指针**，而 `initializeServerAnimation` 已经门控它们相等。

结论：

> 四个退出点里**只有 `+0x1A004 + 0x204 * movetype` 的脚本计数通过了静态排除**；`logServerAnimScriptTable` 报告它。
>
> **退出条件**：`torsoAnim` 随移动变化，且颈部命中解析在 **58** 附近而不是 **36**。
>
> **那个测量是在 3.3.3.3 上做的**，那里数组至少落在引擎推导的偏移上；**这里它没有**，所以那个测量对本构建什么都没说明。

**最后一句很重要**：不要拿另一个 build 的结论当本 build 的结论。

## 五、`ServerLoadAnimStorageSize = 0x12000`：与 3.3.3.3 相同**且是对的**

### 5.1 两个维度都有直接证据

```text
454c6d  mov [ebp+var_100], 400h     ; 动画 CAPACITY
454cca  mov esi, dword_827F730      ; anim-condition 基址
454cd6  push 0
454cd8  push ecx                    ; &var_100
454cd9  mov ecx, [ebp+var_10C]      ; loadAnims 数组
454cdf  call sub_407530
```

`sub_407530` 把数组存进 `dword_1971E04`、容量存进 `dword_196DB0C`，**然后清掉调用者的计数**；`sub_404FE0` 用 `v5 += 72` 遍历它。

⇒ **`0x400` 槽 × 72 字节 = 0x12000**，而 `MaximumPlayerAnimations` 就是引擎传的那个 1024。

### 5.2 那句方法论

> **这个值与 3.3.3.3 的【完全相同】而仍然是对的——这正是为什么"匹配"只是一个怀疑，而只有核验才是结果。**

## 六、`BaseWeaponAssetCount = 0x514` 的三段

### 6.1 值

```text
1649370  1300 项（0x514）
3.3.3.3  500 项
```

### 6.2 边界由两侧 RVA 夹出

```cpp
static_assert(
    AttachmentModelCountRva - PerWeaponAttachmentCountsRva == BaseWeaponAssetCount,
    "the per-weapon attachment counts are one byte each and fill the gap "
    "between these two globals: change a base weapon count without the RVAs "
    "and this is what says so");
```

**数组长度 = 两个全局之差** —— 这是最硬的一种测量：**不需要数元素**。

### 6.3 那个真实后果

> 它写了两遍而**只有一个副本被更新**，**于是 500 以上的每一个基础武器都被静默地当作越界拒绝**。

## 七、`MaximumWeaponAssetIndex` 是**别名不是重推**

```cpp
// Defined in sv_gamestate_mp.hpp; ALIASED here, never re-derived.
static constexpr std::uint32_t MaximumWeaponAssetIndex =
    ::CodolGameServer::MaximumWeaponAssetIndex;
```

注释解释了为什么：

> 本项目里**每一个**武器索引健全检查都曾是 `> 0x3FF`，那是 3.3.3.3 的。**那个数字是【线宽】不是【表大小】**：那边十位，这里**十一位**，注册表随之从 900 涨到 1700 项。**模块化武器是动态注册的，落在表的【末端】附近**，所以拒绝 1023 以上**恰好拒绝了真实 loadout 会产生的那些武器**。

**"线宽 ≠ 表大小"** 是本组最值得记的一条区分。

## 八、八个 dvar 注册块：七个调用、一个故意不调用

```text
CG_Init 在 0x61701D..0x617040 连续调八个注册块
在受限进程里【一个都没跑过】⇒ 它们缓存的每个 dvar 指针仍是 null
而读它的原生代码像 sub_432000 那样 `mov ecx,[edx+0Ch]`，【没有 null 检查】
```

症状：

> 武器注册表的 per-weapon gametype 过滤器读 `*(char**)(g_gametype + 0xC)` 来测试武器的 `|` 分隔 gametype 列表，**而读的地址是 0xC**。

修法：

> **八个里的七个在这里被调用**，按 `CG_Init` 的顺序。每一个都先反汇编过，每一个都只是 `push "name"; call Dvar_Register*; mov dword_..., eax` —— **没有设备状态、没有分配，且是幂等的**，因为 `Dvar_Register` 会把已有的 dvar 还回来。

**第八个不是其中一员**：

> `sub_4EAC90` 开头是 `memset(unk_31437A0, 0, 0x164000)`，**是一个恰好坐在同一串调用里的状态初始化器**。故意排除。

## 九、`Com_Error` 自己的三个状态

```text
ComErrorTextRva  0x2FE7958
ComErrorLevelRva 0x2FE7904
ComErrorDepthRva 0x31053DC
```

> `sub_4F82E0` 格式化进文本缓冲区、保留 level、**递增 depth**，然后 **LONGJMP** ——
> **所以原生 fault 之后，非零 depth 说明引擎抛了错误而不是解引用了什么，而文本说明是哪一个。**

**"抛错误" vs "解引用"** 是可区分的关键——因为两者都表现为崩溃。

## 十、`CurrentCharacterGetRva` 的那次"地址一直在仓库里"

```text
"no address is established on 1649370" 对这一个【是错的】，
而【地址整个时间都在这个仓库里】。
tools/runtime/CodolMatchFlow.py 的 1649370 块带着
CURRENT_CHARACTER_GET_RVA = 0x2B87C0，每次运行都调它；
本次会话在一个活客户端上返回 current_character_index 4。
同一个文件、同一棵树，相反的断言 —— 正是 §35 称为
"同一个常量住在多于一个文件里" 的那类，而它已经造成过一次 bind() 失败。
```

三条独立确认：

```text
sub_6B87C0: int __cdecl(), 无参数
            缓存 sub_512120("currentCharacterIndex", 0)
            —— 一个【按名字】的查找，这就是它没有随其余角色方案移动的原因
```

## 十一、关键结论

1. **"损坏而不是崩溃"是最难归因的失败**，所以这类尺寸宁可向上取整。
2. **区间关系要用 static_assert**（事件表在 memset 内、在 characterInfo 外）。
3. **统计离群值若能自我解释**（都是结构内部字段），统计就是干净的。
4. **注释对、断言对、只有一个常量旧**——这类不一致要靠"按断言反查常量"发现。
5. **相同值不等于正确值**：`0x12000` 与 3.3.3.3 相同但独立核验过。
6. **线宽 ≠ 表大小**：10/11 位是线宽，900/1700 是表大小。
7. **同一串调用里可能混着不同性质的函数**，第八个是状态初始化器。

## 十二、未闭合点

- `torsoAnim` 只 5% 有真实索引的问题**在本 build 上未测量**。
- 退出条件（torsoAnim 随移动变化、颈命中 58 而非 36）未达成。
- `EngineBindings.hpp` 897 行之后未读取。
