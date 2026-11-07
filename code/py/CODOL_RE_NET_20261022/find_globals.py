import struct
p=r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read(); BASE=0x400000
targets={'auth_host':0x081A76A8,'lsg_host':0x081A7F34,'port_lo':0x081A9780,'port_hi':0x081A9784,'port2':0x081A9EC4,'conn_obj':0x08269774,'dwstate':0x0849BA34,'st':0x084ABA50,'tqos_host':0x081A9C50}
for name,va in targets.items():
    pat=struct.pack('<I',va); hits=[]; i=0
    while True:
        i=d.find(pat,i)
        if i<0: break
        v=BASE+i
        if 0x401000<=v<0xE5C8000: hits.append(v)
        i+=1
    print('%-10s %#010x refs=%d %s'%(name,va,len(hits),[hex(x) for x in hits[:16]]))
