"""全量提取：EXE 里所有与房间相关的 RTTI 类型名。

输出分类清单，覆盖 room / match / ready / team / vote / party / lobby / member。
这是"彻底逆向"的第一层：先把名字空间完整列出来。
"""
import re
import sys
import collections
import pefile

EXE = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe'
OUT = sys.argv[1] if len(sys.argv) > 1 else '.'

pe = pefile.PE(EXE, fast_load=True)
base = pe.OPTIONAL_HEADER.ImageBase
secs = [(s.Name.rstrip(b'\x00').decode('latin1'), base + s.VirtualAddress,
         s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData) for s in pe.sections]
data = open(EXE, 'rb').read()


def va_of(o):
    for n, va, vs, pr, rs in secs:
        if pr <= o < pr + rs:
            return va + (o - pr)
    return None


# MSVC RTTI 名字: .?AVName@@ / .?AUName@@ / 含模板 .?AVName@ns@@
PAT = re.compile(rb'\.\?A[VU][A-Za-z0-9_@?$<>,\- .]{1,120}?@@')

all_names = []
for m in PAT.finditer(data):
    raw = m.group(0)
    try:
        s = raw.decode('latin1')
    except Exception:
        continue
    all_names.append((va_of(m.start()), s))

print('RTTI 类型名总数: %d' % len(all_names))

KEY = re.compile(r'(?i)(room|match|ready|team|vote|party|lobby|member|player|'
                 r'invitation|channel|mmgroup|booking|session|host)')

groups = collections.defaultdict(list)
for va, s in all_names:
    if KEY.search(s):
        # 归类
        t = s[4:]
        if 'dwRoom' in s:
            g = 'dwRoom*'
        elif 'dwRoomMessage' in s:
            g = 'dwRoomMessage*'
        elif 'AS_' in s:
            g = 'AS_* (Scaleform)'
        elif 'MKT_' in s:
            g = 'MKT_* (商城)'
        elif 'WL_' in s:
            g = 'WL_* (武器/配装)'
        elif 'CL_' in s:
            g = 'CL_* (角色)'
        elif 'EventHandler' in s:
            g = 'EventHandler'
        elif 'dw' in s:
            g = 'dw* 其他'
        else:
            g = '其他'
        groups[g].append((va, s))

lines = []
lines.append('# EXE 内与房间相关的 RTTI 类型名（全量）')
lines.append('')
lines.append('来源: `COD OL\\codoMP_client_shipRetail.exe`，正则 `\\.\\?A[VU]...@@`')
lines.append('')
for g in sorted(groups):
    items = sorted(set(groups[g]))
    lines.append('## %s（%d 个）' % (g, len(items)))
    lines.append('')
    lines.append('| VA | 类型名 |')
    lines.append('|---|---|')
    for va, s in items:
        lines.append('| 0x%08X | `%s` |' % (va, s))
    lines.append('')

txt = '\n'.join(lines)
open(OUT + r'\rtti_full.md', 'w', encoding='utf-8').write(txt)

print()
for g in sorted(groups):
    print('  %-28s %d' % (g, len(set(groups[g]))))
print()
print('-> rtti_full.md')
