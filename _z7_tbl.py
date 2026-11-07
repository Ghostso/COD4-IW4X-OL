from capstone import Cs, CS_ARCH_X86, CS_MODE_32
img = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
d = open(img,"rb").read()
md = Cs(CS_ARCH_X86, CS_MODE_32)
# scan back for the prologue (push ebp; mov ebp,esp) before 0x803EE0
o = 0x803EE0 - BASE
back = d[o-0x200:o]
idx = back.rfind(b"\x55\x8b\xec")
print("prologue at VA:", hex(0x803EE0-0x200+idx) if idx>=0 else "not found")
start = 0x803EE0-0x200+idx if idx>=0 else 0x803EE0
n=0
for ins in md.disasm(d[start-BASE:start-BASE+0x80], start):
    print("0x%08X  %-18s %s %s" % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
    n+=1
    if n>15: break
