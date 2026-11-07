import re
d=open(r"COD OL\IIPS\iips.dll","rb").read()
print("=== iips.dll: message/cmd/pipe/state 相关 ===")
for m in re.finditer(rb"[\x20-\x7e]{4,}", d):
    s=m.group().decode("latin1")
    if any(k in s for k in ("MSG_","CMD_","_CMD",".cmd","msg.cmd","iipsClient","IIPSMsg","IIPSHostAlive","HostAction","HOST_","ShareState","WND_","WM_")):
        print("+0x%06X %r" % (m.start(), s[:130]))
