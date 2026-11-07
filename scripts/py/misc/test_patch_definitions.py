import sys, os
sys.path.insert(0, r"D:\BaiduNetdiskDownload\使命召唤OL\_combat_next001")
from peimg import PE

pe = PE.load()

# Let's verify each patch address and its original bytes
tests = [
    ("Gate1 (0x632695)", 0x632695, bytes.fromhex("0f8450020000")),
    ("Gate3 (0x6326B0)", 0x6326B0, bytes.fromhex("0f8c37020000")),
    ("Gate4 (0x6326BF)", 0x6326BF, bytes.fromhex("0f8551020000")),
    ("Gate5 (0x6326CE)", 0x6326CE, bytes.fromhex("0f8542020000")),
    ("SlotMismatch (0x632705)", 0x632705, bytes.fromhex("750b")),
    ("SlotMatchJmp (0x632710)", 0x632710, bytes.fromhex("7424")),
    ("BridgeSkip (0x632822)", 0x632822, bytes.fromhex("7540")),
]

for name, va, want in tests:
    got = pe.read(va, len(want))
    ok = (got == want)
    print(f"{name:25}: want={want.hex()} got={got.hex()} -> {'PASS' if ok else 'FAIL'}")
    assert ok, f"{name} byte mismatch"

print("\nALL 7 PATCH LOCATIONS AND ORIGINAL BYTES 100% VERIFIED!")
