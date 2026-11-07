# -*- coding: utf-8 -*-
"""从 `lf_init_common_marketplace_*.ifs` 里抽**道具资源清单**。

★ 2026-10-05 重大发现: 主目录里一直有**完整版** `common_marketplace`
  (之前只啃了 29MB 的 `common_marketplace_lite`), 共 37 个包 / 9.4 GB。
  这些包是 **`nifs` 明文容器**(不是加密 ff), 头 0x200 之后就是
  `main/images/xxx_item_icon.iwi`、`main/models/...` 这类资源路径。

意义: 这些资源名 = 商城道具的**权威清单**(客户端要显示什么, 就有什么资源)。
      可用它反推 SKU/道具的编号体系, 或至少确认"本地到底有哪些道具可展示"。

用法: python -X utf8 _extract_marketplace_assets.py [outdir]
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
IIPS = os.path.abspath(os.path.join(ROOT, "..", "COD OL", "IIPS", "IIPSDownload"))


def iter_marketplace_packs():
    try:
        names = os.listdir(IIPS)
    except Exception:
        return
    for n in sorted(names):
        if "common_marketplace" in n and n.lower().endswith(".ifs"):
            yield os.path.join(IIPS, n)


def scan_pack(path, out):
    """抽一个包里的资源路径。返回 (路径数, 按类别计数)。"""
    base = os.path.basename(path)
    try:
        b = open(path, "rb").read()
    except Exception as e:
        return 0, {}, str(e)
    if b[:4] != b"nifs":
        return 0, {}, "not nifs"
    ss = [s.decode("latin1") for s in re.findall(rb"[ -~]{6,160}", b)]
    paths = [s for s in ss if s.startswith("main/") or s.startswith("mp/")]
    if out:
        fn = os.path.join(out, base + ".paths.txt")
        with open(fn, "w", encoding="utf-8") as f:
            for s in sorted(set(paths)):
                f.write(s + "\n")
    cnt = {}
    for s in paths:
        if s.startswith("main/images/"):
            cnt["images"] = cnt.get("images", 0) + 1
        elif s.startswith("main/models/"):
            cnt["models"] = cnt.get("models", 0) + 1
        elif s.startswith("mp/"):
            cnt["mp"] = cnt.get("mp", 0) + 1
        else:
            cnt["other"] = cnt.get("other", 0) + 1
    return len(paths), cnt, None


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "mkt_assets")
    os.makedirs(out, exist_ok=True)
    total = 0
    agg = {}
    for p in iter_marketplace_packs():
        n, cnt, err = scan_pack(p, out)
        total += n
        for k, v in cnt.items():
            agg[k] = agg.get(k, 0) + v
        print("%-52s paths=%-7d %s%s"
              % (os.path.basename(p), n, cnt, (" ERR=%s" % err) if err else ""))
    print("----")
    print("合计资源路径:", total, agg)


if __name__ == "__main__":
    main()
