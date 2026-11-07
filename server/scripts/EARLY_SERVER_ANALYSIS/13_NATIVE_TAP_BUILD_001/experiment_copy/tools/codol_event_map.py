"""Verify/generate event-ID facts against the user's C1.exe 1.1.1.13 image."""
import argparse
from pathlib import Path
import re
import struct

parser = argparse.ArgumentParser()
parser.add_argument('client', type=Path)
parser.add_argument('--write', action='store_true')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
data = args.client.read_bytes()
u16 = lambda p: struct.unpack_from('<H', data, p)[0]
u32 = lambda p: struct.unpack_from('<I', data, p)[0]
pe = u32(60); opt = pe+24; base = u32(opt+28); sections = opt+u16(pe+20)
assert data[pe:pe+4] == b'PE\0\0' and u16(opt) == 0x10b

def offset(va):
    rva = va-base
    for i in range(u16(pe+6)):
        p = sections+40*i; start = u32(p+12)
        if start <= rva < start+u32(p+16):
            return u32(p+20)+rva-start
    raise ValueError(f'Unmapped address {va:#x}')

target = {}
for i in range(187):
    p = offset(u32(offset(0xCD81D8)+4*i))
    name = data[p:data.index(0, p)].decode('ascii')
    assert name.startswith('EV_') and name not in target
    target[name] = i
assert target['EV_FIRE_WEAPON'] == 30 and target['EV_OBITUARY'] == 107 and target['EV_DTP_LAND'] == 186
enum = (root/'src/bg.h').read_text().split('typedef enum BGEvent')[1].split('}BGEvent')[0]
names = re.findall(r'\bEV_[A-Z0-9_]+\b', enum)
lines = ['/* Exact name matches: IW3 bg.h -> C1.exe event names at VA 0xCD81D8.',
         ' * Generated/verified by tools/codol_event_map.py. Unmatched names remain unsupported. */']
unmapped = []
for name in names:
    if name in target:
        lines.append(f'    case {name}: return {target[name]};')
    else:
        unmapped.append(name)
content = '\n'.join(lines)+'\n'
path = root/'src/codol/snapshot/codol_event_map.inc'
if args.write:
    path.write_text(content)
else:
    assert path.read_text() == content, 'Event map differs from installed client'
print(f'PASS: {len(names)-len(unmapped)} exact-name mappings; unsupported: {", ".join(unmapped)}')
