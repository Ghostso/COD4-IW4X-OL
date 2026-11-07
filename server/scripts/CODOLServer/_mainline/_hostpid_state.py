import os
import time

BASE = r"COD OL\IIPS"


def show(path):
    if not os.path.exists(path):
        print("MISSING  %s" % path)
        return
    size = os.path.getsize(path)
    print("%-52s size=%-6d mtime=%s" % (
        path, size, time.ctime(os.path.getmtime(path))))
    if size <= 256:
        print("    raw=%r" % open(path, "rb").read())


def main():
    show(os.path.join(BASE, "HostPid"))
    show(os.path.join(BASE, "iips.ini"))
    show(os.path.join(BASE, "IIPSVersion.ini"))

    log_dir = os.path.join(BASE, "TenioLog")
    print()
    print("TenioLog dir exists: %s" % os.path.isdir(log_dir))
    if os.path.isdir(log_dir):
        for name in sorted(os.listdir(log_dir)):
            path = os.path.join(log_dir, name)
            print("  %-40s %8d  %s" % (
                name, os.path.getsize(path), time.ctime(os.path.getmtime(path))))

    print()
    print("top-level IIPS entries:")
    for name in sorted(os.listdir(BASE)):
        path = os.path.join(BASE, name)
        kind = "DIR " if os.path.isdir(path) else "FILE"
        size = 0 if os.path.isdir(path) else os.path.getsize(path)
        print("  %s %-40s %8d  %s" % (
            kind, name, size, time.ctime(os.path.getmtime(path))))


main()
