import struct, pefile
p=r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read(); BASE=0x400000
pe=pefile.PE(r'C:\Windows\SysWOW64\ws2_32.dll')
ex={}
for s in pe.DIRECTORY_ENTRY_EXPORT.symbols:
    if s.name: ex[s.address]=s.name.decode()
lo,hi=0x779A0000,0x779E0000
hits=[]
for off in range(0,len(d)-4,4):
    v=struct.unpack_from('<I',d,off)[0]
    if lo<=v<hi: hits.append((BASE+off,v-lo))
print('total ws2 ptr slots',len(hits))
groups={}
for va,rva in hits: groups.setdefault(rva,[]).append(va)
for rva in sorted(groups):
    print('%-18s ws2+%08x slots: %s'%(ex.get(rva,'?'),rva,', '.join(hex(x) for x in groups[rva][:8])))
