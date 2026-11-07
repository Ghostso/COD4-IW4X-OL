# CODOL 3.19 武器索引表（名称 ↔ 引擎编号）

2026-10-25　数据源：本机 `COD OL\main\*.ff`（逐块 CTR + zlib 解包，脚本在目录内，只读可复跑）

## 交付物

| 文件 | 内容 |
|---|---|
| **`codol_weapon_index_3_19.csv`** | **武器表**：`engine_index` ↔ `name` + 实测属性，1136 行 |
| **`CODOL_3.19_道具表.xlsx`** | **道具表**：经验卡/名片/徽章/称号/边框/名牌/表情等，2969 行 |
| `codol_items_3_19.csv` | 道具表 CSV 版 |
| `localize_zh.csv` | 本地化对照：11365 条 `键 → 中文` |
| `zone_name_pool.txt` | zone 内武器名池原文（1134 个，按字母序） |
| `codol_weapon_table_3_19.csv` | 全量 type-28 资产表（1134 行，含 dir_index / 资产大小） |
| `st*/` | 各 zone 的 stringtable 全量 CSV |
| `*.py` | 解析脚本（全部只读、可重跑） |

## 公式

```
engine_index = pool_index + 2
```

`pool_index` = 武器名在 `common_mp.zone` 里那个**连续字母序名字池**中的位置。
前两个槽是隐式定义：

```
0  none
1  defaultweapon_mp
2  aa12_mp          <- pool[0]
...
585 m4a1tech_mp     <- pool[583]
646 m9_mp
1112 vector_mp
1135 zombie_cymbal_monkey  (池的最后一个)
```

## 锚点验证（三中三）

来自 `composite-gamestate-candidate.json` 里我们自己的实跑记录（`baseWeapon` 字段）：

| 武器 | pool_index | +2 | 实测 |
|---|---|---|---|
| m4a1tech_mp | 583 | **585** | 585 ✓ |
| vector_mp | 1110 | **1112** | 1112 ✓ |
| m9_mp | 644 | **646** | 646 ✓ |

三个独立锚点同时命中，且它们**互不相邻**（583 / 644 / 1110），排除了巧合。

## 名字池的位置（可复算）

`common_mp.zone` 偏移 **`0x34eeb` .. `0x396eb`**（18424 字节）。
前面是 `0xFF` 填充，池内是连续的 NUL 分隔 token：

```
aa12_mp\0aa12anniversarya_mp\0aa12anniversaryb_mp\0...
```

共 1134 个 token，**全部唯一、无重复**，其中 1129 个以 `_mp/_so/_zm` 结尾，
另外 5 个是 `bow_arrow_mp_cupid`、`bow_arrow_mp_fire`、`destructible_car`、
`flare_callforsupport`、`zombie_cymbal_monkey`（同样是武器定义）。

## 怎么复算

```bash
# 1. 解包 zone
python CODOL_SERVER_319_20261021\tools\codol_ff_unpack.py "COD OL\main\common_mp.ff" common_mp.zone

# 2. 重建表
python _weapon_table_20261025\build_final_index.py
```

`build_final_index.py` 内建三条锚点断言，不通过会直接 `assert` 失败。

## 注意

- 这是 **stock 定义**的索引（0..1135）。运行时在它之后追加的**合成/改装武器**索引
  见 [`codol_dynamic_index_model.md`](codol_dynamic_index_model.md)：
  **动态武器索引 = configstring 索引 − 5960**（实测 `7184 − 5960 = 1224`
  = `firstDynamicWeapon`），`** <base> <v8> <v9> <附件...>` 里的 `<base>`
  就是本表的索引（41 个 base 中 40 个能对上真枪名）。
- 旧文档里的 CS_WEAPONS 窗口表（CS 5363..5537，来自 1.1.1.13）**不适用本 build**：
  3.19 的 `code_post_gfx_mp.ff` 里 `constconfig` 零命中。
