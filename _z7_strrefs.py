import struct
d=open(r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin","rb").read()
base=0x400000
for va in (0xde0610,0xde0624,0xde0640):
    off=va-base
    print(hex(va), repr(d[off:off+48]))
for va in (0xde0610,0xde0624,0xde0640):
    pat=struct.pack("<I",va)
    print(hex(va),"refs:",[hex(base+i) for i in range(len(d)-4) if d[i:i+4]==pat])
