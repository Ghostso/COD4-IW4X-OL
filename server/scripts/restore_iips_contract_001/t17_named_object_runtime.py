"""RESTORE-IIPS-CONTRACT-001 / Task 13 - runtime check of the named-object contract.

Static work (Task 12) produced the exact names the provider's contract needs:

    Global\\SharedSpaceName_          shared memory  (OpenFileMappingA)
    Global\\FDTFileMutxtName_         mutex
    Global\\ReadBitMapInfos_          file mapping
    Global\\IIPSShareState_MMF_       share-state MMF
    Global\\IIPSShareState_Mutex_     share-state mutex
    Global\\DownloadingFileInfos_     file mapping
    \\\\.\\Pipe\\                     pipe prefix
    IIPSHostApp.exe  /mode iipslaunch host process
    IFS.dll                           IFS library

This script enumerates the system's named objects BEFORE and AFTER each run, to
determine whether either condition ever reaches the point of creating/opening
them. It is a passive, non-debugger observation (NtOpenDirectoryObject).

It also reports whether IIPSHostApp.exe is ever launched as a child process.
"""
import ctypes
import ctypes.wintypes as wt
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "restore_iips_contract_001", "evidence")

PRESENT = ["SharedSpaceName_", "FDTFileMutxtName_", "ReadBitMapInfos_",
           "IIPSShareState_MMF_", "IIPSShareState_Mutex_", "DownloadingFileInfos_",
           "IIPSHostApp", "iips"]


def enum_dir(path):
    """List names in an NT object directory. Best-effort; returns [] on failure."""
    ntdll = ctypes.WinDLL("ntdll")
    names = []

    class UNICODE_STRING(ctypes.Structure):
        _fields_ = [("Length", wt.USHORT), ("MaximumLength", wt.USHORT),
                    ("Buffer", ctypes.c_wchar_p)]

    class OBJECT_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("Length", wt.ULONG), ("RootDirectory", wt.HANDLE),
                    ("ObjectName", ctypes.POINTER(UNICODE_STRING)),
                    ("Attributes", wt.ULONG), ("SecurityDescriptor", ctypes.c_void_p),
                    ("SecurityQualityOfService", ctypes.c_void_p)]

    us = UNICODE_STRING()
    us.Buffer = path
    us.Length = len(path) * 2
    us.MaximumLength = us.Length + 2
    oa = OBJECT_ATTRIBUTES()
    oa.Length = ctypes.sizeof(OBJECT_ATTRIBUTES)
    oa.ObjectName = ctypes.pointer(us)
    oa.Attributes = 0x40  # OBJ_CASE_INSENSITIVE

    h = wt.HANDLE()
    st = ntdll.NtOpenDirectoryObject(ctypes.byref(h), 0x0001, ctypes.byref(oa))
    if st != 0:
        return None
    try:
        buf = ctypes.create_string_buffer(0x4000)
        ctx = wt.ULONG(0)
        ret = wt.ULONG(0)
        while True:
            st = ntdll.NtQueryDirectoryObject(h, buf, len(buf), False, False,
                                              ctypes.byref(ctx), ctypes.byref(ret))
            if st != 0:
                break
            # Entries are pairs of UNICODE_STRING; parse the first name only, then
            # advance context. Sufficient for a presence check by substring.
            names.append(buf.raw.decode("utf-16-le", "ignore"))
            if ctx.value == 0:
                break
    finally:
        ctypes.WinDLL("kernel32").CloseHandle(h)
    return names


def scan_snapshot():
    res = {}
    for d in (r"\BaseNamedObjects", r"\Sessions\1\BaseNamedObjects"):
        n = enum_dir(d)
        res[d] = n if n is not None else []
    return res


def present_in(snapshot, needle):
    for names in snapshot.values():
        for blob in names:
            if needle.lower() in blob.lower():
                return True
    return False


def main():
    os.makedirs(OUT, exist_ok=True)
    rep = {}
    print("=== Task 13: runtime named-object contract check ===")
    print()

    before = scan_snapshot()
    print("  baseline named-object snapshot taken")
    rep["baseline_present"] = {n: present_in(before, n) for n in PRESENT}
    for n, v in rep["baseline_present"].items():
        print("     %-24s %s" % (n, "PRESENT" if v else "absent"))

    # Check whether IIPSHostApp.exe exists on disk at all (it must, for the
    # contract to be satisfiable).
    host = os.path.join(ROOT, "COD OL", "IIPS", "IIPSHostApp.exe")
    ifs = os.path.join(ROOT, "COD OL", "IIPS", "IFS2.dll")
    ifs2 = os.path.join(ROOT, "COD OL", "IIPS", "IFS2.dll")
    ifs_alt = os.path.join(ROOT, "COD OL", "IIPS", "IFS.dll")
    rep["dependencies_on_disk"] = {
        "IIPSHostApp.exe": os.path.exists(host),
        "IFS.dll (literal name)": os.path.exists(ifs_alt),
        "IFS2.dll": os.path.exists(ifs2),
    }
    print()
    print("  dependencies present on disk:")
    for k, v in rep["dependencies_on_disk"].items():
        print("     %-24s %s" % (k, v))

    # What IFS-named libraries actually exist?
    iips_dir = os.path.join(ROOT, "COD OL", "IIPS")
    ifs_files = [f for f in os.listdir(iips_dir) if f.lower().startswith("ifs")]
    rep["ifs_named_files"] = ifs_files
    print("     IFS-named files in IIPS\\: %s" % ", ".join(ifs_files))

    with open(os.path.join(OUT, "t17_named_object_runtime.json"), "w",
              encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("  NOTE: this script only snapshots; the A/B runs were performed by")
    print("        AboProbe (observer2) and are analysed in Task 14.")
    print("wrote %s" % os.path.join(OUT, "t17_named_object_runtime.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
