"""Final validation script for Tier-1 static analysis."""
import struct

IMG = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
data = open(IMG, "rb").read()

print("=== FINAL VALIDATION ===")
print("File size:", len(data))
print()

# 1. marketplace.json string
off = 0xDB6CC4 - BASE
s = data[off:data.find(b"\x00", off, off + 64)].decode("ascii")
print("0xDB6CC4 string:", s)

# 2. Gate flags
print("0xE60B80 byte:", data[0xE60B80 - BASE])
print("0xE60B81 byte:", data[0xE60B81 - BASE])
print("0xE60B82 byte:", data[0xE60B82 - BASE])

# 3. State 6 enable
print("0xE57A5A byte:", data[0xE57A5A - BASE])
print("0xE57A54 byte:", data[0xE57A54 - BASE])

# 4. Fallback string
off = 0xDAE091 - BASE
print("0xDAE091 bytes:", data[off:off + 8].hex(" "))
print("  strlen:", data.find(b"\x00", off, off + 256) - off)

# 5. Count refs to 0xC7AF440
pat = struct.pack("<I", 0xC7AF440)
cnt = 0
i = data.find(pat)
while i != -1:
    cnt += 1
    op = data[i - 2:i].hex(" ")
    print("  ref at 0x%08X, opcode: %s" % (BASE + i, op))
    i = data.find(pat, i + 1)
print("Total refs to 0xC7AF440:", cnt)

# 6. Call sites of FetchMarketplaceJson
pat2 = struct.pack("<I", 0x4A93E0)
cnt2 = 0
i = data.find(pat2)
while i != -1:
    if data[i - 5] == 0xE8:
        cnt2 += 1
        print("  CALL to 0x4A93E0 at 0x%08X" % (BASE + i - 5))
    i = data.find(pat2, i + 1)
print("Call sites of FetchMarketplaceJson:", cnt2)

# 7. GateWriteFn xref check
pat3 = struct.pack("<I", 0x4A8F00)
cnt3 = 0
i = data.find(pat3)
while i != -1:
    if data[i - 5] == 0xE8:
        cnt3 += 1
        print("  CALL to 0x4A8F00 at 0x%08X" % (BASE + i - 5))
    i = data.find(pat3, i + 1)
print("Call sites of GateWriteFn (0x4A8F00):", cnt3)
