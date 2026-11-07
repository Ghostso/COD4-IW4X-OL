# -*- coding: utf-8 -*-
"""Finalize the dynamic weapon index model and emit the reference files.

MODEL (all four parts independently anchored):

  1. stock weapon index       : 0..1155, from zone name pool + 2
       none=0, defaultweapon_mp=1, pool[i] = i+2
  2. CS_WEAPONS block         : configstring 5960 + weapon_index
       (weapon cfgstr = base)

  3. dynamic weapon index     : configstring_index - 5960
       verified: retail '** 646 0 0 8738 9321' at cs 7184
                 -> 7184 - 5960 = 1224 == measured firstDynamicWeapon

  4. modular string format    : '** <base> <value8> <value9> <attach...>'
       <base> IS a stock weapon index (40/41 bases resolved to real guns)
       <value8> measured nonzero only as 11 and 72 (slot/flag byte)
       <value9> always 0 in this corpus
       trailing numbers are attachment asset indices
"""
import re, csv, io, sys, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

BASE = r'D:\BaiduNetdiskDownload\使命召唤OL\_weapon_table_20261025'
CS_BASE = 5960
FIRST_DYN_CS = 7184

stock = {}
for r in csv.DictReader(open(BASE + r'\codol_weapon_index_3_19.csv', encoding='utf-8-sig')):
    stock[int(r['engine_index'])] = r

text = open(r'D:\BaiduNetdiskDownload\使命召唤OL\_LEARN_TESTOL_DELIVERY2\decoded\str-CodolGameServer.txt',
            'rb').read().decode('latin-1', 'replace')
pat = re.compile(r'\*\*[ ]+(\d+)[ ]+(\d+)[ ]+(\d+)((?:[ ]+\d+)*)')

seen = {}
for m in pat.finditer(text):
    base, v8, v9 = int(m.group(1)), int(m.group(2)), int(m.group(3))
    atts = tuple(int(x) for x in m.group(4).split()) if m.group(4).strip() else ()
    seen.setdefault((base, v8, v9, atts), 0)
    seen[(base, v8, v9, atts)] += 1

out = BASE + r'\codol_modular_weapons.csv'
with open(out, 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['base_index', 'base_name', 'value8', 'value9',
                'attachment_count', 'attachments', 'config_string', 'occurrences'])
    for (b, v8, v9, atts), n in sorted(seen.items()):
        nm = stock.get(b, {}).get('name', '')
        cfg = ' '.join(['**', str(b), str(v8), str(v9)] + [str(a) for a in atts])
        w.writerow([b, nm, v8, v9, len(atts), ' '.join(map(str, atts)), cfg, n])

print('wrote', out, '->', len(seen), 'distinct modular weapon definitions')
all_bases = {b for (b, _, _, _) in seen}
resolved = sum(1 for b in all_bases if b in stock)
print('bases resolving to a named stock weapon: %d / %d distinct bases'
      % (resolved, len(all_bases)))

dyn = BASE + r'\codol_dynamic_index_model.md'
open(dyn, 'w', encoding='utf-8').write(f"""# CODOL 3.19 动态武器索引

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
python _weapon_table_20261025\\dynamic_formula.py
python _weapon_table_20261025\\check_bases.py
python _weapon_table_20261025\\decode_dynamic.py <gamestate字符串导出>
```
""")
print('wrote', dyn)
