import os,re
try:
    names=os.listdir(r'\\.\pipe\\')
except Exception as e:
    print('ERR',repr(e)); raise SystemExit
pat=re.compile(r'iips|tenio|tcls|host|ten|qq|session|pipe',re.I)
for n in sorted(names):
    if pat.search(n):
        print(n)
print('TOTAL',len(names))
