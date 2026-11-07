import hashlib
d=open(r"run_codol_001\sandbox_ifs1_20260923\GDPLoader.dll","rb").read()
print("sha256:", hashlib.sha256(d).hexdigest()[:16])
print("tqos.gamesafe.qq.com 出现次数:", d.count(b"tqos.gamesafe.qq.com"))
print("183.60.58.99 出现次数:", d.count(b"183.60.58.99"))
