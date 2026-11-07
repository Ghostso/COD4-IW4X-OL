# -*- coding: utf-8 -*-
import hashlib, os
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL'
FILES = ['COMBAT_V0_1_NEXT_006_CALLERS.md','COMBAT_V0_1_NEXT_006_SOURCE_ARRAY.md',
         'COMBAT_V0_1_NEXT_006_FIELD_MAPPING.md','COMBAT_V0_1_NEXT_006_IMPLEMENTATION_GATE.md']
out = ['# COMBAT-V0.1-NEXT-006 交付物 SHA-256', '',
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
for f, d in [('zc_callers.py','0x63794F 直调者与全部 dword 引用定位'),
             ('zd_caller.py','调用者 0x6379DF 全文（0x6379F4 call + rep movsd 循环）'),
             ('ze_wrapper.py','转发器 0x6379E0 唯一引用 = 0x62DE9C'),
             ('zf_wrapctx.py','0x62DE90 / 0x62DE80 上下文'),
             ('zg_7fb240.py','0x7FB240 按 id 查表 fire/cancel'),
             ('zh_task32.py','0x62DE90 的 vtable 归属（+0x024）'),
             ('zi_vtslots.py','主 vtable 槽位总表 + 0x6292B0 四调用点配对表'),
             ('zj_args.py','0x7FA9B0 前参数装配'),
             ('zk_verify.py','0x7FA9B0 处寄存器取值链'),
             ('zm_cmp.py','0x7FA640 两调用点对比'),
             ('zn_prologue.py','**0x7FA800 直通机制（入参原样搬进条目）**')]:
    p = os.path.join(BASE, '_combat_next001', f)
    if os.path.exists(p):
        b = open(p, 'rb').read()
        out.append('| `_combat_next001/%s` | %d | `%s` | %s |' % (f, len(b), hashlib.sha256(b).hexdigest(), d))
open(os.path.join(BASE, 'COMBAT_V0_1_NEXT_006_SHA256.txt'), 'w',
     encoding='utf-8', newline='\r\n').write('\n'.join(out) + '\n')
print('regenerated')
