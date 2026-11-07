# -*- coding: utf-8 -*-
"""按 MD5 在包文件里找那 6 张商城表(完整版)。

原理:
  mp/marketplace.json 给出 6 张表各自的 MD5。
  nifs 容器里资源路径是明文, 但表体大概率是 zlib 压缩。
  所以: 扫包里所有合法 zlib 流 -> 解压 -> 算 MD5 -> 与目标比对。

zlib 头校验: CMF=0x78, (0x78*256+FLG) % 31 == 0  -> FLG ∈ {01,5E,9C,DA}
"""
import hashlib
import json
import os
import re
import sys
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
IIPS = os.path.abspath(os.path.join(ROOT, "..", "COD OL", "IIPS", "IIPSDownload"))
MAN = os.path.join(ROOT, "mkt_assets", "marketplace.client.json")
OUTDIR = os.path.join(ROOT, "mkt_assets", "co_market")

CHUNK = 8 * 1024 * 1024
OVERLAP = 128 * 1024
MAXOUT = 24 * 1024 * 1024
FLGS = (0x01, 0x5E, 0x9C, 0xDA)
ZLIB_RE = re.compile(rb"\x78[\x01\x5e\x9c\xda]")


def candidates(buf, base_off):
    """产出 (全局偏移, 当前位置) 的 zlib 候选（用正则加速）。"""
    for m in ZLIB_RE.finditer(buf):
        i = m.start()
        if (0x78 * 256 + buf[i + 1]) % 31 == 0:
            yield base_off + i


def try_inflate(buf, i):
    try:
        d = zlib.decompressobj(15)
        out = d.decompress(buf[i:i + MAXOUT])
        out += d.flush()
    except Exception:
        return None
    return out or None


def scan_file(path, targets, found, log):
    size = os.path.getsize(path)
    off = 0
    checked = 0
    with open(path, "rb") as f:
        tail = b""
        while True:
            block = f.read(CHUNK)
            if not block:
                break
            buf = tail + block
            base = off - len(tail)
            for gpos in candidates(buf, base):
                loc = gpos - base
                out = try_inflate(buf, loc)
                checked += 1
                if not out:
                    continue
                h = hashlib.md5(out).hexdigest().upper()
                if h in targets:
                    name = targets[h]
                    log("  ★ 命中 %s @0x%X (%d 字节)" % (name, gpos, len(out)))
                    found[name] = out
            tail = buf[-OVERLAP:]
            off += len(block)
    return checked


def main():
    j = json.load(open(MAN, "r", encoding="utf-8"))
    targets = {}
    for k, v in j.items():
        if isinstance(v, str) and len(v) == 32:
            targets[v.upper()] = k
    print("目标表 %d 张" % len(targets))
    for h, n in targets.items():
        print("   %s  %s" % (n, h))
    print()

    only = sys.argv[1] if len(sys.argv) > 1 else "marketplace"
    names = [n for n in os.listdir(IIPS) if n.lower().endswith(".ifs")]
    if only == "marketplace":
        names = [n for n in names if "marketplace" in n.lower()]
    names.sort()
    print("扫描 %d 个包 (筛选=%s)" % (len(names), only))

    found = {}
    total_checked = 0
    for idx, n in enumerate(names, 1):
        p = os.path.join(IIPS, n)
        try:
            sz = os.path.getsize(p)
        except OSError:
            continue
        print("[%d/%d] %s (%.0f MB)" % (idx, len(names), n, sz / 1048576.0))
        try:
            c = scan_file(p, targets, found, print)
            total_checked += c
        except Exception as e:
            print("   扫描失败 %r" % (e,))

    print()
    print("共检查 %d 个 zlib 候选" % total_checked)
    print("命中 %d / %d" % (len(found), len(targets)))
    os.makedirs(OUTDIR, exist_ok=True)
    for name in found:
        with open(os.path.join(OUTDIR, name), "wb") as f:
            f.write(found[name])
        print("  写出 %s (%d 字节)" % (name, len(found[name])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
