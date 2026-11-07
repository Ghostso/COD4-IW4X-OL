import re, struct
img = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
d = open(img,"rb").read()
target = 0xB9A470
print("=== callers of 0xB9A470 ===")
for m in re.finditer(rb"\xe8(....)", d, re.S):
    off = m.start()
    rel = struct.unpack("<i", m.group(1))[0]
    if BASE + off + 5 + rel == target:
        va = BASE + off
        print("  call at 0x%08X" % va)
        print("    arg setup (16B before):", " ".join("%02X"%x for x in d[off-16:off+5]))
