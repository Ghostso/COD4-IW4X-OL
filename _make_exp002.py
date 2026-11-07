import hashlib
import json
import time
from pathlib import Path

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
COD = ROOT / "COD OL"
TOOLS = ROOT / "工具"
EXP1 = TOOLS / "EXPERIMENT_DIR"
EXP2 = TOOLS / "EXPERIMENT_002_DIR"

ORIG = COD / "codoMP_client_shipRetailBase.dll"
EXP1_BIN = EXP1 / "codoMP_client_shipRetailBase.dll"
EXP2_BIN = EXP2 / "codoMP_client_shipRetailBase.dll"

PATCH1_RAW = 0x27D80C  # Base RVA 0x27E40C
PATCH2_RAW = 0x291CAC  # Base RVA 0x2928AC
PATCH1_ORIG = bytes.fromhex("ff15f422b010")
PATCH1_NEW = bytes.fromhex("b80100000090")
PATCH2_ORIG = bytes.fromhex("832700")
PATCH2_NEW = bytes.fromhex("909090")


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


orig = ORIG.read_bytes()
exp1 = EXP1_BIN.read_bytes()
exp2 = EXP2_BIN.read_bytes()

assert orig[PATCH1_RAW : PATCH1_RAW + 6] == PATCH1_ORIG, "EX-001 original mismatch"
assert exp1[PATCH1_RAW : PATCH1_RAW + 6] == PATCH1_NEW, "EX-001 patch missing"
assert exp2[PATCH1_RAW : PATCH1_RAW + 6] == PATCH1_NEW, "EX-002 must inherit EX-001"
assert exp2[PATCH2_RAW : PATCH2_RAW + 3] == PATCH2_ORIG, "EX-002 target mismatch"

patched = bytearray(exp2)
patched[PATCH2_RAW : PATCH2_RAW + 3] = PATCH2_NEW
EXP2_BIN.write_bytes(patched)

manifest = {
    "experiment": "EX-002",
    "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "note": "EXPERIMENTAL CONTROL FLOW: continue Base bootstrap past invalid-free and null-write nodes only to observe the next real state.",
    "original_untouched": {
        "exe": sha256(COD / "codoMP_client_shipRetail.exe"),
        "base_dll": sha256(ORIG),
        "tenproxy_dll": sha256(COD / "TenProxy.dll"),
    },
    "inherited_experiment": "EX-001",
    "ex001_base_sha256": sha256(EXP1_BIN),
    "ex002_base_sha256": sha256(EXP2_BIN),
    "patches": [
        {
            "id": "EX-001",
            "module": "codoMP_client_shipRetailBase.dll",
            "rva": "0x27E40C",
            "raw_offset": "0x27D80C",
            "original_bytes": PATCH1_ORIG.hex(),
            "modified_bytes": PATCH1_NEW.hex(),
            "reason": "skip RtlFreeHeap(0x404000) invalid-free call in free wrapper",
        },
        {
            "id": "EX-002",
            "module": "codoMP_client_shipRetailBase.dll",
            "rva": "0x2928AC",
            "raw_offset": "0x291CAC",
            "original_bytes": PATCH2_ORIG.hex(),
            "modified_bytes": PATCH2_NEW.hex(),
            "reason": "neutralize null-write at config string parser terminator to observe next bootstrap edge",
        },
    ],
}

(TOOLS / "EXPERIMENT_002_MANIFEST.json").write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
)
(EXP2 / "EXPERIMENTAL_CONTROL_FLOW.txt").write_text(
    "EX-002 experimental Base DLL. Original files are never modified.\n", encoding="ascii"
)

print(json.dumps(manifest, indent=2, ensure_ascii=False))
