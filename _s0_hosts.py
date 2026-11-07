import re
d=open(r"COD OL\codoMP_client_shipRetail.exe","rb").read()
h=open(r"COD OL\codoMP_client_shipRetailBase.dll","rb").read() if __import__("os").path.exists(r"COD OL\codoMP_client_shipRetailBase.dll") else b""
def find(buf,tag):
    for m in re.finditer(rb"[\x20-\x7e]{6,}", buf):
        s=m.group()
        if any(k in s for k in (b"qq.com",b"gamedl",b"iips",b"tcls",b"codol",b"tencent",b"lego",b"7.",b"master")):
            print("  %s +0x%06X %r"%(tag,m.start(),s))
print("=== EXE ===")
find(d,"exe")
print("=== Base.dll ===")
find(h,"base")
