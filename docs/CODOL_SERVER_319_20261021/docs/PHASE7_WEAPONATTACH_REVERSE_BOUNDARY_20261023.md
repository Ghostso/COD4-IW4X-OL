# Phase 7 weaponattach 逆向边界（2026-10-23）

## 已确认

3.19 客户端资产类型名表中：

- 目录 type 28 对应 `weapon`
- 目录 type 43 对应 `weaponattach`
- `weaponattach` 类型名 VA = `0x00DB5CF0`
- 类型名指针表起点 VA = `0x00E5C800`
- 类型回调/访问器表起点 VA = `0x00E5C8C0`

`common_mp_zone.bin` 中：

- type 43 资产：285
- 可找到 metadata 的资产：259
- 未解析资产：27
- metadata 位置通常在资产 `+0x28`，少数为 `+0x04`

metadata 结构：

```text
u32 name_ref   = 0xFFFFFFFF
u32 count
u32 entries_ref = 0xFFFFFFFF
char name[]
```

## 不能直接套用的地方

1.1.1.13 参考实现中，name 后固定跟着：

```text
count * 12 bytes {u32 offset, u32 type, u32 value}
```

3.19 zone 中这个假设不成立：

| attachment | count | tail after name |
|---|---:|---:|
| fmj_base | 4 | 8 B |
| scope_none | 1 | 1 B |
| flashhider_base | 8 | 56 B |
| akimbo_base | 5 | 20 B |
| heartbeat_base | 8 | 211 B |
| silencer_m4 | 14 | 212 B |

因此 3.19 的 override 数据是变长/压缩/分块格式，不能按 12B tuple 解释。

## 下一步唯一正确入口

需要继续追 3.19 客户端里的 `weaponattach` 资产加载器，而不是继续读文件尾部猜结构。类型名表已定位：

```text
type names: 0x00E5C800
callbacks:  0x00E5C8C0
```

下一步应做：

1. 从 `0x00E5C8C0` 的调用链继续反向到 type 43 loader。
2. 找到 loader 后确认 name/count/entry 实际读取顺序。
3. 再生成可验证的 override 表。

## 2026-10-23 追加定位

3.19 客户端的资产类型表进一步确认：

- type-name pointer array: `0x00E5C800`
- type accessor/callback array: `0x00E5C8C0`
- type size/accessor array: `0x00E5CA30`
- type43 size callback returns `0x0C`，与 12B weaponattach header 一致
- type45 name pointer is `weaponattach`

因此目录 type 43 是 `weaponattach`，不是车辆。附件资产的 12B header 位于：

```text
asset_offset + 0x28
```

其中：

```text
+0  u32 name_ref (0xFFFFFFFF = inline)
+4  u32 count
+8  u32 entries_ref
+12 char name[]
```

当前未闭合的是 name 后的 override payload 编码；不能再按 1.1.1.13 的 12B tuple 解释。

## 关键发现：type43 payload 是“编码后的字段流”，不是 12B tuple

3.19 中：

- `0xAF0790` = `%c%c%c%c` / `%c%c%c=` / `%c%c==` base64 encoder
- `0xAF0920` = encoder wrapper
- `0x49CC70` 通过 `0xE5CA30[type]` 取 type 固定大小，然后拷贝资产
- `0xE5CA30[43] = 0x4834D0`，返回 `0x0C`
- `0xE5CA30[45] = 0x4834E0`，返回 `0x30EC`

因此：

- 目录中的 type 43 资产的 12B header 是 `{name_ref,count,entries_ref}`
- 名字后不是 1.1.1.13 的 12B tuple 数组，而是 3.19 自有的变长字段流
- 可变字段流最终被编码/序列化为附件数据；当前观察到 `07 08/06/03 ...`、`00 04 ...`、`0A 03 ...`、`0E 03 ...` 等稳定 opcode

这解释了不同附件 `count` 与尾部长度不成 12 倍关系。

## 下一步

以 `0xAF0790` / `0xAF0920` 及 `0xAF0920` 上游解析器为入口，恢复：

1. 字段流 opcode 表
2. 每个 opcode 的 payload 长度
3. 与 WeaponDef 的 offset 映射
4. 多个附件叠加顺序

## 纠正：payload 不是 base64 文本

