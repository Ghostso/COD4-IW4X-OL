# -*- coding: utf-8 -*-
"""从 lobby_tasks.bin 提取每个 SKU 实际走的服务号, 推出货币。

服务约定(照抄 CodolLocalLobbyServer.cs):
  service 80  -> currency 1 (CP/CodPoints)
  service 93  -> currency 2 (GP/Gold)

输出: mkt_assets/sku_currency.csv
"""
import csv
import json
import os
import struct
import sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(ROOT, "lobby_tasks.bin")
OUT = os.path.join(ROOT, "mkt_assets", "sku_currency.csv")


def scan_fields(payload):
    """按 TLV 取 u32 序列(与 marketplace_store._scan_purchase_fields 同义)。"""
    out = []
    i = 0
    n = len(payload)
    while i < n:
        tag = payload[i]
        i += 1
        if tag == 0x01:
            i += 1
        elif tag == 0x03:
            i += 1
        elif tag == 0x06:
            i += 2
        elif tag == 0x07:
            out.append(struct.unpack_from("<I", payload, i)[0]); i += 4
        elif tag == 0x08:
            out.append(struct.unpack_from("<I", payload, i)[0]); i += 4
        elif tag == 0x09:
            i += 8
        elif tag == 0x0A:
            i += 8
        elif tag == 0x10:
            j = payload.find(b"\x00", i)
            if j < 0:
                break
            i = j + 1
        elif tag == 0x13:
            if i + 5 > n or payload[i] != 0x08:
                break
            ln = struct.unpack_from("<I", payload, i + 1)[0]
            i += 5 + ln
        else:
            break
    return out


def main():
    raw = open(TASKS, "rb").read()
    off = 0
    acc = defaultdict(Counter)
    while off + 6 <= len(raw):
        svc = raw[off]
        task = raw[off + 1]
        ln = struct.unpack_from("<I", raw, off + 2)[0]
        if off + 6 + ln > len(raw):
            break
        pl = raw[off + 6:off + 6 + ln]
        off += 6 + ln
        if (svc, task) not in ((80, 154), (93, 131)):
            continue
        vals = scan_fields(pl)
        if len(vals) < 4 or vals[1] == 0:
            continue
        acc[vals[1]][svc] += 1

    # ★ 合并历史记录: lobby_tasks.bin 每轮会被覆盖, 但 sku_currency.csv 累积。
    #   读入已有记录, 用本轮观测覆盖, 其余保留。
    merged = {}
    if os.path.exists(OUT):
        for r in csv.DictReader(open(OUT, "r", encoding="utf-8-sig")):
            try:
                merged[int(r["sku"])] = {
                    "sku": int(r["sku"]), "service": int(r["service"]),
                    "currency": int(r["currency"]), "votes": int(r["votes"]),
                }
            except Exception:
                pass
    # 从客户端目录回填历史 —— 只限"我们新增的那批 SKU"(client_catalog + extra),
    # 不要把 exe 内嵌目录的 3.7 万条灌进来。
    clientp = os.path.join(ROOT, "mkt_assets", "client_catalog.csv")
    catp = os.path.join(ROOT, "marketplace-catalog-client.json")
    if os.path.exists(clientp) and os.path.exists(catp):
        try:
            ours = set()
            for r in csv.DictReader(open(clientp, "r", encoding="utf-8-sig")):
                ours.add(int(r["sku"]))
            extp = os.path.join(ROOT, "mkt_assets", "extra_skus.csv")
            if os.path.exists(extp):
                for r in csv.DictReader(open(extp, "r", encoding="utf-8-sig")):
                    ours.add(int(r["sku"]))
            for e in json.load(open(catp, "r", encoding="utf-8")):
                sid = int(e.get("Id", 0))
                cur = int(e.get("Currency", 0))
                if sid in ours and cur in (1, 2) and sid not in merged:
                    merged[sid] = {"sku": sid,
                                   "service": 80 if cur == 1 else 93,
                                   "currency": cur, "votes": 0}
        except Exception:
            pass

    rows = []
    for sku in sorted(acc):
        svc = acc[sku].most_common(1)[0][0]
        cur = 1 if svc == 80 else 2
        merged[sku] = {"sku": sku, "service": svc, "currency": cur,
                       "votes": sum(acc[sku].values())}
    rows = [merged[k] for k in sorted(merged)]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["sku", "service", "currency", "votes"])
        w.writeheader()
        w.writerows(rows)
    print("购买帧 SKU: 本轮 %d 个, 累计 %d 个 -> %s"
          % (len(acc), len(rows), OUT))
    c = Counter(r["currency"] for r in rows)
    print("货币分布: %s" % dict(c))
    for r in rows[:20]:
        print("  sku=%-7d service=%d currency=%d" % (r["sku"], r["service"], r["currency"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
