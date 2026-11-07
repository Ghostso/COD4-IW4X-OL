from pathlib import Path
p=Path(r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_SERVER_319_20261021\docs\PHASE7_WEAPONATTACH_REVERSE_BOUNDARY_20261023.md')
s=p.read_text(encoding='utf-8')
s += '''\n## 2026-10-23 追加定位\n\n3.19 客户端的资产类型表进一步确认：\n\n- type-name pointer array: `0x00E5C800`\n- type accessor/callback array: `0x00E5C8C0`\n- type size/accessor array: `0x00E5CA30`\n- type43 size callback returns `0x0C`，与 12B weaponattach header 一致\n- type45 name pointer is `weaponattach`\n\n因此目录 type 43 是 `weaponattach`，不是车辆。附件资产的 12B header 位于：\n\n```text\nasset_offset + 0x28\n```\n\n其中：\n\n```text\n+0  u32 name_ref (0xFFFFFFFF = inline)\n+4  u32 count\n+8  u32 entries_ref\n+12 char name[]\n```\n\n当前未闭合的是 name 后的 override payload 编码；不能再按 1.1.1.13 的 12B tuple 解释。\n'''
p.write_text(s,encoding='utf-8')
print('updated boundary doc')
