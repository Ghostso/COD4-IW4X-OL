# -*- coding: utf-8 -*-
import hashlib, io, os
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL'
FILES = [
  'COMBAT_V0_1_NEXT_001_CALLCHAIN.md',
  'COMBAT_V0_1_NEXT_001_DATAFLOW.md',
  'COMBAT_V0_1_NEXT_001_BLOCKER.md',
]
out = []
out.append('# COMBAT-V0.1-NEXT-001 交付物 SHA-256')
out.append('')
out.append('生成方式: 对本目录下 3 个报告逐文件读字节计算 SHA-256（无规范化、无换行转换）。')
out.append('')
out.append('| 文件 | 字节数 | SHA-256 |')
out.append('|---|---|---|')
for f in FILES:
    p = os.path.join(BASE, f)
    b = open(p, 'rb').read()
    h = hashlib.sha256(b).hexdigest()
    out.append('| `%s` | %d | `%s` |' % (f, len(b), h))
out.append('')
out.append('## 分析基座（可复核）')
out.append('')
tools = ['_combat_next001/peimg.py']
for f in tools:
    p = os.path.join(BASE, f)
    if os.path.exists(p):
        b = open(p, 'rb').read()
        out.append('| `%s` | %d | `%s` |' % (f, len(b), hashlib.sha256(b).hexdigest()))
out.append('')
out.append('## 被分析镜像')
out.append('')
img = os.path.join(BASE, 'CODOLServer', '_mainline',
                   '_dyn100_run_20260925_182324', 'live', 'image_best.bin')
b = open(img, 'rb').read()
out.append('| `image_best.bin` | %d | `%s` |' % (len(b), hashlib.sha256(b).hexdigest()))
out.append('')
out.append('## 复核方法')
out.append('')
out.append('```powershell')
out.append('cd "' + BASE + '"')
out.append('# 重新计算三个报告的 SHA-256')
out.append('Get-ChildItem COMBAT_V0_1_NEXT_001_*.md | Get-FileHash -Algorithm SHA256 | Format-Table Hash,Path -AutoSize')
out.append('# 复现分析基座')
out.append('cd _combat_next001')
out.append('python -X utf8 j1_table.py      # 关键地址 -> 文件偏移表')
out.append('python -X utf8 k4_pairs.py      # 预约项 +0x168/+0x16c 成对写入点')
out.append('python -X utf8 k5_mmbook.py     # mmbook 请求构造器与格式串')
out.append('```')
txt = '\n'.join(out) + '\n'
open(os.path.join(BASE, 'COMBAT_V0_1_NEXT_001_SHA256.txt'), 'w', encoding='utf-8', newline='\r\n').write(txt)
print(txt)
