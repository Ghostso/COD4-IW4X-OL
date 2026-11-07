# -*- coding: utf-8 -*-
"""Decode every '** <base> <v8> <v9> <attachments...>' modular weapon string in
a byte blob, and attach engine/base indices using the verified formula:
    dynamic weapon index = configstring index - 5960
"""
import re, sys, io, csv, os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')

CS_BASE = 5960
REF = r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-CLIENT-PARSER-SEMANTICS-046\_extracted\reference\composite-gamestate-candidate.json'

raw = open(sys.argv[1], 'rb').read() if len(sys.argv) > 1 else b''

# The decoded strings file has them as NUL-terminated lines.
text = raw.decode('latin-1', 'replace')
pat = re.compile(r'\*\*[ ]+(\d+)[ ]+(\d+)[ ]+(\d+)((?:[ ]+\d+)*)')

table = {}
for m in pat.finditer(text):
    base, v8, v9 = int(m.group(1)), int(m.group(2)), int(m.group(3))
    atts = [int(x) for x in m.group(4).split()] if m.group(4).strip() else []
    key = (base, v8, v9, tuple(atts))
    table.setdefault(key, 0)
    table[key] += 1

print('distinct modular weapon definitions:', len(table))
print('%-6s %-4s %-4s %-32s %s' % ('base', 'v8', 'v9', 'attachments', 'occurrences'))
for (b, v8, v9, atts), n in sorted(table.items())[:40]:
    print('%-6d %-4d %-4d %-32s %d' % (b, v8, v9, ' '.join(map(str, atts)), n))

# sanity: the formula itself
print()
print('formula: dynamic weapon index = configstring index -', CS_BASE)
print('  cs 7184 (retail ** 646 0 0 8738 9321) ->', 7184 - CS_BASE)
