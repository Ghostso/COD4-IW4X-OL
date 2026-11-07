# -*- coding: utf-8 -*-
"""校验 marketplace-catalog-client.json 与开关行为。"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import marketplace_store as ms


def main():
    base = json.load(open(os.path.join(ROOT, "marketplace-catalog.json"),
                          "r", encoding="utf-8"))
    client = json.load(open(os.path.join(ROOT, "marketplace-catalog-client.json"),
                            "r", encoding="utf-8"))
    print("exe 目录: %d 条" % len(base))
    print("客户端目录: %d 条" % len(client))
    by_id = {int(e["Id"]): e for e in client}
    for s in (980, 986, 16350, 19428, 37115, 37251, 39592, 32223):
        e = by_id.get(s)
        print("  sku=%-7d -> %s" % (s, e))

    print()
    print("catalog_path() =", ms.catalog_path())
    print("load_catalog() 条数 =", len(ms.load_catalog()))

    # 验证开关生效
    on = os.path.join(ROOT, "marketplace-catalog-client.on")
    open(on, "w").close()
    ms._catalog = None
    try:
        p = ms.catalog_path()
        n = len(ms.load_catalog())
        print("打开开关后 catalog_path() =", p)
        print("打开开关后 load_catalog() 条数 =", n)
        assert p.endswith("marketplace-catalog-client.json"), p
        assert n == len(client), n
        print("开关行为: OK")
    finally:
        os.remove(on)
        ms._catalog = None
    return 0


if __name__ == "__main__":
    sys.exit(main())
