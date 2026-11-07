import struct
d = open(r"run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin", "rb").read()
B = 0x400000
base = 0x3306994

# write patterns: mov [reg*4+base], reg32  => 89 0C 85 base / 89 14 85 base / 89 04 85 base ...
pats = []
for modrm in range(0x00, 0x40):
    pass
sigs = {
    "mov [eax*4+b], ecx": bytes([0x89,0x0C,0x85]) + struct.pack("<I", base),
    "mov [eax*4+b], edx": bytes([0x89,0x14,0x85]) + struct.pack("<I", base),
    "mov [eax*4+b], eax": bytes([0x89,0x04,0x85]) + struct.pack("<I", base),
    "mov [eax*4+b], esi": bytes([0x89,0x34,0x85]) + struct.pack("<I", base),
    "mov [eax*4+b], edi": bytes([0x89,0x3C,0x85]) + struct.pack("<I", base),
    "mov [eax*4+b], ebx": bytes([0x89,0x1C,0x85]) + struct.pack("<I", base),
    "mov [ecx*4+b], eax": bytes([0x89,0x04,0x8D]) + struct.pack("<I", base),
    "mov [ecx*4+b], edx": bytes([0x89,0x14,0x8D]) + struct.pack("<I", base),
    "mov [edx*4+b], eax": bytes([0x89,0x04,0x95]) + struct.pack("<I", base),
    "mov [edx*4+b], ecx": bytes([0x89,0x0C,0x95]) + struct.pack("<I", base),
    "mov dword [eax*4+b], imm": bytes([0xC7,0x04,0x85]) + struct.pack("<I", base),
    "mov dword [ecx*4+b], imm": bytes([0xC7,0x04,0x8D]) + struct.pack("<I", base),
}
for name, sig in sigs.items():
    hits = []
    i = 0
    while True:
        i = d.find(sig, i)
        if i < 0:
            break
        v = B + i
        if 0x401000 <= v < 0xE5C8000:
            hits.append(v)
        i += 1
    if hits:
        print(name, len(hits), [hex(x) for x in hits[:10]])
print("done")
