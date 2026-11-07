from pathlib import Path
import pefile
p=pefile.PE(r'COD OL/TCLS/Client.exe',fast_load=True)
for s in p.sections:
    if s.VirtualAddress<=0x1f000 and 0x1f000<s.VirtualAddress+min(s.Misc_VirtualSize,s.SizeOfRawData):
        b=s.get_data(); base=0x400000+s.VirtualAddress; break
lo=0x41f400-base; hi=0x41f700-base
# print dwords and strings in range
import struct
for off in range(lo,hi,4):
    va=base+off; x=int.from_bytes(b[off:off+4],'little'); c=b[off:off+80].split(b'\0')[0]
    if all(32<=q<127 or q in (9,10,13) for q in c) and c:
        print(hex(va),hex(x),repr(c))

