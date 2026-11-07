import sys
sys.stdout.reconfigure(encoding="utf-8",errors="replace")
E=r"E:\codol_re\client_image_20261027.bin";VA=0x400000
d=open(E,"rb").read()
for va in [0x6336F0,0x6336EE,0x63371F,0x633757,0x62ADB1,0x62C2D1,0x63350C]:
    o=va-VA
    print(hex(va), o, d[o:o+32].hex())
