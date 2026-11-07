import re
import sys

PKT = r"run_codol_001\runs\ENTRY_CAPTURE_ELEVATED_20260924_160326\pktmon.txt"


def load():
    with open(PKT, "rb") as f:
        return f.read().decode("utf-16le", "replace")


def main():
    txt = load()
    print("pktmon chars:", len(txt))

    print("\n########## 1. config keyword context ##########")
    seen = set()
    for m in re.finditer(r"(?i)(PsIps|EnableP2P|QosMode|IIPSHostApp|ctrl\.iips|PolicySvr|policySvrAddr)", txt):
        key = m.group(1).lower()
        if key in seen and key != "psiips":
            continue
        seen.add(key)
        s = max(0, m.start() - 500)
        e = min(len(txt), m.end() + 1200)
        print("=" * 30, m.group(1), "at", m.start())
        print(txt[s:e])

    print("\n########## 2. flow summary table ##########")
    pat = re.compile(r"^\s*([0-9.]+)\.(\d+) > ([0-9.]+)\.(\d+): (UDP|TCP), length (\d+)\s*$", re.M)
    import collections
    c = collections.Counter()
    tot = collections.Counter()
    first = {}
    for m in pat.finditer(txt):
        src, sport, dst, dport, proto, ln = m.groups()
        k = (dst, int(dport), proto)
        c[k] += 1
        tot[k] += int(ln)
        first.setdefault(k, m.start())
    print("%-18s %-6s %-5s %-6s %-9s %s" % ("dst", "port", "proto", "pkts", "bytes", "firstoff"))
    for (dst, port, proto), n in c.most_common(70):
        print("%-18s %-6d %-5s %-6d %-9d %d" % (dst, port, proto, n, tot[(dst, port, proto)], first[(dst, port, proto)]))

    print("\n########## 3. first 116.130.224.66 window ##########")
    idx = [m.start() for m in re.finditer(r"116\.130\.224\.66\.8000", txt)]
    print("hits:", len(idx))
    if idx:
        i = idx[0]
        s = max(0, i - 2500)
        e = min(len(txt), i + 3500)
        for ln in txt[s:e].splitlines()[:140]:
            print(ln[:210])


if __name__ == "__main__":
    main()
