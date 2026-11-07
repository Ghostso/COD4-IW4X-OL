import pefile, os, shutil

# 1. Patch installDedicatedProcessPatches in CodolGameServer.Localnet32
paths = [
    r"E:\CODOL_SANDBOX\RUN001\Ayria\Plugins\CodolGameServer.Localnet32",
    r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\Ayria\Plugins\CodolGameServer.Localnet32",
    r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\CodolGameServer.dll"
]

target_off = 0x62B90 # VA 0x10063790
patch_code = bytes.fromhex("b801000000c3") # mov eax, 1; ret

for p in paths:
    if not os.path.exists(p): continue
    with open(p, "rb") as f:
        data = bytearray(f.read())
    orig = data[target_off:target_off+6]
    print(f"[{p}] Original @ 0x{target_off:X}: {orig.hex()}")
    assert orig.hex().startswith("558bec83"), f"Mismatch at offset 0x{target_off:X}"
    data[target_off:target_off+6] = patch_code
    with open(p, "wb") as f:
        f.write(data)
    print(f"[{p}] Patched installDedicatedProcessPatches -> mov eax, 1; ret!")

# 2. Create codoMP_dedicated_server.exe with distinct single-instance mutex
game_dir = r"E:\CODOL_SANDBOX\RUN001"
client_exe = os.path.join(game_dir, "codoMP_client_shipRetail.exe")
ded_exe = os.path.join(game_dir, "codoMP_dedicated_server.exe")

shutil.copy2(client_exe, ded_exe)
print(f"Copied {client_exe} -> {ded_exe}")

pe = pefile.PE(ded_exe)
name_rva = 0x9DBA14
off = pe.get_offset_from_rva(name_rva)

with open(ded_exe, "rb") as f:
    d = bytearray(f.read())

old_name = b"Global\\{{5BD75B76-601A-4b20-80C8-D2317C94BB30}}"
new_name = b"Global\\{{5BD75B76-601A-4b20-80C8-D2317C94BB31}}"

cur_name = d[off:off+len(old_name)]
print("Current mutex name at 0x%X:" % off, bytes(cur_name))
assert bytes(cur_name) == old_name, "Mutex name mismatch!"

d[off:off+len(new_name)] = new_name
with open(ded_exe, "wb") as f:
    f.write(d)

print(f"Patched dedicated mutex name in {ded_exe} successfully!")
