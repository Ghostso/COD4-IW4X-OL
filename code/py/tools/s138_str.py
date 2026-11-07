import sys
d = open(r'E:\codol_re\client_image_20261027.bin', 'rb').read()
VA = 0x400000
for a in sys.argv[1:]:
    off = int(a, 0) - VA
    end = d.find(b'\x00', off)
    print('== 0x%08X ==' % int(a, 0))
    print(repr(d[off:end]))
    print()
