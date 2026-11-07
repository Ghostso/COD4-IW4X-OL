import os, hashlib, pefile
pairs = [
 ("EARLY exe", r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe"),
 ("CUR exe", r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe"),
 ("CUR base", r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll"),
]
for label, p in pairs:
    if not os.path.exists(p):
        print(label, "MISSING", p); continue
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1<<20), b''): h.update(chunk)
    try:
        pe = pefile.PE(p, fast_load=True)
        ib = hex(pe.OPTIONAL_HEADER.ImageBase); ep = hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint)
        ts = pe.FILE_HEADER.TimeDateStamp
        import datetime; tsu = datetime.datetime.utcfromtimestamp(ts).isoformat()+"Z"
        pe.close()
    except Exception as e:
        ib=ep=tsu=str(e)
    print(f"{label}|{os.path.getsize(p)}|{h.hexdigest()}|IB={ib}|EP={ep}|ts={tsu}")
