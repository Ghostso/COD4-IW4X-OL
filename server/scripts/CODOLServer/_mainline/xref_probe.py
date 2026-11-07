import pefile, struct
p = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe'
data = open(p,'rb').read()
pe = pefile.PE(p, fast_load=True)
ib = pe.OPTIONAL_HEADER.ImageBase
# target string VA
fo = 0x6a8fe0
rva = 0x9BCFE0
va = ib + rva
needle = struct.pack('<I', va)
hits = []
for i in range(0, len(data)-4):
    if data[i:i+4] == needle:
        hits.append(i)
print('config_mp cfg VA', hex(va), 'imm32 hits', len(hits), [hex(x) for x in hits])

# all FF 15 in raw-backed executable sections
for s in pe.sections:
    if not (s.Characteristics & 0x20000000):
        continue
    start = s.PointerToRawData
    end = start + s.SizeOfRawData
    sec = data[start:end]
    ff15 = []
    for i in range(0, max(0,len(sec)-6)):
        if sec[i:i+2] == b'\xff\x15':
            slot = struct.unpack_from('<I', sec, i+2)[0]
            ff15.append((s.VirtualAddress + i, slot))
    print('SECTION', s.Name.decode(errors='replace').strip(), 'rva', hex(s.VirtualAddress), 'raw', hex(start), 'ff15', len(ff15))
    for r, slot in ff15[:20]:
        fo2 = s.PointerToRawData + (r - s.VirtualAddress)
        print('  rva=%08x va=%08x slot=%08x file=%08x' % (r, ib+r, slot, fo2))
