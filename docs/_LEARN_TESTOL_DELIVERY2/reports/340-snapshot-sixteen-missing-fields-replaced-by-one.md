# 340 · **"那十六个『缺失』字段不是缺失 —— 这个 build 用一个替代了它们"**、三条独立证据、`82e` 的"诊断错而建议对"

## 一、范围

本报告学习 `sv_snapshot_mp.cpp` 5398–5600 行。

## 二、**四个字段的索引变更**（本组第三重要）

```php
// indexes appear in the dm demo with these exact widths, written by
// a real retail server:
//     modelIndex  16 -> 17   4 bits   seen 20x
//     faction     17 -> 18   1 bit    seen 20x
//     female      18 -> 19   1 bit    seen  4x
// and `color` follows by position: 0x140..0x15C is a contiguous
// eight-slot run whose other seven are all confirmed, which puts it
// at index 56 and widens it from 2 bits to 5.
```

### 2.1 四行

| 字段 | 旧索引 | 新索引 | 宽度 | 出现次数 |
|---|---|---|---|---|
| `modelIndex` | 16 | **17** | 4 位 | 20 |
| `faction` | 17 | **18** | 1 位 | 20 |
| `female` | 18 | **19** | 1 位 | 4 |
| `color` | ? | **56** | **2 → 5 位** | （位置推断） |

**⇒ 四个字段全部 +1 而 `color` 跳得更远。**

### 2.2 而 `color` 的**位置推断**

```text
0x140..0x15C 是一个连续的八槽游程
其它七个全部确认
⇒ 所以它（第八个）在索引 56
⇒ 而宽度从 2 位加宽到 5 位
```

**✅ 一个**用"邻域已确认"定位**的手法**（第八次"用已知作锚"）。

### 2.3 而 `color` 从 **2 位变 5 位**

**⚠ 而 §315 的 `validCharacterCustomization` 说 `color > 3` 就拒绝** —— 所以 `color` 只有 2 位有效。**

**⚠ 而这里是 5 位。**

**⇒ 所以**线格式 5 位而有效值 2 位**。**

**✅ 与 §315 的 `color <= 3` 配合（5 位宽但只用 0..3）。**

## 三、**"那十六个『缺失』字段不是缺失"**（本组最重要的一段）

### 3.1 那段

```php
// AND THE SIXTEEN "MISSING" FIELDS ARE NOT MISSING -- THIS BUILD
// REPLACED THEM WITH ONE (section 92). 3.3.3.3 packs eleven
// selection ids into a 76-bit blob spread over eight clientInfo
// fields, then hangs four explicit model/tag attachment pairs off
// it. OLfinal sends the CHARACTER ITEM ID instead, in ONE 16-bit
// field, and lets the engine derive the eleven -- which is exactly
// what section 67 found the LOCAL path doing (sub_619AD0's second
// pass fills every empty record entry from the character's own
// per-slot defaults).
//
//     index 20, offset +0x7C, 16 bits, type 0 (generic arm)
```

### 3.2 七层

```text
1. **那十六个"缺失"字段不是缺失 —— 这个 build 用一个替代了它们**
2. ⇒ 3.3.3.3 把**十一个选择 id 打包成一个 76 位 blob 分散在八个 clientInfo 字段**上
3. ⇒ 然后**挂四个显式 model/tag 附件对**
4. ⇒ **OLfinal 改为发【角色物品 id】在一个 16 位字段里**
5. ⇒ 而**让引擎推导那十一个**
6. ⇒ **那正是 §67 发现【本地】路径所做的事**（`sub_619AD0` 的第二 pass 从角色自己的每槽默认填每一个空记录项）
7. ⇒ **`index 20, offset +0x7C, 16 bits, type 0`**
```

### 3.3 **"一个字段替代了十六个"**

**✅ 三层**：

```text
3.3.3.3   76 位 blob（八个字段）+ 四对附件
本 build  一个 16 位角色物品 id
⇒ 而引擎从它推导十一项
```

**✅ 这是一个**架构级的简化**。**

**⇒ 与 §282/§309 的"`CharacterSelectionResolve` 缺席而 OLfinal 用一个 item 驱动方案"**完全一致** ✓**

## 四、**三条独立证据**（本组核心）

### 4.1 证据一：**值集**

```php
//   the VALUES   a real 1608541 server writes it, and its value set
//       IS this account's character list. Mining the demo corpus
//       (CODOL-main Tools/demo-re/mine-clientstate.py, 93,042
//       snapshots that decoded to their last bit) gives 686x111,
//       1902x83, 0x51, 792x48, 2056x41, 789x25, 1945x25, 569x24,
//       1978x21, 592x19, 649x15 ... -- ELEVEN of the TWELVE ids
//       section 66a read out of the zone's own mp/playerdata.def
//       (545 569 592 649 686 789 792 1945 1978 2056 2105 2127),
//       and they are the top of the distribution. In the one demo
//       that decodes 6160/6160 the whole value set is
//       {1945, 686, 1902, 0, 570, 649} -- every non-zero one a
//       character item id, no residue at all.
```

