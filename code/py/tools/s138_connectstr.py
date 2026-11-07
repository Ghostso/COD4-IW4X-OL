import re
d = open(r'E:\codol_re\client_image_20261027.bin', 'rb').read()
VA = 0x400000
# look for printable strings that mention connect with a space or 'connect '
for m in re.finditer(rb'[ -~]{4,60}', d):
    s = m.group()
    if b'connect' in s.lower():
        print(hex(VA + m.start()), repr(s.decode('latin1')))
