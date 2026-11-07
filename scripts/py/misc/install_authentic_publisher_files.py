import os, shutil

src_dir = r"_e1_regression\ol-mod-olfinal\assets\backend\1004\Server"
dst_dir = r"REF_LOBBY_KIT\publisher_files"

files = [
    "configs_s.info",
    "market_ui.info",
    "sku_tags.info",
    "tlogconfig.info",
    "whitelist_tester.info",
    "market-down.info"
]

for fn in files:
    src = os.path.join(src_dir, fn)
    dst = os.path.join(dst_dir, fn)
    if os.path.exists(src):
        if os.path.exists(dst):
            bak = dst + ".bak_dummy"
            if not os.path.exists(bak):
                shutil.copy2(dst, bak)
                print(f"Backed up {dst} -> {bak}")
        shutil.copy2(src, dst)
        size = os.path.getsize(dst)
        print(f"Installed {fn} ({size} bytes)")
    else:
        print(f"Source file not found: {src}")
