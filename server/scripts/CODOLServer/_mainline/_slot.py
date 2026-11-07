import struct
exe = r"run_codol_001\sandbox_datafix_20260929\codoMP_client_shipRetail.exe"
data = open(exe,'rb').read()
# section 2: va=0x008A8000 raw=0x594000
raw = 0x594000 + (0x8A8128 - 0x8A8000)
print("file off", hex(raw))
b = data[raw-32:raw+32]
print("bytes around 0xCA8128 (as file content):")
for i in range(0, 64, 16):
    va = 0x8A8128 - 32 + i
    print(f"  {va:08X}  {b[i:i+16].hex()}")
print()
val = struct.unpack_from('<I', data, raw)[0]
print("value at slot = 0x%08X" % val)
