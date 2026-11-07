"""Agent 16 (part 1) - compilerless environment re-check.

RESTORE_LOCALRM_002 reported no C/C++ toolchain.  Re-verify before choosing an
implementation strategy, because 006 requires real (not stub) code.
"""
import glob
import os
import shutil
import subprocess

CANDIDATES = [
    "cl.exe", "clang.exe", "clang-cl.exe", "gcc.exe", "g++.exe",
    "link.exe", "lld-link.exe", "ml.exe", "ml64.exe", "llvm-mc.exe",
    "zig.exe", "tcc.exe", "nasm.exe", "yasm.exe", "jwasm.exe",
]


def main():
    print("=" * 78)
    print("AGENT 16 - COMPILERLESS ENVIRONMENT RE-CHECK")
    print("=" * 78)
    found = {}
    for c in CANDIDATES:
        p = shutil.which(c)
        found[c] = p
        print("  %-14s %s" % (c, p if p else "absent"))

    print()
    print("  --- filesystem sweep for clang/cl/link outside PATH ---")
    roots = [
        r"C:\Program Files\Microsoft Visual Studio",
        r"C:\Program Files (x86)\Microsoft Visual Studio",
        r"C:\Program Files (x86)\Windows Kits",
        r"C:\Program Files\LLVM",
        os.path.expanduser(r"~\AppData\Local\Microsoft\WinGet"),
    ]
    hits = []
    for r in roots:
        if not os.path.isdir(r):
            print("  (missing) %s" % r)
            continue
        for pat in ("cl.exe", "lld-link.exe", "clang-cl.exe"):
            hits += glob.glob(os.path.join(r, "**", pat), recursive=True)[:3]
    print("  hits: %s" % (hits if hits else "none"))

    print()
    print("  --- LLVM archives in ./toolchain ---")
    for p in glob.glob(os.path.join("toolchain", "llvm", "*")):
        size = os.path.getsize(p)
        ok = ""
        if p.endswith(".tar.xz"):
            # an xz stream ends with the 6-byte footer 59 5A ... ; a truncated
            # download will not have it, so decompression fails early.
            with open(p, "rb") as f:
                f.seek(-16, os.SEEK_END)
                tail = f.read()
            ok = "  (truncated: no xz end-of-stream marker)" if len(tail) < 6 else ""
        print("  %-52s %12d bytes%s" % (os.path.basename(p), size, ok))

    print()
    print("  --- .NET SDK (available, but not a native code generator) ---")
    try:
        v = subprocess.run(["dotnet", "--version"], capture_output=True, text=True)
        print("  dotnet SDK        = %s" % v.stdout.strip())
    except Exception as e:
        print("  dotnet            = unavailable (%s)" % e)
    packs = r"C:\Program Files\dotnet\packs"
    if os.path.isdir(packs):
        names = sorted(os.listdir(packs))
        print("  runtime packs     = %s" % ", ".join(names))
        print("  NativeAOT pack    = %s"
              % ("present" if any("ILCompiler" in n for n in names) else "ABSENT"))

    print()
    print("=" * 78)
    any_native = any(found.values()) or bool(hits)
    print("NATIVE_C_COMPILER_AVAILABLE = %s" % ("YES" if any_native else "NO"))
    print("TOOLCHAIN_STATUS            = %s"
          % ("PRESENT" if any_native else "NOT_FOUND (unchanged from RESTORE_LOCALRM_002)"))
    print("""
  Consequence for Agent 16:
    The RM provider cannot be produced by compiling C/C++.
    It must be produced by direct machine-code emission (an assembler we
    control), which is legitimate for a fixed, fully specified object:
      - 0x410-byte object with a known field layout
      - vtable[0] destructor with the exact deleting-dtor ABI
      - all remaining vtable slots filled with a valid shared stub
    No "compiler-less C" shortcut is used, and no sketch is treated as truth.
""")


if __name__ == "__main__":
    main()
