import struct
d=open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read();B=0x400000
hi=B+0xE5C8000
for name,va in [('CA_GAMESTATE',0x00DC0974),('gamestateupdate',0x00DB4700),('northyaw',0x00DB9754),('mp_firingrange',0x00DD66FF)]:
    pat=struct.pack('<I',va); hits=[];i=0
    while True:
        i=d.find(pat,i)
        if i<0: break
        v=B+i
        if 0x401000<=v<hi: hits.append(v)
        i+=1
    print('%-16s %#010x refs=%d %s'%(name,va,len(hits),[hex(x) for x in hits[:20]]))
