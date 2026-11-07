patch_bytes = bytes.fromhex('e9f10a0000909090')
assert len(patch_bytes) == 8

paths = [
    r"E:\CODOL_SANDBOX\RUN001\Ayria\Plugins\CodolGameServer.Localnet32",
    r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\Ayria\Plugins\CodolGameServer.Localnet32",
    r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\CodolGameServer.dll"
]

target_off = 0x20A021

for p in paths:
    with open(p, "rb") as f:
        data = bytearray(f.read())
    
    orig = data[target_off:target_off+8]
    print(f"[{p}] Original @ 0x{target_off:X}: {orig.hex()}")
    assert orig.hex() == '85ff0f84e6000000', "Original bytes mismatch!"
    
    data[target_off:target_off+8] = patch_bytes
    with open(p, "wb") as f:
        f.write(data)
    print(f"[{p}] Bypass patch applied successfully!")

print("\nAll 3 copies patched with prefix-bypass jump!")
