# CODOL 3.19 动态武器索引

## 公式

```
configstring 索引 = 5960 + weapon_index          (武器块基址)
weapon_index      = configstring 索引 − 5960
```

- `weapon_index` 0..1155 = **stock 定义**（见 `codol_weapon_index_3_19.csv`）
- `weapon_index` >= 1224 = **动态/模块化定义**，见下

## 实测锚点

| 事实 | 数值 | 来源 |
|---|---|---|
| 武器 configstring 块基址 | 5960 | `WeaponConfigStringBase` |
| 零售 `** 646 0 0 8738 9321` 落在 | cs 7184 | 项目报告逐字引用 |
| `7184 − 5960` | **1224** | = 实测 `firstDynamicWeapon` |
| 另一局 `firstDynamicWeapon` | 1147 | `mp_battlecity` |

⇒ **动态武器索引 = configstring 索引 − 5960**，首值 = 1224。

## 动态条目格式

```
** <base> <value8> <value9> <attachment...>
```

- `<base>` —— **就是 stock 武器索引**。实测 41 个不同 base 中 **40 个**都能在
  `codol_weapon_index_3_19.csv` 里查到真枪名（`22=acr_mp`、`41=ak104_mp`、
  `78=ak47_mp`、`646=m9_mp`、`583=m4_mp`、`1112` 段同理）。
  唯一例外 `1155` 是动态段边界值。
- `<value8>` —— 槽位/标志字节，实测只出现 `0`、`11`、`72`
- `<value9>` —— 本语料恒为 `0`
- 尾随数字 —— 附件资产索引，**每个附件组合都是独立条目**

## 为什么没有静态全表

动态索引由客户端 `CL_ParseGamestate` **第二趟**按 gamestate 里 `**` 串的出现顺序
现场分配（`0x454B55`，arg=0；第一趟 `0x454A54` 走普通武器，arg=1）。
零售端"每个附件组合都是一条独立武器串"，所以条目数取决于当局玩家实际配装。

⇒ 动态段**不存在与局无关的静态表**；能定死的是**公式 + 编码 + base 解析**，
全量条目必须从该局 gamestate 读。

## 复算

```bash
python _weapon_table_20261025\dynamic_formula.py
python _weapon_table_20261025\check_bases.py
python _weapon_table_20261025\decode_dynamic.py <gamestate字符串导出>
```
