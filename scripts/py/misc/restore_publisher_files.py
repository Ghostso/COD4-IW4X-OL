import os, shutil

pub_dir = r"REF_LOBBY_KIT\publisher_files"
files = [
    "configs_s.info",
    "market_ui.info",
    "sku_tags.info",
    "tlogconfig.info",
    "whitelist_tester.info",
    "market-down.info"
]

for fn in files:
    dst = os.path.join(pub_dir, fn)
    bak = dst + ".bak_dummy"
    if os.path.exists(bak):
        shutil.copy2(bak, dst)
        print(f"Restored {fn} from {bak} ({os.path.getsize(dst)} bytes)")
    elif fn == "sku_tags.info" and os.path.exists(dst):
        os.remove(dst)
        print("Removed sku_tags.info (was not present in baseline)")
