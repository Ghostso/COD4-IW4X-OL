from pathlib import Path
import sys, re, pefile
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
root = Path(r'D:\BaiduNetdiskDownload\使命召唤OL')
rel = r'COD OL\codoMP_client_shipRetailBase.dll'
p = root / rel
b = p.read_bytes()
pe = pefile.PE(str(p), fast_load=True)
for off in [0x122be3a, 0x12b0858]:
    print('===', hex(off), 'RVA', hex(pe.get_rva_from_offset(off)))
    lo=max(0,off-256); hi=min(len(b),off+768)
    blob=b[lo:hi]
    print('ASCII:', repr(blob.decode('latin1','replace')))
    print('UTF16:', repr(blob.decode('utf-16le','replace')))
