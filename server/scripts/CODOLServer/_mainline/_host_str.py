import re
for f in [r"COD OL\IIPS\IIPSHost.dll", r"COD OL\IIPS\IIPSHostApp.exe"]:
    d=open(f,"rb").read()
    print("="*70); print(f, len(d))
    for m in re.finditer(rb"[\x20-\x7e]{5,}", d):
        s=m.group().decode("latin1")
        if any(k in s for k in ("Pipe","pipe","HostPid","ShareState","Global\\\\","iipslaunch","IIPSHostApp",
                                "CreateNamedPipe","ConnectNamedPipe","Listen","listen","MMF","Mutex","mode",
                                "\\\\.\\","cmd","CMD")):
            print("  +0x%06X %r"%(m.start(), s[:130]))
