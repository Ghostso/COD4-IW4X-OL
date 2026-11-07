import io,sys
p=r"D:\BaiduNetdiskDownload\使命召唤OL\REF_LOBBY_KIT_CAP009\codol_crypto.py"
lines=open(p,encoding='utf-8').read().splitlines()
def show(a,b,label):
    print("="*90); print(label); print("="*90)
    for i in range(a-1,min(b,len(lines))):
        print("%4d| %s" % (i+1, lines[i]))
# find Buf class and blob()
import re
for i,l in enumerate(lines):
    if re.match(r'\s*class Buf', l) or 'def blob' in l or 'def string' in l or 'def u32' in l or 'def u64' in l or 'use_types' in l and 'def ' in l:
        print("%4d| %s" % (i+1,l))
