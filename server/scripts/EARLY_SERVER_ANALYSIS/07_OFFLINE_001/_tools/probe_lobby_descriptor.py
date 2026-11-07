import pickle, hashlib
base = r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\lobby"
with open(base + r"\session_desc.pickle","rb") as f:
    obj = pickle.load(f)
print("type:", type(obj).__name__, "len:", len(obj))
for i,e in enumerate(obj):
    if isinstance(e,(bytes,bytearray)):
        print(i, "BLOB", len(e), hashlib.sha1(e).hexdigest().upper())
    elif isinstance(e,tuple):
        print(i, "TUPLE", [ (len(x), hashlib.sha1(x).hexdigest().upper()) if isinstance(x,(bytes,bytearray)) else x for x in e])
    else:
        print(i, type(e).__name__, repr(e))
with open(base + r"\securitykey.bin","rb") as f:
    sk = f.read()
print("securitykey.bin len:", len(sk), "sha1:", hashlib.sha1(sk).hexdigest().upper())
for i,e in enumerate(obj):
    if isinstance(e,(bytes,bytearray)) and len(e)==16:
        print("16B field at index", i, "== securitykey.bin:", bytes(e)==sk)
