import re

RUN = r"run_codol_001\runs\LOBBY_DEEP_20260924_181441"
PKT = RUN + r"\pktmon.txt"


def main():
    txt = open(PKT, "rb").read().decode("utf-16le", "replace")

    # Lines produced by pktmon's textual protocol decoder, e.g.
    # ... q: A? ied-tqos.qq.com. 1/0/0 ied-tqos.qq.com. [55s] A 116.130.224.66
    q = []
    for line in txt.splitlines():
        if " q: A" not in line:
            continue
        m = re.search(r"q: (A+)\? ([^ ]+)\. \d+/\d+/\d+ ([^ ]+)\. \[(\d+)s\] (A+) ([0-9a-fA-F:.]+)", line)
        if m:
            q.append(m.groups())

    print("DNS answer records:", len(q))
    seen = set()
    for typ, name, cname, ttl, atype, addr in q:
        key = (name.lower(), cname.lower(), addr)
        if key in seen:
            continue
        seen.add(key)
        print(f"{name:45s} -> {addr:48s} ttl={ttl:>5s} cname={cname}")

    print("\n########## interesting name filters ##########")
    keys = ("qq.com", "tcls", "tqos", "codol", "iips", "gamesafe", "stun", "qos")
    for typ, name, cname, ttl, atype, addr in q:
        if any(k in name.lower() or k in cname.lower() for k in keys):
            print(f"{name:45s} -> {addr:48s} cname={cname}")


if __name__ == "__main__":
    main()
