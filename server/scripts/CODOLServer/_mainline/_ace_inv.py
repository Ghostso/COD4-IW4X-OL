import pefile, os, hashlib

def sig_state(p):
    # minimal Authenticode presence check
    try:
        pe=pefile.PE(p, fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_SECURITY"]])
        d=pe.OPTIONAL_HEADER.DATA_DIRECTORY[5]
        return ("SIGNED(%d)"%d.Size) if d.Size else "UNSIGNED"
    except Exception as e:
        return "ERR"

def info(p):
    try:
        pe=pefile.PE(p, fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
                                               pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
    except Exception as e:
        return {"path":p,"err":str(e)}
    d={"path":p,"size":os.path.getsize(p),"ib":hex(pe.OPTIONAL_HEADER.ImageBase),
       "machine":hex(pe.FILE_HEADER.Machine),"dll":pe.FILE_HEADER.Characteristics&0x2000!=0,
       "imports":[], "exports":[], "sig":sig_state(p)}
    if hasattr(pe,"DIRECTORY_ENTRY_IMPORT"):
        for imp in pe.DIRECTORY_ENTRY_IMPORT:
            d["imports"].append((imp.dll.decode(), len(imp.imports)))
    if hasattr(pe,"DIRECTORY_ENTRY_EXPORT"):
        e=pe.DIRECTORY_ENTRY_EXPORT
        d["exports"]=[(s.ordinal, hex(s.address), (s.name.decode() if s.name else "")) for s in e.symbols]
    return d

files=[]
for root in [r"C:\Program Files\AntiCheatExpert"]:
    for dp,_,fns in os.walk(root):
        for fn in fns:
            if fn.lower().endswith((".sys",".dll",".exe")):
                files.append(os.path.join(dp,fn))
for fn in ["ace-ats32.dll","ACE-DRV32.dll","PolicyProbe.dll","TCJ.dll","TerSafe.dll","TenSLX.dll","TenSp.dll","TenProxy.dll","ProtocalHandler.dll","GbSpy.dll","tvsd.dll","VSDDrvDll.dll","BugTrace.dll","GBSpy.dll"]:
    p=os.path.join(r"COD OL",fn)
    if os.path.isfile(p): files.append(p)

for p in sorted(files):
    d=info(p)
    if "err" in d:
        print("== %s  ERR %s"%(os.path.basename(p), d["err"])); continue
    print("== %s  %d bytes  %s" % (os.path.basename(p), d["size"], d["sig"]))
    print("   IB=%s machine=%s dll=%s" % (d["ib"], d["machine"], d["dll"]))
    if d["exports"]:
        print("   EXPORTS(%d): %s" % (len(d["exports"]), ", ".join(("ord%s:%s"%(o,n or "(no name)")) for o,a,n in d["exports"][:12])))
    print("   IMPORTS: %s" % ", ".join("%s(%d)"%(n,c) for n,c in d["imports"][:14]))
