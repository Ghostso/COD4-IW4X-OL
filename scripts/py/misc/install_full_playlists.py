import zlib, os, shutil

src_path = r"_e1_regression\ol-mod-olfinal\assets\backend\1004\Server\mp_playlists_shipRetail_release.info"
raw_text = open(src_path, "rb").read()
compressed = zlib.compress(raw_text)

pub_dir = r"REF_LOBBY_KIT\publisher_files"
dst1 = os.path.join(pub_dir, "mp_playlists_shipRetail_1.0.0.info")
dst2 = os.path.join(pub_dir, "mp_playlists_shipRetail_release.info")

# Backup originals if not already backed up
for dst in [dst1, dst2]:
    bak = dst + ".bak_dummy"
    if os.path.exists(dst) and not os.path.exists(bak):
        shutil.copy2(dst, bak)
        print(f"Backed up {dst} -> {bak}")

with open(dst1, "wb") as f:
    f.write(compressed)
print(f"Wrote {len(compressed)} bytes to {dst1}")

with open(dst2, "wb") as f:
    f.write(compressed)
print(f"Wrote {len(compressed)} bytes to {dst2}")
