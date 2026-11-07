# -*- coding: utf-8 -*-
import hashlib, os
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL'
F = 'COMBAT_V0_1_NEXT_005_TIMER_QUEUE.md'
b = open(os.path.join(BASE, F), 'rb').read()
out = ['# COMBAT-V0.1-NEXT-005 交付物 SHA-256', '',
       '生成方式: 逐文件读字节计算 SHA-256（无规范化、无换行转换）。', '',
       '| 文件 | 字节数 | SHA-256 |', '|---|---|---|',
       '| `%s` | %d | `%s` |' % (F, len(b), hashlib.sha256(b).hexdigest()),
       '', '## 分析基座与被分析镜像', '', '| 文件 | 字节数 | SHA-256 |', '|---|---|---|']
for f in ['_combat_next001/peimg.py',
          os.path.join('CODOLServer','_mainline','_dyn100_run_20260925_182324','live','image_best.bin')]:
    bb = open(os.path.join(BASE, f), 'rb').read()
    out.append('| `%s` | %d | `%s` |' % (f, len(bb), hashlib.sha256(bb).hexdigest()))
out += ['', '## 本次新增脚本', '', '| 脚本 | 字节数 | SHA-256 | 作用 |', '|---|---|---|---|']
for f, d in [('z5_lookup.py','0x7FA640 条目填充（+0x08 入队 / +0x0C +15s 超时）'),
             ('z6_dispatch.py','表基 0xE69CE0 / 索引表 0xE4E20C / 扫描区间'),
             ('z7_pump.py','0x7FA800 的 7 个调用点 + 0x7FA450 条目清理'),
             ('z8_tail.py','0x7FA9B0 call [ebp-0x20]（处理器调用点）'),
             ('z9_slotvt.py','槽 vtable 0xDC79F0 + 0x63794F 循环'),
             ('za_slotfn.py','槽对象 vtable 方法识别（+0x04 返回 0x238）')]:
    p = os.path.join(BASE, '_combat_next001', f)
    if os.path.exists(p):
        bb = open(p, 'rb').read()
        out.append('| `_combat_next001/%s` | %d | `%s` | %s |' % (f, len(bb), hashlib.sha256(bb).hexdigest(), d))
out += ['', '## 复核方法', '', '```powershell', 'cd "' + BASE + '"',
        'Get-ChildItem COMBAT_V0_1_NEXT_005_*.md | Get-FileHash -Algorithm SHA256 | Format-Table Hash,Path -AutoSize',
        'cd _combat_next001',
        'python -X utf8 z5_lookup.py    # 条目 +0x0C = 入队 + 0x3A98(15000ms)',
        'python -X utf8 z8_tail.py      # 0x7FA9B0 call [ebp-0x20]',
        'python -X utf8 z9_slotvt.py    # 0x63794F 的 rep movsd 装槽循环',
        '```']
open(os.path.join(BASE, 'COMBAT_V0_1_NEXT_005_SHA256.txt'), 'w',
     encoding='utf-8', newline='\r\n').write('\n'.join(out) + '\n')
print('written')
