from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG = Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data = IMG.read_bytes(); BASE=0x400000
md = Cs(CS_ARCH_X86, CS_MODE_32); md.skipdata=True
target=0xC781C0
callers=[]
for insn in md.disasm(data, BASE):
    if insn.mnemonic=="call" and insn.op_str.startswith("0x"):
        try: a=int(insn.op_str,16)
        except Exception: continue
        if a==target: callers.append(insn.address)
print("direct callers of 0xC781C0:", len(callers))
for c in callers: print("   %08X"%c)
# also search raw relative-call opcodes
import struct
pat=b""
print()
print("raw E8 rel32 to target:")
cnt=0
for i in range(len(data)-5):
    if data[i]==0xE8:
        rel=struct.unpack_from('<i',data,i+1)[0]
        if (BASE+i+5+rel) & 0xFFFFFFFF == target:
            print("   %08X"%(BASE+i)); cnt+=1
print("total raw", cnt)
