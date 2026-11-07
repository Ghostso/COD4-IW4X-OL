# -*- coding: utf-8 -*-
import hashlib, os
BASE = r'D:\BaiduNetdiskDownload\使命召唤OL'
FILES = ['COMBAT_V0_1_NEXT_009_CAPTURE_PLAN.md',
         'COMBAT_V0_1_NEXT_009_RAW_RESPONSE_EVIDENCE.md',
         'COMBAT_V0_1_NEXT_009_FIELD_MAPPING.md']
out = ['# COMBAT-V0.1-NEXT-009 交付物 SHA-256', '',
       '生成方式: 逐文件读字节计算 SHA-256（无规范化、无换行转换）。', '',
       '| 文件 | 字节数 | SHA-256 |', '|---|---|---|']
for f in FILES:
    b = open(os.path.join(BASE, f), 'rb').read()
    out.append('| `%s` | %d | `%s` |' % (f, len(b), hashlib.sha256(b).hexdigest()))
out += ['', '## 被引用的既有证据/基线（只读，本次未修改）', '', '| 文件 | 字节数 | SHA-256 |', '|---|---|---|']
for f in ['REF_LOBBY_KIT/lobby_server.py', 'REF_LOBBY_KIT/codol_crypto.py',
          'REF_LOBBY_KIT/lobby_srv.log',
          'GOLDEN-LOBBY-001/REF_LOBBY_KIT/lobby_server.py']:
    p = os.path.join(BASE, f)
    if os.path.exists(p):
        b = open(p, 'rb').read()
        out.append('| `%s` | %d | `%s` |' % (f, len(b), hashlib.sha256(b).hexdigest()))
    else:
        out.append('| `%s` | - | (not found) |' % f)
out += ['', '## 本次新增脚本（只读）', '', '| 脚本 | 字节数 | SHA-256 | 作用 |', '|---|---|---|---|']
p = os.path.join(BASE, '_combat_next001', 'z9_capture_plan.py')
if os.path.exists(p):
    b = open(p, 'rb').read()
    out.append('| `_combat_next001/z9_capture_plan.py` | %d | `%s` | 离线复算 306 B 帧布局 |' % (len(b), hashlib.sha256(b).hexdigest()))
out += ['', '## 授权状态（本次未采集）', '',
        '| 授权项 | 状态 |', '|---|---|',
        '| A1 允许在独立工作副本中新增日志落盘函数 | ❌ 未获得 |',
        '| A2 允许运行大厅 + 手动进对局一次 | ❌ 未获得 |',
        '| A3 允许写 capture-21-5.*.log | ❌ 未获得 |',
        '', '**⇒ 步骤 4–6 未执行；A/B 未恢复；未提出协议修复。**']
out += ['', '## 复核方法', '', '```powershell', 'cd "' + BASE + '"',
        'Get-ChildItem COMBAT_V0_1_NEXT_009_*.md | Get-FileHash -Algorithm SHA256 | Format-Table Hash,Path -AutoSize',
        '',
        '# 复核帧布局（无需授权、不联网）',
        'cd _combat_next001',
        'python -X utf8 z9_capture_plan.py',
        '#  期望输出: frame len = 26 + 272 + 8 = 306   <- 对照日志 (306 字节)',
        '',
        '# 复核"响应体无字节记录"',
        'Select-String -Path "..\REF_LOBBY_KIT\lobby_srv.log" -Pattern "0x85 应答 seq=47"',
        '```']
open(os.path.join(BASE, 'COMBAT_V0_1_NEXT_009_SHA256.txt'), 'w',
     encoding='utf-8', newline='\r\n').write('\n'.join(out) + '\n')
print('manifest written')
