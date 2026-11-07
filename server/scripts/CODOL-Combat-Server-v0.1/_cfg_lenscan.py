import io
p="config/firingrange_live.cfg"
s=io.open(p,encoding="utf-8").read()
if "snap_pad" not in s:
    s += "\n# [LEN-SCAN 2026-10-16] 快照体长度扫描: 0 -> 400B, 每 25 帧 +32B\nsnap_pad = 0\nsnap_pad_step = 32\nsnap_pad_every = 25\nsnap_pad_max = 400\n"
io.open(p,"w",encoding="utf-8",newline="\n").write(s)
print("cfg updated")
