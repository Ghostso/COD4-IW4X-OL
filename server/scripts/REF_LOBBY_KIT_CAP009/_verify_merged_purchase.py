# -*- coding: utf-8 -*-
"""在**临时副本**上用真实账户/库存验证合并目录的新 SKU 能否购买。

不碰 REF_LOBBY_KIT 下的真实文件: 只复制 player-account.json /
marketplace-inventory.json / player_profiles/secure.result 到 temp 目录。
"""
import json
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import marketplace_store as ms  # noqa: E402

TESTS = [
    (37116, 1),   # 用户实测点失败: 29767 / 10000 CP
    (37251, 1),   # 29892 / 8000 CP
    (16096, 2),   # 7110  / 880 GP
    (31184, 2),   # 22384 / 680 GP (7 天)
    (31774, 1),   # 122   / 2280 CP (30 天, 白名单)
]


def main():
    tmp = tempfile.mkdtemp(prefix="mkmerged-verify-")
    try:
        os.makedirs(os.path.join(tmp, "player_profiles"), exist_ok=True)
        for fn in ("player-account.json", "marketplace-inventory.json"):
            shutil.copy(os.path.join(ROOT, fn), os.path.join(tmp, fn))
        shutil.copy(os.path.join(ROOT, "player_profiles", "secure.result"),
                    os.path.join(tmp, "player_profiles", "secure.result"))
        inv = json.load(open(os.path.join(tmp, "marketplace-inventory.json"),
                             encoding="utf-8"))
        owner = int(inv.get("Owner", 16701785630074219790))
        print("catalog =", os.path.basename(ms.catalog_path()))
        a0 = ms.read_account(tmp)
        i0 = ms.read_inventory(tmp, owner)
        print("before: CodPoints=%d Gold=%d Items=%d Tx=%d"
              % (a0["CodPoints"], a0["Gold"], len(i0["Items"]),
                 len(i0["Transactions"])))
        print("-" * 68)
        for n, (sku_id, cur) in enumerate(TESTS, 1):
            sku = ms.load_catalog().get(sku_id)
            if sku is None:
                print("SKU %d: MISSING" % sku_id)
                continue
            before = ms.read_account(tmp)
            b = before["CodPoints"] if cur == 1 else before["Gold"]
            try:
                rc = ms.purchase(tmp, owner, "verify-20261006-%d" % sku_id,
                                 cur, [sku_id], [1])
                err = None
            except Exception as e:
                rc, err = None, repr(e)
            after = ms.read_account(tmp)
            a = after["CodPoints"] if cur == 1 else after["Gold"]
            st = ms.read_inventory(tmp, owner)
            got = st["Items"].get(str(sku.Item), 0)
            ok = (err is None and rc == 0 and a == b - sku.Price)
            print("SKU %-6d Item=%-6d cur=%d price=%-6d rc=%s "
                  "balance %d->%d (%+d) inventory[%d]=%d  %s"
                  % (sku_id, sku.Item, cur, sku.Price, rc, b, a, a - b,
                     sku.Item, got, "OK" if ok else "FAIL " + str(err)))
        print("-" * 68)
        i1 = ms.read_inventory(tmp, owner)
        print("after : Items=%d Tx=%d" % (len(i1["Items"]),
                                          len(i1["Transactions"])))
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
