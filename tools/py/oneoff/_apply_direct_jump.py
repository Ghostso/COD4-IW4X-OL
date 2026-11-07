import pefile

paths = [
    r"E:\CODOL_SANDBOX\RUN001\Ayria\Plugins\CodolGameServer.Localnet32",
    r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\Ayria\Plugins\CodolGameServer.Localnet32",
    r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\CodolGameServer.dll"
]

target_off = 0x209FB7 # VA 0x1020ABB7
patch_bytes = bytes.fromhex('e95b0b0000') # jmp 0x1020B717

# Also clean up 0x20A021 back to 8 NOPs
target_off2 = 0x20A021
nops = b'\x90' * 8

for p in paths:
    with open(p, "rb") as f:
        data = bytearray(f.read())
    
    orig = data[target_off:target_off+5]
    print(f"[{p}] Original @ 0x{target_off:X}: {orig.hex()}")
    assert orig.hex() == '6838cc5810', "Original bytes mismatch at 0x209FB7"
    
    data[target_off:target_off+5] = patch_bytes
    data[target_off2:target_off2+8] = nops
    
    with open(p, "wb") as f:
        f.write(data)
    print(f"[{p}] Patched jump to 0x1020B717 successfully!")

print("\nAll copies updated with direct jump to RVA assignment!")
