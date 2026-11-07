# -*- coding: utf-8 -*-
import hashlib, os
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL'
FILES = [
  'COMBAT_V0_1_NEXT_003_DISPATCH.md',
  'COMBAT_V0_1_NEXT_003_SLOT_FILL.md',
  'COMBAT_V0_1_NEXT_003_IMPLEMENTATION_GATE.md',
]
out = ['# COMBAT-V0.1-NEXT-003 交付物 SHA-256', '',
       '生成方式: 对本目录下 3 个报告逐文件读字节计算 SHA-256（无规范化、无换行转换）。', '',
       '| 文件 | 字节数 | SHA-256 |', '|---|---|---|']
for f in FILES:
    b = open(os.path.join(BASE, f), 'rb').read()
    out.append('| `%s` | %d | `%s` |' % (f, len(b), hashlib.sha256(b).hexdigest()))

out += ['', '## 分析基座与被分析镜像', '', '| 文件 | 字节数 | SHA-256 |', '|---|---|---|']
targets = ['_combat_next001/peimg.py',
           os.path.join('CODOLServer','_mainline','_dyn100_run_20260925_182324','live','image_best.bin')]
for f in targets:
    b = open(os.path.join(BASE, f), 'rb').read()
    out.append('| `%s` | %d | `%s` |' % (f, len(b), hashlib.sha256(b).hexdigest()))

out += ['', '## 本次新增的关键分析脚本（只读）', '', '| 脚本 | 字节数 | SHA-256 | 作用 |', '|---|---|---|---|']
scripts = [
  ('s1_reg.py', '0x7FAA20 反汇编'),
  ('s2_disp.py', '0x7FA800 注册表实现 + 7 个调用点'),
  ('s4_fullvt.py', 'vtable 全槽 dump'),
  ('s5_slot8.py', 'slot+0x08 直接调用点检索（0 命中）'),
  ('s7_refs.py', '0x62CD30 / 0x6376F0 全部数据引用'),
  ('s8_dd.py', '0x62DD5F 函数（消息 0x26 发送点）'),
  ('t1_reg2.py', '0x7F44B0 反汇编 + 仅 2 个调用点'),
  ('t2_b9b.py', '0xB9B0B0 组件 + 0x62932F（消息 0x27）'),
  ('t4_cb2.py', '0x637590 / 0x637720 / 0x6376F0 / 0x637930 逐指令'),
  ('t5_ada.py', '0xD692ADA0 与 criterion 常量检索'),
  ('u3_entry.py', '0x7230 / 0xE360 全部写点'),
  ('u4_bf.py', '0x62C000 构造函数（两个 49x0x238 数组）'),
  ('u5_slotarr.py', '0x806B50 槽构造函数（A/B 清零）+ +0x7470 全部 4 处访问'),
  ('v1_full.py', '0xB9B0B0 全量反汇编（回调只存不调）'),
  ('w1_vt.py', '主 vtable 0xDC7274 与 0xDC72B0 关系'),
  ('w2_disp.py', 'slot+0x04 / +0x08 派发检索'),
  ('w3_13c.py', 'vtable+0x13C 链一致性验证'),
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
        '# 三个报告的 SHA-256',
        'Get-ChildItem COMBAT_V0_1_NEXT_003_*.md | Get-FileHash -Algorithm SHA256 | Format-Table Hash,Path -AutoSize',
        '',
        '# 复现核心证据',
        'cd _combat_next001',
        'python -X utf8 t1_reg2.py      # 0x7F44B0 只有 2 个调用点',
        'python -X utf8 u5_slotarr.py   # 0x806B50 把槽 +0x168/+0x16C 清零',
        'python -X utf8 w1_vt.py        # 主 vtable 0xDC7274；0xDC72B0 = +0x3C',
        'python -X utf8 w3_13c.py       # accepted handler 在 vtable+0x13C',
        '```']
open(os.path.join(BASE, 'COMBAT_V0_1_NEXT_003_SHA256.txt'), 'w',
     encoding='utf-8', newline='\r\n').write('\n'.join(out) + '\n')
print('manifest written, lines =', len(out))
