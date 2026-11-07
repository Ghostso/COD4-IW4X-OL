# EBO1 - build disk-based Local RM proxy: a COPY of iips.dll with an embedded,
# position-relocatable Local RM object so GetResourceManagerII/GetResourceManager
# return a valid RM from the very first call (eliminates the runtime patch race).
# Original iips.dll is NEVER touched; output goes to the sandbox tree only.
import struct, os, sys, shutil

SRC = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\IIPS\iips.dll'
DST = r'D:\BaiduNetdiskDownload\使命召唤OL\工具\EB1_SANDBOX\IIPS\iips.dll'

IMG = 0x10000000
d = bytearray(open(SRC, 'rb').read())
pe = struct.unpack_from('<I', d, 0x3C)[0]
numsec = struct.unpack_from('<H', d, pe + 6)[0]
szopt = struct.unpack_from('<H', d, pe + 20)[0]
opt = pe + 24
sechdr = opt + szopt

secs = []
for i in range(numsec):
    off = sechdr + i * 40
    name = bytes(d[off:off + 8]).rstrip(b'\x00').decode('ascii', 'replace')
    vs, va, rs, rp = struct.unpack_from('<IIII', d, off + 8)
    secs.append((name, vs, va, rs, rp, off))
    print('sec', name, 'va=%08X vs=%X raw=%X rawptr=%X' % (va, vs, rs, rp))

# strip authenticode certificate (signature becomes invalid anyway after patching)
cert_rva, cert_sz = struct.unpack_from('<II', d, opt + 96 + 4 * 8)
if cert_rva:
    struct.pack_into('<II', d, opt + 96 + 4 * 8, 0, 0)
    print('cert stripped @%X size %X' % (cert_rva, cert_sz))
    d = d[:cert_rva]  # drop overlay

# old .reloc content
reloc = next(s for s in secs if s[0] == '.reloc')
old_reloc = bytes(d[reloc[4]:reloc[4] + reloc[2]])
old_reloc_size = struct.unpack_from('<I', d, opt + 96 + 5 * 8 + 4)[0]
old_reloc = old_reloc[:old_reloc_size]

# new section .ebo - NOTE: FileAlignment == SectionAlignment == 0x1000 in this DLL,
# so the loader requires PointerToRawData == VirtualAddress for every section.
prev_end = max(s[2] + max(s[1], s[3]) for s in secs)  # last va+size
secVA = (prev_end + 0xFFF) & ~0xFFF
secRAWV = secVA  # ROM-image rule: raw offset must equal VA
secVS = 0x8000
secRaw = (secVS + 0xFFF) & ~0xFFF
if len(d) < secRAWV:
    d += b'\x00' * (secRAWV - len(d))
sec = bytearray(secVS)

RELOCS = []  # offsets within new section needing HIGHLOW reloc
def put32(off, val, reloc=True):
    struct.pack_into('<I', sec, off, val)
    if reloc:
        RELOCS.append(off)

# ---- stubs: 48 x 0x20 bytes at 0x800 ----
STUBS = 0x800
for i in range(48):
    so = STUBS + i * 0x20
    ctr = secVA + 0x1000 + i * 4
    # call $+5 ; pop ecx ; lea eax,[ecx+d1](rm) ; lea ecx,[ecx+d2](ctr) ; inc [ecx] ; eax=val ; ret
    code = bytearray()
    code += b'\xE8\x00\x00\x00\x00'          # 5
    code += b'\x59'                          # pop ecx  (ecx = base + secVA + so + 5)
    d1 = (secVA + 0x000) - (secVA + so + 5)  # rm object
    d2 = ctr - (secVA + so + 5)
    code += b'\x8D\x81' + struct.pack('<i', d1)
    code += b'\x8D\x89' + struct.pack('<i', d2)
    code += b'\xFF\x01'                      # inc dword [ecx]
    if i == 2:
        code += b'\xB8\x01\x00\x00\x00'      # mov eax,1
    else:
        code += b'\x33\xC0'                  # xor eax,eax
    code += b'\xC3'
    sec[so:so + len(code)] = code

