"""对比 10-26 成功轮与 10-27 失败轮的 kit 差异。

成功: ONCE_20261026_220815 (21 个战斗服事件)
失败: ONCE_20261027_140400 (A 形态但 0 事件)

对比: 开关文件、关键配置、lobby_server.py 版本。
"""
import hashlib
import os

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs'
OK = os.path.join(ROOT, 'ONCE_20261026_220815', 'kit')
BAD = os.path.join(ROOT, 'ONCE_20261027_140400', 'kit')


def ls(d):
    if not os.path.isdir(d):
        return None
    return {f for f in os.listdir(d) if os.path.isfile(os.path.join(d, f))}


a, b = ls(OK), ls(BAD)
if a is None or b is None:
    raise SystemExit('目录缺失 ok=%s bad=%s' % (a is not None, b is not None))

print('成功轮文件 %d 个, 失败轮 %d 个' % (len(a), len(b)))
print()
print('=== 只在成功轮里有 ===')
for f in sorted(a - b):
    print('  %s' % f)
print()
print('=== 只在失败轮里有 ===')
for f in sorted(b - a):
    print('  %s' % f)
print()
print('=== 两边都有但内容不同 ===')
diff = []
for f in sorted(a & b):
    pa, pb = os.path.join(OK, f), os.path.join(BAD, f)
    try:
        if os.path.getsize(pa) != os.path.getsize(pb):
            diff.append((f, os.path.getsize(pa), os.path.getsize(pb), 'size'))
            continue
        if hashlib.sha256(open(pa, 'rb').read()).digest() != \
           hashlib.sha256(open(pb, 'rb').read()).digest():
            diff.append((f, os.path.getsize(pa), os.path.getsize(pb), 'hash'))
    except Exception:
        pass
for f, sa, sb, why in diff:
    print('  %-40s ok=%d bad=%d (%s)' % (f, sa, sb, why))
