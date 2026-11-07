import struct
d=open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin","rb").read()
B=0x400000
for target in [0x0E7B6490, 0x0E7B6496, 0x0E7B6498]:
    pat=struct.pack("<I",target); h=[]; i=0
    while True:
        i=d.find(pat,i)
        if i<0: break
        v=B+i
        if 0x401000<=v<0x0E5C8000: h.append(v)
        i+=1
    print(hex(target),"refs",len(h),[hex(x) for x in h[:16]])
