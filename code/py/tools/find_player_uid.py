r"""从历史日志里找客户端真实的玩家标识（xuid / CODOID / name）。

已知：
    客户端 connect 命令: \name\TTctRThTNkNsaWVudA==\xuid\e7c8a98a6b4c2d0e
    TLog: CODOID(16701785630074219790)
    我们的 player-account.json: Name = "LAtt"

要确认：
  1. xuid 0xe7c8a98a6b4c2d0e 是否恒定
  2. 它与 CODOID 16701785630074219790 的关系
  3. 有没有别的 uid 出现在 0x82 票据或 room 相关报文里
"""
import glob
import os
import re

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs'

logs = glob.glob(os.path.join(ROOT, '**', 'lobby_srv.log'), recursive=True)
print('日志 %d 份' % len(logs))

xuid = {}
codoid = {}
names = {}

for lp in logs:
    try:
        txt = open(lp, encoding='utf-8', errors='replace').read()
    except Exception:
        continue
    for m in re.finditer(r'xuid\\(\w+)', txt):
        xuid[m.group(1)] = xuid.get(m.group(1), 0) + 1
    for m in re.finditer(r'CODOID\((\d+)\)', txt):
        codoid[m.group(1)] = codoid.get(m.group(1), 0) + 1
    for m in re.finditer(r'\\name\\([\w+/=]+)', txt):
        names[m.group(1)] = names.get(m.group(1), 0) + 1
    # 0x82 票据里的 b64 name
    for m in re.finditer(r'TTctRThTNkNsaWVudA==', txt):
        pass

print()
print('=== xuid 取值 ===')
for k, v in sorted(xuid.items(), key=lambda x: -x[1])[:8]:
    try:
        print('  %-20s ×%-4d  十进制=%d' % (k, v, int(k, 16)))
    except ValueError:
        print('  %-20s ×%-4d' % (k, v))

print()
print('=== CODOID 取值 ===')
for k, v in sorted(codoid.items(), key=lambda x: -x[1])[:8]:
    print('  %-24s ×%-4d  hex=%s' % (k, v, hex(int(k))))

print()
print('=== name (base64) 取值 ===')
import base64
for k, v in sorted(names.items(), key=lambda x: -x[1])[:8]:
    try:
        dec = base64.b64decode(k + '=' * (-len(k) % 4)).decode('utf-8', 'replace')
    except Exception:
        dec = '?'
    print('  %-24s ×%-4d  解码=%r' % (k, v, dec))

print()
print('=== 关系检查 ===')
for xk in list(xuid)[:3]:
    try:
        xv = int(xk, 16)
    except ValueError:
        continue
    for ck in list(codoid)[:3]:
        cv = int(ck)
        print('  xuid 0x%X (%d) vs CODOID %d  相等=%s'
              % (xv, xv, cv, xv == cv))
