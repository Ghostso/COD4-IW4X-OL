# Phase 7 战斗世界清单（2026-10-23）

> 证据基座：`run_codol_001/runs/OMIT_RETEST_20261022/mem/mem_005.bin`
> 地图数据：`_map_extract/coop_train_zone.bin`
> 武器数据：`run_codol_001/runs/PHASE7_STATIC_20261023/common_mp_zone.bin`
> 纪律：OLmod、alpha0022、其他版本的源码只作为字段命名/结构提示；最终进入本表的偏移必须在 3.19 字节或 3.19 zone 中自洽。

## 已完成

| 项 | 3.19 证据 | 产物 |
|---|---|---|
| 出生点 | `info_player_start_so = 48 -572 -116` | `_map_extract/coop_train_spawns.json` |
| MapEnts 触发体 | TriggerModel/Hull/Slab 直接从 zone 解码 | `tools/clipmap_locate.py` |
| ClipMap 平面 | 27 个 `cplane_s`，20B/项，法线自检 | `fixtures/coop_train_clipmap_20261023.json` |
| ClipMap 材质 | 4 个 `ClipMaterial`，12B/项 | 同上 |
| BrushSide | 27 个 8B side，plane 指针步长 20B | 同上 |
| Brush | 30 个 36B `cbrush_t` | 同上 |
| Brush bounds | 30 个 24B Bounds | 同上 |
| Brush contents | 30 个 u32 contents | 同上 |
| 实体模型映射 | `*71..*99` 对应 cbrush 1..29，叠加实体 origin | `include/codol_clipmap_coop_train.inc` |
| AABB 碰撞 | 精确 bounds 替换旧 64³近似，测试验证半宽 8/4 | `src/world/collision.c`、`tests/test_collision.c` |

## 武器数据进展

`common_mp_zone.bin` 的 XAsset 目录：

- 目录起点 `0xFC24`
- 8557 条 16B 记录 `{type, offset, ptr, size}`
- 目录结束 `0x312F4`
- type 28 共 1134 条
- 其中 878 条可由 `SF_WEAPON_<NAME>_MP_NAME` 恢复名称
- firingrange 武器名单 18 把全部找到

已由 M4A1TECH、AK47、R870、MP5K 四个武器交叉验证的字段：

| 字段 | 3.19 zone offset |
|---|---:|
| `clip_size` | `0xE90` |
| `fire_time_ms` | `0xE98` |
| `reload_ms` | `0x884` |
| `reload_empty_ms` | `0x890` |
| `reload_add_ms` | `0x898` |
| `damage` | `0xD38` |
| `player_damage` | `0xD3C` |
| `min_damage` | `0xD40` |
| `min_player_damage` | `0xD44` |
| `max_damage_range` | `0xD50` |
| `min_damage_range` | `0xD58` |
| `move_speed_scale` | `0x9A0` |
| `ads_move_speed_scale` | `0x9A4` |
| `sprint_duration_scale` | `0x9A8` |
| `location_damage_multipliers[20]` | `0xD74` |

样本值：

| weapon | clip | fire ms | damage | min damage | range max/min |
|---|---:|---:|---:|---:|---:|
| m4a1tech_mp | 30 | 71 | 33 | 33 | 500 / 1800 |
| ak47_mp | 30 | 96 | 45 | 33 | 1600 / 2250 |
| mp5k_mp | 30 | 74 | 40 | 33 | 675 / 1100 |
| r870_mp | 8 | 192 | 50 | 0 | 250 / 400 |

命中部位倍率已验证：M4/AK47 头部 `1.2`，MP5K 头部 `1.1`，R870 头部 `1.0`，狙击头部 `3.0`；上躯干倍率随武器为 `1.0–1.75`。`codol_weapondef_damage_for_hit()` 已包含距离衰减与 hit location 倍率。

产物：

- `tools/export_weapondefs.py`
- `fixtures/common_mp_weapondefs_20261023.json`
- `include/codol_weapondefs.h`
- `include/codol_weapondefs_firingrange.inc`
- `src/battle/weapondefs.c`
- `tests/test_weapondefs.c`
- `fixtures/common_mp_weaponattach_metadata_20261023.json`（附件元数据，override 布局待闭合）

## 仍未闭合

1. 武器配件/合成表：已提取 3.19 type-43 附件元数据（259 条可见 metadata，27 条 unresolved），但 3.19 的 override tuple 布局与 1.1.1.13 不同；尚未把它应用到 WeaponDef。
2. 后坐力、扩散、ADS 精度、移动/姿态对扩散的完整公式。
3. 角色命中盒几何、护甲/穿透；武器侧距离伤害和 hit-location multiplier 已闭合。
4. 手雷、爆炸、溅射、焚烧和投掷物生命周期。
5. actor、载具、炮塔、loot、objective 的生命周期。
6. game mode、round、score、spawn/respawn/match end 状态机。
7. 爆炸/溅射参数已具备从 WeaponDef 继续提取的入口，但尚未接入伤害结算。
8. 完整实机验证：客户端接收真实快照、受伤、死亡、计分、回放。

