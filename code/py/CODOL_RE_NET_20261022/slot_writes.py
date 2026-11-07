import struct
p=r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read(); BASE=0x400000
slots=[0xCA8534,0xCA8538,0xCA853C,0xCA8540,0xCA8544,0xCA8548,0xCA854C,0xCA8550,0xCA8554,0xCA855C]
for s in slots:
    b=struct.pack('<I',s)
    for prefix,name in [(b'\xc7\x05',"mov dword [slot],imm32"),(b'\x89\x05',"mov [slot],eax"),(b'\x8b\x05',"mov eax,[slot]")]:
        hits=[]; i=0
        while True:
            i=d.find(prefix+b,i)
            if i<0: break
            hits.append(BASE+i); i+=1
        if hits: print('%s %#x: %s'%(name,s,[hex(x) for x in hits[:10]]))
