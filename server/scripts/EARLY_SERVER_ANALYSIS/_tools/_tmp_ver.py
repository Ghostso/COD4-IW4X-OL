import pefile
def ver(p):
    pe=pefile.PE(p,fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]])
    v={}
    try:
        for fi in getattr(pe,"FileInfo",[]) or []:
            for entry in (fi if isinstance(fi,list) else [fi]):
                if getattr(entry,"Key",b"")==b"StringFileInfo":
                    for st in entry.StringTable:
                        for k,val in st.entries.items(): v[k.decode("latin-1")]=val.decode("latin-1")
    except Exception as e: v["err"]=str(e)
    print(p.split("\\")[-1])
    print("   FileVersion=",v.get("FileVersion")," ProductVersion=",v.get("ProductVersion"))
    print("   Company=",v.get("CompanyName")," ProductName=",v.get("ProductName"))
    print("   EP=",hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint)," IB=",hex(pe.OPTIONAL_HEADER.ImageBase),
          " ts=",pe.FILE_HEADER.TimeDateStamp, " linker=%d.%d"%(pe.OPTIONAL_HEADER.MajorLinkerVersion,pe.OPTIONAL_HEADER.MinorLinkerVersion))
for p in [r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\codoMP_client_shipRetail.exe",
          r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe",
          r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll"]:
    ver(p)
