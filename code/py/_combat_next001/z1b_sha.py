# -*- coding: utf-8 -*-
import hashlib, os
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL'
FILES = ['COMBAT_V0_1_NEXT_008_CAPTURE_INVENTORY.md',
         'COMBAT_V0_1_NEXT_008_FIELD_RECOVERY.md',
         'COMBAT_V0_1_NEXT_008_IMPLEMENTATION_GATE.md']
out = ['# COMBAT-V0.1-NEXT-008 交付物 SHA-256', '',
       '生成方式: 逐文件读字节计算 SHA-256（无规范化、无换行转换）。', '',
       '| 文件 | 字节数 | SHA-256 |', '|---|---|---|']
for f in FILES:
    b = open(os.path.join(BASE, f), 'rb').read()
    out.append('| `%s` | %d | `%s` |' % (f, len(b), hashlib.sha256(b).hexdigest()))
out += ['', '## 被盘点的证据文件（只读，未修改）', '', '| 文件 | 字节数 | SHA-256 |', '|---|---|---|']
for f in ['REF_LOBBY_KIT/lobby_srv.log', 'REF_LOBBY_KIT/battle_srv.log',
          'REF_LOBBY_KIT/lobby_tasks.bin',
          'REF_LOBBY_KIT/mem_linear_20261007_134406/r_39EEA000_00246000.bin']:
    p = os.path.join(BASE, f)
    if os.path.exists(p):
        b = open(p, 'rb').read()
        out.append('| `%s` | %d | `%s` |' % (f, len(b), hashlib.sha256(b).hexdigest()))
    else:
        out.append('| `%s` | - | (not found) |' % f)
out += ['', '## 本次新增脚本（只读）', '', '| 脚本 | 字节数 | SHA-256 | 作用 |', '|---|---|---|---|']
for f, d in [('zy_evidence.py', '全 KIT 检索 21/5 / mmbook 证据文件与 0x85 帧'),
             ('zz_dump.py', 'mem_linear 转储中 mmbook/SessionId 检索（证明无 21/5 响应字节）')]:
    p = os.path.join(BASE, '_combat_next001', f)
    if os.path.exists(p):
        b = open(p, 'rb').read()
        out.append('| `_combat_next001/%s` | %d | `%s` | %s |' % (f, len(b), hashlib.sha256(b).hexdigest(), d))
out += ['', '## 复核方法', '', '```powershell', 'cd "' + BASE + '"',
        'Get-ChildItem COMBAT_V0_1_NEXT_008_*.md | Get-FileHash -Algorithm SHA256 | Format-Table Hash,Path -AutoSize',
        '',
        '# 复核"响应体无字节记录"这一关键事实',
        'Select-String -Path "REF_LOBBY_KIT\lobby_srv.log" -Pattern "0x85 应答 seq=47"',
        'Select-String -Path "REF_LOBBY_KIT\lobby_srv.log" -Pattern "6d 6d 62 6f 6f 6b"',
        'cd _combat_next001',
        'python -X utf8 zy_evidence.py   # 检索结论',
        'python -X utf8 zz_dump.py       # 转储内无 SessionId 结构',
        '```']
open(os.path.join(BASE, 'COMBAT_V0_1_NEXT_008_SHA256.txt'), 'w',
     encoding='utf-8', newline='\r\n').write('\n'.join(out) + '\n')
print('manifest written')
