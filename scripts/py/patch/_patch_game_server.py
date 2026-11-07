import shutil

src = r"E:\CODOL_SANDBOX\RUN001\Ayria\Plugins\CodolGameServer.Localnet32"
bak = r"E:\CODOL_SANDBOX\RUN001\Ayria\Plugins\CodolGameServer.Localnet32.bak"

shutil.copy2(src, bak)
print(f"Backed up to {bak}")

with open(src, "rb") as f:
    data = f.read()

old_val = (0x0E5D6000).to_bytes(4, "little")
new_val = (0x0E659000).to_bytes(4, "little")

count = data.count(old_val)
print(f"Found {count} occurrences of 0x0E5D6000")

patched = data.replace(old_val, new_val)
assert len(patched) == len(data), "Length mismatch!"
assert patched.count(old_val) == 0, "Old value still present!"
assert patched.count(new_val) == count, f"New value count mismatch: {patched.count(new_val)} vs {count}"

with open(src, "wb") as f:
    f.write(patched)

print("Patch applied successfully to E:\\CODOL_SANDBOX\\RUN001\\Ayria\\Plugins\\CodolGameServer.Localnet32!")
