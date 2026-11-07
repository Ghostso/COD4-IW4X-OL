import pefile, capstone

exe = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\codoMP_client_shipRetail.exe"
pe = pefile.PE(exe)
base = pe.OPTIONAL_HEADER.ImageBase
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

with open(exe, "rb") as f:
    d = f.read()

# SV_UnlinkEntity is at RVA 0x217B05 (file offset 0x217B05)
# Let's inspect functions in the range RVA 0x216000 to 0x219000
start_rva = 0x216E00
end_rva = 0x218800
off = pe.get_offset_from_rva(start_rva)
size = end_rva - start_rva
data = d[off:off+size]

insns = list(md.disasm(data, base + start_rva))

# Find function entries (preceded by ret/int3 or standard prologues like push ebp; mov ebp, esp)
funcs = []
for i in range(len(insns)):
    ins = insns[i]
    if ins.mnemonic == 'push' and ins.op_str == 'ebp' and i + 1 < len(insns) and insns[i+1].mnemonic == 'mov' and insns[i+1].op_str == 'ebp, esp':
        funcs.append((ins.address - base, ins.address, insns[i:i+8]))
    elif ins.address == base + 0x217B05:
        funcs.append((0x217B05, ins.address, insns[i:i+8]))

print(f"Found {len(funcs)} functions around 0x217B05:")
for rva, va, f_insns in funcs:
    code_str = " ".join(f"{x.mnemonic} {x.op_str};" for x in f_insns[:5])
    raw = d[pe.get_offset_from_rva(rva):pe.get_offset_from_rva(rva)+12].hex()
    mark = "  <-- SV_UnlinkEntity" if rva == 0x217B05 else ""
    print(f"  RVA 0x{rva:06X} (VA 0x{va:08X}): {raw} | {code_str}{mark}")
