import pefile, struct
p = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe'
data = open(p,'rb').read()
pe = pefile.PE(p, fast_load=True)
ib = pe.OPTIONAL_HEADER.ImageBase
# map rva -> file offset
def rva2fo(rva):
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            d = rva - s.VirtualAddress
            if d < s.SizeOfRawData:
                return s.PointerToRawData + d
    return None
def fo2rva(fo):
    for s in pe.sections:
        if s.PointerToRawData <= fo < s.PointerToRawData + s.SizeOfRawData:
            return s.VirtualAddress + (fo - s.PointerToRawData)
    return None

# dump sentinel table around 0xca8000
fo = rva2fo(0xca8000)
print('sentinel table file offset', hex(fo))
vals = struct.unpack_from('<64I', data, fo)
print('sentinel[0..64]')
for i in range(0,64,8):
    print('  ', ' '.join('%08x'%v for v in vals[i:i+8]))
# how many FF15 reference 0xca8xxx range
cnt = 0
for i in range(0, len(data)-6):
    if data[i:i+2] == b'\xff\x15':
        slot = struct.unpack_from('<I', data, i+2)[0]
        if 0xca8000 <= slot < 0xca9000:
            cnt += 1
print('ff15 -> slot in 0xca8xxx:', cnt)
# count slots referenced
from collections import Counter
c = Counter()
for i in range(0, len(data)-6):
    if data[i:i+2] == b'\xff\x15':
        slot = struct.unpack_from('<I', data, i+2)[0]
        c[slot] += 1
print('top slots:')
for slot, n in c.most_common(20):
    print('   %08x  x%d' % (slot, n))
print('total distinct slots', len(c), 'total ff15', sum(c.values()))
