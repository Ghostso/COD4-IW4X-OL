# 200 · WeaponDef 的七个独立位移、物品记录的两个偏移、12 字节条目

## 一、范围

本报告学习 `EngineBindings.cpp` 1407–1587 行。

## 二、`ItemDefinitionNameOffset`：12 是**显示键**不是内部名

### 2.1 活体转储

```text
Dumped live from item 10001:
    +8  = m4_mp                  ← 武器资产名
    +12 = sf_weapon_m4_mp_name   ← 本地化键
    +16 = sf_weapon_m4_mp_desc
    +20 = wea_m4_item_icon
```

### 2.2 后果

> 读 +12 把 `sf_weapon_m4_mp_name` 交给了武器解析器，**而那不是一个武器**，所以它返回 0，**而每一个 loadout 里的每一个职业都以 `base_weapon_resolver` 被跳过**。
>
> **两个字符串只差一个后缀，这就是为什么在只记录 id 的那段时间里，这件事读起来像"这个 build 上物品缺失"。**

**"两个字符串只差一个后缀"** —— 这让错误完全无法从"找不到"这个现象上分辨。

## 三、物品记录的四个前导 short

```cpp
constexpr std::size_t ItemDefinitionFlagsOffset = 4;        // u16 at +4
constexpr std::size_t ItemDefinitionRecordEntryOffset = 6;  // u16 at +6
constexpr std::uint16_t ItemCategoryCharacter = 2;
constexpr std::uint16_t ItemCategoryCharacterPiece = 3;
```

注释：

```text
定义是 {u16 id, u16 slot, u16 flags, u16 recordEntry, char* name, ...}
—— 与 Tools/olfinal/marketplace-decode.py 从 zone 里读的同一批四个前导 short
```

### 3.1 分类在 `flags >> 8`

```text
sub_61B7D0 测试 `*(BYTE*)(definition + 5) == 2` 才能把一个物品当角色
    —— 那是 +4 处 u16 的【高字节】，所以分类住在 flags >> 8：
       2 = 角色，3 = 角色零件
```

**`definition + 5` = `flags` 的高字节** —— 所以在代码里看到的是"字节 5 == 2"，而语义是"`flags` 高字节 == 2"。

### 3.2 `+6` 是记录条目号，引擎自己给了证明

```text
角色 569 活体解析为
    record=569,555,525,552,1139,561,-,564
而 zone 给那些零件 recordEntry 1,2,3,4,5 和 7
    —— 正好是 sub_619AD0 放它们的那些条目
角色自己的条目是 0
```

### 3.3 为什么这使"存储的服装可放置"

> **profile 密集地保存已装备零件（`slots[0..8] = 545,18481,2137,0,...`）而记录是按条目键控的，只有物品表能把一个映射到另一个。**

**两个索引空间**：

```text
profile slots：密集，按装备顺序
record：      按条目号（0=角色，1..11=零件）
```

## 四、附件槽表：15 个 CSV 与 15 个槽号

```cpp
std::array<std::pair<std::string_view, std::uint8_t>, 15> AttachmentSlotTables{
    { "mp/coweapitemsbas.csv",  3 },
    { "mp/coweapitemscqc.csv", 13 },
    { "mp/coweapitemshbs.csv",  4 },
    { "mp/coweapitemsiro.csv", 10 },
    { "mp/coweapitemsmuz.csv",  2 },
    { "mp/coweapitemsrai.csv",  6 },
    { "mp/coweapitemsret.csv", 15 },
    { "mp/coweapitemssco.csv",  1 },
    { "mp/coweapitemssto.csv",  5 },
    { "mp/coweapitemsgri.csv",  7 },
    { "mp/coweapitemsbip.csv",  8 },
    { "mp/coweapitemssra.csv",  9 },
    { "mp/coweapitemsmag.csv", 11 },
    { "mp/coweapitemscam.csv", 12 },
    { "mp/coweapitemsdec.csv", 16 },
};
```

### 4.1 那次"子目录形式不存在"

```text
CODDIFF(1649370): the last five were `mp/coweapitems/gri.csv` -- a
SUB-DIRECTORY form that does not exist in this build's zone.
```

解密 `common_marketplace_lite.ff`（`ff_init_common_marketplace_V95.ifs`）并列出它的 StringTable 资产：

> **十六张表，每一张都是平铺的 `mp/coweapitemsXXX.csv`，而字符串 `coweapitems/` 在 zone 里【任何地方都不出现】。**

后果：

> **第十项的查找没有返回表，而旧的循环把那个当成致命 —— 所以每一个已装备附件都以 `equipped_attachment_slot` 失败，不管它在哪个槽。**

**"最后一个失败让前九个的成功白费"** —— 典型的"局部失败被当整体失败"。

### 4.2 两个表的缺席有理由