# ---- RM object at 0x000 ----
put32(0x000, IMG + secVA + 0x500)            # vtable ptr
sec[4:4 + 14] = b'LocalRM_v5ds\x00\x00'
put32(0x070, IMG + secVA + 0x700)
put32(0x074, IMG + secVA + 0x740)
struct.pack_into('<I', sec, 0x078, 0xFFFFFFFF)
put32(0x0B4, IMG + secVA + 0x780)
put32(0x104, IMG + secVA + STUBS + 2 * 0x20)

# ---- vtables ----
for i in range(48):
    put32(0x500 + i * 4, IMG + secVA + STUBS + i * 0x20)
for i in range(12):
    put32(0x700 + i * 4, IMG + secVA + STUBS + (2 if i == 2 else 0) * 0x20)
for i in range(8):
    put32(0x740 + i * 4, IMG + secVA + STUBS + (1 if i == 0 else 0) * 0x20)
for i in range(4):
    put32(0x780 + i * 4, IMG + secVA + STUBS + 3 * 0x20)

# ---- GRMII/GRM patches ----
GRM_CTR = secVA + 0x10C0
def patch_export(rva):
    code = bytearray()
    code += b'\xE8\x00\x00\x00\x00'          # call $+5
    code += b'\x59'                          # pop ecx (ecx = base + rva + 5)
    d1 = (secVA + 0x000) - (rva + 5)
    d2 = GRM_CTR - (rva + 5)
    code += b'\x8D\x81' + struct.pack('<i', d1)
    code += b'\x8D\x89' + struct.pack('<i', d2)
    code += b'\xFF\x01'                      # inc dword [ecx]
    code += b'\xC3'
    return code

for rva in (0x1C80, 0x1BC0):
    code = patch_export(rva)
    # .text: va=0x1000 rawptr=0x1000 so file offset == rva
    d[rva:rva + len(code)] = code
    print('patched export RVA %X with %d bytes' % (rva, len(code)))

# ---- reloc table: copy old, append our block ----
reloff = 0x2000
blk_entries = sorted(set(RELOCS))
blk = struct.pack('<II', secVA, 8 + 2 * len(blk_entries))
blk += b''.join(struct.pack('<H', 0x3000 | e) for e in blk_entries)
while len(blk) % 4:
    blk += b'\x00\x00'
new_reloc = old_reloc + blk
sec[reloff:reloff + len(new_reloc)] = new_reloc
struct.pack_into('<II', d, opt + 96 + 5 * 8, secVA + reloff, len(new_reloc))
print('reloc table moved: old=%d new=%d (+%d entries)' % (len(old_reloc), len(new_reloc), len(blk_entries)))

# ---- write section header ----
noff = sechdr + numsec * 40
name = b'.ebo\x00\x00\x00\x00'
struct.pack_into('<8sIIIIIIHHI', d, noff, name, secVS, secVA, secRaw, secRAWV, 0, 0, 0, 0, 0xE0000040)
struct.pack_into('<H', d, pe + 6, numsec + 1)
newsize = (secVA + secVS + 0xFFF) & ~0xFFF
struct.pack_into('<I', d, opt + 56, newsize)
struct.pack_into('<I', d, opt + 64, 0)  # checksum zeroed

assert len(sec) <= secVS, 'section payload overflow: %X > %X' % (len(sec), secVS)
d += bytes(sec[:secVS])
os.makedirs(os.path.dirname(DST), exist_ok=True)
open(DST, 'wb').write(bytes(d))
print('written', DST, 'size %X' % len(d), 'secVA=%X' % secVA)
print('VERIFY ORIGINAL UNCHANGED:')
import hashlib
print('orig md5', hashlib.md5(open(SRC, 'rb').read()).hexdigest())
