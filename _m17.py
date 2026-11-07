import struct, os, capstone
D=r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\E1_20261029_103001\dump"
data=open(os.path.join(D,"snap_002.bin"),"rb").read(); LO=0x00010000
BASE=0x400000; END=BASE+0x0E659000; buf=data[BASE-LO:END-LO]
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
print("==== 0x637037 onward (what the room reader does) ====")
c=0
for i in md.disasm(buf[0x637037-BASE:0x637037-BASE+0xA0],0x637037):
    print("  0x%08X  %-9s %s"%(i.address,i.mnemonic,i.op_str)); c+=1
    if c>34: break
print()
# who allocates reader and stores to [x+0xB0] within a wider window
print("==== allocations near a +0xb0 store (window 0x200) ====")
k=0; found=0
while True:
    k=buf.find(b"\x6A\x24\xE8",k)
    if k<0: break
    a=BASE+k
    rel=struct.unpack_from("<i",buf,k+3)[0]
    if a+7+rel==0xB74220:
        win=buf[k:k+0x200]
        if b"\xb0" in win:
            for i in md.disasm(win,a):
                s=i.op_str.replace(" ","")
                if i.mnemonic=="mov" and s.endswith("+0xb0]") and not s.startswith("dwordptr[0x"):
                    print("   alloc@0x%08X store %s @0x%08X"%(a,s,i.address)); found+=1
            pass
    k+=1
print("  total with +0xb0 store in window:",found)
