# -*- coding: utf-8 -*-
import hashlib, os
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL'
FILES = [
  'COMBAT_V0_1_NEXT_002_U2.md',
  'COMBAT_V0_1_NEXT_002_U1.md',
  'COMBAT_V0_1_NEXT_002_IMPLEMENTATION_GATE.md',
]
out = ['# COMBAT-V0.1-NEXT-002 交付物 SHA-256', '',
       '生成方式: 对本目录下 3 个报告逐文件读字节计算 SHA-256（无规范化、无换行转换）。', '',
       '| 文件 | 字节数 | SHA-256 |', '|---|---|---|']
for f in FILES:
    b = open(os.path.join(BASE, f), 'rb').read()
    out.append('| `%s` | %d | `%s` |' % (f, len(b), hashlib.sha256(b).hexdigest()))

out += ['', '## 分析基座与被分析镜像', '',
        '| 文件 | 字节数 | SHA-256 |', '|---|---|---|']
targets = ['_combat_next001/peimg.py']
img = os.path.join('CODOLServer', '_mainline', '_dyn100_run_20260925_182324', 'live', 'image_best.bin')
targets.append(img)
for f in targets:
    b = open(os.path.join(BASE, f), 'rb').read()
    out.append('| `%s` | %d | `%s` |' % (f, len(b), hashlib.sha256(b).hexdigest()))

out += ['', '## 本次新增的关键分析脚本（只读，可复核）', '',
        '| 脚本 | 字节数 | SHA-256 | 作用 |', '|---|---|---|---|']
scripts = [
  ('m1_mmbook_full.py', 'mmbook 构造器 0x62F6F0 完整反汇编'),
  ('m2_callers.py', '3 个调用者 + 字符串 xref（发现 0x7F153F）'),
  ('m3_7f15.py', '本地 mmbook 分派器 0x7F153F -> 0x632680 唯一路径'),
  ('m5_screen.py', '22 条候选的上下文全量清单'),
  ('m6_aligned.py', '对齐感知筛查（21/22 ALIGNED）'),
  ('n2_strings.py', '"mmbook" / "%s %d %s %d" 字节级确认'),
  ('n4_slotinit.py', '预约槽布局权威来源（0x238 / 0x6EF0 / 0x7470 / 0xE360）'),
  ('n5_slot2.py', '第二个整槽初始化器 0x637720'),
  ('n6_exact.py', '证伪 [+0x75D8/+0x75DC] 的字段级写入'),
  ('r1_proof.py', '穷尽证明：该位移全镜像仅 2 次访问且均为读'),
  ('p1_278.py', '+0x278 全部 60 处访问（含宽度分类）'),
  ('p2_bytes.py', '5 处字节宽访问的上下文与所属函数'),
  ('p3_callers.py', '开闸函数 0x62B640 的调用者'),
  ('p4_setctx.py', '0x63735F 的开闸条件（64-bit ID 比对）'),
  ('q1_filler.py', '预约槽填充器的 vtable/激活器追踪（缺口定位）'),
]
for f, d in scripts:
    p = os.path.join(BASE, '_combat_next001', f)
    if os.path.exists(p):
        b = open(p, 'rb').read()
        out.append('| `_combat_next001/%s` | %d | `%s` | %s |' % (f, len(b), hashlib.sha256(b).hexdigest(), d))
    else:
        out.append('| `_combat_next001/%s` | - | MISSING | %s |' % (f, d))

out += ['', '## 复核方法', '', '```powershell',
        'cd "' + BASE + '"',
        '# 重新计算三个报告的 SHA-256',
        'Get-ChildItem COMBAT_V0_1_NEXT_002_*.md | Get-FileHash -Algorithm SHA256 | Format-Table Hash,Path -AutoSize',
        '',
        '# 复现核心证据',
        'cd _combat_next001',
        'python -X utf8 n4_slotinit.py   # 预约槽布局：0x238 / 0x6EF0 / 0x7470 / 0xE360',
        'python -X utf8 r1_proof.py      # A/B 无字段级写入的穷尽证明（0 write）',
        'python -X utf8 p4_setctx.py     # [mk+0x278] 开闸条件（ID 比对）',
        '```']
open(os.path.join(BASE, 'COMBAT_V0_1_NEXT_002_SHA256.txt'), 'w',
     encoding='utf-8', newline='\r\n').write('\n'.join(out) + '\n')
print('written; lines =', len(out))
