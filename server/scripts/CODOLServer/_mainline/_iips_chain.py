import re
d=open(r"COD OL\IIPS\iips.dll","rb").read()
# every ResourceManagerII / IIPSClient / pipe related string in order
for m in re.finditer(rb"[\x20-\x7e]{6,}", d):
    s=m.group().decode("latin1")
    if ("ResourceManagerII" in s or "IIPSClient" in s or "Pipe" in s or "\\\\\\\\." in s
        or "Global\\\\" in s or "IIPSERR" in s or "HostPid" in s or "ShareState" in s
        or "HOSTAPP" in s.upper() or "iipslaunch" in s or "Launch" in s):
        print("+0x%06X %r" % (m.start(), s[:150]))
