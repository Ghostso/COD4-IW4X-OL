import hashlib, struct
p = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d = open(p,'rb').read()
BASE=0x400000
def g(va,n): 
    o=va-BASE
    return d[o:o+n]
def hexs(b): return " ".join("%02x"%x for x in b)
print("=== string anchors (ASCII) ===")
for va,label,n in [
  (0xDC6800,"mmstart fmt",48),
  (0xDC6704,"MM_RESERVE_CMD_REQUEST",32),
  (0xDC6724,"mmbook",16),
  (0xDC69B0,"mmbook accepted",32),
  (0xDC69D4,"mmbook timedout",32),
  (0xDC6930,"start_map_rotate_once",32),
  (0xDC6914,"2634 1; start_map_rotate",32),
]:
    b=g(va,n)
    print("%08X %-24s %r" % (va,label,b.split(b'\x00')[0]))
print()
print("=== code bytes at anchors ===")
for va,label in [(0x632070,"mmstart ctor"),(0x632680,"accepted parser"),(0x634402,"latch consumer"),(0x634340,"latch reader?")]:
    print("%08X %-20s %s" % (va,label,hexs(g(va,24))))
print()
# check ret imm16 near end of 0x632680
print("=== around 0x632680 ret ===")
print(hexs(g(0x632680,0x100))[:400])
