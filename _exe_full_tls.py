import sys
import struct
from pathlib import Path
import pefile

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

p = Path(r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe")
pe = pefile.PE(str(p), fast_load=False)
ib = pe.OPTIONAL_HEADER.ImageBase
tls = pe.DIRECTORY_ENTRY_TLS.struct

print("TLS StartAddressOfRawData", hex(tls.StartAddressOfRawData))
print("TLS EndAddressOfRawData", hex(tls.EndAddressOfRawData))
print("TLS AddressOfIndex", hex(tls.AddressOfIndex))
print("TLS AddressOfCallBacks", hex(tls.AddressOfCallBacks))

back_rva = tls.AddressOfCallBacks - ib
back_off = pe.get_offset_from_rva(back_rva)
print("callback_dir_rva", hex(back_rva), "off", hex(back_off))

arr = []
for i in range(32):
    va = struct.unpack_from("<I", pe.__data__, back_off + i * 4)[0]
    if va == 0:
        break
    arr.append(va)
print("callback count", len(arr))
for va in arr:
    rva = va - ib
    sec = pe.get_section_by_rva(rva)
    print(hex(va), hex(rva), sec.Name.rstrip(b"\x00").decode("latin1") if sec else None)
    off = pe.get_offset_from_rva(rva)
    print("  bytes", pe.__data__[off : off + 16].hex())
