# Find a byte offset in the connection object that the observer samples
# but which is NOT used as a pointer/dword by the game.
# Candidate: obj+0x5E0 (a byte field per 0xBA2950 "mov byte [esi+0x5E0], bl")
from pathlib import Path
from capstone import CS_ARCH_X86, CS_MODE_32, Cs
IMG=Path(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin")
data=IMG.read_bytes(); BASE=0x400000
md=Cs(CS_ARCH_X86,CS_MODE_32); md.skipdata=True
print("=== byte-sized writes to obj (mov byte [reg+off], ..) in 0xBA3000..0xBA5000 ===")
seen={}
lo,hi=0xBA3000,0xBA5000
for insn in md.disasm(data[lo-BASE:hi-BASE], lo):
    o=insn.op_str
    if insn.mnemonic=="mov" and o.startswith("byte ptr [") and o.split(",")[0].endswith("]"):
        dst=o.split(",")[0]
        import re
        m=re.search(r"\+ 0x([0-9a-f]+)\]", dst)
        if m: seen.setdefault(m.group(1), []).append(insn.address)
for off,addrs in sorted(seen.items()):
    print("   +0x%-4s  %d writes  first=0x%08X" % (off, len(addrs), addrs[0]))
