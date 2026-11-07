d=open(r"run_codol_001\sandbox_ifs1_20260923\GDPLoader.dll","rb").read() if __import__("os").path.isfile(r"run_codol_001\sandbox_ifs1_20260923\GDPLoader.dll") else b""
if d:
    i=d.find(b"tqos.gamesafe.qq.com")
    print("   tqos.gamesafe.qq.com @ file 0x%06X"%i)
    j=d.find(b"183.60.58.99")
    print("   183.60.58.99 @ file 0x%06X"%j)
    print("   size", len(d))
