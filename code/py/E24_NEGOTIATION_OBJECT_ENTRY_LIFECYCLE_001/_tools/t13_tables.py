import sys, struct
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\E24_NEGOTIATION_OBJECT_ENTRY_LIFECYCLE_001\_tools")
from peh import *
img = Img()
print("=== obj+0xC region via ACE180: cmp [ecx+4] where ecx=this+0xC ===")
# ACE180: arg2=ebp+0xc, arg3(=ecx)=ebp+0x10 => ecx is second? Let's re-read call:
# slot+3: push esi(this+0xC); push 0x10; push arg1 -> ACE180(arg1, 0x10, this+0xC)
print("call convention at 0xA87D50 -> ACE180:")
for i in img.dis(0x687D50,0x18):
    print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
print()
print("=== ACE180 arg mapping ===")
for i in img.dis(0x6CE180,0x16):
    print("  %06X %s %s"%(i.address-img.IB,i.mnemonic,i.op_str))
print("  -> arg1(ebp+8)=buf, arg2(ebp+0xC)=0x10, arg3(ebp+0x10)=this+0xC")
print("  cmp [arg3+4], arg2  => compares this+0x10 (dword) with 0x10")
print()
print("=== table base 0xD48F48 / 0xD48F60 / 0xD48F64 (VA) ===")
for va in (0xD48F48,0xD48F60,0xD48F64):
    print("  VA %08X sec=%s"%(va, img.sec(va-img.IB)))
b=img.rd(0xD48F00,0x80)
for i in range(0,0x80,4):
    v=struct.unpack_from("<I",b,i)[0]
    print("  0x%08X = %08X"%(0xD48F00+i,v))
