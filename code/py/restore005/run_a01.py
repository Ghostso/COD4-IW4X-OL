import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a01_pe_dump as A

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL'
TARGETS = [
    (os.path.join(ROOT, r'工具\EX035_DIR\IIPS\iips.dll'), 'ORIGINAL_iips.dll (EX035 pristine copy)'),
    (os.path.join(ROOT, 'LocalRM.dll'), 'GENERATED_LocalRM.dll (RESTORE-004)'),
]
out = []
for p, l in TARGETS:
    out += A.dump(p, l)
    out.append('')
print('\n'.join(out))
