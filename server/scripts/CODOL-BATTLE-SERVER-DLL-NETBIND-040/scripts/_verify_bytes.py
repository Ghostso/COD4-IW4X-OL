import pefile,struct
DLL=r"D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll"
b=open(DLL,'rb').read();pe=pefile.PE(data=b,fast_load=False)
def rva2off(r):
    for s in pe.sections:
        if s.VirtualAddress<=r<s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):return s.PointerToRawData+(r-s.VirtualAddress)
    return None
checks=[
 ("0x235D6D","ff15602ab010"),("0x235D4F","ff156c2ab010"),("0x235D81","ff15682ab010"),
 ("0x235EC9","ff154c2ab010"),("0x235F23","ff15702ab010"),("0x235F4C","ff15642ab010"),
 ("0x235F7E","ff15482ab010"),("0x235F84","8bf8"),("0x235F86","83ffff"),
 ("0x235F94","8a8df4feffff"),("0x235FBB","3b5e08"),("0x236058","2b410c"),
 ("0x23606E","2bf8"),("0x236073","66891e"),("0x236079","894e0c"),
]
ok=True
for rva,exp in checks:
    o=rva2off(int(rva,16))
    got=b[o:o+len(exp)//2].hex()
    m = "OK " if got==exp else "MISMATCH"
    if got!=exp: ok=False
    print(f"  {m} {rva}: expected {exp} got {got}")
print("all match:",ok)
