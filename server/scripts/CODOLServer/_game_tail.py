import re

RUN = r"run_codol_001\runs\LOBBY_DEEP_20260924_180747"
AFD = RUN + r"\afd.xml"
GAME_PID = "20500"


def main():
    data = open(AFD, "rb").read().decode("utf-8", "replace")
    blocks = data.split("<Event xmlns=")
    rows = []
    for b in blocks:
        m = re.search(r'<Execution ProcessID="(\d+)"', b)
        if not m or m.group(1) != GAME_PID:
            continue
        t = re.search(r'SystemTime="([^"]+)"', b)
        msg = re.search(r"<Message>(.*?)</Message>", b, re.S)
        if not (t and msg):
            continue
        rows.append((t.group(1), msg.group(1).strip()))
    rows.sort()
    print("game pid", GAME_PID, "events:", len(rows))
    print("first:", rows[0][0])
    print("last :", rows[-1][0])

    # collapse identical consecutive sendto bursts for readability
    print("\n########## external address touchpoints (game pid) ##########")
    seen = {}
    for t, m in rows:
        a = re.search(r"Addr ([0-9a-fA-F:.\[\]%]+)", m)
        c = re.search(r"Address ([0-9a-fA-F:.\[\]%]+)", m)
        addr = (a or c)
        if not addr:
            continue
        v = addr.group(1)
        if v.startswith("0.0.0.0") or v.startswith("127.0.0.1") or v.startswith("[fe80"):
            continue
        if v not in seen:
            seen[v] = [t, t, 0]
        seen[v][1] = t
        seen[v][2] += 1
    for v, (t0, t1, n) in sorted(seen.items()):
        print(f"{v:28s} first={t0[11:23]} last={t1[11:23]} count={n}")

    print("\n########## last 60 game events ##########")
    for t, m in rows[-60:]:
        print(f"{t[11:23]}  {m[:170]}")

    print("\n########## any 'connection aborted' / error status ##########")
    for t, m in rows:
        if "abort" in m.lower() or "refus" in m.lower() or "Status STATUS_" in m and "SUCCESS" not in m:
            print(f"{t[11:23]}  {m[:200]}")


if __name__ == "__main__":
    main()