### 4.2 五个数字

```text
93,042     解到最后一个位的快照数
x111,x83,x48,x41,x25,x25,x24,x21,x19,x15    十个频率
12         从 mp/playerdata.def 读出的 id 数
11         其中出现在分布顶部的
{1945, 686, 1902, 0, 570, 649}   一个 6160/6160 的 demo 的完整值集
```

### 4.3 而**十二个 id 的完整清单**

```text
545  569  592  649  686  789  792  1945  1978  2056  2105  2127
```

**⚠ 而 §313 的"12 个官方 `cha_*` 角色 id"是：**

```text
545  569  570  592  612  635  649  671  789  792  2056  2105
```

**⇒ 两个清单**只有四个相同**（545/569/592/649）。**

**⚠ 而 `mp/playerdata.def` 的清单有 686/1945/1978/2127 而 §313 有 570/612/635/671。**

**⇒ 所以**两个清单不同**。**

**⚠ 一处需要核对的差异。**

**⇒ 可能 §313 的清单是**默认轮换列表**而这里是**archive 里的全部角色**。**

**✅ 与 §313 的"`10362 cha_zombiehunter` 被踢掉因为它是默认/玩家同款"配合。**

### 4.4 而"**没有一个残余**"

**⇒ 三层**：

```text
1. 一个 6160/6160 的 demo 的完整值集是 `{1945, 686, 1902, 0, 570, 649}`
2. ⇒ **每一个非零值都是一个角色物品 id**
3. ⇒ **没有任何残余**
```

**✅ 极强的证据。**

**⚠ 而 `570` 在 §313 的清单里**没有**（§313 是 569/570？）。

**⇒ 让我核对：§313 说 `569 cha_snibasea` 与 `570 cha_sniveterana`。**

**✅ 所以 **570 在 §313 的清单里** ✓**

**⇒ 那这里说 `570` 是"角色物品 id" ⇒ 一致。**

## 五、证据二：**共现**

```php
//   the COMPANY  in the same corpus it is asserted together with
//       modelIndex 91% of the time, with faction 89% and with
//       female 86% -- i.e. with exactly the three fields dest1yo
//       writes as the rest of the customization group.
```

### 5.1 三个百分比

```text
与 modelIndex   91%
与 faction      89%
与 female       86%
```

**⇒ 三层**：

```text
1. 字段 20（角色物品）与三个定制化字段**共现**
2. ⇒ 91% / 89% / 86%
3. ⇒ **所以它属于同一个定制化组**
```

**✅ 一个**统计共现**证据。**

## 六、证据三：**缺席（一个"定向的负面"）**

### 6.1 那段

```php
//   the ABSENCE  3.3.3.3's storage blob is built by sub_40CAB0,
//       which walks the clientState NETFIELD TABLE from
//       0x00C55B78 = table+0x10 and copies every entry whose
//       offset is 0x14 or in [0x18, 0x68) into a 21-entry
//       {offset,width,type} table -- the one
//       CODOL_CharacterCustomization_UnpackSelectionIds 0x0040CBD0
//       then reads. out.exe references its own clientState table
//       0x00DA8078 exactly three times (sub_471560 twice,
//        sub_6783B0 once) and references table+0x10 ZERO times.
//       A table walker must reference the table, so that is a
//       DIRECTED negative, not a code-shape guess.
```

### 6.2 九层

```text
1. **3.3.3.3 的存储 blob 由 `sub_40CAB0` 构建**
2. ⇒ 它**从 `0x00C55B78` = `table + 0x10` 走 clientState 的 NETFIELD 表**
3. ⇒ 并**把每一个偏移是 `0x14` 或在 `[0x18, 0x68)` 的条目拷进一个 21 项的 `{offset,width,type}` 表**
4. ⇒ **那正是 `CODOL_CharacterCustomization_UnpackSelectionIds 0x0040CBD0` 读的那张**
5. ⇒ **而 `out.exe` 引用它自己的 clientState 表 `0x00DA8078` 恰好三次**
     · `sub_471560` 两次
     · `sub_6783B0` 一次
6. ⇒ **而引用 `table + 0x10` **零次**
7. ⇒ **一个表遍历器【必须】引用那张表**
8. ⇒ **所以那是一个【定向的负面】，不是一个代码形状的猜测**
```

### 6.3 **"定向的负面"**

**✅ 这是本文件里**最重要的一条证据学概念**。**

**⇒ 三层**：

