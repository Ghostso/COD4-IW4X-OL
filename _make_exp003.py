import hashlib
import json
import time
from pathlib import Path

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
COD = ROOT / "COD OL"
TOOLS = ROOT / "工具"
EXP2 = TOOLS / "EXPERIMENT_002_DIR"
EXP3 = TOOLS / "EXPERIMENT_003_DIR"

ORIG = COD / "codoMP_client_shipRetailBase.dll"
EXP2_BIN = EXP2 / "codoMP_client_shipRetailBase.dll"
EXP3_BIN = EXP3 / "codoMP_client_shipRetailBase.dll"

PATCH3_RAW = 0x28800A  # Base RVA 0x288C0A
PATCH3_ORIG = bytes.fromhex("e844f7ffff")
PATCH3_NEW = bytes.fromhex("9090909090")


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


orig = ORIG.read_bytes()
exp2 = EXP2_BIN.read_bytes()
exp3 = EXP3_BIN.read_bytes()

assert orig[PATCH3_RAW : PATCH3_RAW + 5] == PATCH3_ORIG, "EX-003 original mismatch"
assert exp2[PATCH3_RAW : PATCH3_RAW + 5] == PATCH3_ORIG, "EX-002 target mismatch"
assert exp3[PATCH3_RAW : PATCH3_RAW + 5] == PATCH3_ORIG, "EX-003 target mismatch"

patched = bytearray(exp3)
patched[PATCH3_RAW : PATCH3_RAW + 5] = PATCH3_NEW
EXP3_BIN.write_bytes(patched)

manifest = {
    "experiment": "EX-003",
    "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "note": "EXPERIMENTAL CONTROL FLOW: continue Base bootstrap past the BAADF00D refcount decrement cleanup call to observe the next real state.",
    "inherited_experiment": "EX-002",
    "original_untouched": {
        "exe": sha256(COD / "codoMP_client_shipRetail.exe"),
        "base_dll": sha256(ORIG),
        "tenproxy_dll": sha256(COD / "TenProxy.dll"),
    },
    "ex002_base_sha256": sha256(EXP2_BIN),
    "ex003_base_sha256": sha256(EXP3_BIN),
    "patches": [
        {
            "id": "EX-001",
            "rva": "0x27E40C",
            "original_bytes": "ff15f422b010",
            "modified_bytes": "b80100000090",
        },
        {
            "id": "EX-002",
            "rva": "0x2928AC",
            "original_bytes": "832700",
            "modified_bytes": "909090",
        },
        {
            "id": "EX-003",
            "rva": "0x288C0A",
            "raw_offset": "0x28800A",
            "original_bytes": PATCH3_ORIG.hex(),
            "modified_bytes": PATCH3_NEW.hex(),
            "reason": "skip LC_ config cleanup call whose refcount is already BAADF00D",
        },
    ],
}

(TOOLS / "EXPERIMENT_003_MANIFEST.json").write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
)
(EXP3 / "EXPERIMENTAL_CONTROL_FLOW.txt").write_text(
    "EX-003 experimental Base DLL. Original files are never modified.\n", encoding="ascii"
)

print(json.dumps(manifest, indent=2, ensure_ascii=False))
