# -*- coding: utf-8 -*-
"""TASK-035: exact OOB literal bytes + surrounding literals (target image)."""
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
def dump(va,label):
    o=va-BASE
    e=d.find(b'\x00',o)
    raw=d[o:e]
    print("  %-22s VA=%08X off=%08X len=%2d  hex=%s  ascii=%r" % (label,va,o,len(raw),raw.hex(),raw.decode('latin1')))
print("== exact OOB literals (no NUL included) ==")
for va,lab in [(0xDBFD04,"getchallenge fmt"),(0xDBFE40,"heartbeat"),(0xDBFEE8,"challengeResponse"),
               (0xDBFF0C,"connectResponse"),(0xDBFC8C,"cancelConnect"),(0xDC5694,"connect"),
               (0xDBFFB4,"userinfo fmt"),(0xDB4700,"gamestateupdate fmt"),(0xDBFE38,"stats-related")]:
    dump(va,lab)
print()
print("== neighbourhood around 0xDBFE00..0xDBFF40 (command vocabulary) ==")
o=0xDBFE00-BASE
p=o; end=0xDBFF60-BASE
while p<end:
    n=d.find(b'\x00',p)
    if n<0 or n>end: break
    if n>p:
        raw=d[p:n]
        if all(32<=c<127 for c in raw):
            print("   VA %08X  %r" % (p+BASE, raw.decode()))
    p=n+1
