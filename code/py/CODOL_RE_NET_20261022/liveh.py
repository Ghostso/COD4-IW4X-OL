t = open(r'run_codol_001\runs\OMIT_RETEST_20261022\kit\live.txt', encoding='utf-8', errors='replace').read().splitlines()
print('lines', len(t))
for l in t[:80]: print(l[:200])
