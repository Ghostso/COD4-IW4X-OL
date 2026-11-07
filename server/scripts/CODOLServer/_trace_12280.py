import re

AFD = r"run_codol_001\runs\ENTRY_CAPTURE_ELEVATED_20260924_160326\afd.xml"
PKT = r"run_codol_001\runs\ENTRY_CAPTURE_ELEVATED_20260924_160326\pktmon.txt"
PKTMON = r"run_codol_001\runs\ENTRY_CAPTURE_ELEVATED_20260924_160326\pktmon.pcapng"


def afd_events_for_pid(pid, limit=400):
    data = open(AFD, "rb").read().decode("utf-8", "replace")
    blocks = data.split("<Event xmlns=")
    out = []
    for b in blocks:
        m = re.search(r'<Execution ProcessID="(\d+)"', b)
        if not m or m.group(1) != str(pid):
            continue
        t = re.search(r'SystemTime="([^"]+)"', b)
        msg = re.search(r"<Message>(.*?)</Message>", b, re.S)
        if not msg:
            continue
        out.append((t.group(1) if t else "", msg.group(1).strip()))
    out.sort()
    return out[:limit]


def main():
    ev = afd_events_for_pid(12280)
    print("PID 12280 events:", len(ev))
    for t, m in ev:
        print(t, "|", m)


if __name__ == "__main__":
    main()
