import struct, re, collections, math
p=r"D:\BaiduNetdiskDownload\使命召唤OL\E06_TVM0_STATIC_DECODE_001\_work\lasttp3_blocks.bin"
d=open(p,"rb").read()
print("=== recovered last-.tp3 content: 0x%X (%d) bytes ===" % (len(d),len(d)))
# structure: look for the 4-byte prefix pattern B1CAB4BA style -> these are 'value CRC' headers
print("\n--- first 96 bytes ---")
print(d[:96].hex(" "))
print("\n--- does it contain AP32/PE/MZ/text markers? ---")
for tok in (b"AP32", b"MZ", b"PE\x00\x00", b".text", b".rdata", b".data"):
    print("  %-8r : %d" % (tok, d.count(tok)))
print("\n--- ASCII strings >= 8 ---")
ss=re.findall(rb"[\x20-\x7e]{8,}", d)
print("  count=%d" % len(ss))
for s in ss[:30]: print("   ", s[:100])