`0xAF0790` 的字符表确实是 base64，但这只是 C1 某条编码路径，不是 type43 payload 的编码。type43 payload 实测为二进制且以 `07 08 21 75 ...` 等字段流开头；尝试按 4 字符一组反转时 284/285 条在第一组就失败。

因此撤回“payload 是编码文本流”的假设，保留已证实的资产 header 和真实 payload 字节。

已确认：

```text
asset = [12B header][NUL name][payload bytes]
header = {name_ref=0xFFFFFFFF, count, entries_ref}
```

285/285 条 type43 都能按这个真实基点解析，0 条短资产。

下一步应直接依据 payload 的 opcode 边界（`07 08 ...`、`00 04 ...`、`0A 03 ...`、`0E 03 ...`）恢复字段流语法。

## 2026-10-23 最终边界（本轮）

本轮继续追踪 `0x31xxxxxx` 后，已确认它不是可直接用 `文件偏移 = 低24位 + 固定基址` 解释的普通指针：

- 同一 token 会出现在不同附件中，而这些附件关联的本地字符串组不同；例如 `0x317c1f41` 的引用分布于多个枪声/枪口焰上下文中，`0x317c197f` 分布于多个瞄具/ADS 上下文中。
- 64 个附件同时有本地尾表和引用，其中 42 个的唯一引用数不超过本地字符串数；抽查这些样本时，首次出现的唯一引用顺序与字符串表顺序一致。另有 168 个附件带引用却没有本地尾表，说明还存在共享槽位/资源池。
- 已抽样验证多个固定基址假设（`0x119b688`、`0x1950000`、`0x317a000`、`0x31a0000` 等）；没有任何单一基址能同时解释局部和共享引用。
- 因此运行时继续保留 token，不把未解析引用误写成索引；`weaponattach.c` 只应用已确认的 scalar 字段，未闭合引用记录显式计为 skipped。

可复核统计（`fixtures/common_mp_weaponattach_records_20261023.json`）：

| 项 | 数量 |
|---|---:|
| type-43 assets | 285 |
| 12B records | 4912 |
| assets with local trailing strings | 73 |
| reference records (`0x30`/`0x31`) | 3750 |
| assets carrying references | 232 |
| assets with both local strings and references | 64 |
| of those, unique token count <= local string count | 42 |
| unique `0x30`/`0x31` reference tokens | 272 |
| records with type 0/10/12/14/15 (string/resource class) | 545 |
| scalar-class records (types 4/6/7/9/20) | 879 |
| type-0 records (indices 3/4/5; mostly string handles) | 3625 |
| scalar records applied | 172 / 879 |

下一步必须从 3.19 客户端的 type-43 reader / shared string-table accessor 继续，而不是继续猜文件尾部或固定基址。

## 2026-10-23 外部参考交叉验证

本机 IW4X 参考实现 `Components/Modules/Zones.cpp` 的
`LoadWeaponAttachStuff` 明确给出同构线索：

```text
Game::Load_Stream(true, tuple, 12 * count);
if (tuple[0] < 16 || tuple[0] == 39)
    if (tuple[2] == -1)
        tuple[2] = allocate_stream_position();
        Load_XStringCustom(tuple[2]);
tuple += 3;
```

对应到 3.19 的 12B 记录 `{type,index,flags,field,value}`：

- 3.19 记录中 `type` 是 3.19 自有字段/资源分类，`index` 是字段槽位；IW4X 的 `tuple[0]` 仅能作分类提示，不能按数值逐项等同
- `type < 16 || type == 39` 的条目需要走字符串/资源读取路径；其中 3.19 已验证的数值类型 `7/9` 例外
- 3.19 里已经看到 `type=0/10/12/14/15` 的字符串/资源类（合计 545 条），以及 `type=7/9` 的标量类
- 当前 `raw_offset` 的高位有序列化噪声，低 16 位与 WeaponDef 字段 offset 自洽

3.19 参考证据和 IW4X 的关键差异仍在：

- 3.19 的字符串记录允许 `flags` 携带额外信息，且同一个 `0x31...` 值可在不同资产上下文映射到不同字符串
- 因此只能把“index 分类”作为已验证语义，不能把 IW4X 的绝对地址直接搬进 3.19 文件解析

结论：

- 标量应用保持现状
- 字符串/资源类记录继续显式 skipped
- 下一步从 `index=3/4/5` 的字符串表绑定路径继续

