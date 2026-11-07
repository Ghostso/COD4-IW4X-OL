import re, os
# 1) 谁 import 了 iips.dll / IIPSHost.dll（静态导入）
import pefile
targets = ("iips.dll","IIPSHost.dll","IFS2.dll","IFS.dll","IIPSVFS.dll","iips_policymsg.dll","Download.dll","p2papp.dll")
roots = [r"COD OL", r"COD OL\TCLS", r"COD OL\tqm", r"COD OL\Cross", r"COD OL\components", r"COD OL\TCLS\TenProtect"]
found = {}
for r in roots:
    if not os.path.isdir(r): continue
    for dp,_,fns in os.walk(r):
        for fn in fns:
            if not fn.lower().endswith((".exe",".dll")): continue
            p=os.path.join(dp,fn)
            try:
                pe=pefile.PE(p, fast_load=True)
                pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
            except Exception: continue
            if not hasattr(pe,"DIRECTORY_ENTRY_IMPORT"): continue
            for imp in pe.DIRECTORY_ENTRY_IMPORT:
                nm=imp.dll.decode("latin1").lower()
                if nm in targets:
                    found.setdefault(nm, []).append((p, [ (f.name.decode() if f.name else "ord_%s"%f.ordinal) for f in imp.imports ][:12]))
for k in sorted(found):
    print("### %s  <- 被 %d 个模块导入"%(k, len(found[k])))
    for p,fl in found[k]:
        print("   ", p)
        print("        ", fl)
