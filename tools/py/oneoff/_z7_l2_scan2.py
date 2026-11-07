import sys, os, struct, importlib.util, collections, math
sys.path.insert(0, r"CODOLServer\_mainline")
spec = importlib.util.spec_from_file_location("ff", r"CODOLServer\_mainline\ff_iw4_decrypt.py")
ff = importlib.util.module_from_spec(spec); spec.loader.exec_module(ff)

def plain(n): return ff.decrypt_file(os.path.join("COD OL","main",n))["plain"]
pl = plain("mp_playlists.ff")

print("=== mp_playlists: ALL ascii runs >=5 in WHOLE file (not just head) ===")
i=0; cnt=0
while i < len(pl) and cnt < 60:
    j=i
    while j < len(pl) and 32<=pl[j]<127: j+=1
    if j-i >= 5:
        print("   @0x%06x len=%3d  %r" % (i, j-i, pl[i:j]))
        cnt+=1
    i=max(j,i+1)
print("   total ascii runs>=5 shown:", cnt)

print()
print("=== zero runs >= 8 ===")
i=0; z=0
while i < len(pl):
    if pl[i]==0:
        j=i
        while j<len(pl) and pl[j]==0: j+=1
        if j-i>=8:
            print("   zeros @0x%06x len=%d" % (i,j-i)); z+=1
            if z>=25: break
        i=j
    else: i+=1

print()
print("=== compare head region across files: offsets 0x100..0x200 ===")
for nm in ["mp_playlists.ff","development_mp.ff","localized_ui_mp.ff"]:
    p = plain(nm)
    print("  ---", nm)
    for r in range(0x120, 0x1a0, 0x10):
        b=p[r:r+0x10]
        print("     +0x%03x %s %s" % (r, b.hex(), ''.join(chr(x) if 32<=x<127 else '.' for x in b)))
