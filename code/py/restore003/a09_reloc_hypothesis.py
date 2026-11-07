"""EB-003 Agent 09 - falsify or confirm the relocation hypothesis.

Agent 08 showed .localrm has zero base relocations covering 8 hardcoded absolute
addresses that all encode the preferred image base 0x10000000.

Hypothesis H1: "LocalRM_v3.dll loads and exports resolve, but calling
GetResourceManagerII at any base other than 0x10000000 reads/writes the wrong
addresses, so the provider cannot construct its object."

A clean way to test H1 WITHOUT any debugger is to load the DLL in the observer's
own 32-bit process at a base we control, and drive the export twice:
  (1) as loaded (base != 0x10000000, and relocations applied by the loader)
  (2) after loading at the preferred base, if we can reserve it first

If (2) works and (1) does not, H1 is CONFIRMED: the defect is the missing
relocations for the .localrm absolutes, not the ABI or the exports.
"""
import ctypes
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "restore003", "evidence")
DLL = os.path.join(ROOT, "LocalRM_v3.dll")
PREFERRED = 0x10000000

k32 = ctypes.WinDLL("kernel32", use_last_error=True)

k32.VirtualAlloc.restype = ctypes.c_void_p
k32.VirtualAlloc.argtypes = [ctypes.c_void_p, ctypes.c_size_t,
                             ctypes.c_uint32, ctypes.c_uint32]
k32.VirtualFree.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_uint32]
k32.LoadLibraryExW.restype = ctypes.c_void_p
k32.LoadLibraryExW.argtypes = [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_uint32]
k32.GetProcAddress.restype = ctypes.c_void_p
k32.GetProcAddress.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
k32.FreeLibrary.argtypes = [ctypes.c_void_p]
k32.GetModuleHandleA.restype = ctypes.c_void_p
k32.GetModuleHandleA.argtypes = [ctypes.c_char_p]
k32.LoadLibraryW.restype = ctypes.c_void_p
k32.LoadLibraryW.argtypes = [ctypes.c_wchar_p]
k32.GetCurrentProcess.restype = ctypes.c_void_p
k32.GetCurrentProcess.argtypes = []

MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
MEM_RELEASE = 0x8000


def rd32(addr):
    return ctypes.c_uint32.from_address(addr).value


def try_call(handle, base, label):
    p = k32.GetProcAddress(ctypes.c_void_p(handle), b"GetResourceManagerII")
    res = {"label": label, "base": "0x%X" % base,
           "export_addr": ("0x%X" % p) if p else None}
    if not p:
        res["result"] = "EXPORT_MISSING"
        return res
    proto = ctypes.CFUNCTYPE(ctypes.c_uint32)
    fn = proto(p)
    try:
        obj = fn()
        res["returned"] = "0x%X" % obj
        if obj:
            vptr = rd32(obj)
            res["object_vptr"] = "0x%X" % vptr
            res["vptr_in_image"] = bool(base <= vptr < base + 0x60000)
            res["vptr_expected_preferred_range"] = bool(
                PREFERRED <= vptr < PREFERRED + 0x60000)
        # the guard/instance slots the stub addresses
        res["actual_guard_at_base+0x55200"] = "0x%X" % rd32(base + 0x55200)
        res["actual_instance_at_base+0x55204"] = "0x%X" % rd32(base + 0x55204)
        res["result"] = "NO_FAULT"
    except OSError as ex:
        res["result"] = "FAULT"
        res["exception"] = str(ex)
        res["winerror"] = ctypes.get_last_error()
    return res


def main():
    os.makedirs(OUT, exist_ok=True)
    rep = {"preferred_base": "0x%X" % PREFERRED, "dll": DLL}
    print("=== EB-003 Agent 09: relocation hypothesis ===")
    print("  host bits = %d" % (struct.calcsize("P") * 8))
    print("  dll       = %s" % DLL)
    print()

    if struct.calcsize("P") * 8 != 32:
        print("  NOT a 32-bit host; aborting (must not load a PE32 image here).")
        rep["host"] = "not 32-bit"
        with open(os.path.join(OUT, "a09_reloc_hypothesis.json"), "w",
                  encoding="utf-8") as f:
            json.dump(rep, f, indent=2)
        return 0

    # --- Run 1: natural load (loader picks the base and applies relocations) ---
    h1 = k32.LoadLibraryW(DLL)
    if not h1:
        print("  LoadLibraryW failed: %d" % ctypes.get_last_error())
        return 2
    b1 = k32.GetModuleHandleA(b"LocalRM_v3.dll")
    rep["natural_load_base"] = "0x%X" % b1
    print("  natural load base = 0x%X  (preferred 0x%X)" % (b1, PREFERRED))
    rep["natural"] = try_call(h1, b1, "natural")
    for k, v in rep["natural"].items():
        print("    %-38s %s" % (k, v))
    k32.FreeLibrary(ctypes.c_void_p(h1))
    print()

    # --- Run 2: reserve the preferred base first, then load there ---
    reserved = k32.VirtualAlloc(ctypes.c_void_p(PREFERRED), 0x100000,
                                MEM_RESERVE, PAGE_READWRITE)
    print("  reserving preferred base 0x%X -> %s"
          % (PREFERRED, ("0x%X" % reserved) if reserved else "FAILED"))
    if reserved and reserved != PREFERRED:
        k32.VirtualFree(ctypes.c_void_p(reserved), 0, MEM_RELEASE)
        reserved = None

    if reserved:
        # Map it as reserved-but-free so the loader can use it.
        k32.VirtualFree(ctypes.c_void_p(PREFERRED), 0x100000, MEM_RELEASE)
        # Reserve then free creates a hole; load immediately.
        h2 = k32.LoadLibraryW(DLL)
        if h2:
            b2 = k32.GetModuleHandleA(b"LocalRM_v3.dll")
            rep["preferred_attempt_base"] = "0x%X" % b2
            print("  second load base = 0x%X" % b2)
            rep["preferred"] = try_call(h2, b2, "preferred_attempt")
            for k, v in rep["preferred"].items():
                print("    %-38s %s" % (k, v))
            k32.FreeLibrary(ctypes.c_void_p(h2))
    else:
        rep["preferred"] = {"result": "COULD_NOT_RESERVE_PREFERRED_BASE"}
        print("  could not reserve the preferred base (it is already occupied by")
        print("  another module in this host), so the controlled A/B is unavailable here.")

    with open(os.path.join(OUT, "a09_reloc_hypothesis.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print("\nwrote %s" % os.path.join(OUT, "a09_reloc_hypothesis.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
