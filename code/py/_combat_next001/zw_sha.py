# -*- coding: utf-8 -*-
import hashlib, os
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL'
FILES = ['COMBAT_V0_1_NEXT_007_PRODUCER.md','COMBAT_V0_1_NEXT_007_DATAFLOW.md',
         'COMBAT_V0_1_NEXT_007_IMPLEMENTATION_GATE.md']
out = ['# COMBAT-V0.1-NEXT-007 交付物 SHA-256', '',
       '生成方式: 逐文件读字节计算 SHA-256（无规范化、无换行转换）。', '',
       '| 文件 | 字节数 | SHA-256 |', '|---|---|---|']
for f in FILES:
    b = open(os.path.join(BASE, f), 'rb').read()
    out.append('| `%s` | %d | `%s` |' % (f, len(b), hashlib.sha256(b).hexdigest()))
out += ['', '## 分析基座与被分析镜像', '', '| 文件 | 字节数 | SHA-256 |', '|---|---|---|']
for f in ['_combat_next001/peimg.py',
          os.path.join('CODOLServer','_mainline','_dyn100_run_20260925_182324','live','image_best.bin')]:
    b = open(os.path.join(BASE, f), 'rb').read()
    out.append('| `%s` | %d | `%s` |' % (f, len(b), hashlib.sha256(b).hexdigest()))
out += ['', '## 本次新增脚本（只读）', '', '| 脚本 | 字节数 | SHA-256 | 作用 |', '|---|---|---|---|']
for f, d in [('zr_callers3.py','0x7FA800 三个业务调用点全文'),
             ('zs_238.py','0x238(11) / 0x8E(23) 常量全量清单'),
             ('zt_writes.py','全镜像 [+0x168]/[+0x16C] 写入点(54/60) 按区筛选'),
             ('zu_netwriters.py','网络区 7 处命中的逐一排除'),
             ('zv_prio.py','0x7F343F / 0xBAD24F 的排除')]:
    p = os.path.join(BASE, '_combat_next001', f)
    if os.path.exists(p):
        b = open(p, 'rb').read()
        out.append('| `_combat_next001/%s` | %d | `%s` | %s |' % (f, len(b), hashlib.sha256(b).hexdigest(), d))
out += ['', '## 复核方法', '', '```powershell', 'cd "' + BASE + '"',
        'Get-ChildItem COMBAT_V0_1_NEXT_007_*.md | Get-FileHash -Algorithm SHA256 | Format-Table Hash,Path -AutoSize',
        'cd _combat_next001',
        'python -X utf8 zt_writes.py      # +0x168/+0x16C 全部写入点',
        'python -X utf8 zu_netwriters.py  # 网络区 7 处排除',
        'python -X utf8 zs_238.py         # 候选检索入口（0x238 / 0x8E）',
        'python -X utf8 zv_prio.py        # 两个已排除的 0x238 点',
        '```']
open(os.path.join(BASE, 'COMBAT_V0_1_NEXT_007_SHA256.txt'), 'w',
     encoding='utf-8', newline='\r\n').write('\n'.join(out) + '\n')
print('manifest written')
