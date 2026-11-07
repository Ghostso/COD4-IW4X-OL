import sys
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools")
import e_common as e
b = e.load_bin(e.SRV, e.DATA + r"\syms_NEW.json")
# cstrings
for va in (0x7c424c,0x7c429c,0x7c42a0,0x7c42e4,0x64b74,0x7d59c4,0x7d59ed,0x7d5a0c,0x7d5a3b,0x7d5a74,0x7d5b40):
    r=va-b.ib if va>=b.ib else va
    print("VA %08x (rva %x): %r"%(va, r, b.cstr(r)))
print()
print("#### _collect  RVA 0xa31f8")
e.show(b, 0xa31f8, end_rva=0xa3300)
