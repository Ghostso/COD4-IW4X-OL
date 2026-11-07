import pefile, os, shutil

game_dir = r"E:\CODOL_SANDBOX\RUN001"
client_exe = os.path.join(game_dir, "codoMP_client_shipRetail.exe")
ded_exe = os.path.join(game_dir, "codoMP_dedicated_server.exe")

# 1. Read bytes from client_exe
with open(client_exe, "rb") as f:
    d = bytearray(f.read())

pe = pefile.PE(data=d, fast_load=True)
name_rva = 0x9DBA14
off = pe.get_offset_from_rva(name_rva)
pe.close()

old_name = b"Global\\{{5BD75B76-601A-4b20-80C8-D2317C94BB30}}"
new_name = b"Global\\{{5BD75B76-601A-4b20-80C8-D2317C94BB31}}"

cur_name = d[off:off+len(old_name)]
print("Current mutex name at 0x%X:" % off, bytes(cur_name))
assert bytes(cur_name) == old_name, "Mutex name mismatch!"

d[off:off+len(new_name)] = new_name
with open(ded_exe, "wb") as f:
    f.write(d)

print(f"Patched dedicated mutex name in {ded_exe} successfully!")
