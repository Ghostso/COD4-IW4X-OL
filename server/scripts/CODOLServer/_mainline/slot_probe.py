import pefile, struct
from collections import Counter
p = r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe'
data = open(p,'rb').read()
pe = pefile.PE(p, fast_load=True)
def rva2fo(rva):
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + s.Misc_VirtualSize:
            d = rva - s.VirtualAddress
            if d < s.SizeOfRawData:
                return s.PointerToRawData + d
    return None
c = Counter()
for i in range(0, len(data)-6):
    if data[i:i+2] == b'\xff\x15':
        slot = struct.unpack_from('<I', data, i+2)[0]
        c[slot] += 1
print('distinct slots', len(c), 'total ff15', sum(c.values()))
print('slots in 0x00ca8xxx:', sum(n for s,n in c.items() if 0xca8000 <= s < 0xca9000))
print('top slots:')
for slot, n in c.most_common(15):
    print('   %08x x%d' % (slot, n))
# slot 0xca8000..0xca9000 lives in which section (virtual only?)
for s in pe.sections:
    if s.VirtualAddress <= 0xca8000 < s.VirtualAddress + s.Misc_VirtualSize:
        print('0xca8000 in section', s.Name, 'raw', hex(s.SizeOfRawData), 'virt', hex(s.Misc_VirtualSize), 'X', bool(s.Characteristics & 0x20000000))
