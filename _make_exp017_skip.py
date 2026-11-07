import hashlib, json, time
from pathlib import Path

root = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
src = root / "COD OL" / "codoMP_client_shipRetail.exe"
dst = root / "工具" / "EXPERIMENT_017_BOOT_SKIP" / "codoMP_client_shipRetail.exe"

RVA = 0xE5DC690
FILE_OFF = 0x776690
ORIG = bytes.fromhex("ff1565c69d0e")
MODIFIED = bytes.fromhex("b800000000c3")  # mov eax,0; ret

orig_bin = Path(src).read_bytes()
if orig_bin[FILE_OFF:FILE_OFF + len(ORIG)] != ORIG:
    raise ValueError("entry bytes mismatch")
data = bytearray(orig_bin)
data[FILE_OFF:FILE_OFF + len(MODIFIED)] = MODIFIED
Path(dst).write_bytes(data)

h = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
record = {
    "experiment": "EX-017-EXEC-SKIP",
    "rva": hex(RVA),
    "file_offset": hex(FILE_OFF),
    "original": ORIG.hex(),
    "modified": MODIFIED.hex(),
    "original_exe_sha256": h(src),
    "modified_exe_sha256": h(dst),
}
(root / "工具" / "EXPERIMENT_017_BOOT_SKIP_MANIFEST.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
print(json.dumps(record, indent=2))
