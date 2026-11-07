# -*- coding: utf-8 -*-
"""验证: 购买后该物品会被排到库存应答最前面(避免被截掉)。"""
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import marketplace_store as ms


def main():
    owner = 16701785630074219790
    tmp = tempfile.mkdtemp(prefix="codol_prio_")
    try:
        for name in ("player-account.json", "marketplace-inventory.json"):
            src = os.path.join(ROOT, name)
            if os.path.exists(src):
                shutil.copy(src, os.path.join(tmp, name))
        # secure.result 在 profile_results 子目录
        sp = ms.secure_path(ROOT)
        if os.path.exists(sp):
            dst = ms.secure_path(tmp)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy(sp, dst)
            print("secure.result -> %s" % dst)

        # 用客户端目录(含 31181/31184)
        here = ROOT
        on = os.path.join(here, "marketplace-catalog-client.on")
        ms._catalog = None
        catalog = ms.load_catalog(os.path.join(here, "marketplace-catalog-client.json"))
        print("目录条目: %d" % len(catalog))

        st = ms.read_inventory(tmp, owner)
        print("库存件数: %d" % len(st["Items"]))
        print("Priority 初始: %s" % st.get("Priority"))

        objs = ms.inventory_results(tmp, owner)
        print("默认应答件数: %d" % len(objs))

        # 模拟购买 31184 -> item 22384
        sku = catalog.get(31184)
        print()
        print("购买 sku=31184 -> %r" % sku)
        ms.purchase(tmp, owner, "test-prio-1", sku.Currency, [sku.Id], [1])
        st2 = ms.read_inventory(tmp, owner)
        print("购买后 Priority: %s" % st2.get("Priority"))

        objs2 = ms.inventory_results(tmp, owner)
        print("购买后应答件数: %d" % len(objs2))
        # 检查 22384 是否在发出的对象里
        import struct
        def item_of(o):
            # inventory_object: 0x0A + u64 + 0x10 'cod'\0 + 0x08 item
            return struct.unpack_from("<I", o, 15)[0]
        sent = set(item_of(o) for o in objs2)
        print("item 22384 是否在应答里: %s" % (22384 in sent))
        print("应答首件 item: %d" % item_of(objs2[0]))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
