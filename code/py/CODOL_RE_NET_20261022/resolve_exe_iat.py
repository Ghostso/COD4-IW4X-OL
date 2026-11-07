import struct, pefile
d = open(r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin','rb').read()
B = 0x400000
ws = pefile.PE(r'C:\Windows\SysWOW64\ws2_32.dll')
wsex = {}
for s in ws.DIRECTORY_ENTRY_EXPORT.symbols:
    if s.name: wsex[s.address] = s.name.decode()
try:
    wh = pefile.PE(r'C:\Windows\SysWOW64\winhttp.dll')
    whex = {}
    for s in wh.DIRECTORY_ENTRY_EXPORT.symbols:
        if s.name: whex[s.address] = s.name.decode()
    whbase = 0x72E60000
except Exception as e:
    whex = {}; whbase = 0
slot_names = {}
lo, hi = 0xCA8240, 0xCB2000
for slot in range(lo, hi, 4):
    v = struct.unpack_from('<I', d, slot-B)[0]
    if 0x779A0000 <= v < 0x779E0000:
        slot_names[slot] = 'ws2_32!' + wsex.get(v-0x779A0000, '?%x' % (v-0x779A0000))
    elif whbase and whbase <= v < whbase+0x100000:
        slot_names[slot] = 'winhttp!' + whex.get(v-whbase, '?%x' % (v-whbase))
print('resolved slots:', len(slot_names))
import collections
byapi = collections.defaultdict(list)
for slot, nm in sorted(slot_names.items()):
    byapi[nm.split('!')[1]].append(slot)
for nm in sorted(byapi):
    print('%-28s %s' % (nm, ' '.join('%#x' % s for s in byapi[nm])))
