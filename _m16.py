import struct, os, capstone
D=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\E1_20261029_103001\dump"
data=open(os.path.join(D,"snap_002.bin"),"rb").read(); LO=0x00010000
def off(va): return va-LO
BASE=0x400000; END=BASE+0x0E659000
buf=data[BASE-LO:END-LO]
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
# find "push 0x24 ; call 0xB74220"
alloc=[]
k=0
while True:
    k=buf.find(b"\x6A\x24\xE8",k)
    if k<0: break
    a=BASE+k
    rel=struct.unpack_from("<i",buf,k+3)[0]
    if a+7+rel==0xB74220: alloc.append(a)
    k+=1
print("reader allocations (push 0x24; call 0xB74220): %d"%len(alloc))
# for each, disasm forward 0x60 and look for store into [reg+0xB0]
for a in alloc:
    stores=[]
    c=0
    for i in md.disasm(buf[a-BASE:a-BASE+0x90],a):
        s=i.op_str.replace(" ","")
        if i.mnemonic=="mov" and s.endswith("+0xb0]"): stores.append((i.address,s))
        c+=1
        if c>40: break
    if stores:
        for ad,s in stores: print("   alloc@0x%08X -> store %s @0x%08X"%(a,s,ad))
print()
print("==== room channel 0x637000 (proper start) ====")
c=0
for i in md.disasm(buf[0x637000-BASE:0x637000-BASE+0x80],0x637000):
    print("  0x%08X  %-9s %s"%(i.address,i.mnemonic,i.op_str)); c+=1
    if c>24: break
