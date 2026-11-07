import sys, os, struct, importlib.util
sys.path.insert(0, r"CODOLServer\_mainline")
spec = importlib.util.spec_from_file_location("ff", r"CODOLServer\_mainline\ff_iw4_decrypt.py")
ff = importlib.util.module_from_spec(spec); spec.loader.exec_module(ff)

names = ["code_post_gfx_default_mp.ff","code_post_gfx_mp.ff","code_pre_gfx_mp.ff",
         "common_mp_reload.ff","development_mp.ff","localized_code_post_gfx_mp.ff",
         "localized_code_pre_gfx_mp.ff","localized_ui_mp.ff","mp_playlists.ff","ui_mp.ff"]
print("%-32s %10s  %-24s %-24s %s" % ("file","size","head[8:24]","head[16:32]","u32@8 / u32@12"))
rows=[]
for n in names:
    i = ff.decrypt_file(os.path.join("COD OL","main",n))
    p = i["plain"]
    rows.append((n, i["size"], p, i["key"], i["iv"]))
    print("%-32s %10d  %s %s  %d / %d" % (n, i["size"], p[8:24].hex(), p[16:32].hex(),
          struct.unpack_from("<I",p,8)[0], struct.unpack_from("<I",p,12)[0]))

print()
print("=== hypothesis: head[0:12] = 'IWffs100' + u32 decryptedSize, plaintext (not AES) ===")
for n, sz, p, k, iv in rows:
    hdr8 = p[8:12]
    print("  %-32s hdr8=%s  size=%9d  hdr8_as_u32=%d  size//hdr8=%s" % (
        n, hdr8.hex(), sz, struct.unpack('<I',hdr8)[0],
        (sz/max(1,struct.unpack('<I',hdr8)[0])) if struct.unpack('<I',hdr8)[0] else "n/a"))

print()
print("=== do these files share a prefix? compare first differing offset ===")
base = rows[0][2]
for n, sz, p, k, iv in rows[1:]:
    j = 0
    while j < min(len(base), len(p)) and base[j] == p[j]:
        j += 1
    print("  %-32s first diff at 0x%03x (%d)" % (n, j, j))
