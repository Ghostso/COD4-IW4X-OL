import hashlib
import json
import time
from pathlib import Path

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
COD = ROOT / "COD OL"
TOOLS = ROOT / "工具"
EXP3 = TOOLS / "EXPERIMENT_003_DIR"
EXP4 = TOOLS / "EXPERIMENT_004_DIR"

ORIG = COD / "codoMP_client_shipRetailBase.dll"
EXP3_BIN = EXP3 / "codoMP_client_shipRetailBase.dll"
EXP4_BIN = EXP4 / "codoMP_client_shipRetailBase.dll"

PATCH4_RAW = 0x230D  # Base RVA 0x2F0D
PATCH4_ORIG = bytes.fromhex("c746180f000000")
PATCH4_NEW = bytes.fromhex("90909090909090")


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


orig = ORIG.read_bytes()
exp3 = EXP3_BIN.read_bytes()
exp4 = EXP4_BIN.read_bytes()

assert orig[PATCH4_RAW : PATCH4_RAW + 7] == PATCH4_ORIG, "EX-004 original mismatch"
assert exp3[PATCH4_RAW : PATCH4_RAW + 7] == PATCH4_ORIG, "EX-003 target mismatch"
assert exp4[PATCH4_RAW : PATCH4_RAW + 7] == PATCH4_ORIG, "EX-004 target mismatch"

patched = bytearray(exp4)
patched[PATCH4_RAW : PATCH4_RAW + 7] = PATCH4_NEW
EXP4_BIN.write_bytes(patched)

manifest = {
    "experiment": "EX-004",
    "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "note": "EXPERIMENTAL CONTROL FLOW: single RVA neutralization at Base+0x2F0D to reveal the next real execution node.",
    "inherited_experiment": "EX-003",
    "original_untouched": {
        "exe": sha256(COD / "codoMP_client_shipRetail.exe"),
        "base_dll": sha256(ORIG),
        "tenproxy_dll": sha256(COD / "TenProxy.dll"),
    },
    "ex003_base_sha256": sha256(EXP3_BIN),
    "ex004_base_sha256": sha256(EXP4_BIN),
    "patches": [
        {"id": "EX-001", "rva": "0x27E40C", "original_bytes": "ff15f422b010", "modified_bytes": "b80100000090"},
        {"id": "EX-002", "rva": "0x2928AC", "original_bytes": "832700", "modified_bytes": "909090"},
        {"id": "EX-003", "rva": "0x288C0A", "original_bytes": "e844f7ffff", "modified_bytes": "9090909090"},
        {
            "id": "EX-004",
            "rva": "0x2F0D",
            "raw_offset": "0x230D",
            "original_bytes": PATCH4_ORIG.hex(),
            "modified_bytes": PATCH4_NEW.hex(),
            "reason": "single-point neutralization of [esi+18h]=0Fh with esi=3 to observe next node",
        },
    ],
}

(TOOLS / "EXPERIMENT_004_MANIFEST.json").write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
)
(EXP4 / "EXPERIMENTAL_CONTROL_FLOW.txt").write_text(
    "EX-004 experimental Base DLL. Original files are never modified.\n", encoding="ascii"
)

print(json.dumps(manifest, indent=2, ensure_ascii=False))
