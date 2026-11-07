p=r'COD OL\codoMP_client_shipRetailBase.dll'
d=open(p,'rb').read()
i=d.find(b'VmpVersion')
print('VmpVersion at',hex(i))
print(repr(d[max(0,i-120):i+200]))
for q in [b'TCLSCheck',b'TenProtect',b'ace-',b'tp3',b'TP3']:
    print('==',q,d.count(q))
    j=0;n=0
    while True:
        j=d.find(q,j)
        if j<0: break
        s=j
        while s>0 and 32<=d[s-1]<127: s-=1
        e=d.find(b'\x00',j)
        print('  ',hex(s),repr(d[s:e][:90])); j+=1; n+=1
        if n>=8: break
