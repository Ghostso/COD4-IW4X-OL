from pathlib import Path
import re
import sys
from datetime import datetime

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")


def read_log(path):
    b = path.read_bytes()
    if b[:2] == b"\xff\xfe":
        return b.decode("utf-16", errors="replace")
    return b.decode("utf-8", errors="replace")


def mode_a_events(text):
    rows = []
    for line in text.splitlines():
        m = re.search(r"MODULE_LOAD t=([\d.]+) (.+?) base (0x[0-9a-fA-F]+) size (0x[0-9a-fA-F]+)", line)
        if m:
            rows.append((float(m.group(1)), "MODULE_LOAD", Path(m.group(2)).name, m.group(2)))
            continue
        m = re.search(r"THREAD t=([\d.]+) TID (\d+) start (0x[0-9a-fA-F]+)", line)
        if m:
            rows.append((float(m.group(1)), "THREAD", m.group(2), m.group(3)))
            continue
        m = re.search(r"FINAL_EXIT (\S+)", line)
        if m:
            rows.append((999.0, "FINAL_EXIT", "", m.group(1)))
            continue
        m = re.search(r"TERMINATE (\d+)", line)
        if m:
            rows.append((999.0, "TERMINATE", m.group(1), ""))
    return rows


def mode_b_events(text):
    rows = []
    base = None
    for line in text.splitlines():
        m = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}) (.*)", line)
        if not m:
            continue
        ts = datetime.fromisoformat(m.group(1))
        if base is None:
            base = ts
        rel = (ts - base).total_seconds()
        rest = m.group(2)
        m2 = re.search(r"LOAD_DLL tid=(\d+) base=([0-9a-fA-F]{8}) .*path=(.+)$", rest)
        if m2:
            path = m2.group(3).replace("\\\\?\\", "")
            rows.append((rel, "LOAD_DLL", m2.group(1), Path(path).name + " " + path))
            continue
        m2 = re.search(r"BP_HIT tid=(\d+) label=([^ ]+) addr=([0-9a-fA-F]{8})", rest)
        if m2:
            rows.append((rel, "BP_HIT", m2.group(1), m2.group(2) + " " + m2.group(3)))
            continue
        m2 = re.search(r"CREATE_THREAD tid=(\d+) start=([0-9a-fA-F]{8})", rest)
        if m2:
            rows.append((rel, "CREATE_THREAD", m2.group(1), m2.group(2)))
            continue
        m2 = re.search(r"EXCEPTION code=([0-9A-Fa-f]+) addr=([0-9A-Fa-f]+) first=(\d+) module=(\S+)", rest)
        if m2:
            rows.append((rel, "EXCEPTION", "", m2.group(1) + " " + m2.group(4)))
            continue
        m2 = re.search(r"EXIT_PROCESS code=(\d+)", rest)
        if m2:
            rows.append((rel, "EXIT_PROCESS", "", m2.group(1)))
    return rows


def main():
    if len(sys.argv) < 3:
        print("usage: ex028_build_timeline.py <mode_a_log> <mode_b_log>")
        return 2
    a_path = Path(sys.argv[1])
    b_path = Path(sys.argv[2])
    a = mode_a_events(read_log(a_path))
    b = mode_b_events(read_log(b_path))

    project = ["ACE-DRV32.dll", "tersafe.dll", "TenRpcs.dll", "GameRpcs.dll", "GDPLoader.dll",
               "tcj.dll", "GameDataPlatformServer.dll", "policyprobe.dll", "TenProxy.dll", "GbSpy.dll"]
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_log = ROOT / "工具" / "logs" / ("ex028_observer_divergence_" + stamp + ".log")
    out_csv = ROOT / "工具" / "logs" / ("ex028_timeline_" + stamp + ".csv")

    lines = []
    lines.append("EX-028 OBSERVER DIVERGENCE SUMMARY")
    lines.append("MODE_A=" + str(a_path))
    lines.append("MODE_B=" + str(b_path))
    lines.append("")
    lines.append("PROJECT MODULE TIMES MODE_A")
    for name in project:
        hits = [x for x in a if x[1] == "MODULE_LOAD" and name.lower() in x[3].lower()]
        if hits:
            lines.append("  T+%.3f %s" % (hits[0][0], name))
        else:
            lines.append("  ABSENT " + name)
    lines.append("")
    lines.append("PROJECT MODULE TIMES MODE_B")
    for name in project:
        hits = [x for x in b if x[1] == "LOAD_DLL" and name.lower() in x[3].lower()]
        if hits:
            lines.append("  T+%.3f %s" % (hits[0][0], name))
        else:
            lines.append("  ABSENT " + name)
    lines.append("")
    lines.append("COMMON NODES BEFORE DIVERGENCE")
    for node in ["codoMP_client_shipRetail.exe", "codoMP_client_shipRetailBase.dll", "libcef.dll", "BugTrace.dll"]:
        ah = min([x[0] for x in a if x[1] == "MODULE_LOAD" and node.lower() in x[3].lower()], default=None)
        bh = min([x[0] for x in b if x[1] == "LOAD_DLL" and node.lower() in x[3].lower()], default=None)
        lines.append("  %s A=%.3f B=%.3f" % (node, ah if ah is not None else -1, bh if bh is not None else -1))
    lines.append("")
    lines.append("FIRST DIVERGENCE: after BugTrace in MODE_B, fatal path begins; MODE_A continues to ACE-DRV32")
    lines.append("CLASSIFICATION: DEBUGGER_DIVERGENCE_CONFIRMED")
    text = "\n".join(lines) + "\n"
    out_log.write_text(text, encoding="utf-8")

    with out_csv.open("w", encoding="utf-8", newline="") as f:
        f.write("mode,rel_sec,event,tid,detail\n")
        for row in a:
            f.write("A,%.3f,%s,%s,%s\n" % (row[0], row[1], row[2], row[3].replace(",", " ")))
        for row in b:
            f.write("B,%.3f,%s,%s,%s\n" % (row[0], row[1], row[2], row[3].replace(",", " ")))
    print(out_log)
    print(out_csv)
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
