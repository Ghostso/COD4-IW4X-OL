import re, struct
img = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000
d = open(img,"rb").read()
pats = [
    (rb"\xc7\x85(....)\xe6\x02\x00\x00", "mov [ebp+disp32],0x2E6"),
    (rb"\xc7\x45(.)\xe6\x02\x00\x00",    "mov [ebp+disp8],0x2E6"),
    (rb"\xc7\x05(....)\xe6\x02\x00\x00", "mov [addr],0x2E6"),
]
for pat, name in pats:
    for m in re.finditer(pat, d, re.S):
        off = m.start(); va = BASE + off
        if "disp32" in name:
            disp = struct.unpack("<i", m.group(1))[0]; extra = " [ebp%+#x]" % disp
        elif "disp8" in name:
            disp = struct.unpack("<b", m.group(1))[0]; extra = " [ebp%+#x]" % disp
        else:
            addr = struct.unpack("<I", m.group(1))[0]; extra = " [0x%08X]" % addr
        print("0x%08X  %s%s" % (va, name, extra))