> 同一个 zone 解决了这里没列出的两张表。它的 WEA 表的槽名列用的正是这十四个 ——
> `iro mag rai sco hbs muz cam sto gri bas bip sra cqc ret`
> —— 所以 **`mp/coweapitemsdec.csv` 不是 loadout 槽**，而 **`rof`（SlotNames 里的槽 14）在这个 build 上没有表，因为没有任何东西装备它**。

**表格里 `dec` 映射到槽 16，而 16 不在十四个槽名里** —— 所以 `dec` 存在但不是 loadout 槽。

## 五、WeaponDef：**七个独立位移**，没有单一 delta

```text
CODDIFF(1649370): THE WHOLE WeaponDef MOVED. Every offset below was
3.3.3.3's, and the struct grew in seven separate places between the
builds, so no single delta fixes it -- the shift is
    +268 at the head
    +308 across the ammo block
    +312, +320, +344, +348 and +352 by the tail
```

**六个数值，七个位置**（`+312` 覆盖一处，`+320` 一处，`+344/+348/+352` 三处）。

### 5.1 每个值的来源都标了函数

```cpp
WeaponTypeOffset = 1416;          // sub_42BF80 == 3
WeaponClassOffset = 1420;         // sub_421DE0 == 11
WeaponPenetrateTypeOffset = 1424; // between 1420/1428     ← 夹逼
WeaponImpactTypeOffset = 1428;    // sub_421DE0 == 2
WeaponFireTypeOffset = 1432;      // sub_426320
WeaponAmmoIndexOffset = 2028;     // sub_42EC80 writes it
WeaponClipIndexOffset = 2036;     // sub_42EE90 writes it
WeaponMaxAmmoOffset = 2040;       // sub_42BF80
WeaponShotCountOffset = 2044;     // between 2040/2048     ← 夹逼
WeaponMeleeDamageOffset = 2072;   // sub_4BC1D0
WeaponFireDelayOffset = 2088;     // sub_426320
WeaponDropTimeOffset = 2188;      // sub_423CF0 putaway
WeaponRaiseTimeOffset = 2192;     // sub_424470 raise
WeaponOverlayReticleOffset = 2348;// sub_421DE0 != 3
WeaponHipSpread*Min/Max = 2384..2404;  // sub_423060 的十一次读与 sub_422AA0 完全吻合
WeaponAdsSpreadOffset = 3096;     // sub_56C510
WeaponDamageOffset = 3344;        // sub_591790
WeaponDamageRangeOffset = 3368;   // sub_432510 indexed
WeaponHitLocationMultipliersOffset = 3404;
WeaponRifleBulletOffset = 3802;   // sub_5923C0
WeaponBulletExplosiveDamageOffset = 3810;
WeaponDualWieldCapableOffset = 0xEEC;  // BG_DualWieldActive 0x433030
WeaponClipSizeOffset = 3688;      // sub_432E90
WeaponFireTimeOffset = 3696;      // sub_433360
WeaponAimDownSightOffset = 3806;  // sub_433910, sub_434680
WeaponAmmoCountClipRelativeOffset = 3865;  // sub_42BF80
```

### 5.2 两个"夹逼"出来的值

```text
WeaponPenetrateTypeOffset = 1424  // between 1420/1428
WeaponShotCountOffset     = 2044  // between 2040/2048
```

注释：

> **三个没有函数引用的由固定步长的已确认邻居在两侧夹住，这就把它们精确钉住了。**

### 5.3 六项 hipSpread 的交叉验证

```text
sub_423060 的十一次字段读与 sub_422AA0 的【完全吻合】
```

**两个函数读同一批偏移且顺序一致** —— 这是"结构性"证据。

### 5.4 `Tools/olfinal/struct-offset-uses.py`

> 列出在任一镜像里触及某个偏移的**每一条指令**；这里的每个值都由 **out.exe 自己的代码**点名，推导函数写在注释里。

**这个工具的存在本身就是方法**：不是"猜偏移"，而是**由使用点反推**。

## 六、`MaximumWeaponFireType = 10` 而不是 6

```text
CODDIFF(1649370): 6 was 3.3.3.3's highest fire type. out.exe compares
this field against 7, 8, 9 and 10 as well (sub_426320 tests == 10), so
the old bound rejected four fire types that exist on this build.
```

**旧的 6 会拒绝四个存在的开火类型**。

## 七、`CharacterItemDefinitionSize`：40 → **52**

### 7.1 同一文件里 800 行之外的自我矛盾

```text
CODDIFF(1649370): 40 IS 3.3.3.3's AND IT WAS WRONG BY TWELVE BYTES PER RECORD,
and this file already said so eight hundred lines away:
"indexes CharacterItemDefinitionTable at stride 52 by the u16 at +2".
The constant that actually places the record was never moved to match
-- section 51k's rule, and the third time it has cost this port.
```

