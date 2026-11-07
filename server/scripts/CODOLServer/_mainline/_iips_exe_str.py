import re
d=open(r"COD OL\codoMP_client_shipRetail.exe","rb").read()
print("=== exe 里所有 IIPS 相关字符串（含 API 名/dvar/ini） ===")
for m in re.finditer(rb"[\x20-\x7e]{4,}", d):
    s=m.group().decode("latin1")
    if any(k in s for k in ("iips","IIPS","IFS","ifs_")) and len(s)<120:
        print("  off 0x%06X %r"%(m.start(), s))
