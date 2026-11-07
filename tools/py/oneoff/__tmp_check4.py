from pathlib import Path
p=Path('COD OL/codoMP_client_shipRetail.exe')
data=p.read_bytes()
off=7824949
for i in range(80):
    b=data[off+i]
    print(f'{i:02x} {b:02x} {chr(b) if 32 <= b < 127 else "."}')
