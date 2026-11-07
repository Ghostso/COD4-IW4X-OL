import sys, os, struct, importlib.util, collections, math
sys.path.insert(0, r"CODOLServer\_mainline")
spec = importlib.util.spec_from_file_location("ff", r"CODOLServer\_mainline\ff_iw4_decrypt.py")
ff = importlib.util.module_from_spec(spec); spec.loader.exec_module(ff)
p = ff.decrypt_file(r"COD OL\main\mp_playlists.ff")["plain"]

print("=== printable-run map: find every ASCII run >=4 in first 4096 bytes ===")
i=0
while i < min(len(p), 4096):
    j=i
    while j < len(p) and 32 <= p[j] < 127: j+=1
    if j-i >= 4:
        print("  @0x%04x (%5d) len=%2d  %r" % (i, i, j-i, p[i:j]))
    i = max(j, i+1)

print()
print("=== zero-run map in first 4096 ===")
i=0
while i < min(len(p), 4096):
    if p[i]==0:
        j=i
        while j < len(p) and p[j]==0: j+=1
        if j-i >= 4:
            print("  zeros @0x%04x (%5d) len=%d" % (i, i, j-i))
        i=j
    else: i+=1

print()
print("=== full-file zero/ascii statistics ===")
z = sum(1 for b in p if b==0)
a = sum(1 for b in p if 32<=b<127)
hi = sum(1 for b in p if b>=128)
print("  len=%d  zeros=%d (%.2f%%)  printable=%d (%.2f%%)  high=%d (%.2f%%)" % (
    len(p), z, 100*z/len(p), a, 100*a/len(p), hi, 100*hi/len(p)))

print()
print("=== value histogram (top 24) ===")
c = collections.Counter(p)
for v,n in c.most_common(24):
    print("   0x%02x %-8d %s" % (v, n, repr(chr(v)) if 32<=v<127 else ""))

print()
print("=== low-value concentration: how many bytes < 0x40? ===")
lows = sum(1 for b in p if b < 0x40)
print("   <0x40: %d (%.2f%%)   >=0x80: %d (%.2f%%)" % (lows, 100*lows/len(p), hi, 100*hi/len(p)))
