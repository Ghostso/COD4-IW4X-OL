#!/usr/bin/env python3
"""Resolve <module>+0xRVA addresses in a sh1x crash / lifecycle line to symbols.

bin/codol_crash.txt (written by src/win32/sys_win32_crash.c) and the
"CoDOL lifecycle:" lines in qconsole.log name every address as
``codol_dedrun_next.exe+0x8638 (0x00348638)``.  The RVA is stable across runs
even though the absolute address is not (ASLR), so it can be looked up in the
exe's own symbol table - the mingw link keeps it, no .map file is needed.

    python tools/codol_crash_symbolize.py bin/codol_crash.txt bin/codol_dedrun_next.exe
    grep "CoDOL lifecycle" qconsole.log | python tools/codol_crash_symbolize.py - bin/...exe

The exe must be the one that produced the report; an RVA from another build
resolves to the wrong function silently.
"""
import bisect
import re
import shutil
import subprocess
import sys

ADDR = re.compile(r'([A-Za-z0-9_.\-]+\.(?:exe|dll|EXE|DLL))\+0x([0-9a-fA-F]+)')
# PE default image base for these 32-bit mingw links.
IMAGE_BASE = 0x400000


def load_symbols(exe):
    for tool in ('i686-w64-mingw32-nm', 'nm'):
        if shutil.which(tool):
            cmd = [tool, '--defined-only', exe]
            break
    else:
        # No host nm: try it through WSL, which is where this tree cross-builds.
        cmd = ['wsl', '-e', 'i686-w64-mingw32-nm', '--defined-only',
               exe.replace('\\', '/')]
    out = subprocess.run(cmd, capture_output=True, text=True)
    syms = []
    for line in out.stdout.splitlines():
        parts = line.split()
        if len(parts) != 3:
            continue
        try:
            addr = int(parts[0], 16)
        except ValueError:
            continue
        name = parts[2]
        if name.startswith('.'):
            continue
        syms.append((addr, name.lstrip('_')))
    syms.sort()
    return [a for a, _ in syms], [n for _, n in syms]


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    report, exe = sys.argv[1], sys.argv[2]
    addrs, names = load_symbols(exe)
    if not addrs:
        sys.exit('no symbols read from %s (is it the stripped build?)' % exe)

    exe_name = exe.replace('\\', '/').rsplit('/', 1)[-1].lower()

    def annotate(m):
        if m.group(1).lower() != exe_name:
            return m.group(0)
        va = IMAGE_BASE + int(m.group(2), 16)
        i = bisect.bisect_right(addrs, va) - 1
        if i < 0:
            return m.group(0)
        return '%s [%s+0x%x]' % (m.group(0), names[i], va - addrs[i])

    src = sys.stdin if report == '-' else open(report, encoding='utf-8',
                                               errors='replace')
    for line in src:
        sys.stdout.write(ADDR.sub(annotate, line))


if __name__ == '__main__':
    main()
