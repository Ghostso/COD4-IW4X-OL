s = open(r'CODOL_SERVER_319_20261021\src\battle\battle_service.c', encoding='utf-8', errors='replace').read().splitlines()
for a,b in [(96,200),(240,300),(360,420),(500,567)]:
    print('\n===== %d..%d =====' % (a,b))
    for i in range(a-1, min(b, len(s))):
        print('%4d %s' % (i+1, s[i]))
