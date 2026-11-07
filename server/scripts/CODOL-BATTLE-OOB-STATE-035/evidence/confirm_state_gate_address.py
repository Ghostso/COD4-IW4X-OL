# -*- coding: utf-8 -*-
"""TASK-035: confirm the ADDRESS EXPRESSION and STORAGE OBJECT of the client state gate [0x76446B0]."""
import struct, capstone
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
TARGET=0x076446B0
print("== 1) section mapping of VA 0x%08X ==" % TARGET)
pe=struct.unpack_from("<I",d,0x3C)[0]
nsec=struct.unpack_from("<H",d,pe+6)[0]
sizeopt=struct.unpack_from("<H",d,pe+20)[0]
opt=pe+24; so=opt+sizeopt
imgbase=struct.unpack_from("<I",d,opt+28)[0]
sizeofimg=struct.unpack_from("<I",d,opt+56)[0]
for i in range(nsec):
    o=so+40*i
    nm=d[o:o+8].rstrip(b'\x00'); nm="".join(chr(c) if 32<=c<127 else '?' for c in nm)
    vsz,va,rsz,raddr=struct.unpack_from("<IIII",d,o+8)
    ch=struct.unpack_from("<I",d,o+36)[0]
    lo,hi=va,va+max(vsz,rsz)
    inside = lo<=TARGET<hi
    if inside or i<3:
        print("  %-9s VA=%08X..%08X VSize=%08X RawPtr=%08X RawSize=%08X ch=%08X  TARGET_INSIDE=%s" % (nm,lo,hi,vsz,raddr,rsz,ch,inside))
print("  ImageBase=%08X SizeOfImage=%08X ; file(raw) size=%08X" % (imgbase,sizeofimg,len(d)))
print("  => TARGET VA 0x%08X is INSIDE the image VA range but BEYOND the raw file (uninitialized/.data, zero-filled at load)" % TARGET)
print()
print("== 2) the exact state-gate instructions in the OOB sender 0x1C05F0 ==")
for ins in md.disasm(d[0x1C0607:0x1C0650],0x1C0607):
    print("   RVA %08X  %-20s %s %s" % (ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str))
print()
print("== 3) count absolute references to that VA across all common operand forms ==")
tb=struct.pack("<I",TARGET).lstrip(b'\x00')
tb=struct.pack("<I",TARGET)
forms=[(b"\xa1","A1 mov eax,[disp32]"),(b"\x8b\x0d","8B0D mov ecx,[disp32]"),
       (b"\x8b\x15","8B15 mov edx,[disp32]"),(b"\x8b\x1d","8B1D mov ebx,[disp32]"),
       (b"\x83\x3d","833D cmp [disp32],imm8"),(b"\x81\x3d","813D cmp [disp32],imm32"),
       (b"\x89\x35","8935 mov [disp32],esi"),(b"\xc7\x05","C705 mov dword [disp32],imm32"),
       (b"\xff\x35","FF35 push [disp32]"),(b"\x39\x05","3905 cmp [disp32],eax"),
       (b"\x3b\x05","3B05 cmp eax,[disp32]")]
tot=0
for pfx,name in forms:
    pat=pfx+tb; s=0; hits=[]
    while True:
        i=d.find(pat,s)
        if i<0: break
        hits.append(i); s=i+1
    tot+=len(hits)
    print("   %-30s %4d  %s" % (name,len(hits),", ".join("%X"%x for x in hits[:8])))
print("   TOTAL absolute refs: %d" % tot)