## 当前结论

Phase 7 尚未完成，但“地图碰撞数据”和“基础武器定义”已经不再是猜测：

- 地图：已有 3.19 zone 直接提取的 30 个 brush、27 个 side、27 个 plane、30 个 bounds。
- 武器：已有 3.19 common_mp 直接提取的 18 把对局武器基础参数。
- 测试：`test_collision`、`test_weapondefs` 及全量 19 个测试通过。

下一轮应从 `weaponattach`/配件覆盖和射击命中盒开始，而不是继续扩大静态表清单。


## 2026-10-23 WeaponDef offset correction and attachment application

XAsset offsets are relative to the zone body (`zone + 0x28`), not the raw file.
The old field offsets were 0x28 too high.  Corrected offsets:

| field | offset |
|---|---:|
| clip_size | 0xE68 |
| fire_time_ms | 0xE70 |
| reload_ms | 0x85C |
| reload_empty_ms | 0x868 |
| reload_add_ms | 0x870 |
| damage | 0xD10 |
| player_damage | 0xD14 |
| min_damage | 0xD18 |
| min_player_damage | 0xD1C |
| max_damage_range | 0xD28 |
| min_damage_range | 0xD30 |
| location_damage_multipliers | 0xD4C (20 floats) |
| move_speed_scale | 0x978 |
| ads_move_speed_scale | 0x97C |
| sprint_duration_scale | 0x980 |

All 18 firingrange weapon values were re-exported from the corrected asset base.

Type-43 attachment payload is now parsed as:

```text
12B header {name_ref, count, entries_ref}
NUL name
count x 12B record {u8 type, u8 index, u16 flags, u32 raw_offset, u32 value}
optional NUL-terminated string table
```

`raw_offset & 0xFFFF` is the WeaponDef field offset.  Valid scalar records are
exported to `include/codol_weaponattach_scalar_firingrange.inc` and applied by
`src/battle/weaponattach.c`.  `type 7` is float, `type 4` int, `type 6` bool,
`type 9` millisecond duration.  Records beyond the currently decoded WeaponDef
subset are counted as skipped, not applied blindly.

Evidence:
- `fixtures/common_mp_weaponattach_records_20261023.json`
- `include/codol_weaponattach_scalar_firingrange.inc`
- `include/codol_weaponattach_names.inc`
- `src/battle/weaponattach.c`
- `tests/test_weapondefs.c`
- verified full regression: 19/19 tests passed

## 2026-10-23 WeaponAttach reference boundary (shared string/resource slots)

Verified against `fixtures/common_mp_weaponattach_records_20261023.json`:

- type-43 assets: 285
- 12-byte records: 4912
- assets with a trailing NUL string table: 73
- assets with both local strings and references: 64
- of those, unique token count <= local string count: 42
- assets carrying a `0x30`/`0x31` reference token: 232
- reference records: 3750 (type 0: 3486; type 12: 101; type 14: 86; type 10: 48; type 40: 25; type 15: 3; type 13: 1)
- unique `0x30`/`0x31` reference tokens: 272
- scalar records currently applied by `weaponattach.c`: 172 / 879 (19.6%)

The `0x30`/`0x31` value is not a directly usable raw file pointer.  Some
records are consistent with local string-table slot references; others appear
to be shared-slot references whose resolver lives outside the attachment.  A single token can occur in many attachments and resolve to
different strings in different asset contexts, for example:

- `0x317c1f41` appears in 45 records and its associated local string-table
  contexts contain different suppressor fire sound groups
- `0x317c197f` appears in 18 records and its associated local string-table
  contexts contain different optic ADS/tag groups
- `0x317d9c51` / `0x317d9c60` appear in hundreds of GL records and map to
  different viewmodel animation stages

For 42 of the 64 attachments that have both local strings and references,
the unique-token count does not exceed the local string count.  In inspected
samples, first-occurrence token order is consistent with trailing-string order.
This is a useful parser-side invariant, but it is not yet a complete runtime dereference rule because
168 assets carry reference tokens without a local trailing string table
(shared slots).

### What is safe to consume now

- scalar attachment overrides with verified `WeaponDef` offsets
- `highcal_base` `0x0D54` -> `location_damage_multipliers[2]` (`CODOL_HITLOC_HEAD` in the current runtime enum); neighboring slot labels remain unconfirmed
- type 7 float, type 4 int, type 6 bool, type 9 milliseconds

### What remains explicitly unclosed

- global shared-string/resource slot resolver
- `0x30`/`0x31` shared-slot dereference for all 168 assets with references but no local trailing string table
- `fmj_base` `0xE78` penetration semantics
- recoil, spread, ADS accuracy
- hitbox geometry / armor / penetration
- explosions, actors, vehicles, objectives, round/score/spawn/match-end

