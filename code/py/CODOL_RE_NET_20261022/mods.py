import re
t = open(r'run_codol_001\runs\OMIT_RETEST_20261022\chain.txt', encoding='utf-8', errors='replace').read().splitlines()
for i, l in enumerate(t):
    if 'MODULE' in l or '模块' in l:
        print(i+1, l[:200])