```text
① 普通负面："我没有找到 X" ⇒ 可能因为它不在那里，也可能因为我找的方式不对
② 定向负面："我【按它必须出现的方式】找 X 而【零次命中】"
⇒ 所以 X 确定不在
```

**✅ 与 §265 的"`test byte [reg+11A],4` 在 out.exe 和 OL.exe 里都零次"**完全同族**（第三次"定向负面"）。**

**⇒ 三次：**

```text
§265  svFlags 的 test byte 指令零次
§314  76 项表与 clientState 三处矛盾（间接）
§340  table+0x10 零次引用 ⇒ 遍历器不存在
```

### 6.4 而**"一个表遍历器必须引用那张表"**

**⇒ 三层**：

```text
1. 一个遍历器**必须**引用被遍历的表
2. ⇒ 所以我们知道"它的引用出现在哪里"
3. ⇒ **而 `table + 0x10` 零次 ⇒ 那个遍历器不存在**
```

**✅ 一个**结构必然性论证**。**

## 七、**`SV_PackCharacterCustomization` 与 `ClientInfoCustomizationStorageFields` 是死的**

```php
// So SV_PackCharacterCustomization and
// ClientInfoCustomizationStorageFields stay dead here, and they are
// dead because the SUBSYSTEM is gone, not because eight indexes are
// unknown. Do not re-derive them.
```

### 7.1 四层

```text
1. ⇒ 所以 `SV_PackCharacterCustomization` 与 `ClientInfoCustomizationStorageFields` **留在这里是死的**
2. ⇒ **而它们是死的因为这个【子系统】没了**
3. ⇒ **不是因为有八个索引未知**
4. ⇒ **不要重新推导它们**
```

### 7.2 而 §313 的**两个 `static_assert`**

**§313**：`CharacterSelectionMaximumPayloadBitCount == 72` 与 `CharacterSelectionStorageBitCount == 76`。

**⇒ 而这里说那两个**是死的**。**

**⚠ 所以 §313 的代码**存在但从不执行**。**

**✅ 与 §235 的"注释滞后"、§280 的 `pinnedSession` 同族（第六处"已死的代码被标注"）。**

## 八、**"`82e` 的诊断错而建议对"**（本组第四重要）

```php
// AND section 82e's DIAGNOSIS WAS WRONG WHERE ITS ADVICE WAS RIGHT.
// It compared the two tables BY OFFSET and read "+0x30..+0x3C is 10
// bits on 3.3.3.3 and 6 bits here" as one field whose width
// changed. It is not one field: this build's +0x30..+0x3C are TAG
// indexes, and the model indexes moved to +0x18..+0x28 where they
// are still 10 bits. Comparing by offset is as wrong on a
// rearranged table as comparing by index.
```

### 8.1 五层

```text
1. **§82e 的诊断在它建议对的地方是【错的】**
2. ⇒ 它**按偏移比较两张表**并把"`+0x30..+0x3C` 在 3.3.3.3 是 10 位而这里是 6 位"读成一个宽度变了的字段
3. ⇒ **它不是同一个字段**
4. ⇒ **这个 build 的 `+0x30..+0x3C` 是 TAG 索引，而 model 索引移到了 `+0x18..+0x28`（在那里仍是 10 位）**
5. ⇒ **按偏移比较在一个重排的表上和按索引比较一样错**
```

### 8.2 **"按偏移比较在重排的表上和按索引比较一样错"**

**✅ 与 §4.3 的"偏移匹配与单调对齐都给出错误答案"**完全一致** ✓**

**⇒ 所以**两种比较方式都失效**。**

**⇒ 唯一可靠的是**语义**（值集 / 共现 / 缺席）。**

**✅ 一个**重要的方法论结论**。**

## 九、**四个附件的偏移表**

```php
//     slot  model field  offset    tag field  offset
//       0       33       0x18         57       0x2C     <- the STOWED WEAPON
//       1       34       0x1C         46       0x30
//       2       35       0x20         47       0x34
//       3       44       0x24         48       0x38
//       4       45       0x28         58       0x3C
```

### 9.1 五个槽

| 槽 | model 字段 | 偏移 | tag 字段 | 偏移 |
|---|---|---|---|---|
| 0 | 33 | `0x18` | 57 | `0x2C` | ← **收纳武器** |
| 1 | 34 | `0x1C` | 46 | `0x30` |
| 2 | 35 | `0x20` | 47 | `0x34` |
| 3 | 44 | `0x24` | 48 | `0x38` |
| 4 | 45 | `0x28` | 58 | `0x3C` |

### 9.2 **"索引顺序是乱的（33,34,35,44,45 对 57,46,47,48,58）"**

