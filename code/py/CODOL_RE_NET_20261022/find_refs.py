import struct
p=r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read(); BASE=0x400000
for name,addr in [('connect',0x779B5710),('sendto',0x779B6160)]:
    pat=struct.pack('<I',addr)
    offs=[]; i=0
    while True:
        i=d.find(pat,i)
        if i<0: break
        offs.append(BASE+i); i+=1
    print(name,hex(addr),'hits',len(offs))
    for va in offs[:30]: print('   %#010x'%va)
targets={'WSAStartup':0xCA8534,'socket':0xCA8548,'bind':0xCA8554,'closesocket':0xCA8544,'ioctlsocket':0xCA854C,'inet_addr':0xCA8540,'gethostbyname':0xCA855C}
for nm,va in targets.items():
    pat=struct.pack('<I',va)
    hits=[];i=0
    while True:
        i=d.find(pat,i)
        if i<0:break
        hits.append(BASE+i); i+=1
    code=[h for h in hits if 0x401000<=h<0xE5C8000]
    print(nm,hex(va),'total',len(hits),'code',len(code), [hex(x) for x in code[:15]])