**`51k` 的规则被第三次付出代价** —— 而这条规则是：

> **注释对、断言对、只有一个常量旧。**

### 7.2 四处独立的反汇编

```text
0044E1F0  movzx eax, word ptr [eax + 2]     ← 记录索引
0044E1F4  cmp   eax, [0x7798900]            ← 计数
0044E1FC  imul  eax, eax, 0x34              ← 【步长】
0044E1FF  add   eax, [0x77988FC]            ← 表
```

**四处一致**：`0x0061B859`、`0x00619C1D`、`0x00660A94` 都同意。

第三方确认：

> `tools/runtime/CodolCharacterCategoryDump.py` 自 §67 起在活客户端上用同一个 `0x34` 读同一张表，**跨 54 条记录与十二个角色**。

### 7.3 代价：不是外观问题

```text
读出的两个字节是【女性标志】与【颜色选择子】。
在记录索引 0 处两个步长一致，而本项目取过的每一次测量都在角色 0 上；
在索引 1 处它们已经差十二字节，
所以任何一个不在第一个角色上的玩家都会被给予【另一个角色的性别与颜色】
    —— 静默地，没有错误，正是 §48d 的失效模式。
```

**"测量都在索引 0 上，而错误从索引 1 开始"** —— 这是为什么它一直没被发现。

### 7.4 `static_assert`

```cpp
static_assert(CharacterItemDefinitionSize == 0x34,
    "out.exe indexes CharacterItemDefinitionTable with imul reg, reg, 0x34 at "
    "0x0044E1FC, 0x0061B859, 0x00619C1D and 0x00660A94");
```

**断言消息里写出四个地址** —— 编译器报错时你直接知道去哪看。

## 八、`CharacterRecordToSelectionName` 的十二项置换

```cpp
constexpr std::array<std::uint8_t, 12> CharacterRecordToSelectionName{
    11, 0, 1, 2, 3, 4, 5, 6, 7, 8, 11, 9,
};
```

**注意 `11` 出现两次**（索引 0 和索引 10）—— 所以这是一个**多对一**映射，不是置换。

注释：

> `CODOL_CharacterCustomization_CopyCurrentItems 0x00568860` 与 `..._ResolveSelectionIds 0x0040CA30` 闭合了这个记录到名字的顺序。
> **后面那个 76 位的打包只是传输，绝不能被当作"每一个已解析模型都可见"的证明。**

**"76 位 = 12 × 6 + 4"？** 12 个选择项，每项可能 6 位（`selectionIds[11]` + 1）⇒ 约 72 位，加 4 位标志 = 76。这与"11 个名字"和"12 个记录项"的关系一致。

## 九、`character_item_record`：**12 字节不是 8**

### 9.1 `sub_619E90` 的四条指令

```text
619ed0  lea ebx, [ecx+4]        ; ecx = 目标，条目 0 的存在位
619ee6  lea esi, [ebx-4]        ; 条目 BASE 是 目标 + 12k
619ef3  mov dword ptr [ebx+4], 0  ; 高 dword，在 +8
619efa  mov byte ptr [ebx], 0     ; 存在字节，在 +4
619f00  add ebx, 0Ch              ; 十二，十二次
619f08  cmp byte ptr [ecx+4], 0   ; 条目 0 的存在位，又在 +4
```

### 9.2 那个致命的 48 字节

```text
它的唯一调用者在每次调用前把目标 memset 成 0x90 = 144 = 12 × 12（0x618bad）。
在八字节下十二个的数组是 96，所以引擎【写过了 48 字节】
—— 而它在【两条分支上都这么做】，
因为 sub_6206B0 说 no 的路径（0x619eb0）仍然以那个步长走完十二个条目
```

**"在两条分支上都越界"** —— 所以即使走"不需要填充"的路径也会写坏。

## 十、关键结论

1. **`+12` 是本地化键 vs `+8` 是资产名**，差一个后缀，错误无法从现象分辨。
2. **分类住在 `flags >> 8`**，所以代码里是"字节 5"。
3. **profile slots（密集）与 record entry（按号）是两个索引空间**，只有物品表能桥接。
4. **一个表的查找失败不该让前九个的成功白费**。
5. **WeaponDef 有七个独立位移，没有单一 delta** —— 每个值都由 out.exe 自己的代码点名。
6. **"测量都在索引 0 上，错误从索引 1 开始"是最隐蔽的一类**。
7. **12 字节条目的越界发生在两条分支上**，包括"不需要填充"的那条。

## 十一、未闭合点

- `CharacterRecordToSelectionName` 里 `11` 出现两次的语义未说明。
- `EngineBindings.cpp` 1587 行之后未读取。
