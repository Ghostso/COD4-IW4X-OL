import re
d = open(r'E:\codol_re\client_image_20261027.bin', 'rb').read()
VA = 0x400000
# find printable strings containing 'port' (length 4..40)
res = []
for m in re.finditer(rb'[ -~]{3,40}', d):
    s = m.group()
    if b'port' in s.lower() or b'Port' in s:
        res.append((VA + m.start(), s.decode('latin1')))
seen = set()
for va, s in res:
    if s in seen:
        continue
    seen.add(s)
    print(hex(va), repr(s))
print('total unique', len(seen))
