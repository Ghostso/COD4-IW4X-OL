import re
import sys
from collections import Counter, OrderedDict

RUN = r"run_codol_001\runs\LOBBY_DEEP_20260924_180747"
AFD = RUN + r"\afd.xml"
JSONL = RUN + r"\game_etw.jsonl"


def load(path):
    with open(path, "rb") as f:
        return f.read().decode("utf-8", "replace")


def main():
    data = load(AFD)
    print("afd.xml chars:", len(data))

    # game pid from the run
    GAME_PID = "20500"

    blocks = data.split("<Event xmlns=")
    print("event blocks:", len(blocks))

    rows = []
    for b in blocks:
        m = re.search(r'<Execution ProcessID="(\d+)"', b)
        if not m:
            continue
        t = re.search(r'SystemTime="([^"]+)"', b)
        msg = re.search(r"<Message>(.*?)</Message>", b, re.S)
        if not (t and msg):
            continue
        rows.append((t.group(1), m.group(1), msg.group(1).strip()))

    rows.sort()
    print("parsed events:", len(rows))

    print("\n########## 1. all external connects (any pid) ##########")
    conn = []
    for t, pid, msg in rows:
        if msg.startswith("connect: 0:") or msg.startswith("connect:"):
            a = re.search(r"Address ([0-9a-fA-F:.\[\]%]+)", msg)
            if a:
                conn.append((t, pid, a.group(1)))
    for t, pid, addr in conn:
        if addr.startswith("0.0.0.0") or addr == "0.0.0.0":
            continue
        print(f"{t}  pid={pid}  {addr}")

    print("\n########## 2. connects after t=18:11:00 (last 30s) ##########")
    for t, pid, addr in conn:
        if t >= "2026-09-24T18:11:00":
            print(f"{t}  pid={pid}  {addr}")

    print("\n########## 3. game pid activity, last 40 events ##########")
    g = [(t, m) for t, p, m in rows if p == GAME_PID]
    print("game events:", len(g))
    for t, m in g[-40:]:
        print(f"{t}  {m[:180]}")

    print("\n########## 4. game pid socket/connect/sendto only ##########")
    for t, m in g:
        if re.match(r"^(connect|sendto|socket|bind|closesocket)", m):
            print(f"{t}  {m[:180]}")

    print("\n########## 5. ports touched by game pid ##########")
    ports = Counter()
    for t, m in g:
        for a in re.findall(r":(\d{2,5})\b", m):
            ports[a] += 1
    for p, n in ports.most_common(30):
        print("port", p, "count", n)

    print("\n########## 6. game_etw.jsonl tail ##########")
    try:
        lines = open(JSONL, "r", encoding="utf-8", errors="replace").read().splitlines()
        print("jsonl lines:", len(lines))
        for ln in lines[-25:]:
            print(ln[:220])
    except Exception as e:
        print("jsonl error:", e)


if __name__ == "__main__":
    main()
