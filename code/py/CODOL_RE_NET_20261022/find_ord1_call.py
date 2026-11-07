import struct
p=r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read(); BASE=0x400000
pat=b'\xff\x15\x65\xc6\x9d\x0e'
i=0
print('call [0xE9DC665] occurrences:')
while True:
    i=d.find(pat,i)
    if i<0: break
    print('  VA %#010x'%(BASE+i)); i+=1
pat2=struct.pack('<I',0xE9DC665)
i=0; print('any dword ref to 0xE9DC665:')
while True:
    i=d.find(pat2,i)
    if i<0: break
    print('  VA %#010x  prev=%s'%(BASE+i,d[max(0,i-6):i].hex())); i+=1
# dump around file EP in the on-disk exe
e=open(r'COD OL\codoMP_client_shipRetail.exe','rb').read()
off=0x776690
print('\ndisk EP bytes:',e[off:off+64].hex(' '))
