import pefile, os
for p in [r"run_codol_001\sandbox_ifs1_20260923\codoMP_client_shipRetail.exe",
          r"run_codol_001\sandbox_ifs1_20260923\codoMP_client_shipRetailBase.dll"]:
    if not os.path.isfile(p): print("MISS",p); continue
    pe=pefile.PE(p, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
    print("=== %s ==="%os.path.basename(p))
    if hasattr(pe,"DIRECTORY_ENTRY_IMPORT"):
        for imp in pe.DIRECTORY_ENTRY_IMPORT:
            print("   %s"%imp.dll.decode())
    else: print("   (无导入表)")
print()
# 沙箱里有没有 .local 重定向目录
print("=== 沙箱 目录 ===")
for d in os.listdir(r"run_codol_001\sandbox_ifs1_20260923"):
    fp=os.path.join(r"run_codol_001\sandbox_ifs1_20260923",d)
    if os.path.isdir(fp) and (d.endswith(".local") or ".local" in d): print("   LOCAL:",d)
print()
# 谁导入 GDPLoader
import glob
for p in glob.glob(r"COD OL\*.dll")+glob.glob(r"COD OL\*.exe")+glob.glob(r"run_codol_001\sandbox_ifs1_20260923\*.dll"):
    try:
        d=open(p,"rb").read()
        if b"GDPLoader" in d or b"GDPLoader.dll".encode("utf-16-le") in d:
            print("   含 GDPLoader 串:", p)
    except: pass
