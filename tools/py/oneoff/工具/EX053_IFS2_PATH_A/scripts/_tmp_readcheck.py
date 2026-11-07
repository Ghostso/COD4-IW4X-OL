from pathlib import Path
r=Path('codoMP_client_shipRetail.exe').read_bytes()
print(len(r), r[:4].hex(), r[0x3c:0x40].hex())
