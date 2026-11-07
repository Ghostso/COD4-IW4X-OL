import pefile, capstone

patch_bytes = bytes.fromhex('68c8000000ff15bcb14410e9e2ffffff' + '90'*12)
assert len(patch_bytes) == 28, f"Patch length is {len(patch_bytes)}, expected 28"

paths = [
    r"E:\CODOL_SANDBOX\RUN001\Ayria\Plugins\CodolGameServer.Localnet32",
    r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\Ayria\Plugins\CodolGameServer.Localnet32"
]

target_off = 0x1EE735

for p in paths:
    with open(p, "rb") as f:
        data = bytearray(f.read())
    
    orig_chunk = data[target_off:target_off+28]
    print(f"[{p}] Original @ 0x{target_off:X}: {orig_chunk.hex()}")
    
    data[target_off:target_off+28] = patch_bytes
    with open(p, "wb") as f:
        f.write(data)
    print(f"[{p}] Patched successfully!")

# Verify disassembly of the patched file
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
with open(paths[0], "rb") as f:
    d = f.read()

print("\n--- Verified Disassembly around 0x101EF327 ---")
chunk = d[target_off - 14 : target_off + 35]
for ins in md.disasm(chunk, 0x101EF335 - 14):
    print("  0x%08X: %-10s %s" % (ins.address, ins.mnemonic, ins.op_str))
