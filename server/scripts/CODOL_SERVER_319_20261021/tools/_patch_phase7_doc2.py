from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\docs\PHASE7_COMBAT_WORLD_INVENTORY_20261023.md')
s=p.read_text(encoding='utf-8')
s=s.replace('命中部位倍率已验证：M4/AK47 头部 `1.2`，MP5K 头部 `1.1`，R870 头部 `1.0`，狙击头部 `3.0`；上躯干倍率随武器为 `1.0–1.75`。\n', '命中部位倍率已验证：M4/AK47 头部 `1.2`，MP5K 头部 `1.1`，R870 头部 `1.0`，狙击头部 `3.0`；上躯干倍率随武器为 `1.0–1.75`。`codol_weapondef_damage_for_hit()` 已包含距离衰减与 hit location 倍率。\n')
s=s.replace('- `tests/test_weapondefs.c`\n', '- `tests/test_weapondefs.c`\n- `fixtures/common_mp_weaponattach_metadata_20261023.json`（附件元数据，override 布局待闭合）\n')
s=s.replace('7. 爆炸/溅射参数已具备从 WeaponDef 继续提取的入口，但尚未接入伤害结算。\n7. 完整实机验证：客户端接收真实快照、受伤、死亡、计分、回放。', '7. 爆炸/溅射参数已具备从 WeaponDef 继续提取的入口，但尚未接入伤害结算。\n8. 完整实机验证：客户端接收真实快照、受伤、死亡、计分、回放。')
p.write_text(s,encoding='utf-8')
print('patched')
