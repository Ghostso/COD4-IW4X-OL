import re
import collections

RUN = r"run_codol_001\runs\LOBBY_DEEP_20260924_181441"
AFD = RUN + r"\afd.xml"
PKT = RUN + r"\pktmon.txt"
PCAP = RUN + r"\pktmon.pcapng"


def main():
    print("########## A. afd: game pid 12696 external touchpoints ##########")
    data = open(AFD, "rb").read().decode("utf-8", "replace")
    rows = []
    for b in data.split("<Event xmlns="):
        m = re.search(r'<Execution ProcessID="(\d+)"', b)
        if not m:
            continue
        t = re.search(r'SystemTime="([^"]+)"', b)
        msg = re.search(r"<Message>(.*?)</Message>", b, re.S)
        if t and msg:
            rows.append((t.group(1), m.group(1), msg.group(1).strip()))
    rows.sort()
    print("total afd events:", len(rows))

    game = [(t, m) for t, p, m in rows if p == "12696"]
    print("game pid 12696 events:", len(game))
    if game:
        print("first:", game[0][0], "last:", game[-1][0])

    touch = {}
    for t, m in game:
        mm = re.search(r"(?:Addr|Address) ([0-9a-fA-F:.\[\]%]+)", m)
        if not mm:
            continue
        v = mm.group(1)
        if v.startswith("0.0.0.0") or v.startswith("127.0.0.1") or v.startswith("[fe80"):
            continue
        if v not in touch:
            touch[v] = [t, t, 0]
        touch[v][1] = t
        touch[v][2] += 1
    for v, (t0, t1, n) in sorted(touch.items()):
        print(f"  {v:26s} first={t0[11:23]} last={t1[11:23]} n={n}")

    print("\n########## B. pktmon: flows touching port 8000 ##########")
    txt = open(PKT, "rb").read().decode("utf-16le", "replace")
    print("pktmon chars:", len(txt))
    pat = re.compile(r"^\s*([0-9.]+)\.(\d+) > ([0-9.]+)\.(\d+): (UDP|TCP), length (\d+)\s*$", re.M)
    agg = collections.Counter()
    for m in pat.finditer(txt):
        src, sp, dst, dp, proto, ln = m.groups()
        if int(dp) == 8000 or int(sp) == 8000:
            agg[(src, int(sp), dst, int(dp), proto)] += 1
    for k, n in agg.most_common(50):
        print("  ", k, "packets:", n)

    print("\n########## C. pktmon: any 116.130.224.66 context ##########")
    idx = [m.start() for m in re.finditer(r"116\.130\.224\.66", txt)]
    print("hits:", len(idx))
    for i in idx[:8]:
        s = max(0, i - 900)
        e = min(len(txt), i + 1600)
        print("-" * 60)
        for ln in txt[s:e].splitlines():
            if ln.strip():
                print(ln[:190])


if __name__ == "__main__":
    main()