```php
// Each run is contiguous in the clientState table, so a slot's model and
// tag are at the same POSITION within their run -- and the index order is
// scrambled (33,34,35,44,45 against 57,46,47,48,58), which is exactly why
// reading them as indexes pairs the wrong ones together.
```

**⇒ 三层**：

```text
1. 每一段在 clientState 表里**连续**
2. ⇒ 所以一个槽的 model 与 tag 在**它们各自段的同一个位置**
3. ⇒ 而**索引顺序是乱的** ⇒ **按索引读会把错的配对**
```

**✅ 又一个"索引不是偏移"的实例。**

## 十、**"槽 0 不是我们写的"**

```php
// SLOT 0 IS NOT OURS TO WRITE. Across 14,610 retail clientState entries
// slot 0 carries tag 28 with models 239/240/31 on 709 assertions -- the
// stow model that sub_61B7D0 reads mp/bodyTypeStowModelTable.csv for. The
// other four fire 41-72 times each, which is what leaves them free.
```

### 10.1 五层

```text
1. **槽 0 不是我们写的**
2. ⇒ 在 **14,610 个零售 clientState 条目**里，槽 0 携带 **tag 28** 而 **models 239/240/31** 在 **709 个断言**里
3. ⇒ **那是 `sub_61B7D0` 为 `mp/bodyTypeStowModelTable.csv` 读的收纳模型**
4. ⇒ **其它四个每个只触发 41-72 次**
5. ⇒ **那就是它们空着的原因**
```

**✅ 与 §340 的 `P(tag|model) = 74%` / `P(model|tag) = 98%` / `n = 1690/1279` 一致。**

### 10.2 而**五个槽共享一个数组**

```php
// These land in the SAME ten-slot attachment array a character's own
// pieces occupy: BG_UpdatePlayerDObj reads characterInfo modelName +0x18,
// ten attachment names +0x20 and ten attachment tags +0x48, and this
// server already fills that array on its own DObj. So an attachment here
// is not a prop system, it is the one channel that adds a model to a
// player the client is not predicting.
```

**⇒ 五层**：

```text
1. **它们落在【角色自己的部件所占的同一个十槽附件数组】里**
2. ⇒ `BG_UpdatePlayerDObj` 读 `characterInfo` 的 `modelName +0x18`、十个附件名 `+0x20` 与十个附件 tag `+0x48`
3. ⇒ **而这个服务器已经在它自己的 DObj 上填那个数组**
4. ⇒ **所以这里的一个附件不是一个 prop 系统**
5. ⇒ **它是【唯一那个给客户端未预测的玩家加一个模型的通道】**
```

**✅ 与 §300 的"`characterInfo +0x18` 是 base model name、`+0x20` 是十个附件名"**完全一致** ✓**

**⇒ **第二次确认那三个偏移**。**

## 十一、关键结论

1. **四个字段的索引变更**（`modelIndex` 16→17、`faction` 17→18、`female` 18→19、`color` → 56 且 2→5 位）。
2. **`color` 的位置由"邻域八个槽的七个已确认"推断。**
3. **⭐ "那十六个『缺失』字段不是缺失 —— 这个 build 用一个替代了它们"**。
4. **3.3.3.3 的 76 位 blob（八字段）+ 四对附件 → 本 build 一个 16 位角色物品 id。**
5. **三条独立证据**：值集（93,042 快照）、共现（91%/89%/86%）、**缺席（定向的负面）**。
6. **`mp/playerdata.def` 的十二个 id** 与 §313 的十二个**只有四个相同** —— 一处需核对的差异。
7. **⭐ "定向的负面"**：`table+0x10` 零次引用 ⇒ 遍历器不存在（第三次该概念）。
8. **"一个表遍历器必须引用那张表"** —— 一个结构必然性论证。
9. **`SV_PackCharacterCustomization` 与 `ClientInfoCustomizationStorageFields` 是死的**，因为**子系统没了**而不是索引未知。
10. **⭐ "§82e 的诊断错而建议对"** —— 按偏移比较在重排表上和按索引一样错。
11. **五个附件槽的偏移表**，而**索引顺序是乱的**（33,34,35,44,45 vs 57,46,47,48,58）。
12. **"槽 0 不是我们写的"** —— 它是收纳武器（tag 28、models 239/240/31、709 次断言）。
13. **五个槽共享角色自己的十槽附件数组**，而 `BG_UpdatePlayerDObj` 读 `+0x18`/`+0x20`/`+0x48`（第二次确认）。

## 十二、未闭合点

- 两份十二个角色 id 清单的差异。
- `color` 的 5 位宽 vs §315 的 `color <= 3`。
- `1902` 是角色 id 还是别的（它不在 §313 或 `playerdata.def` 的清单里）。
- `sv_snapshot_mp.cpp` 5600 行之后未读取（27,016 行，进度 21%）。
