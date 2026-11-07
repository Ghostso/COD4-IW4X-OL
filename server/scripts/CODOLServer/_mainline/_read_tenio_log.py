import os

paths = [
    r"COD OL\IIPS\TPFUI\NewTenioLog.txt",
    r"COD OL\IIPS\IIPSVersion.ini",
    r"COD OL\IIPS\IIPSClient.ini",
]

for rel in paths:
    print("===== %s =====" % rel)
    if not os.path.exists(rel):
        print("MISSING")
        continue
    blob = open(rel, "rb").read()
    for enc in ("utf-8", "gbk", "utf-16"):
        try:
            text = blob.decode(enc)
            print("(decoded as %s)" % enc)
            lines = text.splitlines()
            print("lines=%d" % len(lines))
            for line in lines[:120]:
                print(line)
            break
        except UnicodeDecodeError:
            continue
    else:
        print("(undecodable) %r" % blob[:80])
    print()
