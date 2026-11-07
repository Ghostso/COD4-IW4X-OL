import pickle, hashlib
base = r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Server\lobby"
obj = pickle.load(open(base + r"\session_desc.pickle","rb"))
sk = open(base + r"\securitykey.bin","rb").read()
f19 = obj[19][1]
print("field19 inner type:", type(f19).__name__, "len:", len(f19))
print("field19 == securitykey.bin (bytes):", bytes(f19) == sk)
for name, fn in (("sha1",hashlib.sha1),("md5",hashlib.md5),("sha256",hashlib.sha256)):
    print(name, "field19:", fn(bytes(f19)).hexdigest(), " securitykey.bin:", fn(sk).hexdigest())
print("field0 blob len:", len(obj[0][1]))
print("field21 blob len:", len(obj[21][1]))
print("field23 (crc32 combat):", obj[23][1], "field24 (crc32 map):", obj[24][1])
import zlib
print("crc32('combat'):", zlib.crc32(b'combat'), " crc32('mp_crash_tropical'):", zlib.crc32(b'mp_crash_tropical'))
