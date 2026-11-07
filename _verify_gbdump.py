import os, math, collections, struct
p=os.path.join(r'D:\BaiduNetdiskDownload\使命召唤OL','COD OL','tqm','dump','GbDump.2.8975234.codomp_client_shipretail.exe.dmp.dat')
b=open(p,'rb').read()
print('SIZE',len(b))
print('HEAD64',b[:64].hex(' '))
print('TAIL32',b[-32:].hex(' '))
for sig in (b'MZ',b'MDMP',b'PAGEDUMP',b'MSCF',b'PK\x03\x04',b'7z\xbc\xaf',b'\x1f\x8b',b'BZh',b'\xfd7zXZ'):
    print('SIG',repr(sig),b.find(sig))
cnt=collections.Counter(b); n=len(b)
ent=-sum((v/n)*math.log2(v/n) for v in cnt.values()) if n else 0
print('ENTROPY',round(ent,6),'UNIQUE',len(cnt),'ZERO_FRAC',round(cnt[0]/n,8),'PRINTABLE_FRAC',round(sum(v for k,v in cnt.items() if 32<=k<127 or k in (9,10,13))/n,8))
print('FIRST_DWORDS',[hex(struct.unpack_from('<I',b,i)[0]) for i in range(0,min(64,len(b)),4)])
for s in (b'codoMP',b'client_shipRetail',b'MDMP',b'<'):
    print('ASCII_HIT',repr(s),b.lower().find(s.lower()))
