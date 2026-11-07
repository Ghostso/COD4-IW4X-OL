import os, re
p = r'CODOL_SERVER_319_20261021\src\battle\battle_service.c'
s = open(p, encoding='utf-8', errors='replace').read()
print('lines', s.count(chr(10)))
for m in re.finditer(r'^([A-Za-z_][A-Za-z0-9_ \*]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^;]*?)\)\s*$', s, re.M):
    print(m.group(1).strip(), m.group(2))
for kw in ['omit_motion','configstring','gamestate','28960','usercmd']:
    print('==', kw)
    for m in re.finditer(kw, s):
        ln = s[:m.start()].count(chr(10))+1
        line = s.splitlines()[ln-1].strip()
        print('  %d: %s' % (ln, line[:150]))