The runtime keeps unresolved type-0 string handles out of the scalar table
instead of guessing a string table index.

## 2026-10-23 IW4X cross-check

The local IW4X reference (`Components/Modules/Zones.cpp`,
`LoadWeaponAttachStuff`) confirms that a weapon-attachment override tuple
is three dwords and that its first dword is a field/resource discriminator.
The numeric values are version-specific, so this is used only as a layout hint.

Applied to the 3.19 record layout `{type,index,flags,field,value}` this means:

- `type` is the field/resource discriminator; `index` is the field slot
- 545 records with type 0/10/12/14/15 are in the string/resource class
- type-7/type-9 records are numeric and may be applied through field offsets
- the type-0 handle stream still needs its loaded binding validated
- scalar records remain the only subset currently applied to `WeaponDef`

The IW4X addresses and pointer widths are not copied into the 3.19 parser;
only the structural rule is retained as cross-version evidence.


## 2026-10-23 Final WeaponDef / attachment boundary

locator table.
Raw-zone verified: clip/rate/reload/damage, range, movement scales, 20-value
Unverified cross-version candidate: hip spread +0x810..+0x824,
ADS spread +0xAC0, six-point damage +0xBB4/+0xBCC, 21 hit-location multipliers
+0xBF0. Zone-body cross-checks disproved +0xBB4/+0xBCC/+0xBF0 for 3.19;
none of these offsets is treated as a 3.19 runtime fact.

Runtime attachment coverage after conservative scalar regeneration: 44 type-43
assets, 94 scalar records; 545 string/resource records remain explicitly
skipped; no unresolved 0x31xxxxxx token is interpreted as a file pointer.

Full-match completion is tracked in INMATCH_COMPLETENESS_GAP_MATRIX_20261023.md.
## 2026-10-23 最终布局证据校正（本轮）

- 3.19 zone 的 18 把 firingrange 武器均在资产体 `+0x101C` 结束，与运行时 `WeaponDef` 大小 `0x101C` 相同；这只证明资产大小一致，不能证明最终运行布局偏移可直接套用到 zone 体。
- 将 `+0xBB4/+0xBCC/+0xBF0` 直接套到 3.19 zone 后，读到的是动画、边界和骨骼参数，而非六段伤害、距离和 21 项命中倍率。因此这些字段在本版本中再次降级为 `UNVERIFIED`。
- OLFinal/3.3.3.3 的 `WEAPON_DEFINITIONS_RVA=0x13F5A40` 与 `WEAPON_COUNT_RVA=0x7417B88` 在 3.19 PE 中无对应引用，读值全零；不能作为 3.19 证据。
- `tools/export_weapondefs_runtime.py` 已改为 fail-closed 探针：显式验证旧地址为零，并输出 `runtime-layout-unverified`，不生成伪数据。
- 仍可信的 3.19 武器数据只有 zone 直接验证的字段：射速、弹匣、换弹、基础/最小伤害、最大/最小距离、移动倍率和 20 项位置倍率。

## 2026-10-23 Snapshot codec 校正

- 写入器 `bw_index()` 已改为原生 `0x670CB0` 的 `bw_run()`，按表宽传入 index bits；playerState 使用 7 位。
- 新增 `tests/test_snapshot_run.c`，用独立 7 位解码器验证首字段 run。
- 现有 141B 黄金向量仍能通过；但历史实机报告记录该载荷未被客户端 ack，且 124B 读向量完整可消费而写侧仍冲突。Phase 3 因此改为 `PARTIAL`，不再声称完整快照 codec 已收口。


## 2026-10-23 第二轮闭合：六段伤害、命中映射、附件类型

- 3.19 zone 的六段伤害数组固定在资产偏移 `0xD10`，六段距离固定在 `0xD28`；18/18 firingrange 武器逐项一致，首项分别等于 `damage` 和 `max_damage_range`。
- 零值伤害档表示沿用前一个非零档，零值距离表示空槽；曲线超出最后一档时使用最后一个非零伤害档。
- 原始字符串表 `hitloc_mapping` 已恢复：20 个槽位 `0..19` 依次为 `none/helmet/head/neck/torso_upper/torso_lower/right_arm_upper/.../shield`。
- 运行结构已增加 `damage_tiers[6]`、`damage_ranges[6]`，本轮静态基线先为 21/21，最终静态闭合为 22/22。
- WeaponAttach 的 `0xD10..0xD1C` 记录是浮点倍率，不是整数绝对伤害；运行时只对相应档位与基础字段做倍率缩放。
- 投掷物专用字段仍未命名。普通手雷/闪光/烟雾/C4 的 `0x76C..0x798`、`0x984..0x9EC` 大量相同，RPG 在 `0x984..` 出现 `25/30` 等差异；目前不足以安全命名为 fuse/radius。
