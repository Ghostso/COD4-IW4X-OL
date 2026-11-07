import sys, os, struct, importlib.util
sys.path.insert(0, r"CODOLServer\_mainline")
spec = importlib.util.spec_from_file_location("ff", r"CODOLServer\_mainline\ff_iw4_decrypt.py")
ff = importlib.util.module_from_spec(spec); spec.loader.exec_module(ff)

def plain(n): return ff.decrypt_file(os.path.join("COD OL","main",n))["plain"]

print("=== PARSE zone header at 0x0 : 'IWffs100' + u32 + zone name @0x12c ===")
for nm in ["mp_playlists.ff","development_mp.ff","localized_ui_mp.ff","code_pre_gfx_mp.ff"]:
    p = plain(nm)
    magic = p[0:8]
    u8    = struct.unpack_from("<I", p, 8)[0]
    # zone name: find NUL-terminated run starting at 0x12c
    name = p[0x12c:p.index(b"\0",0x12c)]
    print("  %-26s magic=%r u32@8=%d  name@0x12c=%r  len=%d" % (nm, magic, u8, name, len(p)))

print()
print("=== what is at 0x120..0x12c (12 bytes before the name) per file? ===")
for nm in ["mp_playlists.ff","development_mp.ff","localized_ui_mp.ff","code_pre_gfx_mp.ff"]:
    p = plain(nm)
    print("  %-26s %s" % (nm, p[0x120:0x12c].hex()))

print()
print("=== structural constant check: magic+u32+12B+xName+pad16+zero16 ===")
# 8 + 4 + 12 + 16 + 16 = 0x38 -> data at 0x12c+16+16 = 0x14c
for nm in ["mp_playlists.ff","development_mp.ff","localized_ui_mp.ff"]:
    p = plain(nm)
    print("  %-26s data@0x14c begins: %s" % (nm, p[0x14c:0x15c].hex()))

print()
print("=== Is 0x14c..EOF a proportional-size stream? compare header field u32@8 to file size ===")
for nm in ["mp_playlists.ff","development_mp.ff","localized_ui_mp.ff","code_pre_gfx_mp.ff","ui_mp.ff","code_post_gfx_mp.ff"]:
    p = plain(nm)
    u = struct.unpack_from("<I", p, 8)[0]
    print("  %-26s len=%9d  u32@8=%d  len-0x14c=%9d" % (nm, len(p), u, len(p)-0x14c))
