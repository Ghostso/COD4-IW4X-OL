# -*- coding: utf-8 -*-
import hashlib, os
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL'
FILES = [
  'COMBAT_V0_1_NEXT_004_CALLBACK_CONSUMER.md',
  'COMBAT_V0_1_NEXT_004_SLOT_SOURCE.md',
  'COMBAT_V0_1_NEXT_004_IMPLEMENTATION_GATE.md',
]
out = ['# COMBAT-V0.1-NEXT-004 交付物 SHA-256', '',
       '生成方式: 对本目录下 3 个报告逐文件读字节计算 SHA-256（无规范化、无换行转换）。', '',
       '| 文件 | 字节数 | SHA-256 |', '|---|---|---|']
for f in FILES:
    b = open(os.path.join(BASE, f), 'rb').read()
    out.append('| `%s` | %d | `%s` |' % (f, len(b), hashlib.sha256(b).hexdigest()))
out += ['', '## 分析基座与被分析镜像', '', '| 文件 | 字节数 | SHA-256 |', '|---|---|---|']
for f in ['_combat_next001/peimg.py',
          os.path.join('CODOLServer','_mainline','_dyn100_run_20260925_182324','live','image_best.bin')]:
    b = open(os.path.join(BASE, f), 'rb').read()
    out.append('| `%s` | %d | `%s` |' % (f, len(b), hashlib.sha256(b).hexdigest()))
out += ['', '## 本次新增的关键分析脚本（只读）', '', '| 脚本 | 字节数 | SHA-256 | 作用 |', '|---|---|---|---|']
for f, d in [
  ('x1_ba74.py', '0xBA74B0 / 0xBA72C0（消息对象布局）'),
  ('x2_cb.py', '[reg+0x28] / [reg+0x20] 的 call/mov 全量检索'),
  ('x5_msgvt.py', '消息 vtable 0xD5A64C 与引用'),
  ('x8_recheck.py', '函数入口校正 + 0x6376F0/0x637930 引用重查'),
  ('x9_637930.py', '3 处 push 0x637930 的上下文'),
  ('y1_sched.py', '0x6292B0（含 0x62934C call ebx 回调调用点）'),
  ('y2_fwd.py', '0x637930 转发器 + 0x637720 槽写入器'),
  ('y3_source.py', '[mk+0x10728] 与 [0x82E13FC] 引用统计'),
  ('y4_singleton.py', '匹配对象单例构造点 0x639D00'),
  ('y5_path.py', '0x62F840 槽分支（只读 A 不写）'),
]:
    p = os.path.join(BASE, '_combat_next001', f)
    if os.path.exists(p):
        b = open(p, 'rb').read()
        out.append('| `_combat_next001/%s` | %d | `%s` | %s |' % (f, len(b), hashlib.sha256(b).hexdigest(), d))
    else:
        out.append('| `_combat_next001/%s` | - | MISSING | %s |' % (f, d))
out += ['', '## 复核方法', '', '```powershell',
        'cd "' + BASE + '"',
        'Get-ChildItem COMBAT_V0_1_NEXT_004_*.md | Get-FileHash -Algorithm SHA256 | Format-Table Hash,Path -AutoSize',
        'cd _combat_next001',
        'python -X utf8 y1_sched.py      # 0x6292B0 失败路径 call ebx（回调消费点）',
        'python -X utf8 x1_ba74.py       # 消息对象布局（+0x1C 是 byte；+0x28 是回调槽）',
        'python -X utf8 y5_path.py       # 0x62F840 只读 A 不写',
        '```']
open(os.path.join(BASE, 'COMBAT_V0_1_NEXT_004_SHA256.txt'), 'w',
     encoding='utf-8', newline='\r\n').write('\n'.join(out) + '\n')
print('manifest written, lines =', len(out))
