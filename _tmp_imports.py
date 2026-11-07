import pefile
p=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe=pefile.PE(p)
print("DLLs:", [e.dll.decode() for e in pe.DIRECTORY_ENTRY_IMPORT])
for e in pe.DIRECTORY_ENTRY_IMPORT:
    names=[(i.name or b"").decode() for i in e.imports]
    print(e.dll.decode(), len(names))
    # crypto relevant
    for n in names:
        if any(k in n.lower() for k in ("crypt","hash","aes","sha","hmac","bcrypt","wintrust","advapi")):
            print("   *",n)
