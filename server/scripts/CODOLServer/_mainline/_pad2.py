import sys, importlib.util
spec=importlib.util.spec_from_file_location("lp", r"CODOLServer\lobby_server\lobby_plain_probe.py")
lp=importlib.util.module_from_spec(spec); sys.modules["lp"]=lp; spec.loader.exec_module(lp)

CONST24 = bytes.fromhex("ad42f59088a421e63bc9890239ff02dc110477ffee88620d")
# groups as written in the disassembly: 6,6,6,5 dwords
GROUPS = [[0x08,0x12,0x09,0x0E,0x05,0x14],
          [0x0A,0x07,0x0B,0x0C,0x15,0x16],
          [0x0D,0x10,0x03,0x00,0x01,0x0F],
          [0x13,0x11,0x17,0x06,0x04]]
# The loop reads [esi-4] for the FIRST byte of each group, i.e. the index
# at esi-4.  esi starts at ebp-0x78 and the table begins at ebp-0x7C, so the
# very first read is table[0].  Then it reads [esi], [esi+4] ... [esi+0x10]
# which is 5 more, for 6 per group.  After 4 groups esi has advanced 0x60.
flat=[GROUPS[0][0]]
for g in GROUPS:
    flat.extend(g)
    # after consuming a group the pointer advances by 0x18 = 6 dwords
flat = flat[:24]
print("flat indices (%d):" % len(flat), [hex(x) for x in flat])
pad = bytes(CONST24[i] for i in flat)
print("XOR pad:", pad.hex())
def transform(src):
    return bytes(src[i] ^ pad[i] for i in range(min(24,len(src))))
print("roundtrip:", transform(transform(bytes(range(24)))) == bytes(range(24)))
