from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\docs\PHASE7_COMBAT_WORLD_INVENTORY_20261023.md')
s=p.read_text(encoding='utf-8')
s=s.replace('| `sprint_duration_scale` | `0x9A8` |\n', '| `sprint_duration_scale` | `0x9A8` |\n| `location_damage_multipliers[20]` | `0xD74` |\n')
s=s.replace('| r870_mp | 8 | 192 | 50 | 0 | 250 / 400 |\n', '| r870_mp | 8 | 192 | 50 | 0 | 250 / 400 |\n\n命中部位倍率已验证：M4/AK47 头部 `1.2`，MP5K 头部 `1.1`，R870 头部 `1.0`，狙击头部 `3.0`；上躯干倍率随武器为 `1.0–1.75`。\n')
s=s.replace('## 仍未闭合\n\n1. 武器配件/合成表：`weaponattach`、marketplace item、attachment override。', '## 仍未闭合\n\n1. 武器配件/合成表：已提取 3.19 type-43 附件元数据（259 条可见 metadata，27 条 unresolved），但 3.19 的 override tuple 布局与 1.1.1.13 不同；尚未把它应用到 WeaponDef。')
s=s.replace('6. game mode、round、score、spawn/respawn/match end 状态机。', '6. game mode、round、score、spawn/respawn/match end 状态机。\n7. 爆炸/溅射参数已具备从 WeaponDef 继续提取的入口，但尚未接入伤害结算。')
p.write_text(s,encoding='utf-8')
print('updated inventory')
