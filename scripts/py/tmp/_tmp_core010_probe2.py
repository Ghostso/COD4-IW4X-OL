from __future__ import annotations

"""Throwaway CORE-010 pre-check #2: exact instruction encodings at the tracked
file offsets, the -qa/-src=tgp/WIN_NO_TCLS token region, and the STUN endpoint
source. Read-only."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXE = ROOT / "COD OL" / "codoMP_client_shipRetail.exe"
blob = EXE.read_bytes()

sites = {
    "0x0849413B write? A": 0x00239C68,
    "0x0849413B read B": 0x0016FF08,
    "0x0849413B read C": 0x0017FF46,
    "0x0849413B read D": 0x0028E1A4,
    "0x0849413B extra 5th": 0x0021CCA4,
    "0x0849B501 read": 0x002835BA,
    "argv_count 0x0196928C site1": 0x00239C23,
    "argv_count 0x0196928C site2": 0x0056111A,
    "argv_array 0x01969290 site1": 0x00239C2F,
    "argv_array 0x01969290 site2": 0x00561120,
    "argv_array 0x01969290 site3": 0x0059376C,
    "provider 0x00CA827C call": 0x00561131,
}

for label, off in sites.items():
    start = max(0, off - 3)
    chunk = blob[start : off + 12]
    print(f"{label:<30} file_off={off:#010x}  bytes={chunk.hex(' ').upper()}")

print()
print("token region around -qa / -src=tgp / WIN_NO_TCLS:")
region = blob[7110440:7110620]
print(" ", region.decode("latin-1").replace("\x00", "."))

print()
print("endpoint search:")
for pat in [b"stun1-tub.codol.qq.com", b"stun.us.demonware.net", b"stun"]:
    idx = [m.start() for m in re.finditer(re.escape(pat), blob)]
    print(f"  {pat!r} in EXE: {len(idx)} hits {[hex(i) for i in idx[:5]]}")

blob = EXE.read_bytes()
