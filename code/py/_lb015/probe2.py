img = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d = open(img, "rb").read()
print("len", hex(len(d)), len(d))
print("first 64:", d[:64].hex())
try:
    import pefile
    pe = pefile.PE(data=d, fast_load=True)
    print("parsed as PE ImageBase", hex(pe.OPTIONAL_HEADER.ImageBase))
except Exception as e:
    print("not PE:", e)
