from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
import struct
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
# Is 0xBA3710 entered anywhere else via a jump table or indirect?
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== any reference to 0xBA3710 as data (jump table) ===")
tgt=struct.pack("<I",0xBA3710)
i=0; c=0
while True:
    j=data.find(tgt,i)
    if j<0: break
    va=BASE+j
    print("   data ref at %08X" % va); c+=1; i=j+1
print("count:", c)
print()
print("=== 0xBA4430 entry: is it reached from a table? ===")
tgt=struct.pack("<I",0xBA4430)
i=0; c=0
while True:
    j=data.find(tgt,i)
    if j<0: break
    print("   data ref at %08X" % (BASE+j)); c+=1; i=j+1
print("count:", c)
